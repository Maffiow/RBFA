"""Tests for the RBFA GraphQL client."""
from __future__ import annotations

import asyncio
import json

import aiohttp
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.rbfa.API import RbfaApi, RbfaBlockedError, RbfaError
from custom_components.rbfa.const import API_URL, QUERIES

from .conftest import TEAM_ID, load_fixture

JSON = {"Content-Type": "application/json"}


def _api(hass: HomeAssistant) -> RbfaApi:
    return RbfaApi(async_get_clientsession(hass), min_interval=0)


@pytest.mark.parametrize(
    ("method", "operation", "key", "fixture", "variable"),
    [
        ("get_team", "GetTeam", "team", "team", "teamId"),
        ("get_calendar", "GetTeamCalendar", "teamCalendar", "calendar", "teamId"),
        ("get_match_detail", "GetMatchDetail", "matchDetail", "match_detail", "matchId"),
        ("get_rankings", "GetSeriesRankings", "seriesRankings", "rankings", "seriesId"),
        ("get_team_members", "GetTeamMembers", "teamMembers", "team_members", "teamId"),
    ],
)
async def test_queries(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    method,
    operation,
    key,
    fixture,
    variable,
) -> None:
    """Every call sends its full query document and returns the result field."""
    data = load_fixture(fixture)
    aioclient_mock.post(API_URL, text=json.dumps({"data": {key: data}}), headers=JSON)

    assert await getattr(_api(hass), method)(TEAM_ID) == data

    _, _, payload, _ = aioclient_mock.mock_calls[0]
    assert payload["operationName"] == operation
    assert payload["query"] == QUERIES[operation]
    assert payload["variables"] == {variable: TEAM_ID, "language": "nl"}
    assert "extensions" not in payload


async def test_no_result(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.post(API_URL, text='{"data": {"team": null}}', headers=JSON)
    assert await _api(hass).get_team(TEAM_ID) is None


@pytest.mark.parametrize(
    ("kwargs", "error", "message"),
    [
        (
            {"text": "<HTML><HEAD><TITLE>Access Denied</TITLE>", "headers": {"Content-Type": "text/html"}},
            RbfaBlockedError,
            "Access Denied",
        ),
        ({"status": 500, "text": "oops", "headers": JSON}, RbfaError, "HTTP 500"),
        ({"text": "<html>maintenance</html>", "headers": {"Content-Type": "text/html"}}, RbfaError, "unexpected text/html"),
        ({"text": "{not json", "headers": JSON}, RbfaError, "invalid JSON"),
        (
            {
                "text": '{"errors": [{"message": "PersistedQueryNotFound"}]}',
                "headers": JSON,
            },
            RbfaError,
            "PersistedQueryNotFound",
        ),
        ({"text": '{"errors": []}', "headers": JSON}, RbfaError, "unknown error"),
        ({"exc": aiohttp.ClientError("boom")}, RbfaError, "connection error"),
        ({"exc": asyncio.TimeoutError()}, RbfaError, "connection error"),
    ],
)
async def test_errors(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, kwargs, error, message
) -> None:
    aioclient_mock.post(API_URL, **kwargs)
    with pytest.raises(error, match=message):
        await _api(hass).get_calendar(TEAM_ID)


async def test_requests_are_spaced(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """A second call waits until min_interval has passed since the first."""
    aioclient_mock.post(API_URL, text='{"data": {"team": {}}}', headers=JSON)
    api = RbfaApi(async_get_clientsession(hass), min_interval=0.05)
    loop = asyncio.get_running_loop()
    start = loop.time()
    await api.get_team(TEAM_ID)
    await api.get_team(TEAM_ID)
    assert loop.time() - start >= 0.05
