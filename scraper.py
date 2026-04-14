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
from datetime import datetime

from flights.config import GITHUB_REPO, GITHUB_TOKEN, WEEKS_AHEAD
from flights.github_push import push_flights_json
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

    weeks_data = []
    for i, week in enumerate(weeks, 1):
        logger.info("[%d/%d] %s", i, len(weeks), week["label"])
        deals = search_all_deals(week)
        weeks_data.append({"week": week, "deals": [d.to_dict() for d in deals]})
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
        payload = {
            "generated_at": datetime.utcnow().isoformat(),
            "weeks": weeks_data,
            "progress": {"completed": i, "total": len(weeks)},
        }
        try:
            push_flights_json(payload, GITHUB_TOKEN, GITHUB_REPO)
        except Exception as exc:  # don't abort the run on a transient GitHub error
            logger.warning("  GitHub push failed (continuing): %s", exc)

    try:
        update_history(weeks_data, GITHUB_TOKEN, GITHUB_REPO)
    except Exception as exc:
        logger.warning("history update failed: %s", exc)

    logger.info("Done — %d weeks committed.", len(weeks_data))


if __name__ == "__main__":
    main()
