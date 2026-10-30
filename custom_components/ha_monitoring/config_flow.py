"""Formulaires de configuration : adresse + jeton (ou découverte de l'add-on), puis options."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import urlparse

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_TOKEN, CONF_URL
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
from homeassistant.helpers.service_info.hassio import HassioServiceInfo

from .api import (
    MonitoringApi,
    MonitoringAuthError,
    MonitoringConnectionError,
    MonitoringError,
    MonitoringNotSupported,
    normalize_url,
)
from .const import (
    CONF_MAIL_PREVIEW,
    CONF_PANEL,
    CONF_SCAN_INTERVAL,
    DEFAULT_MAIL_PREVIEW,
    DEFAULT_PANEL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)
from .coordinator import MonitoringConfigEntry

TOKEN_SELECTOR = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))
URL_SELECTOR = TextSelector(TextSelectorConfig(type=TextSelectorType.URL))


class MonitoringConfigFlow(ConfigFlow, domain=DOMAIN):
    """Ajout du monitoring depuis Paramètres > Appareils et services."""

    VERSION = 1

    _discovered: dict[str, str]

    async def _validate(self, url: str, token: str) -> tuple[dict[str, Any] | None, dict[str, str]]:
        """Teste l'adresse et le jeton ; renvoie (infos, erreurs)."""
        api = MonitoringApi(async_get_clientsession(self.hass), url, token)
        try:
            return await api.async_get_info(), {}
        except MonitoringAuthError:
            return None, {"base": "invalid_auth"}
        except MonitoringNotSupported:
            return None, {"base": "not_monitoring"}
        except MonitoringConnectionError:
            return None, {"base": "cannot_connect"}
        except MonitoringError:
            return None, {"base": "unknown"}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            url = normalize_url(user_input[CONF_URL])
            token = user_input[CONF_TOKEN].strip()
            info, errors = await self._validate(url, token)
            if info:
                await self.async_set_unique_id(info["instance_id"])
                self._abort_if_unique_id_configured(
                    updates={CONF_URL: url, CONF_TOKEN: token}
                )
                return self.async_create_entry(
                    title=f"Monitoring ({urlparse(url).hostname})",
                    data={CONF_URL: url, CONF_TOKEN: token},
                )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(
                    {
                        vol.Required(CONF_URL): URL_SELECTOR,
                        vol.Required(CONF_TOKEN): TOKEN_SELECTOR,
                    }
                ),
                user_input or {CONF_URL: "http://"},
            ),
            errors=errors,
        )

    async def async_step_hassio(
        self, discovery_info: HassioServiceInfo
    ) -> ConfigFlowResult:
        """L'add-on Monitoring s'est annoncé avec son adresse et un jeton prêt à l'emploi."""
        config = discovery_info.config
        url = f"http://{config['host']}:{config['port']}"
        token = config["token"]
        info, errors = await self._validate(url, token)
        if not info:
            return self.async_abort(reason=errors["base"])
        await self.async_set_unique_id(info["instance_id"])
        # Déjà configuré (à la main ou par une découverte précédente) : on passe à
        # l'adresse et au jeton de l'add-on, ce qui suit aussi un jeton recréé.
        self._abort_if_unique_id_configured(updates={CONF_URL: url, CONF_TOKEN: token})
        self._discovered = {CONF_URL: url, CONF_TOKEN: token}
        self.context["title_placeholders"] = {"addon": discovery_info.name}
        return await self.async_step_hassio_confirm()

    async def async_step_hassio_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(
                title="Monitoring (add-on)", data=self._discovered
            )
        return self.async_show_form(step_id="hassio_confirm")

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Le jeton a été supprimé ou remplacé côté monitoring."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            token = user_input[CONF_TOKEN].strip()
            info, errors = await self._validate(entry.data[CONF_URL], token)
            if info:
                await self.async_set_unique_id(info["instance_id"])
                self._abort_if_unique_id_mismatch(reason="wrong_instance")
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_TOKEN: token}
                )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_TOKEN): TOKEN_SELECTOR}),
            description_placeholders={"url": entry.data[CONF_URL]},
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Changer l'adresse (par exemple si l'IP du conteneur a changé) ou le jeton."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            url = normalize_url(user_input[CONF_URL])
            token = (user_input.get(CONF_TOKEN) or "").strip() or entry.data[CONF_TOKEN]
            info, errors = await self._validate(url, token)
            if info:
                await self.async_set_unique_id(info["instance_id"])
                self._abort_if_unique_id_mismatch(reason="wrong_instance")
                return self.async_update_reload_and_abort(
                    entry,
                    title=f"Monitoring ({urlparse(url).hostname})",
                    data_updates={CONF_URL: url, CONF_TOKEN: token},
                )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(
                    {
                        vol.Required(CONF_URL): URL_SELECTOR,
                        vol.Optional(CONF_TOKEN): TOKEN_SELECTOR,
                    }
                ),
                {CONF_URL: (user_input or entry.data)[CONF_URL]},
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(entry: MonitoringConfigEntry) -> MonitoringOptionsFlow:
        return MonitoringOptionsFlow()


class MonitoringOptionsFlow(OptionsFlowWithReload):
    """Options : fréquence de mise à jour, aperçu des mails et panneau /monitoring."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            user_input[CONF_SCAN_INTERVAL] = int(user_input[CONF_SCAN_INTERVAL])
            return self.async_create_entry(data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(
                    {
                        vol.Required(CONF_SCAN_INTERVAL): NumberSelector(
                            NumberSelectorConfig(
                                min=MIN_SCAN_INTERVAL,
                                max=3600,
                                step=1,
                                unit_of_measurement="s",
                                mode=NumberSelectorMode.BOX,
                            )
                        ),
                        vol.Required(CONF_MAIL_PREVIEW): BooleanSelector(),
                        vol.Required(CONF_PANEL): BooleanSelector(),
                    }
                ),
                {
                    CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                    CONF_MAIL_PREVIEW: DEFAULT_MAIL_PREVIEW,
                    CONF_PANEL: DEFAULT_PANEL,
                    **self.config_entry.options,
                },
            ),
        )
