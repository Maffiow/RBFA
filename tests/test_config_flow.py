"""Config flow tests."""
from __future__ import annotations

from unittest.mock import patch

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.rbfa.API import RbfaBlockedError
from custom_components.rbfa.const import DOMAIN

from .conftest import TEAM_ID


@pytest.fixture(autouse=True)
def skip_entry_setup():
    """Only test the flow; setting up the created entry is tested in test_init.

    The HTTP session is replaced too: closing a real one leaves a DNS resolver
    thread behind, which the test harness reports as a leak.
    """
    with (
        patch("custom_components.rbfa.async_setup_entry", return_value=True),
        patch("custom_components.rbfa.config_flow.async_get_clientsession"),
    ):
        yield


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
