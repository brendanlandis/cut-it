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
  m_nano        m_launchpad      m_organelle        ← device mapping
  ch 17/18        ch 1          aux + knobs 1-4
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

⚠️ **This diagram is the target, not the current state.** ✅ Everything in it exists except `u_net`
(Phase 7) and `u_state` (Phase 8) — `m_launchpad` and `g_grid` arrived in Phase 6, along with the
first `c_clock` instance the diagram never showed. The allowlist in [ref-conventions.md](ref-conventions.md) is the authority on
which buses actually exist.

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
| 5 | ✅ hardware | Clock and transport |
| 6 | ✅ hardware | Launchpad, the grid arbiter, the `mode` driver, the replug watchdog |
| **7** | **next** | **Phone status link** |
| 8 | | State and presets |

Details of 0–6, and every correction they produced, are in
[ref-build-log.md](ref-build-log.md). **Read its corrections before writing any Pd** — most of
them were found by measuring something a plan had asserted, and one of them by measuring the
thing that did the measuring.

---

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
| **SP-404 pad note range** — measured 47+*n* here, Roland's chart says 35–51 | v0.3's `m_404` | Only pads 1 and 2 were ever checked. **This is the one that silently corrupts work** — sequencing code written against the wrong range looks correct and triggers the wrong pads. Sweep all 16 with `tools/midi-drive.pd` |
| **Full-load power** | v0.3's `m_404` — no longer Phase 6 | ✅ **Two** controllers plus the wifi dongle on a hub held up across two sessions, a 25-step bench run, a hot replug and sustained 500 BPM, with no dropouts. ⬜ **The SP-404 has still never been powered alongside them**, and that is the whole of what item 95 has left. Blocked by the cable shortage. **A marginal hub presents as intermittent MIDI dropouts rather than an obvious failure**, so when it goes in, suspect power before code. [plan-tests.md](plan-tests.md) items 5 and 95 |
| **Save New in a category folder** | Phase 8 | ⚠️ Already diagnosed — see the Phase 8 note above. Verify against a menu-selected patch, not a deploy-loaded one |

### The last thing that could force a redesign

**How the 404 places external input in the stereo field.** ✅ The Organelle's own TRS split is
verified — `inL` is the tip, `inR` the ring, and the two are genuinely independent — but the 404's
*internal* routing of its external input is not, and no cable will answer it. Blocked on the TRS
Y-cable; procedure in [plan-tests.md](plan-tests.md) Session 3, items 12–13.

### Not blocking anything, but worth knowing

| Question | Where it stands |
|---|---|
| **`g_grid` lights LED index 10 before the first beat arrives** | ⬜ The beat store starts at 0 and `0 + 10` is a left-column ring button, so the very first painted frame carries a stray white light. **Cosmetic and Mac-only**: on the device mother enables DSP at 200 ms, so beats are flowing well before ownership rises at ~3 s and the frame is never seen. One box to fix — seed the store at 1 — and deliberately not fixed here, because this round of work was scoped to tests. Found by `tools/phase6-assert.sh`, which reports it as a NOTE rather than a failure |
| **A panic blanks the Launchpad until the patch is reloaded** | ⚠️ New in Phase 6, deliberate, and currently harmless. `panic` returns the device to Live Mode and nothing re-enters Programmer Mode except `u_init`'s boot — so the grid stays the device's own for the rest of the session. **Nothing on the Organelle sends `panic`**; only the bench and the dev panel do. Revisit if a panic ever becomes performer-reachable, and note the trade: the escape hatch is worth more than the display |
| **The six modes are named `mode-1`…`mode-6`** | Placeholders, three `compose` and three `perform`. The names are six message boxes in `u_map` and nothing else has to change. ⚠️ The **ratio** is not arbitrary: `u_err` routes on those two words, so a split weighted toward `perform` would make most mode selections silently quieten the error display |
| **CC 99, the Launchpad's top-right corner** | ⬜ The one ring button never pressed. Nothing needs it |
| **Does the System menu's MIDI Config page re-open mother's MIDI gates?** | ⬜ `u_init` closes `midiInGate` and `midiOutGate` 2 s after load, which beats the mother binary's own push. Entering *MIDI Config* mid-session sends `/midich` and `/midiConfig` and may push the gates again — reopening the CC 21–26 collision that made a nano button toggle the transport ([plan-tests.md](plan-tests.md) item 76). Cheap to check: open the page, leave it, then press `btn-t-5` |
| **The Organelle drops its wifi after a while.** | ⬜ Reproducible enough to be annoying — the connection is there after a deploy and gone an hour later, needing a manual reconnect. Costs nothing during a session that is already underway, but it breaks `deploy.sh` and `fetch-errors.sh` without warning, and it would take the phone display down mid-set. Unattributed: could be the dongle, power, the AP, or `wifi_control.py`. **Session 5's access-point work would sidestep it entirely**, which is the argument for doing that before chasing this |
| **`[midiout]`'s port creation argument** | ⬜ and **unneeded** — `u_tempo` uses `u_init`'s proven pattern, the port sent to the cold inlet at load, and ✅ item 63 fired a real 404 pad through exactly that. What stays open is only whether `[midiout 3]` works, and **the obvious experiment is invalid**: Pd 0.49 does not warn about extra creation arguments at all — `[loadbang 7]` loads in silence — so a clean syntax check proves nothing. Answering it needs a real MIDI destination on two ports, or the 0.49 source |
| **Does `mother.pd` stream the knob positions continuously, or only on movement?** | ✅ **Moot.** Hands off the device the OLED sits on the meters, so nothing pins the param layer open — but that cannot separate "does not stream" from "the `[change -1]` guard filters it", and the guard is staying either way. Item 68 |
| **Are the OLED's 16px and 8px param rows legible at arm's length?** | ⬜ A judgement, not a test — and the last thing about the display nobody has actually decided. The geometry is verified through `oscOut`, and all three layouts have now been *rendered* on the device with their row behaviour passing (item 80), but they were watched for correctness rather than read. [plan-tests.md](plan-tests.md) item 39; feeds the *OLED UI refinement* work below |
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
| **A mapped control shows two rows** | ✅ Phase 5 created this: `og-knob-1 0.53` from `m_organelle` and the BPM from `u_tempo`. Mitigated by putting tempo in the footer, but it is the first concrete case of why an `m_` layer must eventually emit **parameter** names rather than control names — which is `u_map`'s job to hand back |
| **Transport keys as mode selection** | ✅ **Done in Phase 6** — all six now select a mode, shown as a lit lamp on the Launchpad's top row. This supersedes Phase 4's "scene selection" intent: scenes and modes were the same idea, and modes is what it is called now |

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
learns that a nanoKONTROL exists, that is permanent. ✅ `u_map` now keeps that boundary honest, and
is the only file that says what a control means.

**The display arbiter was the piece most likely to be wrong first time** — contention, TTL and
rate limiting are easy to describe and fiddly to tune. Built early (Phase 3) precisely so there
was time to live with it; now verified on hardware, and Phase 4's reversal of its ordering scheme is
exactly the kind of thing that early build bought time to discover.

**Timing is architectural.** Grain clocks must be audio-domain from the first line, and
`u_tempo` must be a master reference *plus* an instantiable `c_clock`, not a singleton.
Retrofitting either once Phases 6–8 depend on them is the expensive mistake this plan exists to
avoid.
