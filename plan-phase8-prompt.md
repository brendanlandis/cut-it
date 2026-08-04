# Briefing for whoever picks up Phase 8

Copy everything below the line and send it as the opening message.

---

I'm working on **Cut It**, a cut-up/harsh-noise instrument in Pure Data for the **original
Critter & Guitari Organelle** (Organelle 1 — not M/S/S2). Phases 0–7 are done and verified on
hardware. We're starting **Phase 8: state and presets (`u_state`)** — the last phase of v0.2.

Before doing anything, read these, in this order and at this depth:

**READ WORD-FOR-WORD (all of it):**

1. `CLAUDE.md` — project instructions. Non-negotiable constraints live here.
2. `plan-phase8.md` — the Phase 8 execution plan. This is your task. It names a design decision
   that must be settled with me before any code, and a Step 0 of six measurements.
3. `ref-conventions.md` — naming, `$0`, `[trigger]` discipline, the global-send allowlist, the
   banned-constructs list, and the dev workflow. **Most of the existing patch predates these rules
   and does not demonstrate them, so you cannot infer them from the code.** Its *State and
   persistence* section is the mechanism Phase 8 is built on, and its *How a phase runs* section is
   the shape every phase has used.

**READ CAREFULLY, BUT ONLY THESE SECTIONS:**

4. `plan-v02.md` → *Phase 8* and *Open questions*. The Save New `!` bug is already diagnosed there
   — do not rediscover it. Skim the rest.
5. `ref-build-log.md` → *Phase 7* and *What every phase had in common* (the last two sections).
   These are the process lessons that matter most, and Phase 7's are unusually rich: a measurement
   generalised past what it measured, a gate whose assertions were proxies, and a bug found only
   because the Mac bench was run *after* the device one. Skim the earlier phases, but do read
   every section headed with a correction.
6. `ref-hardware.md` → *The device itself* and *Measuring the running patch*. You need the paths,
   the `mother`/Pd launch line, and the current CPU/UDP baselines.

**SKIM (know what's in them, look things up as needed):**

7. `tools/README.md` — what each tool proves and how to run it. You will need `bench-gen.py`,
   `bench-verify.py`, `pd-layout-check.py`, `go.sh` and `phase6-cpu.sh`.
8. `ref-display.md`, `ref-midi.md`, `ref-software.md` — reference. Search rather than read.

**SKIP unless you need a specific number:**

9. `plan-tests.md` — 2000+ lines of ordered hardware checks with every measured result. It is a
   lookup table, not a document to read. Phase 8's checks get appended, numbered **after 134**.
10. `! v0.1 plans/` — superseded, kept for musical intent only. Not code to lift.

**The constraints that will bite you if you skip them:**

- **Pd 0.49 vanilla, permanently.** No objects newer than 0.49. No ELSE, no cyclone.
- **Never save an Organelle-bound patch from plugdata** — it rewrites the file format and 0.49
  cannot parse the result. Edit with vanilla Pd 0.49.
- **Never insert or delete a box mid-list in a `.pd` file.** `#X connect` indexes boxes by file
  position, so every later cord silently rewires. Append before the connect block.
  `python3 tools/pd-layout-check.py <file>` catches it. It has bitten five times.
- **Git is read-only.** Never commit, stage, push, checkout, or `git rm` — even if a plan says to.
  Leave changes in the working tree and describe them. Brendan commits his own work.
- **Before any bulk delete or overwrite, print the count, a sample, and the evidence — then ask.**

**How this project works, and it is the whole method:**

- **Measure on the device; do not infer from documentation.** Every phase's most valuable output
  has been a correction to something a plan asserted. Claims are marked ✅ verified / 📄 documented
  / ⬜ unknown — **do not treat 📄 or ⬜ as settled.**
- ⚠️ **Do not generalise a measurement past what it measured.** Phase 7 measured a UDP failure on
  loopback and wrote it up as true of a remote host; and measured broadcast *delivery*, concluded
  broadcast was free, and missed 819 ms of added latency that a person noticed in seconds.
- ⚠️ **A green bench does not mean a phase is done, and a bench that lies is worse than none.**
  Phase 6 passed 25/25 on the Mac twice and shipped three bugs. Four of Phase 6's first five
  failures were in the bench, not the patch.
- **Run the bench on the Mac FIRST, then the device.** Phase 7 reversed this and the Mac run then
  found two faults the device pass had gone straight past.
- **Off-device development is the default.** Open `Cut It/main-dev.pd` in Pd 0.49 and the whole
  instrument is there with a simulated front panel.
- **`./deploy.sh` does the whole device loop** and refuses to deploy on any syntax-check output.
- **There IS a console on the device** — launch the patch by hand over SSH. See `ref-conventions.md`
  → *There IS a console*. ⚠️ That workflow uses `killall pd`, which strands the Launchpad in
  Programmer Mode; run `./tools/lp-live.sh` afterwards.

**Current state of the rig, so you don't misread a symptom:**

- ⚠️ **The Organelle intermittently loses its IPv4 lease** (items 81 and 133). It stays *associated*
  and **SSH keeps working over IPv6**, so a login proves nothing. Check
  `ip addr show wlan0 | grep "inet "`. A restart fixes it first try. `/sdcard/wifi-watch.sh` may be
  running and logging this to `/sdcard/wifi-watch.log` — leave it alone.
- **`u_net` sends to the phone continuously.** If PdParty is shut it retries every 5 s and logs one
  `net-link-down`; that is correct behaviour, not a fault.
- ⚠️ **Two instruments will fight over one phone.** Running `main-dev.pd` on the Mac while the
  Organelle also runs Cut It makes the phone display flutter between two values. Stop one.
- **`/tmp` is wiped on reboot**, and **`/tmp/patch` does not exist until mother has loaded the patch
  once** — launching by hand before that leaves `wire.sh` unrun and the MIDI wiring silently absent.

Start by reading the docs above, then tell me your plan for Step 0 — and the design decision in
`plan-phase8.md` needs settling with me before any Pd is written.
