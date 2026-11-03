---
name: pd
description: Writing, editing or reviewing Pure Data for the Cut It Organelle patch, and the Lua beside it. Vanilla Pd 0.57 constraints, pdlua and ELSE, the C-1..C-14 conventions, how to edit a .pd file by hand without breaking it, and the gates that must pass. Use whenever touching anything under "Cut It/" (.pd, .lua, .pd_lua) or tools/*.pd.
---

# Writing Pd for Cut It

## The three constraints that are not negotiable

**1. Target is Pd vanilla 0.57**, on the device and on the Mac, from 2026-11-03. The Organelle 1's
factory Pd is 0.49 (`Pd-0.49.0, compiled Oct 9 2018`), and its OS 4.0 is **the end of the line for
this hardware** — 4.1 was Organelle M only; 4.2 / 4.4 / OS 5 are M/S/S2. So 0.57 is our own build,
in `/sdcard/pd-0.57-0`: `/usr/bin/pd`, the path `mother` launches, is a script that runs it and
falls back to the factory 0.49, kept as `/usr/bin/pd-0.49`, if those files are missing
(`device/README.md`). **Do not suggest any object newer than 0.57**; one newer than 0.49 fails to
create on the fallback.

**2. Never save an Organelle-bound patch from plugdata.** plugdata is built on Pd 0.55+ and rewrites
`.pd` files into a newer format — iemgui colors become hex (`#fcfcfc` instead of `-262144`),
floatatoms gain a trailing arg. **Vanilla 0.57 writes and reads its own version of that format, but
whether plugdata adds anything 0.57 cannot read is untested.** It broke a patch here once, under 0.49.
Edit with vanilla Pd for anything that ships. ⚠️ A file 0.57 re-saves picks up that format beyond the
edit (hex colors, a number-box argument); 0.49 reads it, so it is diff noise (`cut-it/pd-057`).

**3. Vanilla objects, plus `[shell]`, pdlua and ELSE.** The Organelle's own externals are a factory
dozen in `/root/Pd/externals`, of which Cut It uses `[shell]`
(`~/Sites/!reference/critter-guitari-organelle-1.md`, *Externals*). Two libraries are ours, built
for 0.57 (from 2026-11-03): **pdlua**, for rules written in Lua, and **ELSE**, whose objects may
replace hand-built parts where they clearly help (*Lua and ELSE*, below). Neither loads on the 0.49
fallback. Nothing else: no cyclone, no other library, without a build and a decision.

## Lua and ELSE

**Where they come from:** `device/README.md`, *Lua and ELSE*, has the build recipe, the sources and
the install. On the device both live in `/sdcard/PdExtraLibs`, which `mother`'s launch line puts on
the path; on the Mac in `~/Library/Pd`, Pd's standard user folder, which every Pd the suite and
`tools/deploy.sh` start gets as `-path` (`CUTIT_PD_LIBS` overrides; the suite empties `HOME`). What
each costs and what is missing on the device: the Organelle's Reference page, *Externals*.

**pdlua 0.12.24, Lua 5.4.7.** Logic goes to Lua where it is clearly simpler than boxes and cords:
the sequencer's rules are the worked example (`ref/module/sequencer.md`).

- **Two files beside the abstraction**: `<name>.lua`, the rules in plain Lua that never call Pd,
  each a function of a state table returning what leaves; and `<name>-lua.pd_lua`, the pdlua class
  that maps messages to those calls and their answers to outlets. The abstraction loads pdlua with
  `[declare -lib pdlua]` and makes `[<name>-lua …]`.
- ⛔ **Never `<name>.pd_lua` for an abstraction's name**: pdlua's loader runs before Pd looks for
  the `.pd`, so it would replace the abstraction everywhere.
- ⛔ **A Lua error must reach `err`, not just the console**: run each rule under `pcall` and send
  `fail <source> lua-<selector>` out of an outlet corded to `[s err]`; and answer an `init` at load
  with a bang, so the abstraction can say `no-lua` when the Lua never loaded (C-12).
- **Test the rules without Pd**: a `test/gate/lua/<name>_test.lua` on `test/gate/lua/lib_test.lua`
  (its tally, and a stand-in for pdlua that loads the class), run by its module's gate through
  `lib_scratch.lua()` with lua.org's Lua 5.4 (`~/.local/bin/lua`; `LUA` overrides).
- **Reload without restarting Pd:** `; pdluax reload <name>-lua` re-runs the class file and the rules
  it reads; objects keep their state.
- pdlua's three load lines are moved to `-verbose` in our build, so the entry points stay silent.
  A stock pdlua, or ELSE's own copy, would print and fail the deploy check.

**ELSE 1.0-0 rc14.** Name its objects with the folder: `[else/knob]`, never bare. Its abstractions
call each other that way, so the folder *holding* `else/` must be on the path, and it is;
`[declare -path else]` does not find it there in 0.57. ⛔ **Never load the `[else]` library binary**
(`-lib else`, `[declare -lib else]`): it prints ~35 lines at every load. On the device:

- ⛔ **21 of its objects print when created under `-nogui`**, which fails the deploy check:
  `knob`, `numbox~`, `popmenu`, `scope~`, `keyboard` and the rest of its GUI objects, which send Tcl
  to a GUI that isn't there, and `del~` and `trig.delay2~`, deprecated. The list is in
  `~/Sites/!reference/pure-data.md`, *pdlua and ELSE*.
- **Missing:** `play.file~`, `sfload`, `sfinfo` (FFmpeg) and the abstractions built on them —
  `player~`, `gran.player~`, `pvoc.player~`, `sample~` — and `circuit~`, `pdlink`, `pdlink~`, `sfz~`
  (C++17, which the device's gcc 5.2 lacks).
- ⚠️ **Too big for 495 MB:** `grain.live~`, `grain.sampler~` and `grain.synth~` take ~72 MB each.
- ⚠️ **CPU on one core:** a reverb costs ~11–14%; `freeze~` at its defaults doesn't fit.
- Every new ELSE object is a dependency the gates exercise only on the Mac's build; check it
  creates on the device too (`device/pd-libs/loadcheck.sh`).

## The rules

Full text and reasoning: `ref/conventions.md`. **Cite a rule by ID from a patch comment** — a `.pd`
comment is the only documentation visible while editing in Pd and it has no link syntax.
`test/gate/docs-check.py` asserts every `C-NN` cited anywhere resolves.

| ID | Rule |
|----|------|
| C-1 | **`$0-` every send, receive, table and array name** inside an abstraction |
| C-2 | **Bare global names only from the allowlist** — `mode` `tempo` `clock` `start`/`stop` `panic` `recover` `param` `err` `disp` `state` `presence`, plus mother's own |
| C-3 | **`[trigger]` on every fan-out**, even when the current order happens to work |
| C-4 | **Never `adc~` / `dac~`** — `[r~ inL]`/`[r~ inR]` in, `[throw~ outL]`/`[throw~ outR]` out |
| C-5 | **One owner per display surface** — `oscOut` / `screenLine*` are `g_oled`'s, `led` is its own. Everything else asks via `disp` |
| C-6 | **Finish assembled messages with `[list trim]`**, and `[list append]` after a `route` |
| C-7 | **Clear optional fields on every message** — `[list split n]` on exactly *n* atoms sends an empty remainder, which a `[symbol]` store refuses |
| C-8 | **`[t b]` in front of anything behind a reject outlet** — a reject carries DATA, not a bang |
| C-9 | **Every `[print]` in a deployed abstraction sits behind `[del 2000]`** — `tools/deploy.sh` gates on output |
| C-10 | **Append boxes at the end of a `.pd`, and move the `#X connect`s with them** |
| C-11 | **Grain timing is audio-domain** — `phasor~` and `vline~`, never `metro` / `line~` |
| C-12 | **Report on `[s err]`** as `<level> <source> <text>` — `info` logs, `warn` draws in compose, `fail` always. Text one symbol ≤ 21 chars |
| C-13 | **No dynamic patching, no `[value]`, no copied subpatches** |
| C-14 | **Edit a `#X text` by replacing the WHOLE LINE** — escaped `\;` is legal inside one, so scanning for "the next `;`" splits the comment |

## Editing a `.pd` file by hand

⛔ **C-14 — a `#X text` cannot be edited by finding "the next `;`".** Pd splits a file into records
on **unescaped** semicolons, and a comment legitimately contains escaped ones (`\;`). A scan stops
mid-comment and the tail becomes a record with no `#X` prefix. **This has broken the patch three
times.** Replace the whole line.

⚠️ **The same trap from the other side: an unescaped `;` TYPED into a comment ends the record.**
`Outlet 1 is the beat bang; outlet 0 is a signal phase` makes the remainder a new record Pd tries to
instantiate — `error: outlet: no such object`. **Escape it as `\;` or rewrite the sentence.** Item
207, and it has happened twice in one session.

⚠️ **A digit followed by a full stop is a FLOAT, and the stop vanishes.** `43.` in a message box's
sentence prints as `43` — Pd parses the atom as the number 43. Cosmetic rather than structural, unlike
the comma, which splits the line into fragments. Item 122.

⛔ **C-10 — `#X connect` names boxes by POSITION IN THE FILE.** Inserting a box mid-file renumbers
every subsequent index and silently invalidates every later connect. Append at the end and move the
connects with it. **This has bitten the project five times.**

Counting records by eye is what causes it. Ask instead:

```sh
python3 test/gate/pd-layout-check.py --boxes "Cut It/u_map.pd"
```

Comments count. `#X declare` does not. Subpatch contents do not, but the `#X restore` line does.

⚠️ **A reject outlet carries the data that failed to match, not a bang** — `route`, `select`,
`moses`, `spigot`. Put `[t b]` in front of anything downstream (C-8).

⚠️ **`[list split n]` on exactly *n* atoms sends an empty remainder**, which a `[symbol]` or `[f]`
store refuses, so a field left off keeps its old value (C-7).

⚠️ **`[list trim]` before `route`** — `route` matches a *selector*, and `[list prepend]`/`[list
append]` produce a `list` selector (C-6).

⚠️ **Pd does not warn about extra creation arguments at all**, 0.49 or 0.57. A wrong arg count loads
in perfect silence, so a clean syntax check proves nothing about arity.

## The gates

**Run these before calling anything done.** All Mac-side; they touch no device.

```sh
python3 test/gate/pd-layout-check.py "Cut It"/*.pd    # after every edit -- PROBLEM = fail
./test/run.sh                                    # ~1 min, every gate in one command
```

⚠️ **Read `run.sh`'s result, do not grep for it.** Exactly one line matches `RESULT:`, and the
exit status is trustworthy. A pattern like `grep -E 'ALL|FAILED'` also matches the per-gate
`--- FAILED:` lines, and a broken patch has been committed that way.

⚠️ **`tools/deploy.sh` gates on OUTPUT, not exit status** — Pd exits 0 even when objects fail to create.
Its check quits at about 735 ms, which is why every deployed `[print]` sits behind `[del 2000]`
(C-9).

⛔ **A gate is not trusted until it has failed.** `state-assert.sh` passed the broken patch 15/15
on its first can-it-fail run. Reintroduce the bug, watch it go red, revert.

## Where to read more

| | |
|---|---|
| `ref/conventions.md` | The rules in full, with reasoning |
| `~/Sites/!reference/pure-data.md` | What Pd itself does — the behavior and the traps the rules work around, measured in 0.49 and marked where 0.57 differs |
| `ref/workflow.md` | How the loop is run — deploy, the by-hand SSH console, how a phase runs |
| `ref/README.md` | How the documentation is organized, and the page schema |
| `ref/device/<name>.md` | How Cut It uses one device; the device itself is on its page in `~/Sites/!reference/` |
| `ref/module/<name>.md` | One instrument concern |
| `AGENTS.md` | Repo layout, working notes, the device itself |
| `!projects/cut-it/` | **What is open** — the repo beside this one. A comment cites a file as `cut-it/<slug>`, a loosie as `cut-it/inbox`; the docs gate resolves both. `plan-v04.md` is the last plan document and is being moved there by hand |

**Off-device development is the default.** Open `Cut It/main-dev.pd` in Pd 0.57 on the Mac and the
whole instrument is there — `u_mother-stub` draws the front panel inline and fakes the knobs, keys,
aux and encoder. Most work should never need the Organelle powered on.

**There is a console, but not the obvious way.** A menu-launched patch runs `-nogui` and its errors
go to tty1. Launch `mother.pd` and `main.pd` together over SSH with output redirected to a file and
you get a real console, including `[print]` taps on any bus. It found a silent bug in Phase 1.
