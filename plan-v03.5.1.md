# Plan v0.3.5.1 — the phone becomes interactive

**The phone is the only thing in the rig with a real screen and touch, and it is one-way.** Four
Organelle→phone OSC addresses, none the other way, and `u_net` has no `netreceive` at all. This plan
gives it buttons.

✅ **The OLED half of this plan has landed** — `g_oled`'s diag layer names every device's state on
the instrument, and it is on [ref/module/display.md](ref/module/display.md) with the presence
decision behind it on [ref/module/presence.md](ref/module/presence.md). The reasoning is in
`git log`. **What is left is the phone.**

**One sibling plan came out of the same batch** — [plan-v03.5.2.md](plan-v03.5.2.md), the standalone
debug patch, which touches nothing under `Cut It/` and is independent of this one.

---

## ⚠️ Constraints that bind everything below

- **Pd vanilla 0.49, permanently.** ⛔ **Never open or save an Organelle-bound patch in plugdata.**
  **Vanilla objects only.**
- ⛔ **Invoke the `pd` skill before touching a `.pd`, the `gate` skill before touching anything under
  `test/`, and the `docs` skill before a `ref/` page.**
- ⛔ **A bench `.pd` is an OUTPUT.** Edit `test/bench/bench_steps.py` and regenerate; never the
  `.pd`.
- ⛔ **A gate is not trusted until it has FAILED.** Reintroduce the bug, watch it go red, revert.
- ⚠️ **Read `run.sh`'s `RESULT:` line; do not grep for it.** ⛔ **One suite run at a time**, and
  never while a bench is on the device.
- **Commit as you go.** ⛔ **Brendan is the sole author: no `Co-Authored-By` trailer and no agent
  byline.**

---

## What to read, and how much

| Document | How much | Why |
|---|---|---|
| [CLAUDE.md](CLAUDE.md) | **All of it** | The router |
| The **`pd`** / **`gate`** / **`docs`** skills | ⛔ **Invoked, not read** | New Pd, new gate checks, one `ref/` page |
| [ref/device/phone.md](ref/device/phone.md) | **All of it** | The wire format, the rate limiting, the address discovery, and the one-way property this plan changes |
| [ref/conventions.md](ref/conventions.md) | The rules table, then only the sections it links | **C-2, C-6 and C-8 are all live here** |
| `Cut It/u_net.pd` | **All of it, comments included** | You are adding an inbound path. Its comments hold the UDP-connect trap and the address-resolution timings |
| `tools/pdparty-scene/CutItRemote/_main.pd` | **All of it** | The scene you are adding buttons to. ⛔ Its staleness detector must stay phone-side |
| `git log` | **Grep it, never read it** | Git is the journal |

**Do not read** [ref/wifi.md](ref/wifi.md), [ref/device-os.md](ref/device-os.md),
[ref/module/state.md](ref/module/state.md) or [ref/module/tempo.md](ref/module/tempo.md).

---

## What is already true

- **One-way in practice.** Four Organelle→phone OSC addresses, none the other way, and the scene has
  no outbound sends. **`u_net` has no `netreceive` at all.**
- **`u_net` owns no selector on the display bus** — it subscribes and mirrors. ⚠️ **It does carry a
  matched-and-unconnected argument for every one `g_oled` routes**, and `phone-assert.sh` now parses
  both boxes and requires them to be identical.
- ⚠️ **The staleness detector lives on the phone by necessity.** UDP is fire-and-forget; only the end
  that stops hearing can know. Its default label is `NO-LINK`, not `ok`.
- **The Organelle never waits for the phone.** Phone off, phone crashed, wifi gone — **the
  instrument plays identically.**

---

## The inbound path

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

## Tests

⛔ **Invoke the `gate` skill.** ⛔ **Make every new check fail before trusting it.**

| Gate | Add |
|---|---|
| `test/gate/phone-assert.sh` | The inbound path routes its vocabulary — **and the negative: a selector outside the list reaches nothing** |

**Bench steps** go through `test/bench/bench_steps.py` and a regenerate. ⚠️ **Counts must be exact
rather than non-zero.**

---

## Where this sits in the order

⚠️ **Run this plan BEFORE the next bench session.** `test/runner/steps.py`'s `DEPS` table stales
every bench verdict that depends on a changed file, and `u_net.pd` stales **phone**.
⚠️ **`python3 test/runner/run.py --list` is the authority on what is stale** — read it rather than
trusting a number written here.

---

## Verification

```sh
./test/run.sh                        # read the RESULT: line
python3 test/gate/docs-check.py -v
./tools/deploy.sh
```

Then, on the rig: **the phone's buttons do what they say.**

⚠️ **Prove the probe before believing the silence.** If a button appears to do nothing, establish
that the path works — with something you know arrives — before concluding the button is dead.
⛔ **And before calling a hardware symptom an instrument fault, check the patch comments, the `ref/`
page and the gates first.**

⚠️ **The Mac is not the device.** Phase 6 passed 25/25 on the Mac twice and shipped three bugs.

---

## Open

**Nothing.** ✅ The diag layer's summoning control is decided and shipped — `lp-cc-80` in all six
modes, with its bench steps on `display` and `nanokontrol`. See
[ref/device/launchpad.md](ref/device/launchpad.md).

---

## Done means

1. The phone has buttons and a closed inbound vocabulary, recorded on
   [ref/device/phone.md](ref/device/phone.md) as what the path is.
2. `phone.md`'s `What it is` describes what the link carries rather than what it may not.
3. `./test/run.sh` reports `RESULT: PASS`, and every new check has been seen to fail.
4. **This file is deleted.**

⛔ **This plan does not hand its open items to [plan-v04.md](plan-v04.md).**
