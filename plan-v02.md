# Cut It v0.2 — Infrastructure Plan

The scaffolding the instrument stands on: startup, audio path, controller mapping, display,
state. **No musical DSP.** When this is done, Cut It makes no interesting sound — it passes
audio through, knows what every control is doing, and can tell you about it. The four filter
stages are built on top of this, afterwards.

**This file holds what is still open.** Phases 0–4 are done and their outcomes, corrections and
measured numbers live in [ref-build-log.md](ref-build-log.md). Read
[ref-conventions.md](ref-conventions.md) first — naming, `$0`, `[trigger]` discipline and the
global allowlist are assumed throughout.

v0.1 is not being extended. Its plans are kept in [! v0.1 plans/](<! v0.1 plans/README.md>) and
the patch itself in [! v0.1 plans/patch/](<! v0.1 plans/patch/README.md>) — **reference for
intent, not code to lift.** All of it predates the conventions; assume it is naive.

---

## Why infrastructure first

Three constraints make the usual "get a sound out, then tidy up" approach expensive here:

1. **There is no console.** Errors vanish. Anything not built to report itself is invisible,
   and retrofitting reporting across an existing patch is far worse than designing it in.
2. **The device mapping layer is the expensive thing to retrofit.** Compose and perform mode
   give the same physical controls different meanings. If `e_chop` learns about the
   nanoKONTROL, that is permanent.
3. **Timing is architectural.** Grain clocks must be audio-domain from the first line, not
   converted later.

---

## What exists already

Not starting from nothing. These are verified and have working reference implementations in
[tools/](tools/):

| Proven | Reference |
|---|---|
| ALSA MIDI wiring from inside a patch via `[shell]` | `tools/self-wire.pd` + `wire.sh` |
| Launchpad Programmer Mode, LEDs, velocity, poly aftertouch | `tools/lp-monitor.pd`, `lp-modes.pd` |
| OLED graphics API from a patch | `tools/oled-probe/` |
| Bidirectional OSC to the phone, named-parameter protocol | `tools/status-display/`, `tools/pdparty-scene/` |
| nanoKONTROL full CC map, decoded through the real patch | [ref-midi.md](ref-midi.md) |
| Deploy + syntax check workflow | [ref-conventions.md](ref-conventions.md) |

**The job is turning these into abstractions that obey the conventions**, not discovering
whether they work.

---

## Architecture

```
                        main.pd
                     (wiring only)
                           |
    ┌──────────┬───────────┼───────────┬──────────┐
    │          │           │           │          │
  u_init    u_tempo      u_err      u_state    u_net
  startup   clock        errors     presets    phone
    │          │           │           │          │
    └──────────┴─────┬─────┴───────────┴──────────┘
                     │
              global buses
   mode · tempo · clock · start/stop · panic · err · disp · param
                     │
    ┌────────────────┼────────────────┐
    │                │                │
  m_nano        m_launchpad         m_keys          ← device mapping
  ch 17/18        ch 1               mother
    │                │                │
    └────────────────┼────────────────┘
                     │
                   u_map                            ← control name → destination
                     │
              (v0.3: e_chop, e_pitch, e_trem, e_verb)
                     │
    ┌────────────────┴────────────────┐
  g_oled          g_led            g_grid           ← display arbiters
  OLED            aux LED          Launchpad
```

⚠️ **This diagram is the target, not the current state.** `u_map`, `g_led`, `u_tempo`, `c_clock` and
the `param` bus arrive in Phase 5; `m_launchpad` / `g_grid` in Phase 6; `u_net` in 7; `u_state` in 8.
The allowlist in [ref-conventions.md](ref-conventions.md) is the authority on which buses actually
exist — `param` is not in it yet, and adding it is a Phase 5 step.

**The `m_` layer is the load-bearing boundary.** Nothing below it knows a nanoKONTROL exists. A
device publishes a **named control** on `param`; what that control *means* is decided in `u_map`,
above everything it controls. This is what makes the compose/perform split tractable and it is the
one boundary that is genuinely expensive to retrofit.

### Phase status

| Phase | | Built |
|---|---|---|
| 0 | ✅ | Skeleton and the off-device shim |
| 1 | ✅ | Audio path |
| 2 | ✅ | Startup sequencing |
| 3 | ✅ hardware | Display and errors |
| 4 | ✅ hardware | nanoKONTROL, persistent error log, multi-parameter display |
| **5** | **next** | **Clock and transport** |
| 6 | | Launchpad |
| 7 | | Phone status link |
| 8 | | State and presets |

Details of 0–4, and every correction they produced, are in
[ref-build-log.md](ref-build-log.md). **Read its corrections before writing any Pd** — nine of
them were found by measuring something a plan had asserted.

---

## Phase 5 — Clock and transport

`u_tempo`, `c_clock`, `u_map`, `g_led`

A **rewrite**, not a port. v0.1's `midiclock.pd` is archived in
[! v0.1 plans/patch/](<! v0.1 plans/patch/README.md>) and is worth reading for *which MIDI realtime
bytes went where*, nothing more — it drove `[metro]` from `tempo $1 permin` and predates every
convention in this project.

**Done when:** tempo is settable from the nano, the 404 follows it, the aux button starts and stops
the transport and its LED says which, grain-rate timing derives from `phasor~` rather than `metro`,
and two `c_clock` instances run at different rates at once.

### Step 0 — the aux LED ✅ answered

Done first, because the transport work needs a state indicator to aim at. ✅ Read off the device and
then swept by eye: **`[s led]` takes 0–7 and gives seven colours plus off** — off, red, yellow,
green, cyan, dark blue, pink, white. Full detail, including the RGB bitmask underneath and the
undocumented `/led/flash`, is in [ref-display.md](ref-display.md).

That is better than expected. **A full RGB LED is the only state display in the rig that is not a
screen**, so it can carry transport state without spending any of the OLED, and it is glanceable in a
way the OLED is not.

### Step 1 — `param`, and the mapping layer

**`m_nano` publishes only to `disp`, which is a display bus.** Nothing can *consume* a control today.
So Phase 5 adds the missing bus and the layer that reads it — and it is the cheapest possible moment,
because there is exactly one device to rewire and Phase 6 would otherwise add a second with no
consumer path.

**One new allowlisted global: `param`, carrying `<name> <value>`** — a control *changed*, as distinct
from `disp`, which is a request to *show* something. Adding to the allowlist is a deliberate edit to
[ref-conventions.md](ref-conventions.md), so make it there with the reasoning.

- **`m_nano`** gains `[s param]` beside its existing `[s disp]`, off the same `[list trim]`. *(Judgment
  call: this duplicates the data, where teaching `g_oled` to listen on `param` would not. Not touching
  a hardware-verified display file wins.)*
- **`u_map`** is new: `[r param]` → `[route knob-9 …]` → scale → `[s tempo]`. **Explicit route
  branches, not a table.** One branch per mapping, statically visible — which is what keeps the
  allowlist auditable, since a data-driven `[send]` could write any global name with no evidence in
  the patch. A `[text]` table is the v0.3 upgrade once there are rows enough to justify it, and the
  structure should admit `[r mode]` selecting between tables without being rebuilt.
- **The one Phase 5 mapping: `knob-9` → `tempo`, 0–127 → 60–180 BPM.** Group 9 is the spare —
  [ref-hardware.md](ref-hardware.md) already reserves it "for global volume or master tempo". 60–180
  gives ~0.94 BPM per step; 40–200 would be 1.26 and harder to place.
- **A control's range and the legal range are different decisions.** `u_map` picks 60–180 for that
  fader; `u_tempo` clamps at 20–300 so a bench, a tap tempo or an LFO is not limited by what one
  fader chose.

### Step 2 — `u_tempo`

Owns master BPM, the pulse oscillator, MIDI realtime out and transport state.

- `[r tempo]` → clamp 20–300 (`warn u_tempo bpm-out-of-range` when it bites) → store → `/ 60` → `× 24`
  → `[phasor~]` at the **pulse** rate.
- **`loadbang` publishes 120 on `tempo` once, and that is the only time `u_tempo` writes that bus.**
  It stores what it hears without re-emitting, so there is no loop, and consumers that came up first
  still get a value.
- Pulse detection: **`[threshold~ 0.5 2 0.1 2]`**. A `phasor~` ramps 0→1 and wraps, so it crosses 0.5
  upward exactly once per cycle and falls below the 0.1 rest value on the wrap — one bang per pulse.
  ✅ `threshold~` is in the local 0.49 binary. The 2 ms debounce caps the usable pulse rate near
  250 Hz ≈ 625 BPM, far above the clamp.
- Per pulse: emit **248** and count; `[mod 24]` → 0 bangs `[s clock]`. **Counting rather than running
  a second oscillator is what makes the beat and the MIDI pulse the same clock by construction.**
- **248 goes out on Pd MIDI ports 1 and 3** — the Launchpad, which paces its own LED flash and pulse
  from incoming beat clock, and the SP-404, whose BPM SYNC learns tempo only from pulse intervals.
  `wire.sh` already wires `Pure Data:4` and `Pure Data:6`, so no change there. ⬜ Confirm `[midiout]`
  takes a port creation argument; if not, use `u_init`'s proven pattern of setting the port into the
  cold inlet at load.
- **Clock never stops.** 248 flows whether the transport is running or not; only 250/252 mark
  transport. Stop the pulse stream and the 404 stretches to a stale tempo. **This is the least obvious
  thing in the step** — both [ref-hardware.md](ref-hardware.md) and
  [ref-software.md](ref-software.md) say clock is not decorative.
- `[r start]` → 250, reset the pulse phase and the 24-counter, set running. `[r stop]` → 252, clear
  running. **Never 251** — nothing in the rig has Song Position Pointer, so resume-from-position does
  not exist and a Continue would be a lie.
- `[r panic]` → 252 + all-notes-off + stopped, **clock still running**.
- **Tempo goes to the footer**, not the param layer: `disp` → `status <n>-bpm`, sticky and always
  visible. It supersedes `v0.2-ready` once the clock is up, which is the right progression, and
  `panic` still overwrites it — correctly.

⚠️ **Say plainly, in the patch and here, what audio-domain buys.** It does **not** reduce the ~1.45 ms
jitter on the MIDI byte: `threshold~` reports on block boundaries exactly as `metro` fires on them,
and [ref-midi.md](ref-midi.md) already records that as unfixable in vanilla Pd. What it buys is
phase-continuous glitch-free rate changes, and **one shared phase that grain-rate code reads as a
signal**, sample-accurately, so MIDI clock and grain timing cannot drift apart. Without this written
down someone will later try to "fix" jitter that cannot be fixed.

### Step 3 — `c_clock`

**`u_tempo` is a master reference, not the clock.** Cut It runs poly-tempo — see *Poly-tempo* in
[ref-conventions.md](ref-conventions.md). `c_clock` is a separately instantiable abstraction owning
its own rate and time signature, optionally slaved to master by a ratio. **Do not build a clock
singleton**; retrofitting one once Phases 6–8 depend on it is the expensive mistake this plan exists
to avoid.

- `[c_clock <ratio> <beats-per-bar>]`. `[r tempo]` × ratio → its own `[phasor~]`.
- Outlets: `[outlet~]` the raw phase, for sample-accurate grain use; then beat bang, beat-in-bar, bar
  bang. Time signature is a `c_clock` concern, never a global.
- `[r start]` → phase to 0. **That start-reset is the only thing aligning instances** to each other
  and to `u_tempo`; equal frequencies derived by the same arithmetic then hold alignment.
- `[r stop]` does not halt it. A running phasor nobody reads is silent, and halting is the consumer's
  business.
- **No instances in the deployed patch**, because nothing consumes a beat yet. The bench instantiates
  two — which still exercises them under real DSP on the device, since the bench loads as a third
  patch alongside `mother.pd` and `main.pd`.

### Step 4 — `g_led`, and the aux button

**`g_led` is the sole owner of `led`**, the same way `g_oled` owns the screen: `[r disp]` → selector
`led <state>` → colour, so callers send semantics and never a colour. The rule is already in
[ref-conventions.md](ref-conventions.md); this is the abstraction that honours it. Phase 6 (mode) and
Phase 8 (save in progress) both want it, and mother already sets `led 0` on `quitting` so the safe
exit needs nothing.

**Aux drives the transport:** `[r aux]` → toggle → `start` / `stop`. ⬜ Confirm mother does not
intercept a long aux press — the encoder is known to be contested via `enableSubMenu`, so do not
assume aux is clean just because nothing has claimed it.

### Step 5 — hand over a two-machine test procedure

**The last step of the phase is writing down how to check it**, in an order Brendan can follow with
one cable move. Phase 4 established the shape and it worked: every Mac step first with the nano still
on the Mac, then move the cable once, then the device steps. Not a summary of what was built — a
procedure, with the expected result stated *before* each action, including the steps whose correct
result is that nothing happens.

It must name: the one-time Mac setup (**DSP on**, and the IAC bus if the loopback is used, at input
slot 3); what to look at for each check and what a pass looks like; the exact commands; and which
failures point at configuration rather than the patch. Goes into
[plan-tests.md](plan-tests.md) as a new session, the way *The procedure, in order* did for Phase 4,
**and** is given to Brendan directly in chat, since that is where it gets used.

### Files

| File | Change |
|---|---|
| `Cut It/u_tempo.pd` | **new** — Step 2 |
| `Cut It/c_clock.pd` | **new** — Step 3 |
| `Cut It/u_map.pd` | **new** — Step 1 |
| `Cut It/g_led.pd` | **new** — Step 4 |
| `Cut It/m_nano.pd` | `[s param]` beside `[s disp]` |
| `Cut It/u_root.pd` | instantiate the four |
| `Cut It/u_mother-stub.pd` | panel: an LED indicator, a beat `bng`, a BPM readout |
| `tools/phase5-bench.pd` | **new** — same shape as `phase4-bench.pd` |
| `ref-conventions.md` | `param` in the allowlist |
| `ref-midi.md`, `plan-tests.md`, `tools/README.md` | clock out, a new session, the bench |

### Verification

After **every** patch edit, both:

```sh
python3 tools/pd-layout-check.py "Cut It"/*.pd
/Applications/Pd-0.49-1.app/Contents/Resources/bin/pd -nogui -noaudio \
    -path mac-stubs -send "pd quit" "Cut It/main-dev.pd"      # silence == pass
```

⚠️ **On the Mac the clock does nothing until DSP is on.** `threshold~` is a signal object, so with
Pd's *Compute Audio* unchecked there is no phasor and no pulse — which looks exactly like a broken
patch. Same class of trap as Phase 4's "no MIDI input saved in preferences".

**Verify what Pd actually emits with a loopback through the macOS IAC bus.** Audio MIDI Setup →
enable IAC; Pd → MIDI Settings → output device 1 = IAC, **input device 3 = IAC**. Slot 3, not 2:
slot 1 must stay the nano so `[u_root 1]` still holds, and slot 2 would collide with it. Then
`[midirealtimein]` reads back the real bytes. ⬜ Unverified that 0.49 on macOS enumerates IAC and
that `midirealtimein` reports on it; ✅ `midirealtimein` *is* in the local binary, and the fallback is
`aseqdump` on the device.

1. **24 PPQN.** Count 248s for 60 s at 120 BPM → 2880, ± a few. Run a `metro`-derived reference in
   the same patch and show they agree, so the accuracy claim is measured rather than asserted.
2. **248 continues while stopped**, 250 on start, 252 on stop, never 251.
3. **Tempo from the nano's knob 9**; the footer follows; out-of-range warns.
4. **Two `c_clock` at ratios 1 and 1.5** — 20 and 30 beats in 10 s at 120 BPM.
5. **Phase 3 *and* Phase 4 regressions.** `m_nano` changed, so `phase4-bench.pd` is the gate; run
   `phase3-bench.pd` too, since a footer now carrying the BPM touches the home layer.
6. **Device:** aux toggles transport and the LED follows; **the 404's own display follows the tempo**
   — that is the real *done when*; then CPU and datagram rate, comparable to items 21 and 37.

### Risks specific to this phase

- **`param` is a new allowlisted global** and the allowlist is deliberately hard to change. If `u_map`
  turns out to want something `param` cannot carry, fix the bus rather than adding a second.
- **Clock out to two ports adds ~96 MIDI messages/second** on top of the display's ~110 datagrams.
  Almost certainly free at 5–8 % CPU, but measure — that measurement is what closed the equivalent
  question in Phase 3.
- **`[midiout]`'s port argument and the IAC loopback are both ⬜.** Neither blocks the build; both
  would cost a rework of how the clock is *verified*. Check them early.

---

## Phase 6 — Launchpad

`m_launchpad`, `g_grid`

The most complex piece, deliberately late. Pad input on Pd channel 1 with `r*10+c` decode and
polyphonic aftertouch. `g_grid` is the same arbiter shape as `g_oled` — playhead, slot state,
mode and meters all contend for 64 pads.

Batch LED updates: **one SysEx can carry up to 106 colour specs**, so a full-grid repaint is
one message, not 64.

Flash and pulse are **synced to MIDI beat clock**, so animation follows `u_tempo` for free — which
is why Phase 5 sends clock to the Launchpad's port as well as the 404's.

**This is also where `mode` finally gets a driver.** The Launchpad is the right home for it because it
is the only device Pd can light, so mode state becomes visible rather than remembered.
`u_init`'s `pd launchpad-init` subpatch lifts wholesale into `m_launchpad`.

**Done when:** pads report position, velocity and pressure; the grid shows mode state; a full
repaint is one message.

## Phase 7 — Phone status link

`u_net`

Promotion of `tools/status-display/` to an abstraction. Subscribes to `disp` and forwards over
`[netsend -u]`, plus the heartbeat.

**State never events; fire and forget; the Organelle never waits.** Rate limiting lives here,
not in the callers.

**Done when:** every parameter shown on the OLED also reaches the phone, and pulling the plug
shows `NO-LINK` within 1.5 s.

## Phase 8 — State and presets

`u_state`

Hooks `[r saveState]`, writes to `/tmp/state/` within the **0.5 s budget**, reads from
`/tmp/patch/` on load. Plain text via `[text]`, git-diffable.

Gets Save and Save New from the Organelle's own menu for free.

⚠️ **Save New is broken for patches in a category folder, and `deploy.sh` makes it worse.**
`save-new-patch.sh` derives the name with `ls /tmp/curpatchname`, and mother records whatever
name it was given. A `deploy.sh` load passes `!/Cut It`, so that becomes `/tmp/curpatchname/!/Cut It`
and the script reads back `!` — Save New then creates a folder called `! 2`. Selecting the
patch from the menu leaves the correct `Cut It`. Plain Save is unaffected; it works off the
`/tmp/patch` symlink. **Verify this phase against a menu-selected patch, not a deploy-loaded
one**, and decide then whether to have `deploy.sh` repair `/tmp/curpatchname`.

**Done when:** control state survives Save → reload, and Save New produces a working variant in
the patch menu.

---

## Open questions

**Every unresolved question in the project lives here or in [plan-tests.md](plan-tests.md).**
The `ref-*` documents state what is known and mark uncertainty with ⬜, but they carry no plans —
when something there is unverified, the work to resolve it is listed below.

### Blocking a v0.2 phase

| Question | Blocks | Where it stands |
|---|---|---|
| **SP-404 pad note range** — measured 47+*n* here, Roland's chart says 35–51 | Phase 5's *done when*, and v0.3's `m_404` | Only pads 1 and 2 were ever checked. **This is the one that silently corrupts work** — sequencing code written against the wrong range looks correct and triggers the wrong pads. Sweep all 16 with `tools/midi-drive.pd` |
| **What drives `mode`** | Nothing hard, but the mode filter has had no physical driver since Phase 4 | Phase 6, on the Launchpad — the only device Pd can light, so the state becomes visible. Until then the bench drives it, which is how items 19 and 21c were verified anyway |
| **Does mother intercept a long aux press?** | Phase 5 Step 4 | ⬜ Assumed clean because nothing has claimed it, which is exactly the reasoning that was wrong about the encoder. Cheap to check |
| **`[midiout]` port creation argument** | Phase 5 Step 2 | ⬜ `u_init` sets the port into the cold inlet at load instead, which works; confirm whether the shorter form does too |
| **Launchpad perimeter CC numbers** | Phase 6 | Documented 📄, never confirmed on this unit. Ten minutes with `tools/lp-monitor.pd` |
| **Do flashing / pulsing LEDs track a *modulated* tempo?** | Phase 6 | The modes work ✅; tracking a sweeping tempo is ⬜. Phase 5 makes a sweeping tempo possible, so this becomes testable for the first time |
| **Full-load power** | Phase 6 | Never run with three controllers plus the wifi dongle — the cable shortage. Presents as intermittent MIDI dropouts rather than an obvious failure, so if Phase 6 produces flaky Launchpad behaviour, **suspect the hub before the code**. [plan-tests.md](plan-tests.md) item 5 |
| **Save New in a category folder** | Phase 8 | ⚠️ Already diagnosed — see the Phase 8 note above. Verify against a menu-selected patch, not a deploy-loaded one |

### The last thing that could force a redesign

**How the 404 places external input in the stereo field.** ✅ The Organelle's own TRS split is
verified — `adc~ 1` is the tip and the channels are independent — but the 404's *internal*
routing of its external input is not, and no cable will answer it. Blocked on the TRS Y-cable;
procedure in [plan-tests.md](plan-tests.md) Session 3, items 12–13.

### Not blocking anything, but worth knowing

| Question | Where it stands |
|---|---|
| **Can Pd emit an OSC blob?** | Gates `gWaveform` and `gFrame` — so it gates ever drawing the captured buffer, which is what would stop playhead placement being blind. Untested ⬜ |
| **Does the 404's *pattern playback* transmit notes?** | `SEQ Note Out` is On and pad presses transmit, but no pattern has been captured. Determines whether the 404 is a compose-time authoring surface. Watch for the reported stray continuous C |
| **Can Novation Components disable the onboarding drive?** | A cleaner fix than the `mount.sh` guard, since it changes nothing on the Organelle. Untried |
| **`/led/flash`** | ✅ Exists in the `mother` binary and is unreachable through `mother.pd`. Deliberately unused — it needs raw `oscOut`, which would put a second writer on that name. See [ref-display.md](ref-display.md) |

### Stage-readiness — the phone link

Everything about the PdParty display works ✅ except what makes it trustworthy in a venue.
Phase 7 or later:

- **Organelle as its own access point.** `hostapd` and `dnsmasq` are installed and the chip
  supports AP mode ✅, but it has never been configured ⬜. It removes the venue-WiFi dependency
  and is the last thing between the phone display and being stage-worthy.
  [plan-tests.md](plan-tests.md) Session 5 — read its warning first, since bringing up an AP
  drops SSH.
- **Rate limiting on the wire.** Every CC change currently sends a packet, so a fast fader sweep
  floods. Needs coalescing to ~20 Hz with a guaranteed trailing edge. The OLED gets this free
  because layers hold state; the phone link does not.
- **Phone hardening.** Auto-Lock Never ✅; Do Not Disturb and Guided Access still to set.
- **Cosmetic.** The value is an `nbx`, which draws box chrome around the number; a `cnv` label
  through `[makefilename %g]` would be pure text. Dynamic labels are proven ✅.

### Still to acquire

| Item | For |
|---|---|
| **1/4" TRS male → 2× 1/4" TS male** (insert cable) | ⚠️ **The critical cable in the rig** — nothing else merges the 404's two outs into the Organelle's single input jack. Blocks Session 3 |
| **Class-compliant USB→DIN MIDI interface** | The Volca FM. Roland UM-ONE mk2 in its class-compliant "TAB" position, iConnectivity mio, or similar. **Phase 5 makes this worth buying** — clock and note-out have somewhere to go once it exists |
| **Dynamic microphone** | Dynamic rather than condenser — better SPL handling and far better feedback behaviour in a rig where a mic feeds a processor that feeds the PA |

Ordinary cables — USB-A→C for the 404, TS patch cables, 3.5mm TRS→2× TS for the Volca,
XLR→1/4" for the mic — are probably already in the box; the full list is in
[ref-hardware.md](ref-hardware.md). **Optional:** a *MeeBlip cubit duo* replaces the MIDI
interface and the original cubit in one box, worth it only if more DIN synths arrive. Don't buy
a ground-loop isolator pre-emptively — but know it is the cause if hum appears, rather than
chasing a bad cable.

### OLED UI refinement — v0.3

Phase 4 made the display *correct*; it is not yet *good*. From reading it on the hardware:

| Wanted | Note |
|---|---|
| **Sliders instead of numbers** | a bar reads faster than a number for a continuous control. `gFillArea` already does this for the meters, so the drawing is solved — what is not is how a bar and a name share 128 px, and what happens when five of them stack |
| **Show where the control was when the edit began** | a tick at the value the fader held when you first touched it, so you can see how far you have moved and get back. Needs a per-control "value at first touch", which is a new field in the param store — cheap, since the store already keys by name |
| **Buttons should not display `1`** | the `1` is a placeholder for "pressed". What a button shows depends on what it is mapped to, so this resolves itself once `u_map` gives them meanings |
| **A mapped control shows two rows** | Phase 5 creates this: `knob-9 64` from `m_nano` and the tempo from `u_tempo`. Mitigated by putting tempo in the footer, but it is the first concrete case of why `m_nano` must eventually emit **parameter** names rather than control names |
| **Transport keys as scene selection** | ✅ they are ordinary CC buttons now. What remains is the *mapping*, which is `u_map` work in v0.3 |

The first two are real design work rather than plumbing, and both want the hardware in front of
you. The param store is the right place for both: it already holds a name, a value, a unit and a
frame stamp per row.

### Deliberately deferred

| Deferred | Why |
|---|---|
| **The four filter stages** | v0.3 — this plan is the floor they stand on |
| **Footswitch / expression pedal** | `mother.pd` exposes `fs` and `exp` on the pedal jack, one or the other, not both. Noted so it isn't rediscovered as news; it stays the obvious control to reach for when both hands are busy |
| **SP-404 and Volca mapping** | `m_404` and the DIN interface, which isn't bought |
| **Compose-mode capture** | Needs the mode system working first |
| **nanoKONTROL scenes** | Four scenes exist but switch locally, so Pd is never told — hidden state. If they are ever used, assign **distinct CC numbers per scene** so Pd infers the active one from which CCs arrive |
| **A pre-set checklist for the 404** | Its hidden menu state — ExtIn monitoring, bus assignments, input FX — is the remaining "wrong knob" risk in the rig |
| **`u_map` as a `[text]` table** | The route-branch form is statically auditable and there is one mapping. Revisit when the count justifies it, which is v0.3 |

---

## Risks

**The `m_` layer is the one boundary that is genuinely expensive to retrofit.** If `e_chop` ever
learns that a nanoKONTROL exists, that is permanent. Phase 5's `u_map` is what keeps that boundary
honest once controls start meaning things.

**The display arbiter was the piece most likely to be wrong first time** — contention, TTL and
rate limiting are easy to describe and fiddly to tune. Built early (Phase 3) precisely so there
was time to live with it; now verified on hardware, and Phase 4's reversal of its ordering scheme is
exactly the kind of thing that early build bought time to discover.

**Timing is architectural.** Grain clocks must be audio-domain from the first line, and
`u_tempo` must be a master reference *plus* an instantiable `c_clock`, not a singleton.
Retrofitting either once Phases 6–8 depend on them is the expensive mistake this plan exists to
avoid.
