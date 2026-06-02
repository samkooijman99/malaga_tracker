#!/bin/bash
# Wrapper invoked by cron to run the Bangkok flight tracker.
# Kept as a script so the crontab line stays free of nested quoting.
set -euo pipefail
source /root/.local/bin/env
cd /root/malaga_tracker
uv run python bangkok_tracker.py
