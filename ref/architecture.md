<!-- schema: freeform -->
# Architecture — how the modules compose

**What each module is lives on its own page. This is the shape they connect in**, and the handful of
decisions that are about the *joins* rather than about any one part.

The single rule everything below follows from: **a device publishes what its surface did; exactly one
file decides what that means; and nothing below that file knows what hardware exists.**

## The shape

```
                             main.pd
                          (wiring only)
                                |
                              u_root
                                |
   ┌──────────┬──────────┬──────┴─────┬──────────┬──────────┬───────────┐
   │          │          │            │          │          │           │
 u_init    u_tempo     u_err       u_state    u_net      u_level    u_present
 startup   clock +     errors      the data   the phone  meters     the tick +
 order     transport               store         │                  ONE re-wire
   │          │          │            │          │          │           │
   └──────────┴────┬─────┴────────────┴──────────┴──────────┴───────────┘
                   │
              global buses
  mode · tempo · clock · start/stop · panic · param · err · disp · state
                       · presence
                   │
   ┌───────────────┼───────────────┐
   │               │               │
 m_nano       m_launchpad     m_organelle         ← device mapping,
 ch 17          ch 1          aux + knobs 1-4        INPUT side
 c_presence   c_presence      passive             ← and each one
 c_devid 66   c_devid 0       seen only              knows if it
                                                     is THERE
   │               │               │
   └───────────────┼───────────────┘
                   │
                 u_map  ←── cut-it-map.txt         ← the ONLY file that says
                   │        <mode> <control>          what a control MEANS.
                   │        <dest> <arg>              Table-driven, guarded by
                   │                                  a literal route box
                   │  CORDS, not a bus             ← an output device is TOLD
          ┌────────┴─────────┐                        what to play. No bus
          │              c_synth ◄── m_nanokey        carries that. u_net has
          │           fm │     │ strings   ch 49      cords too: the phone's
          ▼              │     ▼                      synth choice, its drum
       m_volca ◄─────────┘   m_streich                controls and its tempo
       ch 49                 ch 33, polled:
       notes/cc/program/note c_presence, c_devid 62
                   │
            (v0.4: e_chop, e_pitch, e_trem, e_verb)
                   │
   ┌───────┬───────┴───────┐
 g_oled  g_led          g_grid                     ← the three display surfaces
 OLED    aux LED        Launchpad

 u_net ── phone                                    ← the Launchpad's page, on cords:
                                                     state in, commands out
```

**What the diagram cannot show, all of it load-bearing:**

- ⛔ **`c_clock` is instantiated, not global.** `u_root` holds `c_clock 1 8` driving the grid's beat
  row, `c_steps` holds its own `c_clock 1 4`, and **nothing downstream may assume the global `clock`
  is its clock** — Cut It runs poly-tempo. See [tempo.md](module/tempo.md).
- **`c_steps`, page 2's drum machine, hangs off `u_map` by a cord** — its second outlet, carrying
  what a drum-page press means — and its own two outlets reach `c_kit`, which plays the drums,
  and `g_grid` with the page. Its rules are Lua, in `c_steps.lua`, behind one pdlua object; its clock and cords
  are Pd. See [sequencer.md](module/sequencer.md).
- **`c_synth` holds the synth choice on every page**, and the nanoKEY's keys reach it by a cord
  from `m_nanokey`, not on `param`: a key means the chosen synth's note whichever page is up. It
  sends each key to `m_volca` or `m_streich`, a release to the synth its press went to, and the
  choice to `u_net` and `g_grid`, and its velocity switch to `u_net`, by cords. Page 3's pads
  choose through `u_map`. See [synths.md](module/synths.md).
- **The phone reads nothing on `disp`** (Brendan, 2026-11-04): `u_net` takes each module's state on
  a cord — `c_steps`', `c_synth`'s and `u_tempo`'s BPM — and hands the phone's commands back out by
  cords to `c_steps`, `c_synth` and `u_tempo`. Page 1's tap pad reaches `u_tempo` from `u_map` by a
  cord too, and `u_tempo` flashes it through `g_grid`. See [phone.md](device/phone.md) and
  [tempo.md](module/tempo.md).
- **`u_inject` takes the checklists' Send lines** and puts them on eight buses, so a rig check can
  fake what no control sends: from the device itself, on `127.0.0.1` alone, where `tools/send.sh`
  carries them over SSH. Nothing from the phone reaches it (Brendan, 2026-11-04). `u_map`'s
  `test-mode` reaches `u_net` by a cord, and puts the phone's line check up. See [test/checklists/README.md](../test/checklists/README.md), *Send lines*.
- **`u_state` owns two `u_store` instances**, one per persistence policy. See
  [state.md](module/state.md).
- ⛔ **`c_presence` and `c_devid` are instantiated INSIDE the `m_` layers**, one pair per pollable
  device, and `u_present` holds no per-device state at all — only a count of how many sources are
  lost. Deciding *"my device is gone"* has to know about that device; doing something about it has
  to happen once for the whole rig, because re-running `wire.sh` re-enumerates everything. See
  [presence.md](module/presence.md).

**The layout of `u_root`'s canvas is this diagram.** Left is the `m_` layer, device by device; middle
is the buses and the map; right is the display owners. **Where a file has cords, the cords decide
where it goes** — which is why `m_volca` sits under `u_map` rather than in the `m_` column. Everything without cords talks on the allowlisted buses alone.

**Seven kinds of cord exist on that canvas, and each one is a seam worth seeing.** `u_init` reaches
`m_launchpad` and `u_state`, because the boot *order* is `u_init`'s while the *action* belongs to the
file at the other end. `u_map` reaches the output device, `m_volca`, because no bare global name
carries a sounding note (C-2). `m_launchpad` hands surface ownership to `g_grid`.
`c_clock` feeds `g_grid`'s beat row. `c_steps` sits between `u_map` and both `c_kit` and
`g_grid`: told what a press means, it plays the drums and says what the drum page shows. And
`c_synth` sits between `m_nanokey`, `u_map` and `u_net` on one side and the two synths, `u_net` and
`g_grid` on the other: it plays the nanoKEY's keys on the chosen synth and says which that is. And
`u_tempo` sits between `u_map`'s tap pad and `u_net`'s tempo on one side and `u_net` and `g_grid`
on the other: it turns taps and the phone's drag into the tempo, and says what it is.

## Creation arguments — the contract between the two entry points

`main.pd` and `main-dev.pd` differ in exactly two things, and every other difference between the Mac
and the device is absorbed by these six arguments to `u_root`.

| # | Is | Device | Mac |
|---|---|---|---|
| 1 | Pd channel the **nanoKONTROL**'s own channel 1 lands on | `17` | whatever slot it fills |
| 2 | The same for the **Launchpad** | `1` | " |
| 3 | **`u_state`'s data directory** — absolute, no trailing slash | `/sdcard/cut-it-state` | `/tmp` |
| 4 | Pd channel for the **Streichfett**'s channel 1, the SP-404's block until it left the rig (Brendan, 2026-11-04) | `33` | " |
| 5 | Pd channel for the **Volca**'s channel 1, and the first of the **nanoKEY**'s port, which it shares with the Volca's interface | `49` | " |
| 6 | **`u_net`'s inbound UDP port** | `9001` | `9002` |

**A Pd input slot maps to channels `(n-1)*16+1` upward**, so slot 2 begins at 17 and slot 3 at 33.
On the device that ordering comes from `/root/.pdsettings`; set the Mac's MIDI inputs to the same
order — Launchpad first, nano second — and both entry points pass the same two numbers, which is the
point of doing it that way round.

⛔ **The Launchpad goes first in the Mac's MIDI output list too.** Argument 2 is a channel block, but
`m_launchpad`'s watchdog and `g_grid` (which `u_root` hands the same `$2`) use it as the Launchpad's
output **port**, and `m_launchpad`'s init sends to a literal port 1. That holds only while the
Launchpad is input slot 1 and output port 1, as it is on the device. `m_nano` derives its port from
its block instead, `(block-1)/16+1`.

⛔ **Argument 3 is a genuine platform difference, and it is not an oversight.** There is no
`/sdcard` on a Mac. The device path survives `tools/deploy.sh`, `--clean` and a power cycle, which
the patch folder does not — **the instrument's data is deliberately outside the code**. See
[state.md](module/state.md).

⛔ **Argument 6 differs for a different reason: contention, not platform.** Only one process on a
machine can hold a UDP port, and `main-dev.pd` is open in Pd while `./test/run.sh` loads it again —
so one number for both would print `bind: Address already in use` and fail the silence gate on every
suite run. ⚠️ **It also means the phone's buttons drive the device rather than the Mac.** See
[phone.md](device/phone.md).

⛔ **Pd does not warn about a missing or extra creation argument, 0.49 or 0.57, and positional
arguments cannot be skipped.** A wrong count loads in perfect silence, so a clean syntax check
proves nothing about arity — and omitting one would silently shift every argument after it. **That is why each
`m_` layer prints the channel it actually received**, a couple of seconds in, behind `[del 2000]`
(C-9).

## The `m_` boundary is the expensive thing

**Nothing below the `m_` layer knows a nanoKONTROL exists.** A device publishes a **named control**
on `param`; what that control means is decided in `u_map`, above everything it controls.

⛔ **Names on `param` are physical, never functional** — the rule, and what it binds when you write
an `m_` layer, are in [conventions.md](conventions.md) under *The global name allowlist*.

This is what makes a control's meaning per page tractable, and **it is the one boundary that is
genuinely expensive to retrofit.** If `e_chop` ever learns about the nanoKONTROL, that is permanent.

## Request buses and publications

The ten bare names are C-2's allowlist and are listed in [conventions.md](conventions.md). What the
allowlist does not say is that **they are not all the same kind of thing.**

| Kind | Buses | Who writes | Who owns |
|------|-------|------------|----------|
| **Request** | `tempo`, `start`/`stop`, `mode`, `param`, `err`, `disp`, `state`, `panic` | Anyone with something to say | Exactly one consumer |
| **Publication** | `clock` | **Only `u_tempo`** | `u_tempo` |
| **Both directions** | `presence` | An `m_` registers and reports; `u_present` ticks | Disjoint by selector, so there is no loop |

**`u_tempo` owns the BPM value and the transport state; it does not own the right to change them.**
`clock` is the exception because it is a publication of something already decided.

**`param` is a control changing; `disp` is a request to show it**, and the distinction is the whole
reason for a second bus. **A device layer publishes on `param` alone, and `u_map` makes the
request**, because it is the only file that knows what a control means: the row it draws is the
destination's — `volca-cc41 64`, `bpm 157` — or `<name> <raw>` for a control nothing maps. When the
`m_` layers posted their own row as well, a mapped fader drew two (item 317). `g_oled` still listens
on `disp` alone, so no display file has had to learn that `param` exists.

## Output devices are WIRED, not given a bus

`m_volca` and `m_streich` are **told what to play**, as `m_404` was until the SP-404 left the rig
(Brendan, 2026-11-04). No bus carries a sounding note — `param` is device-to-map and `disp` is
display, and a note is neither. `m_streich` is told by `c_synth`, which chooses between the two
for the nanoKEY's keys ([synths.md](module/synths.md)); `u_map`'s cord to `c_synth` carries the
choice, not a note.

**`u_map` grows one outlet per output DEVICE**, wired in `u_root`, carrying a **selector-prefixed**
message the device layer routes internally: `notes 48 100 200`, `cc 41 64`, `program 20`.

| | |
|---|---|
| A new capability | Costs **one `route` argument inside that device** and nothing anywhere else — not `u_map`'s outlet count, not `u_root`'s cords |
| ⚠️ The device's `route` **reject** | A **real error**, straight to `[s err]` — an unrecognized selector means `u_map` and the device layer disagree about the interface, and nothing else would notice |

⛔ **That is the opposite of `u_map`'s lookup miss**, where an unmapped control is normal and
silent. Opposite meanings, one layer apart.

*(judgment call)* **One outlet per device *inlet* was considered and rejected.** It makes `u_map`'s
outlet count a function of every device's feature list. *(judgment call)* **A bus was considered and
rejected** — `u_root` could serve several device layers the way `disp` serves four surfaces, but
**the allowlist is audited by reading**, and a sounding note is not application-wide state.

## `u_err` — one filter, one place

**The Organelle runs Pd with `-nogui`, so an error you cannot see is a silent failure.** `u_err` is
the one filter that decides what a problem is allowed to interrupt, and it is the only file that
decides it, by level alone: every warning and every failure is drawn, on every page. Any abstraction
reports with `[s err]` and none of them knows which page the instrument is on. It never draws — C-5
gives `g_oled` the screen, so this forwards onto `disp`.

**Everything about it is on [module/error.md](module/error.md)** — the levels, why no page hides a
warning, and the durable log. The message format is rule C-12; the four display surfaces and how an
alert is arbitrated are on [display.md](module/display.md).

## Load-bearing decisions

The four that shape everything else.

| Decision | Consequence |
|---|---|
| **Grain timing must be audio-domain** | Pd's message clock is quantized to a 64-sample block (~1.45 ms), ~20% of a 256th note at 120 BPM. `phasor~` and `vline~`, never `metro`/`line~` at grain rate (C-11). Built that way from the first line — see [tempo.md](module/tempo.md) |
| **Pd sequences everything** | Timing rides in note events, not MIDI clock. No external device runs its own sequencer during a performance |
| **Two independent input channels** | `inL` = the tip, `inR` = the ring of the one input jack: the mic on the tip since 2026-11-04 — see [audio.md](module/audio.md) |
| **Pages, not a compose and perform split** | The Launchpad's left column chooses one of eight pages, and `u_map` looks every control up per page, so one surface serves a different role on each: 1 the arrangement, 2 the drums, 3 the synths, 8 the songs, 4 to 7 nothing yet (Brendan, 2026-11-04). This shapes the top level of the patch |

### Why the infrastructure was built before any DSP

Three constraints made the usual "get a sound out, then tidy up" approach expensive here, and all
three were borne out:

1. **There is no console.** Errors vanish. Anything not built to report itself is invisible, and
   retrofitting reporting across an existing patch is far worse than designing it in. `u_err` exists
   because of this.
2. **The device mapping layer is the expensive thing to retrofit.** See *The `m_` boundary* above.
3. **Timing is architectural.** Grain clocks must be audio-domain from the first line, not converted
   later.

## Division of labor between the surfaces

Nothing overlaps, and that is deliberate:

| Surface | Role |
|---|---|
| **Launchpad** | Pads, grid state, sequencing — page 2 is the drum page. Anything needing state you can *see* |
| **nanoKONTROL** | Continuous control, with position visible on the panel. Momentary buttons only |
| **Organelle keyboard** | Choosing songs, once there are songs: until then its keys play nothing (Brendan, 2026-11-04). Under aux, the four keys every page shares: diag, test mode, stop and recover |
| **nanoKEY** | Playing the chosen synth, the Volca or the Streichfett, on every page (Brendan, 2026-11-04) |

⚠️ **The Launchpad mode conflict evaporates because of this split.** Authoring that needs Note or
Chord mode uses them; everything Cut It draws, the drum page's sequencing included, is Programmer
Mode. They never coexist, so there is no mid-set SysEx flipping.

⛔ **Every surface is shared between pages, and that is what forces explicit pages.** A control
means what the current page's row says, so the Launchpad's grid is the drum page on one page and a
beat row on the rest. Designing that in from the start is much cheaper than retrofitting it once the
filter logic exists, which is why `mode` and a page-dependent `u_map` exist before any filter does.

## The naming, and what it tells you

| Prefix | Is | Talks on |
|--------|-----|----------|
| `m_` | One physical device | Publishes `param`, never a control's row; knows no meaning |
| `u_` | One instrument-wide utility | Buses, and owns one of them |
| `g_` | One display surface, and its sole owner | Consumes `disp` |
| `c_` | **Instantiable** — there is more than one | Its creation arguments |
| `e_` | An effect stage (v0.4) | Signal in, signal out |

⛔ **A `c_` prefix means instances, and a `$0-` on everything inside it (C-1).** Six exist:
`c_clock`, `c_presence` and `c_devid` inside the `m_` layers, `c_mapped` inside `u_map`, one per
destination that carries a value, `c_steps`, the sequencer, whose bank (vestigial since the
SP-404 left the rig) and stored part are its creation arguments, and `c_synth`, the synth choice,
one today, since a second keyboard would want its own. The v0.4 filter stages are the reason the prefix exists.

## Open

- ⬜ **`e_` has no members yet.** The four filter stages, the drum mode and the sampler are v0.4, and
  they are the first thing to sit *between* `u_map` and the audio chain rather than beside it. See
  [plan-v04.md](../plan-v04.md) §3.
- ⬜ **Nothing composes two `c_clock` instances yet.** Poly-tempo is built and has one consumer. See
  [plan-v04.md](../plan-v04.md) §3.
