"""Constants for the Blackmagic ATEM integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "atem"

# Config keys
CONF_HOST: Final = "host"
CONF_NAME: Final = "name"

# Defaults
DEFAULT_NAME: Final = "Blackmagic ATEM"

# PyATEMMax control port (UDP). Informational only; the library defaults to this.
DEFAULT_PORT: Final = 9910

# Seconds to wait for the initial handshake before giving up.
CONNECTION_TIMEOUT: Final = 10.0

# Manufacturer shown in the device registry.
MANUFACTURER: Final = "Blackmagic Design"

# Debounce window (seconds) for coalescing the frequent "receive" callbacks
# into a single Home Assistant state update.
UPDATE_DEBOUNCE: Final = 0.2


def signal_update(entry_id: str) -> str:
    """Return the dispatcher signal used to push state updates for an entry."""
    return f"{DOMAIN}_{entry_id}_update"
