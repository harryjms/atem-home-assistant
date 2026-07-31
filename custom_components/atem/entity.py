"""Base entity for the Blackmagic ATEM integration."""

from __future__ import annotations

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity

from .const import DOMAIN, MANUFACTURER
from .coordinator import AtemConnection


class AtemEntity(Entity):
    """Base entity that subscribes to the push hub for state updates."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, connection: AtemConnection) -> None:
        """Initialise common attributes and the device registry entry."""
        self.connection = connection
        entry = connection.entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer=MANUFACTURER,
            model=connection.model,
        )

    @property
    def available(self) -> bool:
        """Return whether the switcher is reachable."""
        return self.connection.connected

    async def async_added_to_hass(self) -> None:
        """Subscribe to push updates from the hub."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, self.connection.signal, self._handle_update
            )
        )

    @callback
    def _handle_update(self) -> None:
        """Write updated state when the hub reports a change."""
        self.async_write_ha_state()
