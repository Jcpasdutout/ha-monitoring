"""Récupération périodique de l'état des sondes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import MonitoringApi, MonitoringAuthError, MonitoringError
from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass
class MonitoringData:
    """Ce que l'intégration garde pour une entrée de configuration."""

    api: MonitoringApi
    coordinator: MonitoringCoordinator
    instance_id: str


type MonitoringConfigEntry = ConfigEntry[MonitoringData]


def probe_device_id(instance_id: str, probe_id: int) -> tuple[str, str]:
    """Identifiant de l'appareil Home Assistant d'une sonde."""
    return (DOMAIN, f"{instance_id}_{probe_id}")


class MonitoringCoordinator(DataUpdateCoordinator[dict[int, dict[str, Any]]]):
    """Interroge /api/probes et tient les appareils à jour."""

    config_entry: MonitoringConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: MonitoringConfigEntry,
        api: MonitoringApi,
        instance_id: str,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(
                seconds=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            ),
        )
        self.api = api
        self.instance_id = instance_id

    async def _async_update_data(self) -> dict[int, dict[str, Any]]:
        try:
            probes = await self.api.async_get_probes()
        except MonitoringAuthError as err:
            raise ConfigEntryAuthFailed(
                translation_domain=DOMAIN, translation_key="invalid_auth"
            ) from err
        except MonitoringError as err:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="cannot_connect",
                translation_placeholders={"error": str(err)},
            ) from err
        data = {p["id"]: p for p in probes if isinstance(p, dict) and "id" in p}
        if self.data is not None:
            self._sync_devices(self.data, data)
        return data

    def _sync_devices(
        self, old: dict[int, dict[str, Any]], new: dict[int, dict[str, Any]]
    ) -> None:
        """Retire les sondes supprimées et suit les changements de nom."""
        registry = dr.async_get(self.hass)
        for pid, probe in old.items():
            device = registry.async_get_device(
                identifiers={probe_device_id(self.instance_id, pid)}
            )
            if device is None:
                continue
            if pid not in new:
                _LOGGER.debug("Sonde %s supprimée du monitoring", probe.get("name"))
                registry.async_update_device(
                    device.id, remove_config_entry_id=self.config_entry.entry_id
                )
            elif new[pid].get("name") != device.name:
                registry.async_update_device(device.id, name=new[pid].get("name"))

    def remove_stale_devices(self) -> None:
        """Au démarrage : retire les appareils des sondes supprimées pendant l'arrêt."""
        registry = dr.async_get(self.hass)
        current = {probe_device_id(self.instance_id, pid) for pid in self.data}
        current.add((DOMAIN, self.instance_id))
        for device in dr.async_entries_for_config_entry(
            registry, self.config_entry.entry_id
        ):
            if not device.identifiers & current:
                registry.async_update_device(
                    device.id, remove_config_entry_id=self.config_entry.entry_id
                )
