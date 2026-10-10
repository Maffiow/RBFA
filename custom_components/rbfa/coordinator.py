"""Data update coordinator for the RBFA integration."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .API import RbfaApi, RbfaBlockedError, RbfaError
from .const import (
    CONF_DURATION,
    CONF_SHOW_RANKING,
    CONF_SHOW_REFEREE,
    CONF_TEAM,
    DEFAULT_DURATION,
    DOMAIN,
    MAX_DETAIL_FETCHES,
    REQUEST_DELAY,
    SQUAD_REFRESH,
    TZ,
    UPDATE_INTERVAL,
    get_option,
)

_LOGGER = logging.getLogger(__name__)


class MyCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch the calendar, match details and rankings of one team.

    coordinator.data = {
        "team":      team info dict (clubName, name, logo, ...) or None,
        "upcoming":  match dict of the next match, or None,
        "lastmatch": match dict of the previous match, or None,
        "events":    list of calendar event dicts,
    }
    """

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} {entry.data[CONF_TEAM]}",
            update_interval=UPDATE_INTERVAL,
        )
        self.team: str = str(entry.data[CONF_TEAM]).strip()
        self.api = RbfaApi(async_get_clientsession(hass), min_interval=REQUEST_DELAY)
        self._team_info: dict | None = None
        # match id -> {"location": str | None, "referee": str | None}
        self._details: dict[str, dict[str, str | None]] = {}
        # team id -> (fetched at, {"players": [...], "staff": [...]})
        self._squads: dict[str, tuple[datetime, dict[str, list[dict]]]] = {}

    async def _async_update_data(self) -> dict[str, Any]:
        entry = self.config_entry
        duration = int(get_option(entry, CONF_DURATION, DEFAULT_DURATION))
        show_ranking = get_option(entry, CONF_SHOW_RANKING, True)
        show_referee = get_option(entry, CONF_SHOW_REFEREE, True)

        try:
            if self._team_info is None:
                self._team_info = await self.api.get_team(self.team)
            calendar = await self.api.get_calendar(self.team)
        except RbfaBlockedError as err:
            raise UpdateFailed(
                f"{err}. The RBFA website is blocking requests from this IP "
                "address; it will be retried automatically"
            ) from err
        except RbfaError as err:
            raise UpdateFailed(str(err)) from err

        if self._team_info is None and not calendar:
            raise UpdateFailed(
                f"Team {self.team} not found on rbfa.be. Team IDs change "
                "every season, check the ID in the URL of the team page"
            )
        calendar = calendar or []

        tz = dt_util.get_time_zone(TZ)
        now = dt_util.utcnow()
        matches = []
        for item in calendar:
            start = datetime.fromisoformat(item["startTime"]).replace(tzinfo=tz)
            matches.append((item, start, start + timedelta(minutes=duration)))
        matches.sort(key=lambda m: m[1])

        upcoming_idx = next(
            (i for i, (_, _, end) in enumerate(matches) if end >= now), None
        )
        if upcoming_idx is None:
            last_idx = len(matches) - 1 if matches else None
        else:
            last_idx = upcoming_idx - 1 if upcoming_idx > 0 else None

        await self._update_details(matches, upcoming_idx, last_idx, now)

        upcoming = (
            self._match_data(*matches[upcoming_idx], show_referee)
            if upcoming_idx is not None
            else None
        )
        lastmatch = (
            self._match_data(*matches[last_idx], show_referee)
            if last_idx is not None
            else None
        )

        if show_ranking:
            await self._add_rankings([m for m in (upcoming, lastmatch) if m])

        return {
            "team": self._team_info,
            "upcoming": upcoming,
            "lastmatch": lastmatch,
            "events": [self._event(*m) for m in matches],
        }

    async def _update_details(
        self,
        matches: list[tuple[dict, datetime, datetime]],
        upcoming_idx: int | None,
        last_idx: int | None,
        now: datetime,
    ) -> None:
        """Fetch location/referee for a limited number of matches.

        The next match is refreshed every update (referee may still change);
        other matches only once, nearest first, a few per update.
        """
        todo: list[str] = []
        if upcoming_idx is not None:
            todo.append(matches[upcoming_idx][0]["id"])
        if last_idx is not None and matches[last_idx][0]["id"] not in self._details:
            todo.append(matches[last_idx][0]["id"])

        uncached = sorted(
            (m for m in matches if m[0]["id"] not in self._details and m[0]["id"] not in todo),
            key=lambda m: abs(m[1] - now),
        )
        todo.extend(m[0]["id"] for m in uncached[:MAX_DETAIL_FETCHES])

        for match_id in todo:
            try:
                detail = await self.api.get_match_detail(match_id)
            except RbfaBlockedError as err:
                _LOGGER.warning("Stopped fetching match details: %s", err)
                return
            except RbfaError as err:
                _LOGGER.debug("Match detail %s failed: %s", match_id, err)
                continue
            self._details[match_id] = _parse_detail(detail)

    async def _add_rankings(self, items: list[dict]) -> None:
        cache: dict[str, list[dict]] = {}
        for match in items:
            series = match["seriesid"]
            if series not in cache:
                try:
                    cache[series] = _parse_ranking(await self.api.get_rankings(series))
                except RbfaError as err:
                    _LOGGER.debug("Ranking for %s failed: %s", series, err)
                    cache[series] = []
            match["ranking"] = cache[series]
            match["squads"] = await self._squads_for(cache[series])
            for rank in cache[series]:
                if rank["id"] == match["hometeamid"]:
                    match["hometeamposition"] = rank["position"]
                if rank["id"] == match["awayteamid"]:
                    match["awayteamposition"] = rank["position"]

    async def _squads_for(self, ranking: list[dict]) -> dict[str, dict]:
        """Return players and staff of every team in a series, keyed by team id.

        Cached per team; a stale or missing squad is fetched again, and a
        failure keeps whatever was fetched before.
        """
        now = dt_util.utcnow()
        for rank in ranking:
            team_id = rank.get("id")
            if not team_id:
                continue
            cached = self._squads.get(team_id)
            if cached and now - cached[0] < SQUAD_REFRESH:
                continue
            try:
                members = await self.api.get_team_members(team_id)
            except RbfaBlockedError as err:
                _LOGGER.warning("Stopped fetching squads: %s", err)
                break
            except RbfaError as err:
                _LOGGER.debug("Squad of team %s failed: %s", team_id, err)
                continue
            self._squads[team_id] = (now, _parse_squad(members))

        return {
            rank["id"]: self._squads[rank["id"]][1]
            for rank in ranking
            if rank.get("id") in self._squads
        }

    def _match_data(
        self, item: dict, start: datetime, end: datetime, show_referee: bool
    ) -> dict[str, Any]:
        detail = self._details.get(item["id"], {})
        outcome = item.get("outcome") or {}
        home = item.get("homeTeam") or {}
        away = item.get("awayTeam") or {}
        series = item.get("series") or {}

        referee = None
        if show_referee:
            referee = detail.get("referee") or _calendar_referee(item)

        return {
            "matchid": item["id"],
            "team": self.team,
            "channel": item.get("channel") or "",
            "starttime": start,
            "endtime": end,
            "location": detail.get("location"),
            "referee": referee,
            "hometeam": home.get("name"),
            "hometeamid": home.get("id"),
            "hometeamlogo": home.get("logo"),
            "hometeamgoals": outcome.get("homeTeamGoals"),
            "hometeampenalties": outcome.get("homeTeamPenaltiesScored"),
            "hometeamposition": None,
            "awayteam": away.get("name"),
            "awayteamid": away.get("id"),
            "awayteamlogo": away.get("logo"),
            "awayteamgoals": outcome.get("awayTeamGoals"),
            "awayteampenalties": outcome.get("awayTeamPenaltiesScored"),
            "awayteamposition": None,
            "series": series.get("name"),
            "seriesid": series.get("id"),
            "ranking": [],
            "squads": {},
        }

    def _event(self, item: dict, start: datetime, end: datetime) -> dict[str, Any]:
        outcome = item.get("outcome") or {}
        series = (item.get("series") or {}).get("name") or ""
        description = f"{series} (state: {item.get('state')})"

        if outcome.get("homeTeamGoals") is not None:
            description += (
                f"; Goals: {outcome['homeTeamGoals']} - {outcome.get('awayTeamGoals')}"
            )
        if outcome.get("homeTeamPenaltiesScored") is not None:
            description += (
                f"; Penalties: {outcome['homeTeamPenaltiesScored']}"
                f" - {outcome.get('awayTeamPenaltiesScored')}"
            )

        return {
            "uid": item["id"],
            "starttime": start,
            "endtime": end,
            "summary": f"{(item.get('homeTeam') or {}).get('name')} - "
            f"{(item.get('awayTeam') or {}).get('name')}",
            "location": self._details.get(item["id"], {}).get("location"),
            "description": description,
        }


def _parse_detail(detail: dict | None) -> dict[str, str | None]:
    if not detail:
        return {"location": None, "referee": None}

    location = None
    loc = detail.get("location")
    if loc:
        location = f"{loc.get('address')}\n{loc.get('postalCode')} {loc.get('city')}\nBelgium"

    referee = None
    for official in detail.get("officials") or []:
        if official.get("function") == "referee":
            referee = f"{official.get('firstName')} {official.get('lastName')}"
            break

    return {"location": location, "referee": referee}


def _calendar_referee(item: dict) -> str | None:
    """The calendar lists officials without function; only trust a single one."""
    officials = item.get("officials") or []
    if len(officials) == 1:
        return f"{officials[0].get('firstName')} {officials[0].get('lastName')}"
    return None


def _parse_ranking(data: dict | None) -> list[dict]:
    rankings = (data or {}).get("rankings") or []
    if not rankings:
        return []
    return [
        {"position": t.get("position"), "team": t.get("name"), "id": t.get("teamId")}
        for t in rankings[0].get("teams") or []
    ]


def _person_name(person: dict) -> str:
    """RBFA lists people as upper-case LASTNAME FIRSTNAME; make it readable."""
    first = (person.get("firstName") or "").strip().title()
    last = (person.get("lastName") or "").strip().title()
    return f"{first} {last}".strip()


def _parse_squad(data: dict | None) -> dict[str, list[dict]]:
    data = data or {}
    players = []
    for player in data.get("players") or []:
        stats = player.get("statistics") or {}
        players.append(
            {
                "name": _person_name(player),
                "matches": stats.get("numberOfMatches") or 0,
                "goals": stats.get("numberOfGoals") or 0,
            }
        )

    staff = []
    for member in data.get("staff") or []:
        function = member.get("function") or []
        if isinstance(function, str):
            function = [function]
        staff.append({"name": _person_name(member), "function": ", ".join(function)})

    return {"players": players, "staff": staff}
