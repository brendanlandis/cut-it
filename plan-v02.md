# Cut It v0.2 — Infrastructure Plan

The scaffolding the instrument stands on: startup, audio path, controller mapping, display,
state. **No musical DSP.** When this is done, Cut It makes no interesting sound — it passes
audio through, knows what every control is doing, and can tell you about it. The four filter
stages are built on top of this, afterwards.

v0.1 is not being extended. Its plans are kept in [! v0.1 plans/](<! v0.1 plans/README.md>) and
the patch itself in [! v0.1 plans/patch/](<! v0.1 plans/patch/README.md>) — **reference for
intent, not code to lift.** All of it predates the conventions; assume it is naive.

Read [ref-conventions.md](ref-conventions.md) first — naming, `$0`, `[trigger]` discipline
and the global allowlist are assumed throughout.

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
| nanoKONTROL full CC map incl. transport on Pd ch 18 | [ref-midi.md](ref-midi.md) |
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
      mode · tempo · clock · start/stop · panic · err · disp
                     │
    ┌────────────────┼────────────────┐
    │                │                │
  m_nano        m_launchpad         m_keys          ← device mapping
  ch 17/18        ch 1               mother
    │                │                │
    └────────────────┼────────────────┘
                     │
              (v0.3: e_chop, e_pitch, e_trem, e_verb)
                     │
    ┌────────────────┴────────────────┐
  g_oled                           g_grid           ← display arbiters
  OLED                             Launchpad
```

**The `m_` layer is the load-bearing boundary.** Nothing below it knows a nanoKONTROL exists.
A device sends `mode`, `tempo` or a named parameter onto a bus; what consumes it is decided
elsewhere. This is what makes the compose/perform split tractable and it is the one boundary
that is genuinely expensive to retrofit.

---

## Build phases

Each phase is independently testable and leaves the patch in a working state. **Phases 0 and 1
require no hardware**, which matters because the Organelle is not always on the desk.

### Phase 0 — Skeleton and the off-device shim ✅ **done**

`main.pd`, `main-dev.pd`, `u_root`, `u_mother-stub`, `deploy.sh`

Two thin entry points with all content in `u_root` — that is what stops them drifting.
`main-dev.pd` instantiates `u_mother-stub`, the Mac-only stand-in for `mother.pd` and the
**one sanctioned exception** to the reserved-name rule; `main.pd` does not, so the device never
sees it. It has since grown into the full dev panel — see *Seeing it off-device* in
[ref-display.md](ref-display.md).

`deploy.sh` closes the loop: **syntax check → scp → reload → load**, no physical interaction.
The check is blocking and gates on *output*, since Pd exits 0 even on load errors.

**Two corrections, both read out of `/root/Organelle_UI/`:** `/loadPatch` resolves against the
current patch directory, so the argument must be `!/Cut It`, not `Cut It`; and `enc` is `1`/`0`
for up/down, not `±1` — as are `aux` and `encbut`.

### Phase 1 — Audio path ✅ **done**

`u_root` audio chain, `u_level`, `g_levels`

`[r~ inL]` / `[r~ inR]` straight through to `[throw~ outL]` / `[throw~ outR]`, with a
`u_level` tap on each input reporting onto the `disp` bus. Deliberately first: it proves the
whole signal chain with no DSP to blame. Also established here because Phase 3 depends on both:
the `disp` bus, and the rule that exactly one abstraction owns `oscOut` and `screenLine*`.

**Three corrections, all read off the device:**

- **Not `adc~`/`dac~`.** `mother.pd` owns the sound card — see *Audio I/O* in
  [ref-conventions.md](ref-conventions.md).
- **Not `/oled/vumeter`.** mother already drives it, and it lives in the info bar, which is now
  off by decision — see [ref-display.md](ref-display.md).
- **`gShowInfoBar 3 0` moved out of Phase 2 into here**, because it must go out on every redraw
  rather than once at init, which makes it the display's job and not startup's.

**Done when:** ✅ audio is audible and the volume knob controls it; both levels on the OLED read
the 18–19 noise floor at rest. Covers [plan-tests.md](plan-tests.md) item 11 through the real
patch; items 12–13 stay blocked on the TRS Y-cable.

### Phase 2 — Startup sequencing ✅ **done**

`u_init`, `wire.sh`

**Verified end to end on hardware** — `[shell]` runs `wire.sh`, `aconnect -l` shows both
directions wired, and captured pads read `r*10+c` with live velocity.

`loadbang` fires before ALSA connections exist, so rather than scattering `[del]` objects one
abstraction owns the ordered startup:

1. wire `aconnect` via `[shell]` (pattern from `tools/wire.sh`)
2. wait for ALSA
3. Launchpad → Programmer Mode by SysEx
4. clear the Launchpad grid — **LED state survives mode switches**

*(`gShowInfoBar` is deliberately not on this list — it moved to Phase 1, because mother
restores the info bar after every patch load, so it must be re-sent on each redraw.)*

**Each stage reports to the OLED as it completes.** With no console, that is the boot
diagnostic — a patch stuck at stage 3 tells you the Launchpad never answered.

**Also here: panic / safe exit.** `[r panic]` returns the Launchpad to Live mode and clears
everything, fired on `quitting` — which `mother.pd` sends, giving the patch **100 ms**. Pd 0.49
has no `closebang`, so that is the only shutdown hook there is. Without it, a crash in
Programmer Mode means power-cycling the Launchpad.

**The lesson here was hardware, not code.** The Launchpad would not configure behind three
chained USB hubs (`can't set config #1, error -32`) and the same topology wedged the wifi
dongle at boot; plugged directly in, it works first time. Evidence in
[ref-hardware.md](ref-hardware.md), tracked as Session 3b in [plan-tests.md](plan-tests.md).

### Phase 3 — Display and errors ✅ **done, verified on hardware**

`g_oled` (replaces `g_levels`), `u_err`

The arbiter: layers with priority and TTL, `home` < `param` < `modal` < `alert`, sole owner of
`oscOut` and `screenLine*`. Callers send semantics, never layout — `[s disp]` with
`chop-size 43 %`. Full description and geometry in [ref-display.md](ref-display.md).

**Verified on the Organelle**, all fourteen steps of `tools/phase3-bench.pd` — every layer, the
priority order, the mode filter and the 30 s safety TTL. Details in
[plan-tests.md](plan-tests.md) items 21–21c.

**Throughput is not a problem:** **110 UDP datagrams a second** at **8.2 % CPU**, load 0.16.
That also clears the phase's biggest unknown — `packOSC` drops a mismatched typetag *before*
`udpsend`, so a full datagram rate proves the **runtime typetag builder produces tags the real
`packOSC` accepts**, which the Mac could never demonstrate having no `packOSC` at all.

**Three corrections**, all now in [ref-conventions.md](ref-conventions.md):

- **`u_err` does not draw.** This section used to say it writes to the ALERT buffer, which
  contradicts *Banned* — two writers, one screen. It filters and forwards onto `disp`.
- **The alert draws to screen 3**, not the ALERT buffer. Nothing underneath needs preserving
  when the frame is rebuilt from state ten times a second. ✅ Buffer 4 has since been proven
  writable and switchable — and deliberately still isn't used, because it would make the alert
  the one edge-triggered layer in a state-driven arbiter.
- **`route`'s remainder trap is wider than documented** — any remainder whose first atom is a
  symbol arrives as a selector, not just a lone symbol. And `[list split n]` on exactly *n*
  atoms silently never fires its right outlet, which is what would have made `grain 12` draw as
  `grain 12 %`.

⚠️ **Deploy this phase with `./deploy.sh --clean`** — there is no rsync on the device, so a
plain deploy would leave the deleted `g_levels.pd` behind to shadow the new display.

#### Layout decisions, settled

- **The home screen is the two level meters** — `gFillArea` bars, not numbers, with a small 8px
  readout so they stay calibratable and the measured reference marks drawn in: noise floor
  **18–19**, gate threshold **25–30**.
- **A moving knob shrinks the meters** and gives the parameter the rest of the screen at 24px,
  readable at arm's length. The meters never vanish — signal presence is always visible.
- **A parameter readout lingers ~1.2 s**, then the meters expand back. Expected to be tuned by
  living with it.

#### Errors follow the mode, not a severity guess

| `mode` | Shows |
|---|---|
| compose | **verbose** — every error reaches the screen |
| perform | **quiet** — only failures; warnings stay on the bus |

This is why `err` carries a level: **`<level> <source> <text>`**, level ∈ `warn` `fail`.
Nothing drives `mode` until Phase 4, so **default to verbose** — it degrades safely.

Errors **time out** rather than waiting to be dismissed; a stuck error covering the display
mid-set is the worse failure. **The bus is unfiltered; only the screen is filtered**, so the
by-hand console sees warnings even in perform mode. This does not catch Pd's *own* runtime
errors — those still go to tty1.

### Phase 4 — nanoKONTROL, a persistent error log, and a multi-parameter display ✅ **built**

`m_nano`, `u_err`'s log, `g_oled`'s param layer

**Deployed and running on the Organelle.** Everything that does not need the controller plugged
into the device is verified — the decode (all 21 branches), the three display layouts and their
ageing, the Phase 3 regression, and the error log surviving a patch reload with wall-clock session
markers. ⬜ **What remains is the controller sweep on the device itself**, where the nano is Pd
input slot 2 and the channel is 17; steps 15–17 of `tools/phase4-bench.pd` exist for it. Results in
[plan-tests.md](plan-tests.md) Sessions 4b and 4c.

**Three bugs this phase found by measuring rather than reading**, all now fixed and recorded:

- A **reject outlet carries a value, not a bang.** `[select 1 2 3 4 5 6]`'s reject emits `cc − 40`,
  which landed on an `[f]`'s *hot* inlet and overwrote the stored CC — so an unknown CC 47 reported
  itself as `cc-7`. Any `[f]` behind a reject outlet needs a `[t b]` in front of it.
- A **`[print]` at `loadbang` breaks `deploy.sh`**, which gates on *output* rather than exit status.
  `m_nano`'s channel diagnostic now sits behind `[del 2000]`: the check quits at load and never sees
  it, while the by-hand console still does.
- **`pgrep pd` matches substrings** — on this device a kernel thread — so `fetch-errors.sh` reported
  pd running while it was killed. `pgrep -nx pd`.

**This is the first phase where a physical device can misbehave while nobody is watching**, and
that reframes it into three pieces of work. The order is fixed: step 0 exists so that steps 1
and 2 are debuggable.

0. **Errors must survive.** `u_err` prints every error unconditionally, but the menu-launched
   patch sends stdout to tty1 — so in normal operation an error draws on the OLED for 2–4 s and
   is then gone forever. Tolerable when the only inputs were four knobs you were holding; not
   tolerable once a surface with 42 controls is attached.
1. **`m_nano`** — the mapping layer. CC only, no LEDs, no SysEx.
2. **The display must show more than one thing at once.** With 18 continuous controls, moving two
   faders together is ordinary use, and today's param layer holds exactly one name and value, so
   two movers alternate at the 10 Hz frame rate.

**Done when:** every slider, knob and button is identified by name on the OLED, the transport
buttons change `mode` visibly, several controls can be read at once, and an error raised while
playing can be read off the Mac the next day.

#### Develop against the real nanoKONTROL, plugged into the Mac

It is USB class-compliant and needs no driver, so the real `[ctlin]`, the real CC numbers and
real momentary behaviour are all exercised off-device. Nothing is faked, which is what avoids
needing a new global bus — the dev panel is a *sibling* of `u_root` and could only reach inside it
through a global name, so the allowlist in [ref-conventions.md](ref-conventions.md) stays
untouched.

The catch, and the design consequence: **Pd numbers MIDI channels by device slot.** ✅ Measured
with `pd -listdev` — on the Mac the nano is input device **1** and the only one, so it lands on
**channel 1**; on the Organelle it is device 2, so **channel 17**. The channel block therefore
becomes a creation argument, and this is the one place the two entry points are allowed to
differ:

```
main.pd       [u_root 17]      nano is Pd device 2 on the Organelle
main-dev.pd   [u_root 1]       nano is Pd device 1 on the Mac
u_root.pd     [m_nano $1]
```

One argument, because "the nano occupies a block of two channels" is a fact about the nano and
belongs inside `m_nano`. Creation arguments are static, so `[ctlin $1+1]` is impossible — but no
`loadbang` arithmetic is needed either, since `[- $1]` *is* a legal creation argument:

```
[ctlin]  channel outlet → [- $1] → [select 0 1] → controls / transport / another device
```

⬜ **This Mac's Pd has no MIDI input device saved in its preferences**, so `[ctlin]` receives
nothing until Media → MIDI Settings selects the nano once. A setup step, not a code change — but
it looks exactly like a broken patch.

#### Step 0 — errors survive the session

`u_err` gains a `[pd logfile]`: every error appends `<ms> <level> <source> <text>` to a
`[text define]`, unconditionally, with `ms` from a `[timer]` started at load. The **write** is
rate-limited by a dirty flag plus `[metro 2000]` — the same hold-state-flush-on-a-clock pattern
as the display, and for the same reason — and bounded to ~200 lines, since `[text write]`
rewrites the whole file. It targets **`/sdcard/cut-it-err.cur`**, this session only. `/sdcard` is
writable with no remount and survives reboot; `/tmp` is wiped.

Cross-session durability is a **second file and one shell call at load**. `[text write]` rewrites
the whole file, so on its own the next patch load would destroy the previous session's log —
which is the wrong property when debugging across many reloads. So `u_err`'s `loadbang` fires
`sh logroll.sh` into the `[shell]` `u_init` already uses, and the script appends the previous
`.cur` onto a durable `/sdcard/cut-it-err.log` behind a `date`-stamped `BOOT` separator, empties
`.cur`, and trims the durable file.

Three properties that matter:

- **One fork per patch load, never per error.** Nothing shells out during a performance.
- **A real wall clock without depending on `[shell]`'s return path**, because `date` runs inside
  the script. Pd 0.49 vanilla has no wall clock of its own.
- **`deploy.sh`'s gate stays clean.** The syntax check quits at load, before the metro fires, and
  `[shell]` resolves to `mac-stubs/shell.pd`, which swallows the message. No output, no
  per-platform path, no second creation argument.

`tools/fetch-errors.sh` pulls **both** files — reading both is what makes a fetch correct even
before a roll has happened — prints a summary of counts by level and source before the detail,
newest session first, reports whether `pd` is running and its uptime, and md5-compares the
deployed files against the repo, because an error from a build you no longer have is a trap.
`--follow` tails; `--clear` truncates after reading.

**Scope limit, stated honestly:** this captures errors the *patch raises*. Pd's own runtime
errors still go to tty1 and no vanilla 0.49 object can intercept them. The by-hand SSH console
remains the tool for those.

#### Step 1 — `m_nano`

Route the transport channel **first**, before any CC decoding, so a mode change can never be
confused with a performance control even if the CC map is later revised. Then the `div 10` /
`mod 10` idiom that already covers the Launchpad grid — sliders, knobs and the two button rows
are kinds 0–3, and transport needs no `div 10` at all, since its own channel plus `[- 40]` is
direct. Full map in [ref-midi.md](ref-midi.md).

`[ctlin]`'s outlets are value, controller, channel, and Pd fires **right to left** — so channel
and controller land in cold stores and the value arrives last and drives the dispatch. That is
convenient rather than lucky, but it is the same fact behind this repo's `polytouchin` bruise, so
**print it before building the decode on top of it.**

Names come from `[makefilename slider-%d]` and friends — **placeholders, deliberately.** There
are no parameters to name yet; `e_chop` and the rest arrive in v0.3. Generated names are honest
about that in a way a lookup table pretending to be a mapping would not be, and those four
objects are the seam where v0.3 swaps in real names and where mode-dependent mapping will hang.

| Control | Emits |
|---|---|
| Sliders, knobs | `disp` → `<name> <value>`, raw 0–127. Scaling belongs to whoever consumes it later |
| Buttons | `disp` → `<name> 1` on press only. Momentary; Pd owns any state |
| The six transport keys | exactly the same — `xport-1`…`xport-6` on press. **No toggle, no transport meaning** |
| An unmapped CC in the block | `warn m_nano cc-<n>-unmapped` on `err`, so a surprise is visible rather than silent — and it exercises step 0 |

**The transport row gets ordinary CC treatment**, decided after playing with it: it is being
repurposed as **scene selection**, so "play" and "loop" would be a lie. CC 41–46 give `div 10` = 4
and `mod 10` = 1…6, so it folds into the decode as a **fifth kind** and needs no separate path —
which deleted a whole subpatch. Names follow physical position, like every other control.

⚠️ **Consequence: nothing drives `mode`, `start` or `stop` any more.** `mode` degrades safely
(`u_err` defaults to verbose) and all three are documented as first consumed in Phase 5, but the
end-to-end mode test that the LOOP toggle provided is gone. **Deciding what drives them is a
Phase 5 / 6 decision** — the encoder, the aux button and the Launchpad are all candidates.

⚠️ **Second consequence, smaller:** the decode is now purely CC-number-based within the block, so
CC 41–49 on *either* channel reads as `xport-1`…`xport-9` rather than warning. For scene selection
that is probably what you want; there is no bounds check on the units digit anywhere, so CC 0 has
always read as `slider-0`.

⚠️ **`disp` parameter values must be floats.** `g_oled` sends them through `[makefilename %g]`,
which refuses a symbol. So the mode cannot be a parameter: it goes to the **footer**, which is
sticky and takes one symbol. That makes the footer shared between `u_init` and `m_nano` — fine,
since `disp` is a bus and last-writer-wins is its documented model — but it meant the `boot`
selector was misnamed. ✅ **Renamed to `status`**, in a commit of its own that changed no
behaviour.

**LOOP toggling mode is an end-to-end test that already exists:** `u_err` consumes `mode`, so
flipping to perform and raising a `warn` should draw nothing while a `fail` still draws.

#### Step 2 — several controls at once

The largest piece, and the one that touches a file verified on hardware. `g_oled`'s param layer
stops being one name/value/unit and becomes a **most-recently-used list** of up to five entries
in a `[text define]`, newest first, one line per entry:

```
<name>  <value>  <unit>  <frame-stamp>
```

On each param message: `[text search]` the name, `[text delete]` it if present, `[text insert]`
at line 0 to push it to the front, and drop the last if there are now more than five. ✅
`text search`, `insert`, `delete`, `get`, `set` and `size` are all present in the local Pd
0.49-1 binary — checked against it and against `text-object-help.pd`, not inferred.

**Ageing is free, because the frame clock already runs.** Each entry stores the frame number when
it last moved rather than an age to increment, and each frame the list is walked in from the tail
dropping anything older than 12 frames (1.2 s). Because the list is strictly ordered by
last-touched time, the expired entries are always a suffix, so the walk stops at the first live
one. This replaces the param layer's single `[del 1200]` and keeps the existing promise that the
TTL follows the *last* message rather than the first. Ageing runs **before** the priority
cascade, so the frame trigger grows one outlet.

Side benefit: the stale-unit trap is **structurally eliminated** in the new path, because each
line is written whole rather than field by field.

**Rows do not move once a control has one.** The first design pushed the most-recently-moved to
the front, which is what this plan originally asked for and was **wrong in the hand** — two faders
moving together swapped places several times a second and could not be read. A control already on
screen is now updated **in place**; a new one is appended below; and a **sixth is refused** rather
than rotated in, so nothing ever shifts while you are reading it. The cost is stated honestly: move
nine faders and you see the five you touched first, not the five most recent.

Font size adapts to how many are moving. The settled "24px is readable at arm's length" is
preserved for the common case — one hand, one control — and degrades rather than being abandoned.
The meters keep their 5 px bottom strips at y=48/56 throughout, so the param area is y=0…46:

| Moving | Layout |
|---|---|
| 1 | name 8px, value **24px** — exactly today's layout, unchanged |
| 2 | two stacked pairs, each name 8px over value **16px** |
| 3–5 | **8px** lines, one per control, newest at top |

The 2-mover case is a deliberate deviation from "two 16px lines": ✅ 16px fits about ten
characters across 128 px, so `slider-1 43` would clip to `slider-1 4` — a silent failure that
looks like a working display — and real v0.3 names like `chop-size` are no shorter.

**`u_net` in Phase 7 gets this for free**, since it subscribes to `disp` — one address for all
parameters, which [ref-display.md](ref-display.md) says scales to the nano's 18 controls without
redesign.

⚠️ **Step 2 edits a file verified on hardware, so re-running `tools/phase3-bench.pd` is the gate
on it being finished, not a courtesy.** If the MRU list turns hairy it is separable: ship
`m_nano` against today's single-parameter display and follow up, rather than blocking the phase
on a display rewrite.

### Phase 5 — Clock and transport

`u_tempo`, `c_clock`

A **rewrite**, not a port. v0.1's `midiclock.pd` is archived in
[! v0.1 plans/patch/](<! v0.1 plans/patch/README.md>) and is worth reading for *which MIDI
realtime bytes went where*, nothing more — it predates every convention in this project.

`u_tempo` owns `tempo`, `clock`, `start`/`stop`; emits MIDI realtime (248/250/251/252).

**Audio-domain from the start** — `phasor~`-derived, with the message-rate clock only for
things that genuinely tolerate it. Normalise BPM and ms to Hz at the edge.

**`u_tempo` is a master reference, not the clock.** Cut It runs poly-tempo — see *Poly-tempo*
in [ref-conventions.md](ref-conventions.md). Build `c_clock` as a separately instantiable
abstraction in this phase, owning its own rate and time signature and optionally slaved to
master by a ratio. **Do not build a clock singleton**; retrofitting once Phases 6–8 depend on
one is the expensive mistake this plan is trying to avoid.

**Done when:** tempo is settable from the nano, the 404 follows, grain-rate timing derives from
`phasor~` rather than `metro`, and two `c_clock` instances run at different rates at once.

### Phase 6 — Launchpad

`m_launchpad`, `g_grid`

The most complex piece, deliberately late. Pad input on Pd channel 1 with `r*10+c` decode and
polyphonic aftertouch. `g_grid` is the same arbiter shape as `g_oled` — playhead, slot state,
mode and meters all contend for 64 pads.

Batch LED updates: **one SysEx can carry up to 106 colour specs**, so a full-grid repaint is
one message, not 64.

Flash and pulse are **synced to MIDI beat clock**, so animation follows `u_tempo` for free.

**Done when:** pads report position, velocity and pressure; the grid shows mode state; a full
repaint is one message.

### Phase 7 — Phone status link

`u_net`

Promotion of `tools/status-display/` to an abstraction. Subscribes to `disp` and forwards over
`[netsend -u]`, plus the heartbeat.

**State never events; fire and forget; the Organelle never waits.** Rate limiting lives here,
not in the callers.

**Done when:** every parameter shown on the OLED also reaches the phone, and pulling the plug
shows `NO-LINK` within 1.5 s.

### Phase 8 — State and presets

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
| **SP-404 pad note range** — measured 47+*n* here, Roland's chart says 35–51 | Phase 5, and v0.3's `m_404` | Only pads 1 and 2 were ever checked. **This is the one that silently corrupts work** — sequencing code written against the wrong range looks correct and triggers the wrong pads. Sweep all 16 with `tools/midi-drive.pd` |
| **Launchpad perimeter CC numbers** | Phase 6 | Documented 📄, never confirmed on this unit. Ten minutes with `tools/lp-monitor.pd` |
| **Do flashing / pulsing LEDs track a *modulated* tempo?** | Phase 6 | The modes work ✅; tracking a sweeping tempo is ⬜. Needs a patch that sweeps tempo |
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
| **Class-compliant USB→DIN MIDI interface** | The Volca FM. Roland UM-ONE mk2 in its class-compliant "TAB" position, iConnectivity mio, or similar |
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
| **Buttons should not display `1`** | the `1` is a placeholder for "pressed". What a button shows depends on what it is mapped to, so this resolves itself when v0.3 gives them meanings |
| **Transport keys as scene selection** | ✅ already done in Phase 4 — they are ordinary CC buttons now. What remains is the *mapping*, which is v0.3 |

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

---

## Risks

**The `m_` layer is the one boundary that is genuinely expensive to retrofit.** If `e_chop` ever
learns that a nanoKONTROL exists, that is permanent.

**The display arbiter was the piece most likely to be wrong first time** — contention, TTL and
rate limiting are easy to describe and fiddly to tune. Built early (Phase 3) precisely so there
was time to live with it; now verified on hardware.

**Timing is architectural.** Grain clocks must be audio-domain from the first line, and
`u_tempo` must be a master reference *plus* an instantiable `c_clock`, not a singleton.
Retrofitting either once Phases 6–8 depend on them is the expensive mistake this plan exists to
avoid.
