# Blackmagic ATEM — Home Assistant

A Home Assistant custom integration to control a Blackmagic Design ATEM video
switcher, distributed via [HACS](https://hacs.xyz/). The component lives under
`custom_components/atem/`.

Control a Blackmagic Design ATEM video switcher from Home Assistant over the
local network. The integration uses [PyATEMMax](https://pypi.org/project/PyATEMMax/)
as the protocol layer (UDP port 9910) and pushes live state into Home Assistant,
so entity states follow changes made from the ATEM Software Control panel,
hardware panels, or other controllers.

> **Note on the protocol.** The ATEM control protocol is **unofficial** and has
> been reverse-engineered. Available features, model topology (number of M/Es,
> keyers, macros), and exact behaviour vary by switcher model and firmware. Treat
> this integration as best-effort and verify against your specific hardware.

### What it does

On setup the integration connects to the switcher, reads its topology, and
creates entities dynamically based on what the switcher actually reports
(number of M/Es, inputs, upstream/downstream keyers, and stored macros).
Models that report zero of something simply get no entities for it.

### Entities

| Platform | Entity | Notes |
| --- | --- | --- |
| `select` | Program input (per M/E) | Options are the switcher's input long names; selecting routes the source to program. |
| `select` | Preview input (per M/E) | As above, for the preview bus. |
| `button` | Cut (per M/E) | Performs a cut. |
| `button` | Auto (per M/E) | Performs an auto transition. |
| `button` | Fade to black (per M/E) | Triggers fade-to-black. |
| `button` | Macro | One button per stored macro; pressing runs the macro. |
| `switch` | Upstream keyer on air | One per upstream keyer per M/E; reflects and controls on-air state. |
| `switch` | Downstream keyer on air | One per downstream keyer; reflects and controls on-air state. |
| `binary_sensor` | Connectivity | `connectivity` device class; stays available even while disconnected. |

All entities (except the connectivity sensor) become unavailable when the
switcher is unreachable, and update automatically as the switcher's state
changes.

### Installation (HACS custom repository)

1. In Home Assistant, open **HACS → Integrations**.
2. Use the overflow menu (three dots) → **Custom repositories**.
3. Add `https://github.com/harryjms/atem-home-assistant` with category
   **Integration**.
4. Install **Blackmagic ATEM** and restart Home Assistant.

Alternatively, copy `custom_components/atem/` into your Home Assistant
`config/custom_components/` directory and restart.

### Configuration

1. Go to **Settings → Devices & services → Add integration**.
2. Search for **Blackmagic ATEM**.
3. Enter the switcher's **IP address** (and, optionally, a name). Home Assistant
   connects to confirm the switcher is reachable before finishing setup.

The switcher must be reachable from the Home Assistant host on UDP port 9910.

### Limitations

- Requires a routable IP; the ATEM protocol has no authentication.
- Only one controller "session" per client — the library maintains its own
  connection and auto-reconnects.
- Feature coverage is intentionally focused (program/preview, transitions,
  keyers, macros). Audio, media players, SuperSource, camera control, and other
  advanced features are not (yet) exposed.
