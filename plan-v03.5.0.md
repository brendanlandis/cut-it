# Plan v0.3.5.0 — the venue network

**At a venue there is no house wifi**, so the phone — the only thing in the rig with a real screen —
is reachable only if the Organelle hosts the network itself. **This plan is almost entirely not
code**: a router, a front panel, a phone setting, and one measurement that needs a real set's
duration to mean anything.

⛔ **EVERY FACT ABOUT WIFI LIVES ON [ref/wifi.md](ref/wifi.md), NOT HERE.** The venue sequence, the
AP mechanics, the roam fault, the evidence ledger, the two attacks and the stopping rule are all on
that page, deliberately — **so they outlive this file, which is deleted when the work lands.**
⚠️ **Do not copy any of it back into this plan.** What belongs here is only what is still OPEN and
who does it.

✅ **The hard part was already built by the vendor.** `Start AP` is in the Organelle's own System
menu and the venue sequence is verified end to end. ⛔ **There is no boot-time service to write** —
Brendan's decision, 2026-08-11: neither network connects automatically and a couple of clicks each is
fine. **Nothing here should try to change that.**

**Two sibling plans came out of the same batch** — [plan-v03.5.1.md](plan-v03.5.1.md), diagnostics
inside the instrument, and [plan-v03.5.2.md](plan-v03.5.2.md), the standalone debug patch. They are
independent of this one. ⚠️ **But run 5.1 first** — see *Where this sits in the order*.

---

## ⚠️ Constraints that bind this plan

- ⚠️ **Bringing the AP up kills the house link**, the ssh session and every Mac-side tool.
  ⛔ **Stage the session first** — the checklist is on [ref/wifi.md](ref/wifi.md) under *The
  Organelle as its own access point*.
- ⛔ **Never `pgrep -f wifi-watch`** — item 163, bitten three times.
- ⚠️ **The `critterandguitari/Organelle_OS` repo targets the M and S2.** Its paths are wrong here.
- **Commit as you go.** ⛔ **Brendan is the sole author: no `Co-Authored-By` trailer and no agent
  byline.**
- ⚠️ **Nothing in this plan changes a `.pd`**, so `./test/run.sh` is not part of its loop —
  `python3 test/gate/docs-check.py -v` is.

---

## What to read, and how much

| Document | How much | Why |
|---|---|---|
| [CLAUDE.md](CLAUDE.md) | **All of it** | The router |
| The **`docs`** skill | ⛔ **Invoked, not read** | Every deliverable here is a `ref/` edit |
| [ref/wifi.md](ref/wifi.md) | **All of it** | ⛔ **This is the subject matter.** Everything this plan would otherwise restate, plus *If it recurs — what to try, and when to stop*, which holds the two attacks and the binding stopping rule |
| [ref/device/phone.md](ref/device/phone.md) | *The network*, *Traps*, `Open` | Airplane mode, and the Guided Access item Phase C closes |
| `git log` | **Grep it, never read it** | Git is the journal |

**Do not read** any gate, `test/runner/`, or any `ref/module/` page. Nothing here touches them.

---

## Phase A — the AP is the performance network

**The house wifi stays the development-time convenience. The AP is what the rig runs on when it
matters.** ⛔ **There is nothing to build.**

### ✅ A1 — the venue sequence is the operating procedure. Done 2026-08-12

On [ref/wifi.md](ref/wifi.md). It states that neither network connects automatically and that this is
a choice rather than a gap, that **no boot-time service should be added**, and it carries the two
consequences that read as faults.

### ⬜ A2 — item 45, AP link quality over a set-length window

**The one thing nothing has ever measured**, and ⚠️ it *"needs an actual set's duration to mean
anything"* — so this plan's acceptance test closes it by construction, but **only if the test is
actually run.**

⚠️ **This does NOT wait on Phase B.** It rides on the AP rather than the house network, so the pause
below does not touch it.

**Brendan runs it and gives the verdict.** Stage the session per [ref/wifi.md](ref/wifi.md) first.
Record the result there and strike item 45 from its `Open`.

---

## Phase B — the house fault

## ⏸ PAUSED 2026-08-12. Do not start B1 without asking.

**Brendan's call: the Organelle has been behaving, so this waits a couple of weeks and comes back
only if it becomes a problem again.** ⚠️ **That is this repo's own standing rule rather than a
departure from it.**

⛔ **The pause is NOT the stopping rule being invoked.** Item 81 is **parked, not closed** — no
configuration change has been tried, so neither outcome in *Done means* #3 has happened yet. **Do not
close it as won't-fix on the strength of a quiet fortnight.**

**When it resumes:** ⛔ **read [ref/wifi.md](ref/wifi.md)'s *If it recurs* section, which holds the
two attacks, the constraint that rules out per-band separation, the verification recipe and the
stopping rule.** The baseline to resume from is items 298, 299 and 300 there. ⚠️ **Re-take item 300
first** — it is a scan cache and will be stale.

**Brendan does the router configuration; this plan records the result.**

⚠️ **What the pause costs:** this plan cannot reach *Done means* and be deleted while item 81 is
open, and [plan-v03.5.2.md](plan-v03.5.2.md) is written as **the last of the three**. If 5.2 becomes
ready first, either resolve item 81 or move the closing chore — **do not let 5.2 land silently out of
order.**

---

## ⬜ Phase C — Guided Access

**Guided Access is not set up**, so a stray swipe can drop you out of the scene mid-set.
⚠️ **Five minutes on the phone, and it is exactly the venue failure this plan exists to prevent.** It
has survived three counts because it is not code.

**Brendan does it**, ideally in the same session as A2. Record it on
[ref/device/phone.md](ref/device/phone.md) and strike the ⬜ in its `Open`.

---

## Where this sits in the order

⚠️ **Run [plan-v03.5.1.md](plan-v03.5.1.md) before this plan's rig session, not after.** 5.1 edits
`g_oled.pd` and `u_net.pd`, and `test/runner/steps.py`'s `DEPS` table stales every bench verdict that
depends on them — display, midi, nanokontrol and phone. ⛔ **A rig session run first would be
wasted**, because those verdicts would go stale again the moment 5.1 landed.

**So the one rig session runs in this order**, because the bench runner needs a network the AP takes
away:

1. **On house wifi:** `./test/run.sh --benches`, clearing the whole stale backlog at once.
   ⚠️ **Afterwards read `test/results/latest.json`** rather than asking Brendan to retype failures.
2. **Then switch to the AP** and run A2.

---

## Verification

```sh
python3 test/gate/docs-check.py -v
```

⚠️ **`./test/run.sh` is not part of this plan's loop** — nothing here changes a `.pd`.

Then, and this is the real test:

**A full set's duration, on the AP, with the phone as the only display, and no laptop in the room.**

During it, confirm: the AP stays up; the phone repopulates within a few seconds of being backgrounded
and returned; and ⚠️ **the instrument keeps playing identically when the phone is switched off
entirely.**

⚠️ **Prove the probe before believing the silence.** ⛔ **And before calling a hardware symptom an
instrument fault, check the patch comments, the `ref/` page and the gates first** — `grep ref/` for
the literal error string, because symptoms are as greppable as `item NNN`.

---

## Done means

1. ✅ The venue sequence is the stated operating procedure on [ref/wifi.md](ref/wifi.md). **Done
   2026-08-12.**
2. **Item 45 is measured over a real set** and struck from [ref/wifi.md](ref/wifi.md)'s `Open`.
3. The house fault is either fixed by configuration or **closed as won't-fix under the stopping
   rule** — not left open. ⏸ **Paused, not started.**
4. **Guided Access is on**, and the ⬜ on [ref/device/phone.md](ref/device/phone.md) is struck.
5. [plan-v04.md](plan-v04.md) §3's wifi index is **gone**, not merely shortened. ⚠️ **It cannot go
   until items 45 and 81 are closed** — the doc gate requires every ⬜ on a `ref/` page to link to
   §3, so emptying it early would leave [ref/wifi.md](ref/wifi.md)'s `Open` pointing at nothing.
   ✅ Its restated account and item 45's duplicate row in *Checks that were never run* went on
   2026-08-12; what is left is the four-row table itself.
6. **This file is deleted**, and ⛔ **nothing on it is copied anywhere except `ref/`.**

⛔ **This plan does not hand its open items to [plan-v04.md](plan-v04.md).**
