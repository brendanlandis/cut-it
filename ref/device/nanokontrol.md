<!-- schema: device -->
# Korg nanoKONTROL (mk1)

**Files:** `Cut It/m_nano.pd`, `Cut It/m_nano.lua`, `Cut It/m_nano-lua.pd_lua` · **Gate:** `test/gate/nano-assert.sh` · **Checklist:** `test/checklists/nanokontrol.md`

The rig's fader bank. What the device is, the CC numbers it sends as configured, its configuration,
LEDs and traps are in Reference: `~/Sites/!reference/korg-nanokontrol-mk1.md`. This page is how Cut It
uses it.

**Pd cannot light anything here**, which is why every button is momentary and all visible state lives
on the Launchpad or the OLED.

`m_nano.pd` takes its Pd channel block as a creation argument and decodes every control onto
`param`. It posts no row of its own: what the OLED shows for a control is `u_map`'s — the
destination's row when the mode maps it, the raw row when nothing does. See
[map.md](../module/map.md), item 317.

## Design

### Channels and decoding

| Control | CC | Pd channel | `div 10` | `mod 10` | Evidence | Item |
|---------|----|------------|----------|----------|----------|------|
| Sliders 1–9 | 1–9 | 17 | 0 | channel | verified | 31 |
| Knobs 1–9 | 11–19 | 17 | 1 | channel | verified | 31 |
| Buttons, top row 1–9 | 21–29 | 17 | 2 | channel | verified | 31 |
| Buttons, bottom row 1–9 | 31–39 | 17 | 3 | channel | verified | 31 |
| Transport ×6 | 41–46 | **18** | 4 | button, left to right | verified | 31 |

Through the real patch, slider 1 → CC 1 … PLAY → CC 42 and LOOP → CC 44 on Pd channel 18.

### Transport buttons in the patch

**`m_nano` treats all six as ordinary momentary buttons** — `xport-1`…`xport-6` on press, no
toggle — and names them by physical position, because what a control *means* is not knowable at the
`m_` layer.

**Mode selection is the Launchpad's left column**, where the lit lamp already is — see
[map.md](../module/map.md).

✅ `xport-2` is **PLAY** and drives `start`; `xport-5` is **STOP** and drives `stop`, on every
page. The Organelle's `aux` is the keyboard's modifier, not a transport — see
[organelle.md](organelle.md).

⚠️ **The other four report a raw row on the OLED**, because they fall through to the table and miss
it: item 242's rule, and correct, since a control that does nothing and says nothing cannot be told
from a broken one. **REW, FF, LOOP and REC are four free controls for v0.4.**

Because CC 41–46 give `div 10` = 4, `m_nano` folds the row in as a **fifth control kind** and reads
both channels through one path.

### Presence

`m_nano` registers as `active` on the presence bus and is polled every two seconds with a universal
device inquiry. **The nano answers** — manufacturer byte `42`, KORG, item 249 — so `[c_devid 66]`
inside `m_nano` is what tells its reply apart from the Launchpad's on the one SysEx stream the
whole patch shares. ⚠️ **The argument is decimal and the byte is hex**: `42` is 66.

Any CC landing in this file's own channel block counts as liveness as well, so a nano being *played*
stays present even if one reply is dropped. The inquiry leaves on **port 2**, derived as
`(17-1)/16+1` from the channel block this file already takes as its one argument rather than passed
in separately. See [presence.md](../module/presence.md).

### The CC numbers collide with the Volca's parameter range

The nano's transport row is CC 41–46; the Volca's parameters are CC 40–50.

**Fix:** nothing to do — harmless. The Volca is device 4 on channel 49+, the nano is device 2, and
Pd separates by channel long before a CC number is examined. Recorded so the collision is not
mistaken for a bug.

### Moved off the factory map

The regular CC layout (sliders 1–9, knobs 11–19, buttons 21–29 and 31–39) is what lets the tens and
units digits decode the entire surface, with no table to keep by hand. Reading the factory assignment would have
needed `[sysexin]` and a byte-matching state machine if it was MMC, which Reference explains.

### Momentary only — the host cannot reach the LEDs

⚠️ **A dark nanoKONTROL is correct and expected**, and it is not evidence of a fault, a missing wire,
or an unfinished feature. Set to **Toggle**, a button's LED would latch and desync silently (Reference),
so every button is configured momentary and **Pd owns all state**. This is the single decision the
whole nano configuration rests on.

### `[ctlin]`'s outlet order

Trigger off the **value** outlet, which fires last — a Pd fact, in `~/Sites/!reference/pure-data.md`
(item 23).

### The decode is Lua

**`m_nano.lua` decodes a CC, and `m_nano.pd` decides which CCs it sees.** The Lua answers
`<controller> <value>` with the control's name and value, a button's press as 1 and its release as
nothing, or `warn m_nano cc-N-unmapped` for a CC with no kind, as plain Lua that runs on the Mac
without Pd. The Pd keeps `[ctlin]`, the two-channel gate, the liveness tap and the device inquiry,
so presence works without the Lua. The same split as the sequencer's and the map's
([sequencer.md](../module/sequencer.md), *The rules in Lua, the timing in Pd*).

| | Evidence |
|---|---|
| **The face**, `m_nano-lua.pd_lua`: inlet 1 `<controller> <value>` from the gate's `[spigot]` and a `[list prepend]` holding the controller, inlet 2 `init` at load; outlet 1 `param`, outlet 2 `err`, outlet 3 a bang on `init` | verified |
| **What it replaced:** three nested subpatches — the decode, its two kind flags and the name in private sends, and the unmapped path that had to clear both flags before warning, or the next value went out under the last control's name. The Lua keeps no state between messages, so that trap is gone rather than guarded | verified |
| **A Lua that never loads** says `fail m_nano no-lua` on `err` at load, and every control on the nano is dead; presence is not. | verified |
| **A rule that throws** says `fail m_nano lua-ctlin`, and the object carries on | verified |
| **Load and memory:** the patch loads in silence in a test Pd on the Organelle, and its peak resident size is 3492 kB against 3480 without the nano's Lua, three runs each (2026-11-03) | verified |
| **Cost per CC:** about 0.07–0.09 ms on the Organelle against the Pd decode's 0.014 — 9000 CCs in 0.64–0.84 s against 0.13 s, in a test Pd niced beside the live one; another device's CC, which the gate refuses before the Lua, costs what it did (2026-11-03) | verified |

**A moving fader is a stream, so this cost is per message.** Every CC the nano sends also passes
through the map's Lua, about 0.33 ms ([map.md](../module/map.md), *Where each part lives*), so the
decode adds about a fifth to a fader's cost: a fast sweep of a few hundred CCs a second takes a few
percent more of the CPU while the hand moves. Pressure, the densest stream on the rig, stays in Pd
([launchpad.md](launchpad.md)).

`test/gate/lua/m_nano_test.lua` tests the decode and the face without Pd, and the nano gate runs it
before its Pd half, which is unchanged since the decode was Pd. Edit the rules in
`Cut It/m_nano.lua`; `; pdluax reload m_nano-lua` re-reads them in a running Pd.

## Open

**Nothing.** The one long-standing question — what the transport buttons shipped with — is a
**permanent limitation** rather than an unknown, and is stated as one in Reference, under *A
factory reset destroys the map*. Item 267.
