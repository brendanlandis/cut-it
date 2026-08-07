# Cut It — Pd Conventions

**Moved** to **[ref/conventions.md](ref/conventions.md)**, and the rules now carry stable IDs.

Cite a rule as **`C-7`** rather than by path — a `.pd` comment is the only documentation visible
while editing in Pd, and a link cannot be followed from one. `tools/docs-check.py` asserts that
every `C-NN` cited anywhere resolves to a rule that exists.

| | |
|---|---|
| C-1 | `$0-` every send, receive, table and array name inside an abstraction |
| C-2 | Bare global names only from the allowlist |
| C-3 | `[trigger]` on every fan-out |
| C-4 | Never `adc~` / `dac~` |
| C-5 | One owner per display surface |
| C-6 | Finish assembled messages with `[list trim]` |
| C-7 | Clear optional fields on every message |
| C-8 | `[t b]` in front of anything behind a reject outlet |
| C-9 | Every `[print]` in a deployed abstraction sits behind `[del 2000]` |
| C-10 | Append boxes at the end of a `.pd`, and move the `#X connect`s with them |
| C-11 | Grain timing is audio-domain |
| C-12 | Report failures on `[s err]` |
| C-13 | No dynamic patching, no `[value]`, no copied subpatches |
| C-14 | Edit a `#X text` by replacing the whole line — never scan for the next `;` |

This stub exists because fourteen files — patches and tools — still name `ref-conventions.md`, and
a `.pd` comment has no link syntax. It goes away when those citations become `C-NN`.
