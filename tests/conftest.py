"""Shared fixtures for the RBFA tests."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, PropertyMock, patch

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
TEAM_ID = "378177"


def load_fixture(name: str):
    """Load a recorded RBFA API response from tests/fixtures."""
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Let Home Assistant load the integration from custom_components."""
    yield


@pytest.fixture
def enable_all_entities():
    """Enable the sensors, which are disabled by default."""
    with patch(
        "homeassistant.helpers.entity.Entity.entity_registry_enabled_default",
        new_callable=PropertyMock,
        return_value=True,
    ):
        yield


@pytest.fixture
def mock_api():
    """Replace the RBFA API calls with recorded responses."""
    target = "custom_components.rbfa.API.RbfaApi"
    with (
        patch(f"{target}.get_team", AsyncMock(return_value=load_fixture("team"))) as team,
        patch(
            f"{target}.get_calendar", AsyncMock(return_value=load_fixture("calendar"))
        ) as calendar,
        patch(
            f"{target}.get_match_detail",
            AsyncMock(return_value=load_fixture("match_detail")),
        ) as detail,
        patch(
            f"{target}.get_rankings", AsyncMock(return_value=load_fixture("rankings"))
        ) as rankings,
        patch(
            f"{target}.get_team_members",
            AsyncMock(return_value=load_fixture("team_members")),
        ) as members,
    ):
        yield {
            "team": team,
            "calendar": calendar,
            "detail": detail,
            "rankings": rankings,
            "members": members,
        }
