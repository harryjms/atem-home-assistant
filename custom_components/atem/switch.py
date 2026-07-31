"""On-air keyer switches for the Blackmagic ATEM integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
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
    """Set up upstream and downstream keyer on-air switches."""
    connection = entry.runtime_data

    entities: list[SwitchEntity] = []

    for me in range(connection.mix_effect_count):
        for keyer in range(connection.keyer_count(me)):
            entities.append(AtemUpstreamKeyerSwitch(connection, me, keyer))

    for dsk in range(connection.dsk_count):
        entities.append(AtemDownstreamKeyerSwitch(connection, dsk))

    async_add_entities(entities)


class AtemUpstreamKeyerSwitch(AtemEntity, SwitchEntity):
    """On-air toggle for an upstream keyer."""

    def __init__(
        self, connection: AtemConnection, me: int, keyer: int
    ) -> None:
        """Initialise an upstream keyer switch."""
        super().__init__(connection)
        self._me = me
        self._keyer = keyer
        self._attr_translation_key = "upstream_keyer"
        self._attr_translation_placeholders = {
            "me": str(me + 1),
            "keyer": str(keyer + 1),
        }
        self._attr_unique_id = (
            f"{connection.entry.entry_id}_me{me}_usk{keyer}"
        )

    @property
    def is_on(self) -> bool:
        """Return whether the keyer is on air."""
        return self.connection.upstream_keyer_on_air(self._me, self._keyer)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Put the keyer on air."""
        await self.connection.async_set_upstream_keyer_on_air(
            self._me, self._keyer, True
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Take the keyer off air."""
        await self.connection.async_set_upstream_keyer_on_air(
            self._me, self._keyer, False
        )


class AtemDownstreamKeyerSwitch(AtemEntity, SwitchEntity):
    """On-air toggle for a downstream keyer."""

    def __init__(self, connection: AtemConnection, dsk: int) -> None:
        """Initialise a downstream keyer switch."""
        super().__init__(connection)
        self._dsk = dsk
        self._attr_translation_key = "downstream_keyer"
        self._attr_translation_placeholders = {"dsk": str(dsk + 1)}
        self._attr_unique_id = f"{connection.entry.entry_id}_dsk{dsk}"

    @property
    def is_on(self) -> bool:
        """Return whether the downstream keyer is on air."""
        return self.connection.downstream_keyer_on_air(self._dsk)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Put the downstream keyer on air."""
        await self.connection.async_set_downstream_keyer_on_air(self._dsk, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Take the downstream keyer off air."""
        await self.connection.async_set_downstream_keyer_on_air(self._dsk, False)
