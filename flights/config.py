import os
from dotenv import load_dotenv

load_dotenv()

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
RATE_LIMIT_DELAY = 60  # seconds between Google Flights scrapes — generous gap to avoid blocking (≈5.2 h per run for 312 searches)
