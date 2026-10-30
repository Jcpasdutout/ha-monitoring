"""Panneau « Monitoring » à l'adresse /monitoring, qui affiche l'add-on dans Home Assistant.

L'add-on a déjà son panneau, mais à une adresse imposée par le Supervisor
(/<empreinte du dépôt>_monitoring). Ce panneau-ci affiche la même page via l'Ingress,
avec une adresse courte, et masque l'entrée de l'add-on pour éviter un doublon.
"""

from __future__ import annotations

import logging
from pathlib import Path
from urllib.parse import urlparse

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.const import CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.hassio import is_hassio
from homeassistant.loader import async_get_integration

from .const import CONF_PANEL, DEFAULT_PANEL, DOMAIN, PANEL_ICON, PANEL_URL_PATH
from .coordinator import MonitoringConfigEntry

_LOGGER = logging.getLogger(__name__)

STATIC_URL = f"/{DOMAIN}_static"
PANEL_JS = "panel.js"
WEBCOMPONENT = "ha-monitoring-panel"
# Entrée de configuration propriétaire du panneau (il n'y en a qu'un).
DATA_PANEL_OWNER = f"{DOMAIN}_panel_owner"
DATA_STATIC = f"{DOMAIN}_static_registered"


def addon_slug(entry: MonitoringConfigEntry) -> str | None:
    """Slug de l'add-on qui sert ce monitoring, d'après son nom d'hôte (af026962-monitoring)."""
    host = urlparse(entry.data[CONF_URL]).hostname or ""
    if not host.endswith("-monitoring"):
        return None  # monitoring installé ailleurs (conteneur Proxmox, autre machine)
    return host.replace("-", "_")


def _supervisor_client(hass: HomeAssistant):
    # Import tardif : le module hassio n'existe pas hors Home Assistant OS / Supervised.
    from homeassistant.components.hassio import get_supervisor_client

    return get_supervisor_client(hass)


async def _set_addon_panel(hass: HomeAssistant, slug: str, visible: bool) -> None:
    """Affiche ou masque l'entrée de l'add-on dans la barre latérale."""
    from aiohasupervisor.models import AddonsOptions

    client = _supervisor_client(hass)
    info = await client.addons.addon_info(slug)
    if info.ingress_panel != visible:
        await client.addons.set_addon_options(slug, AddonsOptions(ingress_panel=visible))


async def async_setup_panel(hass: HomeAssistant, entry: MonitoringConfigEntry) -> None:
    """Crée le panneau /monitoring si ce monitoring est l'add-on et que l'option est active."""
    slug = addon_slug(entry)
    if slug is None or not is_hassio(hass):
        return
    wanted = entry.options.get(CONF_PANEL, DEFAULT_PANEL)
    try:
        if not wanted:
            # Option décochée : l'add-on retrouve son entrée dans la barre latérale.
            await _set_addon_panel(hass, slug, True)
            return
        client = _supervisor_client(hass)
        info = await client.addons.addon_info(slug)
    except Exception as err:  # noqa: BLE001 - le panneau est un confort, pas une condition
        _LOGGER.warning("Panneau /%s non créé : add-on %s illisible (%s)", PANEL_URL_PATH, slug, err)
        return
    if not info.ingress_url:
        _LOGGER.warning("Panneau /%s non créé : l'Ingress de l'add-on %s est désactivé", PANEL_URL_PATH, slug)
        return
    owner = hass.data.get(DATA_PANEL_OWNER)
    if owner is not None and owner != entry.entry_id:
        return  # un autre add-on Monitoring a déjà le panneau

    if not hass.data.get(DATA_STATIC):
        await hass.http.async_register_static_paths(
            [StaticPathConfig(STATIC_URL, str(Path(__file__).parent / "frontend"), False)]
        )
        hass.data[DATA_STATIC] = True
    if owner is None:
        version = (await async_get_integration(hass, DOMAIN)).version
        try:
            await panel_custom.async_register_panel(
                hass,
                frontend_url_path=PANEL_URL_PATH,
                webcomponent_name=WEBCOMPONENT,
                sidebar_title=info.name or "Monitoring",
                sidebar_icon=PANEL_ICON,
                # Le numéro de version force le navigateur à recharger le script après une mise à jour.
                module_url=f"{STATIC_URL}/{PANEL_JS}?v={version}",
                config={"slug": slug, "ingress_url": info.ingress_url, "title": info.name},
                require_admin=True,  # comme le panneau de l'add-on
            )
        except ValueError as err:
            # Une autre page occupe déjà /monitoring (tableau de bord du même nom, par exemple).
            _LOGGER.warning("Panneau /%s non créé : %s", PANEL_URL_PATH, err)
            return
        hass.data[DATA_PANEL_OWNER] = entry.entry_id
    try:
        await _set_addon_panel(hass, slug, False)
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("Entrée de l'add-on %s non masquée : %s", slug, err)


def async_remove_panel(hass: HomeAssistant, entry: MonitoringConfigEntry) -> None:
    """Retire le panneau quand l'entrée qui l'a créé est déchargée."""
    if hass.data.get(DATA_PANEL_OWNER) == entry.entry_id:
        frontend.async_remove_panel(hass, PANEL_URL_PATH)
        hass.data.pop(DATA_PANEL_OWNER)


async def async_restore_addon_panel(hass: HomeAssistant, entry: MonitoringConfigEntry) -> None:
    """Intégration supprimée : l'add-on retrouve son entrée dans la barre latérale."""
    slug = addon_slug(entry)
    if slug is None or not is_hassio(hass):
        return
    try:
        await _set_addon_panel(hass, slug, True)
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("Entrée de l'add-on %s non rétablie : %s", slug, err)
