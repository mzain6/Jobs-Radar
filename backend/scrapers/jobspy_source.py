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


def scrape(
    work_mode: str = "remote",
    country: str = "all",
    location: Optional[str] = None,
    results_wanted: int = 30,
    hours_old: int = 168,
    is_manual: bool = False,
) -> list[dict]:
    """
    Scrape Indeed + LinkedIn via python-jobspy.

    Runs parallel requests per (title, country) combination using ThreadPoolExecutor
    to avoid large OR queries blocking search engines.
    """

    # Determine which countries to loop over
    if country == "all":
        countries = ["US", "CA", "PK"]
    else:
        countries = [country.upper()]

    search_titles = [t for t in JOB_TITLES if len(t) > 2]
    
    tasks = []
    for cc in countries:
        for t in search_titles:
            tasks.append((cc, t))

    all_jobs: list[dict] = []
    seen_urls: set[str] = set()

    from concurrent.futures import ThreadPoolExecutor

    def scrape_title_country(args: tuple[str, str]) -> list[dict]:
        cc, title = args
        loc = location if location else COUNTRY_DEFAULTS.get(cc, "")
        country_indeed = COUNTRY_INDEED.get(cc, "USA")

        # No artificial delay: blast through titles immediately
        import time
        import random
        # Delay removed entirely per user request

        try:
            from jobspy import scrape_jobs
            kwargs: dict = {
                "site_name":       SITE_NAMES,
                "search_term":     title,
                "results_wanted":  results_wanted,
                "country_indeed":  country_indeed,
                "verbose":         0,
                "hours_old":       hours_old,
            }
            if loc:
                kwargs["location"] = loc
            if work_mode == "remote":
                kwargs["is_remote"] = True
            elif work_mode == "onsite":
                kwargs["is_remote"] = False

            # Step 1: Log full parameters
            print(f"[JobSpy] Calling JobSpy: search_term='{title}', location='{loc}', "
                  f"country_indeed='{country_indeed}', hours_old={hours_old}, "
                  f"results_wanted={results_wanted}, work_mode={work_mode}")

            df = scrape_jobs(**kwargs)
            jobs = _df_to_jobs(df, cc)
            
            # Step 5: Explicitly log 0 results vs blocks
            if not jobs:
                print(f"[JobSpy] ZERO RESULTS returned for '{title}' in {cc}. "
                      f"Params: location='{loc}', hours_old={hours_old}, work_mode={work_mode}. "
                      f"This was a clean empty result, not an exception block.")
            else:
                print(f"[JobSpy] SUCCESS: Scraped '{title}' in {cc}: found {len(jobs)} total raw jobs")
                
            return jobs
            
        except ImportError:
            print("[JobSpy] python-jobspy not installed — skipping Indeed/LinkedIn.")
            return []
        except Exception as exc:
            # Step 5: Explicitly catch and log exceptions as potential blocks
            print(f"[JobSpy] BLOCKED OR ERROR scraping '{title}' in {cc}. "
                  f"Params: location='{loc}', hours_old={hours_old}, work_mode={work_mode}. "
                  f"Exception details: {exc}")
            return []

    # Execute scraping for all selected combinations in parallel
    workers = 12 if is_manual else 3
    with ThreadPoolExecutor(max_workers=workers) as executor:
        results = executor.map(scrape_title_country, tasks)

    for job_batch in results:
        for job in job_batch:
            if not title_matches_fixed_list(job["title"]):
                continue
            
            # Strictly filter PK jobs to only include Lahore
            if job["country"] == "PK" and "lahore" not in job["location"].lower():
                continue

            if job["url"] not in seen_urls:
                seen_urls.add(job["url"])
                all_jobs.append(job)

    return all_jobs
