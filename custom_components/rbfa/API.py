"""Async client for the RBFA GraphQL API."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import aiohttp

from .const import API_HEADERS, API_URL, HASHES, REQUIRED, VARIABLES

_LOGGER = logging.getLogger(__name__)

TIMEOUT = aiohttp.ClientTimeout(total=20)


class RbfaError(Exception):
    """Generic error talking to the RBFA API."""


class RbfaBlockedError(RbfaError):
    """The request was refused by the RBFA firewall (Akamai)."""


class RbfaApi:
    """Thin wrapper around the persisted GraphQL queries of rbfa.be."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        language: str = "nl",
        min_interval: float = 1.0,
    ) -> None:
        self._session = session
        self._language = language
        self._min_interval = min_interval
        self._lock = asyncio.Lock()
        self._last_request = 0.0

    async def _query(self, operation: str, value: str) -> Any:
        # Space requests out: bursts of calls get the client IP blocked.
        async with self._lock:
            loop = asyncio.get_running_loop()
            wait = self._last_request + self._min_interval - loop.time()
            if wait > 0:
                await asyncio.sleep(wait)
            try:
                return await self._do_query(operation, value)
            finally:
                self._last_request = loop.time()

    async def _do_query(self, operation: str, value: str) -> Any:
        payload = {
            "operationName": operation,
            "variables": {VARIABLES[operation]: value, "language": self._language},
            "extensions": {
                "persistedQuery": {"version": 1, "sha256Hash": HASHES[operation]}
            },
        }
        try:
            async with self._session.post(
                API_URL, json=payload, headers=API_HEADERS, timeout=TIMEOUT
            ) as resp:
                status = resp.status
                content_type = resp.headers.get("Content-Type", "")
                text = await resp.text()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise RbfaError(f"{operation}: connection error: {err!r}") from err

        if "Access Denied" in text[:300]:
            raise RbfaBlockedError(
                f"{operation}: request blocked by the RBFA firewall (Access Denied)"
            )
        if status != 200:
            raise RbfaError(f"{operation}: HTTP {status}")
        if "json" not in content_type:
            raise RbfaError(
                f"{operation}: unexpected {content_type or 'response'}: {text[:100]!r}"
            )

        try:
            body = json.loads(text)
        except ValueError as err:
            raise RbfaError(f"{operation}: invalid JSON: {text[:100]!r}") from err

        data = body.get("data")
        if data is None:
            errors = body.get("errors") or [{}]
            raise RbfaError(f"{operation}: {errors[0].get('message', 'unknown error')}")

        result = data.get(REQUIRED[operation])
        if result is None:
            _LOGGER.debug("%s(%s): no results", operation, value)
        return result

    async def get_team(self, team_id: str) -> dict | None:
        return await self._query("GetTeam", team_id)

    async def get_calendar(self, team_id: str) -> list[dict] | None:
        return await self._query("GetTeamCalendar", team_id)

    async def get_match_detail(self, match_id: str) -> dict | None:
        return await self._query("GetMatchDetail", match_id)

    async def get_rankings(self, series_id: str) -> dict | None:
        return await self._query("GetSeriesRankings", series_id)
