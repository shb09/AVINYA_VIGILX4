#!/usr/bin/env bash
# Boot the SENTINEL API on SENTINEL_PORT (default 8100).
set -euo pipefail
cd "$(dirname "$0")/../server"
if [ -d .venv ]; then
  PY=".venv/bin/python"
else
  PY="python3"
fi
exec "$PY" -m uvicorn app.main:app --host "${SENTINEL_HOST:-127.0.0.1}" --port "${SENTINEL_PORT:-8100}"
