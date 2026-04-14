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
    weeks_by_wed: dict[str, dict] = {}
    existing = fetch_existing_flights(GITHUB_TOKEN, GITHUB_REPO)
    if existing and isinstance(existing.get("weeks"), list):
        for entry in existing["weeks"]:
            wed = entry.get("week", {}).get("wednesday")
            if wed:
                weeks_by_wed[wed] = entry
        logger.info("Seeded %d existing weeks from flights.json", len(weeks_by_wed))
    # Drop weeks that are no longer in range (e.g. past weeks)
    current_weds = {w["wednesday"] for w in weeks}
    weeks_by_wed = {k: v for k, v in weeks_by_wed.items() if k in current_weds}

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

        # Push incrementally so the site updates as we go
        ordered = [weeks_by_wed[w["wednesday"]] for w in weeks if w["wednesday"] in weeks_by_wed]
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
