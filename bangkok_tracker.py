"""
Bangkok flight tracker — posts a price update to Telegram.

Searches Google Flights (via fast-flights) for DIRECT round-trip economy
flights AMS <-> BKK, departing 2026-11-08 and returning 2026-11-19 for
1 adult, then posts every option sorted cheapest-first to a Telegram group.

Designed to run twice a day from cron. Unlike the Malaga scraper this does
NOT touch GitHub or the frontend — it only sends a Telegram message.

Usage:
    uv run python bangkok_tracker.py
"""

import json
import logging
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from fast_flights import FlightData, Passengers, get_flights

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# --- Search parameters -------------------------------------------------------
ORIGIN = "AMS"
DESTINATION = "BKK"
DEPART_DATE = "2026-11-05"
RETURN_DATE = "2026-11-19"
ADULTS = 1
SEAT = "economy"

# --- Telegram ----------------------------------------------------------------
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

_PRICE_RE = re.compile(r"\d+(?:\.\d+)?")


def _parse_price(price_str: str | None) -> float | None:
    """Extract a numeric price from strings like '€891', '€1,234'."""
    if not price_str:
        return None
    cleaned = price_str.replace(",", "").replace("\xa0", " ")
    match = _PRICE_RE.search(cleaned)
    if not match:
        return None
    try:
        return float(match.group())
    except ValueError:
        return None


def search_options() -> list[dict]:
    """Return direct round-trip options, cheapest first.

    Each option is the outbound leg carrying Google's round-trip TOTAL price.
    """
    result = get_flights(
        flight_data=[
            FlightData(date=DEPART_DATE, from_airport=ORIGIN, to_airport=DESTINATION),
            FlightData(date=RETURN_DATE, from_airport=DESTINATION, to_airport=ORIGIN),
        ],
        trip="round-trip",
        seat=SEAT,
        passengers=Passengers(adults=ADULTS, children=0, infants_in_seat=0, infants_on_lap=0),
        max_stops=0,  # direct only
        fetch_mode="local",  # headless Chromium; handles Google's consent wall
    )

    if not result or not getattr(result, "flights", None):
        return []

    options: list[dict] = []
    seen: set[tuple] = set()
    for f in result.flights:
        price = _parse_price(getattr(f, "price", None))
        if price is None or price <= 0:
            continue
        name = getattr(f, "name", "") or ""
        departure = getattr(f, "departure", "") or ""
        arrival = getattr(f, "arrival", "") or ""
        key = (name, departure, arrival)
        if key in seen:
            continue
        seen.add(key)
        options.append(
            {
                "airline": name,
                "departure": departure,
                "arrival": arrival,
                "duration": getattr(f, "duration", "") or "",
                "price_eur": round(price, 2),
            }
        )

    options.sort(key=lambda o: o["price_eur"])
    return options


def format_message(options: list[dict]) -> str:
    now = datetime.now(ZoneInfo("Europe/Amsterdam"))
    header = (
        f"✈️ <b>AMS ⇄ BKK · direct · 5–19 Nov 2026</b>\n"
        f"{ADULTS} adult · {SEAT} · round-trip total\n"
        f"🕖 {now.strftime('%H:%M %Z · %a %-d %b')}"
    )

    if not options:
        return header + "\n\n⚠️ No direct flights found for these dates right now."

    lines = [header, ""]
    for i, o in enumerate(options, 1):
        dur = f" · {o['duration']}" if o["duration"] else ""
        lines.append(f"<b>{i}. €{o['price_eur']:.0f}</b> · {o['airline']}{dur}")
        lines.append(f"   {o['departure']} → {o['arrival']}")
    return "\n".join(lines)


def send_telegram(text: str) -> None:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = urllib.parse.urlencode(
        {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": "true",
        }
    ).encode()
    req = urllib.request.Request(url, data=data)
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.load(resp)
    if not payload.get("ok"):
        raise RuntimeError(f"Telegram sendMessage failed: {payload}")


def main() -> None:
    logger.info("Bangkok tracker starting — %s ⇄ %s %s/%s", ORIGIN, DESTINATION, DEPART_DATE, RETURN_DATE)
    options = search_options()
    logger.info("Found %d direct option(s)", len(options))
    for o in options:
        logger.info("  €%.0f via %s", o["price_eur"], o["airline"])
    message = format_message(options)
    send_telegram(message)
    logger.info("Posted to Telegram chat %s", TELEGRAM_CHAT_ID)


if __name__ == "__main__":
    main()
