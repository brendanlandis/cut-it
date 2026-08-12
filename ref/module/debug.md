<!-- schema: module -->
# The debug patch

**Files:** `Cut It Debug/main.pd`, `Cut It Debug/wire.sh`, `Cut It Debug/err-tail.sh`, `Cut It Debug/net-probe.sh` · **Gate:** `test/gate/debug-assert.sh` · **Bench:** `test/bench/debug-bench.pd`

## What it is

**A second deployable, and the whole design follows from being separate.** Every other diagnostic
this project has is driven from the Mac over SSH — `test/run.sh`, `tools/fetch-errors.sh`,
`tools/display-cpu.sh` — and SSH needs a network, which is the exact thing that is missing when it
matters. At a venue, three questions used to need a laptop: what MIDI is arriving from each device
and on what channel, whether each device answers when you fire something at it, and what the error
log says.

⛔ **It is a separate patch because the instrument's Pd is what has usually stopped answering.** A
diagnostic living inside Cut It shares the process it is meant to report on. This one is selected
from the menu, which restarts Pd — so it starts from nothing, and nothing that went wrong in the
previous instance can reach it.

**Six screens, steered from the 25 keys.** The lowest key sends `goHome` and leaves. `k2`–`k7` pick
a screen; `k13`, `k15` and `k17` fire the Volca probe, the SP-404 probe and a re-wire, and those
three work from any screen.

## Facts

### The screens

| Key | Screen | Rows | Evidence | Item |
|-----|--------|------|----------|------|
| `k2` | `1-MIDI-IN` | `lp-` `nano-` `sp404-` counts, and `ch-` — the last channel seen | verified | 315 |
| `k3` | `2-TEST-OUT` | which key fires which device, `sent-` and the looping-pad warning | verified | 315 |
| `k4` | `3-ERR-LOG` | the last four lines of `/sdcard/cut-it-err.log` | verified | 315 |
| `k5` | `4-NETWORK` | `ip-` this Organelle's own address, `ap-`, `phone-` | verified | 315 |
| `k6` | `5-RE-WIRE` | `links-` from `wire.sh`'s own report, and `runs-` | verified | 315 |
| `k7` | `6-HELP` | the key map | verified | 315 |
| `k1` | — | sends `goHome` and returns to the Organelle's menu | verified | 315 |

### The port is the device

**The channel-block map is [boot.md](boot.md)'s** — `wire.sh` assigns it and this patch only reads it
back.

| Fact | Evidence | Item |
|---|---|---|
| **`(channel - 1) / 16` names the box an event came out of**, with no device having to identify itself | verified | 315 |
| So one `[notein]` and one `[ctlin]`, both OMNI, cover the whole rig | verified | 315 |
| Within the SP-404's block the channel **is** the bank, so the `ch-` row reads bank A as 33 | verified | 315 |

⛔ **It only holds while `wire.sh` has undone mother's own auto-connect.** `alsaconnect.sh` wires the
lowest-numbered client to Pd's Midi-In 1, and the nanoKONTROL has enumerated below the Launchpad
before now — when that happens two devices really are both channel 1 and nothing in Pd can tell them
apart. Item 274, and it is the fault this screen is most likely to be looking for.

⚠️ **The USB Uno block has no counter row of its own.** The Volca behind it is receive-only, so a row
there could only ever read zero; anything that does appear on the interface's DIN IN jack shows up in
`ch-` as a channel between 49 and 64.

### What it costs to run

| Fact | Evidence | Item |
|---|---|---|
| **Selecting it stops the instrument.** Loading any patch restarts Pd | verified | — |
| It forks `wire.sh` itself, ~1.5 s after load — `loadbang` fires before the ALSA connections exist | verified | 315 |
| The probes are the phone's: `notes 60 100 200` at the Volca, `pad 1 100` at the SP-404 | verified | 306 |
| What `u_state` wrote is untouched — it lives in `/sdcard/cut-it-state/`, outside both patch folders | verified | — |
| It repaints the current screen at **3.3 Hz**, so the counters are live rather than frozen | verified | 315 |
| `err-tail.sh` and `net-probe.sh` fork **once per selection**, never per repaint | verified | 315 |

### Where it lives

`/sdcard/Patches/! debug/Cut It Debug/`, deployed with `./tools/deploy.sh --debug`.

⛔ **`! debug` is a second menu directory and that is deliberate.** `/sdcard/Patches/!` holds `Cut It`
and nothing else — **at a venue you should scroll past nothing to reach the instrument**, and
anything you might reach for *instead of* playing belongs in the other folder. The stage probes under
`tools/stage-patches/` live there too.

## Traps

### A debug patch that does not wire itself reports a working rig as dead

⛔ **Loading any patch drops Pd's ALSA connections.** A MIDI monitor that skipped `wire.sh` would
measure silence and print it as *"nothing is arriving"* — the worst available lie for this particular
tool, because reporting silence is its whole job.

**Fix:** it forks `wire.sh` on a 1.5 s delay at load, and `debug-assert.sh` asserts that the first
thing it ever runs is that fork.

### Prove the probe before believing the silence

⛔ **If the MIDI screen shows nothing, that is not evidence about any device yet.** Establish that the
monitor works — move a nanoKONTROL fader, which transmits the moment you touch it and has nothing to
go wrong at the far end — and only then conclude anything about the device you were worried about.

**Fix:** the bench makes this step 3 and says every later step depends on it.

### It must not ask the `presence` bus for a re-wire

⛔ The bus gained a `re-wire` selector for the phone, and it is the wrong mechanism here: that bus
lives inside Cut It's Pd instance, and **loading this patch is what killed that instance**.

**Fix:** fork `wire.sh` directly. Its own copy, not the instrument's — see below.

### Its `wire.sh` is a copy, and a copy can drift

⛔ At a venue the instrument's folder may not be there. `test/bench/recover` step 5 literally moves it
away, and the two menu directories are separate anyway — so the debug patch carries its own
`wire.sh`. But two independent copies of nine `aconnect` lines is exactly the drift this project keeps
removing: the tool would report a rig wired one way while the instrument wires it another.

**Fix:** `debug-assert.sh` runs `cmp` on the two before it starts any Pd, and names the one-line
command that fixes a divergence.

### The two data scripts must emit a fixed number of lines

⛔ The patch counts lines out of `[shell]` and routes line *N* to `screenLine N+1`. A script that
emitted three lines on a short log and four on a long one would put the newest error on a different
row every time.

⛔ **And they must fork on selection, not on repaint.** The first version forked from the draw chain,
which the repaint metro bangs three times a second — so sitting on the error log meant 3.3 `sh` forks
a second on a Pi, forever, and two overlapping runs would interleave their lines into one router and
scramble the rows.

**Fix:** `err-tail.sh` pads to four lines and `net-probe.sh` always prints three; a `[change]` on the
screen number gates both forks. The gate asserts the fork counts **exactly**, which is what caught the
repaint bug — "did it fork at all" passes it happily.

### The link count is a dash until the device answers

⚠️ `links-` is parsed out of `wire.sh`'s own last line, `wire.sh: N connections`. **If that line ever
changes shape the screen shows a dash forever rather than going red**, and no gate can see it: on the
Mac `t_shell` reports the command and emits nothing, so there is no output to parse. Only the bench
can judge this row.

## Design

**Every row is a single symbol, with dashes where you want spaces.** mother's chain is
`[r screenLineN]` → `[list]` → `[list append send /oled/line/N]` → `oscOut`, so a multi-atom message
does arrive — but **whether the display joins the arguments with spaces has never been measured on
this device**, and this is the one tool that must not surprise you. Dashes are ugly and certain.
`makefilename` builds every dynamic row. The shell scripts flatten their own whitespace to dots so
the same rule holds for text this patch did not write.

**It draws with `screenLine` rather than `oscOut`.** C-5 gives `g_oled` sole ownership of `oscOut`
*inside the instrument*; this is a different patch and a different process, so it owns its own
surface. `screenLine` is five rows of 21 characters with no drawing code at all, which is the right
trade for a tool whose content is six words and four numbers.

⛔ **It deliberately does not take the encoder, although it is allowed to.** Asking means banging
`enableSubMenu`, and that is an **override which takes the click as well** — the press that leaves a
running patch. **A debug tool you cannot get out of at a venue is worse than one you steer with the
keys.** Items 313 and 314 on [organelle.md](../device/organelle.md). The lowest key sends `goHome`
and every screen's help row says so, so the encoder would buy scrolling and cost the exit.

**The keyboard is the menu because it is the one surface that cannot go missing.** Knobs, the aux
button and 25 keys all arrive from mother whatever the USB bus is doing — and the rig fault most
likely to bring you here is a device that stopped enumerating.

**Three action keys work from any screen.** Firing a probe is something you want while looking at the
MIDI monitor, not after navigating away from it; screens 2 and 5 document the keys rather than
owning them.

## Open

No unknowns. What the gate cannot reach — the `links-` parse, and whether a real device answers a
real probe — is [debug-bench.pd](../../test/bench/debug-bench.pd)'s, and that is a difference of
oracle rather than a gap in coverage.
