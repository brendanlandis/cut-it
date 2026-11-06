<!-- schema: device -->
# Organelle 1 — the panel, the OLED and the aux LED

**Files:** `Cut It/m_organelle.pd`, `Cut It/m_organelle.lua`, `Cut It/m_organelle-lua.pd_lua`, `Cut It/g_oled.pd`, `Cut It/g_led.pd`, `Cut It/u_mother-stub.pd` · **Gate:** `test/gate/organelle-assert.sh`, `test/gate/led-assert.sh` · **Checklist:** `test/checklists/display.md`

The host device and its own control surface. What the Organelle 1 is — its OS, paths, SSH, the
`mother.pd` interface, the OLED and LED APIs, how it saves, its MIDI quirks and traps, and its wifi —
is in Reference: `~/Sites/!reference/critter-guitari-organelle-1.md`. This page is how Cut It uses its
panel, OLED and aux LED. ([device-os.md](../device-os.md) is how Cut It lives on the box as a computer.)

**The panel is not MIDI** (Reference), so all MIDI in this rig is Pd talking to the four attached
controllers, and the panel is read like any other device: mother's reserved names in, named controls
out. Three abstractions divide it: `m_organelle` reads the panel onto `param`, `g_oled`
owns the screen and is the only file allowed to send `oscOut` or `screenLine*`, and `g_led` owns the
aux LED. The display *arbiter* they share with `g_grid` is instrument architecture, not device fact —
see [display.md](../module/display.md). The reserved names mother uses are enumerated in
[conventions.md](../conventions.md) under *The global name allowlist*.

## Design

### What Cut It puts on the LED

`g_led` owns `led`, and callers send a **state** on the `disp` bus — `led running` — never a color.

| State | `led` | Color | Means | Evidence | Item |
|-------|-------|--------|-------|----------|------|
| `off` | 0 | off | Nothing claims it | verified | — |
| `stopped` | 5 | dark blue | Patch up, transport stopped | verified | — |
| `running` | 3 | green | Transport running | verified | — |
| `panic` | 1 | red | Panic raised — cleared by the next start or stop | verified | — |

Anything `g_led` does not recognize raises `warn g_led unknown-led-state` and **leaves the LED
alone**, so a typo cannot silently blank the only non-screen indicator in the rig.

### `stopped` is lit rather than dark

*(judgment call)* A stopped patch and a dead patch look identical if `stopped` is `off` — and on a
dark stage that is the difference between a pause and a problem.

### Design against the patch-facing LED numbers, not the bitmask

They are the sensible ordering, they are what `[s led]` takes, and they are stable. The bitmask
(Reference) is only interesting for composing a color from components, and that needs the raw path —
`oscOut` — which belongs to `g_oled`.

### `/led/flash` is deliberately unused

mother.pd does not expose it (Reference), so reaching it means sending raw OSC to `oscOut`, and
**only one abstraction may send on that name** — adopting flash would put a second writer on it.
Recorded so it is not rediscovered as news.

### The LED was deliberately not claimed for mode or for saving

The page is on the Launchpad's columns — the surface with sixteen lamps rather than one. A "save in
progress" state was rejected: `Storage → Save` already flips the OLED to mother's own "Saving…"
screen, so the confirmation exists for free.

It remains the cheapest candidate if a *performable* commit is ever added — one row in the state
table and nothing else, since a commit from a Launchpad pad would have no screen of its own.

### `g_oled` repaints screen 3 at 10 Hz under the info bar, which is on

`g_oled` rebuilds screen 3 ten times a second from stored state, and sends `gShowInfoBar 3 1` on
**every** redraw rather than once from `u_init`, because mother repaints after a patch load
(Reference). Rows 0 to 7 are the bar's: mother draws it over whatever is there, so every layer
`g_oled` draws starts at row 8 ([display.md](../module/display.md)).

`gShowInfoBar` toggles mother's VU meters (Reference). **Cut It shows them** (Brendan, 2026-11-04:
"It should show the output the way the organelle usually shows it by default, on a single line,
and with levels at 0 when nothing is playing"). Four 11-segment meters, in L and R and out L and
R, read by mother off the input and off her own `catch~` after the volume knob, so they are the
levels. Cut It's own two bars, the input's until 2026-11-04 and the output's for the rest of that
day, are gone, and `u_level` with them. Battery, power and wifi come with the bar.

This reverses the decision that turned the bar off: that its 11 segments were less legible than
Cut It's own bars, and battery and wifi not worth an eighth of the screen. **What it buys is the
levels on every layer**, a modal, a parameter row or the roster included, where Cut It's bars
showed only on home and as a 5 px strip; and what it costs is rows 0 to 7.

### Anything rhythmic goes on the Launchpad, not the OLED

The OLED trails the audio by ~200 ms (Reference, *The OLED lags the audio by ~200 ms*); the audio
and the Launchpad's playhead agree, and the OLED does not. So a playhead, a beat
indicator or a step position belongs on **the Launchpad**, which `g_grid` repaints over ALSA MIDI at
50 Hz when dirty. The OLED is for state, values and text.

### What `m_organelle` publishes

The front panel is mapped like any other device, with **no notion anywhere in the file of what any
control does.** Same layer and the same silence about meaning as `m_nano`.

| Fact | Evidence | Item |
|------|----------|------|
| The four knobs publish `og-knob-1`…`og-knob-4`, and aux `og-aux 1`, on its press | unknown | 305 |
| **The `og-` prefix is not decoration** — `m_nano` already publishes `knob-1` to `knob-9`, and a single hyphen is not a distinction anyone can be trusted to read inside a `route` box | verified | — |
| **Every knob goes through `[change -1]`**, because mother pushes the knobs once at load and then says nothing (Reference, item 237). Parameter pickup depends on that: if mother streamed, the first value would be spent on its own reading and pickup would never arm | verified | 237 |
| ⛔ **The `-1` is load-bearing.** A bare `[change]` starts life holding 0, so a knob parked at 0 would never publish at all and whatever it feeds would sit at its default. `-1` cannot be a real value, because mother's knobs are 0 to 1 | verified | 237 |
| ⛔ **The knobs reach `param` and NOT `disp`.** A knob's raw 0-to-1 position is not a readable parameter row — `og-knob-1 0.245` where a BPM belongs. `u_map` reports the value instead, because it is the only file that knows what a control MEANS | verified | 242 |
| **`aux` is a press.** Its release publishes nothing | unknown | 305 |
| **The four knobs are the same on every page** (Brendan, 2026-11-06): tempo, last step, track last step and rush ([map.md](../module/map.md)) | unknown | — |

### Aux opens the songs page

**The table gives `og-aux` to `u_voices`, which opens the songs and sections page and closes it again** (Brendan,
2026-11-06; [voices.md](../module/voices.md)). It is no shift: a key under it is the same key. The transport is the
nano's PLAY and STOP, [nanokontrol.md](nanokontrol.md); the diagnostics and test mode are one place, the Launchpad's
Setup, [launchpad.md](launchpad.md); and recover is CC 90 there.

⚠️ **So the panel alone can't ask what died, stop the rig or force a reload**, if the nano and the Launchpad are gone
(Brendan, 2026-11-06). The debug patch, chosen from Organelle's own menu, does the asking
([debug.md](../module/debug.md)).

### The keyboard — 25 controls, one per key

`param` carries exactly one value per control, and mother packs the keyboard into one two-float list
whose lowest key is note 60 (Reference, item 293). So the **pitch rides in the control NAME** and the
velocity is the value.

| Fact | Evidence | Item |
|------|----------|------|
| 25 keys, publishing `og-key-60` … `og-key-84` | verified | 293 |
| The value is that key's **velocity** | verified | 293 |
| ⛔ **A release publishes too, as velocity 0.** A note-off is a real event a destination must act on | verified | 293 |
| They load songs, key N the Nth song of the setlist chosen, and only a press counts (Brendan, 2026-11-05, [songs.md](../module/songs.md)) | unknown | — |
| ⛔ **The keys reach `param` and NOT `disp`** — `g_oled` holds five parameter rows, so a two-handed chord would evict the screen twice per note | verified | 293 |
| …and `u_map` does not report them raw either, which is a deliberate exception to item 242 | verified | 293 |

⚠️ **`notes` is one of mother's own reserved names, not a C-2 allowlist name.** Reading it here is
the same legitimate move `led` and `oscOut` are: mother publishes on reserved globals and the `m_`
layer that owns the device is the file allowed to read them.

### The keys are Lua

**`m_organelle.lua` names each key, and `m_organelle.pd` does everything else.** The Lua answers a key
with `og-key-NN` and its velocity, as plain Lua that runs on the Mac without Pd; the Pd keeps mother's names, the
knobs and their `[change -1]`, aux, and presence. It is the same split as the sequencer's and the map's: the rules
in Lua, and I/O in Pd ([sequencer.md](../module/sequencer.md), *The rules in Lua, the timing in Pd*).

| | Evidence |
|---|---|
| **The face**, `m_organelle-lua.pd_lua`: inlet 1 mother's `notes`, inlet 2 `init` at load; outlet 1 `param`, outlet 2 `err`, outlet 3 a bang on `init` | verified |
| **What it replaced:** the press and pitch stores, the 25-element array with its write and read, two `makefilename`s and the `pack` that met them — 25 boxes | verified |
| **A Lua that never loads** says `fail m_organelle no-lua` on `err` at load, and the keys are dead while the knobs and `aux` are not. | verified |
| **A rule that throws** says `fail m_organelle lua-notes` (or `lua-init`), and the object carries on | verified |
| **Load and memory:** the patch loads in silence in a test Pd on the Organelle, and its peak resident size went from 3512 to 3480 kB, three runs each (2026-11-03) | verified |
| **Cost per key:** about 0.09 ms on the Organelle against the Pd version's 0.008 — 9000 keys in 0.80–0.90 s against 0.07 s, in a test Pd niced beside the live one (2026-11-03). Nothing at a hand's rate: fifty keys a second is under half a percent of the CPU | verified |

`test/gate/lua/m_organelle_test.lua` tests the rules and the face without Pd, and the Organelle gate
runs it before its Pd half, which is unchanged since the keys were Pd. Edit the rules in
`Cut It/m_organelle.lua`; `; pdluax reload m_organelle-lua` re-reads them in a running Pd, as for
the sequencer.

⚠️ **Not in the file, deliberately:** the encoder, `encbut` and the pedal jack. ⛔ **Taking the
encoder costs the instrument its own way out** — item 314, in Reference — which is a bad trade mid-set, and
neither of the others has anything to drive yet. They belong here when they do — it is one device,
so it is one `m_` abstraction.

### `u_init` sends `midiInGate 0` at load, and again at 2 s

mother's OMNI CC 21–26 collide with the nano's top button row (CC 21–29 by this project's by-tens
scheme), and the mother *binary* overwrites a value sent at `loadbang` about half a second in
(Reference). **Fix:** `u_init` sends `midiInGate 0` at load **and** again at 2 s. The sequence is on
[boot.md](../module/boot.md).

### Saving, as Cut It meets it

After any Save every knob is desynced from its saved value until it is touched, and nothing on the
instrument can detect it (Reference, *Saving*). **Knob 1 is master tempo**, so the first touch would
lurch the tempo: that is what `u_map`'s parameter pickup exists for — see
[map.md](../module/map.md).

⚠️ **Cut It does not deliver its data this way.** `u_state` writes straight to `/sdcard` with an
absolute path, so nothing it does has to finish inside mother's sleep. The only part that reaches the
patch is that `saveState` triggers a `manual` commit — see [state.md](../module/state.md). The 250 ms
still binds anything that writes into `/tmp/state/` and relies on the copy, which today is only
`knobs.txt`.

⚠️ **`knobs.txt`:** Cut It ships without one and `Storage → Save` creates it. `./tools/deploy.sh`
will not remove it once it exists — `--clean` will.

### Presence: `passive`

`m_organelle` registers as `passive` on the presence bus and publishes `seen m_organelle` whenever
mother sends anything. It holds no last-heard clock and **can never be declared lost**.

⛔ **A passive layer must not age.** mother pushes the knobs once at load and then says nothing
(Reference, item 237), so a clock here would run out a few seconds into *every* boot and put a
`device-lost` warning on the screen for hardware that is bolted to the instrument. What a passive
layer can offer is *last heard*; it cannot tell unplugged from untouched, and the operator supplies
that. See [presence.md](../module/presence.md).

## Open

**Nothing.** The ruled-out cause for the OLED lag (the serial `Rx FIFO overrun` in `dmesg`) is in
Reference, under *The OLED lags the audio by ~200 ms*, for the next person who spots it.
