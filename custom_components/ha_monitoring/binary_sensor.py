"""Capteurs binaires « Problème » : un par sonde et un pour l'ensemble."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import STATUS_ERROR, STATUS_PENDING, STATUS_WARNING
from .coordinator import MonitoringConfigEntry, MonitoringCoordinator
from .entity import (
    MonitoringHubEntity,
    MonitoringProbeEntity,
    async_add_dynamic_entities,
    probe_status,
)

PARALLEL_UPDATES = 0
PROBLEM_STATUSES = (STATUS_WARNING, STATUS_ERROR)


class ProbeProblem(MonitoringProbeEntity, BinarySensorEntity):
    """Allumé quand la sonde est en alerte ou en erreur."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_translation_key = "problem"
    _unrecorded_attributes = frozenset({"resume"})

    def __init__(self, coordinator: MonitoringCoordinator, probe_id: int) -> None:
        super().__init__(coordinator, probe_id, "problem")

    @property
    def is_on(self) -> bool | None:
        probe = self.probe
        if not probe or probe_status(probe) == STATUS_PENDING:
            return None
        return probe_status(probe) in PROBLEM_STATUSES

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        probe = self.probe
        if not probe:
            return None
        return {
            "statut": probe_status(probe),
            "resume": (probe.get("last") or {}).get("summary"),
        }


class HubProblem(MonitoringHubEntity, BinarySensorEntity):
    """Allumé dès qu'une sonde est en alerte ou en erreur."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator: MonitoringCoordinator) -> None:
        super().__init__(coordinator, "any_problem")

    def _problems(self) -> list[str]:
        return [
            p.get("name")
            for p in self.coordinator.data.values()
            if probe_status(p) in PROBLEM_STATUSES
        ]

    @property
    def is_on(self) -> bool:
        return bool(self._problems())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"sondes": self._problems()}


def _build(coordinator: MonitoringCoordinator) -> Iterable[BinarySensorEntity]:
    yield HubProblem(coordinator)
    for pid in coordinator.data:
        yield ProbeProblem(coordinator, pid)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MonitoringConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Crée les capteurs binaires."""
    async_add_dynamic_entities(entry, async_add_entities, _build)
