"""Config flow tests."""
from __future__ import annotations

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.rbfa.API import RbfaBlockedError
from custom_components.rbfa.const import DOMAIN

from .conftest import TEAM_ID

USER_INPUT = {"team": f" {TEAM_ID} ", "duration": 105, "show_ranking": True, "show_referee": True}


async def test_user_flow_creates_entry(hass: HomeAssistant, mock_api) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == TEAM_ID
    assert result["data"]["team"] == TEAM_ID


async def test_user_flow_unknown_team(hass: HomeAssistant, mock_api) -> None:
    mock_api["team"].return_value = None
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"team": "invalid_team"}


async def test_user_flow_blocked(hass: HomeAssistant, mock_api) -> None:
    mock_api["team"].side_effect = RbfaBlockedError("Access Denied")
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    assert result["errors"] == {"base": "blocked"}
