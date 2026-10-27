"""Formulaires de configuration."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.const import CONF_TOKEN, CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import aiohttp

from custom_components.ha_monitoring.const import (
    CONF_MAIL_PREVIEW,
    CONF_SCAN_INTERVAL,
    DOMAIN,
)

from .conftest import AUTH, INSTANCE, TOKEN, URL


async def _start(hass: HomeAssistant):
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )


async def test_user_flow(hass: HomeAssistant, mock_api) -> None:
    result = await _start(hass)
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_URL: "192.168.1.241:8080/", CONF_TOKEN: f" {TOKEN} "}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Monitoring (192.168.1.241)"
    assert result["data"] == {CONF_URL: URL, CONF_TOKEN: TOKEN}
    assert result["result"].unique_id == INSTANCE
    # Le jeton est bien envoyé en en-tête
    assert mock_api.mock_calls[0][3]["Authorization"] == f"Bearer {TOKEN}"


async def test_user_flow_invalid_token(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(f"{URL}/api/auth", status=401, json={"error": "jeton"})
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_URL: URL, CONF_TOKEN: "faux"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_user_flow_old_monitoring(hass: HomeAssistant, aioclient_mock) -> None:
    """Monitoring pas encore mis à jour : il ignore le jeton et ne renvoie pas d'identifiant."""
    aioclient_mock.get(f"{URL}/api/auth", json={"setup_needed": False, "user": None})
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_URL: URL, CONF_TOKEN: TOKEN}
    )
    assert result["errors"] == {"base": "not_monitoring"}


async def test_user_flow_token_ignored(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(f"{URL}/api/auth", json={**AUTH, "api_token": None})
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_URL: URL, CONF_TOKEN: TOKEN}
    )
    assert result["errors"] == {"base": "invalid_auth"}


async def test_user_flow_cannot_connect(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(f"{URL}/api/auth", exc=aiohttp.ClientConnectionError())
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_URL: URL, CONF_TOKEN: TOKEN}
    )
    assert result["errors"] == {"base": "cannot_connect"}


async def test_already_configured_updates_url(hass: HomeAssistant, entry, aioclient_mock) -> None:
    """Même monitoring à une nouvelle adresse : l'entrée existante est mise à jour."""
    entry.add_to_hass(hass)
    new_url = "http://192.168.1.50:8080"
    aioclient_mock.get(f"{new_url}/api/auth", json=AUTH)
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_URL: new_url, CONF_TOKEN: TOKEN}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert entry.data[CONF_URL] == new_url


async def test_reconfigure_keeps_token(hass: HomeAssistant, entry, mock_api) -> None:
    entry.add_to_hass(hass)
    new_url = "http://192.168.1.50:8080"
    mock_api.get(f"{new_url}/api/auth", json=AUTH)
    mock_api.get(f"{new_url}/api/probes", json=[])
    result = await entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_URL: new_url}
    )
    assert result["reason"] == "reconfigure_successful"
    assert entry.data == {CONF_URL: new_url, CONF_TOKEN: TOKEN}
    assert entry.title == "Monitoring (192.168.1.50)"


async def test_reauth(hass: HomeAssistant, entry, mock_api) -> None:
    entry.add_to_hass(hass)
    result = await entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_TOKEN: "mon_nouveau"}
    )
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_TOKEN] == "mon_nouveau"


async def test_options(hass: HomeAssistant, entry, mock_api) -> None:
    hass.config.language = "fr"
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_SCAN_INTERVAL: 60.0, CONF_MAIL_PREVIEW: False}
    )
    await hass.async_block_till_done()
    assert entry.options == {CONF_SCAN_INTERVAL: 60, CONF_MAIL_PREVIEW: False}
    coordinator = entry.runtime_data.coordinator
    assert coordinator.update_interval.total_seconds() == 60
    state = hass.states.get("sensor.boite_free_mails_non_lus")
    assert "derniers_mails" not in state.attributes
