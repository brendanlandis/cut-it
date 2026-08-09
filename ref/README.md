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
| **Modules** — one instrument concern each | `ref/module/` | `audio` · `boot` · `display` · `map` · `state` · `tempo` |
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
