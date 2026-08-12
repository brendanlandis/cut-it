# Plan v0.3.5.3 — the shift key, and three controls that move

**The diagnostic screen is on a button that cannot report its own device.** `lp-cc-80` summons
`g_oled`'s device roster, and a Launchpad that has come unplugged sends no CC — so the one control
that would name the missing device is dead in exactly that case. Only the **Organelle's own panel**
can never be the thing that went away, and its four knobs are continuous, its aux button is the
transport, and its 25 keys play the Volca.

**So the aux button becomes a modifier and the keyboard gains a second layer.** That needs two
things out of the way first, and both are improvements on their own:

| Move | From | To | Why it is better anyway |
|---|---|---|---|
| **Mode selection** | `xport-1`…`xport-6` — the nano's transport row | **`lp-cc-91`…`lp-cc-96`** | `g_grid` **already lights those six as the mode lamps**. The thing you look at becomes the thing you press |
| **Start / stop** | `og-aux`, one button toggling both | **`xport-2` and `xport-5`** | Those are physically **PLAY** and **STOP** — item 31. Two of the six labels stop lying |
| **The aux button** | `transport` | **A pure modifier** | Press is shift on, release is shift off. No latch, no timing change, and it frees 25 controls rather than one |

⛔ **The order matters and it is the order below**: nothing may be left without a mode selector or
without a transport in between two commits.

✅ **Brendan's call, and the shape is his.** Making aux a modifier *while* it still carried the
transport would have forced start/stop from the press onto the release — a feel change to the most
used control on the panel. Moving the transport off it first makes the modifier free.

---

## ⚠️ Constraints that bind everything below

- **Pd vanilla 0.49, permanently.** ⛔ **Never open or save an Organelle-bound patch in plugdata.**
  **Vanilla objects only.**
- ⛔ **Invoke the `pd` skill before touching a `.pd`, the `gate` skill before anything under `test/`,
  and the `docs` skill before a `ref/` page.**
- ⛔ **A bench `.pd` is an OUTPUT.** Edit `test/bench/bench_steps.py` and regenerate.
- ⛔ **A gate is not trusted until it has FAILED.** Reintroduce the bug, watch it go red, revert.
- ⚠️ **Read `run.sh`'s `RESULT:` line; do not grep for it.** ⛔ **One suite run at a time.**
- **Commit as you go — one phase, one commit.** ⛔ **Brendan is the sole author: no
  `Co-Authored-By` trailer and no agent byline.**

---

## What to read, and how much

| Document | How much | Why |
|---|---|---|
| [CLAUDE.md](CLAUDE.md) | **All of it** | The router |
| The **`pd`** / **`gate`** / **`docs`** skills | ⛔ **Invoked, not read** | Pd in four files, three gate drivers, two benches, four pages |
| [ref/module/map.md](ref/module/map.md) | **All of it** | *The destinations*, *the allowlist guard*, and **the six hardcoded keys that come first** — which is the box Phase 1 edits |
| [ref/device/organelle.md](ref/device/organelle.md) | The panel section and the keyboard section | `aux` is `1`/`0`, the keys publish their release, and `og-aux` reaches `disp` |
| [ref/device/nanokontrol.md](ref/device/nanokontrol.md) | *Transport buttons* | The six are REW · PLAY · FF · LOOP · STOP · REC on CC 41–46 |
| [ref/device/launchpad.md](ref/device/launchpad.md) | The CC map, and *CC 90 is the panic button* | CC 91–98 is the top row; CC 80 and CC 90 are already spoken for |
| [ref/module/display.md](ref/module/display.md) | The `g_grid` layer table, and the diag section | The mode lamps, and the screen this whole plan exists to make reachable |
| `Cut It/m_organelle.pd` | **All of it** | The shift latch and the second keyboard layer go here |
| `Cut It/u_map.pd` | Its **first** `route` box and the destination `route` | The mode selector, and where `start` / `stop` / `diag` / `recover` already live |
| `git log` | **Grep it, never read it** | Git is the journal |

**Do not read** [ref/wifi.md](ref/wifi.md), [ref/device-os.md](ref/device-os.md),
[ref/module/state.md](ref/module/state.md) or [ref/module/audio.md](ref/module/audio.md).

---

## What is already true

- **The six mode keys are HARDCODED and come first**, above the table lookup — they *are* the mode
  selector, so a mode change can never itself be mode-dependent, and a broken table still leaves you
  able to change mode on a device with no console. **That property is kept; only the six names
  change.**
- ⛔ **`aux` sends `1` and `0`** — [organelle.md](ref/device/organelle.md), item 42's row. `m_organelle`
  discards the `0` in a `[select 1]` reject **by choice**, not because it is unavailable.
- ⛔ **The keys already publish their release**, as velocity 0 — item 293. A shifted layer therefore
  needs no new event model.
- **The keys reach `param` and NOT `disp`**, and `u_map` does not report them raw either — a
  deliberate exception to item 242, because five parameter rows would be evicted twice per note.
- **`m_launchpad`'s `[ctlin]` is unfiltered**, so `lp-cc-91`…`lp-cc-96` already publish with no
  change to that file.
- **`g_grid`'s `home` draws six mode lamps on CC 91–96** off the `mode` bus. A lamp is output and a
  press is input, so nothing loops.

---

## Phase 1 — mode selection moves to the Launchpad's top row

`u_map`'s **first** `route` box swaps its six arguments: `xport-1`…`xport-6` become
`lp-cc-91`…`lp-cc-96`. Everything it does not match still falls out of its reject into the table.

### ⛔ The one thing that is not a rename

**A nano transport button publishes on PRESS ONLY. A Launchpad CC button sends 127 on the press and
0 on the release.** The six outlets feed their `compose mode-N` / `perform mode-N` message boxes
**with no non-zero gate at all** — safe today only because a release never arrives. Left alone, every
mode selection would fire **twice**, once on each edge: idempotent, so nothing looks wrong, and every
`mode` message, state-store write and `g_grid` repaint doubles.

⛔ **The gate cannot go above the route.** The reject is the whole table path, and `og-key-*`
releases are **real note-offs** that `volca-key` must act on — item 293. Gating the value before the
route would swallow every one of them and leave notes hanging on the Volca.

**Fix:** gate the six branches individually, below the route. `[select 0]`'s **reject** carries
anything that is not a release, which is the value the message box wants anyway (C-8).

### The work

| File | Change |
|---|---|
| `Cut It/u_map.pd` | The six route arguments, six `[select 0]` gates, and the comment that calls them transport keys |
| `test/gate/map-assert-drive-gen.py` | Its `MODE-4` and `MODE-1-BACK` windows press `xport-4` / `xport-1` |
| `test/gate/nano-assert.py` | References `xport` |
| `ref/module/map.md`, `ref/device/nanokontrol.md`, `ref/device/launchpad.md` | Where the mode selector lives |

⚠️ **`xport-1`, `-3`, `-4`, `-6` — REW, FF, LOOP and REC — become free controls.** Four unmapped
buttons for v0.4, at no cost.

---

## Phase 2 — start and stop move to PLAY and STOP

Twelve rows in `Cut It/cut-it-map.txt`: `xport-2` → `start` and `xport-5` → `stop`, in all six
modes. The six `og-aux transport` rows go.

⚠️ **`transport` keeps its place on the allowlist with no row naming it**, exactly as `panic` does.
It is a destination on a `route` box feeding a readable handler; a one-button toggle is still the
right answer for a smaller rig and costs nothing to keep.

⚠️ **Between this commit and the next, `og-aux` is unmapped and therefore reports itself raw on
`disp`** — item 242's rule doing its job. It stops when Phase 3 makes aux a modifier rather than a
control.

---

## Phase 3 — the aux button becomes a modifier

`m_organelle`: `[r aux]` stops feeding `[select 1]` → `og-aux 1`, and instead sets a `$0-shift`
flag — **1 on the press, 0 on the release.** While it is 1, the keyboard publishes
`og-shift-60`…`og-shift-84` instead of `og-key-60`…`og-key-84`.

### ⛔ A release must carry the same name as its press

**Press a shifted key, let go of aux, then let go of the key** — and the press published
`og-shift-72` while the release publishes `og-key-72`. The shifted control never sees its note-off
and an unshifted one gets a note-off it never had a note-on for. In mode 1 that is **a stuck note on
the Volca**, and nothing anywhere reports it.

**Fix:** the layer is latched **per key, at press time**. A 25-element array indexed by
`pitch - 60`, written on the press (velocity > 0) from the current flag and **read on both edges** to
choose the name — the same shape `u_map`'s pickup uses for its four knobs. A release then cannot
disagree with its own press however the modifier moves underneath it.

### ⚠️ A modifier with no feedback is a mystery

`m_organelle` sends `disp` → `modal shift` on the press and `modal-off` on the release, so holding
aux says so on the OLED. **A modal is priority 2 and diag is 3**, so a shifted key that summons the
roster still draws over it. ⚠️ **A missed release leaves the word up for the 30 s safety TTL** —
which is what that TTL is for, and the failure is visible rather than silent.

*(judgment call)* — reverse it if it reads as noise in the hand.

### ⛔ aux publishes no control at all any more

It is a modifier, so it is **not** an unmapped control and must not report itself raw on `disp`.
⚠️ **The aux LED is unaffected** — `g_led` draws the transport state, not the button.

---

## Phase 4 — what the shifted keys do

Three rows, in all six modes. **Proposed, and to be judged in the hand:**

| Control | Destination | Why there |
|---|---|---|
| `og-shift-60` — the **lowest** key | `diag` | An end of the keyboard, findable by feel without looking |
| `og-shift-72` — the **middle** key | `stop` | ⛔ The panel keeps a way to silence the rig **when the nano is unplugged**, which is what moving the transport off aux costs |
| `og-shift-84` — the **highest** key | `recover` | The destructive one, as far from `diag` as the keyboard allows. It reloads the patch |

⛔ **`stop` and `recover` on the Organelle are the point, not a bonus.** After Phase 2 the transport
lives on the nano and `recover` lives on the Launchpad, so **both critical controls sit on devices
that can be unplugged.** These two rows mean the panel alone can always stop a runaway rig and force
a reload, whichever controller has died.

⚠️ **`recover` reads the RELEASE** — item 298, two tiers on one control. A shifted key publishes both
edges, so it works unchanged; **but the release carries the latched name**, which is exactly what
Phase 3's array guarantees. Without it the hold would never complete.

---

## Tests

⛔ **Invoke the `gate` skill.** ⛔ **Make every new check fail before trusting it.**

| Gate | Add |
|---|---|
| `test/gate/map-assert.sh` | Mode selection from `lp-cc-9N`, **and ⛔ that a release does NOT select it a second time** |
| `test/gate/organelle-assert.sh` | The shift flag; a key publishing `og-shift-NN` while held; ⛔ **the press/release name agreeing across an aux release mid-note**; and that `og-aux` publishes no control |
| `test/gate/map-assert.sh` | `xport-2` → `start`, `xport-5` → `stop`, and the shifted rows resolving |

**Bench steps** through `test/bench/bench_steps.py` and a regenerate. ⚠️ **Counts must be exact.**
The `nanokontrol` bench's mode steps move to `launchpad`; `display`'s diag step changes its control.

---

## Verification

```sh
./test/run.sh                        # read the RESULT: line
python3 test/gate/docs-check.py -v
./tools/deploy.sh
```

Then, on the rig: **hold aux and the OLED says `shift`; the lowest key draws the roster; unplug the
nano and the middle key still stops the instrument.**

⚠️ **The Mac is not the device.** Phase 6 passed 25/25 on the Mac twice and shipped three bugs.
⚠️ **The shift key's FEEL is the part no gate can reach** — whether a modifier on the aux button is
natural in the hand is a bench verdict.

---

## Done means

1. Mode is selected from the Launchpad's lit top row, and a release does not select it twice.
2. Start and stop are on PLAY and STOP, and `nanokontrol.md` no longer says those labels lie.
3. `aux` is a modifier, the keyboard has 25 shifted controls, and ⛔ **a release always carries the
   name its press did.**
4. `diag`, `stop` and `recover` are reachable from the Organelle alone, recorded on
   [ref/device/organelle.md](ref/device/organelle.md).
5. `lp-cc-80` is **freed** — the diag layer's blind spot on
   [ref/device/launchpad.md](ref/device/launchpad.md) is struck, and that page's CC 80 section goes
   with it.
6. `./test/run.sh` reports `RESULT: PASS`, and every new check has been seen to fail.
7. **This file is deleted.**

⛔ **This plan does not hand its open items to [plan-v04.md](plan-v04.md).**
