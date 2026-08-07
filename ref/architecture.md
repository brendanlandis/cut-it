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
   ┌──────────┬──────────┬──────┴─────┬──────────┬──────────┐
   │          │          │            │          │          │
 u_init    u_tempo     u_err       u_state    u_net      u_level
 startup   clock +     errors      the data   the phone  meters
 order     transport               store         │
   │          │          │            │          │
   └──────────┴────┬─────┴────────────┴──────────┘
                   │
              global buses
  mode · tempo · clock · start/stop · panic · param · err · disp · state
                   │
   ┌───────────────┼───────────────┬───────────────┐
   │               │               │               │
 m_nano       m_launchpad     m_organelle       m_404            ← device mapping,
 ch 17          ch 1          aux + knobs 1-4   ch 33-42            INPUT side
   │               │               │               │
   └───────────────┼───────────────┴───────────────┘
                   │
                 u_map  ←── cut-it-map.txt         ← the ONLY file that says
                   │        <mode> <control>          what a control MEANS.
                   │        <dest> <arg>              Table-driven, guarded by
                   │                                  a literal route box
       ┌───────────┴───────────┐
       │  CORDS, not a bus     │                   ← output devices are TOLD
    m_404                  m_volca                    what to play. No bus
    ch 33-42               ch 49                      carries that.
    pad <n> <vel>          notes/cc/program
                   │
            (v0.4: e_chop, e_pitch, e_trem, e_verb)
                   │
   ┌───────┬───────┴───────┬───────────┐
 g_oled  g_led          g_grid       u_net         ← the four display surfaces
 OLED    aux LED        Launchpad    phone
```

**Two things the diagram cannot show, and both are load-bearing:**

- ⛔ **`c_clock` is instantiated, not global.** `u_root` holds `c_clock 1 8` driving the grid's beat
  row, and **nothing downstream may assume the global `clock` is its clock** — Cut It runs
  poly-tempo. See [tempo.md](module/tempo.md).
- **`u_state` owns two `u_store` instances**, one per persistence policy. See
  [state.md](module/state.md).

**The layout of `u_root`'s canvas is this diagram.** Left is the `m_` layer, device by device; middle
is the buses and the map; right is the display owners. **The only wires on that canvas come out of
`u_init`** — to `m_launchpad` and to `u_state` — because the boot *order* is `u_init`'s while the
*action* belongs to the file at the other end. Everything else talks on the allowlisted buses.

## The `m_` boundary is the expensive thing

**Nothing below the `m_` layer knows a nanoKONTROL exists.** A device publishes a **named control**
on `param`; what that control means is decided in `u_map`, above everything it controls.

⛔ **Names on `param` are physical, never functional** — `slider-1`, `og-knob-1`, `xport-2`. What a
control *does* is not knowable at the `m_` layer and must not be guessed there.

This is what makes the compose/perform split tractable, and **it is the one boundary that is
genuinely expensive to retrofit.** If `e_chop` ever learns about the nanoKONTROL, that is permanent.

## Request buses and publications

The nine bare names are C-2's allowlist and are listed in [conventions.md](conventions.md). What the
allowlist does not say is that **they are not all the same kind of thing.**

| Kind | Buses | Who writes | Who owns |
|------|-------|------------|----------|
| **Request** | `tempo`, `start`/`stop`, `mode`, `param`, `err`, `disp`, `state`, `panic` | Anyone with something to say | Exactly one consumer |
| **Publication** | `clock` | **Only `u_tempo`** | `u_tempo` |

**`u_tempo` owns the BPM value and the transport state; it does not own the right to change them.**
`clock` is the exception because it is a publication of something already decided.

**`param` is a control changing; `disp` is a request to show it**, and the distinction is the whole
reason for a second bus. `m_nano` and `m_organelle` publish to both off one `[t a a]`, action first
and report second. That duplicates the data where teaching `g_oled` to listen on `param` would not,
and it was the right trade: **not touching a hardware-verified display file beat saving a send.**

## Output devices are WIRED, not given a bus

`m_volca` and `m_404` are **told what to play**. No bus carries a sounding note — `param` is
device-to-map and `disp` is display, and a note is neither.

**`u_map` grows one outlet per output DEVICE**, wired in `u_root`, carrying a **selector-prefixed**
message the device layer routes internally: `notes 48 100 200`, `cc 41 64`, `program 20`,
`pad 23 96`.

| | |
|---|---|
| A new capability | Costs **one `route` argument inside that device** and nothing anywhere else — not `u_map`'s outlet count, not `u_root`'s cords |
| ⚠️ The device's `route` **reject** | A **real error**, straight to `[s err]` — an unrecognised selector means `u_map` and the device layer disagree about the interface, and nothing else would notice |

⛔ **That is the opposite of `u_map`'s own reject**, where an unmapped control is normal and silent.
Two rejects, opposite meanings, one layer apart.

*(judgment call)* **One outlet per device *inlet* was considered and rejected.** It makes `u_map`'s
outlet count a function of every device's feature list. *(judgment call)* **A bus was considered and
rejected** — `u_root` could serve several device layers the way `disp` serves four surfaces, but
**the allowlist is audited by reading**, and a sounding note is not application-wide state.

## `u_err` — one filter, one place

**The Organelle runs Pd with `-nogui`, so an error you cannot see is a silent failure** — and Pd's
failure mode for a wrong message is to print and continue. `u_err` was built in the first
infrastructure pass rather than retrofitted. *(judgment call: an architecture requirement, not a
debugging convenience.)*

| | |
|---|---|
| **Filters by `mode`** | compose shows everything, perform only `fail`. One place, same bus, same callers |
| **Defaults to verbose** | Which is what made an undriven `mode` safe through Phases 4 and 5. `u_map` drives it from Phase 6 on, and the filter needed no change — `route` matches on the selector, so two-atom `compose mode-1` sets verbose exactly as bare `compose` did |
| ⛔ **Never draws** | It forwards onto `disp` as `alert <level> <source> <text>`; `g_oled` decides what an error looks like |
| **The bus is unfiltered; only the SCREEN is filtered** | An unconditional `[print err]` means the by-hand SSH console sees every error raised, even in perform mode |
| **Errors time out; they are never modal** | A stuck error covering the display mid-set is worse than a missed warning |

⚠️ **This does not catch Pd's own runtime errors** — those still go to tty1. It catches the ones we
raise, which is most of what actually goes wrong.

The message format is rule C-12; the four display surfaces and how an alert is arbitrated are on
[display.md](module/display.md).

## Load-bearing decisions

The four that shape everything else.

| Decision | Consequence |
|---|---|
| **Grain timing must be audio-domain** | Pd's message clock is quantised to a 64-sample block (~1.45 ms), ~20% of a 256th note at 120 BPM. `phasor~` and `vline~`, never `metro`/`line~` at grain rate (C-11). Built that way from the first line — see [tempo.md](module/tempo.md) |
| **Pd sequences everything** | Timing rides in note events, not MIDI clock. No external device runs its own sequencer during a performance |
| **Two independent input channels** | `inL` = drums (the tip), `inR` = fx (the ring), from the 404's hard-panned pair through a TRS Y-cable — see [audio.md](module/audio.md) |
| **Compose and perform are separate modes** | Both the Launchpad and the Organelle's keyboard serve different roles in each, so this shapes the top level of the patch |

### Why the infrastructure was built before any DSP

Three constraints made the usual "get a sound out, then tidy up" approach expensive here, and all
three were borne out:

1. **There is no console.** Errors vanish. Anything not built to report itself is invisible, and
   retrofitting reporting across an existing patch is far worse than designing it in. `u_err` exists
   because of this.
2. **The device mapping layer is the expensive thing to retrofit.** See *The `m_` boundary* above.
3. **Timing is architectural.** Grain clocks must be audio-domain from the first line, not converted
   later.

## Division of labour between the surfaces

Nothing overlaps, and that is deliberate:

| Surface | Role |
|---|---|
| **Launchpad** | Pads, grid state, compose-time sequencing. Anything needing state you can *see* |
| **nanoKONTROL** | Continuous control, with position visible on the panel. Momentary buttons only |
| **Organelle keyboard** | Note entry at compose time; filter control at perform time |

⚠️ **The Launchpad mode conflict evaporates because of this split.** Authoring uses
Note/Chord/Sequencer; performance uses Programmer Mode. They never coexist, so there is no mid-set
SysEx flipping.

⛔ **Two surfaces are DOUBLE-BOOKED, and that is what forces explicit modes.** The Launchpad *and*
the Organelle's own keyboard both serve two roles — the keyboard is **four filter groups during
performance and a note-entry surface during composition**. Designing that in from the start is much
cheaper than retrofitting it once the filter logic exists, which is why `mode` was built in v0.2 and
`u_map` became mode-dependent in v0.3.

## The naming, and what it tells you

| Prefix | Is | Talks on |
|--------|-----|----------|
| `m_` | One physical device | Publishes `param` and `disp`; knows no meaning |
| `u_` | One instrument-wide utility | Buses, and owns one of them |
| `g_` | One display surface, and its sole owner | Consumes `disp` |
| `c_` | **Instantiable** — there is more than one | Its creation arguments |
| `e_` | An effect stage (v0.4) | Signal in, signal out |

⛔ **A `c_` prefix means instances, and a `$0-` on everything inside it (C-1).** `c_clock` is the
only one today; the v0.4 filter stages are the reason the prefix exists.

## Open

- ⬜ **`e_` has no members yet.** The four filter stages, the drum mode and the sampler are v0.4, and
  they are the first thing to sit *between* `u_map` and the audio chain rather than beside it. See
  [plan-v04.md](../plan-v04.md) §3.
- ⬜ **Nothing composes two `c_clock` instances yet.** Poly-tempo is built and has one consumer. See
  [plan-v04.md](../plan-v04.md) §3.
