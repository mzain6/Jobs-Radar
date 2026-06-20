"""
filters.py — Shared filter utilities for Remote Job Radar scrapers.
"""

import re
from typing import Optional

JOB_TITLES = [
    "Associate Software Engineer",
    "Python Developer",
    "Junior Python Developer",
    "Artificial Intelligence Engineer",
    "Machine Learning Engineer",
    "ML Engineer",
    "ML",
    "AI",
    "Django Developer",
    "Backend Developer",
    "FastAPI",
    "Flask",
]


def title_matches_fixed_list(title: str) -> bool:
    """
    Check if a job title (or company description text) matches any entry in JOB_TITLES.
    Uses case-insensitive matching. For very short entries (length <= 2, like ML/AI),
    checks using word boundaries to avoid false matches (e.g. matching 'email' or 'html').
    """
    if not title:
        return False
    title_lower = title.lower()
    for pt in JOB_TITLES:
        pt_lower = pt.lower()
        if len(pt) <= 2:
            if re.search(r"\b" + re.escape(pt_lower) + r"\b", title_lower):
                return True
        else:
            if pt_lower in title_lower:
                return True
    return False


def keyword_match(text: str, query: str) -> bool:
    """Return True if all words of query appear in text (case-insensitive)."""
    if not query:
        return True
    text_lower = text.lower()
    return all(word.lower() in text_lower for word in query.split())


def location_match(job_location: str, filter_location: str) -> bool:
    """Return True if filter_location is a substring of job_location."""
    if not filter_location:
        return True
    return filter_location.lower() in job_location.lower()


def is_remote_job(job_location: str) -> bool:
    """
    Heuristic: does the location string indicate a remote position?
    Checks for common remote indicators.
    """
    indicators = ["remote", "anywhere", "worldwide", "work from home", "wfh", "distributed"]
    loc_lower = job_location.lower()
    return any(ind in loc_lower for ind in indicators)


def work_mode_pass(job_location: str, work_mode: str) -> bool:
    """
    Check if a job's location string satisfies the requested work_mode.
    work_mode: 'remote' | 'onsite' | 'both'
    """
    if work_mode == "both":
        return True
    remote = is_remote_job(job_location)
    if work_mode == "remote":
        return remote
    if work_mode == "onsite":
        return not remote
    return True


def normalize_country(raw: str) -> str:
    """
    Map a raw country string from a job board to a short code.
    Falls back to the raw string if unknown.
    """
    raw_lower = raw.lower()
    if "united states" in raw_lower or raw_lower in ("us", "usa", "u.s.", "u.s.a."):
        return "US"
    if "canada" in raw_lower or raw_lower == "ca":
        return "CA"
    if "pakistan" in raw_lower or raw_lower == "pk":
        return "PK"
    return raw.upper()[:2] if raw else ""


COUNTRY_DEFAULTS: dict[str, str] = {
    "US": "",          # whole US — jobspy handles it
    "CA": "",          # whole Canada
    "PK": "Lahore, Pakistan",
}

COUNTRY_INDEED: dict[str, str] = {
    "US": "USA",
    "CA": "Canada",
    "PK": "Pakistan",
}
