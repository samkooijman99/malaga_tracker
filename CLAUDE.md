# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Purpose

Tracks the cheapest round-trip flights from AMS / BRU / EIN / RTM to Malaga (AGP)
for the upcoming 26 weeks. Departure: Wednesday or Thursday. Return: Sunday.
A React page at https://samkooijman99.github.io/malaga_tracker/ shows the results
week by week.

## Stack

- **Python** via **uv** (`uv run python scraper.py`)
- **Amadeus API** for real flight prices (free tier: 2 000 calls/month)
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
AMADEUS_CLIENT_ID=      # from https://developers.amadeus.com
AMADEUS_CLIENT_SECRET=  # same
GITHUB_TOKEN=           # PAT with repo scope
GITHUB_REPO=            # samkooijman99/malaga_tracker
```

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

## API limits

Amadeus free tier: **2 000 calls / month**.
Each weekly scraper run makes ~208 calls (4 airports × 2 days × 26 weeks).
Running once per week = ~832 calls/month — comfortably within the free tier.
Running daily would exceed the limit; increase to a paid plan if needed.
