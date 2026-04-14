"""
Flight search via the Amadeus API.

Generates a list of weeks (Wed/Thu departure + Sun return) for the next
N weeks, then queries Amadeus for round-trip flight offers from each
NL/BE airport to AGP and returns the cheapest deal per combo.
"""

import logging
import time
from datetime import date, timedelta

from amadeus import Client, ResponseError

from .config import (
    AIRPORTS,
    DEPARTURE_WEEKDAYS,
    DESTINATION,
    AMADEUS_CLIENT_ID,
    AMADEUS_CLIENT_SECRET,
    MAX_OFFERS_PER_QUERY,
    RATE_LIMIT_DELAY,
    WEEKS_AHEAD,
)
from .models import Deal

logger = logging.getLogger(__name__)

# IATA carrier code → readable name
AIRLINE_NAMES: dict[str, str] = {
    "FR": "Ryanair",
    "HV": "Transavia",
    "VY": "Vueling",
    "U2": "easyJet",
    "SN": "Brussels Airlines",
    "KL": "KLM",
    "IB": "Iberia",
    "W6": "Wizz Air",
    "PC": "Pegasus",
    "TO": "Transavia France",
    "A5": "HOP!",
    "EW": "Eurowings",
}


def get_client() -> Client:
    return Client(
        client_id=AMADEUS_CLIENT_ID,
        client_secret=AMADEUS_CLIENT_SECRET,
    )


def build_weeks(weeks_ahead: int = WEEKS_AHEAD) -> list[dict]:
    """
    Return a list of week dicts covering the next `weeks_ahead` weeks.

    Each dict has:
      week_number, wednesday, thursday, sunday (ISO date strings), label
    """
    today = date.today()
    # Find next Wednesday that isn't today
    days_to_wed = (2 - today.weekday()) % 7
    if days_to_wed == 0:
        days_to_wed = 7
    first_wed = today + timedelta(days=days_to_wed)

    weeks = []
    for i in range(weeks_ahead):
        wed = first_wed + timedelta(weeks=i)
        thu = wed + timedelta(days=1)
        sun = wed + timedelta(days=4)  # Wed + 4 days = Sun
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


def _parse_itinerary(itin: dict) -> tuple[str, str, str, int]:
    """Return (dep_time HH:MM, arr_time HH:MM, airline name, num_stops)."""
    segs = itin["segments"]
    dep_time = segs[0]["departure"]["at"][11:16]
    arr_time = segs[-1]["arrival"]["at"][11:16]
    carrier = segs[0]["carrierCode"]
    airline = AIRLINE_NAMES.get(carrier, carrier)
    stops = len(segs) - 1
    return dep_time, arr_time, airline, stops


def _search_round_trip(
    client: Client, origin: str, outbound_date: str, return_date: str
) -> Deal | None:
    """Query Amadeus for the cheapest round trip on a specific date pair."""
    origin_info = AIRPORTS[origin]
    outbound_day = date.fromisoformat(outbound_date).strftime("%A")

    try:
        response = client.shopping.flight_offers_search.get(
            originLocationCode=origin,
            destinationLocationCode=DESTINATION,
            departureDate=outbound_date,
            returnDate=return_date,
            adults=1,
            currencyCode="EUR",
            max=MAX_OFFERS_PER_QUERY,
        )
    except ResponseError as exc:
        logger.warning("Amadeus error %s→%s on %s: %s", origin, DESTINATION, outbound_date, exc)
        return None

    offers = response.data
    if not offers:
        return None

    offer = offers[0]  # already sorted cheapest-first by Amadeus
    price = float(offer["price"]["grandTotal"])
    out_dep, out_arr, out_airline, out_stops = _parse_itinerary(offer["itineraries"][0])
    ret_dep, ret_arr, ret_airline, ret_stops = _parse_itinerary(offer["itineraries"][1])

    return Deal(
        origin_iata=origin,
        origin_name=origin_info["name"],
        country=origin_info["country"],
        outbound_date=outbound_date,
        outbound_day=outbound_day,
        outbound_dep=out_dep,
        outbound_arr=out_arr,
        outbound_airline=out_airline,
        outbound_stops=out_stops,
        return_date=return_date,
        return_dep=ret_dep,
        return_arr=ret_arr,
        return_airline=ret_airline,
        return_stops=ret_stops,
        price_eur=price,
    )


def search_all_deals(week: dict, client: Client) -> list[Deal]:
    """
    Search all airport × departure-day combos for a single week.
    Returns deals sorted cheapest-first.
    """
    deals: list[Deal] = []
    outbound_dates = [week["wednesday"], week["thursday"]]

    for origin in AIRPORTS:
        for outbound_date in outbound_dates:
            deal = _search_round_trip(client, origin, outbound_date, week["sunday"])
            if deal:
                deals.append(deal)
            time.sleep(RATE_LIMIT_DELAY)

    deals.sort(key=lambda d: d.price_eur)
    return deals
