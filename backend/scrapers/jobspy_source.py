"""

jobspy_source.py — Indeed + LinkedIn scraper via python-jobspy.

Mapping:
  country US  → country_indeed="USA"
  country CA  → country_indeed="Canada"
  country PK  → country_indeed="Pakistan"
  country all → loop over US + CA + PK

Default locations:
  US → "" (whole US)
  CA → "" (whole Canada)
  PK → "Pakistan" (whole country)
"""

from typing import Optional
import pandas as pd

from backend.filters import COUNTRY_DEFAULTS, COUNTRY_INDEED, JOB_TITLES, title_matches_fixed_list

SITE_NAMES = ["indeed", "linkedin"]


def _df_to_jobs(df: pd.DataFrame, country_code: str) -> list[dict]:
    """Convert a jobspy DataFrame to our internal job dict format."""
    jobs: list[dict] = []
    if df is None or df.empty:
        return jobs

    for _, row in df.iterrows():
        title   = str(row.get("title") or "").strip()
        company = str(row.get("company") or "").strip()
        url     = str(row.get("job_url") or "").strip()

        if not url or not title:
            continue

        # Build location string using location column, fallback to city/state
        location_raw = str(row.get("location") or "").strip()
        if location_raw and location_raw.lower() != "nan":
            location = location_raw
        else:
            city  = str(row.get("city") or "").strip()
            state = str(row.get("state") or "").strip()
            location_parts = [p for p in [city, state] if p and p.lower() != "nan"]
            location = ", ".join(location_parts) if location_parts else ""

        is_remote_val = row.get("is_remote")
        if is_remote_val is not None and not pd.isna(is_remote_val):
            is_remote = bool(is_remote_val)
        else:
            is_remote = "remote" in location.lower() if location else False

        # If location is empty, assign a sensible default based on remote status
        if not location:
            location = "Remote" if is_remote else "On-site"

        # posted_date
        posted = row.get("date_posted")
        posted_date = str(posted) if posted is not None and str(posted) != "NaT" else None

        description = str(row.get("description") or "").strip()
        source_site = str(row.get("site") or "jobspy").lower()

        jobs.append({
            "source":      source_site,
            "title":       title,
            "company":     company,
            "location":    location,
            "country":     country_code,
            "remote":      is_remote,
            "url":         url,
            "posted_date": posted_date,
            "description": description[:2000] if description else "",  # cap size
        })

    return jobs


def _scrape_one_country(
    query: str,
    country_code: str,
    location_str: str,
    is_remote: bool,
    results_wanted: int = 30,
) -> list[dict]:
    """Scrape Indeed + LinkedIn for one country. Returns list of job dicts."""
    country_indeed = COUNTRY_INDEED.get(country_code, "USA")

    try:
        from jobspy import scrape_jobs  # lazy import — not installed at module load
        kwargs: dict = {
            "site_name":       SITE_NAMES,
            "search_term":     query,
            "results_wanted":  results_wanted,
            "country_indeed":  country_indeed,
            "verbose":         0,
        }
        if location_str:
            kwargs["location"] = location_str
        if is_remote:
            kwargs["is_remote"] = True

        df = scrape_jobs(**kwargs)
        return _df_to_jobs(df, country_code)

    except ImportError:
        print("[JobSpy] python-jobspy not installed — skipping Indeed/LinkedIn.")
        return []
    except Exception as exc:
        print(f"[JobSpy] Error scraping {country_code}: {exc}")
        return []


def scrape(
    work_mode: str = "remote",
    country: str = "all",
    location: Optional[str] = None,
    results_wanted: int = 40,
) -> list[dict]:
    """
    Scrape Indeed + LinkedIn via python-jobspy.

    For US/CA: uses a single combined OR query (fast).
    For PK: loops per title with higher results_wanted (more results from a smaller market).

    country values: "US" | "CA" | "PK" | "all"
    """
    is_remote = (work_mode == "remote")

    # Determine which countries to loop over
    if country == "all":
        countries = ["US", "CA", "PK"]
    else:
        countries = [country.upper()]

    # Combined OR query for US/CA (fast, single request)
    search_titles = [t for t in JOB_TITLES if len(t) > 2]
    combined_query = " OR ".join([f'"{title}"' for title in search_titles])

    all_jobs: list[dict] = []
    seen_urls: set[str] = set()

    for cc in countries:
        # Location: use the explicit param if given, else the per-country default
        loc = location if location else COUNTRY_DEFAULTS.get(cc, "")

        if cc == "PK":
            # PK has fewer listings — loop per title for maximum coverage
            for title in JOB_TITLES:
                jobs = _scrape_one_country(
                    query=title,
                    country_code=cc,
                    location_str=loc,
                    is_remote=is_remote,
                    results_wanted=20,   # 20 per title × 12 titles = up to 240 raw
                )
                print(f"[JobSpy] PK query '{title}': found {len(jobs)} raw jobs")
                for job in jobs:
                    if not title_matches_fixed_list(job["title"]):
                        continue
                    if job["url"] not in seen_urls:
                        seen_urls.add(job["url"])
                        all_jobs.append(job)
        else:
            # US / CA — single combined OR query (fast)
            jobs = _scrape_one_country(
                query=combined_query,
                country_code=cc,
                location_str=loc,
                is_remote=is_remote,
                results_wanted=results_wanted,
            )
            print(f"[JobSpy] Scraped combined query for country {cc}: found {len(jobs)} total raw jobs")
            for job in jobs:
                if not title_matches_fixed_list(job["title"]):
                    continue
                if job["url"] not in seen_urls:
                    seen_urls.add(job["url"])
                    all_jobs.append(job)

    return all_jobs
