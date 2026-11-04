<!-- schema: module -->
# Errors and the error bus

**Files:** `Cut It/u_err.pd`, `Cut It/logroll.sh` · **Gate:** `test/gate/err-assert.sh` · **Checklist:** `test/checklists/display.md`

## What it is

**The Organelle runs Pd with `-nogui`, so an error you cannot see is a silent failure** — and Pd's
own failure mode for a wrong message is to print and continue. **`u_err` draws every warning and
every failure, on every page** (Brendan, 2026-11-04). It is the only file that decides what a
problem is allowed to interrupt, and it decides by level alone: any abstraction reports with
`[s err]` and a message box, and neither the callers nor `u_err` know or care which page the
instrument is on.

*(judgment call)* It is an architecture requirement, not a debugging convenience — built in from
the start rather than retrofitted.

**The message format is rule C-12** — `<level> <source> <text>`, level `warn` or `fail`, text one
symbol of at most 21 characters. `u_err` decides what reaches the screen; `g_oled` decides what it
looks like.

## Facts

### Three levels, and only the screen tells them apart

<!-- check: pd-route "Cut It/u_err.pd" warn -->

| Level | Logged | Drawn | Evidence | Item |
|-------|--------|-------|----------|------|
| `warn` | yes | **always** | verified | — |
| `fail` | yes | **always** | verified | — |
| `info` | yes | **never** | verified | 291 |

⛔ **`info` draws nothing by construction, not by filtering** — its `route` outlet is connected to
nothing, the same deliberate dead-outlet idiom `u_map` uses. That works because the logfile tap
hangs off the trigger **above** the route, so every level reaches the log whatever the screen does.

⛔ **It exists because diagnostic detail and operator alerts are not the same thing.** `u_present`
forks `wire.sh` up to eight times per recovery episode and every one belongs in the log; nine alerts
on a 21-character screen mid-set does not.

### What it does

| | Evidence | Item |
|---|---|---|
| **Decides by level alone** — `warn` and `fail` are drawn on every page, `info` never. Nothing in it reads the `mode` bus, and `err-assert.sh` reads that off the patch as well as driving it | verified | — |
| ⛔ **It never draws.** C-5 gives `g_oled` sole ownership of `oscOut`, so this forwards onto `disp` as `alert <level> <source> <text>` | verified | — |
| **An unconditional `[print err]`** means the by-hand SSH console sees every error raised, `info` included | verified | — |
| **A level that is neither `warn` nor `fail`** falls out of `route`'s reject and is printed as `err-BAD-LEVEL` rather than displayed. Swallowing it would be the exact failure this file exists to prevent | verified | — |
| **Errors time out; they are never modal.** A stuck error covering the display mid-set is worse than a missed warning | verified | — |

⚠️ **This does not catch Pd's own runtime errors** — those still go to tty1. It catches the ones we
raise, which is most of what actually goes wrong.

### The log that survives the session

| | Evidence | Item |
|---|---|---|
| **Capture is unconditional.** The level decides what reaches the SCREEN, never what reaches the log | verified | — |
| `/sdcard/cut-it-err.cur` is the current session, bounded at **200 lines** from inside the patch | verified | — |
| `/sdcard/cut-it-err.log` is the durable one, bounded at **400 lines** and trimmed to 300 by `logroll.sh` | verified | — |
| `logroll.sh` runs **once per load** through `[shell]`, rolls `.cur` into `.log` and writes a `BOOT` line — the wall clock Pd does not have, 0.49 or 0.57. It echoes how many lines it carried, because a silent roll is indistinguishable from a missing script | verified | — |
| `[r quitting]` forces a last flush, so the final seconds of a session are not lost | verified | — |
| Each line is stamped with `[timer]` — **milliseconds since load**, and there is no other clock in the patch | verified | — |
| ⛔ The stamp reaches `[text]` as a **symbol**, through `[makefilename %d]`, and must | verified | 290 |

## Traps

### A float stamp rots after 16 minutes 40 seconds

⛔ `[text]` writes a float with `%g`, six significant figures, so a millisecond stamp loses
precision 16 min 40 s into a session: 10 ms from then, 100 ms from 2 h 46 min (Pure Data, in
Reference). Both forms are in the device's own log. **The log is the only record of when anything
happened on this instrument, and a set runs for hours.**

**Fix:** `[makefilename %d]` between `[timer]` and the `[list prepend]` that builds the line, so
`[text]` stores a symbol it cannot reformat. Exact to the millisecond for 4 h 39 min, where a Pd
float stops holding every integer, and to 2 ms after (Pure Data, in Reference).

⚠️ **Not a change of unit, and the arithmetic is the reason.** Logging tenths of a second would be
exact for only 27.8 hours and whole seconds for 11.6 days, and every stamp already cited in `ref/`
and in `git log` is in milliseconds.

⚠️ **`makefilename %g` is the bug wearing the fix's clothes** — it formats as `[text]` does, so
the box being present proves nothing. `err-assert.sh` asserts the **format**, not the
object.

### Anything built with `list prepend` is a list, and `route` will reject it

Callers use a **message box**, which already carries `warn` or `fail` as its selector. A message
assembled with `[list prepend]` has the selector `list` instead, so `u_err`'s `route` drops it — and
the error that was raised to stop something being silent is itself silent.

**Fix:** finish an assembled error with `[list trim]` (C-6). `c_presence`'s `device-lost` warning
is the worked example.

### The text does not wrap

`gPrintln` draws until it runs off the right of the screen. Nothing downstream can shorten an error
for you.

**Fix:** keep the text to 21 characters at the call site (C-12).

## Design

**One filter, one place, by level.** The alternative was every caller deciding whether its own
problem was worth showing, which makes a change to the policy a change to all of them.

**No page hides a warning** (Brendan, 2026-11-04: any warnings or errors that come up should be
displayed). A filter on the screen fails in the direction of silence, which is what this file exists
to prevent, and the worst case of drawing everything is an error you did not need.

## Open

No unknowns. The levels, the log and the screen drawing on every page are all asserted by
[test/gate/err-assert.sh](../../test/gate/err-assert.sh).

