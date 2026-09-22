"""Paths, environment and the quarter list."""
from __future__ import annotations

import json
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
STAGING_DIR = DATA_DIR / "staging"
DEFAULT_DB_PATH = DATA_DIR / "fundamentals.duckdb"
SQL_DIR = PROJECT_ROOT / "sql"
MODELS_DIR = SQL_DIR / "models"
QUERIES_DIR = SQL_DIR / "queries"
QUALITY_DIR = PROJECT_ROOT / "tests" / "quality"
QUARTERS_PATH = PROJECT_ROOT / "config" / "quarters.json"

# SEC's fair-access policy requires a User-Agent naming the requester. No
# default on purpose: a public repo must not ship a contact address, and an
# absent value should fail with an explanation rather than a 403.
USER_AGENT_ENV = "SEC_USER_AGENT"

TABLES = ("sub", "num", "tag", "pre")


class ConfigError(RuntimeError):
    """Missing or malformed configuration."""


def user_agent() -> str:
    value = os.environ.get(USER_AGENT_ENV, "").strip()
    if not value:
        raise ConfigError(
            f"{USER_AGENT_ENV} is not set. SEC requires a User-Agent of the form "
            f'"app-name contact@example.com"; without an address it returns 403.\n'
            f"  set {USER_AGENT_ENV}=equity-fundamentals-sql you@example.com"
        )
    return value


def load_quarters(path: Path = QUARTERS_PATH) -> tuple[str, ...]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"quarter list not found: {path}") from exc
    quarters = raw.get("quarters")
    if not isinstance(quarters, list) or not quarters:
        raise ConfigError(f"{path} must contain a non-empty 'quarters' list")
    for q in quarters:
        if not (len(q) == 6 and q[:4].isdigit() and q[4] == "q" and q[5] in "1234"):
            raise ConfigError(f"quarter {q!r} is not of the form YYYYqN")
    return tuple(quarters)


def db_path() -> Path:
    override = os.environ.get("EFS_DB_PATH")
    return Path(override) if override else DEFAULT_DB_PATH
