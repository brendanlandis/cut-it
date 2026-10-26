<!-- schema: module -->
# Novation Launchpad Pro MK3

**Files:** `Cut It/m_launchpad.pd`, `Cut It/g_grid.pd` · **Gate:** `test/gate/launchpad-assert.sh` · **Bench:** `test/bench/launchpad-bench.pd`

## What it is

**The only device in the rig that is a genuine blank slate, and the only one Pd can light.** What the
device is, its MIDI, its Programmer Mode index map, lighting, quirks and measurements are in
Reference: `~/Sites/!reference/novation-launchpad-pro-mk3.md`. This page is how Cut It uses it.

It runs in **Programmer Mode**, where each button becomes a note or CC number the patch defines.

`m_launchpad.pd` is the only file that talks to it: Programmer Mode, the safe exit, pads, ring and
pressure onto `param`, and the replug watchdog. The row a pad or ring button draws is `u_map`'s
(item 317); pressure draws none unless the mode maps it (item 318). `g_grid.pd` owns its
LEDs and nothing else does.

## Facts

What the device does is in Reference, under the same item numbers. This is what is true of the
patch around it.

### Addresses and counts in the patch

| Property | Value | Evidence | Item |
|----------|-------|----------|------|
| Pd channel block | 1–16 (input slot 1) | verified | — |
| Port wired | `wire.sh` connects **port 0 only**, so the layout announcements on port 3 never reach Pd | verified | 250 |
| What `g_grid` sends | 108 specs per message, indices 1–108 | verified | — |

`g_grid` paints **indices 1–108**, CC 1–8 included. The span is a choice, not a limit: an index
outside it would hold whatever Live Mode last drew there, forever.

⛔ **Four counts are in play and they are four different quantities.** `g_grid.pd` uses all of them.

| Count | Is | Evidence | Item |
|---|---|---|---|
| **96** | **Physical buttons** on the device — 64 pads plus 32 edge | verified | — |
| **108** | **Specs sent per frame**, indices 1–108, per the index map below | verified | — |
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
inquiry (item 249) and there is exactly one `[sysexin]` box in the whole patch, so that shortcut
reports the Launchpad present whenever the **nano** answers. `[c_devid 0]` matches byte 5 of the
reply — `00`, Novation — and byte 5 discriminates all three. The `[sysexin]` port outlet is unused for
the reason in `~/Sites/!reference/pure-data.md`.

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

## Traps

Each is a claim and its fix. How any of them was found is in the git history. The device's own traps
(the Settings lockout, LED state surviving a mode switch, 7-bit data bytes, a dirty SysEx pipe, the
dead mode buttons) are in Reference.

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

### The grid paints the full span on init

Because LED state survives mode switches (Reference), `g_grid` clears the whole span on init and
paints 1–108 rather than a subset.

## Design

### Three tiers, and Cut It only builds the top one

The three tiers are described in Reference ("Modes: three tiers"). Which world the surface is in is
something the patch decides at runtime rather than once.

**Do not rebuild the built-ins.** Note mode's scale tables, root selection and isomorphic layout
maths are genuinely fiddly in Pd and Novation's are good. Chord mode is worse to replicate. The
Sequencer is a substantial project on its own, and it is already the compose-time authoring tool.
Projects handles save/recall of that data. Anything needing "empty / loaded / queued / playing" as four
distinct states needs Programmer Mode; a plain CC grid or a scaled keyboard does not.

### CC 90 is the panic button, and it has two tiers

**The top-left corner — item 82, a real button this unit sends and Novation does not document,
whose numbering starts at 91.** Nothing else wants it, and `g_grid` can light it, so the armed state
is visible on the surface itself.

| Gesture | Raises | What happens |
|---------|--------|--------------|
| **Short press** | `panic` | All Notes Off to the SP-404 on all ten channels and to the Volca; realtime STOP on ports 1, 3 and 4; the aux LED goes red; the whole grid flashes red for a second; the OLED footer reads `panic` |
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

### CC 91–96 are the mode selector, and they are the lamps

**The first six of the top row**, and `g_grid` lights them as the mode lamps — so this is one
surface rather than press-here-look-there. Pressing one selects that mode; the lamp it paints is the
confirmation.

⛔ **`u_map` gates each of the six on the press.** A CC button here sends **127 then 0**, where a
nanoKONTROL button sends only the press — so an ungated branch would select the same mode twice per
push. Idempotent, therefore invisible. The mechanism is on [map.md](../module/map.md).

⚠️ **Mode selection is on a device that can be unplugged.** It is not a control you need in a hurry.

### CC 80 is free

**The left column's top button**, one row under the CC 90 corner. It does not hold the diagnostic
screen: ⛔ **a Launchpad that has come unplugged sends no CC**, so a control here that named the
missing device would be dead in exactly the case the screen exists for. `diag` lives on the
Organelle's own keyboard, under the aux modifier — see [organelle.md](organelle.md).

⚠️ **The same objection applies to everything else on this surface**, `recover` on CC 90 included;
the Organelle's keyboard is where the controls you reach for when a device has died belong. Anything
put on CC 80 should be something you would not miss if the Launchpad were the thing that went.

### Pressure is the forgotten input

The pads are polyphonic-aftertouch sensitive, and that channel is free panel space: any continuous
parameter can ride pad pressure while a pad is held. It is the most expressive control on the rig
and costs no buttons.

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
(items 193 and 204, velocity and aftertouch).

**So the trade is bad and the decision is to stop asking.** The drive is neutralized on the device
side instead, by a guard in `mount.sh` — see [device/README.md](../../device/README.md).
⚠️ **Revisit only if an update is being done for another reason** — then re-measure velocity and
aftertouch afterwards rather than trusting the old numbers.

## Open

- ⬜ **`[polytouchin]` has no stub, so the pressure path is uncovered.** See
  [plan-v04.md](../../plan-v04.md) §3. This page's own text calls aftertouch the most expressive
  control on the rig. A `t_polytouchin` would be the same shape as `t_ctlin`.
- ⬜ **What every layout ID means.** `02`, `03` and `04` were seen; the full set and their names are
  not established. See [plan-v04.md](../../plan-v04.md) §3. *That it announces at all* is
  established (item 100) — see *Mode changes are announced* in Reference.
- ⬜ **What firmware version this unit is on, in Novation's terms.** Item 98, and
  [plan-v04.md](../../plan-v04.md) §3. The device inquiry returns firmware bytes `00 04 06 05`
  and nothing published maps that to a marketing version, so *how far behind* this unit is cannot
  be stated. ⚠️ **It does not change the decision** to decline the update — see *The firmware
  update is DECLINED* under **Design**.
