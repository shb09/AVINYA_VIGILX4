"""Pytest configuration.

Runs the integration suite against a dedicated port so the embedded Chromium
navigation targets (built from Settings.port) match the server the tests bind.
"""

import os
import sys
from pathlib import Path

SERVER_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVER_ROOT))

os.environ.setdefault("SENTINEL_PORT", "8101")

# Prime the settings cache so app-level get_settings() matches the env above.
from app.config import get_settings  # noqa: E402

get_settings()