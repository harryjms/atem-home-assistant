"""Buttons for the Blackmagic ATEM integration (Cut, Auto, FTB, macros)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from homeassistant.components.button import ButtonEntity
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
    """Set up transition and macro buttons."""
    connection = entry.runtime_data

    entities: list[ButtonEntity] = []

    for me in range(connection.mix_effect_count):
        entities.append(
            AtemTransitionButton(
                connection, me, "cut", connection.async_cut
            )
        )
        entities.append(
            AtemTransitionButton(
                connection, me, "auto", connection.async_auto
            )
        )
        entities.append(
            AtemTransitionButton(
                connection, me, "ftb", connection.async_fade_to_black
            )
        )

    for index, name in connection.macros():
        entities.append(AtemMacroButton(connection, index, name))

    async_add_entities(entities)


class AtemTransitionButton(AtemEntity, ButtonEntity):
    """A Cut / Auto / Fade-to-black button for an M/E."""

    def __init__(
        self,
        connection: AtemConnection,
        me: int,
        action: str,
        handler: Callable[[int], Awaitable[None]],
    ) -> None:
        """Initialise a transition button."""
        super().__init__(connection)
        self._me = me
        self._handler = handler
        self._attr_translation_key = action
        self._attr_translation_placeholders = {"me": str(me + 1)}
        self._attr_unique_id = f"{connection.entry.entry_id}_me{me}_{action}"

    async def async_press(self) -> None:
        """Execute the transition action."""
        await self._handler(self._me)


class AtemMacroButton(AtemEntity, ButtonEntity):
    """Runs a stored macro on the switcher."""

    def __init__(
        self, connection: AtemConnection, index: int, name: str
    ) -> None:
        """Initialise a macro button."""
        super().__init__(connection)
        self._index = index
        self._attr_translation_key = "macro"
        self._attr_translation_placeholders = {"name": name}
        self._attr_unique_id = f"{connection.entry.entry_id}_macro{index}"

    async def async_press(self) -> None:
        """Run the macro."""
        await self.connection.async_run_macro(self._index)
