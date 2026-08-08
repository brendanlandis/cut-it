# Plan v0.3.0 — the measurement session, and the shipped bugs

**One session with the whole rig powered closes ten open items, takes three decisions, and fixes the
one bug in this batch that bites on every boot.** It runs **first** of the six v0.3.x plans, because
two of its measurements are inputs that [plan-v03.4.md](plan-v03.4.md) cannot be designed without.

`plan-v04.md` §6 already says to batch hardware measurements the next time the rig is out. This is
that batch.

---

## ⚠️ Constraints that bind everything below

- **Pd vanilla 0.49, permanently.** The Organelle 1 runs OS 4.0 and that is the end of the line for
  this hardware. Do not suggest any object newer than 0.49.
- ⛔ **Never open or save an Organelle-bound patch in plugdata.** It is built on Pd 0.55+ and
  rewrites `.pd` files into a format 0.49 cannot parse. This has already happened once here.
- **Vanilla objects only** — the Organelle ships neither ELSE nor cyclone.
- ⛔ **Never touch git.** Reading (`log`, `show`, `diff`, `blame`) is fine. Brendan commits his own
  work; leave changes in the working tree and describe them.
- ⚠️ **Run `./test/check-all.sh` and read its `RESULT:` line before calling anything done.** Do not
  grep for it — `grep -E 'ALL|FAILED'` also matches the per-gate `--- FAILED:` lines, and a broken
  patch has been committed that way.

---

## What to read, and how much

| Document | How much | Why |
|---|---|---|
| [CLAUDE.md](CLAUDE.md) | **All of it** | The router. Hard constraints, where everything is, working notes |
| The **`pd`** skill | ⛔ **Invoked, not read** | You are editing shipped Pd |
| The **`docs`** skill | ⛔ **Invoked, not read** | Every measurement below lands on a `ref/` page |
| [plan-v04.md](plan-v04.md) | §3 and §7 in full | What is unresolved, and the seven ways this project has been wrong before |
| [ref/conventions.md](ref/conventions.md) | The rules table, then only the sections it links | `C-1`…`C-14`, cited by ID from patch comments |
| `git log` | **Grep it, never read it** | Git is the journal. `item NNN` is a fact ID — grep resolves it |
| [plan-v04.md](plan-v04.md) | §3 *Parameter pickup* and *Which control should raise panic*, in full | Both are diagnosed down to the measurement. Do not re-derive them |
| [ref/device/organelle.md](ref/device/organelle.md) | The **Saving** section in full, then the OLED facts | ⛔ `knobs.txt` is four saved knob **positions**, and the saved file beats the physical knob. That is the pickup bug's mechanism |
| `Cut It/u_map.pd` | **All of it, comments included** | Where pickup lands. Its comments hold the item-234 postmortem |
| `Cut It/m_organelle.pd` | All 44 lines | Where knob values enter. `[change -1]` on every knob is load-bearing |
| [ref/rig.md](ref/rig.md) | **All of it** — power, cabling, both audio diagrams | Two decisions are about cables; one measurement is about brownouts |
| [ref/device/sp404.md](ref/device/sp404.md) | The CC table and `Facts` | The unexercised CC map, and the pre-set checklist you are writing |
| [ref/device/launchpad.md](ref/device/launchpad.md) | Its `Open` section, items 77 and 100 | Two measurements, one of which plan v0.3.4 needs |
| [ref/device-os.md](ref/device-os.md) | The three CPU-measurement facts only | Item 134's unexplained readings |
| `tools/stage-patches/Inquiry Probe/` | **Both halves, before running it** | ✅ **Built 2026-08-08.** The probe for the three questions below. Its script creates the nanoKONTROL output link, which had never existed anywhere in this project |
| `tools/lp-monitor.pd`, `tools/lp-step0.pd` | **Load them; do not read them** | ⚠️ Kept in the cleanup precisely as the re-check for a session like this. ✅ `lp-monitor` was repaired 2026-08-08 — see below |

**Do not read** anything under `test/`, `ref/module/display.md`, `ref/module/state.md`,
`ref/module/map.md`, or `Cut It/g_oled.pd`. None of it bears on this plan, and `ref/` is ~5,300 lines
— reading it all is the failure mode, not the diligent option.

---

## What is already true

- **The rig**: Organelle 1 (brains, clock master), SP-404MK2 (sample store and audio front end),
  nanoKONTROL, Launchpad Pro MK3, Volca FM. Cabling and power are on [ref/rig.md](ref/rig.md).
- **Pd input slot *n* carries MIDI channels `(n-1)*16+1` upward.** Launchpad 1–16, nanoKONTROL 17–32,
  SP-404 33–48, USB Uno → Volca 49–64. The channel number *is* the port.
- **mother pushes `knobs.txt` at boot**, and item 234 is fixed — the restored knob position only
  becomes a tempo once `u_map` has read its table and has a mode key.
- ⛔ **`adc~` and `dac~` appear nowhere in this patch and must not.** mother owns both.

---

## Phase 1 — the measurements

Run them in one sitting with everything powered, because item 5/95 *is* everything powered at once
and the rest are cheap once the rig is out.

⛔ **Record each result on its `ref/` page and strike its ⬜ in the same pass.** A measurement whose
number never reaches a page has to be taken again. New facts take the next free item number — grep
first, and never reuse one.

### The two that plan v0.3.4 is blocked on

⚠️ **Answer these before anything in [plan-v03.4.md](plan-v03.4.md) is designed.** They decide
whether three of the five devices get active polling or only passive last-heard detection.

| # | Question | How |
|---|---|---|
| 1 | **Does the nanoKONTROL answer a universal device inquiry** (`F0 7E 7F 06 01 F7`)? | `Inquiry Probe`, phase 2. This is a **new** open item — nobody has asked it |
| 2 | **Does the SP-404MK2 answer one?** | `Inquiry Probe`, phase 3. 📄 Its chart marks SysEx `x` both ways, so a **no** confirms documentation |
| 3 | **Does the Launchpad announce a mode change made by hand in Live Mode?** Item 100 | `lp-monitor.pd`, watching its new `SYSEX` print |

⚠️ **Prove the probe before believing the silence.** A null result is worthless until the channel is
proven — the probe asks the Launchpad **first**, which is known to answer in either mode, and only
then asks the other two. **If phase 1 produces no bytes, the run tells you nothing about phases 2
and 3.**

✅ **Both tools were built or repaired on 2026-08-08**, because neither existed in a usable form:

- **`tools/stage-patches/Inquiry Probe/`** — a menu patch that wires itself through `[shell]`, asks
  one device per phase four seconds apart, packs the phase number alongside every received byte, and
  writes `/sdcard/inquiry-probe.log`. ⛔ **Its script creates a `Pure Data:5 → nanoKONTROL` link that
  has never existed anywhere in this project** — Cut It's `wire.sh` wires an input from the nano and
  no output to it, so the nano has never been sent a byte.
- **`tools/lp-monitor.pd`** — it could not answer item 100 as written: **no `[sysexin]`**, so a reply
  or an announcement was discarded; **no `[ctlin]`**, so the whole function ring was invisible; and
  its Live Mode escape was a click-only message box, which is useless on a device running `-nogui`.
  All three are fixed, and the escape now fires from a datagram to port 9996.

⛔ **Run the probe from the menu, not over SSH.** Loading it costs no `killall pd`, which strands the
Launchpad in Programmer Mode every time.

```sh
scp -r "tools/stage-patches/Inquiry Probe" 'root@organelle.local:/sdcard/Patches/! debug/'
ssh root@organelle.local "oscsend localhost 4001 /reloadNoRemount i 1"
ssh root@organelle.local "oscsend localhost 4001 /loadPatch s '! debug/Inquiry Probe'"
# ... wait ~20 s, then read it back
scp root@organelle.local:/sdcard/inquiry-probe.log .
```

### The rest

| Item | Question | Lands on |
|---|---|---|
| 5, 95 | **Brownouts with the full rig powered at once.** Partially closed by item 211; never run with every box live simultaneously | [ref/rig.md](ref/rig.md) |
| 39 | **The OLED read by eye** — the three type-size layouts and the ageing. *"Is 16 px readable at arm's length"* is a judgement only the hardware can settle | [ref/module/display.md](ref/module/display.md) |
| 77 | **The Launchpad animation rate's upper and lower limits**, past which the device reverts to a default rate | [ref/device/launchpad.md](ref/device/launchpad.md) |
| — | **The SP-404 CC map beyond 16/17.** CC 7, 8, 20–27, 80–83 and Program Change 0–15 are manufacturer documentation, never exercised from Pd | [ref/device/sp404.md](ref/device/sp404.md) |
| 173 | **Whether the `imx-uart` Rx FIFO overruns and the OLED lag share a cause** | [ref/device/organelle.md](ref/device/organelle.md) |
| 134 | **The unexplained 10.2–10.5 % CPU readings** from Phase 7, against 11.7 % under controlled conditions minutes later. Re-measure, or close it as *recorded rather than rationalised* | [ref/device-os.md](ref/device-os.md) |
| — | **Whether a boot-started `wpa_supplicant` has a `ctrl_interface`.** One command: `ls /var/run/wpa_supplicant/` after a power cycle | [ref/device-os.md](ref/device-os.md) |
| — | **Whether Novation Components can disable the onboarding drive on the Launchpad itself.** Needs a computer with Components installed | [ref/device-os.md](ref/device-os.md) |

⚠️ **Wait for the whole measurement.** Three confident wrong answers in this project came from acting
on a partial result — items 182, 209, 210, and again in 225. ⚠️ And **concluding from a single
SUCCESS is the same error as concluding from a single failure**; this project forbids the second in
writing and the first still got through (item 182).

---

## Phase 2 — parameter pickup, the one shipped bug

**It fires on every boot, and knob 1 is master tempo.**

mother pushes `knobs.txt` at boot, the restored position becomes the tempo, and the physical knob is
wherever it was left — so the first touch jumps. **Measured at 443 BPM.** Nothing on the instrument
can detect it: mother reports position, not whether the position still matches the file.

✅ Seen again on a cold boot 2026-08-07 as a **57 BPM** start — `knobs.txt` has knob 1 at ≈0.096, and
`10 + 0.096 × 490` rounds to 57.

⛔ **That 57 is also the proof item 234 is fixed.** Do not "fix" the restore while fixing the jump.
The restore working is exactly what puts the patch and the hardware out of step; the two facts sit on
top of each other.

**The fix** is not in dispute: **ignore the control until its value passes *through* the stored
value, then hand it authority.**

**Where it lives: `u_map`, not `m_organelle`.** ⛔ Nothing outside an `m_` may know a knob exists —
the `m_` boundary is the one genuinely expensive thing to retrofit, and pickup is a property of a
*mapped destination*, not of a physical control. A knob mapped to nothing needs no pickup.

⚠️ **This affects every control that can be restored, not only knob 1.** Write it once in `u_map` and
it covers whatever v0.4 maps.

**Its gate belongs to [plan-v03.3.md](plan-v03.3.md)** if the ordering works out — the pickup rule is
pure message logic and is exactly what a headless `u_map` assertion can cover. Say so there rather
than leaving it untested here.

---

## Phase 3 — the three decisions, taken with hands on the rig

### Which control, if any, raises panic

Bound to a nano button in v0.3 and **withdrawn**. A bare button is too easy to brush mid-set on a
device with no console — and ⛔ `m_launchpad` wires `[r panic]` straight to the Live Mode SysEx, so
**panic hands the surface back and the watchdog stops re-asserting**, because it only re-asserts
while `want` is 1 and panic sets `want` 0. **Panic kills the grid until the patch reloads.**

Decide with the rig in front of you. *"A held combination"* and *"nothing"* are both real answers —
record whichever it is on [ref/module/map.md](ref/module/map.md) and strike the question from
`plan-v04.md` §3.

### Organelle audio back into the 404

Considered and dropped: the mixer's FX SEND as a variable-gain feedback path. **It needs no rewiring
beyond one cable.** Try it, decide, close `rig.md`'s ⬜.

### The 404 pre-set checklist

⬜ **The only routing in the rig that depends on a menu rather than a cable is on the 404** — ExtIn
monitoring, bus assignments, input FX. Write the checklist with the box in hand and put it on
[ref/rig.md](ref/rig.md).

⚠️ **When a device has a settings menu, read the menu.** The Volca's Program Change was gated behind
two adjacent, undocumented global settings; three reasoned hypotheses failed and photographs of the
menu solved it in one step (item 226). ⚠️ **And toggles are hazardous** — pressing a setting that is
already correct turns it *off*. Re-use a known-good prior result as a probe for device state.

---

## Verification

```sh
python3 test/gate/docs-check.py -v
./test/check-all.sh                    # read the RESULT: line
```

- **Every ⬜ this plan owns is struck on its own page**, and every number has an item ID that grep
  resolves. A measurement recorded only in a session note does not count as taken.
- **Pickup is verified by the shape of the fault, not by one number**: cold boot, observe the
  restored tempo on the OLED footer, touch knob 1, and confirm the value does **not** move until the
  knob passes through the restored value. Then confirm it tracks normally afterwards.
- ⚠️ **Re-check that the restore still works** after the pickup change — item 234's symptom is the
  instrument coming up at `u_tempo`'s own 120 instead of the saved tempo.

---

## Done means

1. Every ⬜ assigned to this plan is struck on its page, and the two device-inquiry answers are
   written down where [plan-v03.4.md](plan-v03.4.md) will look for them —
   [ref/device/nanokontrol.md](ref/device/nanokontrol.md) and
   [ref/device/sp404.md](ref/device/sp404.md).
2. Pickup is shipped, hardware-verified, and its behaviour is stated on
   [ref/module/map.md](ref/module/map.md).
3. The three decisions are recorded as decisions, not as open questions.
4. `plan-v04.md` §3 no longer carries *Parameter pickup*, *Which control should raise panic*, or the
   four never-run checks.
5. `CLAUDE.md`'s router table and `plan-v04.md` §2 are updated to match what is now true.
6. **This file is deleted.**

⛔ **This plan does not hand its open items to `plan-v04.md`.** Only the nine genuine v0.4 items
belong there; anything else is closed here or this plan is not done.

⛔ **Leave every change in the working tree.** Brendan commits his own work.
