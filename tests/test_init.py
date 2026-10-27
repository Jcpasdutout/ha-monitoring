"""Création et mise à jour des entités."""

from __future__ import annotations

from datetime import timedelta

from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.ha_monitoring.const import DOMAIN

from .conftest import INSTANCE, URL


async def _setup(hass: HomeAssistant, entry) -> None:
    hass.config.language = "fr"
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_entities(hass: HomeAssistant, entry, mock_api) -> None:
    await _setup(hass, entry)
    assert entry.state is ConfigEntryState.LOADED

    # Mail
    state = hass.states.get("sensor.boite_free_mails_non_lus")
    assert state.state == "3"
    assert state.attributes["derniers_mails"][0]["objet"] == "Coucou"
    assert state.attributes["dossiers"] == {"INBOX": 3}
    assert hass.states.get("sensor.boite_free_etat").state == "ok"
    assert hass.states.get("binary_sensor.boite_free_probleme").state == "off"

    # HTTP
    assert hass.states.get("sensor.site_temps_de_reponse").state == "2500"
    assert hass.states.get("sensor.site_valeur_json").state == "21.5"
    assert hass.states.get("binary_sensor.site_probleme").state == "on"
    assert hass.states.get("sensor.site_etat").state == "warning"

    # SNMP : une entité par jauge
    assert hass.states.get("sensor.nas_cpu").state == "12.0"
    disk = hass.states.get("sensor.nas_disque")
    assert disk.state == "97.0"
    assert disk.attributes["niveau"] == "error"
    assert hass.states.get("sensor.nas_allumee_depuis").state == "12"

    # Sonde en pause, jamais exécutée
    assert hass.states.get("sensor.routeur_etat").state == "paused"
    assert hass.states.get("sensor.routeur_latence").state == STATE_UNKNOWN

    # Vue d'ensemble
    assert hass.states.get("sensor.monitoring_sondes_en_alerte_ou_en_erreur").state == "2"
    assert hass.states.get("sensor.monitoring_sondes_en_erreur").state == "1"
    assert hass.states.get("sensor.monitoring_mails_non_lus_total").state == "3"
    problem = hass.states.get("binary_sensor.monitoring_probleme_sur_une_sonde")
    assert problem.state == "on"
    assert problem.attributes["sondes"] == ["Site", "NAS"]

    devices = dr.async_get(hass)
    nas = devices.async_get_device(identifiers={(DOMAIN, f"{INSTANCE}_3")})
    assert nas.name == "NAS"
    assert nas.model == "Machine distante (SNMP)"
    assert nas.via_device_id == devices.async_get_device(identifiers={(DOMAIN, INSTANCE)}).id


async def test_probes_added_and_removed(
    hass: HomeAssistant, entry, mock_api, probes, freezer: FrozenDateTimeFactory
) -> None:
    await _setup(hass, entry)
    devices = dr.async_get(hass)
    entities = er.async_get(hass)

    removed = probes.pop(0)  # la boîte mail est supprimée dans le monitoring
    probes.append({**removed, "id": 7, "name": "Gmail"})  # et une nouvelle sonde apparaît
    probes[0]["name"] = "Site web"  # renommage
    mock_api.clear_requests()
    mock_api.get(f"{URL}/api/probes", json=probes)
    freezer.tick(timedelta(seconds=31))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert devices.async_get_device(identifiers={(DOMAIN, f"{INSTANCE}_1")}) is None
    assert entities.async_get("sensor.boite_free_mails_non_lus") is None
    assert hass.states.get("sensor.gmail_mails_non_lus").state == "3"
    site = devices.async_get_device(identifiers={(DOMAIN, f"{INSTANCE}_2")})
    assert site.name == "Site web"


async def test_unavailable_then_reauth(
    hass: HomeAssistant, entry, mock_api, freezer: FrozenDateTimeFactory
) -> None:
    await _setup(hass, entry)
    mock_api.clear_requests()
    mock_api.get(f"{URL}/api/probes", status=401, json={"error": "jeton"})
    freezer.tick(timedelta(seconds=31))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get("sensor.site_etat").state == STATE_UNAVAILABLE
    flows = hass.config_entries.flow.async_progress()
    assert [f["context"]["source"] for f in flows] == ["reauth"]


async def test_setup_retry_when_offline(hass: HomeAssistant, entry, aioclient_mock) -> None:
    aioclient_mock.get(f"{URL}/api/auth", status=502)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_buttons(hass: HomeAssistant, entry, mock_api) -> None:
    await _setup(hass, entry)
    await hass.services.async_call(
        "button", "press", {"entity_id": "button.boite_free_verifier_maintenant"}, blocking=True
    )
    assert any(str(c[1]).endswith("/api/probes/1/run") for c in mock_api.mock_calls)


async def test_stale_device_removed_on_startup(hass: HomeAssistant, entry, mock_api) -> None:
    entry.add_to_hass(hass)
    devices = dr.async_get(hass)
    devices.async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={(DOMAIN, f"{INSTANCE}_99")}, name="Ancienne"
    )
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert devices.async_get_device(identifiers={(DOMAIN, f"{INSTANCE}_99")}) is None
