from __future__ import annotations

import os
import secrets
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

SERVER_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[2]

_BROWSER_PATH = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")


def default_browser_dir() -> str:
    if _BROWSER_PATH:
        return _BROWSER_PATH
    return str(SERVER_ROOT / ".browsers")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(SERVER_ROOT / ".env"),
        env_prefix="SENTINEL_",
        extra="ignore",
    )

    # server
    host: str = "127.0.0.1"
    port: int = 8100
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:5174",
            "http://127.0.0.1:5174",
        ]
    )

    # browser
    browser_headless: bool = True
    browser_binaries_dir: str = default_browser_dir()
    viewport_width: int = 1360
    viewport_height: int = 840
    nav_timeout_ms: int = 20000
    shot_interval_ms: int = 320
    shot_quality: int = 70

    # persistence
    data_dir: Path = SERVER_ROOT / "data"
    audit_dir: Path = SERVER_ROOT / "data" / "audit"
    db_path: Path = SERVER_ROOT / "data" / "sentinel.db"

    # demo sites
    demo_sites_dir: Path = PROJECT_ROOT / "demo-sites"
    internal_trusted_hosts: list[str] = Field(
        default_factory=lambda: [
            "home.localhost",
            "article.localhost",
            "account.localhost",
        ]
    )
    trusted_external_vendors: list[str] = Field(default_factory=lambda: [])
    demo_hosts: dict[str, str] = Field(
        default_factory=lambda: {
            "home.localhost": "home",
            "article.localhost": "article",
            "malicious.localhost": "malicious",
            "account.localhost": "account",
            "vendor.localhost": "vendor",
        }
    )
    home_host: str = "home.localhost"

    # planner
    planner_provider: str = "auto"  # auto | local | openai
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_api_key: str = ""

    # security
    approval_ttl_seconds: int = 120
    agent_max_steps: int = 8
    max_session_events: int = 1500
    max_audit_lines_per_file: int = 5000

    # canary seed used by security tests and the attack scenario
    canary_seed: str = f"SENTINEL_CANARY_{secrets.token_hex(6).upper()}"

    @property
    def demo_sites(self) -> Path:
        return self.demo_sites_dir

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.audit_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_dirs()
    return settings