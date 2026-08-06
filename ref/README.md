<!-- schema: freeform -->
# `ref/` — one page per module

**A module is either a physical device or one instrument concern.** Everything about it lives on its
page: what it is, what was measured, what will bite you, and how Cut It chooses to use it.

This replaced a topic-major layout — `ref-midi`, `ref-display`, `ref-hardware`, `ref-software` —
where the Launchpad's facts were spread over 416 lines in four files. Nobody decided that; each
session added to whichever file it was already in. **A device-major layout gives a fact exactly one
place it can go**, which is the only thing that resists the drift, because the docs are written by
agents who cannot know what the other files already say.

## The page schema

Line 1 declares which schema applies. `tools/docs-check.py` enforces the rest, so the shape does not
have to be remembered — **run the gate and it will tell you.**

```markdown
<!-- schema: module -->
# Roland SP-404MKII
**Files:** `Cut It/m_404.pd` · **Gate:** `tools/phase9-assert.sh`

## What it is     one or two paragraphs
## Facts          schema'd tables, every one with Evidence and Item columns
## Traps          what will bite you
## Design         how Cut It uses the device, and why
## Open           unknowns only, each linking to plan-v03.md §4
```

`##` is the fixed skeleton and must appear exactly, in that order. `###` inside a section is free.

| Schema | For | Checked |
|--------|-----|---------|
| `module` | A device or an instrument concern | Full skeleton, Files/Gate paths, Facts tables, marker placement |
| `rules` | `conventions.md` — a numbered rule list rather than a module | Markers only |
| `freeform` | This file | Markers only |

**What it is / Facts / Traps are about the DEVICE. Design is about US.** That distinction is why
`Design` exists: the three-tier Launchpad decision and the 404's accepted mic bleed are neither
measured behaviour nor something that will bite you, and they were being crammed into `Facts` as
prose.

⚠️ **`Design` holds what is DECIDED, not what is planned.** A table of features that do not exist is
intent, and `ref/` states what is. It belongs in `plan-v03.md`.

## How a Trap is written

**A claim and its fix. Nothing about how it was found** — that is git's job. Keep the mechanism
where the fix needs it; drop the history.

```markdown
### <the claim, as a heading>

<what goes wrong, and the mechanism if the fix needs it>

**Fix:** <what to do instead>
```

## The markers, and they are the project's only permitted emoji

| Glyph | Means, exactly |
|-------|----------------|
| ✅ | Verified on this hardware |
| 📄 | Manufacturer documentation |
| ⬜ | Unknown or unverified. **Only inside `Open`** |
| ⛔ | A trap: ignoring it breaks something **silently** |
| ⚠️ | An operational rule: never do this to the rig or the device |

⛔ **A check mark never means "built".** An evidence marker never rots; a completion marker silently
becomes false, which is how `ref-conventions.md` came to assert that `u_map` used no lookup table
and kept saying it until Phase 9. `docs-check.py` fails on a ✅ in any heading.

In tables the evidence class is a **column value** — `verified` / `doc` / `unknown` — so that no
fact row can omit it. In prose the glyph is used directly.

## Facts that the patch also holds

Where a fact exists in both a page and a patch, **anchor it** and the two cannot drift:

```markdown
<!-- check: pd-text "Cut It/m_404.pd" $0-pad -->
```

The table immediately below must equal that `[text define]`'s contents. Reintroduce the old `47 + n`
pad map and the gate goes red **at pad 5**, before deploy and before hardware.

## Material that fits no section

**Do not cram it in, and do not drop it.** Move it verbatim into `_unfiled.md`, work out what shape
it wants and what else would belong in that shape, then ask *with the proposal*. The gate fails
while anything is parked there, so the question cannot be quietly skipped. One instance is an
exception; three are a missing section — `Design` was added exactly that way.
