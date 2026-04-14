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

from .config import AIRPORTS, DESTINATION, MAX_OUTBOUND_OPTIONS, MAX_RETURN_OPTIONS, RATE_LIMIT_DELAY, WEEKS_AHEAD
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


def _search_top_n(from_airport: str, to_airport: str, date_str: str, n: int):
    """Return top-n cheapest one-way results as list of (flight, price_eur)."""
    try:
        result = get_flights(
            flight_data=[
                FlightData(date=date_str, from_airport=from_airport, to_airport=to_airport)
            ],
            trip="one-way",
            seat="economy",
            passengers=Passengers(adults=1, children=0, infants_in_seat=0, infants_on_lap=0),
            max_stops=0,  # direct flights only
            fetch_mode="local",  # headless Chromium; handles Google's consent wall
        )
    except Exception as exc:  # fast-flights raises various exceptions
        logger.warning("Search failed %s→%s on %s: %s", from_airport, to_airport, date_str, exc)
        return []

    if not result or not getattr(result, "flights", None):
        return []

    priced = []
    seen = set()  # dedupe identical flights (same airline+dep+arr)
    for f in result.flights:
        p = _parse_price(getattr(f, "price", None))
        if p is None or p <= 0:
            continue
        key = (getattr(f, "name", ""), getattr(f, "departure", ""), getattr(f, "arrival", ""))
        if key in seen:
            continue
        seen.add(key)
        priced.append((f, p))

    priced.sort(key=lambda x: x[1])
    return priced[:n]


def search_all_deals(week: dict) -> list[Deal]:
    """
    For one week, generate all reasonable outbound × return combinations.

      - Top N returns per destination airport (N = MAX_RETURN_OPTIONS)
      - Top M outbounds per (origin × Wed/Thu) (M = MAX_OUTBOUND_OPTIONS)
      - Cross-product → each outbound gets paired with every return option
        across all 4 airports, giving M × 4×N rows per (origin × day)
    """
    # 1. Top-N returns per airport — flatten into one list of (iata, flight, price)
    all_returns: list[tuple[str, object, float]] = []
    for origin in AIRPORTS:
        logger.info("  returns AGP→%s on %s ...", origin, week["sunday"])
        results = _search_top_n(DESTINATION, origin, week["sunday"], MAX_RETURN_OPTIONS)
        time.sleep(RATE_LIMIT_DELAY)
        if not results:
            logger.info("    none")
            continue
        for rf, rp in results:
            logger.info("    €%.0f via %s", rp, rf.name)
            all_returns.append((origin, rf, rp))

    if not all_returns:
        return []

    # 2. Top-M outbounds per (origin × day), each paired with every return option
    deals: list[Deal] = []
    for origin, origin_info in AIRPORTS.items():
        for outbound_date in (week["wednesday"], week["thursday"]):
            logger.info("  outbounds %s→AGP on %s ...", origin, outbound_date)
            outs = _search_top_n(origin, DESTINATION, outbound_date, MAX_OUTBOUND_OPTIONS)
            time.sleep(RATE_LIMIT_DELAY)
            if not outs:
                logger.info("    none")
                continue

            outbound_day = date.fromisoformat(outbound_date).strftime("%A")
            for out_flight, out_price in outs:
                logger.info("    outbound €%.0f via %s", out_price, out_flight.name)
                for ret_iata, ret_flight, ret_price in all_returns:
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
                            outbound_price_eur=round(out_price, 2),
                            return_date=week["sunday"],
                            return_iata=ret_iata,
                            return_name=AIRPORTS[ret_iata]["name"],
                            return_dep=getattr(ret_flight, "departure", "") or "",
                            return_arr=getattr(ret_flight, "arrival", "") or "",
                            return_airline=getattr(ret_flight, "name", "") or "",
                            return_stops=int(getattr(ret_flight, "stops", 0) or 0),
                            return_price_eur=round(ret_price, 2),
                            price_eur=round(out_price + ret_price, 2),
                        )
                    )

    deals.sort(key=lambda d: d.price_eur)
    # Cap per week — avoid exposing 100+ redundant combos
    return deals[:40]
