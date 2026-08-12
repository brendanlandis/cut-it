# Plan v0.3.5.0 — the venue kit

**Two things stand between the rig and a set played with no laptop in the room**, and neither is
code. Both are Brendan's, in the room, with the hardware in front of him.

⛔ **NOTHING ABOUT THE NETWORK IS IN THIS FILE, AND NOTHING ABOUT IT MAY BE ADDED.** The stage
procedure, the mechanics, the evidence and what to do if it misbehaves are all on
[ref/wifi.md](ref/wifi.md) — **one page, and this plan is deleted when the work lands.** ⚠️ **Read
that page before either task; do not copy any of it back here.**

**Two sibling plans came out of the same batch** — [plan-v03.5.1.md](plan-v03.5.1.md), diagnostics
inside the instrument, and [plan-v03.5.2.md](plan-v03.5.2.md), the standalone debug patch.
⚠️ **Run 5.1 before this plan's rig session** — see *Where this sits in the order*.

---

## ⚠️ Constraints

- **Commit as you go.** ⛔ **Brendan is the sole author: no `Co-Authored-By` trailer and no agent
  byline.**
- ⚠️ **Nothing here changes a `.pd`**, so `./test/run.sh` is not part of this plan's loop —
  `python3 test/gate/docs-check.py -v` is.
- ⛔ **Both tasks are Brendan's and their verdicts are his.** This plan's job is to record them on
  the right `ref/` page.

---

## What to read

| Document | How much | Why |
|---|---|---|
| [CLAUDE.md](CLAUDE.md) | **All of it** | The router |
| The **`docs`** skill | ⛔ **Invoked, not read** | Every deliverable here is a `ref/` edit |
| [ref/wifi.md](ref/wifi.md) | **All of it** | ⛔ **The subject matter of task 1**, including how to stage a session so it does not strand you |
| [ref/device/phone.md](ref/device/phone.md) | *The network*, *Traps*, `Open` | Task 2, and the ⬜ it closes |

**Do not read** any gate, `test/runner/`, or any `ref/module/` page. Nothing here touches them.

---

## ⬜ Task 1 — measure the stage network over a real set. Item 45

**Nothing has ever measured whether the stage link holds for the length of an actual set**, and
⚠️ it *"needs an actual set's duration to mean anything"* — so this closes by construction, but
**only if the test is actually run.**

⛔ **Stage the session per [ref/wifi.md](ref/wifi.md) first.** Starting it cuts off every Mac-side
tool at once, and that page holds the checklist for what must already be on the device.

**Record the result on [ref/wifi.md](ref/wifi.md) and strike item 45 from its `Open`.**

## ⬜ Task 2 — Guided Access

**Guided Access is not set up**, so a stray swipe can drop you out of the scene mid-set.
⚠️ **Five minutes on the phone, and it is exactly the venue failure this plan exists to prevent.** It
has survived three counts because it is not code.

⛔ **DO IT BEFORE TASK 1, NOT ALONGSIDE IT.** ⚠️ **This task is independent of everything else in the
repo** — no rig session, no AP, no 5.1, no device even powered. Five minutes whenever. And done
first, **task 1's set becomes its test too**: an hour with the phone as the only display is exactly
the condition a stray swipe would show up in. Done afterwards, that evidence is lost.

Record it on [ref/device/phone.md](ref/device/phone.md) and strike the ⬜ in its `Open`.

---

## Where this sits in the order

⚠️ **Run [plan-v03.5.1.md](plan-v03.5.1.md) before this plan's rig session, not after.** 5.1 edits
`g_oled.pd` and `u_net.pd`, and `test/runner/steps.py`'s `DEPS` table stales every bench verdict that
depends on them — display, midi, nanokontrol and phone. ⛔ **A rig session run first would be
wasted**, because those verdicts would go stale again the moment 5.1 landed.

**So the one rig session runs in this order**, because the bench runner needs a network task 1 takes
away:

1. `./test/run.sh --benches`, clearing the whole stale backlog at once.
   ⚠️ **Afterwards read `test/results/latest.json`** rather than asking Brendan to retype failures.
2. **Then** switch over and run task 1.

---

## Verification

```sh
python3 test/gate/docs-check.py -v
```

⚠️ **`./test/run.sh` is not part of this plan's loop** — nothing here changes a `.pd`.

Then, and this is the real test:

**A full set's duration, with the phone as the only display, and no laptop in the room.**

During it, confirm: the link stays up; the phone repopulates within a few seconds of being
backgrounded and returned; and ⚠️ **the instrument keeps playing identically when the phone is
switched off entirely.**

⚠️ **Prove the probe before believing the silence.** ⛔ **And before calling a hardware symptom an
instrument fault, check the patch comments, the `ref/` page and the gates first** — `grep ref/` for
the literal error string, because symptoms are as greppable as `item NNN`.

---

## Done means

1. **Item 45 is measured over a real set** and struck from [ref/wifi.md](ref/wifi.md)'s `Open`.
2. **Guided Access is on**, and the ⬜ on [ref/device/phone.md](ref/device/phone.md) is struck.
3. **This file is deleted**, and ⛔ **nothing on it is copied anywhere except `ref/`.**

⛔ **This plan does not hand its open items to [plan-v04.md](plan-v04.md).**
