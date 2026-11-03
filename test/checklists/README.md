# Checklists

**The hands-on half of the tests: a person at the rig is the oracle.** One checklist per area, each
step something to do and a sentence that says what passes. The headless half, where a program is the
oracle, is the gates: [test/README.md](../README.md).

They replaced the bench runner on 2026-11-03: `test/run.sh --bench`, the generated bench patches and
the verdict file went, and every step's text came here. A rig session means opening a checklist.

| Checklist | Steps | Judges |
|---|---|---|
| [display](display.md) | 20 | the OLED's layers and the error bus |
| [nanokontrol](nanokontrol.md) | 7 | every control, and hot-swap |
| [tempo](tempo.md) | 13 | the transport, knob 1's pickup, the clamp, the 404 following |
| [launchpad](launchpad.md) | 27 | the grid, its layers, the mode lamps, the beat row, hot-swap, panic |
| [phone](phone.md) | 18 | what PdParty shows, the link dropping and coming back, its buttons |
| [state](state.md) | 5 | the front-panel Save, a power cycle, the mode surviving it |
| [recover](recover.md) | 7 | panic's second tier: the reload, and a reload that cannot land |
| [midi](midi.md) | 18 | the map by mode, the SP-404 both ways, the Volca by ear, hot-swap |
| [debug](debug.md) | 9 | the debug patch, with the instrument stopped |
| [sequencer](sequencer.md) | 12 | mode 1's drum page and what the 404 does with it |

⚠️ **The Mac is not the device.** The Phase 6 gate passed 25/25 on the Mac twice and shipped three
bugs; a checklist on the rig is the last word.

## Reading a step

| | |
|---|---|
| **Need** | what has to be true first. Every step sets up its own preconditions, including the ones the step before it destroyed |
| **Send** | messages onto the instrument's buses, all in one go (below) |
| **Do** | what your hands do, after the Send |
| **Check** | a command to run on the Mac, where a file on the device is the only evidence |
| **Pass if** | tick the box only if every sentence holds. Several steps pass when **nothing** happens |
| **Note** | why the step is shaped as it is. Not something to do |

Capitals mean literally on a screen or a label (REW, PLAY, EXT, Programmer Mode), never emphasis.

**Tick boxes in a copy.** The files here stay unticked so the next session starts clean, and what a
run found goes where the work is tracked, in `!projects`.

**Loading Cut It again** means selecting it from the Organelle menu, which restarts Pd as a power-up
does. Never `killall pd`: it skips `m_launchpad`'s safe exit and strands the Launchpad in Programmer
Mode (`tools/lp-live.sh` rescues it).

## Send lines

A **Send** line is what the bench patches used to put on the buses: each message's first word is the
receive name, and a `;` separates messages. `disp chop-size 43 %` sends `chop-size 43 %` to `disp`.

**On the Mac**, open `Cut It/main-dev.pd` in Pd 0.57 and tick **enable-DSP** on its dev panel
(`c_clock` hangs off `threshold~`, so with DSP off the beat row never moves and every count reads
0). Then open Pd's *Send a Pd message* window (Cmd-Shift-M, or File > Message), paste the whole
line, and press Return. `u_mother-stub` draws the OLED and the aux LED in the dev panel.

⚠️ On the Mac every step that sends `err` also prints `/sdcard/cut-it-err.cur: write failed`, and
that is not a failure: `u_err` keeps its durable log on the Organelle's SD card, which no Mac has.
On the device that line must never appear.

⛔ **On the Organelle nothing takes a Send line.** Its Pd runs `-nogui`, so there is no message
window, and `u_net`'s inbound vocabulary is closed (three commands and two device names). The bench
patches reached the buses by running as a third patch inside the instrument's own Pd, and they went
with the runner. So a step with a Send line runs on the Mac. That covers what is judged on the OLED
and the aux LED; a step judged on the Launchpad, the SP-404 or the phone needs that device reaching
the Mac's Pd, which is untested.

**Except where a control on the rig sends the same message**, which these do, through `u_map` and
the map:

| Send | On the rig |
|---|---|
| `mode compose mode-1` to `mode compose mode-3` | the first to third button down the Launchpad's left column |
| `mode perform mode-4` to `mode perform mode-6` | the fourth to sixth button down it |
| `start bang` · `stop bang` | PLAY · STOP on the nanoKONTROL |
| `panic bang` | a short tap on the Launchpad's top-left corner button |

A step whose Send line is only those runs on the rig by hand. Anything else (`disp`, `err`, `param`,
`grid`, a `tempo` value, `perform mode-3`) has no control behind it.

## Writing a step

A step is a promise about one thing a person can see, hear or read, so the rules are about keeping
it honest:

- **A step belongs to whatever it touches.** Before adding one, ask: could it run with the named
  device unplugged? Then it is not that device's step. The nanoKONTROL's checklist once carried
  fourteen steps that never touched the controller, nine of them display steps under another name,
  and the record reported more coverage than existed.
- **A checklist suits a surface, not a store.** A feature whose whole output is a file is proven by a
  gate (`state-assert`); the checklist keeps only what hardware can show.
- **Include the steps whose correct result is that nothing happens.** A meter that must not reach the
  phone is a step, with its **Pass if** saying what nothing looks like.
- **Every step sets up its own preconditions.** A parameter row ages out in about 1.3 seconds and a
  modal in 30, so a step judging what the step before put up judges an empty screen and passes. A
  step that raises a modal clears it, or the next one re-raises or clears it.
- **A step judging something late and brief says where to look and when.** A `device-lost` warn
  arrives up to 8 seconds after the cable comes out and clears two seconds later, while your hands
  and eyes are on the cable.
- **Say what a gate already proves, and leave it to the gate.** One claim judged in two places
  reports more coverage than exists.
- **Append rather than renumber** where a step number is cited: `ref/` pages and `!projects` cite
  steps by number (`recover` step 5).
