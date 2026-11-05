"""Set up the integration in a real Home Assistant instance."""
from __future__ import annotations

import logging

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.rbfa.const import DOMAIN

from .conftest import TEAM_ID

# The fixtures hold the 2026-27 season; pin "now" to two days before the
# KFC Turnhout - E. Mechelen a/d Maas match of 7 November 2026.
NOW = "2026-11-05 12:00:00+01:00"


def _entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title=TEAM_ID,
        unique_id=TEAM_ID,
        data={"team": TEAM_ID, "duration": 105, "show_ranking": True, "show_referee": True},
    )


def _state(hass: HomeAssistant, unique_id: str):
    entity_id = er.async_get(hass).async_get_entity_id("sensor", DOMAIN, unique_id)
    assert entity_id, f"no entity for {unique_id}"
    return hass.states.get(entity_id)


def _integration_problems(caplog: pytest.LogCaptureFixture) -> list[str]:
    """Warnings and errors about this integration, deprecations included."""
    return [
        record.getMessage()
        for record in caplog.records
        if record.levelno >= logging.WARNING
        and "rbfa" in (record.name + record.getMessage()).lower()
        # Logged for every custom integration, not a problem of this one.
        and "has not been tested by home assistant" not in record.getMessage().lower()
    ]


@pytest.mark.usefixtures("enable_all_entities")
async def test_setup_and_sensors(
    hass: HomeAssistant, mock_api, freezer, caplog: pytest.LogCaptureFixture
) -> None:
    """The entry loads, every entity gets a value and nothing is deprecated."""
    freezer.move_to(NOW)
    caplog.set_level(logging.WARNING)
    entry = _entry()
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED

    calendar = er.async_get(hass).async_get_entity_id(
        "calendar", DOMAIN, f"{DOMAIN}_calendar_{TEAM_ID}"
    )
    assert calendar
    state = hass.states.get(calendar)
    assert state.attributes["message"] == "KFC Turnhout A 2 - E. Mechelen a/d Maas A 2"
    assert "Turnhout" in state.attributes["location"]

    assert _state(hass, f"{DOMAIN}_upcoming_hometeam_{TEAM_ID}").state == "KFC Turnhout A 2"
    away = _state(hass, f"{DOMAIN}_upcoming_awayteam_{TEAM_ID}")
    assert away.state == "E. Mechelen a/d Maas A 2"
    assert away.attributes["id"] == TEAM_ID
    assert away.attributes["entity_picture"].endswith("05384.jpg")
    assert "Turnhout" in _state(hass, f"{DOMAIN}_upcoming_location_{TEAM_ID}").state

    series = _state(hass, f"{DOMAIN}_upcoming_series_{TEAM_ID}")
    assert series.attributes["entity_picture"].endswith("LogoVOETBALVLAANDEREN.svg")
    ranking = series.attributes["ranking"]
    assert len(ranking) == 8
    assert {"position", "team", "id", "logo", "matches", "fairplay"} <= set(ranking[0])
    squad = series.attributes["squads"][TEAM_ID]
    assert squad["players"] and squad["staff"]
    assert {"name", "matches", "goals"} == set(squad["players"][0])

    assert _state(hass, f"{DOMAIN}_lastmatch_hometeam_{TEAM_ID}").state == (
        "E. Mechelen a/d Maas A 2"
    )

    assert _integration_problems(caplog) == []


async def test_options_reload_and_unload(hass: HomeAssistant, mock_api, freezer) -> None:
    """Changing the options reloads the entry; the entry unloads cleanly."""
    freezer.move_to(NOW)
    entry = _entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["step_id"] == "init"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"duration": 60, "show_ranking": False, "show_referee": False},
    )
    await hass.async_block_till_done()
    assert entry.options["duration"] == 60
    assert entry.state is ConfigEntryState.LOADED

    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_update_failure_retries(hass: HomeAssistant, mock_api) -> None:
    """An RBFA error during setup leaves the entry retrying, not broken."""
    from custom_components.rbfa.API import RbfaError

    mock_api["calendar"].side_effect = RbfaError("GetTeamCalendar: PersistedQueryNotFound")
    entry = _entry()
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_RETRY
