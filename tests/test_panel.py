"""Panneau /monitoring pour l'add-on."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homeassistant.components.frontend import DATA_PANELS
from homeassistant.const import CONF_TOKEN, CONF_URL
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ha_monitoring.const import CONF_PANEL, DOMAIN

from .conftest import AUTH, INSTANCE, PROBES

ADDON_URL = "http://abcd1234-monitoring:8080"
SLUG = "abcd1234_monitoring"
INGRESS = "/api/hassio_ingress/jeton/"


@pytest.fixture
def addon_api(aioclient_mock):
    aioclient_mock.get(f"{ADDON_URL}/api/auth", json=AUTH)
    aioclient_mock.get(f"{ADDON_URL}/api/probes", json=PROBES)
    return aioclient_mock


@pytest.fixture
def supervisor(hass: HomeAssistant):
    """Supervisor simulé : l'add-on a son Ingress et son entrée dans la barre latérale."""
    info = SimpleNamespace(name="Monitoring", ingress_url=INGRESS, ingress_panel=True)

    async def set_options(slug, options):
        info.ingress_panel = options.ingress_panel

    client = MagicMock()
    client.addons.addon_info = AsyncMock(return_value=info)
    client.addons.set_addon_options = AsyncMock(side_effect=set_options)
    hass.http = MagicMock(async_register_static_paths=AsyncMock())
    with (
        patch("custom_components.ha_monitoring.panel.is_hassio", return_value=True),
        patch("custom_components.ha_monitoring.panel._supervisor_client", return_value=client),
    ):
        yield info


def _addon_entry(**options) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id=INSTANCE,
        title="Monitoring (add-on)",
        data={CONF_URL: ADDON_URL, CONF_TOKEN: "mon_addon"},
        options=options,
    )


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_panel_created(hass: HomeAssistant, addon_api, supervisor) -> None:
    entry = _addon_entry()
    await _setup(hass, entry)
    panel = hass.data[DATA_PANELS]["monitoring"]
    assert panel.sidebar_title == "Monitoring"
    assert panel.config["_panel_custom"]["module_url"].startswith("/ha_monitoring_static/panel.js")
    assert panel.config["ingress_url"] == INGRESS
    assert panel.config["slug"] == SLUG
    # L'entrée d'origine de l'add-on est masquée : pas de doublon dans la barre latérale.
    assert supervisor.ingress_panel is False

    await hass.config_entries.async_unload(entry.entry_id)
    assert "monitoring" not in hass.data[DATA_PANELS]

    await hass.config_entries.async_remove(entry.entry_id)
    assert supervisor.ingress_panel is True


async def test_panel_disabled(hass: HomeAssistant, addon_api, supervisor) -> None:
    supervisor.ingress_panel = False
    await _setup(hass, _addon_entry(**{CONF_PANEL: False}))
    assert "monitoring" not in hass.data.get(DATA_PANELS, {})
    assert supervisor.ingress_panel is True


async def test_no_panel_outside_addon(hass: HomeAssistant, entry, mock_api, supervisor) -> None:
    """Monitoring installé ailleurs (conteneur Proxmox) : rien à afficher par l'Ingress."""
    await _setup(hass, entry)
    assert "monitoring" not in hass.data.get(DATA_PANELS, {})
