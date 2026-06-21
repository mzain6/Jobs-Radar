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

from datetime import datetime
from backend.database import init_db, upsert_jobs, get_jobs, get_sources, get_stats, acquire_scrape_lock, release_scrape_lock, log_scrape_run
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
    work_mode: Literal["remote", "onsite", "both"]    = "both"
    country:   Literal["US", "CA", "PK", "all"]       = "all"
    location:  Optional[str]                           = None


# ─── Scrape Worker ───────────────────────────────────────────────────────────

is_scraping = False

def run_scrape(req: ScrapeRequest, job_name: str = "manual") -> tuple[int, int]:
    """Helper to run scrapers synchronously and return (total_scraped, new_inserted)."""
    if not acquire_scrape_lock(job_name):
        print(f"[Scraper] skipped — {job_name} already in progress")
        log_scrape_run(job_name, datetime.now(), datetime.now(), 0, 0, "skipped_locked")
        return 0, 0

    global is_scraping
    is_scraping = True
    
    started_at = datetime.now()
    hours_old = 2 if job_name == "1hr_recent" else 72
    
    work_mode = req.work_mode
    country   = req.country
    location  = req.location.strip() if req.location else None

    total_scraped = 0
    total_new = 0

    try:
        # ── We Work Remotely ──────────────────────────────────────────────────────
        try:
            print("[WWR] Starting scrape...")
            wwr_jobs = weworkremotely.scrape(
                work_mode=work_mode,
                country=country,
                location=location,
            )
            scraped, new = upsert_jobs(wwr_jobs)
            total_scraped += scraped
            total_new += new
            print(f"[WWR] Finished scrape: fetched {scraped} jobs, {new} new database inserts")
        except Exception as exc:
            print(f"[WWR] Scraper error: {exc}")

        # ── Greenhouse + Lever ────────────────────────────────────────────────────
        try:
            print("[Greenhouse/Lever] Starting scrape...")
            gl_jobs = greenhouse_lever.scrape(
                work_mode=work_mode,
                country=country,
                location=location,
            )
            scraped, new = upsert_jobs(gl_jobs)
            total_scraped += scraped
            total_new += new
            print(f"[Greenhouse/Lever] Finished scrape: fetched {scraped} jobs, {new} new database inserts")
        except Exception as exc:
            print(f"[Greenhouse/Lever] Scraper error: {exc}")

        # ── JobSpy (Indeed + LinkedIn) ────────────────────────────────────────────
        try:
            print("[JobSpy] Starting scrape (Indeed & LinkedIn)...")
            js_jobs = jobspy_source.scrape(
                work_mode=work_mode,
                country=country,
                location=location,
                hours_old=hours_old,
            )
            scraped, new = upsert_jobs(js_jobs)
            total_scraped += scraped
            total_new += new
            print(f"[JobSpy] Finished scrape: fetched {scraped} jobs, {new} new database inserts")
        except Exception as exc:
            print(f"[JobSpy] Scraper error: {exc}")

        print(f"[Scraper] All scrapers completed. Total scraped: {total_scraped}, Total new inserts: {total_new}")
        log_scrape_run(job_name, started_at, datetime.now(), total_scraped, total_new, "success")
    except Exception as exc:
        print(f"[Scraper] Fatal error: {exc}")
        log_scrape_run(job_name, started_at, datetime.now(), total_scraped, total_new, "error")
    finally:
        is_scraping = False
        release_scrape_lock()
        
    return total_scraped, total_new


# ─── API routes ──────────────────────────────────────────────────────────────

@app.get("/api/scrape/status")
async def api_scrape_status():
    """Return whether a scraping job is currently running."""
    global is_scraping
    return {"is_scraping": is_scraping}


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


@app.get("/api/cron/1hr")
async def api_cron_1hr(background_tasks: BackgroundTasks):
    """Triggered by cron every 1 hour to fetch recent jobs."""
    req = ScrapeRequest(work_mode="both", country="all")
    background_tasks.add_task(run_scrape, req, "1hr_recent")
    return {"status": "queued", "job": "1hr_recent"}


@app.get("/api/cron/4hr")
async def api_cron_4hr(background_tasks: BackgroundTasks):
    """Triggered by cron every 4 hours for a full sweep."""
    req = ScrapeRequest(work_mode="both", country="all")
    background_tasks.add_task(run_scrape, req, "4hr_full")
    return {"status": "queued", "job": "4hr_full"}


@app.post("/api/scrape")
async def api_scrape(
    req: ScrapeRequest,
    background_tasks: BackgroundTasks,
    async_scrape: bool = Query(False, alias="async")
):
    """
    Run all applicable scrapers for the given parameters.
    """
    if async_scrape:
        background_tasks.add_task(run_scrape, req, "manual")
        return {"status": "queued", "message": "Scaping task queued in background"}
    else:
        scraped, new = run_scrape(req, "manual")
        return {"scraped": scraped, "new": new}


@app.get("/api/scrape")
async def api_scrape_get(
    background_tasks: BackgroundTasks,
    work_mode: str = Query("both"),
    country: str = Query("all"),
    location: Optional[str] = Query(None),
    async_scrape: bool = Query(True, alias="async")
):
    """
    HTTP GET wrapper to trigger a scrape.
    """
    req = ScrapeRequest(work_mode=work_mode, country=country, location=location)
    if async_scrape:
        background_tasks.add_task(run_scrape, req, "manual")
        return {"status": "queued", "message": "Scraping task queued in background"}
    else:
        scraped, new = run_scrape(req, "manual")
        return {"scraped": scraped, "new": new}
