"""
weworkremotely.py — Scraper for We Work Remotely RSS feeds.

Rules:
  - Always remote jobs → skip entirely when work_mode == "onsite" or country == "PK".
  - Keyword-match title + company text against query.
"""

import xml.etree.ElementTree as ET
from typing import Optional
import requests

from backend.filters import title_matches_fixed_list

WWR_FEEDS = [
    ("programming",       "https://weworkremotely.com/categories/remote-programming-jobs.rss"),
    ("devops",            "https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss"),
    ("design",            "https://weworkremotely.com/categories/remote-design-jobs.rss"),
    ("customer-support",  "https://weworkremotely.com/categories/remote-customer-support-jobs.rss"),
    ("product",           "https://weworkremotely.com/categories/remote-product-jobs.rss"),
    ("marketing",         "https://weworkremotely.com/categories/remote-marketing-jobs.rss"),
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; RemoteJobRadar/1.0; +https://github.com/remote-job-radar)"
    )
}


def _parse_feed(category: str, xml_text: str) -> list[dict]:
    """Parse a single WWR RSS feed and return matching job dicts."""
    jobs: list[dict] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return jobs

    channel = root.find("channel")
    if channel is None:
        return jobs

    for item in channel.findall("item"):
        title_el = item.find("title")
        link_el  = item.find("link")
        pub_el   = item.find("pubDate")

        if title_el is None or link_el is None:
            continue

        raw_title = title_el.text or ""
        # WWR title format: "Company: Job Title at Company"
        # Extract company and job title
        if ": " in raw_title:
            parts = raw_title.split(": ", 1)
            company = parts[0].strip()
            job_title = parts[1].strip()
        else:
            company = ""
            job_title = raw_title.strip()

        url = (link_el.text or "").strip()
        posted_date = (pub_el.text or "").strip() if pub_el is not None else None

        # description / CDATA
        desc_el = item.find("description")
        description = (desc_el.text or "").strip() if desc_el is not None else ""

        # Keyword filter
        search_text = f"{job_title} {company}"
        if not title_matches_fixed_list(search_text):
            continue

        if not url:
            continue

        jobs.append({
            "source":      "weworkremotely",
            "title":       job_title,
            "company":     company,
            "location":    "Remote",
            "country":     "US",   # WWR is US/global — label as US (mostly English-speaking)
            "remote":      True,
            "url":         url,
            "posted_date": posted_date,
            "description": description,
        })

    return jobs


def scrape(
    work_mode: str = "remote",
    country: str = "all",
    location: Optional[str] = None,
) -> list[dict]:
    """
    Fetch and return job dicts from all WWR RSS feeds.
    Returns empty list when work_mode == 'onsite' or country == 'PK'.
    """
    # WWR is remote-only — skip for onsite-only requests
    # Also skip for PK-only requests (WWR is mostly US/global)
    if work_mode == "onsite" or (country == "PK"):
        return []

    all_jobs: list[dict] = []

    for category, feed_url in WWR_FEEDS:
        try:
            resp = requests.get(feed_url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as exc:
            print(f"[WWR] Failed to fetch {feed_url}: {exc}")
            continue

        jobs = _parse_feed(category, resp.text)
        all_jobs.extend(jobs)

    # Deduplicate by URL within this batch
    seen: set[str] = set()
    unique: list[dict] = []
    for job in all_jobs:
        if job["url"] not in seen:
            seen.add(job["url"])
            unique.append(job)

    return unique
