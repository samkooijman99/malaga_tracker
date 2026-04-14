"""
Deploy local code changes to the Hetzner server.

- Rsyncs project files (skips .venv, node_modules, logs)
- Runs uv sync on the server

Usage:
    uv run python deploy.py
"""

import subprocess
import sys
from pathlib import Path

SERVER = "root@46.225.235.220"
SSH_KEY = "~/.ssh/hetzner_id"
REMOTE_DIR = "/root/malaga_tracker"


def run(description: str, cmd: list[str]) -> None:
    print(f"→ {description}...")
    result = subprocess.run(cmd, text=True)
    if result.returncode != 0:
        print("  FAILED")
        sys.exit(1)
    print("  done")


run(
    "Sync files",
    [
        "rsync", "-az", "--delete",
        "--exclude=.venv",
        "--exclude=.git",
        "--exclude=.github",
        "--exclude=scraper.log",
        "--exclude=__pycache__",
        "--exclude=frontend/node_modules",
        "--exclude=frontend/dist",
        "-e", f"ssh -i {SSH_KEY}",
        "./",
        f"{SERVER}:{REMOTE_DIR}/",
    ],
)

if Path(".env").exists():
    run(
        "Push .env",
        ["scp", "-i", SSH_KEY, ".env", f"{SERVER}:{REMOTE_DIR}/.env"],
    )
else:
    print("⚠  No local .env — skipping (server may already have one).")

run(
    "uv sync",
    [
        "ssh", "-i", SSH_KEY, SERVER,
        f"cd {REMOTE_DIR} && source /root/.local/bin/env && uv sync",
    ],
)

print("\nDeployed.")
