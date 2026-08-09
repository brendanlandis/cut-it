<!-- schema: module -->
# Errors and the error bus

**Files:** `Cut It/u_err.pd`, `Cut It/logroll.sh` · **Gate:** `test/gate/err-assert.sh` · **Bench:** `test/bench/display-bench.pd`

## What it is

**The Organelle runs Pd with `-nogui`, so an error you cannot see is a silent failure** — and Pd's
own failure mode for a wrong message is to print and continue. `u_err` is the one filter that decides
what a problem is allowed to interrupt, and **it is the only file that decides it**: any abstraction
reports with `[s err]` and a message box, and none of them knows or cares what mode the instrument is
in.

It was built in the first infrastructure pass rather than retrofitted. *(judgment call: an
architecture requirement, not a debugging convenience.)*

**The message format is rule C-12** — `<level> <source> <text>`, level `warn` or `fail`, text one
symbol of at most 21 characters. `u_err` decides what reaches the screen; `g_oled` decides what it
looks like.

## Facts

### What the filter does

| | Evidence | Item |
|---|---|---|
| **Filters by `mode`** — compose shows everything, perform only `fail`. One place, same bus, same callers | verified | — |
| **Defaults to verbose**, which is the state before any `mode` arrives. `u_map` has driven `mode` since Phase 6 and the filter needed no change — `route` matches on the selector, so a two-atom `compose mode-1` sets verbose exactly as a bare `compose` did | verified | — |
| ⛔ **It never draws.** C-5 gives `g_oled` sole ownership of `oscOut`, so this forwards onto `disp` as `alert <level> <source> <text>` | verified | — |
| **The bus is unfiltered; only the SCREEN is filtered.** An unconditional `[print err]` means the by-hand SSH console sees every error raised, even in perform mode | verified | — |
| **A level that is neither `warn` nor `fail`** falls out of `route`'s reject and is printed as `err-BAD-LEVEL` rather than displayed. Swallowing it would be the exact failure this file exists to prevent | verified | — |
| **Errors time out; they are never modal.** A stuck error covering the display mid-set is worse than a missed warning | verified | — |

⚠️ **This does not catch Pd's own runtime errors** — those still go to tty1. It catches the ones we
raise, which is most of what actually goes wrong.

### The log that survives the session

| | Evidence | Item |
|---|---|---|
| **Capture is unconditional.** The mode filter decides what reaches the SCREEN, never what reaches the log | verified | — |
| `/sdcard/cut-it-err.cur` is the current session, bounded at **200 lines** from inside the patch | verified | — |
| `/sdcard/cut-it-err.log` is the durable one, bounded at **400 lines** and trimmed to 300 by `logroll.sh` | verified | — |
| `logroll.sh` runs **once per load** through `[shell]`, rolls `.cur` into `.log` and writes a `BOOT` line — the wall clock Pd 0.49 does not have. It echoes how many lines it carried, because a silent roll is indistinguishable from a missing script | verified | — |
| `[r quitting]` forces a last flush, so the final seconds of a session are not lost | verified | — |

## Traps

### Anything built with `list prepend` is a list, and `route` will reject it

Callers use a **message box**, which already carries `warn` or `fail` as its selector. A message
assembled with `[list prepend]` has the selector `list` instead, so `u_err`'s `route` drops it — and
the error that was raised to stop something being silent is itself silent.

**Fix:** finish an assembled error with `[list trim]` (C-6). `m_nano`'s unmapped-CC path is the
worked example.

### The text does not wrap

`gPrintln` draws until it runs off the right of the screen. Nothing downstream can shorten an error
for you.

**Fix:** keep the text to 21 characters at the call site (C-12).

### `route`, not `select`, for the mode

`mode` arrives as a bare selector — `compose`, not `symbol compose` — and `select` has no method for
that. Same underlying fact as the `list trim` trap: Pd distinguishes a message's selector from its
arguments.

**Fix:** `[route compose perform]`.

## Design

**One filter, one place.** The alternative was every caller deciding whether its own problem was
worth showing, which puts the mode in every abstraction and makes a change to the policy a change to
all of them.

**Defaulting to verbose degrades safely** — the worst case is an error you did not need. The reverse
default fails in the direction of silence, which is what the file exists to prevent.

⚠️ **A mode split weighted toward `perform` silently quietens the error display.** The six modes are
placeholders but their 3/3 ratio is not, and the sound work is what will name them — see
[plan-v04.md](../plan-v04.md).

## Open

No unknowns. The filter, the log and the levels are all asserted by
[test/gate/err-assert.sh](../../test/gate/err-assert.sh).
