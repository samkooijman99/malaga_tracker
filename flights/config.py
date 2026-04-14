import os
from dotenv import load_dotenv

load_dotenv()

AMADEUS_CLIENT_ID = os.environ["AMADEUS_CLIENT_ID"]
AMADEUS_CLIENT_SECRET = os.environ["AMADEUS_CLIENT_SECRET"]
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GITHUB_REPO = os.environ.get("GITHUB_REPO", "samkooijman99/malaga_tracker")

# Origin airports
AIRPORTS: dict[str, dict] = {
    "AMS": {"name": "Amsterdam Schiphol", "country": "NL"},
    "BRU": {"name": "Brussels Zaventem", "country": "BE"},
    "EIN": {"name": "Eindhoven", "country": "NL"},
    "RTM": {"name": "Rotterdam The Hague", "country": "NL"},
}

DESTINATION = "AGP"  # Malaga

# weekday() values: Mon=0 … Sun=6
DEPARTURE_WEEKDAYS = (2, 3)  # Wednesday, Thursday
RETURN_WEEKDAY = 6            # Sunday

WEEKS_AHEAD = 26
MAX_OFFERS_PER_QUERY = 3       # cheapest N per route/date combo
RATE_LIMIT_DELAY = 0.25        # seconds between Amadeus calls
