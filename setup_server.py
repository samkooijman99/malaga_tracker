"""
Provision the Hetzner server from scratch for malaga_tracker.

- Installs uv
- Creates /root/malaga_tracker
- Copies local .env to server
- Runs uv sync
- Installs the weekly cron job (every Monday 06:00 UTC)

Usage:
    uv run python setup_server.py
"""

import subprocess
import sys
from pathlib import Path

SERVER = "root@46.225.235.220"
SSH_KEY = "~/.ssh/hetzner_id"
REMOTE_DIR = "/root/malaga_tracker"

# Cron: every 8 hours (00:00, 08:00, 16:00 Amsterdam). Each run takes
# ~5.2 h with a 60 s inter-query delay, so ~3 h idle between runs.
# The crontab on the server has `CRON_TZ=Europe/Amsterdam` at the top.
CRON_LINE = (
    "0 */8 * * * /bin/bash -c "
    "'source /root/.local/bin/env && "
    f"cd {REMOTE_DIR} && "
    "uv run python scraper.py >> "
    f"{REMOTE_DIR}/scraper.log 2>&1'"
)


def ssh(command: str) -> bool:
    result = subprocess.run(
        ["ssh", "-i", SSH_KEY, SERVER, command],
        text=True,
    )
    return result.returncode == 0


def step(label: str, command: str) -> None:
    print(f"→ {label}...")
    if not ssh(command):
        print("  FAILED")
        sys.exit(1)
    print("  done")


# 1. Install uv (idempotent)
step(
    "Install uv",
    "command -v uv >/dev/null 2>&1 || curl -LsSf https://astral.sh/uv/install.sh | sh",
)

# 2. Create project directory
step("Create project directory", f"mkdir -p {REMOTE_DIR}")

# 3. Copy .env
env_file = Path(".env")
if not env_file.exists():
    print("ERROR: .env not found locally — create it from .env.example first")
    sys.exit(1)

print("→ Copying .env...")
result = subprocess.run(
    ["scp", "-i", SSH_KEY, ".env", f"{SERVER}:{REMOTE_DIR}/.env"],
    text=True,
)
if result.returncode != 0:
    print("  FAILED")
    sys.exit(1)
print("  done")

# 4. Sync project files
print("→ Syncing project files...")
result = subprocess.run(
    [
        "rsync", "-az",
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
    text=True,
)
if result.returncode != 0:
    print("  FAILED")
    sys.exit(1)
print("  done")

# 5. Install Python deps
step("uv sync", f"cd {REMOTE_DIR} && source /root/.local/bin/env && uv sync")

# 5b. Install Playwright Chromium + OS deps (handles Google consent wall)
step(
    "playwright install chromium",
    f"cd {REMOTE_DIR} && source /root/.local/bin/env && uv run playwright install --with-deps chromium",
)

# 6. Install cron job (idempotent)
step(
    "Install cron job",
    f"(crontab -l 2>/dev/null | grep -qF 'malaga_tracker') || "
    f"(crontab -l 2>/dev/null; echo '{CRON_LINE}') | crontab -",
)

print("\nServer is ready.")
print("The scraper will run daily at 06:00 UTC.")
print("To trigger a manual run:")
print(f"  ssh -i {SSH_KEY} {SERVER} 'cd {REMOTE_DIR} && source /root/.local/bin/env && uv run python scraper.py'")
