"""Program and preview input selects for the Blackmagic ATEM integration."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
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
    """Set up program/preview selects for each M/E."""
    connection = entry.runtime_data

    entities: list[AtemInputSelect] = []
    for me in range(connection.mix_effect_count):
        entities.append(AtemInputSelect(connection, me, bus="program"))
        entities.append(AtemInputSelect(connection, me, bus="preview"))

    async_add_entities(entities)


class AtemInputSelect(AtemEntity, SelectEntity):
    """Selects the program or preview input source on an M/E."""

    def __init__(self, connection: AtemConnection, me: int, bus: str) -> None:
        """Initialise a program or preview select for an M/E."""
        super().__init__(connection)
        self._me = me
        self._bus = bus
        self._attr_translation_key = f"{bus}_input"
        self._attr_translation_placeholders = {"me": str(me + 1)}
        self._attr_unique_id = f"{connection.entry.entry_id}_me{me}_{bus}_input"

    @property
    def options(self) -> list[str]:
        """Return the input long names offered by the switcher."""
        return [name for _value, name in self.connection.available_inputs()]

    @property
    def current_option(self) -> str | None:
        """Return the currently routed input long name."""
        if self._bus == "program":
            source = self.connection.program_source(self._me)
        else:
            source = self.connection.preview_source(self._me)
        return self.connection.input_name(source)

    async def async_select_option(self, option: str) -> None:
        """Route the selected input to this bus."""
        for value, name in self.connection.available_inputs():
            if name == option:
                if self._bus == "program":
                    await self.connection.async_set_program(self._me, value)
                else:
                    await self.connection.async_set_preview(self._me, value)
                return
