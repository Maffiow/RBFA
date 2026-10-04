"""Base entity for the RBFA integration."""
from __future__ import annotations

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import MyCoordinator


class RbfaEntity(CoordinatorEntity[MyCoordinator]):
    """Base class for RBFA entities."""

    _attr_has_entity_name = True
