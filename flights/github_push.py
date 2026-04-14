"""Push flights.json to the GitHub repo via the Contents API."""

import base64
import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

AMS_TZ = ZoneInfo("Europe/Amsterdam")

FLIGHTS_JSON_PATH = "frontend/public/data/flights.json"

logger = logging.getLogger(__name__)


def push_flights_json(data: dict, token: str, repo: str) -> None:
    """
    Commit an updated flights.json to the repo.
    The commit triggers a GitHub Actions rebuild of the React frontend.
    """
    url = f"https://api.github.com/repos/{repo}/contents/{FLIGHTS_JSON_PATH}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    # Fetch existing file SHA so we can update rather than create
    r = requests.get(url, headers=headers, timeout=30)
    sha: str | None = r.json().get("sha") if r.status_code == 200 else None

    content = base64.b64encode(
        json.dumps(data, indent=2, ensure_ascii=False).encode()
    ).decode()

    payload: dict = {
        "message": f"data: update flight prices {datetime.now(AMS_TZ).date()}",
        "content": content,
    }
    if sha:
        payload["sha"] = sha

    r = requests.put(url, headers=headers, json=payload, timeout=30)
    r.raise_for_status()
    commit_url = r.json()["commit"]["html_url"]
    logger.info("Pushed to GitHub: %s", commit_url)
