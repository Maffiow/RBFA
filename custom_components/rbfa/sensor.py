"""Platform for sensor integration."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry

from .const import CONF_SHOW_REFEREE, DOMAIN, get_option
from .coordinator import MyCoordinator
from .entity import RbfaEntity

SENSORS = (
    SensorEntityDescription(
        key="starttime",
        translation_key="starttime",
        device_class = SensorDeviceClass.TIMESTAMP,
    ),
    SensorEntityDescription(
        key="endtime",
        translation_key="endtime",
        device_class = SensorDeviceClass.TIMESTAMP,
    ),
    SensorEntityDescription(
        key="hometeam",
        translation_key="hometeam",
    ),
    SensorEntityDescription(
        key="awayteam",
        translation_key="awayteam",
    ),
    SensorEntityDescription(
        key="location",
        translation_key="location",
        icon="mdi:soccer-field",
    ),
    SensorEntityDescription(
        key="series",
        translation_key="series",
        icon="mdi:table-row",
    ),
    SensorEntityDescription(
        key="referee",
        translation_key="referee",
        icon="mdi:whistle",
    ),
    SensorEntityDescription(
        key="matchid",
        translation_key="matchid",
        icon="mdi:soccer",
    ),
)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up RBFA sensors based on a config entry."""
    coordinator: MyCoordinator = entry.runtime_data
    show_referee = get_option(entry, CONF_SHOW_REFEREE, True)

    async_add_entities(
        RbfaSensor(coordinator, description, collection)
        for description in SENSORS
        if show_referee or description.key != "referee"
        for collection in ("upcoming", "lastmatch")
    )


class RbfaSensor(RbfaEntity, SensorEntity):
    """Sensor showing one field of the upcoming or last match."""

    _attr_entity_registry_enabled_default = False
    # Squads are large and rarely change; keep them out of the recorder.
    _unrecorded_attributes = frozenset({"squads"})

    def __init__(
        self,
        coordinator: MyCoordinator,
        description: SensorEntityDescription,
        collection: str,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self.collection = collection
        self.team = coordinator.team
        self._attr_unique_id = f"{DOMAIN}_{collection}_{description.key}_{self.team}"

    @property
    def _match(self) -> dict | None:
        return (self.coordinator.data or {}).get(self.collection)

    @property
    def native_value(self):
        match = self._match
        if match is not None:
            return match.get(self.entity_description.key)
        return None

    @property
    def entity_picture(self) -> str | None:
        match = self._match
        if match is None:
            return None

        key = self.entity_description.key
        if key in ("hometeam", "awayteam"):
            return match.get(f"{key}logo")
        if key == "series" and match.get("channel"):
            logo = match["channel"].upper()
            return f"https://www.rbfa.be/assets/img/icons/organisers/Logo{logo}.svg"
        return None

    @property
    def extra_state_attributes(self):
        """Return attributes for sensor."""
        attributes = {"baseid": self.team, "tag": self.collection}
        match = self._match
        if match is None:
            return attributes

        key = self.entity_description.key
        if key in ("hometeam", "awayteam"):
            for field in ("id", "goals", "penalties", "position"):
                value = match.get(f"{key}{field}")
                if value is not None:
                    attributes[field] = value

        if key == "series" and match.get("ranking"):
            attributes["ranking"] = match["ranking"]
            if match.get("squads"):
                attributes["squads"] = match["squads"]

        return attributes
