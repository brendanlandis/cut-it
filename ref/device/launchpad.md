<!-- schema: device -->
# Novation Launchpad Pro MK3

**Files:** `Cut It/m_launchpad.pd`, `Cut It/g_grid.pd` · **Gate:** `test/gate/launchpad-assert.sh` · **Checklist:** `test/checklists/launchpad.md`

**The only device in the rig that is a genuine blank slate, and the only one Pd can light.** What the
device is, its MIDI, its Programmer Mode index map, lighting, quirks and measurements are in
Reference: `~/Sites/!reference/novation-launchpad-pro-mk3.md`. This page is how Cut It uses it.

It runs in **Programmer Mode**, where each button becomes a note or CC number the patch defines.

`m_launchpad.pd` is the only file that talks to it: Programmer Mode, the safe exit, pads, ring,
pressure and a tap on Setup onto `param`, and the replug watchdog. The row a pad or ring button draws is `u_map`'s
(item 317); pressure draws none unless the mode maps it (item 318). `g_grid.pd` owns its
LEDs and nothing else does.

## Design

### Addresses and counts in the patch

| Property | Value | Evidence | Item |
|----------|-------|----------|------|
| Pd channel block | 1–16 (input slot 1) | verified | — |
| Ports wired | `wire.sh` connects **port 0 and port 2** (`MIDI 1` and `MIDI 3`), both to Midi-In 1: port 2 for the layout announcement a tap on Setup makes (*A tap on Setup flips test mode*, below). Port 1 is not wired | unknown | — |
| What `g_grid` sends | 108 specs per message, indices 1–108 | verified | — |

`g_grid` paints **indices 1–108**, CC 1–8 included: the whole span, which Reference shows is a
choice rather than a limit (see *The grid paints the full span on init*, below).

⛔ **Four counts are in play and they are four different quantities.** `g_grid.pd` uses all of them.

| Count | Is | Evidence | Item |
|---|---|---|---|
| **96** | **Physical buttons** on the device — 64 pads plus 32 edge | verified | — |
| **108** | **Specs sent per frame**, indices 1–108, per the index map in Reference | verified | — |
| **109** | **Array cells** — `[array define $0-surface 109]`, indices 0–108. Cell 0 is allocated and deliberately never written, so an index maps straight to a cell with no arithmetic | verified | — |
| **~96/s** | **ALSA MIDI writes per second** at the frame clock. ⚠️ Unrelated to the first 96 — a rate, not a count, and the number `g_grid`'s dirty-flag gating exists to hold down | verified | 75 |

The 96 physical buttons and the 1–108 index span are the device's: see Reference.

### Presence and the inquiry

A `c_presence` inside `m_launchpad` polls the device inquiry every two seconds and drops surface
ownership after three missed replies, so `g_grid` stops painting. It costs one round trip per poll
against the 96 ALSA writes a second the clock already makes. The recovery it triggers is not this
file's — see [presence.md](../module/presence.md).

⛔ **AND THE REPLY MUST BE MATCHED, NOT MERELY COUNTED.** Treating *any* SysEx as proof of presence
holds only while nothing else in the rig transmits any. All three detectable devices answer the same
inquiry (item 249) and every `[sysexin]` in the patch hears all of them, so that shortcut
reports the Launchpad present whenever the **nano** answers. `[c_devid 0]` matches byte 5 of the
reply — `00`, Novation — and byte 5 discriminates all three. The `[sysexin]` port outlet is unused for
the reason in `~/Sites/!reference/pure-data.md`. The Launchpad's own layout announcement shares the
stream since port 2 was wired, and its byte 5 is `0E`, so `c_devid` never takes it for a reply.

### Live Mode, ownership and the handback

⚠️ **`wire.sh` connects port 0 to Pd's Midi-In 1**, so a Launchpad left in Live Mode floods Cut It's
primary MIDI input with clock (Reference, item 250). Today the mode SysEx at load prevents it — which
makes that one message load-bearing for more than the grid, and it fails silently if the device is not
yet enumerated.

⛔ **`killall pd` DOES NOT TEST THE SAFE EXIT**: any exit that is not mother's own strands the device
in Programmer Mode, which is what `tools/lp-live.sh` exists to rescue (item 96).

⛔ **`$0-want` is not `$0-own`.** `own` says the surface **is** ours; `want` says we still **intend**
it. Without that split, a handback is undone by the heartbeat two seconds later.

⛔ **PANIC DOES NOT HAND THE DEVICE BACK** (item 251). A panic that surrenders the surface and sets
`want` 0 stops the watchdog re-asserting, so **the grid stays dead until the patch is reloaded** —
during the one moment the instrument is most needed — and in Live Mode the device floods port 0 with
clock into Pd's Midi-In 1 (item 250), burying Cut It's primary MIDI input. **Silencing notes has
nothing to do with surrendering the surface.** `quitting` is the only handback.

⚠️ **The give-up bound is 70 s because nobody reseats a cable in twelve.** A twelve-second bound
reads as perfectly reasonable in source and misses every real replug.

⚠️ **The recovery re-runs `wire.sh`, which is a FORK, and the bound is what makes that permissible.**
Phase 4's rule is *one fork per load, never per event* — written against error logging, which
cascades without limit. Three forks tied to one cable event cannot.

| | Evidence | Item |
|---|----------|------|
| `wire.sh` costs **~247 ms** and is **idempotent** — see [presence.md](../module/presence.md) | verified | 292 |
| Ten forks fired back to back produced **no audio complaint** on Pd's console | verified | — |
| The recovery gives up at about **70 s**, so a device nobody intends to plug back in cannot make Pd fork all night | verified | — |

**All three are measured**, which is the only reason bending the rule is allowed.

### The Live Mode SysEx is sent on `quitting`, and only there

`m_launchpad` returns the device to Live Mode on **`quitting`**, and it is the only file allowed to.
⚠️ **On `quitting` only** (item 251), and the gate drives that path directly rather than through
`panic`. Out of band, `tools/lp-live.sh` does it without Pd — ⚠️ **but only once Pd is gone**: `amidi`
cannot open the device while Pd holds it, so it is a post-mortem tool, not a live one.

### Init SysEx waits for ALSA, and `polytouchin` needs a `[trigger]`

Both are Pd facts, in `~/Sites/!reference/pure-data.md`: `loadbang` fires before ALSA connections
exist (use `[del 2000]` or longer here), and `[polytouchin]` emits note before value.

### A Programmer Mode heartbeat sits beside the inquiry poll

The device answers the inquiry in either mode, so a Mac replug that drops it back to Live Mode is
invisible to the poll alone. `m_launchpad` runs the heartbeat and the poll.

**The heartbeat waits while anything is held.** Entering Programmer Mode makes the device let go
of every held pad, a note off at once (Reference), so a repeat pad held across a tick stopped
repeating within two seconds (Brendan, 2026-11-04); with the heartbeat waiting, one held five
seconds and more kept repeating on the rig. `m_launchpad` keeps a table of what is down,
notes and then CCs from 128, and skips a tick while any is. A pad unplugged while held stays held
in it until it is pressed and let go again; on a Mac the heartbeat waits that long.

### The grid paints the full span on init

Because LED state survives mode switches (Reference), `g_grid` clears the whole span on init and
paints 1–108 rather than a subset.

### Three tiers, and Cut It only builds the top one

The three tiers are described in Reference ("Modes: three tiers"). Which world the surface is in is
something the patch decides at runtime rather than once.

**Do not rebuild Note and Chord mode.** Note mode's scale tables, root selection and isomorphic
layout maths are genuinely fiddly in Pd and Novation's are good. Chord mode is worse to replicate.
Anything needing "empty / loaded / queued / playing" as four distinct states needs Programmer Mode;
a plain CC grid or a scaled keyboard does not.

**The Sequencer is rebuilt, in Pd** — decided 2026-11-02 (Brendan), overturning the rule that it
was the compose-time authoring tool. It cannot do what the drum machine is for: randomizers, and
switching subdivision for a whole or part of a bar, for all tracks or only some. And **Pd sequences
everything** ([architecture.md](../architecture.md)): a pattern in the Launchpad's own memory would
be a second sequencer the patch cannot see, store per section, or keep in step with its own clocks.
Page 2 is the drum page, drawn in Programmer Mode by `g_grid` and played by `c_steps`
([sequencer.md](../module/sequencer.md)); its layout is on [display.md](../module/display.md).

### CC 90 is the panic button, and it has two tiers

**The top-left corner — item 82, a real button this unit sends and Novation does not document,
whose numbering starts at 91.** Nothing else wants it, and `g_grid` can light it, so the armed state
is visible on the surface itself.

| Gesture | Raises | What happens |
|---------|--------|--------------|
| **Short press** | `panic` | All Notes Off to the Volca; the drums stop; realtime STOP on ports 1 and 4; the aux LED goes red; the whole grid flashes red for a second. Nothing on the OLED: panic is the LED's and the grid's to show (2026-11-04) |
| **Held 2000 ms** | `recover` | `panic` again, then the patch **reloads** — every device re-enumerated and `wire.sh` run fresh |

⛔ **`panic` fires on the PRESS, not the release, and that is what makes the hold length free.** You
are already silent while you hold for the reload, so 2000 ms costs nothing and nothing reaches it by
accident. A hold therefore raises `panic` twice — once from `u_map`, once from `u_init` before the
reload — deliberately, so `recover` is self-contained whatever reaches it.

⚠️ **For a device nothing can detect, this and the re-wire heartbeat are the only recoveries.**
`m_volca` registers `none`, so it can never be polled or declared lost, and the bounded recovery
reaches it only if a detectable device fails beside it (item 275). See
[presence.md](../module/presence.md) and [volca.md](volca.md).

⛔ **The map row names `recover` and never `panic`.** A control bound to `panic` in the table would
let a finger on a fader silence the instrument mid-set, and `map-assert.py` refuses one; the tiers
are the *handler's* business. The mechanism is on [map.md](../module/map.md), the reload on
[boot.md](../module/boot.md).

⚠️ **The reload does not surrender the surface.** It touches no ownership, and `quitting` still fires
on the way out because `/loadPatch` runs `killpatch.sh` first (item 252) — so the safe exit
still returns the device to Live Mode. Item 251 stays closed.

### The left column is the page selector, and it is the lamps

**CC 80 down to 10, page 1 at the top** (the up arrow), eight pages, and `g_grid` lights them as the
mode lamps — so this is one surface rather than press-here-look-there. Pressing one selects that
page; the lamp it paints is the confirmation. Decided 2026-11-02 (Brendan), when the top row was given
to song sections (`cut-it/songs-and-sections`), and the column's bottom two joined on 2026-11-04.

⛔ **`u_map` gates each of the eight on the press.** A CC button here sends **127 then 0**, where a
nanoKONTROL button sends only the press — so an ungated branch would select the same mode twice per
push. Idempotent, therefore invisible. The mechanism is on [map.md](../module/map.md).

⚠️ **Mode selection is on a device that can be unplugged.** It is not a control you need in a hurry.
It does not hold the diagnostic screen either: ⛔ **a Launchpad that has come unplugged sends no
CC**, so a control here that named the missing device would be dead in exactly the case the screen
exists for. `diag` lives on the Organelle's own keyboard, under the aux modifier — see
[organelle.md](organelle.md).

### The top row plays the song's sections, and two bottom buttons save and revert

**CC 91 and 92, the arrows, step back and forward a section; CC 93–98 are six section buttons**,
which scroll a section at a time with the one playing; a press while the transport runs starts its
section when the pattern next comes round, and a press while it is stopped at once (Brendan,
2026-11-02 and 2026-11-05). **CC 108, the upper bottom row's rightmost, saves the song, and CC 8,
the lowest row's rightmost, reverts it** (Brendan, 2026-11-04). The map binds them on every page,
as `section`, `save` and `revert`, to `u_song` ([songs.md](../module/songs.md)); `g_grid` lights
them from `u_song`'s state, the playing section solid, a queued one blinking, save red and revert
gray while anything is unsaved ([display.md](../module/display.md)). They held the mode selector
until it moved to the left column.

⚠️ **The objection above applies to everything on this surface**, `recover` on CC 90 included; the
Organelle's keyboard is where the controls you reach for when a device has died belong. A Launchpad
that goes leaves the section playing as it is and the draft on the SD card, so nothing is lost but
the next press; choosing songs will be the Organelle's keys' (`cut-it/songs-and-sections`).

### A tap on Setup flips test mode

**Setup, the bottom left corner, publishes `lp-setup`, and the map binds it to `test-mode` on
every page**, beside `og-shift-61` ([map.md](../module/map.md)): asked for by Brendan, 2026-11-04.
Test mode is on the Organelle's keyboard too, so it passes the test above. In Programmer Mode the
button sends nothing on port 0; a tap makes the device announce its layout on port 2, and a hold
sends nothing at all (Reference, *The Setup button in Programmer Mode*). So `wire.sh` joins port 2
to Midi-In 1, and `m_launchpad`'s `setup` subpatch matches that announcement as a whole frame,
`F0 00 20 29 02 0E 00 11 00 00 F7`. There is no release, so a tap is published as `lp-setup 127`,
a ring button's press.

⛔ **Every Programmer Mode entry makes the same announcement**, within a millisecond, and the
heartbeat enters it every two seconds. Read as taps, the echoes would flip test mode every two
seconds. **So each entry `m_launchpad` sends, at init and on the heartbeat, first raises an
expected echo**, and an announcement that arrives while one is expected is taken as that echo.
Only an announcement nothing expected is a tap.

⚠️ **An expected echo is forgotten 250 ms after the last entry**, so one the device never sent
cannot swallow a tap made later. The price is a tap inside those 250 ms whose entry's echo was
lost, which is taken for the echo. A tap in the same millisecond as an entry still publishes once:
whichever arrives first is the echo.

Other layouts' announcements, which port 2 carries in Live Mode (Reference, *Mode changes are
announced*), never match, and `c_devid` never takes an announcement for an inquiry reply: its byte 5
is `0E`. `launchpad-assert.sh` answers each entry as the device does and proves the echoes publish
nothing, a tap publishes `lp-setup` and flips test mode through the map, other frames do not, and
an echo that never came is forgotten. The wiring and the device's timing are the checklist's.

### Pressure is the forgotten input

The pads are polyphonic-aftertouch sensitive, and that channel is free panel space: any continuous
parameter can ride pad pressure while a pad is held. It is the most expressive control on the rig
and costs no buttons.

### The layer stays Pd

**`m_launchpad` keeps its decode in Pd** (2026-11-03), where the nano and the Organelle's keys
moved theirs to Lua, as the SP-404's had before it left the rig ([nanokontrol.md](nanokontrol.md),
*The decode is Lua*). Three
reasons, each enough:

- **The ring carries the mode keys**, which must work when the Lua does not: `u_map` keeps them in
  Pd so a missing pdlua or a broken table cannot strand you ([map.md](../module/map.md)), and they
  reach it as `lp-cc-80` to `lp-cc-10` from this file.
- **Pressure is the densest stream on the rig**, a message per held pad as often as the device
  sends one, and it already crosses the map's Lua. A pdlua call costs about 0.1 ms on the Organelle,
  where `makefilename pad-%d-at` costs a few microseconds.
- **There is little to decode.** A pad is its note number and a ring button its CC number, each one
  `makefilename`; the rest of the file is I/O, ownership, the safe exit and the watchdog's timing.

### The firmware update is DECLINED, and the onboarding drive stays on

✅ **Item 265.** Novation Components refuses to open the Launchpad at all until a **firmware update**
is accepted (Reference, *Firmware*). ⛔ **That would change the firmware every `verified` fact was
measured against** — including item 257, that the device ignores incoming MIDI clock — on the one
device in the rig with a known enumeration quirk (item 248).

**The changelog was read before deciding, rather than left as an unknown.** What the update adds is in
Reference; whether it bears on this rig:

| V1.2 / V1.2.1 / V1.2.2 | Bears on this rig? |
|---|---|
| Unquantised recording | No — it belongs to the **Launchpad's own** sequencer, and ⛔ **Programmer Mode bypasses that entirely**: the patch owns the surface |
| Performance Velocity, Probability and Mutation | No — same, and ⚠️ **v0.4 is building sequencing, probability and mutation in Pd on purpose.** The firmware's versions are not merely unused, they are the thing being replaced |
| **Pad Trigger Threshold** (new setting) | ⚠️ **Yes** — a threshold change can move measured velocity |
| Legacy Mode brought in line with Launchpad X / Mini MK3 | No |
| **Aftertouch threshold fix** | ⚠️ **Yes** — `m_launchpad`'s `pressure` subpatch depends on aftertouch behavior |
| Crash fix, multiple Novation devices connected then disconnected | No — one Novation device here |

⛔ **Nothing in it touches MIDI clock, tempo sync or LED animation**, so it would not be expected to
fix item 257 — the device ignoring incoming clock — which is the only Launchpad behavior this
project actually wants changed. **The update offers nothing needed and risks two things measured**
(velocity and polyphonic aftertouch: the pad rows under *Transmits* in Reference, aftertouch item 86).

**So the trade is bad and the decision is to stop asking.** The drive is neutralized on the device
side instead, by a guard in `mount.sh` — see [device/README.md](../../device/README.md).
⚠️ **Revisit only if an update is being done for another reason** — then re-measure velocity and
aftertouch afterwards rather than trusting the old numbers.

## Open

- ⬜ **`[polytouchin]` has no stub, so the pressure path is uncovered.** See
  [plan-v04.md](../../plan-v04.md) §3. This page's own text calls aftertouch the most expressive
  control on the rig. A `t_polytouchin` would be the same shape as `t_ctlin`.
- ⬜ **What every layout ID means.** `02`, `03` and `04` were seen in Live Mode and `11` is
  Programmer Mode's; the full set and their names are not established. See
  [plan-v04.md](../../plan-v04.md) §3. *That it announces at all* is established (item 100) — see
  *Mode changes are announced* in Reference.
- ⬜ **The Setup tap has not run on the rig**: port 2 joined to Midi-In 1, and the device's echo
  inside the 250 ms. Step 28 of [the Launchpad checklist](../../test/checklists/launchpad.md), with
  the rest of it (`cut-it/inbox`).
- ⬜ **What port 2 carries in Live Mode beyond the layout announcements.** Wired, it reaches
  Midi-In 1 whenever the device is out of Programmer Mode: at boot before the init, and after a Mac
  replug until the next heartbeat. NO PLAN OWNS THIS.
- ⬜ **What firmware version this unit is on, in Novation's terms.** Item 98, and
  [plan-v04.md](../../plan-v04.md) §3. The device inquiry returns firmware bytes `00 04 06 05`
  and nothing published maps that to a marketing version, so *how far behind* this unit is cannot
  be stated. ⚠️ **It does not change the decision** to decline the update — see *The firmware
  update is DECLINED* under **Design**.
