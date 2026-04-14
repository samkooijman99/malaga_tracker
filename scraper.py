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
from flights.search import build_weeks, get_client, search_all_deals

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def main() -> None:
    logger.info("Malaga flight tracker starting")
    client = get_client()
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
        deals = search_all_deals(week, client)
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

    payload = {
        "generated_at": datetime.utcnow().isoformat(),
        "weeks": weeks_data,
    }

    logger.info("Pushing to GitHub repo %s ...", GITHUB_REPO)
    push_flights_json(payload, GITHUB_TOKEN, GITHUB_REPO)
    logger.info("Done.")


if __name__ == "__main__":
    main()
