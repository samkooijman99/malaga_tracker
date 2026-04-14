"""
Append today's per-week price snapshot to history.json on GitHub.

Structure:
{
  "updated_at": "2026-04-15",
  "weeks": {
    "2026-04-22": {
      "wednesday": "2026-04-22",
      "label": "Apr 22 / 23 → 26 Apr 2026",
      "snapshots": [
        {"date": "2026-04-14", "cheapest": 244, "airports": {"AMS": 244, ...}},
        ...
      ]
    }
  }
}
"""

import base64
import json
import logging
from datetime import date

import requests

HISTORY_PATH = "frontend/public/data/history.json"

logger = logging.getLogger(__name__)


def update_history(weeks_data: list, token: str, repo: str) -> None:
    url = f"https://api.github.com/repos/{repo}/contents/{HISTORY_PATH}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    # Load existing file (if any)
    sha: str | None = None
    existing: dict = {"weeks": {}}
    r = requests.get(url, headers=headers, timeout=30)
    if r.status_code == 200:
        try:
            sha = r.json().get("sha")
            decoded = base64.b64decode(r.json()["content"]).decode()
            parsed = json.loads(decoded)
            if isinstance(parsed.get("weeks"), dict):
                existing = parsed
        except Exception as exc:  # schema mismatch or corrupt — start fresh
            logger.warning("history.json unreadable (starting fresh): %s", exc)

    weeks_dict: dict = existing.get("weeks", {})
    today = date.today().isoformat()

    for w in weeks_data:
        week = w["week"]
        deals = w["deals"]
        if not deals:
            continue

        wed = week["wednesday"]
        cheapest = deals[0]["price_eur"]  # deals are sorted cheapest-first

        per_airport: dict[str, float] = {}
        for deal in deals:
            ap = deal["origin_iata"]
            price = deal["price_eur"]
            if ap not in per_airport or price < per_airport[ap]:
                per_airport[ap] = price

        entry = weeks_dict.get(
            wed, {"wednesday": wed, "label": week["label"], "snapshots": []}
        )
        # Replace today's snapshot if the scraper ran twice in one day
        snapshots = [s for s in entry["snapshots"] if s["date"] != today]
        snapshots.append({"date": today, "cheapest": cheapest, "airports": per_airport})
        snapshots.sort(key=lambda s: s["date"])
        entry["snapshots"] = snapshots
        weeks_dict[wed] = entry

    payload = {"updated_at": today, "weeks": weeks_dict}

    body = {
        "message": f"history: snapshot {today}",
        "content": base64.b64encode(
            json.dumps(payload, indent=2, ensure_ascii=False).encode()
        ).decode(),
    }
    if sha:
        body["sha"] = sha

    r = requests.put(url, headers=headers, json=body, timeout=30)
    r.raise_for_status()
    logger.info(
        "history.json updated — %d weeks, snapshot date=%s", len(weeks_dict), today
    )
