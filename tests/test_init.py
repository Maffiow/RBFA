"""Set up the integration in a real Home Assistant instance."""
from __future__ import annotations

import logging

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.rbfa.API import RbfaBlockedError, RbfaError
from custom_components.rbfa.const import DOMAIN

from .conftest import TEAM_ID, load_fixture

# The fixtures hold the 2026-27 season; pin "now" to two days before the
# KFC Turnhout - E. Mechelen a/d Maas match of 7 November 2026.
NOW = "2026-11-05 12:00:00+01:00"


def _entry(**options) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title=TEAM_ID,
        unique_id=TEAM_ID,
        data={"team": TEAM_ID, "duration": 105, "show_ranking": True, "show_referee": True},
        options=options,
    )


async def _setup(hass: HomeAssistant, entry: MockConfigEntry | None = None) -> MockConfigEntry:
    entry = entry or _entry()
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _state(hass: HomeAssistant, unique_id: str):
    entity_id = er.async_get(hass).async_get_entity_id("sensor", DOMAIN, unique_id)
    assert entity_id, f"no entity for {unique_id}"
    return hass.states.get(entity_id)


def _calendar(hass: HomeAssistant) -> str:
    entity_id = er.async_get(hass).async_get_entity_id(
        "calendar", DOMAIN, f"{DOMAIN}_calendar_{TEAM_ID}"
    )
    assert entity_id
    return entity_id


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
    entry = await _setup(hass)
    assert entry.state is ConfigEntryState.LOADED

    state = hass.states.get(_calendar(hass))
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
    entry = await _setup(hass)

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


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (RbfaBlockedError("Access Denied"), "blocking requests"),
        (RbfaError("GetTeamCalendar: PersistedQueryNotFound"), "PersistedQueryNotFound"),
        (None, "not found on rbfa.be"),
    ],
)
async def test_setup_errors_retry(
    hass: HomeAssistant, mock_api, caplog, error, message
) -> None:
    """Errors on the first refresh leave the entry retrying, with a clear reason."""
    if error:
        mock_api["calendar"].side_effect = error
    else:
        mock_api["calendar"].return_value = []
        mock_api["team"].return_value = None
    entry = await _setup(hass)
    assert entry.state is ConfigEntryState.SETUP_RETRY
    assert message in (entry.reason or "") + caplog.text


@pytest.mark.usefixtures("enable_all_entities")
async def test_failed_update_makes_entities_unavailable(
    hass: HomeAssistant, mock_api, freezer
) -> None:
    """Entities go unavailable while RBFA fails, and come back afterwards."""
    freezer.move_to(NOW)
    entry = await _setup(hass)
    coordinator = entry.runtime_data
    unique_id = f"{DOMAIN}_upcoming_hometeam_{TEAM_ID}"

    mock_api["calendar"].side_effect = RbfaError("HTTP 503")
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert _state(hass, unique_id).state == "unavailable"

    mock_api["calendar"].side_effect = None
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert _state(hass, unique_id).state == "KFC Turnhout A 2"


@pytest.mark.usefixtures("enable_all_entities")
async def test_failing_details_and_rankings(hass: HomeAssistant, mock_api, freezer) -> None:
    """Failing match details or rankings do not break the update."""
    freezer.move_to(NOW)
    mock_api["detail"].side_effect = RbfaError("detail")
    mock_api["rankings"].side_effect = RbfaError("rankings")
    entry = await _setup(hass)
    assert entry.state is ConfigEntryState.LOADED
    assert "ranking" not in _state(hass, f"{DOMAIN}_upcoming_series_{TEAM_ID}").attributes
    assert _state(hass, f"{DOMAIN}_upcoming_location_{TEAM_ID}").state == "unknown"


@pytest.mark.usefixtures("enable_all_entities")
@pytest.mark.parametrize("error", [RbfaBlockedError("Access Denied"), RbfaError("HTTP 500")])
async def test_blocked_details_and_squads(
    hass: HomeAssistant, mock_api, freezer, error
) -> None:
    """A blocked or failing detail or squad request is skipped, the rest still loads."""
    freezer.move_to(NOW)
    mock_api["detail"].side_effect = error
    mock_api["members"].side_effect = error
    entry = await _setup(hass)
    assert entry.state is ConfigEntryState.LOADED
    series = _state(hass, f"{DOMAIN}_upcoming_series_{TEAM_ID}")
    assert len(series.attributes["ranking"]) == 8
    assert "squads" not in series.attributes


@pytest.mark.usefixtures("enable_all_entities")
async def test_scores_referee_and_no_channel(hass: HomeAssistant, mock_api, freezer) -> None:
    """Published scores, penalties and the referee end up in the entities."""
    freezer.move_to(NOW)
    calendar = load_fixture("calendar")
    for match in calendar:
        match.pop("channel", None)
        if match["startTime"].startswith("2026-10-31"):
            match["outcome"].update(
                homeTeamGoals=3,
                awayTeamGoals=3,
                homeTeamPenaltiesScored=4,
                awayTeamPenaltiesScored=2,
            )
    mock_api["calendar"].return_value = calendar
    detail = load_fixture("match_detail")
    detail["officials"] = [
        {"firstName": "An", "lastName": "Assistent", "function": "assistant"},
        {"firstName": "Piet", "lastName": "Fluit", "function": "referee"},
    ]
    mock_api["detail"].return_value = detail
    await _setup(hass)

    assert _state(hass, f"{DOMAIN}_upcoming_referee_{TEAM_ID}").state == "Piet Fluit"
    home = _state(hass, f"{DOMAIN}_lastmatch_hometeam_{TEAM_ID}")
    assert home.attributes["goals"] == 3
    assert home.attributes["penalties"] == 4
    assert home.attributes["position"] == 1
    series = _state(hass, f"{DOMAIN}_upcoming_series_{TEAM_ID}")
    assert "entity_picture" not in series.attributes

    calendar_id = _calendar(hass)
    events = await hass.services.async_call(
        "calendar",
        "get_events",
        {"start_date_time": "2026-10-31T00:00:00+01:00", "duration": {"hours": 24}},
        target={"entity_id": calendar_id},
        blocking=True,
        return_response=True,
    )
    description = events[calendar_id]["events"][0]["description"]
    assert "Goals: 3 - 3" in description
    assert "Penalties: 4 - 2" in description


@pytest.mark.usefixtures("enable_all_entities")
async def test_referee_from_calendar_when_detail_has_none(
    hass: HomeAssistant, mock_api, freezer
) -> None:
    """Without match details, a single official on the calendar is the referee."""
    freezer.move_to(NOW)
    calendar = load_fixture("calendar")
    for match in calendar:
        if match["startTime"].startswith("2026-11-07"):
            match["officials"] = [{"firstName": "Jan", "lastName": "Peeters"}]
    mock_api["calendar"].return_value = calendar
    mock_api["detail"].return_value = None
    await _setup(hass)
    assert _state(hass, f"{DOMAIN}_upcoming_referee_{TEAM_ID}").state == "Jan Peeters"
    assert _state(hass, f"{DOMAIN}_upcoming_location_{TEAM_ID}").state == "unknown"


@pytest.mark.usefixtures("enable_all_entities")
@pytest.mark.parametrize(
    ("now", "upcoming", "lastmatch"),
    [
        ("2026-07-01 12:00:00+02:00", "LS LEUT", None),
        ("2027-01-15 12:00:00+01:00", None, "E. Mechelen a/d Maas A 2"),
    ],
)
async def test_before_and_after_the_season(
    hass: HomeAssistant, mock_api, freezer, now, upcoming, lastmatch
) -> None:
    """Without a next or a previous match those sensors are empty, not broken."""
    freezer.move_to(now)
    entry = await _setup(hass)
    assert entry.state is ConfigEntryState.LOADED
    for collection, value in (("upcoming", upcoming), ("lastmatch", lastmatch)):
        state = _state(hass, f"{DOMAIN}_{collection}_hometeam_{TEAM_ID}").state
        assert state == (value or "unknown")
    assert hass.states.get(_calendar(hass)).state in ("on", "off")


async def test_alt_name_and_options_skip_requests(
    hass: HomeAssistant, mock_api, freezer
) -> None:
    """The calendar uses the alternative name; options switch off extra requests."""
    freezer.move_to(NOW)
    await _setup(
        hass, _entry(alt_name="Tiziano", show_ranking=False, show_referee=False)
    )
    assert hass.states.get(_calendar(hass)).attributes["friendly_name"] == "Tiziano"
    mock_api["rankings"].assert_not_called()
    mock_api["members"].assert_not_called()
    assert (
        er.async_get(hass).async_get_entity_id(
            "sensor", DOMAIN, f"{DOMAIN}_upcoming_referee_{TEAM_ID}"
        )
        is None
    )


async def test_calendar_name_fallbacks(hass: HomeAssistant, mock_api, freezer) -> None:
    """Without an alternative name the calendar is named after club and team."""
    freezer.move_to(NOW)
    await _setup(hass)
    calendar_id = _calendar(hass)
    assert hass.states.get(calendar_id).attributes["friendly_name"] == (
        "EENDRACHT MECHELEN A/D MAAS | U10 A"
    )
    entity = hass.data["entity_components"]["calendar"].get_entity(calendar_id)
    entity.coordinator.data = {**entity.coordinator.data, "team": None, "upcoming": None}
    assert entity.name == f"{DOMAIN} {TEAM_ID}"
    assert entity.event is None
