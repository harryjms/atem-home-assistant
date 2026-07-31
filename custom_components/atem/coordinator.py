"""Push hub that owns the PyATEMMax connection to an ATEM switcher.

This is intentionally *not* a polling ``DataUpdateCoordinator``. PyATEMMax keeps
the switcher state up to date on its own worker thread and emits callbacks, so we
model a thin push hub:

* all blocking library calls run in the executor
  (``hass.async_add_executor_job``);
* library callbacks fire on PyATEMMax's thread, so they are marshalled back onto
  the event loop with ``hass.loop.call_soon_threadsafe`` before touching HA;
* entities subscribe to a dispatcher signal and re-read the (in-memory) state.

All access to the ``PyATEMMax.ATEMMax`` instance is centralised here so that any
future correction to a library symbol name is a one-line change.
"""

from __future__ import annotations

from collections.abc import Iterator
import logging
from typing import TYPE_CHECKING

import PyATEMMax

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import CONNECTION_TIMEOUT, MANUFACTURER, UPDATE_DEBOUNCE, signal_update

if TYPE_CHECKING:
    from . import AtemConfigEntry

_LOGGER = logging.getLogger(__name__)


class AtemConnection:
    """Owns the PyATEMMax instance and pushes updates into Home Assistant."""

    def __init__(self, hass: HomeAssistant, entry: AtemConfigEntry) -> None:
        """Initialise the hub and register library event callbacks."""
        self.hass = hass
        self.entry = entry
        self.host: str = entry.data["host"]
        self.switcher = PyATEMMax.ATEMMax()
        self.signal = signal_update(entry.entry_id)
        self._dispatch_scheduled = False

        # Registering callbacks does no network I/O, so it is safe on the loop.
        # verify: event name strings live on switcher.atem.events (connect /
        # disconnect / receive), confirmed against PyATEMMax 1.0b9 source.
        events = self.switcher.atem.events
        self.switcher.registerEvent(events.connect, self._on_connect)
        self.switcher.registerEvent(events.disconnect, self._on_disconnect)
        self.switcher.registerEvent(events.receive, self._on_receive)

    # -- Connection lifecycle -------------------------------------------------

    async def async_connect(self) -> bool:
        """Connect and wait for the initial handshake. Returns success."""
        return await self.hass.async_add_executor_job(self._connect_blocking)

    def _connect_blocking(self) -> bool:
        """Blocking connect + handshake wait. Runs in the executor."""
        self.switcher.connect(self.host)
        # verify: waitForConnection defaults to infinite=True; we must pass
        # infinite=False so the timeout is honoured (PyATEMMax 1.0b9).
        return self.switcher.waitForConnection(
            infinite=False, timeout=CONNECTION_TIMEOUT
        )

    async def async_disconnect(self) -> None:
        """Tear down the connection."""
        await self.hass.async_add_executor_job(self.switcher.disconnect)

    @property
    def connected(self) -> bool:
        """Return whether the switcher is currently connected."""
        return bool(self.switcher.connected)

    # -- Library callbacks (run on the PyATEMMax thread) ----------------------

    def _on_connect(self, _params: dict) -> None:
        self.hass.loop.call_soon_threadsafe(self._async_dispatch_now)

    def _on_disconnect(self, _params: dict) -> None:
        self.hass.loop.call_soon_threadsafe(self._async_dispatch_now)

    def _on_receive(self, _params: dict) -> None:
        # "receive" fires per packet; coalesce into one debounced dispatch.
        self.hass.loop.call_soon_threadsafe(self._async_schedule_dispatch)

    @callback
    def _async_schedule_dispatch(self) -> None:
        """Schedule a debounced dispatch (event loop only)."""
        if self._dispatch_scheduled:
            return
        self._dispatch_scheduled = True
        self.hass.loop.call_later(UPDATE_DEBOUNCE, self._async_dispatch_now)

    @callback
    def _async_dispatch_now(self) -> None:
        """Notify all subscribed entities (event loop only)."""
        self._dispatch_scheduled = False
        async_dispatcher_send(self.hass, self.signal)

    # -- Device metadata ------------------------------------------------------

    @property
    def model(self) -> str:
        """Return the switcher model reported by the switcher."""
        # verify: atemModel is populated after handshake (PyATEMMax 1.0b9).
        return self.switcher.atemModel or "ATEM"

    # -- Topology accessors ---------------------------------------------------

    @property
    def mix_effect_count(self) -> int:
        """Return the number of M/E units."""
        return int(self.switcher.topology.mEs)

    @property
    def dsk_count(self) -> int:
        """Return the number of downstream keyers."""
        return int(self.switcher.topology.downstreamKeyers)

    def keyer_count(self, me: int) -> int:
        """Return the number of upstream keyers on an M/E."""
        # verify: per-M/E upstream keyer count lives at mixEffect.config[me].keyers.
        return int(self.switcher.mixEffect.config[me].keyers)

    # -- Inputs ---------------------------------------------------------------

    def _iter_video_sources(self) -> Iterator[tuple[int, str]]:
        """Yield (source_value, long_name) for every populated input."""
        for source in self.switcher.atem.videoSources:
            props = self.switcher.inputProperties[source]
            long_name = props.longName
            if long_name:
                yield int(source.value), long_name

    def available_inputs(self) -> list[tuple[int, str]]:
        """Return a stable list of (source_value, long_name) for the switcher."""
        return sorted(self._iter_video_sources(), key=lambda item: item[0])

    def input_name(self, source_value: int) -> str | None:
        """Return the long name for a video source value, if known."""
        props = self.switcher.inputProperties[source_value]
        return props.longName or None

    # -- Program / preview ----------------------------------------------------

    def program_source(self, me: int) -> int:
        """Return the current program input value for an M/E."""
        return int(self.switcher.programInput[me].videoSource.value)

    def preview_source(self, me: int) -> int:
        """Return the current preview input value for an M/E."""
        return int(self.switcher.previewInput[me].videoSource.value)

    async def async_set_program(self, me: int, source_value: int) -> None:
        """Set the program input for an M/E."""
        await self.hass.async_add_executor_job(
            self.switcher.setProgramInputVideoSource, me, source_value
        )

    async def async_set_preview(self, me: int, source_value: int) -> None:
        """Set the preview input for an M/E."""
        await self.hass.async_add_executor_job(
            self.switcher.setPreviewInputVideoSource, me, source_value
        )

    # -- MultiViewers ---------------------------------------------------------

    @property
    def multiviewer_count(self) -> int:
        """Return the number of multiviewers reported by the switcher."""
        # verify: multiviewer count is *not* part of topology; PyATEMMax 1.0b9
        # reports it separately at multiViewer.config.multiViewers (_handle_MvC).
        # Some models/firmware leave this unset (None) even when connected, so
        # fall back to 0 rather than raising during platform setup.
        try:
            return int(self.switcher.multiViewer.config.multiViewers)
        except (TypeError, ValueError):
            return 0

    def multiview_window_count(self, mv: int) -> int:
        """Return the number of routable windows reported for a multiviewer."""
        # verify: window count is not reported directly. PyATEMMax populates a
        # window's videoSource only for windows the switcher advertises (via
        # MvIn), so we count windows that have a reported source. ATEMWindows
        # tops out at 10, which is also the library's multiview window ceiling.
        count = 0
        for window in self.switcher.atem.windows:
            try:
                source = self.switcher.multiViewer.input[mv][window].videoSource
            except (KeyError, IndexError, AttributeError):
                continue
            if source.value is not None:
                count += 1
        return count

    def multiview_layouts(self) -> list[tuple[str, str]]:
        """Return (option_value, label) for every multiview layout."""
        # verify: layout enum is ATEMMultiViewerLayouts, exposed as
        # switcher.atem.multiViewerLayouts (top/bottom/left/right).
        return [
            (layout.name, layout.name.capitalize())
            for layout in self.switcher.atem.multiViewerLayouts
        ]

    def multiview_layout(self, mv: int) -> str | None:
        """Return the current layout name for a multiviewer, if known."""
        # verify: live layout state is at multiViewer.properties[mv].layout,
        # an ATEMConstant whose .name matches a multiViewerLayouts member.
        return self.switcher.multiViewer.properties[mv].layout.name or None

    async def async_set_multiview_layout(self, mv: int, option: str) -> None:
        """Set the layout for a multiviewer."""
        # setMultiViewerPropertiesLayout accepts the layout name string or value.
        await self.hass.async_add_executor_job(
            self.switcher.setMultiViewerPropertiesLayout, mv, option
        )

    def multiview_window_source(self, mv: int, window: int) -> int | None:
        """Return the current video source value for a multiview window."""
        # verify: live window source is at
        # multiViewer.input[mv][window].videoSource (an ATEMConstant).
        source = self.switcher.multiViewer.input[mv][window].videoSource
        return None if source.value is None else int(source.value)

    async def async_set_multiview_window_source(
        self, mv: int, window: int, source_value: int
    ) -> None:
        """Route a video source to a multiview window."""
        await self.hass.async_add_executor_job(
            self.switcher.setMultiViewerInputVideoSource, mv, window, source_value
        )

    # -- Transitions ----------------------------------------------------------

    async def async_cut(self, me: int) -> None:
        """Perform a cut on an M/E."""
        await self.hass.async_add_executor_job(self.switcher.execCutME, me)

    async def async_auto(self, me: int) -> None:
        """Perform an auto transition on an M/E."""
        await self.hass.async_add_executor_job(self.switcher.execAutoME, me)

    async def async_fade_to_black(self, me: int) -> None:
        """Toggle fade-to-black on an M/E."""
        # verify: FTB trigger is execFadeToBlackME(mE) (not setFadeToBlackME).
        await self.hass.async_add_executor_job(self.switcher.execFadeToBlackME, me)

    def fade_to_black_active(self, me: int) -> bool:
        """Return whether an M/E is fully faded to black."""
        return bool(self.switcher.fadeToBlack[me].state.fullyBlack)

    # -- Upstream keyers ------------------------------------------------------

    def upstream_keyer_on_air(self, me: int, keyer: int) -> bool:
        """Return whether an upstream keyer is on air."""
        return bool(self.switcher.keyer[me][keyer].onAir.enabled)

    async def async_set_upstream_keyer_on_air(
        self, me: int, keyer: int, enabled: bool
    ) -> None:
        """Enable or disable an upstream keyer on air."""
        await self.hass.async_add_executor_job(
            self.switcher.setKeyerOnAirEnabled, me, keyer, enabled
        )

    # -- Downstream keyers ----------------------------------------------------

    def downstream_keyer_on_air(self, dsk: int) -> bool:
        """Return whether a downstream keyer is on air."""
        return bool(self.switcher.downstreamKeyer[dsk].onAir)

    async def async_set_downstream_keyer_on_air(
        self, dsk: int, enabled: bool
    ) -> None:
        """Enable or disable a downstream keyer on air."""
        await self.hass.async_add_executor_job(
            self.switcher.setDownstreamKeyerOnAir, dsk, enabled
        )

    # -- Macros ---------------------------------------------------------------

    def macros(self) -> list[tuple[int, str]]:
        """Return (index, name) for every macro slot that is in use."""
        result: list[tuple[int, str]] = []
        for macro in self.switcher.atem.macros:
            index = int(macro.value)
            # The macros list contains a sentinel "stop" entry (0xFFFF).
            if index < 0 or index > 0xFF:
                continue
            props = self.switcher.macro.properties[macro]
            if props.isUsed:
                name = props.name or f"Macro {index + 1}"
                result.append((index, name))
        return sorted(result, key=lambda item: item[0])

    async def async_run_macro(self, index: int) -> None:
        """Run a macro by index."""
        # verify: no execMacroRun in 1.0b9; run a macro via
        # setMacroAction(index, "runMacro") (ATEMMacroActions.runMacro).
        await self.hass.async_add_executor_job(
            self.switcher.setMacroAction, index, "runMacro"
        )


async def async_probe(hass: HomeAssistant, host: str) -> str:
    """Attempt a connection for the config flow; return the model name.

    Raises ``asyncio.TimeoutError``-like failure as ``ConnectionError`` if the
    handshake does not complete.
    """

    def _probe() -> str:
        switcher = PyATEMMax.ATEMMax()
        try:
            switcher.connect(host)
            if not switcher.waitForConnection(
                infinite=False, timeout=CONNECTION_TIMEOUT
            ):
                raise ConnectionError(f"Timed out connecting to ATEM at {host}")
            return switcher.atemModel or MANUFACTURER
        finally:
            switcher.disconnect()

    return await hass.async_add_executor_job(_probe)
