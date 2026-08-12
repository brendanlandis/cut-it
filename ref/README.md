<!-- schema: freeform -->
# `ref/` — one page per module

**A module is either a physical device or one instrument concern.** Everything about it lives on its
page: what it is, what was measured, what will bite you, and how Cut It chooses to use it.

This replaced a topic-major layout — `ref-midi`, `ref-display`, `ref-hardware`, `ref-software` —
where the Launchpad's facts were spread over 416 lines in four files. Nobody decided that; each
session added to whichever file it was already in. **A device-major layout gives a fact exactly one
place it can go**, which is the only thing that resists the drift, because the docs are written by
agents who cannot know what the other files already say.

## The index

<!-- check: index -->

| Kind | Where | Pages |
|------|-------|-------|
| **Devices** — one physical thing each | `ref/device/` | `launchpad` · `nanokontrol` · `organelle` · `phone` · `sp404` · `volca` |
| **Modules** — one instrument concern each | `ref/module/` | `audio` · `boot` · `debug` · `display` · `error` · `map` · `presence` · `state` · `tempo` |
| **Cross-cutting** | `ref/` | `architecture` · `conventions` · `workflow` · `device-os` · `wifi` · `rig` · `README` |
| **Parking** | `ref/` | `_unfiled` — must be empty |

**The directory is the kind**, so `ls` answers the question and `docs-check.py` asserts that
`device/` and `module/` hold only `schema: module` pages. The table above is checked against what
actually exists, so it cannot go stale.

⚠️ **v0.4 grows `module/`, not `device/`.** The device set is fixed by the hardware; the filter
stages, drum mode, sampler and capture each become a module page.


## Writing a page — use the `docs` skill

⛔ **Invoke the `docs` skill before adding or restructuring any page here.** It carries the page
schema, how a Trap is written, the five markers and exactly what each means, the anchor syntax for
facts the patch also holds, and what to do with material that fits no section.

It loads on demand, so it costs nothing in a session that only *reads* documentation.

**And `test/gate/docs-check.py` enforces all of it** — run the gate rather than trying to remember it:

```sh
python3 test/gate/docs-check.py -v
```

| Check | What it asserts |
|-------|-----------------|
| `pd-text` | An anchored table equals the `[text define]` in the patch |
| shape | Every `ref/` page declares a schema and keeps to it |
| index | The table above lists exactly the pages that exist |
| dangling | Every pointer to a document resolves |
| `C-NN` | Every rule cited anywhere exists, and the `pd` skill's copy matches the doc |
| ⬜ | Every open item sits under `Open`, on every page, whatever its schema |

## The standard for v0.4

**Written down because it is what keeps the next hundred pages from costing what the last ones
did.** v0.4 grows `ref/module/` — one page per filter stage, the drum mode, the sampler.

- ⛔ **An `e_` page is written AFTER the stage is hardware-verified, not before.** A pre-written
  page is how a completion marker silently becomes false, and this project has already had one
  page assert a thing about `u_map` that stayed wrong until Phase 9 contradicted it.
- **An `e_` page holds what it is, its parameters, and its traps.** No rationale essay, no evidence
  ledger, no history — **git is the journal**.
- **A rejected alternative gets one sentence, not a section.**
- **A measured number goes on the page and is cited from the patch**, never the reverse. A `.pd`
  comment has no link syntax, so it cites a bare `item NNN` or a bare page path — which is what
  makes the number write-once instead of write-twice.

⚠️ **This standard is for NEW material only.** The existing device and module pages describe
hardware that cannot be re-derived from the code, and an agent handed this project cold has no
other source for it. **They stay as they are.**
