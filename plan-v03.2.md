# Plan v0.3.2 — cleanup, and the decision items

**The documentation is not too long; it is duplicated and unpoliced.** Twenty facts are stated in two
to five files each and `test/gate/docs-check.py` mechanically ties only four of them. Meanwhile
~150 KB of Pd comments hold **measured numbers that exist nowhere else**, which makes every new fact
a write-twice job by construction.

This plan fixes both, moves `deploy.sh`, answers three directory questions, takes four decisions that
have been open long enough to look permanent, and closes the enforcement hole that let open items
scatter in the first place.

**No hardware. No patch behaviour changes** — only comments inside `.pd` files, which is still Pd
editing and still needs the skill.

---

## ⚠️ Constraints that bind everything below

- **Pd vanilla 0.49, permanently.**
- ⛔ **Never open or save an Organelle-bound patch in plugdata.** ⚠️ **This plan edits every `.pd` in
  the folder**, so that rule has never mattered more. Edit `.pd` files by hand per the **`pd`** skill.
- **Vanilla objects only.**
- ⛔ **Never touch git.** Reading is fine. Brendan commits his own work.
- ⚠️ **Before any bulk delete or overwrite, print the count, a sample, and the evidence the targets
  are what you claim — then ask.** Verifying privately is not enough.
- ⛔ **A section is not what its heading says.** Read what is under it before deleting from one
  heading to the next, and probe distinctive strings afterwards. **That has caught a real deletion
  twice in this project.**

---

## What to read, and how much

⛔ **This plan reads more than any other of the six, because it is the only one that edits
documentation wholesale. Budget for it.**

| Document | How much | Why |
|---|---|---|
| [CLAUDE.md](CLAUDE.md) | **All of it** | The router, and you are editing it |
| The **`docs`** skill | ⛔ **Invoked, not read** | The page schema, how a Trap is written, the five markers, the anchor syntax |
| The **`pd`** skill | ⛔ **Invoked, not read** | You are editing comments inside every patch |
| [plan-v04.md](plan-v04.md) | §3 and §7 in full | Two of its ⬜ headings are yours to close |
| `git log` | **Grep it, never read it** | Git is the journal — and it is where the history you delete from prose already lives |
| [ref/README.md](ref/README.md) | **All 52 lines** | The page schema you must not break, and the index the gate checks |
| [ref/conventions.md](ref/conventions.md) | **All 746 lines** | **You are splitting it.** The *Development workflow* / *There IS a console* / *How a phase runs* run is ~165 lines of process, not Pd rules |
| [ref/device-os.md](ref/device-os.md) | **All 459 lines** | **You are splitting it.** Half of it is the wifi investigation |
| `test/gate/docs-check.py` | **All of it** | You are extending it. Its ⬜ rule sits inside the `schema == 'module'` branch — that is the hole |
| The `Open` section of **every** `ref/` page | All of them | ~24 items across 18 pages |
| `deploy.sh` | **All 140 lines** | You are moving it. Its header is a third copy of the flag table |
| [device/README.md](device/README.md) | All of it | It duplicates the `mount.sh` guard **verbatim** and sits outside `ref/`, so the gate has never seen it |
| [tools/README.md](tools/README.md) | All of it | Two ⬜ items and the standard for what stays |
| The comments in `Cut It/*.pd` | **The long ones.** Start with `grep -n '^#X text' "Cut It"/*.pd` and read every block over ~400 characters | ~30 blocks hold measured numbers that exist nowhere else |
| [ref/architecture.md](ref/architecture.md), [ref/rig.md](ref/rig.md) | Skim, for the duplication list only | Both restate facts that live elsewhere |
| A `ref/device/` or `ref/module/` page | **Only when you touch it** | Do not read the set |

**Do not read** `test/gate/*-assert.py` or anything under `test/bench/`. This plan changes no test
logic beyond `docs-check.py`.

---

## What is already true

- **`ref/` states what IS; a plan states what is OPEN.** A plan is scoped to one piece of work and is
  deleted when it lands. `plan-v04.md` is the exception that persists.
- **A fact appears once in full; everywhere else it is a citation.**
- **`item NNN` is a fact ID, not a log entry.** ~180 citations resolve by grep. **Never reuse a
  number.**
- **Five markers and no other emoji in this repo.** ⛔ A check mark never means "built" — an evidence
  marker never rots, a completion marker silently becomes false.
- **`docs-check.py` mechanically ties exactly four things today**: the 404 pad map, `u_map`'s
  destination list, and `wire.sh`'s two connect/disconnect lists.

---

## Phase 1 — `deploy.sh` moves into `tools/`

Everything in `tools/` is run by a person, on purpose; `deploy.sh` is the most-run script in the
project and the only one at the root.

Update every caller and every citation: [CLAUDE.md](CLAUDE.md), [ref/conventions.md](ref/conventions.md)'s
flag table, [ref/device-os.md](ref/device-os.md)'s prose copy, [plan-v04.md](plan-v04.md),
[test/README.md](test/README.md), [tools/README.md](tools/README.md), and the bench steps that
instruct `./deploy.sh` — ⛔ **which means editing `test/bench/bench_steps.py` and regenerating, never
a bench `.pd`.**

✅ **`docs-check.py`'s `ROOTSCRIPT` regex can then be deleted.** It exists only because the file had
no directory to recognise it by; once it is under `tools/` the normal `DIRS` matching covers it.
⚠️ Its comment warns that listing `logroll.sh` there reported six phantom failures — do not
generalise the regex, remove it.

---

## Phase 2 — the three directory questions

### `device/` vs `device-state/` — keep both

**The distinction is real and the names already carry it.** `device/` is configuration that exists
**only** on hardware and has no other copy — the nanoKONTROL scene is one accidental
`REC+STOP+SCENE` from being lost forever, and `pdsettings`' `path1` is what makes `[shell]`,
`packOSC` and `routeOSC` resolve in the menu-launched patch. `device-state/` is what the
**instrument** wrote, pulled back by `tools/fetch-state.sh`.

`device-state/` currently holds 20 bytes because only `mode` persists; **its value is prospective and
it grows in v0.4.** Add a short `README.md` under `device-state/` so the distinction is stated
somewhere other than [CLAUDE.md](CLAUDE.md). ⚠️ Note that `docs-check.py` has `device-state` in
`SKIP_DIRS`, so nothing there is ever scanned.

### `mac-stubs/` — keep it exactly where it is

⛔ **Do not move it into `Cut It/`.** Two reasons, both hard:

1. `Cut It/u_err.pd` and `Cut It/u_init.pd` carry `#X declare -path ../mac-stubs`. **It must be a
   sibling of the patch folder.**
2. Its own header records the trap: **a file named `shell.pd` reaching the patch folder shadows the
   external and MIDI wiring silently stops happening.**

It is one file, live in seven places, and **it is the only member the mechanism can ever have** —
everything else the patch needs is a built-in class, which is why `test/stubs/` exists as a separate,
differently-shaped mechanism. ⚠️ Record that reasoning on [ref/conventions.md](ref/conventions.md)
so the question does not recur.

### `tools/` — what goes

| Target | Verdict |
|---|---|
| `tools/__pycache__/` and the two under `test/` | **Delete.** Five orphaned `.pyc` files; one has no source anywhere in the repo. Confirm `.gitignore` covers them |
| `tools/display-cpu.sh` | **Fix or retire.** Its 11.2 % budget is Phase 5's, and Phase 6 already exceeded it — it reports OVER BUDGET as a matter of course |
| `tools/self-wire.pd` | **Retire.** Superseded by `u_init` running `wire.sh` on every load; its one remaining claim is already stated on [ref/module/boot.md](ref/module/boot.md) |
| `tools/audio-probe/`, `oled-probe/`, `osc-bridge/`, `status-display/` | **Keep** — see Phase 5 |

⛔ **The test is "would you run it again", not "is it used".** A script mentioned in no document is
fine.

---

## Phase 3 — the ref/ pass

### Split the two oversized pages

- **`ref/conventions.md`** → the process material becomes a new `workflow.md` under `ref/`: the
  deploy loop, *There IS a console*, *How a phase runs*. What stays is `C-1`…`C-14` and the Pd rules
  they govern.
- **`ref/device-os.md`** → the wifi investigation becomes a new `wifi.md` under `ref/`. ⚠️ **Half of
  that page is an evidence ledger** — an *"evidence, item by item"* table — which is exactly the
  artefact this project says it dissolved. Moving it is the moment to decide what of it is a **fact**
  (which stays, on the page) and what is a **narrative of how it was found** (which goes, because
  git holds it).

⚠️ **Adding a page means adding it to `ref/README.md`'s index**, and the gate asserts the index lists
exactly what exists.

### Resolve the duplications

Twenty facts are stated in more than one place. Pick one home, cite from the rest. The worst:

| Fact | Where it is repeated |
|---|---|
| The `param` vs `disp` rationale | `conventions` and `architecture`, **near-verbatim, two full paragraphs** |
| "Names on `param` are physical, never functional" | `conventions` and `architecture`, **verbatim** |
| The `m_` boundary is expensive to retrofit | `conventions`, `architecture` ×2, `plan-v04` |
| Poly-tempo — nothing may assume the global clock is its clock | `conventions`, `architecture`, `module/tempo` ×2, `plan-v04` |
| `killall pd` strands the Launchpad; `lp-live.sh` rescues it | `conventions`, `device/launchpad` ×3, `tools/README` |
| The `mount.sh` write-protect guard, **including the shell snippet** | `device-os` and `device/README` |
| Output devices are WIRED, not given a bus | `conventions` (with the rejected alternatives) and `architecture` |
| `/reloadNoRemount`, never `reload.sh` | `conventions`, `device-os`, `deploy.sh` |
| `deploy.sh`'s flags | `conventions` (table), `device-os` (prose), the script's own header |
| The `env~` 18–19 noise floor | `rig`, `module/audio`, `module/display` — all cite item 11, and all write the number |
| The DSP-vs-MIDI CPU finding (item 75) | `module/tempo`, `tools/README`, `device-os`, `plan-v04` |
| The audio-gate open item | **Five copies** — see [plan-v03.3.md](plan-v03.3.md), which strikes them |

⚠️ **`[list trim]` / `route` matching a selector (C-6) is the defensible exception.** It is restated
as a local Trap on six pages, but each is a different concrete failure. Leave those; make each one
**cite C-6** rather than re-derive it.

### Two duplicate blocks inside a single page

- [ref/device/sp404.md](ref/device/sp404.md) states **the same trap twice** — that the BPM beside a
  pad is the sample's tempo, not the sync tempo. Same claim, same fix, two headings. **Delete one.**
- [ref/device/phone.md](ref/device/phone.md) states the address-discovery rationale twice.

---

## Phase 4 — the Pd comments

**This is the biggest lever in the plan, and the direct fix for documentation feeling like double
work.**

The rule already exists — a comment cites by ID because a `.pd` comment has no link syntax, and the
fact lives on a `ref/` page where it can be anchored. It is simply not applied: **only eleven
comments in the whole folder name a `ref/` page.**

⛔ **This is not a deletion pass.** Each measured number moves to its page, takes an item number, and
leaves a citation behind. **That is what makes it write-once instead of write-twice.**

### The blocks that hold facts existing nowhere else

| File | What is only there |
|---|---|
| `Cut It/wire.sh` | The 2026-08-03 phantom-`lp-cc-1` incident, and the 2026-08-06 post-power-cycle enumeration order |
| `Cut It/u_tempo.pd`, `Cut It/c_clock.pd` | The 344 Hz audio-domain ceiling and its derivation — **stated twice, in two files** |
| `Cut It/g_grid.pd` | A 300-word retraction about palette indices, *"measured twice, green one run and dark the next"* |
| `Cut It/m_launchpad.pd` | The whole watchdog rationale — 133 ms, ten forks, and why the first version's 12-second bound was useless |
| `Cut It/m_404.pd` | The rate-limit arithmetic, and why `makenote` cannot serve ten channels |
| `Cut It/u_net.pd` | The UDP-connect trap, and the 1550 / 2200 ms address-resolution timings |
| `Cut It/u_root.pd` | ~250 words on broadcast vs unicast delivery — **the single largest block** |
| `Cut It/u_map.pd` | A full bug postmortem, **stated twice in the same file** |
| `Cut It/u_store.pd`, `Cut It/u_state.pd` | Three measured `text` / `moses` / `read -c` facts |

### Also in this pass

- **Five files cite nothing at all**: `c_clock.pd`, `u_state.pd`, `m_organelle.pd`, `main.pd`,
  `main-dev.pd`. `main.pd`'s single comment holds the entire creation-argument contract.
- ⛔ **Stale version strings ship on hardware.** `u_init.pd` sends `status v0.2-ready` and
  `g_oled.pd` sends `cut-it v0.2` **on a completed v0.3**. These are not comments — they are output.
- ⛔ **`g_grid.pd` states its cell count three different ways in one file**: 96, 108, 109. One is
  right; find out which and say it once.
- `u_root.pd` says *"v0.3: e_chop, e_pitch, e_trem, e_verb go in this gap."* That is **v0.4**.
- Several comments say *"revisit in Phase 4"* or *"m_nano in Phase 4 will send…"* for work already
  done.

⚠️ **Do not delete a comment that explains why a box is the way it is.** The 133 ms and the ten forks
are *why the watchdog is allowed to fork at all* — that reasoning stays next to the code. **What
moves is the measurement; what stays is the consequence.**

---

## Phase 5 — the four decisions

⛔ **Not a register. Four decisions taken and struck.**

### Do the reference patches under `tools/*/` earn their keep? — **Keep**

`audio-probe/`, `oled-probe/`, `osc-bridge/` and `status-display/` are each the working proof behind
a claim on a `ref/` page. **[plan-v03.5.md](plan-v03.5.md) will want `oled-probe/` and `osc-bridge/`
as working references within weeks**, which is exactly the "would you run it again" test. Record the
answer on [tools/README.md](tools/README.md) so the question stops recurring, and strike the ⬜ from
`plan-v04.md` §3.

⚠️ `pdparty-scene/` was never part of this question — [ref/device/phone.md](ref/device/phone.md)
names it as a `Files:` entry, so it is live.

### Does `g_led` need layers? — **No**

It takes the last state sent, there are four states, and no caller has ever needed a TTL. Record it
as a **decision** in that page's `Design` section and strike the ⬜ from
[ref/module/display.md](ref/module/display.md).

### The nanoKONTROL's factory transport map — **a permanent limitation**

Unknowable without a factory reset that would destroy the current scene, and the scene is the thing
[device/](device/) exists to protect.

### The Volca transmits nothing, ever — **a permanent limitation**

Structural, not a gap.

⚠️ **The last two are not deletions.** A permanent limitation stays on its page — it changes from an
open question into a stated fact, so nobody rediscovers it as news. **Move it out of `Open` and into
`Facts` or `Traps` with `unknown` as its evidence value.**

---

## Phase 6 — close the enforcement hole

**`docs-check.py`'s ⬜-outside-`Open` rule sits inside its `schema == 'module'` branch, so freeform
pages are unpoliced.** That is how `ref/device-os.md` came to carry five live open items with no
`Open` section at all. **Extend the rule to every page.**

Then add the check that makes this batch stick: **every remaining ⬜ must name the plan or the
version that closes it. A bare ⬜ fails the gate.**

⚠️ **Land this check LAST in the whole batch, after plans v0.3.0, v0.3.3, v0.3.4 and v0.3.5 have
shipped.** Until then most items legitimately have no closer, and **a gate that stays red for two
weeks is a gate that gets ignored.**

⚠️ **Exclude the marker definitions.** [CLAUDE.md](CLAUDE.md)'s marker table, the `docs` skill's
marker table, and prose that *quotes* a past ⬜ are mentions of the glyph, not open items. There are
five such lines today; the check must count structure, not characters.

---

## Phase 7 — the standard for v0.4

**Write this down, because it is what keeps the next hundred pages from costing what the last ones
did.** It goes on [ref/README.md](ref/README.md) under *Writing a page*:

- **An `e_` page is written AFTER the stage is hardware-verified, not before.** ⛔ A pre-written page
  is how a completion marker silently becomes false.
- **An `e_` page holds what it is, its parameters, and its traps.** No rationale, no evidence table,
  no history — **git is the journal**.
- **A rejected alternative gets one sentence, not a section.**
- **A measured number goes on the page and is cited from the patch**, never the reverse.

⚠️ **This standard is for new material only.** The device and module pages describe hardware that
cannot be re-derived from the code and that an agent handed this project cold has no other source
for. **They stay as they are.**

---

## Verification

```sh
python3 test/gate/docs-check.py -v        # after EVERY move, not once at the end
./test/check-all.sh                       # read the RESULT: line
./deploy.sh                               # from its new home, to a real device
```

- ⚠️ **Prove nothing was lost.** When moving material, probe **30–50 distinctive strings** from the
  removed source against the new page and confirm each survives. **That has caught a real omission
  twice.**
- **Grep each retired duplicate's distinctive phrase** and confirm exactly one survivor.
- **`docs-check.py`'s printed path count must go UP, never down** — its own comment says so, and that
  count is what proves the `DIRS` list is still complete after `deploy.sh` moves.
- ⛔ **Re-run every gate after the comment pass.** Editing `.pd` files by hand is how cords get
  misnumbered, and `pd-layout-check.py` is what catches a cord landing on a comment.

---

## Done means

1. `deploy.sh` is under `tools/`, every citation follows it, and the `ROOTSCRIPT` special case is
   gone.
2. `ref/` has two new pages, the index lists them, and no fact is stated in two places without one
   being a citation.
3. Every measured number in a Pd comment has an item number and a home on a `ref/` page.
4. The four decisions are recorded as decisions; two ⬜ items became stated permanent limitations.
5. The ⬜ rule covers every page, and the closer-required check is written **but landed last**.
6. The v0.4 documentation standard is on [ref/README.md](ref/README.md).
7. [CLAUDE.md](CLAUDE.md)'s router and `plan-v04.md` §2 match what is now true.
8. **This file is deleted.**

⛔ **This plan does not hand its open items to `plan-v04.md`.**

⛔ **Leave every change in the working tree.** Brendan commits his own work.
