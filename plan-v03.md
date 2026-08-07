# Cut It v0.3 — the blank slate

**This is the only plan document in the project, and it is written to be handed to an agent
cold.** Read this file first and in full. It tells you what the project is, which other documents
to read and how much of each, what is already true, and exactly what is left to do.

---

## 1. What this project is

**Cut It is a cut-up / harsh-noise instrument patch for the original Critter & Guitari Organelle
(Organelle 1 — *not* the M, S or S2), written in Pure Data.** The Organelle is the brains and the
clock master; an SP-404MK2 is the sample store and audio front end; a nanoKONTROL, a Launchpad Pro
MK3 and a Korg Volca FM complete the rig.

**⛔ Read [CLAUDE.md](CLAUDE.md) before writing a single line of Pd.** It carries hard constraints
that are not negotiable and not obvious — chiefly that the target is **Pd vanilla 0.49 permanently**
(the hardware cannot be upgraded), and that **opening any device-bound patch in plugdata corrupts
it** for Pd 0.49.

### Where the version numbers are

| | |
|---|---|
| **v0.2** | ✅ Complete and hardware-verified. Sixteen abstractions, four display surfaces, three headless gates, six benches |
| **v0.3** | ✅ **Complete and hardware-verified.** The *blank slate* — every device addressable, every control assignable. Eighteen abstractions, four headless gates, seven benches |
| **v0.4** | ⬅ **Next.** The instrument: four filter stages, the drum mode, the sampler, compose-time capture. ⚠️ **But the documentation refactor comes first — see §10** |

⚠️ **v0.3 WAS NOT THE SOUND, AND THIS DOCUMENT ONCE SAID IT WAS.** An earlier version planned the
filter stages here. The goal was to finish the infrastructure so the *next* phase can say
***"in Mode A, moving this fader does X"*** and have somewhere to put the answer. **It can now**:
that sentence is one row of `Cut It/cut-it-map.txt`.

---

## 2. What to read, and how much

**Do not read everything.** The reference docs total ~4000 lines. Read in this order:

| Document | How much | Why |
|---|---|---|
| **[CLAUDE.md](CLAUDE.md)** | **All of it (~280 lines)** | Hard constraints, the file layout, working notes. Non-optional |
| **[ref-conventions.md](ref-conventions.md)** | **"The rules, in one screen" table, then the sections it links** | How the Pd is written. `$0`, the global allowlist, `[trigger]` discipline, the four `route` traps, the banned list. **Read before writing Pd** |
| **[ref-midi.md](ref-midi.md)** | **The addressing model + the section for the device you are touching** | Every CC, note and SysEx each device accepts. Skip the devices you are not working on |
| **[ref-software.md](ref-software.md)** | **Architecture + Load-bearing decisions (~100 lines)** | What the patch is made of and why. The rest is v0.4 design |
| **[ref-hardware.md](ref-hardware.md)** | **"The device itself" + whatever rig section applies** | SSH, paths, how Pd launches, how to measure the running patch |
| **[ref-build-log.md](ref-build-log.md)** | **The corrections in each phase section** | ⚠️ **Every phase produced at least one correction to something a plan asserted.** This is the highest-value-per-line document in the repo |
| **[ref-display.md](ref-display.md)** | Only if touching a display surface | OLED, Launchpad LEDs, aux LED, phone |
| **[plan-tests.md](plan-tests.md)** | **Never read start to finish (~3500 lines).** Grep for the item number you were cited | The evidence ledger. Items are cited bare as "item 133" across every document |

### How this project works

- **⛔ Never touch git.** Brendan commits his own work. Read-only operations are fine.
- **Off-device development is the default.** Open `Cut It/main-dev.pd` in Pd 0.49 on the Mac and the
  whole instrument is there, front panel included.
- **`./deploy.sh` does the whole loop** — syntax check, scp, reload, load. It **gates on output, not
  exit status**, because Pd exits 0 even when objects fail to create.
- **`./tools/check-all.sh` runs every gate in one command.** ⚠️ **Run it before calling anything
  done.** Phase 8 came within one step of shipping without re-running the gates of the phases
  beneath it.
- **A phase runs in a fixed shape** — decisions table, Step 0 measurements, numbered build steps
  each ending with both gates, a generated bench, verification separating Mac from device, then a
  landing checklist. See [ref-conventions.md](ref-conventions.md) → *How a phase runs*.

---

## 3. v0.3 is COMPLETE — what it built, and what it corrected

**All three gaps that defined v0.3 are closed, and the phase ran on the hardware.**

| Gap | |
|---|---|
| The SP-404 has no `m_` layer | **CLOSED.** `m_404`, the first bidirectional device layer. 160 pads, one shared table both directions, a rate limit that drops rather than queues |
| The Volca has no `m_` layer | **CLOSED.** `m_volca` wired in on one selector-prefixed cord |
| `u_map` cannot express a mode-dependent meaning | **CLOSED.** Table-driven with a hardcoded allowlist of destinations |

**The full account is in [ref-build-log.md](ref-build-log.md) under *Phase 9*.** Evidence is
items 228–235. What follows here is only what is still OPEN.

**Four corrections came out of building it**, and they are the part worth carrying forward:
Pd's `pgmout` is 1-based; `u_tempo`'s panic covered one bank in ten; nothing on the device could
raise panic at all; and `ref-conventions.md` asserted that `u_map` did not use a lookup table.

⚠️ **And one bug that 23 green headless checks could not see.** The instrument booted at 120 BPM
instead of the saved 57, because the map was not ready when mother pushes `knobs.txt` at boot. The
gate's own windows were timed *from the implementation detail that was wrong*, so it could only
test the patch after the race had resolved. **A person reading a number off a screen found it.**
Item 234.

---

## 4. Open questions

**The single place to look for what is unresolved.** CLAUDE.md, ref-conventions.md and ref-midi.md
all point here; the section did not exist until v0.3 and the pointers were dangling.

### The Launchpad watchdog cannot recover a device that was absent at load

**Item 235, found on hardware, and it is shipped Phase 6 code rather than anything v0.3 did.**
Power on with the Launchpad unplugged - or with a hub that does not enumerate it in time - and
plugging it in afterwards **never** restores it. Only a patch reload does.

`[r $0-armed]` gates the `[spigot]` in front of the bounded `wire.sh` recovery, and `$0-armed` is
set by exactly one thing: `[sysexin]` receiving a device-inquiry reply. So the recovery arms only
after the device has answered **at least once**, and a device that was never there never answers.
The give-up path sits downstream of the same shut spigot, so it cannot report that it gave up
either - which is why the error log was empty.

**The gap in one sentence: "lost" was built as a TRANSITION from present to absent, and
never-present is not a transition.**

**Likely a one-box change** - arm at load rather than on first reply, letting the existing
`moses 33` bound stop it after eight attempts exactly as it does now. **But it sits beside the safe
exit**, which is the one message in this patch worth more than everything around it, so it wants
its own can-it-fail test rather than being bolted onto the end of another phase.

### Which control, if any, should raise panic

Panic was briefly bound to a nano button in v0.3 and **withdrawn**. `m_launchpad` wires `[r panic]`
straight to the Live Mode SysEx - panic hands the surface back by design - and the watchdog only
re-asserts Programmer Mode while `want` is 1, which panic sets to 0. **So panic kills the grid until
the patch reloads.** A bare button is too easy to brush mid-set on a device with no console.

The capability is right and proven: `m_404` silences all ten banks when panic arrives, which
`u_tempo` never did. Only the binding is open. A deliberate gesture - a two-control combination, or
a control nothing else uses - is a v0.4 decision.

### Still unticked in plan-tests.md

Eight checks have never been run. They are **not** v0.3 work and none of them block it, but this is
where to look for them: **item 5 / 95** brownouts with the full rig powered at once, **item 39** the
OLED read by eye, **item 45** AP link quality over a set-length window, **item 81** the wifi fault
itself, and **43/44/46** struck through as answered by later work.

---

## 5. ⚠️ Constraints that bind what you build

**The four rate ceilings are in [ref-midi.md](ref-midi.md). What they bind here:**

| Constraint | Consequence |
|---|---|
| **`c_clock`'s bang outlet caps at 14.3/s** | ⛔ A dense trigger stream cannot come from `c_clock` — it needs a plain `[metro]` |
| **MIDI triggers cap at ~360–400/s** | `m_404`'s hard rate limit. Overshoot costs seconds of lag |
| **The OLED lags ~200 ms; the Launchpad does not** | Rhythmic feedback goes on the Launchpad |

✅ **The audio-domain path has no ceiling** — `c_clock` outlet 0 is raw phase as a *signal*. **The
ceilings are message-domain only.** ⚠️ If a stage converts that phase to bangs, that is the mistake.

**Other standing risks:**

- **The `m_` boundary is the one genuinely expensive thing to retrofit.** Nothing in `e_*` may know
  a nanoKONTROL exists. v0.3 is when the pressure arrives, because it is when controls start
  meaning things.
- **Timing is architectural** — audio-domain from the first line, and **nothing downstream may
  assume the global `clock` is its clock**. Cut It runs poly-tempo.
- **The DSP is the budget, not the MIDI** — DSP 6.9 points against MIDI's 0.43, measured two ways.

---

## 6. The wifi fault — background, not blocking

**Requirement, as Brendan states it: the Organelle must stop dropping wifi.** Not "recover fast" —
a dead phone display mid-set is the failure.

**Do not spend session time on this unless it recurs.** Everything actionable has shipped:

| | |
|---|---|
| ✅ **The recovery ladder works** | Two real failures, both recovered on rung 1, unattended (item 212) |
| ⛔ **Orbi firmware 2.7.6.6 did NOT fix it** | Twice in 15 hours (item 213) |
| ✅ **Channel 1 was a real win** | 14.4 → **72.2 MBit/s** at the same signal (item 221) |
| ⛔ **The trigger is untouched** | Both APs remain co-channel at −39/−41 dBm. One Orbi setting moves both mesh nodes |
| ⚠️ **Recovery takes ~132 s, not the 20 s the script claims** | ~60 s of it is diagnostics running *before* the rung that works (item 220) |

**The watcher now records what was missing** — outage duration, and a dhcpcd-pid discriminator that
separates "the incumbent daemon cannot re-acquire" from "upstream is not answering". **The next
spontaneous event answers both questions by itself.**

⛔ **The preferred-AP steer is no longer a safe fallback**: one failure happened *on* the router,
which is where the steer parks the device (item 214).

**Open, and Brendan's to do:** read the Orbi DHCP pool (⚠️ **reading is safe — only *saving* caused
outages, twice**), and check satellite backhaul health.

⚠️ **Operating the watcher:** never `pgrep -f wifi-watch` — it matches the ssh carrying it (item
163). Use the pidfile. And `wifi-report.sh --mark` goes **after** a write-up, never before.

---

## 7. Deliberately not in this phase

**Recorded so none of it is rediscovered as news.**

| | Why |
|---|---|
| **The four filter stages** — `e_chop`, `e_pitch`, `e_trem`, `e_verb` | v0.4. ⚠️ **Grain timing must be audio-domain from the first line** when they land — `phasor~` and `vline~`, never `metro`/`line~` |
| **The drum mode, compose-mode capture, the sampler** | v0.4. The `time, note, velocity, duration` format is decided and every device can now fill all four fields |
| **The mic-bleed capture guard** | v0.4, with capture. ⚠️ A live vocal bakes into any drums-channel buffer sampled while the mic is hot |
| **Items 142, 202, 210** | Step 0 measurements that gate the **v0.4 sampler**, not this phase. Batch them next time the rig is up |
| **Footswitch, nanoKONTROL scenes, a 404 pre-set checklist, Save New** | Long-standing deferrals; reasons in [ref-build-log.md](ref-build-log.md) and [ref-hardware.md](ref-hardware.md) |
| **LINE IN R-only, ground loops, 404 latency, CPU headroom** | Upgrade paths and perform-time tuning |
| **Guided Access, a dynamic mic, OLED legibility (item 39), the Launchpad onboarding drive** | Real wants, none of them this phase |
| **AP link quality over a set-length window (item 45)** | The last outstanding measurement. ⚠️ Needs the AP up, which kills the house link |

---

### Grid idioms, and what each would map to

Moved out of `ref-software.md` during the documentation refactor. **Every row below describes a
feature that does not exist yet** — the pattern launcher, the four filter quadrants, Chop Shop's
drunkenness — so it is intent rather than reference, and `ref-` states what is.

| Idiom | What it is | Use for Cut It |
|---|---|---|
| **Clip launching** (Session) | Columns = tracks, rows = scenes. Blinks when queued, solid when playing. Right column fires a whole row | **The pattern launcher.** Columns = destinations (404 drums, Volca, internal), rows = variations. Inherits the queued/playing visual convention free |
| **Drum rack** | 4×4 quadrants of velocity-sensitive trigger pads | **Four filter quadrants**, arranged right-to-left to match the signal chain. 16 pads per filter vs the 5–7 keys currently on the Organelle keyboard |
| **Isomorphic note layout** | Fixed interval per row, scale-locked | Playing the Volca — use built-in Note mode, don't rebuild |
| **Step sequencing** | Row = track, column = step | Compose-time authoring — use built-in Sequencer |
| **Column-as-fader** | Press higher = higher value. 8 steps of resolution | Coarse parameter control if the nano runs out |
| **X/Y pad** | Pad coordinates set two parameters at once | **Chop Shop's drunkenness + sputter.** A 4×4 block = 16 positions over both. Slapping a corner is a different gesture than turning two knobs |
| **Radio buttons** | A row as exclusive mode select, lit | Filter selection |
| **Pure display** | Grid as output only | Playhead position, which sample slots are filled |

**Pressure is the forgotten input.** Grain size, chop intensity, filter depth — any of these
can ride pad pressure while held. Costs no panel space and is the most expressive control on
the rig.

The README says the controls *"will take some practice and memorization."* The RGB grid is
the direct antidote to half of that: which filters are on, which of the five sample slots are
filled, which pattern is queued, where the playhead is — all visible rather than memorised.

---

## 8. ⚠️ How this project gets things wrong

**Read this before trusting your own conclusions. Every one of these cost real time.**

- **Every phase's most valuable output was a correction to something a plan asserted.** The channel
  block, `enc`'s polarity, `route`'s remainder rule, `[list split n]`, `pgrep`, the reject-outlet
  rule, the 404 pad map — none came from reading documentation and several contradict it.
- ⛔ **A reject, left, or non-matching outlet carries DATA, not a bang.** Four instances, every one
  silent. Put a `[t b]` in front of anything behind one.
- ⚠️ **Prove the probe before believing the silence.** A null result is worthless until the channel
  is proven. "No pad lit" meant "receive and transmit differ" for half an hour, until it turned out
  the 404 lights only the *selected* bank.
- ⚠️ **A measuring rig is code and gets the same scrutiny.** Phase 5 had two bugs in its own probes;
  Phase 6's bench had an assertion nothing ever drove; `phase8-assert.sh` passed a broken patch.
- ⚠️ **Wait for the whole measurement.** Three confident wrong answers in this project came from
  acting on a partial result — items 182, 209, 210, and again in item 225.
- ⚠️ **When a device has a settings menu, read the menu.** The Volca's Program Change turned out to
  be gated behind **two adjacent, undocumented global settings**. Three reasoned hypotheses failed;
  photographs of the menu solved it in one step (item 226).
- ⚠️ **Toggles are hazardous.** Pressing a setting that is already correct turns it *off*. Re-use a
  known-good prior result as a probe for device state.

---

## 9. Repo hygiene

**The root is clean.** The firmware `.wav`s, the Volca settings photographs and the stray
screenshot are all gone. Nothing is left to move.

One thing to be aware of rather than to act on: **the Volca settings photographs were the primary
evidence for item 226** and are no longer in the repo. The finding itself survives in full in
plan-tests.md — the key 9–12 table and the `PCnot`/`PCMId` trap — so nothing operational is lost.
If those photographs still exist outside the repo, `device/volca-settings/` is where they belong.

---

## 10. NEXT: the documentation refactor

**Agreed as the work that follows v0.3, and it is a real problem rather than tidying.** The design
below is settled; what is still open is listed at the end.

### 10.1 The size of it, measured

| | Lines |
|---|---|
| `plan-tests.md` | **4,131** — 249 items, append-only, and the single largest file in the project |
| `ref-` docs (six files) | ~4,550 |
| `tools/README.md` | 765 |
| `CLAUDE.md` | 313 |
| **Total prose** | **~10,300** |
| `.pd` comments (21 files, not counted above) | 446 |

That is roughly 400 lines of prose per `.pd` file. **~10,300 lines is most of a context window**, and
CLAUDE.md already tells a cold reader "do not read everything" — an admission that the volume has
outgrown its usefulness. Three facts are restated in eight files apiece (`47 + n`), seven
(`pgmout` is 1-based) and ten (the `[list split]` trap).

### 10.2 The diagnosis, and why it is structural

**Agents have written 100% of these docs.** That means restatement was never laziness — it is the
only thing a cold context can do. A session editing `ref-midi.md` has no way to know the same fact
sits in seven other files; it would have to grep for a fact it does not know exists.

⛔ **So "one home per fact" cannot be a convention that authors follow. It has to be a structure they
fall into, and a program that catches the drift.** Every part of the design below follows from that.

### 10.3 The design, settled

**Format: Markdown stays. The tables become the database.** A GitHub markdown table is already
machine-readable — it is simply not being read. Give the tables a fixed column schema and a parser
and the human-readable copy and the machine-readable copy are *the same bytes*: no build step, no
generated files, no second format, and it still diffs a row at a time. `ref-midi.md` is most of the
way there already.

Anything **Pd itself** must read stays space-separated `.txt` — `cut-it-map.txt` is the proven
pattern and Pd can parse nothing else.

| Kind of content | Home | Rule |
|---|---|---|
| Device facts code depends on | `ref-midi`, `ref-hardware`, `ref-display` | Schema'd markdown tables, checked against the patch |
| Rules and rationale | `ref-conventions` | One rule per numbered heading with a **stable ID** (`C-NN`); everything else cites the ID |
| Open work | `plan-v03` | The only plan document, as now |
| Orientation | `CLAUDE.md` | A router, not a store. Its Layout tree is ~240 of its 313 lines and duplicates each file's own header — one line per file |

**The rule that does the work:** *a fact appears once in full; everywhere else it appears as a
citation.*

### 10.4 The journals dissolve

`plan-tests.md` (4,131) and `ref-build-log.md` (981) are half the corpus and neither is ever read
start to finish. **Both dissolve into the reference docs.**

**Git is now the journal.** `phase 9: fix the boot-time tempo race -- the map was not ready when
mother pushed` is a journal entry with a timestamp, a diff and no maintenance cost; recent commit
bodies run ~36 lines. `plan-tests.md` exists because git was read-only until the commit exception.

⚠️ **But that quality begins at `dca0b04`.** Before it the log reads `docs update, bug fixes` and
`straggler issues part 1`. Git carries the journal role *forward* only — Sessions 1–17 must be
condensed by hand, and **that is the bulk of the work in this refactor.**

**Item numbers survive as fact IDs.** Item 228 stops being "the 228th thing measured" and becomes
the ID of the `pgmout` row in `ref-midi.md`. All ~180 citations across the project keep resolving by
grep, with no renumbering and no index file. New facts take new numbers from the same
never-reused sequence.

⛔ **The disposal rule — without it the `ref-` docs simply absorb 5,100 lines and nothing shrinks.**
Every paragraph of a journal goes to exactly one of four places:

| Journal material | Destination |
|---|---|
| The result | A reference table row: value, evidence class, date, item ID |
| The trap — what looked right and was not | A warning at the point of use: the `.pd` comment, or a numbered rule in `ref-conventions` |
| The method, if reusable | `ref-conventions`, or better, into the tool that performs it |
| Everything else | **Deleted.** The narrative of a session is git's job |

**The fourth row has to actually get used, or this is a move rather than a reduction.**

### 10.5 `tools/docs-check.py` — the checker

A sibling to `pd-layout-check.py`: pure stdlib, into `check-all.sh`, same discipline that any output
is a failure.

Tables are anchored by an HTML comment — invisible when rendered, greppable, self-documenting:

```markdown
<!-- check: table sp404-pads == pd-array "Cut It/m_404.pd" $0-pad -->

| Pad | Note | Evidence | Item |
|-----|------|----------|------|
| 1   | 48   | verified | 190  |
```

The script finds the comment, parses the table into pairs, parses the `#A set` line out of the
patch, and compares. About 40 lines. ⛔ **That check fails on `47 + n` at pad 5, before hardware** —
it is the cheapest thing in this plan and it catches the bug that got furthest.

The same script then does the rest of the upkeep for nothing: every `item NNN` citation resolves to
a row that exists; every fact row carries an evidence class from the allowed set; no duplicate fact
IDs. **That is what stops the docs re-inflating.**

### 10.6 The marker scheme, settled

The repo carries **1,479 markers**. They were doing more jobs than they had glyphs.

| Glyph | Meaning after the refactor | Notes |
|---|---|---|
| ✅ | **Verified on this hardware** | Kept, all ~545 of them. Only 96 of 645 sit in tables, so a table column can never replace them |
| 📄 | **Manufacturer documentation** | Kept |
| ⬜ | **Unknown / unverified** | Kept |
| ⛔ | **A trap: ignoring it breaks something SILENTLY** | Re-sorted. Was covering four jobs |
| ⚠️ | **An operational rule: never do this to the rig or the device** | Re-sorted |
| ❌ | *retired* | Table cells become `none`; the two prose bullets say "rejected" |

**Two things stop being markers:**

- ⛔ **`✅` as a completion marker is deleted — roughly 100 uses, 40 of them in headings**
  (`## Errors must reach the OLED ✅ built`). **An evidence marker never rots; a completion marker
  silently becomes false**, which is exactly how `ref-conventions.md` came to assert that `u_map`
  used no lookup table. And in this project a completion marker is nearly always a *placement*
  error: in a `ref-` doc everything described is built by definition, and in `plan-v03` "complete"
  means the section should have left the file. **Each deletion doubles as a check that the item is
  in the right file.**
- **Corrections lose their marker.** "X was recorded here and it is FALSE" mostly gets deleted once
  the false claim is gone — the *trap that produced it* survives, the retraction does not. Plain
  emphasis becomes bold.

Tables additionally gain an explicit `Evidence` column, so `docs-check.py` can assert that no fact
row is missing its class — something it can never do for prose.

### 10.7 The `.pd` comments are in scope

446 lines across 21 files, and the hardest case: **they are the only copy visible while editing in
Pd**, so a comment can never be replaced by a link.

**The rule: the warning stays inline as one imperative line; the evidence and the reasoning leave.**
`[pgmout] is 1-BASED -- see C-NN` rather than a paragraph — short enough to be obviously not the
source of truth, present enough to stop you at the box.

### 10.8 Order of work, and the three refactors next to this one

Three other cleanups are queued. **They are not part of this work, but two of them constrain its
order.**

| Refactor | Coupling |
|---|---|
| **Testing, by module instead of phase** | **Deep — it is the same job on the same axis.** The gates are named by *phase*: four `phaseN-assert.sh`, four drive-gens, `bench_steps.py`'s `STEPS3`…`STEPS9`. Phase is a *time* axis, which is what this refactor dissolves. The cost is already visible — `phase9-assert` exists partly because `phase6-assert` rewrote only `[midiout]` and would have passed vacuously over `noteout`/`ctlout`/`pgmout`. On a module axis that is **one** MIDI-emission gate, not two. **So this refactor must choose module names knowing the tests will adopt them.** |
| **Tool cleanup** | Sequencing only. `tools/README.md` is 46 KB describing ~40 files, many one-off probes from July. Rewriting it before deciding what survives means documenting things about to be deleted. ⚠️ **Leave `tools/README.md` until last.** ⛔ **And one candidate is already known to be a hazard: `tools/wire.sh` is a Phase 1 ancestor of `Cut It/wire.sh`, 59 lines behind, with no autoconnect undo and no `\|\| true`.** `ref-hardware.md` pointed at it, and `docs-check.py` cannot catch that class — the path resolves; it is simply the wrong file. **It is the only such pair in the repo** — swept every `.sh` / `.py` / `.pd` / `.txt`, and the nine `main.pd` copies are all legitimate Organelle patch folders. So this is one file to delete, not a pattern. ⬜ **And five scripts of 42 are named in NO document at all**, `tools/README.md` included: `404-contend.sh`, `404-rate.sh`, `phase8-assert.py`, `stage-patches/AP Probe/ap-probe.sh`, `stage-patches/Start AP/ap-up.sh`. **`phase8-assert.py` is LIVE** — `phase8-assert.sh` line 36 execs it — so that one is a documentation gap, not a delete candidate. The other four need a decision. `docs-check.py` cannot find these: it is mention-driven, so it proves every mention resolves and can say nothing about a file nobody mentions. |
| **Organelle cruft cleanup** | One chapter. `ref-hardware.md`'s *The device itself* (lines 355–539) describes paths the cleanup will change. ⚠️ **Do not invest there; mark it verify-after.** The rest of that file — wiring, power, gear — is independent. |

**Resulting order:** documentation refactor (every chapter except `tools/README.md` and
`ref-hardware`'s device section) → testing refactor on the taxonomy this establishes → tool cleanup
→ `tools/README.md` → Organelle cleanup → `ref-hardware`'s device section.

### 10.9 Where this stands — 2026-08-06

**Nine commits, `91c68f4`…`156ccd2`. All gates pass.** ⚠️ **Read [ref/README.md](ref/README.md)
first** — it carries the page schema, the trap form, the marker definitions and the parking rule,
and `tools/docs-check.py` enforces all of it. None of it has to be remembered; run the gate.

| | Then | Now |
|---|---|---|
| `ref-conventions.md` | 892 | **27** (a pointer stub) |
| `ref-software.md` | 455 | **33** (a pointer stub) |
| `ref-display.md` | 727 | **19** (a pointer stub) |
| `ref-midi.md` | 897 | **141** |
| `ref-hardware.md` | 697 | **406** — now only the Organelle as a COMPUTER, and verify-after |
| `ref/` pages | — | **4,092 across 16** |
| `CLAUDE.md` | 313 | 327 — **not yet the router** |
| `plan-tests.md` + `ref-build-log.md`, untouched | 5,112 | **5,112 — 78% of what is left at the root** |

⚠️ **`ref/` now has subdirectories.** `ref/device/` (six, fixed by the hardware) and
`ref/module/` (one so far — **this is what v0.4 grows**). Cross-cutting pages stay flat.
`ref/README.md` carries an index that `docs-check.py` verifies against what exists.

⚠️ **A `pd` skill exists** at `.claude/skills/pd/`. Invoke it before writing any Pd; it carries the
constraints, the C-1..C-14 rules and the hand-editing traps, and CLAUDE.md has been trimmed to match.

**Done — all six device pages, plus the conventions:**
`ref/device/sp404.md` · `ref/device/launchpad.md` · `ref/device/volca.md` · `ref/device/nanokontrol.md` · `ref/device/organelle.md` ·
`ref/device/phone.md` · `ref/conventions.md` · `ref/README.md`. Every source section replaced by a
**Moved** pointer.

`tools/docs-check.py` now runs seven checks, each proven to fail. Three of them are **anchored
tables** — a fact that exists twice in machine-readable form, parsed from both sides and compared:

| Anchor | Asserts |
|---|---|
| `pd-text "<patch>" <name>` | The table equals that `[text define]`'s contents. Reintroduce `47 + n` and it goes red **at pad 5** |
| `pd-route "<patch>" <first-arg>` | The table's first column equals that `route` box's arguments, in order. **This is the allowlist guard read from the doc side** |
| `sh-aconnect "<script>" connect\|disconnect` | The table's first two columns equal the script's `aconnect` calls. The two directions are parsed **separately**, because a check that lumped them would pass with the rig unwired |

The other four are dangling document pointers, dangling script and patch paths, the full page
schema, and `C-NN` rule-ID resolution.

⛔ **A path that resolves can still be the WRONG file, and nothing catches that.** `ref-hardware.md`
pointed at `tools/wire.sh`, a Phase 1 ancestor of `Cut It/wire.sh` — 59 lines behind, no autoconnect
undo, no `|| true`. Found by reading, not by a gate.

✅ **Every page is written.** Six device pages, six module pages — `audio`, `boot`, `display`,
`map`, `state`, `tempo` — and three cross-cutting: `architecture`, `conventions`, `rig`.

⚠️ **`ref/device-os.md` was NOT written, deliberately.** `ref-hardware.md` is now exactly that page
and nothing else, and §10.8 says not to invest there until the Organelle cruft cleanup changes its
paths. **Renaming it into `ref/` is the last step of that cleanup, not of this refactor.**

**Next, in order:** **the journals** — which is now the whole of the remaining volume — then
`CLAUDE.md` as a router, then the `.pd` comments citing `C-NN` so the `ref-conventions.md` stub can
go.

⚠️ **THE LINE COUNT GOES UP PER PAGE, AND THAT IS EXPECTED.** `ref/device/sp404.md` replaced 279 source
lines with 281. Tables gained `Evidence` and `Item` columns, the pad map became sixteen rows instead
of a five-line diagram, and merging overlapping sources replaced "summary + full" with one full
statement. **The volume reduction is entirely in the journals**, which are still untouched and are
now **78% of what is left at the root**. Do not compress the module pages chasing it.

⛔ **AND THE LOSS CHECK IS NOT OPTIONAL — it has caught a real deletion twice.** Collapsing
`ref-software.md` lost twelve facts, including tempo propagation in full and the reason explicit
modes exist. Collapsing `ref-hardware.md` nearly lost four `###` subsections that had accumulated
under *Signal flow — power* and had nothing to do with power, including the root cause of the
Launchpad boot hang. ⚠️ **A section is not what its heading says. Read what is under it before
deleting from heading to next `##`** — and probe 30–50 distinctive strings from the old text against
the new pages afterwards, case- and whitespace-normalised.

**Where the material for the remaining pages is:** `ref-software.md` (architecture, load-bearing
decisions, signal architecture, timing), `ref-hardware.md` (the device itself, wifi, power, cabling,
gear), `ref-display.md` (the display arbiter only), `ref-midi.md` (the addressing model and
`u_tempo`'s clock construction), and the `.pd` comments, which hold material that is in no `.md` at
all — `u_map`, `u_state`, `u_init` and `m_404` are the richest.

### 10.10 Still open

- **The module taxonomy itself.** The names the docs adopt are the names the tests will inherit, so
  they are worth settling first. The `.pd` prefixes (`u_`, `m_`, `g_`, `c_`) are the obvious
  candidate axis, but the gates cut across them — a MIDI-emission gate spans `m_volca`, `m_404`,
  `m_launchpad` and `u_tempo`.
- ✅ **How far `docs-check.py` should reach — settled by building it.** It verifies the channel
  blocks against `wire.sh`, and the answer to "how much checking is too much" turned out to be
  governed by whether the fact already exists twice in machine-readable form. Where it does, the
  check is ~25 lines and pays for itself; where it does not, no check is possible at any price.
- ✅ **Where the display arbiter goes — RULED: its own page**, `ref/module/display.md`, built. The
  reasoning is kept below because the same question will come up for whatever v0.4 shares between
  two devices. `ref-display.md` was 279 lines, and about 220 of them
  are the framework rather than device fact: the `home < modal < alert` arbiter that `g_oled`,
  `g_grid` and `g_led` share, the `disp` bus protocol, and the geometry. Four files implement it.
  **Revised proposal: its own page, `ref/module/display.md`** — it is one instrument concern, which
  is what `ref/module/` is for, and it splits the Launchpad no worse than `tempo.md` splits
  `u_tempo`: the device page says what the hardware can show, the module page says how Cut It
  arbitrates. Putting it in `ref/architecture.md` instead would make that file a grab bag before it
  is even written. That splits the Launchpad
  *device vs instrument* rather than accidental. **Brendan has not ruled on this; ask first.**
- **The eight unticked `plan-tests.md` items** (5, 39, 43–46, 81, 95) need a destination before that
  file dissolves — they are open work, so §4 is where they belong.
