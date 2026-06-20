"""
main.py — FastAPI entry point for Remote Job Radar.
"""

import os
from typing import Optional, Literal
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.database import init_db, upsert_jobs, get_jobs, get_sources, get_stats
from backend.scrapers import weworkremotely, greenhouse_lever, jobspy_source

# ─── Lifespan ────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="Remote Job Radar", version="1.0.0", lifespan=lifespan)

# ─── Static frontend ─────────────────────────────────────────────────────────

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
FRONTEND_DIR = os.path.abspath(FRONTEND_DIR)

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/", include_in_schema=False)
async def serve_index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


# ─── Models ──────────────────────────────────────────────────────────────────

class ScrapeRequest(BaseModel):
    work_mode: Literal["remote", "onsite", "both"]    = "remote"
    country:   Literal["US", "CA", "PK", "all"]       = "all"
    location:  Optional[str]                           = None


# ─── Scrape Worker ───────────────────────────────────────────────────────────

def run_scrape(req: ScrapeRequest) -> tuple[int, int]:
    """Helper to run scrapers synchronously and return (total_scraped, new_inserted)."""
    work_mode = req.work_mode
    country   = req.country
    location  = req.location.strip() if req.location else None

    all_jobs: list[dict] = []

    # ── We Work Remotely ──────────────────────────────────────────────────────
    try:
        wwr_jobs = weworkremotely.scrape(
            work_mode=work_mode,
            country=country,
            location=location,
        )
        print(f"[WWR] Fetched {len(wwr_jobs)} jobs")
        all_jobs.extend(wwr_jobs)
    except Exception as exc:
        print(f"[WWR] Scraper error: {exc}")

    # ── Greenhouse + Lever ────────────────────────────────────────────────────
    try:
        gl_jobs = greenhouse_lever.scrape(
            work_mode=work_mode,
            country=country,
            location=location,
        )
        print(f"[Greenhouse/Lever] Fetched {len(gl_jobs)} jobs")
        all_jobs.extend(gl_jobs)
    except Exception as exc:
        print(f"[Greenhouse/Lever] Scraper error: {exc}")

    # ── JobSpy (Indeed + LinkedIn) ────────────────────────────────────────────
    try:
        js_jobs = jobspy_source.scrape(
            work_mode=work_mode,
            country=country,
            location=location,
        )
        print(f"[JobSpy] Fetched {len(js_jobs)} jobs")
        all_jobs.extend(js_jobs)
    except Exception as exc:
        print(f"[JobSpy] Scraper error: {exc}")

    # ── Upsert ────────────────────────────────────────────────────────────────
    scraped, new = upsert_jobs(all_jobs)
    return scraped, new


# ─── API routes ──────────────────────────────────────────────────────────────

@app.get("/api/jobs")
async def api_get_jobs(
    source:   Optional[str]  = Query(None),
    country:  Optional[str]  = Query(None),
    q:        Optional[str]  = Query(None),
    location: Optional[str]  = Query(None),
    remote:   Optional[bool] = Query(None),
    limit:    int            = Query(500, ge=1, le=2000),
):
    jobs = get_jobs(
        source=source,
        country=country,
        q=q,
        location=location,
        remote=remote,
        limit=limit,
    )
    return {"jobs": jobs, "count": len(jobs)}


@app.get("/api/sources")
async def api_get_sources():
    return {"sources": get_sources()}


@app.get("/api/stats")
async def api_get_stats():
    return get_stats()


@app.post("/api/scrape")
async def api_scrape(
    req: ScrapeRequest,
    background_tasks: BackgroundTasks,
    async_scrape: bool = Query(False, alias="async")
):
    """
    Run all applicable scrapers for the given parameters and upsert results.
    If async=true is passed as a query parameter, the task is run in the background
    to prevent connection timeouts.
    """
    if async_scrape:
        background_tasks.add_task(run_scrape, req)
        return {"status": "queued", "message": "Scaping task queued in background"}
    else:
        scraped, new = run_scrape(req)
        return {"scraped": scraped, "new": new}


@app.get("/api/scrape")
async def api_scrape_get(
    background_tasks: BackgroundTasks,
    work_mode: str = Query("remote"),
    country: str = Query("all"),
    location: Optional[str] = Query(None),
    async_scrape: bool = Query(True, alias="async")
):
    """
    HTTP GET wrapper to trigger a scrape. Defaults to async=True so browser/cron hits return immediately.
    """
    req = ScrapeRequest(work_mode=work_mode, country=country, location=location)
    if async_scrape:
        background_tasks.add_task(run_scrape, req)
        return {"status": "queued", "message": "Scraping task queued in background"}
    else:
        scraped, new = run_scrape(req)
        return {"scraped": scraped, "new": new}
