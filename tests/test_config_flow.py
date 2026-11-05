"""Config flow and options flow tests (100% of config_flow.py)."""
from __future__ import annotations

from unittest.mock import patch

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.rbfa.API import RbfaBlockedError, RbfaError
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


USER_INPUT = {
    "team": f" {TEAM_ID} ",
    "duration": 105,
    "show_ranking": True,
    "show_referee": True,
}


async def _start(hass: HomeAssistant):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}
    return result


async def test_user_flow_creates_entry(hass: HomeAssistant, mock_api) -> None:
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == TEAM_ID
    assert result["data"]["team"] == TEAM_ID
    assert result["result"].unique_id == TEAM_ID


@pytest.mark.parametrize(
    ("side_effect", "return_value", "errors"),
    [
        (RbfaBlockedError("Access Denied"), None, {"base": "blocked"}),
        (RbfaError("HTTP 500"), None, {"base": "cannot_connect"}),
        (None, None, {"team": "invalid_team"}),
    ],
)
async def test_user_flow_errors_recover(
    hass: HomeAssistant, mock_api, side_effect, return_value, errors
) -> None:
    """Every error is shown, and the user can finish the flow once it is gone."""
    team_info = mock_api["team"].return_value
    mock_api["team"].side_effect = side_effect
    mock_api["team"].return_value = return_value

    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == errors

    mock_api["team"].side_effect = None
    mock_api["team"].return_value = team_info
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == TEAM_ID


async def test_user_flow_already_configured(hass: HomeAssistant, mock_api) -> None:
    MockConfigEntry(domain=DOMAIN, unique_id=TEAM_ID, data={"team": TEAM_ID}).add_to_hass(
        hass
    )
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    mock_api["team"].assert_not_called()


async def test_options_flow(hass: HomeAssistant) -> None:
    """The options form shows the current settings and stores the new ones."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=TEAM_ID,
        data={**USER_INPUT, "team": TEAM_ID, "alt_name": "Tiziano"},
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"
    defaults = {
        str(key): key.default() if callable(key.default) else key.default
        for key in result["data_schema"].schema
    }
    assert defaults["duration"] == 105
    assert defaults["show_ranking"] is True

    new = {"alt_name": "U10 A", "duration": 60, "show_ranking": False, "show_referee": False}
    result = await hass.config_entries.options.async_configure(result["flow_id"], new)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == new
