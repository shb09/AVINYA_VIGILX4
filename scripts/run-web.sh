#!/usr/bin/env bash
# Boot the SENTINEL web UI (Vite dev server) and proxy API/WS to the backend.
# Set SENTINEL_API to override the backend origin (default http://127.0.0.1:8100).
set -euo pipefail
cd "$(dirname "$0")/../web"
exec npm run dev
