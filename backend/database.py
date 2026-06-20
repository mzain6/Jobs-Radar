"""
database.py — SQLite helpers for Remote Job Radar.
"""

import sqlite3
import os
from contextlib import contextmanager
from datetime import datetime
from typing import Optional
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

DB_PATH = os.environ.get("DATABASE_PATH", os.path.join(os.path.dirname(__file__), "radar.db"))
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://neondb_owner:npg_g6tYMshEfqR1@ep-holy-sunset-aibf04fj-pooler.c-4.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
)


def is_postgres() -> bool:
    """Check if we are using PostgreSQL connection string."""
    return bool(DATABASE_URL and (DATABASE_URL.startswith("postgres://") or DATABASE_URL.startswith("postgresql://")))


def get_connection():
    if is_postgres():
        import psycopg2
        url = DATABASE_URL
        # Normalize legacy postgres:// scheme to postgresql://
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return psycopg2.connect(url)
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn


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
        if is_postgres():
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
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    source      TEXT    NOT NULL,
                    title       TEXT    NOT NULL,
                    company     TEXT    NOT NULL,
                    location    TEXT    NOT NULL DEFAULT '',
                    country     TEXT    NOT NULL DEFAULT '',
                    remote      BOOLEAN NOT NULL DEFAULT 0,
                    url         TEXT    UNIQUE NOT NULL,
                    posted_date TEXT,
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


def upsert_job(job: dict) -> bool:
    """
    Insert a job row. Ignores the insert silently if the URL already exists.
    Returns True if a new row was inserted, False if it was a duplicate.
    """
    normalized_url = normalize_url(job.get("url", ""))
    params = {
        "source":      job.get("source", ""),
        "title":       job.get("title", ""),
        "company":     job.get("company", ""),
        "location":    job.get("location", ""),
        "country":     job.get("country", ""),
        "remote":      True if job.get("remote") else False,
        "url":         normalized_url,
        "posted_date": job.get("posted_date"),
        "description": job.get("description", ""),
    }

    if is_postgres():
        sql = """
            INSERT INTO jobs
                (source, title, company, location, country, remote, url, posted_date, description)
            VALUES
                (%(source)s, %(title)s, %(company)s, %(location)s, %(country)s, %(remote)s, %(url)s, %(posted_date)s, %(description)s)
            ON CONFLICT (url) DO NOTHING
        """
    else:
        sql = """
            INSERT OR IGNORE INTO jobs
                (source, title, company, location, country, remote, url, posted_date, description)
            VALUES
                (:source, :title, :company, :location, :country, :remote, :url, :posted_date, :description)
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

    if source:
        clauses.append("source = :source" if not is_postgres() else "source = %(source)s")
        params["source"] = source
    if country:
        clauses.append("UPPER(country) = :country" if not is_postgres() else "UPPER(country) = %(country)s")
        params["country"] = country.upper()
    if q:
        if is_postgres():
            clauses.append("(title ILIKE %(q)s OR company ILIKE %(q)s)")
        else:
            clauses.append("(title LIKE :q OR company LIKE :q)")
        params["q"] = f"%{q}%"
    if location:
        if is_postgres():
            clauses.append("location ILIKE %(location)s")
        else:
            clauses.append("location LIKE :location")
        params["location"] = f"%{location}%"
    if remote is not None:
        clauses.append("remote = :remote" if not is_postgres() else "remote = %(remote)s")
        params["remote"] = True if remote else False if is_postgres() else 1 if remote else 0

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    
    if is_postgres():
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
    else:
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
            LIMIT :limit
        """
    params["limit"] = limit

    with db() as conn:
        if is_postgres():
            import psycopg2.extras
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
        else:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            return [dict(r) for r in rows]


def get_sources() -> list[str]:
    with db() as conn:
        if is_postgres():
            import psycopg2.extras
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("SELECT DISTINCT source FROM jobs ORDER BY source")
            rows = cursor.fetchall()
            return [r["source"] for r in rows]
        else:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT source FROM jobs ORDER BY source")
            rows = cursor.fetchall()
            return [r["source"] for r in rows]


def get_stats() -> dict:
    with db() as conn:
        if is_postgres():
            import psycopg2.extras
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            cursor.execute("SELECT COUNT(*) AS n FROM jobs")
            total = cursor.fetchone()["n"]
            
            cursor.execute("SELECT country, COUNT(*) AS n FROM jobs GROUP BY country ORDER BY n DESC")
            by_country = cursor.fetchall()
            
            cursor.execute("SELECT source, COUNT(*) AS n FROM jobs GROUP BY source ORDER BY n DESC")
            by_source = cursor.fetchall()
        else:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) AS n FROM jobs")
            total = cursor.fetchone()["n"]
            
            cursor.execute("SELECT country, COUNT(*) AS n FROM jobs GROUP BY country ORDER BY n DESC")
            by_country = cursor.fetchall()
            
            cursor.execute("SELECT source, COUNT(*) AS n FROM jobs GROUP BY source ORDER BY n DESC")
            by_source = cursor.fetchall()
            
    return {
        "total": total,
        "by_country": [dict(r) for r in by_country],
        "by_source": [dict(r) for r in by_source],
    }
