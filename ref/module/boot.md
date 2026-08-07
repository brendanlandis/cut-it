<!-- schema: module -->
# Boot and wiring

**Files:** `Cut It/u_init.pd`, `Cut It/wire.sh`, `Cut It/main.pd`, `Cut It/main-dev.pd`, `Cut It/u_root.pd`, `Cut It/u_mother-stub.pd` · **Gate:** `tools/check-all.sh` · **Bench:** `tools/phase3-bench.pd`

## What it is

**`u_init` owns the ordered startup, and it owns it because `loadbang` fires before the ALSA
connections exist.** Everything here is one timed sequence in one file rather than a pile of `[del]`
objects scattered through the patch — **`u_init` decides WHEN, and the file at the other end of the
wire decides WHAT.** That is why the two things it triggers are cords rather than sends: the seam is
worth being able to see, and a send would make it invisible.

Two entry points instantiate `u_root` and nothing else. `main.pd` is what `mother.pd` loads by name
on the device; `main-dev.pd` is the Mac's, and adds `u_mother-stub`. **Five creation arguments are
the only thing they are allowed to disagree about**, and only one of them actually does.

`wire.sh` is the ALSA half — every `aconnect` in the rig, run once per load through `[shell]`. It
also **undoes mother's own autoconnect**, which is not ours and is actively wrong.

## Facts

### The stage sequence

| ~Time | Stage | What happens | Evidence | Item |
|-------|-------|--------------|----------|------|
| 0 ms | `modal booting` | `midiInGate 0` and `midiOutGate 0` — mother's MIDI mapping off | verified | — |
| 0 ms | | `wire.sh` runs through `[shell]` | verified | — |
| 1500 ms | `modal wiring` | | verified | — |
| 2000 ms | | `midiInGate 0` **again** — the second send is the one that works | verified | — |
| 3000 ms | `modal launchpad` | **Outlet 1** bangs `m_launchpad`, which enters Programmer Mode | verified | — |
| 3500 ms | | **Outlet 2** bangs `u_state` — restore the saved state | verified | — |
| 3500 ms | `modal-off` | `status v0.2-ready` into the footer | verified | — |
| 4000 ms | | `u_tempo` drops the BPM into the footer, taking it over | verified | — |

**Each stage reports to `disp` as it is REACHED.** Nothing here is acknowledged by any device, so a
stage name on screen means the sequence got that far — not that the hardware answered. **A boot stuck
on one name still tells you where to look.**

⚠️ **The stage timings are guesses with evidence, not measurements.** `loadbang` fires before ALSA
is up; init SysEx sent on `loadbang` goes nowhere, and 1500 ms was enough in `tools/self-wire.pd`.
**If the Launchpad ever comes up unlit, lengthen the second delay before suspecting the SysEx.**

⛔ **`u_tempo`'s 4000 is coupled to this sequence.** Change a stage timing and that number changes
with it.

### The ALSA wiring

<!-- check: sh-aconnect "Cut It/wire.sh" connect -->

| From | To | Carries | Evidence | Item |
|------|----|---------|----------|------|
| `Launchpad Pro MK3:0` | `Pure Data:0` | Pads and CCs in, Pd channels 1–16 | verified | — |
| `Pure Data:4` | `Launchpad Pro MK3:0` | LEDs and SysEx out | verified | — |
| `nanoKONTROL:0` | `Pure Data:1` | Faders, knobs, transport, Pd channels 17–32 | verified | — |
| `SP-404MKII:0` | `Pure Data:2` | Pad presses in, Pd channels 33–48 | verified | — |
| `Pure Data:6` | `SP-404MKII:0` | Pad triggers out | verified | — |
| `USB Uno MIDI Interface:0` | `Pure Data:3` | Nothing today — the DIN IN jack, for a future device. Pd channels 49–64 | verified | — |
| `Pure Data:7` | `USB Uno MIDI Interface:0` | Notes and CC out to the Volca | verified | — |

**The port map, from `/root/.pdsettings` — four in, four out:**

| Pd ALSA port | Is | Pd channels | Evidence | Item |
|--------------|-----|-------------|----------|------|
| `Pure Data:0`–`:3` | Midi-In 1–4 | 1–16, 17–32, 33–48, 49–64 | verified | — |
| `Pure Data:4`–`:7` | Midi-Out 1–4 | — | verified | — |

**Slot *n* gets channels (n−1)×16+1 upward.** That is where every `m_` layer's channel-block argument
comes from.

### Undoing mother's autoconnect

<!-- check: sh-aconnect "Cut It/wire.sh" disconnect -->

| From | To | Evidence | Item |
|------|----|----------|------|
| `nanoKONTROL:0` | `Pure Data:0` | verified | — |
| `SP-404MKII:0` | `Pure Data:0` | verified | — |
| `USB Uno MIDI Interface:0` | `Pure Data:0` | verified | — |

`/root/fw_dir/scripts/alsaconnect.sh` wires the **lowest-numbered MIDI client** to Pd's Midi-In 1.
See *Traps*.

### The creation arguments

`u_root` takes five, and `main.pd` passes `17 1 /sdcard/cut-it-state 33 49`:

| # | Is | Device | Mac | Evidence | Item |
|---|----|--------|-----|----------|------|
| 1 | The Pd channel the nanoKONTROL's own channel 1 lands on | `17` | whatever slot it fills | verified | — |
| 2 | The same for the Launchpad | `1` | `1` | verified | — |
| 3 | `u_state`'s **data directory**, absolute, no trailing slash | `/sdcard/cut-it-state` | `/tmp` | verified | — |
| 4 | The same for the SP-404 | `33` | `33` | verified | — |
| 5 | The same for the Volca | `49` | `49` | verified | — |

⚠️ **Argument 3 is the only genuine disagreement, and it is a real platform difference** — there is
no `/sdcard` on a Mac. Set the Mac's MIDI inputs in the same order (Launchpad first, nano second) and
the other four are identical, which is the point of numbering them that way round.

### `u_mother-stub`

| | Evidence | Item |
|---|----------|------|
| Impersonates `mother.pd` off-device **and** is the dev panel — screen, knobs, encoder, volume and keys, laid out like the device and rendered inline on `main-dev.pd` by graph-on-parent | verified | — |
| Supplies `knob1`–`knob4`, `vol`, `notes`, `aux`, `enc`, `encbut`, and previews `screenLine1`–`5` and `oscOut` | verified | — |
| **No cords** — every control binds by its iemgui send name | verified | — |
| Shows *what* is drawn, not *where*. Pixel-accurate OLED rendering is out of scope | verified | — |
| Mac only. The device never loads `main-dev.pd` | verified | — |

## Traps

Each is a claim and its fix. How any of them was found is in the git history.

### mother's autoconnect puts the wrong device on the Launchpad's channel block

⛔ `alsaconnect.sh` wires the **lowest-numbered** MIDI client to Pd's Midi-In 1, and the nanoKONTROL
enumerated below the Launchpad — so mother put the nano on `m_launchpad`'s channel block. One fader
move published **both `slider-1` and a phantom `lp-cc-1`** to `param` and `disp`.

**Nothing in Pd can fix it.** Once two devices share Midi-In 1 they are both genuinely "channel 1";
`m_launchpad`'s channel test is correct and powerless.

**Fix:** `aconnect -d` at the ALSA level, in `wire.sh`. It costs no extra fork — `wire.sh` already
runs once per load.

⚠️ **The client numbers move, which is why the undo list must cover every device that is not the
Launchpad.** Measured across two boots: the order was nano 32 / 404 36, then 404 32 / Uno 36 /
nano 40. **Whichever device enumerates lowest is the one mother grabs**, so undoing only the two seen
so far would leave a hole the next reboot could walk through.

⚠️ **Invisible on the Mac**, which has explicit device slots and no mother — which is why Phase 6
shipped without catching it.

### Shutting mother's own MIDI off is the FIRST thing, and it takes two sends

⛔ mother's OMNI CC mapping collides head-on with the nanoKONTROL, and mother's MIDI **out** echoes
the Organelle's keys and knobs to every port. Both are on
[organelle.md](../device/organelle.md) — what belongs here is only the **when**: `midiInGate 0` and
`midiOutGate 0` at `loadbang`, then `midiInGate 0` **again at 2 s**, because the mother binary pushes
its own `1` over OSC about half a second in and silently overwrites the first send.

**Fix:** both stages, and do not remove the `loadbang` copy — it costs nothing and closes the window
in between.

### Outlets are ordered by x COORDINATE, not by creation order

⛔ The restore outlet had to go to the **right** of the launchpad outlet. Placing it left of x=900
would silently have made it outlet 1 and sent the Launchpad init to `u_state`. **Nothing would have
errored.**

**Fix:** place a new outlet by where it must appear in the order, not by where there is room.

### Positional creation arguments cannot be skipped, and Pd 0.49 does not warn

⛔ Argument 4 was passed for months before `m_404` existed, because omitting it would silently have
delivered the Volca's channel as arg 4. **Pd 0.49 does not warn about a missing or extra creation
argument at all**, so a clean syntax check proves nothing about arity.

**Fix:** pass every position, even the unused ones, and say in the comment that it is unused.

### The footer is handed over, not shared

⛔ `u_tempo` drops the BPM into the footer at 4 s, deliberately **after** the ready line lands at
~3.5 s. The status is sticky and something else has to clear it — without the handover you could
press aux, watch the LED go green and the 404 start, and still be told PANIC.

**Fix:** `u_tempo` bangs the stored BPM back out on every start and stop, so the footer always
describes the state you are actually in.

### `[shell]` exists only on the Organelle

⚠️ `mac-stubs/shell.pd` stands in during the local syntax check and is **never deployed**. Nothing
`wire.sh` or `state-dir.sh` does happens on the Mac.

### Every `aconnect` is allowed to fail

⚠️ Each line carries `2>/dev/null || true`. A device that is not plugged in must not stop the ones
that are, and **must not stop the boot** — `u_init` reports progress either way and cannot tell from
here which devices answered.

⚠️ **A patch load also DROPS Pd's aconnect links**, so anything launched from the Organelle menu that
needs MIDI out must re-wire its own output.

## Design

### `u_init` owns WHEN; the other file owns WHAT

The Launchpad init and the state restore are **cords out of `u_init`**, not sends. Phase 6 moved
Programmer Mode and the safe exit into `m_launchpad`; what stayed here is the order. Putting a
`[del]` inside `u_state` instead would mean two files owning the same sequence and neither one saying
so.

⚠️ **The stage timings are already coupled to `u_tempo`'s 4000.** Duplicating one of them into a
second file is exactly how that coupling gets broken silently.

### The restore fires at the last stage, and first among the three

~3.5 s is **the earliest moment every `m_` layer and `u_map` exist to receive what comes back** —
earlier and a restore would publish into nothing. It fires before `modal-off` and the footer, so the
screen settles *after* the state does rather than during it.

### Connect by NAME, never by client number

Client 28 was the Launchpad, then became the SP-404 when they were swapped. Every line in `wire.sh`
names the device.

### The two entry points share everything but five numbers

`main.pd` and `main-dev.pd` both instantiate `u_root` and nothing else, **which is what stops them
drifting**. `main.pd` stays thin on purpose: it is the file `mother.pd` loads by name, and it is the
one nobody opens.

### Off-device development is the default

Open `main-dev.pd` in Pd 0.49 and the whole instrument is there. **Reach for the hardware when the
thing you are testing is the hardware** — and this project's own history says that line matters:
Phase 6 passed 25/25 on the Mac twice and shipped three bugs.

### `wire.sh` reports what connected

The last line counts the live connections and echoes them, for the run-it-by-hand console. It is the
only way to know from the patch side whether anything answered.

## Open

- ⬜ **Nothing detects a device that failed to wire.** A stage name means the sequence reached that
  point, not that hardware answered, and there is no readback into the patch. See
  [plan-v03.md](../../plan-v03.md) §4.
- ⬜ **A replug after boot destroys the ALSA links** and only the Launchpad has a recovery path
  today — `m_launchpad`'s bounded `wire.sh` retry. See [launchpad.md](../device/launchpad.md) and
  [plan-v03.md](../../plan-v03.md) §4.
