"""Calendar platform for the RBFA integration."""
from __future__ import annotations

from datetime import datetime

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_ALT_NAME, DOMAIN, get_option
from .coordinator import MyCoordinator
from .entity import RbfaEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the RBFA team calendar."""
    async_add_entities([TeamCalendar(entry.runtime_data, entry)])


def _to_event(item: dict) -> CalendarEvent:
    return CalendarEvent(
        uid=item["uid"],
        summary=item["summary"],
        start=item["starttime"],
        end=item["endtime"],
        location=item["location"],
        description=item["description"],
    )


class TeamCalendar(RbfaEntity, CalendarEntity):
    """Calendar with all matches of a RBFA team."""

    _attr_icon = "mdi:soccer"
    _attr_has_entity_name = False

    def __init__(self, coordinator: MyCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{DOMAIN}_calendar_{coordinator.team}"

    @property
    def name(self) -> str:
        alt_name = get_option(self._entry, CONF_ALT_NAME)
        if alt_name:
            return alt_name
        team = (self.coordinator.data or {}).get("team")
        if team:
            return f"{team.get('clubName')} | {team.get('name')}"
        return f"{DOMAIN} {self.coordinator.team}"

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming match."""
        upcoming = (self.coordinator.data or {}).get("upcoming")
        if upcoming is None:
            return None
        return CalendarEvent(
            uid=upcoming["matchid"],
            summary=f"{upcoming['hometeam']} - {upcoming['awayteam']}",
            start=upcoming["starttime"],
            end=upcoming["endtime"],
            location=upcoming["location"],
            description=upcoming["series"],
        )

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Return the matches that overlap the requested period."""
        return [
            _to_event(item)
            for item in (self.coordinator.data or {}).get("events", [])
            if item["endtime"] > start_date and item["starttime"] < end_date
        ]
