# 📡 Remote Job Radar

A self-hosted, dark-themed job aggregator that scans free public sources for remote and on-site job listings across the US, Canada, and Pakistan. No paid APIs, no Docker required.

---

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, SQLite
- **Frontend**: Single static `frontend/index.html` (vanilla JS + CSS)
- **Scrapers**: We Work Remotely (RSS), Greenhouse API, Lever API, Indeed + LinkedIn via `python-jobspy`

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Start the server

```bash
uvicorn backend.main:app --reload
```

The dashboard will be available at **http://localhost:8000**

---

## Usage

1. Open **http://localhost:8000** in your browser.
2. Set your **keyword** (e.g. `react developer`, `customer support`).
3. Choose **Work Mode**: Remote / On-site / Both.
4. Choose **Country**: US / CA / PK / All.
5. Optionally set a **Location** to narrow results (default for PK is Lahore).
6. Click **SCAN** to pull fresh listings from all sources.
7. Use the **Filter** row to search through already-stored jobs without re-scraping.

---

## Data Sources

| Source | Type | Notes |
|--------|------|-------|
| We Work Remotely | RSS feeds | 6 categories; remote-only; skipped for on-site/PK |
| Greenhouse | REST API | 9 companies (gitlab, automattic, zapier…) |
| Lever | REST API | 4 companies (netflix, plaid, shopify, rippling) |
| Indeed | python-jobspy | US, CA, PK; uses `country_indeed` param |
| LinkedIn | python-jobspy | Same; results vary by region |

**Explicitly excluded**: RemoteOK, FlexJobs, TheMuse premium — all require paid subscriptions.

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/jobs` | List stored jobs (filters: source, country, q, location, remote) |
| `GET` | `/api/sources` | Distinct source names |
| `GET` | `/api/stats` | Total count + by country + by source |
| `POST` | `/api/scrape` | Run scrapers; body: `{query, work_mode, country, location}` |

---

## File Structure

```
remote-job-scraper/
  backend/
    __init__.py
    main.py          # FastAPI app + routes
    database.py      # SQLite helpers (idempotent upsert)
    filters.py       # Keyword/location/work-mode utilities
    scrapers/
      __init__.py
      weworkremotely.py     # WWR RSS scraper
      greenhouse_lever.py   # Greenhouse + Lever API scrapers
      jobspy_source.py      # Indeed + LinkedIn via python-jobspy
  frontend/
    index.html       # Full single-page dashboard
  requirements.txt
  README.md
```

---

## Notes

- **Idempotent**: Scraping twice never creates duplicate URL entries.
- **PK country**: defaults location to `Lahore, Pakistan` when no location is specified.
- **on-site mode**: We Work Remotely is entirely skipped (it's remote-only by nature).
