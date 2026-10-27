"""Client de l'API du monitoring."""

from __future__ import annotations

import asyncio
from typing import Any

import aiohttp

from .const import DEFAULT_TIMEOUT


class MonitoringError(Exception):
    """Erreur générale de dialogue avec le monitoring."""


class MonitoringConnectionError(MonitoringError):
    """Le monitoring ne répond pas."""


class MonitoringAuthError(MonitoringError):
    """Le jeton d'accès est refusé."""


class MonitoringNotSupported(MonitoringError):
    """L'adresse ne répond pas comme un monitoring à jour."""


def normalize_url(url: str) -> str:
    """Ajoute http:// si besoin et retire la barre finale."""
    url = url.strip()
    if "://" not in url:
        url = f"http://{url}"
    return url.rstrip("/")


class MonitoringApi:
    """Accès en lecture (et relance des sondes) avec un jeton d'accès."""

    def __init__(self, session: aiohttp.ClientSession, url: str, token: str) -> None:
        self._session = session
        self.url = normalize_url(url)
        self._token = token.strip()

    async def _request(self, method: str, path: str) -> Any:
        try:
            async with asyncio.timeout(DEFAULT_TIMEOUT.total_seconds()):
                async with self._session.request(
                    method,
                    f"{self.url}{path}",
                    headers={"Authorization": f"Bearer {self._token}"},
                ) as resp:
                    if resp.status == 401:
                        raise MonitoringAuthError
                    if resp.status == 404:
                        raise MonitoringNotSupported
                    resp.raise_for_status()
                    try:
                        return await resp.json(content_type=None)
                    except ValueError as err:
                        raise MonitoringNotSupported from err
        except (TimeoutError, aiohttp.ClientConnectionError) as err:
            raise MonitoringConnectionError(str(err) or err.__class__.__name__) from err
        except aiohttp.ClientError as err:
            raise MonitoringError(str(err)) from err

    async def async_get_info(self) -> dict[str, Any]:
        """Vérifie le jeton et renvoie l'identifiant de l'installation."""
        info = await self._request("GET", "/api/auth")
        if not isinstance(info, dict) or "instance_id" not in info:
            raise MonitoringNotSupported
        if not info.get("api_token"):
            raise MonitoringAuthError
        return info

    async def async_get_probes(self) -> list[dict[str, Any]]:
        """Liste des sondes avec leur dernier résultat."""
        probes = await self._request("GET", "/api/probes")
        if not isinstance(probes, list):
            raise MonitoringNotSupported
        return probes

    async def async_run_probe(self, probe_id: int) -> None:
        """Relance une sonde tout de suite."""
        await self._request("POST", f"/api/probes/{probe_id}/run")

    async def async_refresh_all(self) -> None:
        """Relance toutes les sondes."""
        await self._request("POST", "/api/refresh")
