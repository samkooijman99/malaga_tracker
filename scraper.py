"""
Malaga flight tracker — main entry point.

Searches Amadeus for the cheapest round trips from AMS/BRU/EIN/RTM → AGP
for every Wednesday + Thursday departure over the next 26 weeks,
returning the same Sunday. Results are written to GitHub, triggering
a GitHub Pages rebuild.

Usage:
    uv run python scraper.py
"""

import logging
import time
from datetime import datetime, timezone

from flights.config import GITHUB_REPO, GITHUB_TOKEN, WEEKS_AHEAD
from flights.github_push import fetch_existing_flights, push_flights_json
from flights.history import update_history
from flights.search import build_weeks, search_all_deals

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def main() -> None:
    logger.info("Malaga flight tracker starting")
    weeks = build_weeks(WEEKS_AHEAD)
    logger.info(
        "Searching %d weeks (%s → %s)",
        len(weeks),
        weeks[0]["wednesday"],
        weeks[-1]["sunday"],
    )

    # Seed weeks_by_wed from the existing flights.json so incremental pushes
    # during this run don't wipe older weeks we haven't re-scraped yet.
    # Retry up to 3 times — transient network errors at startup should not cause
    # a fresh run that clobbers the existing complete dataset.
    weeks_by_wed: dict[str, dict] = {}
    existing = None
    for attempt in range(1, 4):
        existing = fetch_existing_flights(GITHUB_TOKEN, GITHUB_REPO)
        if existing is not None:
            break
        logger.warning("fetch_existing_flights attempt %d/3 returned None — retrying in 10s", attempt)
        time.sleep(10)

    if existing is None:
        logger.warning("fetch_existing_flights failed after 3 attempts — starting with empty seed")
    elif not isinstance(existing.get("weeks"), list):
        logger.warning("flights.json 'weeks' is not a list (type=%s) — starting fresh", type(existing.get("weeks")))
    else:
        for entry in existing["weeks"]:
            wed = entry.get("week", {}).get("wednesday")
            if wed:
                weeks_by_wed[wed] = entry
        logger.info("Seeded %d existing weeks from flights.json", len(weeks_by_wed))

    # Drop weeks that are no longer in range (e.g. past weeks)
    current_weds = {w["wednesday"] for w in weeks}
    weeks_by_wed = {k: v for k, v in weeks_by_wed.items() if k in current_weds}
    seed_count = len(weeks_by_wed)

    for i, week in enumerate(weeks, 1):
        logger.info("[%d/%d] %s", i, len(weeks), week["label"])
        deals = search_all_deals(week)
        weeks_by_wed[week["wednesday"]] = {
            "week": week,
            "deals": [d.to_dict() for d in deals],
        }
        if deals:
            cheapest = deals[0]
            logger.info(
                "  %d deals — cheapest €%.0f via %s (%s)",
                len(deals),
                cheapest.price_eur,
                cheapest.outbound_airline,
                cheapest.origin_iata,
            )
        else:
            logger.info("  no deals found")

        # Push incrementally so the site updates as we go.
        # Guard: never push fewer weeks than we seeded — a partial run must not
        # clobber a previously complete dataset.
        ordered = [weeks_by_wed[w["wednesday"]] for w in weeks if w["wednesday"] in weeks_by_wed]
        if len(ordered) < seed_count:
            logger.info("  skipping push (%d/%d weeks ready, need ≥%d)", len(ordered), len(weeks), seed_count)
        else:
            payload = {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "weeks": ordered,
                "progress": {"completed": i, "total": len(weeks)},
            }
            try:
                push_flights_json(payload, GITHUB_TOKEN, GITHUB_REPO)
            except Exception as exc:  # don't abort the run on a transient GitHub error
                logger.warning("  GitHub push failed (continuing): %s", exc)

    final_weeks = [weeks_by_wed[w["wednesday"]] for w in weeks if w["wednesday"] in weeks_by_wed]
    try:
        update_history(final_weeks, GITHUB_TOKEN, GITHUB_REPO)
    except Exception as exc:
        logger.warning("history update failed: %s", exc)

    logger.info("Done — %d weeks committed.", len(final_weeks))


if __name__ == "__main__":
    main()
