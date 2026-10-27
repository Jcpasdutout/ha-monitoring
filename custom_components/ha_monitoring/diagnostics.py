"""Diagnostic téléchargeable depuis la page de l'intégration (jeton masqué)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_TOKEN
from homeassistant.core import HomeAssistant

from .coordinator import MonitoringConfigEntry

TO_REDACT = {CONF_TOKEN, "config", "messages", "derniers_mails"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: MonitoringConfigEntry
) -> dict[str, Any]:
    coordinator = entry.runtime_data.coordinator
    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "options": dict(entry.options),
        "instance_id": coordinator.instance_id,
        "probes": async_redact_data(
            [{k: v for k, v in p.items() if k != "history"} for p in coordinator.data.values()],
            TO_REDACT,
        ),
    }
