"""
database.py — PostgreSQL helpers for Remote Job Radar.
"""

import os
import email.utils
from contextlib import contextmanager
from datetime import datetime, date, timedelta
from typing import Optional
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://neondb_owner:npg_g6tYMshEfqR1@ep-holy-sunset-aibf04fj-pooler.c-4.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
)


def get_connection():
    url = DATABASE_URL
    # Normalize legacy postgres:// scheme to postgresql://
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return psycopg2.connect(url)


@contextmanager
def db():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Create the jobs table and indexes."""
    with db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id          SERIAL PRIMARY KEY,
                source      VARCHAR(100) NOT NULL,
                title       VARCHAR(255) NOT NULL,
                company     VARCHAR(255) NOT NULL,
                location    VARCHAR(255) NOT NULL DEFAULT '',
                country     VARCHAR(100) NOT NULL DEFAULT '',
                remote      BOOLEAN NOT NULL DEFAULT FALSE,
                url         TEXT    UNIQUE NOT NULL,
                posted_date VARCHAR(100),
                description TEXT,
                scraped_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_url ON jobs(url)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs(source)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_country ON jobs(country)")


def normalize_url(url: str) -> str:
    """Normalize job URLs for deduplication."""
    if not url:
        return ""
    try:
        parsed = urlparse(url.strip())
        netloc = parsed.netloc.lower()
        if "indeed.com" in netloc:
            # Keep only the 'jk' parameter for Indeed
            qs = parse_qs(parsed.query)
            jk_vals = qs.get("jk")
            if jk_vals:
                new_query = urlencode({"jk": jk_vals[0]})
                return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, ""))
        # For LinkedIn and all other sources, remove query parameters and fragments
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, "", ""))
    except Exception:
        return url


def normalize_date(date_str: Optional[str]) -> Optional[str]:
    """Standardize different scraper date formats into YYYY-MM-DD."""
    if not date_str:
        return None
    date_str = date_str.strip()
    
    # 1. Try ISO format
    try:
        iso_str = date_str
        if iso_str.endswith('Z'):
            iso_str = iso_str[:-1]
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        pass

    # 2. Try RFC 822 format (e.g., Sat, 20 Jun 2026 21:00:33 +0000)
    try:
        dt = email.utils.parsedate_to_datetime(date_str)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        pass

    # 3. Try parsing YYYY-MM-DD directly
    try:
        dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
        return dt.strftime("%Y-%m-%d")
    except Exception:
        pass

    # 4. Try parsing "Nov 7, 25" (%b %d, %y)
    try:
        dt = datetime.strptime(date_str, "%b %d, %y")
        return dt.strftime("%Y-%m-%d")
    except Exception:
        pass

    # 5. Try parsing "Nov 7, 2025" (%b %d, %Y)
    try:
        dt = datetime.strptime(date_str, "%b %d, %Y")
        return dt.strftime("%Y-%m-%d")
    except Exception:
        pass

    # 6. Try parsing "June 5, 2026" (%B %d, %Y)
    try:
        dt = datetime.strptime(date_str, "%B %d, %Y")
        return dt.strftime("%Y-%m-%d")
    except Exception:
        pass

    # 7. Try parsing "June 5, 26" (%B %d, %y)
    try:
        dt = datetime.strptime(date_str, "%B %d, %y")
        return dt.strftime("%Y-%m-%d")
    except Exception:
        pass

    return None


def upsert_job(job: dict) -> bool:
    """
    Insert a job row. Ignores the insert silently if the URL already exists.
    Returns True if a new row was inserted, False if it was a duplicate.
    """
    normalized_url = normalize_url(job.get("url", ""))
    normalized_date = normalize_date(job.get("posted_date"))
    params = {
        "source":      job.get("source", ""),
        "title":       job.get("title", ""),
        "company":     job.get("company", ""),
        "location":    job.get("location", ""),
        "country":     job.get("country", ""),
        "remote":      True if job.get("remote") else False,
        "url":         normalized_url,
        "posted_date": normalized_date,
        "description": job.get("description", ""),
    }

    sql = """
        INSERT INTO jobs
            (source, title, company, location, country, remote, url, posted_date, description)
        VALUES
            (%(source)s, %(title)s, %(company)s, %(location)s, %(country)s, %(remote)s, %(url)s, %(posted_date)s, %(description)s)
        ON CONFLICT (url) DO NOTHING
    """

    with db() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        return cursor.rowcount > 0


def upsert_jobs(jobs: list[dict]) -> tuple[int, int]:
    """
    Batch upsert. Returns (total_attempted, new_inserts).
    """
    new = 0
    for job in jobs:
        if upsert_job(job):
            new += 1
    return len(jobs), new


def get_jobs(
    source: Optional[str] = None,
    country: Optional[str] = None,
    q: Optional[str] = None,
    location: Optional[str] = None,
    remote: Optional[bool] = None,
    limit: int = 500,
) -> list[dict]:
    """Return stored jobs, newest first, with optional filters."""
    clauses = []
    params: dict = {}

    # Filter out jobs older than 7 days (or keep jobs with no date metadata)
    cutoff_date = (date.today() - timedelta(days=7)).strftime("%Y-%m-%d")
    clauses.append("(posted_date >= %(cutoff_date)s OR posted_date IS NULL OR posted_date = '')")
    params["cutoff_date"] = cutoff_date

    if source:
        clauses.append("source = %(source)s")
        params["source"] = source
    if country:
        clauses.append("UPPER(country) = %(country)s")
        params["country"] = country.upper()
    if q:
        clauses.append("(title ILIKE %(q)s OR company ILIKE %(q)s)")
        params["q"] = f"%{q}%"
    if location:
        clauses.append("location ILIKE %(location)s")
        params["location"] = f"%{location}%"
    if remote is not None:
        clauses.append("remote = %(remote)s")
        params["remote"] = True if remote else False

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = f"""
        SELECT id, source, title, company, location, country,
               remote, url, posted_date, description, scraped_at
        FROM jobs
        {where}
        ORDER BY
            CASE WHEN posted_date IS NULL OR posted_date = '' THEN 1 ELSE 0 END,
            posted_date DESC,
            scraped_at DESC,
            id DESC
        LIMIT %(limit)s
    """
    params["limit"] = limit

    with db() as conn:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        
        res = []
        for r in rows:
            d = dict(r)
            if isinstance(d.get("scraped_at"), datetime):
                d["scraped_at"] = d["scraped_at"].isoformat()
            res.append(d)
        return res


def get_sources() -> list[str]:
    with db() as conn:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT DISTINCT source FROM jobs ORDER BY source")
        rows = cursor.fetchall()
        return [r["source"] for r in rows]


def get_stats() -> dict:
    cutoff_date = (date.today() - timedelta(days=7)).strftime("%Y-%m-%d")
    with db() as conn:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cursor.execute(
            "SELECT COUNT(*) AS n FROM jobs WHERE (posted_date >= %s OR posted_date IS NULL OR posted_date = '')",
            (cutoff_date,)
        )
        total = cursor.fetchone()["n"]

        cursor.execute(
            "SELECT country, COUNT(*) AS n FROM jobs WHERE (posted_date >= %s OR posted_date IS NULL OR posted_date = '') GROUP BY country ORDER BY n DESC",
            (cutoff_date,)
        )
        by_country = cursor.fetchall()

        cursor.execute(
            "SELECT source, COUNT(*) AS n FROM jobs WHERE (posted_date >= %s OR posted_date IS NULL OR posted_date = '') GROUP BY source ORDER BY n DESC",
            (cutoff_date,)
        )
        by_source = cursor.fetchall()

    return {
        "total": total,
        "by_country": [dict(r) for r in by_country],
        "by_source": [dict(r) for r in by_source],
    }
