"""Configuration guards that fail fast with an explanation."""
from __future__ import annotations

import json

import pytest

from efs import config


def test_user_agent_is_required(monkeypatch):
    monkeypatch.delenv(config.USER_AGENT_ENV, raising=False)
    with pytest.raises(config.ConfigError, match="contact@example.com"):
        config.user_agent()


def test_user_agent_containing_github_is_rejected_before_any_request(monkeypatch):
    # SEC answers HTTP 403 to any User-Agent with this substring; catch it locally.
    monkeypatch.setenv(config.USER_AGENT_ENV, "efs someone.github@example.com")
    with pytest.raises(config.ConfigError, match="github"):
        config.user_agent()


def test_user_agent_passes_through(monkeypatch):
    monkeypatch.setenv(config.USER_AGENT_ENV, "  efs someone@example.com ")
    assert config.user_agent() == "efs someone@example.com"


def test_quarter_list_is_validated(tmp_path):
    good = tmp_path / "q.json"
    good.write_text(json.dumps({"quarters": ["2024q4", "2025q1"]}))
    assert config.load_quarters(good) == ("2024q4", "2025q1")

    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"quarters": ["2025-Q1"]}))
    with pytest.raises(config.ConfigError, match="YYYYqN"):
        config.load_quarters(bad)

    with pytest.raises(config.ConfigError, match="not found"):
        config.load_quarters(tmp_path / "missing.json")
