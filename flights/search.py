"""
Flight search via the fast-flights library (Google Flights, unofficial).

For each week in the next N weeks, queries:
  - one-way outbound on Wed and Thu from each origin airport to AGP
  - one-way return on Sun from AGP to each origin airport (shared across
    Wed/Thu outbound to save calls)

Sums the two one-way prices to form a "two-one-way" round trip deal.
"""

import logging
import re
import time
from datetime import date, timedelta

from fast_flights import FlightData, Passengers, get_flights

from .config import AIRPORTS, DESTINATION, RATE_LIMIT_DELAY, WEEKS_AHEAD
from .models import Deal

logger = logging.getLogger(__name__)

_PRICE_RE = re.compile(r"\d+(?:\.\d+)?")


def _parse_price(price_str: str | None) -> float | None:
    """Extract a numeric price from strings like '€123', '€1,234', '$99.50'."""
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


def build_weeks(weeks_ahead: int = WEEKS_AHEAD) -> list[dict]:
    """Return a list of week dicts covering the next N weeks."""
    today = date.today()
    days_to_wed = (2 - today.weekday()) % 7
    if days_to_wed == 0:
        days_to_wed = 7
    first_wed = today + timedelta(days=days_to_wed)

    weeks = []
    for i in range(weeks_ahead):
        wed = first_wed + timedelta(weeks=i)
        thu = wed + timedelta(days=1)
        sun = wed + timedelta(days=4)
        weeks.append(
            {
                "week_number": i + 1,
                "wednesday": wed.isoformat(),
                "thursday": thu.isoformat(),
                "sunday": sun.isoformat(),
                "label": f"{wed.strftime('%b %-d')} / {thu.strftime('%-d')} → {sun.strftime('%-d %b %Y')}",
            }
        )
    return weeks


def _search_one_way(from_airport: str, to_airport: str, date_str: str):
    """Return (flight, price_eur) for the cheapest one-way, or None."""
    try:
        result = get_flights(
            flight_data=[
                FlightData(date=date_str, from_airport=from_airport, to_airport=to_airport)
            ],
            trip="one-way",
            seat="economy",
            passengers=Passengers(adults=1, children=0, infants_in_seat=0, infants_on_lap=0),
            fetch_mode="fallback",
        )
    except Exception as exc:  # fast-flights raises various exceptions
        logger.warning("Search failed %s→%s on %s: %s", from_airport, to_airport, date_str, exc)
        return None

    if not result or not getattr(result, "flights", None):
        return None

    priced = []
    for f in result.flights:
        p = _parse_price(getattr(f, "price", None))
        if p is not None and p > 0:
            priced.append((f, p))
    if not priced:
        return None
    priced.sort(key=lambda x: x[1])
    return priced[0]


def search_all_deals(week: dict) -> list[Deal]:
    """Search all airport × outbound-day combos for one week."""
    deals: list[Deal] = []

    for origin, origin_info in AIRPORTS.items():
        ret = _search_one_way(DESTINATION, origin, week["sunday"])
        time.sleep(RATE_LIMIT_DELAY)
        if not ret:
            logger.info("  no return found for %s on %s", origin, week["sunday"])
            continue
        ret_flight, ret_price = ret

        for outbound_date in (week["wednesday"], week["thursday"]):
            out = _search_one_way(origin, DESTINATION, outbound_date)
            time.sleep(RATE_LIMIT_DELAY)
            if not out:
                continue
            out_flight, out_price = out
            outbound_day = date.fromisoformat(outbound_date).strftime("%A")

            deals.append(
                Deal(
                    origin_iata=origin,
                    origin_name=origin_info["name"],
                    country=origin_info["country"],
                    outbound_date=outbound_date,
                    outbound_day=outbound_day,
                    outbound_dep=getattr(out_flight, "departure", "") or "",
                    outbound_arr=getattr(out_flight, "arrival", "") or "",
                    outbound_airline=getattr(out_flight, "name", "") or "",
                    outbound_stops=int(getattr(out_flight, "stops", 0) or 0),
                    return_date=week["sunday"],
                    return_dep=getattr(ret_flight, "departure", "") or "",
                    return_arr=getattr(ret_flight, "arrival", "") or "",
                    return_airline=getattr(ret_flight, "name", "") or "",
                    return_stops=int(getattr(ret_flight, "stops", 0) or 0),
                    price_eur=round(out_price + ret_price, 2),
                )
            )

    deals.sort(key=lambda d: d.price_eur)
    return deals
