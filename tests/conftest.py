"""Fixtures communes."""

from __future__ import annotations

import copy
from typing import Any

import pytest

from homeassistant.const import CONF_TOKEN, CONF_URL
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ha_monitoring.const import DOMAIN

URL = "http://192.168.1.241:8080"
TOKEN = "mon_secret"
INSTANCE = "abc123"

AUTH = {
    "setup_needed": False,
    "user": None,
    "api_token": "Home Assistant",
    "instance_id": INSTANCE,
    "version": "2.1.0",
}

PROBES: list[dict[str, Any]] = [
    {
        "id": 1, "name": "Boîte Free", "type": "imap", "group": "Mails", "enabled": True,
        "config": {"host": "imap.free.fr"},
        "last": {"ts": 1793095958.7, "status": "ok", "value": 3, "duration_ms": 420,
                 "summary": "3 non lus",
                 "details": {"folders": {"INBOX": 3}, "messages": [
                     {"uid": "9", "folder": "INBOX", "from": "Alice", "subject": "Coucou",
                      "date": "2026-10-27T09:00:00+01:00"}]}},
        "history": [],
    },
    {
        "id": 2, "name": "Site", "type": "http", "group": "", "enabled": True,
        "config": {"url": "http://x", "json_path": "data.temp"},
        "last": {"ts": 1793095958.7, "status": "warning", "value": 2500.0, "duration_ms": 2500,
                 "summary": "HTTP 200 en 2500 ms (lent)",
                 "details": {"http_status": 200, "latency_ms": 2500, "json_value": 21.5}},
        "history": [],
    },
    {
        "id": 3, "name": "NAS", "type": "snmp", "group": "LAN", "enabled": True, "config": {},
        "last": {"ts": 1793095958.7, "status": "error", "value": 97.0, "duration_ms": 80,
                 "summary": "CPU 12 % · Disque / 97 %",
                 "details": {"gauges": [
                     {"key": "cpu", "label": "CPU", "pct": 12.0, "text": "4 cœurs", "level": "ok"},
                     {"key": "disk", "label": "Disque /", "pct": 97.0, "text": "1 Go libres", "level": "error"}],
                     "sysname": "nas", "uptime_days": 12}},
        "history": [],
    },
    {
        "id": 4, "name": "Routeur", "type": "ping", "group": "LAN", "enabled": False, "config": {},
        "last": None, "history": [],
    },
]


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Charge custom_components/ dans les tests."""
    return


@pytest.fixture
def probes() -> list[dict[str, Any]]:
    return copy.deepcopy(PROBES)


@pytest.fixture
def mock_api(aioclient_mock, probes):
    """Monitoring simulé (la réponse est figée à l'enregistrement)."""
    aioclient_mock.get(f"{URL}/api/auth", json=AUTH)
    aioclient_mock.get(f"{URL}/api/probes", json=probes)
    aioclient_mock.post(f"{URL}/api/refresh", json={"ok": True})
    aioclient_mock.post(f"{URL}/api/probes/1/run", json={"status": "ok"})
    return aioclient_mock


@pytest.fixture
def entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id=INSTANCE,
        title="Monitoring (192.168.1.241)",
        data={CONF_URL: URL, CONF_TOKEN: TOKEN},
    )
