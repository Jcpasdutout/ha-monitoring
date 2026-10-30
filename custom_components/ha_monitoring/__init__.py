"""Intégration Home Assistant du monitoring maison (sondes mail, HTTP, ping, SNMP)."""

from __future__ import annotations

from homeassistant.const import CONF_TOKEN, CONF_URL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import MonitoringApi, MonitoringAuthError, MonitoringError
from .const import DOMAIN
from .coordinator import MonitoringConfigEntry, MonitoringCoordinator, MonitoringData
from .entity import hub_device_info
from .panel import async_remove_panel, async_restore_addon_panel, async_setup_panel

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.BUTTON, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: MonitoringConfigEntry) -> bool:
    """Connexion au monitoring et création des entités."""
    api = MonitoringApi(
        async_get_clientsession(hass), entry.data[CONF_URL], entry.data[CONF_TOKEN]
    )
    try:
        info = await api.async_get_info()
    except MonitoringAuthError as err:
        raise ConfigEntryAuthFailed(
            translation_domain=DOMAIN, translation_key="invalid_auth"
        ) from err
    except MonitoringError as err:
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN,
            translation_key="cannot_connect",
            translation_placeholders={"error": str(err)},
        ) from err

    coordinator = MonitoringCoordinator(hass, entry, api, info["instance_id"])
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = MonitoringData(api, coordinator, info["instance_id"])
    # L'appareil « Monitoring » existe avant ceux des sondes, qui y sont rattachés.
    dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id, **hub_device_info(coordinator)
    )
    coordinator.remove_stale_devices()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await async_setup_panel(hass, entry)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: MonitoringConfigEntry) -> bool:
    """Retire l'intégration."""
    async_remove_panel(hass, entry)
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: MonitoringConfigEntry) -> None:
    """Intégration supprimée : l'add-on retrouve son propre panneau."""
    await async_restore_addon_panel(hass, entry)
