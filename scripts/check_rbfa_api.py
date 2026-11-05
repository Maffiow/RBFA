"""Run every query of the integration against the live RBFA API.

Catches the failure mode the unit tests cannot: rbfa.be changing or removing
fields the integration asks for. Exits 1 on a GraphQL error and 0 with a
warning when the RBFA firewall blocks the runner's IP address.
"""
from __future__ import annotations

import asyncio
import importlib.util
import sys
import types
from pathlib import Path

import aiohttp

ROOT = Path(__file__).resolve().parent.parent / "custom_components" / "rbfa"
TEAM = sys.argv[1] if len(sys.argv) > 1 else "378177"

# Load API.py and const.py without importing Home Assistant.
package = types.ModuleType("rbfa")
package.__path__ = [str(ROOT)]
sys.modules["rbfa"] = package
for name in ("const", "API"):
    spec = importlib.util.spec_from_file_location(f"rbfa.{name}", ROOT / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[f"rbfa.{name}"] = module
    spec.loader.exec_module(module)
api_module = sys.modules["rbfa.API"]


async def main() -> int:
    async with aiohttp.ClientSession() as session:
        api = api_module.RbfaApi(session)
        try:
            team = await api.get_team(TEAM)
            if team is None:
                # Team IDs change every season; pass a current one as argument.
                print(f"::warning::Team {TEAM} not found on rbfa.be, API not checked")
                return 0
            print(f"GetTeam: {team['name']} ({team['clubName']})")
            calendar = await api.get_calendar(TEAM)
            print(f"GetTeamCalendar: {len(calendar)} matches")
            match = calendar[-1]
            detail = await api.get_match_detail(match["id"])
            print(f"GetMatchDetail: {detail['location']}")
            series = next(
                (m["series"]["id"] for m in calendar if m["series"]["id"].startswith("CHP")),
                match["series"]["id"],
            )
            rankings = await api.get_rankings(series)
            print(f"GetSeriesRankings: {len((rankings or {}).get('rankings') or [])} ranking(s)")
            members = await api.get_team_members(TEAM)
            print(f"GetTeamMembers: {len(members['players'])} players")
        except api_module.RbfaBlockedError as err:
            print(f"::warning::Blocked by the RBFA firewall, API not checked: {err}")
            return 0
        except api_module.RbfaError as err:
            print(f"::error::{err}")
            return 1
    return 0


sys.exit(asyncio.run(main()))
