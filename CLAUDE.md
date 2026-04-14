# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Purpose

Tracks the cheapest round-trip flights from AMS / BRU / EIN / RTM to Malaga (AGP)
for the upcoming 26 weeks. Departure: Wednesday or Thursday. Return: Sunday.
A React page at https://samkooijman99.github.io/malaga_tracker/ shows the results
week by week.

## Stack

- **Python** via **uv** (`uv run python scraper.py`)
- **fast-flights** library (unofficial Google Flights client — free, no API key)
- **GitHub Contents API** to push `flights.json` and trigger a Pages rebuild
- **React + Vite** frontend, deployed via GitHub Actions to GitHub Pages
- **Hetzner server** (same as iliana_scraper: `root@46.225.235.220`, SSH key `~/.ssh/hetzner_id`)

## Commands

```bash
# Install Python deps
uv sync

# Run the scraper once (needs a filled-in .env)
uv run python scraper.py

# Deploy scraper code to Hetzner
uv run python deploy.py

# First-time server provisioning
uv run python setup_server.py

# Frontend: local dev server
cd frontend && npm install && npm run dev

# Frontend: production build
cd frontend && npm run build
```

## Environment variables

Copy `.env.example` to `.env`:

```
GITHUB_TOKEN=   # PAT with repo scope (so the scraper can commit flights.json)
GITHUB_REPO=    # samkooijman99/malaga_tracker
```

No flight API key is required — `fast-flights` queries Google Flights directly.

The `.env` is also copied to the Hetzner server by `setup_server.py`.

## Architecture

### Scraper (`scraper.py`)

Entry point. Calls `flights.search.build_weeks()` to generate the next 26
weeks, then `search_all_deals(week, client)` for each. When done, calls
`flights.github_push.push_flights_json()` which commits
`frontend/public/data/flights.json` to the repo via the GitHub Contents API.
That commit triggers the `pages.yml` GitHub Actions workflow which rebuilds
the frontend and deploys to GitHub Pages.

### Package layout (`flights/`)

- **`config.py`** — env vars, airport list, constants
- **`models.py`** — `Deal` dataclass + `to_dict()`
- **`search.py`** — `build_weeks()`, `search_all_deals()`, Amadeus API calls
- **`github_push.py`** — GitHub Contents API PUT to commit flights.json

### Frontend (`frontend/`)

Vite + React SPA. `App.jsx` fetches `data/flights.json` (served as a static
asset), applies an airport filter, and renders one `<WeekSection>` per week.
Each week shows a table of deals sorted cheapest-first; the cheapest row is
highlighted green.

### Deployment

- **Scraper**: `deploy.yml` rsyncs to `/root/malaga_tracker` on push to main;
  `setup_server.py` installs the weekly cron (`0 6 * * 1`).
- **Frontend**: `pages.yml` builds Vite and deploys to GitHub Pages whenever
  `frontend/**` changes (which includes the data file pushed by the scraper).

## Rate / volume

fast-flights has no documented limit but hammering Google will get you
blocked. Each run does 3 searches per airport per week (2 outbound + 1
shared return) = 4 × 3 × 26 = **312 searches per run**, with a 1.5 s
delay between calls (**60 s** — very generous gap, ~5.2 h wall-clock).
Cron is **daily at 06:00 UTC**; run finishes ~11:15 UTC.
If Google starts returning empty results, bump `RATE_LIMIT_DELAY` in
`flights/config.py` higher still.
