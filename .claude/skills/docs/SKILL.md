---
name: docs
description: Writing or editing documentation for Cut It — anything under ref/, CLAUDE.md, or a plan- document. Carries the page schema, how a Trap is written, the five permitted markers, the anchor syntax for facts the patch also holds, and what to do with material that fits no section. Use before adding or restructuring any documentation page.
---

# Writing documentation for Cut It

## Why this is unusual

**Agents wrote 100% of these docs**, and that is what shaped the rules below. A session editing one
page has no way to know the same fact sits in seven others — it would have to grep for a fact it
does not know exists. Restatement is the only thing a cold context *can* do.

So **"one home per fact" cannot be a convention people follow.** It has to be a structure you fall
into, plus a program that catches drift. That program is `test/gate/docs-check.py`. **Run it rather than
trying to remember any of this:**

```sh
python3 test/gate/docs-check.py -v
```

## Where a page goes

**The directory is the kind.**

| Where | Holds | Schema |
|-------|-------|--------|
| `ref/device/` | One physical thing each. **Fixed set** — the hardware decides it | `module` |
| `ref/module/` | One instrument concern each. **This is what v0.4 grows** | `module` |
| `ref/` | Cross-cutting: `conventions`, `architecture`, `README` | `rules` / `freeform` |
| `plan-*.md` | Everything open. **`ref/` states what IS; a plan states what's OPEN.** A plan is scoped to one piece of work and is **deleted when it lands** — `plan-v04.md` is the standing one | — |

⚠️ Adding a page means adding it to `ref/README.md`'s index. The gate asserts the index lists
exactly what exists.

## The page schema

Line 1 declares the schema. `##` is the fixed skeleton and must appear exactly, in this order;
`###` inside a section is free.

```markdown
<!-- schema: module -->
# Roland SP-404MKII
**Files:** `Cut It/m_404.pd` · **Gate:** `test/gate/sp404-assert.sh` · **Bench:** `test/bench/midi-bench.pd`

## What it is     one or two paragraphs
## Facts          schema'd tables, every one with Evidence and Item columns
## Traps          what will bite you
## Design         how Cut It uses it, and why
## Open           unknowns only, each linking to plan-v04.md §3
```

**What it is / Facts / Traps are about the THING. Design is about US.** That distinction is why
`Design` exists — the Launchpad's three-tier decision and the 404's accepted mic bleed are neither
measured behaviour nor something that will bite you, and they were being crammed into `Facts`.

⚠️ **`Design` is last because most of it is forward-referencing** — "the reject outlet is the normal
path in `u_store`" means nothing before `Facts` says what `u_store` matches. **But the ONE decision
that makes the page legible goes in `What it is`, at the top**, and is then stated properly in
`Design`. Every page does this already: `tempo` opens *"`u_tempo` is the master REFERENCE, and it is
not the clock"*, `state` opens *"it knows nothing about what any key MEANS"*, `map` opens
*"table-driven and mode-dependent"*. **A page whose `What it is` is pure description reads as a list
of parts.** This one is a form, not a gate — nothing can check that the right decision was chosen.

⚠️ **`Design` holds what is DECIDED, not what is planned.** A table of features that do not exist is
intent, and belongs in `plan-v04.md`.

⚠️ **Every path on that line must exist**, so a page cannot outlive the abstraction it documents.
`none` is a legitimate answer to `Gate` or `Bench`.

⛔ **A GATE AND A BENCH ARE DIFFERENT ORACLES, which is why the page declares both.** A gate's verdict
comes from a **program** — headless, on the Mac, unattended, any output is a failure. A bench's comes
from a **person's eyes**, on the device, with the rig plugged in, judging *"PASS IF the third pad is
green"*. Neither substitutes for the other: **Phase 6 passed 25/25 on the Mac twice and shipped three
bugs.** Declaring only one leaves the other kind of coverage invisible, and the gate now fails if a
page names neither.

## How a Trap is written

**A claim and its fix. Nothing about how it was found** — that is git's job. Keep the *mechanism*
where the fix needs it; drop the history, the cost, and what the docs used to say.

```markdown
### <the claim, as a heading>

<what goes wrong, and the mechanism if the fix needs it>

**Fix:** <what to do instead>
```

⚠️ **This is a form, not a line-count target.** Applied to `ref/device/sp404.md` it came out exactly
line-neutral. Pages get more scannable, not shorter.

## The markers — the project's only permitted emoji

| Glyph | Means, exactly |
|-------|----------------|
| ✅ | Verified on this hardware |
| 📄 | Manufacturer documentation |
| ⬜ | Unknown or unverified. **Only inside `Open`** |
| ⛔ | A trap: ignoring it breaks something **silently** |
| ⚠️ | An operational rule: never do this to the rig or the device |

⛔ **A check mark never means "built".** An evidence marker never rots; a completion marker silently
becomes false — which is how the old conventions doc came to assert `u_map` used no lookup table and
kept saying it until Phase 9 contradicted it. **The gate fails on a ✅ in any heading.**

In tables the evidence class is a **column value** — `verified` / `doc` / `unknown` — so no fact row
can omit it. In prose the glyph is used directly.

**Corrections get no marker and usually get deleted.** "X was recorded here and it is FALSE" goes
once the false claim is gone; the trap that produced it survives, the retraction does not.

## Facts the patch also holds

Anchor them and the two cannot drift:

```markdown
<!-- check: pd-text "Cut It/m_404.pd" $0-pad -->

| Pad | Note | Evidence | Item |
|-----|------|----------|------|
| 1   | 48   | verified | 190  |
```

The table immediately below must equal that `[text define]`'s contents. Reintroduce the old `47 + n`
pad map and the gate goes red **at pad 5** — before deploy, before hardware.

## Item numbers are FACT IDS

`item 228` is not "the 228th thing measured" — it is the ID of the `pgmout` row in
`ref/device/volca.md`. About 180 citations across the project resolve by grep. **Never reuse a
number**; new facts take the next one.

## Material that fits no section

**Do not cram it in, and do not drop it.**

1. Move it **verbatim** into `ref/_unfiled.md`.
2. Work out what shape it wants — a new `##` in the schema, a new schema, or a page of its own —
   and what else in the repo would belong in that shape. **One instance is an exception; three are a
   missing section.**
3. **Ask, with the proposal.** Not "where does this go?" but "here is the passage, here is the shape
   I think it wants, here is what else would move into it."

The gate fails while anything is parked there, so the question cannot be quietly skipped. `Design`
was added exactly this way.

## Before calling a page done

```sh
python3 test/gate/docs-check.py        # the doc gate
./test/run.sh                     # every gate, ~2.5 min. Read RESULT:, do not grep for it
```

⚠️ **Prove nothing was lost.** When moving material, probe 30–50 distinctive facts from the removed
source against the new page and check each survives. That has caught a real omission twice.
