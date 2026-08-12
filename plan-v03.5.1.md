# Plan v0.3.5.1 — diagnostics inside the instrument

**When a controller stops working mid-set, nothing on the instrument tells you which one.** The
presence layer knows — it polls every active device every two seconds, declares one lost after three
misses, and runs a bounded re-wire. What it surfaces is a `warn` on a 21-character screen and a
`fail` when the bound is spent. **There is no way to ask *"what is the rig's state right now"*.**

This plan builds two answers, in the two places you can already look without a laptop: **a layer on
the OLED**, and **buttons on the phone**.

✅ **Nothing gates it.** Hot-swap landed on 2026-08-10 and the presence bus is live — `expect`,
`tick`, `lost`/`back` and `seen`, with `seen` published by the passive layer **for exactly this
screen** and read by nothing yet. See [ref/module/presence.md](ref/module/presence.md).

**One sibling plan came out of the same batch** — [plan-v03.5.2.md](plan-v03.5.2.md), the standalone
debug patch. ⚠️ **Run this one first** — see *Where this sits in the order*.

---

## ⚠️ Constraints that bind everything below

- **Pd vanilla 0.49, permanently.** ⛔ **Never open or save an Organelle-bound patch in plugdata.**
  **Vanilla objects only.**
- ⛔ **Invoke the `pd` skill before touching a `.pd`, and the `gate` skill before touching
  anything under `test/`.**
- ⛔ **A bench `.pd` is an OUTPUT.** Edit `test/bench/bench_steps.py` and regenerate; never the
  `.pd`.
- ⛔ **A gate is not trusted until it has FAILED.** Reintroduce the bug, watch it go red, revert.
- ⚠️ **Read `run.sh`'s `RESULT:` line; do not grep for it.** ⛔ **One suite run at a time**, and
  never while a bench is on the device.
- **Commit as you go**, in reviewable batches — the three phases are good boundaries.
  ⛔ **Brendan is the sole author: no `Co-Authored-By` trailer and no agent byline.**

---

## What to read, and how much

| Document | How much | Why |
|---|---|---|
| [CLAUDE.md](CLAUDE.md) | **All of it** | The router |
| The **`pd`** / **`gate`** / **`docs`** skills | ⛔ **Invoked, not read** | New Pd, new gate checks, edits to three `ref/` pages |
| [ref/conventions.md](ref/conventions.md) | The rules table, then only the sections it links | `C-1`…`C-14`. **C-2, C-5, C-6 and C-8 are all live here** |
| [ref/module/display.md](ref/module/display.md) | **All of it** | The priority model, the geometry, the `disp` selector table, and the Trap about what a new selector costs |
| [ref/module/presence.md](ref/module/presence.md) | **The bus, the three kinds, and `Design`** | Where the screen's data comes from, and the one asymmetry Phase 1 may change |
| [ref/module/map.md](ref/module/map.md) | *The destinations* and *The allowlist guard* | How a control gets a new meaning |
| [ref/device/phone.md](ref/device/phone.md) | **All 288 lines** | The wire format, the rate limiting, the address discovery, and the one-way property Phase 2 changes |
| `Cut It/g_oled.pd` | Its `route`, `pd layers`, `pd pick`, and `pd text-out` | You are adding a layer. The cascade is where it goes |
| `Cut It/u_net.pd` | **All of it, comments included** | You are adding an inbound path. Its comments hold the UDP-connect trap and the address-resolution timings |
| `tools/pdparty-scene/CutItRemote/_main.pd` | **All of it** | The scene you are adding buttons to. ⛔ Its staleness detector must stay phone-side |
| `git log` | **Grep it, never read it** | Git is the journal |

**Do not read** [ref/wifi.md](ref/wifi.md), [ref/device-os.md](ref/device-os.md),
[ref/module/state.md](ref/module/state.md) or [ref/module/tempo.md](ref/module/tempo.md).

---

## What is already true

### The display arbiter

- **Four layers, one winner per frame:** `home 0 < param 1 < modal 2 < alert 3`. **Priority is a
  `[select 1]` cascade rather than arithmetic**, in `g_oled`'s `pd pick` — *"adding a layer is one
  more link."* **TTL is one retriggered `[delay]` per layer.**
- ⛔ **A new selector on `disp` costs one `route` argument in every consumer that has a
  fallthrough** — today `g_oled` and `u_net`. Everything a consumer does not recognise is a
  parameter by definition, so a selector with no branch is **drawn as a nonsense parameter row**.
- **Layers hold STATE, not draw calls**, which is why rate limiting needed no code.
- **Geometry that already exists:** the 3–5-mover layout is 8px rows at `y = 0, 9, 18, 27, 36`, and
  ✅ **all three type-size layouts are legible at playing distance** — item 258.

### Presence

- **Every device keeps its own last-heard clock; they all share ONE bounded recovery.**
- **The bus carries `expect <src> <kind>`, `tick`, `lost <src>` / `back <src>`, and `seen <src>`.**
- **Three kinds, and every layer declares one:** `active` (`m_launchpad` `m_nano` `m_404`) is polled
  and can be lost; `passive` (`m_organelle`) is never polled and **never ages**; `none` (`m_volca`)
  can never be lost at all.
- ⚠️ **`seen` is a cord for `active` and a bus message for `passive`**, deliberately — an active
  device's liveness is consumed two boxes away. **Nothing reads `seen` today.** This screen is what
  it exists for.
- ⛔ **`<src>` on the bus is the ABSTRACTION's name, never the hardware's** — `m_nano`, never
  "nanoKONTROL". That is the `m_` boundary rather than a naming preference.
- ⚠️ **A `warn` can name a device you did not touch.** Pulling any USB cable can knock a bystander
  off the bus long enough to cross the three-poll threshold — item 286.

### The phone

- **One-way in practice.** Four Organelle→phone OSC addresses, none the other way, and the scene has
  no outbound sends. **`u_net` has no `netreceive` at all.**
- **`u_net` owns no selector on the display bus** — it subscribes and mirrors, which is why adding
  it cost the OLED's route nothing.
- ⚠️ **The staleness detector lives on the phone by necessity.** UDP is fire-and-forget; only the end
  that stops hearing can know. Its default label is `NO-LINK`, not `ok`.
- **The Organelle never waits for the phone.** Phone off, phone crashed, wifi gone — **the
  instrument plays identically.**

---

## Phase 1 — the diag layer on the OLED

**The highest-value piece, because it needs nothing plugged in and no mode change.**

### Where it sits in the priority model

**Between `modal` and `alert`**, giving `home 0 < param 1 < modal 2 < diag 3 < alert 4`:

- **Above `modal`**, because `modal` is **sticky** — cleared by `modal-off` or a 30 s safety TTL —
  and diag is summoned deliberately. ⛔ **A diag below a live modal would show nothing, which looks
  exactly like a dead patch.**
- **Below `alert`**, because ⚠️ **a diagnostic that covers an alert is worse than no diagnostic.**

Write it onto [ref/module/display.md](ref/module/display.md)'s layer table, which is the page that
owns the model.

### What it shows: here / missing / never seen

**Not a live age** — decided 2026-08-11. Five 8px rows reusing the existing 3–5-mover geometry, one
per source in the roster `expect` publishes.

⚠️ **Presence is *last heard*, not *alive*. Label it honestly** — a nanoKONTROL nobody has touched is
not distinguishable from one on the floor, and no amount of code changes that. ⚠️ `m_volca` registers
`none` and can never be lost, so it reads as its own state rather than as `here`; ⛔ **do not draw a
`none` device as healthy**, because nothing has ever checked it.

### ⬜ The one decision, and it is cheap either way

**Telling *missing* from *never seen* needs a per-source "has this ever answered" bit, and the
presence bus does not carry one.** `c_presence` publishes `lost <src>` **unarmed** — the gate is
split, not removed, and `$0-seen-ever` gates only the `warn`. So on the bus, a device absent since
load and a device that worked and vanished **look identical**.

1. **Recommended — `c_presence` publishes `seen <src>` once, the first time its device ever
   answers.** One message per device per session, no new polling and no rate concern. It makes
   `seen` uniform in the mildest possible way — passive layers publish on every decode, active
   layers exactly once — and gives [ref/module/presence.md](ref/module/presence.md)'s ⬜ a real
   consumer. ⛔ **Rewrite the *asymmetry is deliberate* paragraph rather than leaving it
   contradicted**, and note that `c_presence.pd` is in three benches' dep lists.
2. **Alternative — read the `err` bus.** `warn <src> device-lost` fires only for a device that was
   seen and then lost — item 276, verified. No bus change, but it couples this screen to another
   module's message text.

### How it is summoned

**A `diag` destination on `u_map`'s literal `route` box, plus a row in `Cut It/cut-it-map.txt`** —
the same shape `recover` uses on `lp-cc-90`. ⛔ **The allowlist guard is not optional**: the table
never names a `[send]`, it names a destination that **must exist as a literal argument on a `route`
box** feeding a handler you can read on the canvas. Skip it and the property is gone silently,
because nothing fails and no test notices.

**Cleared on a TTL**, one retriggered `[delay]` like every other layer.

### The work

| File | Change |
|---|---|
| `Cut It/g_oled.pd` | One `route` argument, one layer flag and TTL in `pd layers`, **one link in `pd pick`**, one draw subpatch through the existing `pd text-out` |
| `Cut It/u_net.pd` | ⛔ **The matching `route` argument, matched and left unconnected** — or diag reaches the phone as a nonsense parameter |
| `Cut It/u_map.pd`, `Cut It/cut-it-map.txt` | The `diag` destination and its row |
| `Cut It/c_presence.pd` | Only under decision 1 above |

⛔ **Two Pd comments still point at the plan this one was split out of, and they were deliberately
left for you.** `c_presence.pd` and `m_organelle.pd` both say *"plan-v03.5's diagnostic screen"* —
**this screen**. They were not repointed when the split landed, because `c_presence.pd` is in the
`launchpad`, `midi` and `nanokontrol` dep lists and a comment edit alone would have staled six fresh
verdicts for nothing. **You are staling those benches anyway, so fix both here.** ⚠️ `docs-check.py`
cannot catch this — `DOCNAME`'s name class has no dot, so a bare `plan-v03.5.N.md` in a `.pd` is
invisible to it. **Grep, do not trust the gate.**

⛔ **Every branch out of `route` goes through `[list append]` first**, and assembled `disp` messages
finish with `[list trim]` — `route` matches a **selector**, not a list's first element (C-6).
⛔ **A reject outlet carries DATA, not a bang** (C-8).

⚠️ **Text is ONE symbol and error text is ≤ 21 characters.** `gPrintln` does not wrap and 16px fits
about ten characters across 128 px. **Write `launchpad-silent`, not `launchpad silent`.**

---

## Phase 2 — the phone becomes interactive

**The largest usability win available**, because the phone is the only thing in the rig with a real
screen and touch.

Add `[netreceive -u 9001]` to `u_net` plus a route with a **closed vocabulary**: re-run `wire.sh`,
clear alerts, request a full status dump, fire a test note at a named device. ⚠️ **Drop everything
else silently**, exactly as `u_net` already swallows reserved selectors outbound.

**That is a robustness argument, not a musical one.** ⚠️ **An inbound path is an attack surface on a
shared network**, and a closed list is what keeps the first one small enough to reason about.

⚠️ **`[netreceive]` in 0.49 cannot tell you who sent a datagram.** Checked before designing around
it, and it is why `phone-ip.sh` exists. **Do not design around a sender identity that is not
available.**

⚠️ **`[r #osc-in]` delivers the address as bare symbols, with no slashes** — `/cutit/hb 210` arrives
as `cutit hb 210`. Route as `[route cutit]` → `[route hb]`.

### On scope

⚠️ **Diagnostics is what this plan builds, not a rule about what the phone may ever do.** Brendan's
call, 2026-08-11: the phone may well drive something musical one day, and note timing is not the only
thing an inbound path could be used for.

So **what goes on [ref/device/phone.md](ref/device/phone.md) is what the path IS** — the port, the
vocabulary it accepts, and that it drops the rest silently. A prohibition on future work is a plan
statement, not a page fact.

**What stays, because it was measured:** the two properties already recorded on that page — how
unevenly the link delivers, and that the instrument plays identically without the phone. **They are
evidence anything musical would have to answer to later, not a veto.**

⚠️ **One small edit falls out of this.** `phone.md`'s `What it is` reads *"Status display,
diagnostics and remote console — **not** performance control"*, which is the same prohibition in
weaker clothes. **Reword it to describe what the link carries today** rather than what it may never
carry.

### The scene

Buttons go in `tools/pdparty-scene/CutItRemote/_main.pd`.

- ⛔ **The staleness detector stays phone-side.** An inbound path does not change that — the
  Organelle still cannot know the phone is gone.
- ⛔ **PdParty only renders iemguis that have send AND receive names.** With `empty` or `-` they
  parse, instantiate, participate — and are **invisible**.
- ⚠️ **Non-GUI objects still occupy canvas space.** Keep the main canvas GUI-only and put plumbing in
  `[pd guts]`.
- ⚠️ **The notch eats 22 canvas units off one end in landscape.** `CutItRemote` keeps content at
  `x = 4` and stops at `x = 426`; leave that alone.
- ⛔ **Do not leave `[print]` in a running scene** — it is transmitted as `/pdparty/print` OSC and
  floods.

---

## Phase 3 — the phone-arbitration decision

⬜ **Nothing arbitrates the phone.** Today `u_net` mirrors and the phone decides, so the priority
model stops at the Organelle. **The moment the phone gains buttons and a diag screen it needs one.**

**Give it the same ordering the OLED has, or decide explicitly that it stays a mirror and record
why.** Either closes it; **a third pass that leaves it unstated does not.** Strike the ⬜ in
[ref/module/display.md](ref/module/display.md)'s `Open`.

---

## Tests

⛔ **Invoke the `gate` skill.** ⛔ **Make every new check fail before trusting it.**

| Gate | Add |
|---|---|
| `test/gate/oled-assert.sh` | The diag layer draws its rows — **and ⛔ that an `alert` covers it.** Assert the cascade in the direction that matters, because a layer that always wins passes any positive test |
| `test/gate/map-assert.sh` | `diag` is on the allowlist and the map row resolves |
| `test/gate/phone-assert.sh` | The inbound path routes its vocabulary — **and the negative: a selector outside the list reaches nothing** |
| `test/gate/presence-assert.sh` | Only if `seen` changes under Phase 1's decision 1 |

**Bench steps** go through `test/bench/bench_steps.py` and a regenerate. ⚠️ **Counts must be exact
rather than non-zero.**

---

## Where this sits in the order

⚠️ **Run this plan BEFORE the next bench session.** `test/runner/steps.py`'s
`DEPS` table stales every bench verdict that depends on a changed file: `g_oled.pd` stales **display,
midi and nanokontrol**; `u_net.pd` stales **phone**; `c_presence.pd` stales **launchpad, midi and
nanokontrol**. ⛔ **A rig session run first would be wasted**, because those verdicts would go stale
again the moment this plan landed.

⚠️ **`python3 test/runner/run.py --list` is the authority on what is stale** — read it rather than
trusting a number written here.

---

## Verification

```sh
./test/run.sh                        # read the RESULT: line
python3 test/gate/docs-check.py -v
./tools/deploy.sh
```

Then, on the rig: **the diag layer names a device you deliberately unplug**, and the phone's buttons
do what they say.

⚠️ **Prove the probe before believing the silence.** If a readout shows nothing, establish that the
readout works — with a device you know is transmitting — before concluding the device is dead.
⛔ **And before calling a hardware symptom an instrument fault, check the patch comments, the `ref/`
page and the gates first.**

⚠️ **The Mac is not the device.** Phase 6 passed 25/25 on the Mac twice and shipped three bugs.

---

## Done means

1. The diag layer names every device's state on the OLED, its position in the priority model is
   written on [ref/module/display.md](ref/module/display.md), and the *here / missing / never seen*
   decision is recorded on [ref/module/presence.md](ref/module/presence.md) — including which of the
   two sources for the ever-heard bit was taken, and why.
2. [ref/module/presence.md](ref/module/presence.md)'s ⬜ about a passive layer's last-heard being
   published and unread is **closed**, because this screen reads it.
3. The phone has buttons and a closed inbound vocabulary, recorded on
   [ref/device/phone.md](ref/device/phone.md) as what the path is.
4. **Phone arbitration is decided** and the ⬜ on [ref/module/display.md](ref/module/display.md) is
   struck.
5. [plan-v04.md](plan-v04.md) §3's *Debugging the rig with no laptop* loses its Tier 1 and Tier 3
   material. ⚠️ **The Tier 2 half belongs to [plan-v03.5.2.md](plan-v03.5.2.md)** — leave it.
6. `./test/run.sh` reports `RESULT: PASS`, and every new check has been seen to fail.
7. **This file is deleted.**

⛔ **This plan does not hand its open items to [plan-v04.md](plan-v04.md).**
