"""Program and preview input selects for the Blackmagic ATEM integration."""

from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import AtemConfigEntry
from .coordinator import AtemConnection
from .entity import AtemEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AtemConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up program/preview and multiview selects."""
    connection = entry.runtime_data

    entities: list[SelectEntity] = []
    for me in range(connection.mix_effect_count):
        entities.append(AtemInputSelect(connection, me, bus="program"))
        entities.append(AtemInputSelect(connection, me, bus="preview"))

    # Multiview support is best-effort: some models/firmware do not report
    # multiviewer topology the way PyATEMMax expects. Never let that take down
    # the core program/preview selects.
    try:
        for mv in range(connection.multiviewer_count):
            entities.append(AtemMultiviewLayoutSelect(connection, mv))
            for window in range(connection.multiview_window_count(mv)):
                entities.append(AtemMultiviewWindowSelect(connection, mv, window))
    except Exception:  # noqa: BLE001 - guard against unexpected switcher state
        _LOGGER.warning(
            "Could not set up ATEM multiview selects; skipping them",
            exc_info=True,
        )

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


class AtemMultiviewLayoutSelect(AtemEntity, SelectEntity):
    """Selects the window layout of a multiviewer."""

    def __init__(self, connection: AtemConnection, mv: int) -> None:
        """Initialise a layout select for a multiviewer."""
        super().__init__(connection)
        self._mv = mv
        self._attr_translation_key = "multiview_layout"
        self._attr_translation_placeholders = {"mv": str(mv + 1)}
        self._attr_unique_id = f"{connection.entry.entry_id}_mv{mv}_layout"

    @property
    def options(self) -> list[str]:
        """Return the layout names offered by the switcher."""
        return [value for value, _label in self.connection.multiview_layouts()]

    @property
    def current_option(self) -> str | None:
        """Return the active layout name."""
        return self.connection.multiview_layout(self._mv)

    async def async_select_option(self, option: str) -> None:
        """Apply the selected layout to this multiviewer."""
        await self.connection.async_set_multiview_layout(self._mv, option)


class AtemMultiviewWindowSelect(AtemEntity, SelectEntity):
    """Selects the input source shown in a multiviewer window."""

    def __init__(self, connection: AtemConnection, mv: int, window: int) -> None:
        """Initialise a source select for a multiviewer window."""
        super().__init__(connection)
        self._mv = mv
        self._window = window
        self._attr_translation_key = "multiview_window"
        self._attr_translation_placeholders = {
            "mv": str(mv + 1),
            "window": str(window + 1),
        }
        self._attr_unique_id = (
            f"{connection.entry.entry_id}_mv{mv}_window{window}_source"
        )

    @property
    def options(self) -> list[str]:
        """Return the input long names offered by the switcher."""
        return [name for _value, name in self.connection.available_inputs()]

    @property
    def current_option(self) -> str | None:
        """Return the input long name shown in this window."""
        source = self.connection.multiview_window_source(self._mv, self._window)
        if source is None:
            return None
        return self.connection.input_name(source)

    async def async_select_option(self, option: str) -> None:
        """Route the selected input into this window."""
        for value, name in self.connection.available_inputs():
            if name == option:
                await self.connection.async_set_multiview_window_source(
                    self._mv, self._window, value
                )
                return
