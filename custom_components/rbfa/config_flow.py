"""Config flow for the RBFA integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import UnitOfTime
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .API import RbfaApi, RbfaBlockedError, RbfaError
from .const import (
    CONF_ALT_NAME,
    CONF_DURATION,
    CONF_SHOW_RANKING,
    CONF_SHOW_REFEREE,
    CONF_TEAM,
    DEFAULT_DURATION,
    DOMAIN,
    get_option,
)

_LOGGER = logging.getLogger(__name__)

DURATION_SELECTOR = selector.NumberSelector(
    selector.NumberSelectorConfig(
        min=5,
        max=180,
        step=5,
        mode=selector.NumberSelectorMode.BOX,
        unit_of_measurement=UnitOfTime.MINUTES,
    )
)


class RbfaConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow for RBFA."""

    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            team = str(user_input[CONF_TEAM]).strip()
            user_input[CONF_TEAM] = team
            await self.async_set_unique_id(team)
            self._abort_if_unique_id_configured()

            api = RbfaApi(async_get_clientsession(self.hass))
            try:
                info = await api.get_team(team)
            except RbfaBlockedError:
                errors["base"] = "blocked"
            except RbfaError as err:
                _LOGGER.debug("Validating team %s failed: %s", team, err)
                errors["base"] = "cannot_connect"
            else:
                if info is None:
                    errors[CONF_TEAM] = "invalid_team"
                else:
                    return self.async_create_entry(title=team, data=user_input)

        schema = vol.Schema(
            {
                vol.Required(CONF_TEAM): str,
                vol.Optional(CONF_ALT_NAME): str,
                vol.Required(CONF_DURATION, default=DEFAULT_DURATION): DURATION_SELECTOR,
                vol.Required(CONF_SHOW_RANKING, default=True): bool,
                vol.Required(CONF_SHOW_REFEREE, default=True): bool,
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(schema, user_input),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Create the options flow."""
        return RbfaOptionsFlow()


class RbfaOptionsFlow(OptionsFlow):
    """Options for an existing RBFA team."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        entry = self.config_entry
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_ALT_NAME,
                    description={"suggested_value": get_option(entry, CONF_ALT_NAME, "")},
                ): str,
                vol.Required(
                    CONF_DURATION,
                    default=get_option(entry, CONF_DURATION, DEFAULT_DURATION),
                ): DURATION_SELECTOR,
                vol.Required(
                    CONF_SHOW_RANKING, default=get_option(entry, CONF_SHOW_RANKING, True)
                ): bool,
                vol.Required(
                    CONF_SHOW_REFEREE, default=get_option(entry, CONF_SHOW_REFEREE, True)
                ): bool,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
