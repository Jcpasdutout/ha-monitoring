"""Boutons pour relancer une sonde, ou toutes les sondes."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import MonitoringError
from .const import DOMAIN
from .coordinator import MonitoringConfigEntry, MonitoringCoordinator
from .entity import MonitoringHubEntity, MonitoringProbeEntity, async_add_dynamic_entities

PARALLEL_UPDATES = 1
REFRESH_ALL_DELAY = 5  # secondes laissées aux sondes avant de relire les résultats


class RunProbeButton(MonitoringProbeEntity, ButtonEntity):
    """Vérifie la sonde tout de suite."""

    _attr_translation_key = "run"

    def __init__(self, coordinator: MonitoringCoordinator, probe_id: int) -> None:
        super().__init__(coordinator, probe_id, "run")

    async def async_press(self) -> None:
        try:
            await self.coordinator.api.async_run_probe(self.probe_id)
        except MonitoringError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="action_failed",
                translation_placeholders={"error": str(err)},
            ) from err
        await self.coordinator.async_request_refresh()


class RefreshAllButton(MonitoringHubEntity, ButtonEntity):
    """Relance toutes les sondes."""

    def __init__(self, coordinator: MonitoringCoordinator) -> None:
        super().__init__(coordinator, "refresh_all")

    async def async_press(self) -> None:
        try:
            await self.coordinator.api.async_refresh_all()
        except MonitoringError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="action_failed",
                translation_placeholders={"error": str(err)},
            ) from err
        await asyncio.sleep(REFRESH_ALL_DELAY)
        await self.coordinator.async_request_refresh()


def _build(coordinator: MonitoringCoordinator) -> Iterable[ButtonEntity]:
    yield RefreshAllButton(coordinator)
    for pid in coordinator.data:
        yield RunProbeButton(coordinator, pid)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MonitoringConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Crée les boutons."""
    async_add_dynamic_entities(entry, async_add_entities, _build)
