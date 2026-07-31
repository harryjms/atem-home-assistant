"""The Blackmagic ATEM integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .coordinator import AtemConnection

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.SELECT,
    Platform.SWITCH,
]

type AtemConfigEntry = ConfigEntry[AtemConnection]


async def async_setup_entry(hass: HomeAssistant, entry: AtemConfigEntry) -> bool:
    """Set up Blackmagic ATEM from a config entry."""
    connection = AtemConnection(hass, entry)

    if not await connection.async_connect():
        await connection.async_disconnect()
        raise ConfigEntryNotReady(
            f"Timed out connecting to ATEM switcher at {connection.host}"
        )

    entry.runtime_data = connection

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: AtemConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.async_disconnect()
    return unload_ok
