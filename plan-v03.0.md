# Plan v0.3.0 — what is left that needs hands on the rig

**Everything in this plan that could be done without the hardware in front of you has been done.**
What remains is six things, and every one of them needs a person at the rig — eyes on a screen, ears
on a speaker, fingers on a menu, or a cable moved.

⛔ **This file is now a checklist, not a design document.** The reasoning behind each item lives on
its `ref/` page; what is here is *what to do* and *what counts as done*. The history — parameter
pickup, the device inquiries, the panic decision, items 173, 134, 5 and 95 — is in `git log`, and
every fact it produced is on a page.

⚠️ **It is deliberately not merged into `plan-v04.md`.** Only the genuine v0.4 items belong there.
These are a **session**, and they stay together because they are done together.

---

## ⚠️ Constraints

- **Pd vanilla 0.49, permanently.** The Organelle 1 runs OS 4.0 and that is the end of the line for
  this hardware.
- ⛔ **Never open or save an Organelle-bound patch in plugdata.** It rewrites `.pd` into a format
  0.49 cannot parse. This has already happened once here.
- ⚠️ **Run `./test/check-all.sh` and read its `RESULT:` line** before calling anything done. Do not
  grep for it — `grep -E 'ALL|FAILED'` also matches the per-gate `--- FAILED:` lines.
- ⛔ **Record each result on its `ref/` page and strike its ⬜ in the same pass.** A measurement whose
  number never reaches a page has to be taken again. New facts take the next free item number — grep
  first, and never reuse one.

---

## What to read

**Not much.** Each item below names its own page; read that one and nothing else.

| Document | How much |
|---|---|
| [CLAUDE.md](CLAUDE.md) | **All of it** — the router, the constraints, the working notes |
| The **`docs`** skill | ⛔ **Invoked, not read.** Every measurement lands on a `ref/` page |
| [ref/rig.md](ref/rig.md) | Power, cabling and both audio diagrams — for the two cable decisions |

---

## ⚠️ Before anything else — is the Launchpad in the right socket

⛔ **It is fussy about which socket, and the patch cannot tell you.** A half-enumerated Launchpad
answers `lsusb` but never gets an ALSA port, so from inside Cut It it is identical to one that was
never plugged in — and it would make item 77 below look like a device fault.

**Put it in the bottommost port, the one with the lock icon.** That socket is on the hub's Realtek
controller and works; at least one socket on the Generic controller produces
`can't set config #1, error -32`. Item 256 on [ref/rig.md](ref/rig.md).

```sh
ssh root@organelle.local 'aconnect -l | grep -i launchpad'   # an ALSA client means it really came up
```

⚠️ **Do not count hubs in `lsusb -t`.** There is **one** physical hub; it contains three controllers
and the SP-404 contains another, so the tree looks four deep and is not.

---

## The six

| # | Do | Needs | Lands on |
|---|---|---|---|
| 1 | **Run `Anim Probe`** — the Launchpad animation limits, item 77 | eyes | [ref/device/launchpad.md](ref/device/launchpad.md) |
| 2 | **Read the OLED by eye** — item 39 | eyes | [ref/module/display.md](ref/module/display.md) |
| 3 | **Exercise the SP-404 CC map** beyond 16/17 | the rig | [ref/device/sp404.md](ref/device/sp404.md) |
| 4 | **Write the 404 pre-set checklist** | the box in hand | [ref/rig.md](ref/rig.md) |
| 5 | **Try Organelle audio back into the 404** | one cable | [ref/rig.md](ref/rig.md) |
| 6 | **The Launchpad onboarding drive** — can Components disable it | a Mac, and a firmware update | [ref/device-os.md](ref/device-os.md) |

### 1. Item 77 — run `tools/stage-patches/Anim Probe/`

**Nothing in Cut It exercises the animation channels** — `g_grid` lights every pad *static*, on
channel 1 — which is why this needed a probe of its own. ✅ Built and proved on the Mac 2026-08-08.

```sh
scp -r "tools/stage-patches/Anim Probe" 'root@organelle.local:/sdcard/Patches/! debug/'
ssh root@organelle.local "oscsend localhost 4001 /reloadNoRemount i 1"
ssh root@organelle.local "oscsend localhost 4001 /loadPatch s '! debug/Anim Probe'"
# knob 1 sweeps 5-1000 BPM. aux marks + restarts. Then:
scp root@organelle.local:/sdcard/anim-probe.log .
```

⛔ **A ruler pad sits beside each animated one, and that is the whole method.** Pads 43 and 47 are
blinked *by the patch*; 44 and 48 are flashed and pulsed *by the device* at the same two rates. While
it tracks, each pair holds its relative phase; the moment it stops, one laps the other.

⛔ **The OLED's `act` line is the probe checking itself.** If `act` stops following `req`, the limit
you just found is **Pd's, not the Launchpad's**. ⚠️ The Mac held 1000 BPM with no audio running; the
device resolves `metro` against 1.45 ms DSP blocks, so expect a lower ceiling and read `act` first.

⛔ **120 BPM is the one tempo this cannot measure** — 📄 the documented fallback *is* 120, so there a
tracking device and a reverted one look identical. Judge from well away and sweep **toward** each
limit.

**Done means:** an upper and a lower BPM on `launchpad.md`, each with `act` recorded alongside, and
a note on whether a Start makes the rate dip before settling.

### 2. Item 39 — the OLED read by eye

The geometry is already verified through `oscOut` on the Mac. What cannot be: *"is 16 px readable at
arm's length"*, across the three type-size layouts, and whether the panel has aged.

**Done means:** a judgement per layout on `display.md`, and a note on ageing. ⚠️ A `⬜` that says
*"looks fine"* with no viewing distance is not an answer.

### 3. The SP-404 CC map beyond 16/17

📄 CC 7, 8, 20–27, 80–83 and Program Change 0–15 are **manufacturer documentation, never exercised
from Pd**. ⛔ And the 404's chart is now known to be wrong in at least one place — item 249 caught it
claiming SysEx `x` in both directions when the device answers a device inquiry. **Treat every
unexercised row as unverified**, not as fact.

**Done means:** each row on `sp404.md` moves to `verified` or gets a ⬜ saying what it actually did.

### 4. The 404 pre-set checklist

⬜ **The only routing in the rig that depends on a menu rather than a cable is on the 404** — ExtIn
monitoring, bus assignments, input FX.

⚠️ **When a device has a settings menu, read the menu.** The Volca's Program Change was gated behind
two adjacent undocumented globals; three reasoned hypotheses failed and photographs of the menu
solved it in one step (item 226). ⚠️ **And toggles are hazardous** — pressing a setting that is
already correct turns it *off*. Re-use a known-good prior result as a probe for device state.

**Done means:** an ordered checklist on `rig.md` that someone can run at a venue without thinking.

### 5. Organelle audio back into the 404

Considered and dropped once: the mixer's **FX SEND** as a variable-gain feedback path. **It needs no
rewiring beyond one cable.** Try it, decide, and close `rig.md`'s ⬜ — *"tried it, it howls"* is a
perfectly good answer and closes the item just as well as a yes.

### 6. The Launchpad onboarding drive

⬜ Whether Novation Components can disable it on the device itself. ⚠️ **It costs more than "a
computer with Components"** — Components will not talk to the unit without a firmware update first,
and this is the Launchpad the whole rig depends on. Details on
[ref/device-os.md](ref/device-os.md). **Declining is a legitimate outcome**; record it as one.

---

## Verification

```sh
python3 test/gate/docs-check.py -v
./test/check-all.sh                    # read the RESULT: line
```

- **Every ⬜ this plan owns is struck on its own page**, and every number has an item ID that grep
  resolves. A measurement recorded only in a session note does not count as taken.
- ⚠️ **Wait for the whole measurement.** Confident wrong answers in this project came from acting on
  a partial result — items 182, 209, 210, 225. ⚠️ And **concluding from a single SUCCESS is the same
  error as concluding from a single failure**; this project forbids the second in writing and the
  first still got through (item 182).

## Done means

1. All six above are answered on their pages, or explicitly declined with the reason recorded.
2. `plan-v04.md` §3 no longer carries item 39.
3. **This file is deleted.**
