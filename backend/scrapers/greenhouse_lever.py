"""
greenhouse_lever.py — Scrapers for Greenhouse and Lever public job board APIs.

Greenhouse: https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true
Lever:      https://api.lever.co/v0/postings/{slug}?mode=json

Filtering:
  - work_mode: match location string for "remote" keyword.
  - location:  substring match against job location.
  - query:     keyword match against job title.
"""

import re
from typing import Optional
import requests

from backend.filters import title_matches_fixed_list, location_match, work_mode_pass, normalize_country

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; RemoteJobRadar/1.0)"
    )
}

GREENHOUSE_TOKENS = [
    "gitlab",
    "stripe",
    "airbnb",
    "figma",
    "reddit",
    "okta",
    "cloudflare",
    "mongodb",
    "elastic",
    "webflow",
    "discord",
    "robinhood",
]

LEVER_SLUGS = [
    "netflix",
    "plaid",
    "palantir",
    "atlassian",
]


def _strip_html(text: str) -> str:
    """Remove HTML tags from a string."""
    return re.sub(r"<[^>]+>", " ", text or "").strip()


# ─── Greenhouse ──────────────────────────────────────────────────────────────

def _fetch_greenhouse(token: str) -> list[dict]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        print(f"[Greenhouse] {token}: {exc}")
        return []

    jobs = []
    for j in data.get("jobs", []):
        location = (j.get("location") or {}).get("name", "")
        job_url  = j.get("absolute_url", "")
        title    = j.get("title", "")
        content  = _strip_html(j.get("content", ""))
        updated  = j.get("updated_at", "")

        if not job_url:
            continue

        jobs.append({
            "source":      "greenhouse",
            "title":       title,
            "company":     token.capitalize(),
            "location":    location,
            "country":     "",       # will be inferred by filter
            "remote":      "remote" in location.lower(),
            "url":         job_url,
            "posted_date": updated,
            "description": content,
        })
    return jobs


def scrape_greenhouse(
    work_mode: str,
    location: Optional[str],
) -> list[dict]:
    results = []
    from concurrent.futures import ThreadPoolExecutor

    def process_token(token: str) -> list[dict]:
        token_results = []
        raw = _fetch_greenhouse(token)
        for job in raw:
            if not title_matches_fixed_list(job["title"]):
                continue
            if not work_mode_pass(job["location"], work_mode):
                continue
            if location and not location_match(job["location"], location):
                continue
            # Infer country from location string
            job["country"] = _infer_country(job["location"])
            token_results.append(job)
        return token_results

    with ThreadPoolExecutor(max_workers=len(GREENHOUSE_TOKENS)) as executor:
        token_lists = executor.map(process_token, GREENHOUSE_TOKENS)

    for sublist in token_lists:
        results.extend(sublist)
    return results


# ─── Lever ───────────────────────────────────────────────────────────────────

def _fetch_lever(slug: str) -> list[dict]:
    url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        print(f"[Lever] {slug}: {exc}")
        return []

    jobs = []
    if not isinstance(data, list):
        return jobs

    for j in data:
        location = j.get("categories", {}).get("location", "") or j.get("workplaceType", "")
        title    = j.get("text", "")
        job_url  = j.get("hostedUrl", "")
        created  = j.get("createdAt")
        # Lever returns milliseconds epoch
        posted_date = None
        if created:
            try:
                from datetime import datetime
                posted_date = datetime.utcfromtimestamp(created / 1000).isoformat()
            except Exception:
                posted_date = str(created)

        # Description from lists
        desc_parts = []
        for section in j.get("lists", []):
            desc_parts.append(section.get("text", ""))
            desc_parts.append(section.get("content", ""))
        description = _strip_html(" ".join(desc_parts))

        if not job_url:
            continue

        jobs.append({
            "source":      "lever",
            "title":       title,
            "company":     slug.capitalize(),
            "location":    location,
            "country":     "",
            "remote":      "remote" in location.lower(),
            "url":         job_url,
            "posted_date": posted_date,
            "description": description,
        })
    return jobs


def scrape_lever(
    work_mode: str,
    location: Optional[str],
) -> list[dict]:
    results = []
    from concurrent.futures import ThreadPoolExecutor

    def process_slug(slug: str) -> list[dict]:
        slug_results = []
        raw = _fetch_lever(slug)
        for job in raw:
            if not title_matches_fixed_list(job["title"]):
                continue
            if not work_mode_pass(job["location"], work_mode):
                continue
            if location and not location_match(job["location"], location):
                continue
            job["country"] = _infer_country(job["location"])
            slug_results.append(job)
        return slug_results

    with ThreadPoolExecutor(max_workers=len(LEVER_SLUGS)) as executor:
        slug_lists = executor.map(process_slug, LEVER_SLUGS)

    for sublist in slug_lists:
        results.extend(sublist)
    return results


# ─── Combined entry point ─────────────────────────────────────────────────────

def scrape(
    work_mode: str = "remote",
    country: str = "all",
    location: Optional[str] = None,
) -> list[dict]:
    """Return combined Greenhouse + Lever jobs matching the given parameters."""
    gh = scrape_greenhouse(work_mode, location)
    lv = scrape_lever(work_mode, location)
    return gh + lv


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _infer_country(location: str) -> str:
    """Best-effort country inference from a location string."""
    loc_lower = location.lower()
    if any(x in loc_lower for x in ("canada", ", ca", "ontario", "british columbia", "toronto", "vancouver")):
        return "CA"
    if any(x in loc_lower for x in ("pakistan", "lahore", "karachi", "islamabad")):
        return "PK"
    if any(x in loc_lower for x in (
        "united states", ", us", ", usa", "new york", "san francisco", "austin",
        "seattle", "chicago", "boston", "los angeles", "remote",
    )):
        return "US"
    return "US"   # default to US for Western-focused boards
