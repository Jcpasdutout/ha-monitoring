"""Capteurs : état, valeurs mesurées et vue d'ensemble."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.util import slugify

from .const import (
    CONF_MAIL_PREVIEW,
    DEFAULT_MAIL_PREVIEW,
    STATUS_ERROR,
    STATUS_WARNING,
    STATUSES,
)
from .coordinator import MonitoringConfigEntry, MonitoringCoordinator
from .entity import (
    MonitoringHubEntity,
    MonitoringProbeEntity,
    async_add_dynamic_entities,
    probe_details,
    probe_status,
)

PARALLEL_UPDATES = 0


def _last(probe: dict[str, Any]) -> dict[str, Any]:
    return probe.get("last") or {}


def _value_unless_error(probe: dict[str, Any]) -> StateType:
    """Valeur principale, sauf quand la vérification a échoué."""
    last = _last(probe)
    return None if last.get("status") == STATUS_ERROR else last.get("value")


def _last_check(probe: dict[str, Any]) -> datetime | None:
    ts = _last(probe).get("ts")
    return datetime.fromtimestamp(ts, UTC) if ts else None


def _json_value(probe: dict[str, Any]) -> StateType:
    value = probe_details(probe).get("json_value")
    if value is None or isinstance(value, (int, float)) and not isinstance(value, bool):
        return value
    return str(value)[:255]


def _status_attrs(probe: dict[str, Any], options: dict[str, Any]) -> dict[str, Any]:
    last = _last(probe)
    return {
        "resume": last.get("summary"),
        "groupe": probe.get("group") or None,
        "duree_ms": last.get("duration_ms"),
    }


def _mail_attrs(probe: dict[str, Any], options: dict[str, Any]) -> dict[str, Any]:
    details = probe_details(probe)
    attrs: dict[str, Any] = {"dossiers": details.get("folders")}
    if options.get(CONF_MAIL_PREVIEW, DEFAULT_MAIL_PREVIEW):
        attrs["derniers_mails"] = [
            {
                "de": m.get("from"),
                "objet": m.get("subject"),
                "date": m.get("date"),
                "dossier": m.get("folder"),
            }
            for m in details.get("messages") or []
        ]
    return attrs


@dataclass(frozen=True, kw_only=True)
class ProbeSensorDescription(SensorEntityDescription):
    """Capteur d'une sonde."""

    value_fn: Callable[[dict[str, Any]], StateType | datetime]
    types: tuple[str, ...] | None = None  # None : tous les types de sonde
    exists_fn: Callable[[dict[str, Any]], bool] = lambda probe: True
    attrs_fn: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]] | None = None


PROBE_SENSORS: tuple[ProbeSensorDescription, ...] = (
    ProbeSensorDescription(
        key="status",
        translation_key="status",
        device_class=SensorDeviceClass.ENUM,
        options=STATUSES,
        value_fn=probe_status,
        attrs_fn=_status_attrs,
    ),
    ProbeSensorDescription(
        key="last_check",
        translation_key="last_check",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_last_check,
    ),
    ProbeSensorDescription(
        key="unread",
        translation_key="unread",
        types=("imap",),
        native_unit_of_measurement="mails",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_value_unless_error,
        attrs_fn=_mail_attrs,
    ),
    ProbeSensorDescription(
        key="response_time",
        translation_key="response_time",
        types=("http",),
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MILLISECONDS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda p: probe_details(p).get("latency_ms", _last(p).get("value")),
    ),
    ProbeSensorDescription(
        key="http_status",
        translation_key="http_status",
        types=("http",),
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda p: probe_details(p).get("http_status"),
    ),
    ProbeSensorDescription(
        key="json_value",
        translation_key="json_value",
        types=("http",),
        exists_fn=lambda p: bool(
            (p.get("config") or {}).get("json_path") or "json_value" in probe_details(p)
        ),
        value_fn=_json_value,
    ),
    ProbeSensorDescription(
        key="latency",
        translation_key="latency",
        types=("ping",),
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MILLISECONDS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=_value_unless_error,
    ),
    ProbeSensorDescription(
        key="packet_loss",
        translation_key="packet_loss",
        types=("ping",),
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda p: (
            100 if _last(p).get("status") == STATUS_ERROR else probe_details(p).get("loss_pct")
        ),
    ),
    ProbeSensorDescription(
        key="uptime",
        translation_key="uptime",
        types=("snmp",),
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.DAYS,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda p: probe_details(p).get("uptime_days"),
    ),
)


class ProbeSensor(MonitoringProbeEntity, SensorEntity):
    """Une valeur d'une sonde."""

    entity_description: ProbeSensorDescription
    _unrecorded_attributes = frozenset({"derniers_mails", "dossiers", "resume", "duree_ms"})

    def __init__(
        self,
        coordinator: MonitoringCoordinator,
        probe_id: int,
        description: ProbeSensorDescription,
    ) -> None:
        super().__init__(coordinator, probe_id, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> StateType | datetime:
        probe = self.probe
        return self.entity_description.value_fn(probe) if probe else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        probe = self.probe
        if not probe or not self.entity_description.attrs_fn:
            return None
        return self.entity_description.attrs_fn(probe, self.coordinator.config_entry.options)


class GaugeSensor(MonitoringProbeEntity, SensorEntity):
    """Une jauge SNMP (CPU, RAM, chaque disque, OID personnalisé)."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self, coordinator: MonitoringCoordinator, probe_id: int, gauge: dict[str, Any]
    ) -> None:
        self._label = gauge.get("label") or gauge.get("key") or "valeur"
        super().__init__(coordinator, probe_id, gauge_key(gauge))
        self._attr_name = self._label
        if gauge.get("pct") is not None:
            self._attr_native_unit_of_measurement = PERCENTAGE
            self._attr_suggested_display_precision = 1
        if gauge.get("key") == "cpu":
            self._attr_icon = "mdi:cpu-64-bit"
        elif gauge.get("key") == "ram":
            self._attr_icon = "mdi:memory"
        elif gauge.get("key") == "disk":
            self._attr_icon = "mdi:harddisk"

    def _gauge(self) -> dict[str, Any] | None:
        probe = self.probe
        if not probe:
            return None
        for gauge in probe_details(probe).get("gauges") or []:
            if (gauge.get("label") or gauge.get("key")) == self._label:
                return gauge
        return None

    @property
    def native_value(self) -> StateType:
        gauge = self._gauge()
        if gauge is None:
            return None
        if gauge.get("pct") is not None:
            return gauge["pct"]
        raw = gauge.get("raw", gauge.get("text"))
        if raw is None or isinstance(raw, (int, float)):
            return raw
        return str(raw)[:255]

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        gauge = self._gauge()
        return {"detail": gauge.get("text"), "niveau": gauge.get("level")} if gauge else None


def gauge_key(gauge: dict[str, Any]) -> str:
    return f"gauge_{slugify(gauge.get('label') or gauge.get('key') or 'valeur')}"


@dataclass(frozen=True, kw_only=True)
class HubSensorDescription(SensorEntityDescription):
    """Capteur de vue d'ensemble."""

    value_fn: Callable[[list[dict[str, Any]]], StateType]
    attrs_fn: Callable[[list[dict[str, Any]]], dict[str, Any]] | None = None


def _names(probes: list[dict[str, Any]], *statuses: str) -> list[str]:
    return [p.get("name") for p in probes if probe_status(p) in statuses]


HUB_SENSORS: tuple[HubSensorDescription, ...] = (
    HubSensorDescription(
        key="problems",
        translation_key="problems",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda probes: len(_names(probes, STATUS_WARNING, STATUS_ERROR)),
        attrs_fn=lambda probes: {
            "erreurs": _names(probes, STATUS_ERROR),
            "alertes": _names(probes, STATUS_WARNING),
        },
    ),
    HubSensorDescription(
        key="errors",
        translation_key="errors",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda probes: len(_names(probes, STATUS_ERROR)),
    ),
    HubSensorDescription(
        key="unread_total",
        translation_key="unread_total",
        native_unit_of_measurement="mails",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda probes: sum(
            _value_unless_error(p) or 0
            for p in probes
            if p.get("type") == "imap" and p.get("enabled", True)
        ),
    ),
    HubSensorDescription(
        key="probe_count",
        translation_key="probe_count",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=len,
    ),
)


class HubSensor(MonitoringHubEntity, SensorEntity):
    """Vue d'ensemble de toutes les sondes."""

    entity_description: HubSensorDescription

    def __init__(
        self, coordinator: MonitoringCoordinator, description: HubSensorDescription
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> StateType:
        return self.entity_description.value_fn(list(self.coordinator.data.values()))

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if not self.entity_description.attrs_fn:
            return None
        return self.entity_description.attrs_fn(list(self.coordinator.data.values()))


def _build(coordinator: MonitoringCoordinator) -> Iterable[SensorEntity]:
    for description in HUB_SENSORS:
        yield HubSensor(coordinator, description)
    for pid, probe in coordinator.data.items():
        for description in PROBE_SENSORS:
            if (
                description.types is None or probe.get("type") in description.types
            ) and description.exists_fn(probe):
                yield ProbeSensor(coordinator, pid, description)
        for gauge in probe_details(probe).get("gauges") or []:
            yield GaugeSensor(coordinator, pid, gauge)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MonitoringConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Crée les capteurs, puis ceux des sondes ajoutées plus tard."""
    async_add_dynamic_entities(entry, async_add_entities, _build)
