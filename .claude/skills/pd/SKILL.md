---
name: pd
description: Writing, editing or reviewing Pure Data for the Cut It Organelle patch. Vanilla Pd 0.49 constraints, the C-1..C-14 conventions, how to edit a .pd file by hand without breaking it, and the gates that must pass. Use whenever touching anything under "Cut It/" or tools/*.pd.
---

# Writing Pd for Cut It

## The three constraints that are not negotiable

**1. Target is Pd vanilla 0.49, permanently.** Verified on the device: `Pd-0.49.0, compiled Oct 9
2018`. The Organelle 1 runs OS 4.0, **which is the end of the line for this hardware** — 4.1 was
Organelle M only; 4.2 / 4.4 / OS 5 are M/S/S2. **Do not suggest any object newer than 0.49.**

**2. Never save an Organelle-bound patch from plugdata.** plugdata is built on Pd 0.55+ and rewrites
`.pd` files into a newer format — iemgui colours become hex (`#fcfcfc` instead of `-262144`),
floatatoms gain a trailing arg. **Pd 0.49 cannot parse that.** It has already happened once in this
repo. Edit with vanilla Pd 0.49 for anything that ships.

**3. Vanilla objects only, by default.** The Organelle ships neither ELSE nor cyclone. Bundling them
is possible — the device is armv7 — but current ELSE needs Pd 0.56+, and 0.49 expects the
`.pd_linux` extension rather than `.l_arm`. Pure-Pd abstractions drop into the patch folder with no
such concerns. Prefer vanilla unless a specific object is worth the dependency.

## The rules

Full text and reasoning: `ref/conventions.md`. **Cite a rule by ID from a patch comment** — a `.pd`
comment is the only documentation visible while editing in Pd and it has no link syntax.
`tools/docs-check.py` asserts every `C-NN` cited anywhere resolves.

| ID | Rule |
|----|------|
| C-1 | `$0-` every send, receive, table and array name inside an abstraction |
| C-2 | Bare global names only from the allowlist — `mode` `tempo` `clock` `start`/`stop` `panic` `param` `err` `disp` `state`, plus mother's own |
| C-3 | `[trigger]` on every fan-out, even when the current order happens to work |
| C-4 | Never `adc~` / `dac~` — `[r~ inL]`/`[r~ inR]` in, `[throw~ outL]`/`[throw~ outR]` out |
| C-5 | One owner per display surface. Everything else asks via `disp` |
| C-6 | Finish assembled messages with `[list trim]`, and `[list append]` after a `route` |
| C-7 | Clear optional fields on every message — `[list split n]` on exactly *n* atoms never fires |
| C-8 | `[t b]` in front of anything behind a reject outlet — a reject carries DATA, not a bang |
| C-9 | Every `[print]` in a deployed abstraction sits behind `[del 2000]` |
| C-10 | Append boxes at the end of a `.pd`, and move the `#X connect`s with them |
| C-11 | Grain timing is audio-domain — `phasor~` and `vline~`, never `metro` / `line~` |
| C-12 | Report failures on `[s err]` as `<level> <source> <text>`, text one symbol ≤ 21 chars |
| C-13 | No dynamic patching, no `[value]`, no copied subpatches |
| C-14 | Edit a `#X text` by replacing the whole line — never scan for the next `;` |

## Editing a `.pd` file by hand

⛔ **C-14 — a `#X text` cannot be edited by finding "the next `;`".** Pd splits a file into records
on **unescaped** semicolons, and a comment legitimately contains escaped ones (`\;`). A scan stops
mid-comment and the tail becomes a record with no `#X` prefix. **This has broken the patch three
times.** Replace the whole line.

⛔ **C-10 — `#X connect` names boxes by POSITION IN THE FILE.** Inserting a box mid-file renumbers
every subsequent index and silently invalidates every later connect. Append at the end and move the
connects with it. **This has bitten the project five times.**

Counting records by eye is what causes it. Ask instead:

```sh
python3 tools/pd-layout-check.py --boxes "Cut It/u_map.pd"
```

Comments count. `#X declare` does not. Subpatch contents do not, but the `#X restore` line does.

⚠️ **A reject outlet carries the data that failed to match, not a bang** — `route`, `select`,
`moses`, `spigot`. Put `[t b]` in front of anything downstream (C-8).

⚠️ **`[list split n]` on exactly *n* atoms never fires its right outlet.** Silent non-event (C-7).

⚠️ **`[list trim]` before `route`** — `route` matches a *selector*, and `[list prepend]`/`[list
append]` produce a `list` selector (C-6).

⚠️ **Pd 0.49 does not warn about extra creation arguments at all.** A wrong arg count loads in
perfect silence, so a clean syntax check proves nothing about arity.

## The gates

**Run these before calling anything done.** All Mac-side; they touch no device.

```sh
python3 tools/pd-layout-check.py "Cut It"/*.pd    # after every edit -- PROBLEM = fail
./tools/check-all.sh                              # ~40 s, every gate in one command
```

⚠️ **Read `check-all.sh`'s result, do not grep for it.** Exactly one line matches `RESULT:`, and the
exit status is trustworthy. A pattern like `grep -E 'ALL|FAILED'` also matches the per-gate
`--- FAILED:` lines, and a broken patch has been committed that way.

⚠️ **`deploy.sh` gates on OUTPUT, not exit status** — Pd exits 0 even when objects fail to create.
Its check quits at about 735 ms, which is why every deployed `[print]` sits behind `[del 2000]`
(C-9).

⛔ **A gate is not trusted until it has failed.** `phase8-assert.sh` passed the broken patch 15/15
on its first can-it-fail run. Reintroduce the bug, watch it go red, revert.

## Where to read more

| | |
|---|---|
| `ref/conventions.md` | The rules in full, with reasoning |
| `ref/README.md` | How the documentation is organised, and the page schema |
| `ref/device/<name>.md` | Everything about one device — messages, traps, how Cut It uses it |
| `ref/module/<name>.md` | One instrument concern |
| `CLAUDE.md` | Repo layout, working notes, the device itself |
| `plan-v03.md` | The only plan document. §4 is every open question |

**Off-device development is the default.** Open `Cut It/main-dev.pd` in Pd 0.49 on the Mac and the
whole instrument is there — `u_mother-stub` draws the front panel inline and fakes the knobs, keys,
aux and encoder. Most work should never need the Organelle powered on.

**There is a console, but not the obvious way.** A menu-launched patch runs `-nogui` and its errors
go to tty1. Launch `mother.pd` and `main.pd` together over SSH with output redirected to a file and
you get a real console, including `[print]` taps on any bus. It found a silent bug in Phase 1.
