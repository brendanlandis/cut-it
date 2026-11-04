# Checklists

**The hands-on half of the tests: a person at the rig is the oracle.** Each step is something to do
and a sentence that says what passes. The headless half, where a program is the oracle, is the gates:
[test/README.md](../README.md).

They replaced the bench runner on 2026-11-03: `test/run.sh --bench`, the generated bench patches and
the verdict file went, and every step's text came here.

**Two suites** (Brendan, 2026-11-04). The **line check**, before a set, asks whether every device is
there and talking to the next. The **development checklists**, after a change, ask whether Cut It
does what it should. A failure in the first points at a cable, a power supply or a setting; in the
second, at the code.

## The line check

**Before a set, from the phone, alone at the rig.** One short list, with every step hands-on: nothing
is sent from anywhere.

| Checklist | Steps | Judges |
|---|---|---|
| [linecheck](linecheck.md) | 8 | the phone's link, the roster, the 404's MIDI settings, the drums, the mic and the Volca through the PA, the transport |

1. **Choose mode 1, then tap Setup**, the Launchpad's bottom-left button (or at the Organelle hold
   `aux` and press the second key from the bottom). That turns test mode on, and the phone's screens
   give way to the checklist page, reading `test mode on` (the Organelle's own state, from the
   heartbeat); the OLED warns in compose.
2. Each step shows its title and, from the file, Need, Do, Check and Pass if; the Notes stay here. A
   step too long for one page has a second, and Next shows it first.
3. **Pass** or **Fail** logs the verdict on the Organelle as `info phone linecheck-<n>-pass` (read it
   with `tools/fetch-errors.sh`), flashes, and goes on to the next step. **Back** and **Next** move
   without logging.
4. **Tap Setup again when it's done.** Choosing a mode also turns test mode off and brings the
   phone's screens back, as does every load of Cut It, so no step presses a mode button.

The page is generated from linecheck.md by `tools/touchosc/build.py` and goes to the phone with
`tools/touchosc/push.sh`; edit it, push. **Gate:** `test/gate/touchosc-assert.sh`, which also fails
while the committed layout is stale or the line check has a Send line.

## The development checklists

**After a change, with the Mac at hand.** One per area. Their Send lines go from the Mac (below). A rig
session means opening one.

| Checklist | Steps | Judges |
|---|---|---|
| [display](display.md) | 20 | the OLED's layers and the error bus |
| [nanokontrol](nanokontrol.md) | 7 | every control, and hot-swap |
| [tempo](tempo.md) | 13 | the transport, knob 1's pickup, the clamp |
| [launchpad](launchpad.md) | 28 | the grid, its layers, the mode lamps, the beat row, hot-swap, panic |
| [phone](phone.md) | 23 | what the phone shows, its tabs, the link dropping and coming back, its buttons, the checklist page and test mode |
| [state](state.md) | 5 | the front-panel Save, a power cycle, the mode surviving it |
| [recover](recover.md) | 7 | panic's second tier: the reload, and a reload that cannot land |
| [midi](midi.md) | 18 | the map by mode, the SP-404 both ways, the Volca by ear, hot-swap |
| [debug](debug.md) | 9 | the debug patch, with the instrument stopped |
| [sequencer](sequencer.md) | 23 | mode 1's drum page and the drums it plays |

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

A **Send** line puts messages on the instrument's buses, as its controls do: each message's first
word is the bus, and a `;` separates messages. `disp chop-size 43 %` sends `chop-size 43 %` to `disp`.

**On the rig**, from the Mac:

```bash
./tools/send.sh 'disp chop-size 43 %; disp grain 12'
```

In a walkthrough, Claude sends each step's line and you say what you see. `HOST=` targets the
Organelle by IP, as for `tools/deploy.sh`.

**`u_inject` takes it**, in the instrument. It listens on `127.0.0.1` only, at `u_net`'s inbound
port plus 2000 (11001 on the device), so a line has to start on the device itself: `send.sh`
carries it over SSH to the device's own `pdsend`, one datagram a message, since Pd's `netreceive`
delivers only the first message in a datagram (Reference, *Pure Data*). Nothing on the network
reaches it, the phone included.

**Eight buses and nothing else:** `disp`, `err`, `mode`, `panic`, `param`, `start`, `stop` and
`tempo`, the ones the checklists name. `clock`, `state`, `presence`, `recover`, `pd` and any other
name are dropped, so a line can never quit or reload Pd. **Gate:** `test/gate/inject-assert.sh`.

**On the Mac**, open `Cut It/main-dev.pd` in Pd 0.57 and tick **enable-DSP** on its dev panel
(`c_clock` hangs off `threshold~`, so with DSP off the beat row never moves and every count reads
0). Then `HOST=mac ./tools/send.sh '…'`, or paste the line into Pd's *Send a Pd message* window
(Cmd-Shift-M, or File > Message). `u_mother-stub` draws the OLED and the aux LED in the dev panel.

⚠️ On the Mac every step that sends `err` also prints `/sdcard/cut-it-err.cur: write failed`, and
that is not a failure: `u_err` keeps its durable log on the Organelle's SD card, which no Mac has.
On the device that line must never appear.

**Some Send lines have a control on the rig behind them**, through `u_map` and the map, and these
can be done by hand instead:

| Send | On the rig |
|---|---|
| `mode compose mode-1` to `mode compose mode-3` | the first to third button down the Launchpad's left column |
| `mode perform mode-4` to `mode perform mode-6` | the fourth to sixth button down it |
| `start bang` · `stop bang` | PLAY · STOP on the nanoKONTROL |
| `panic bang` | a short tap on the Launchpad's top-left corner button |

## Writing a step

A step is a promise about one thing a person can see, hear or read, so the rules are about keeping
it honest:

- **A step belongs to one suite.** The line check's judge a connection, a device or a setting, with
  no code under test; they send nothing and press no mode button, since a mode ends test mode and
  takes the page away. Whether Cut It does what it should goes in a development checklist.
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
