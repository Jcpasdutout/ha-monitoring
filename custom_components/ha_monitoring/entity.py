"""Bases communes aux entités : une sonde = un appareil, plus un appareil « Monitoring »."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, PROBE_TYPES, STATUS_PAUSED, STATUS_PENDING
from .coordinator import MonitoringConfigEntry, MonitoringCoordinator, probe_device_id


def probe_status(probe: dict[str, Any]) -> str:
    """Statut d'une sonde : ok, warning, error, ou pending / paused."""
    if not probe.get("enabled", True):
        return STATUS_PAUSED
    last = probe.get("last") or {}
    return last.get("status") or STATUS_PENDING


def probe_details(probe: dict[str, Any]) -> dict[str, Any]:
    """Détails du dernier résultat (jauges, dossiers mail...)."""
    return (probe.get("last") or {}).get("details") or {}


def hub_device_info(coordinator: MonitoringCoordinator) -> DeviceInfo:
    """L'appareil qui représente le monitoring lui-même."""
    return DeviceInfo(
        identifiers={(DOMAIN, coordinator.instance_id)},
        name="Monitoring",
        manufacturer="Monitoring",
        model="Tableau de bord des sondes",
        entry_type=DeviceEntryType.SERVICE,
        configuration_url=coordinator.api.url,
    )


class MonitoringHubEntity(CoordinatorEntity[MonitoringCoordinator]):
    """Entité rattachée à l'appareil « Monitoring » (vue d'ensemble)."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: MonitoringCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.instance_id}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = hub_device_info(coordinator)


class MonitoringProbeEntity(CoordinatorEntity[MonitoringCoordinator]):
    """Entité rattachée à une sonde."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: MonitoringCoordinator, probe_id: int, key: str
    ) -> None:
        super().__init__(coordinator)
        self.probe_id = probe_id
        probe = coordinator.data[probe_id]
        self._attr_unique_id = f"{coordinator.instance_id}_{probe_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={probe_device_id(coordinator.instance_id, probe_id)},
            name=probe.get("name"),
            manufacturer="Monitoring",
            model=PROBE_TYPES.get(probe.get("type"), probe.get("type")),
            via_device=(DOMAIN, coordinator.instance_id),
            configuration_url=f"{coordinator.api.url}/#/sondes",
        )

    @property
    def probe(self) -> dict[str, Any] | None:
        """Données actuelles de la sonde (None si elle a été supprimée)."""
        return self.coordinator.data.get(self.probe_id)

    @property
    def available(self) -> bool:
        return super().available and self.probe is not None


def async_add_dynamic_entities(
    entry: MonitoringConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
    build: Callable[[MonitoringCoordinator], Iterable[Entity]],
) -> None:
    """Ajoute les entités au démarrage, puis celles des nouvelles sondes à chaque mise à jour.

    `build` renvoie toutes les entités souhaitées pour l'état actuel ; seules celles
    dont l'identifiant n'est pas encore connu sont ajoutées.
    """
    coordinator = entry.runtime_data.coordinator
    known: set[str] = set()

    @callback
    def _add_new() -> None:
        new = [e for e in build(coordinator) if e.unique_id not in known]
        if new:
            known.update(e.unique_id for e in new)
            async_add_entities(new)

    _add_new()
    entry.async_on_unload(coordinator.async_add_listener(_add_new))
