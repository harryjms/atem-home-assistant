"""Connectivity binary sensor for the Blackmagic ATEM integration."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import AtemConfigEntry
from .coordinator import AtemConnection
from .entity import AtemEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AtemConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the connectivity binary sensor."""
    async_add_entities([AtemConnectivitySensor(entry.runtime_data)])


class AtemConnectivitySensor(AtemEntity, BinarySensorEntity):
    """Reports whether the switcher is connected.

    This entity stays available even while disconnected so the connection
    status itself is always observable.
    """

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_translation_key = "connectivity"
    _attr_entity_registry_enabled_default = True

    def __init__(self, connection: AtemConnection) -> None:
        """Initialise the connectivity sensor."""
        super().__init__(connection)
        self._attr_unique_id = f"{connection.entry.entry_id}_connectivity"

    @property
    def available(self) -> bool:
        """Connectivity status is always available."""
        return True

    @property
    def is_on(self) -> bool:
        """Return True when the switcher is connected."""
        return self.connection.connected
