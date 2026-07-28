# Cut It — Pd Conventions

How this patch is written: file naming, encapsulation, message discipline, and the handful of
rules that keep a Pd project legible past a few hundred objects.

**These are decisions, not options.** Where a choice was genuinely arguable it is marked
*(judgment call)* with the reasoning, so it can be overruled deliberately rather than drifted
away from.

Companion to [plan-software.md](plan-software.md) (what the instrument does),
[plan-hardware.md](plan-hardware.md) (the rig) and [plan-midi.md](plan-midi.md) (the wire
format). Hard constraints — Pd version, plugdata, vanilla-only — are in [CLAUDE.md](CLAUDE.md).

---

## The mental model

Pd's **abstraction is this project's component**: a `.pd` file on the search path, instantiated
by typing its name in an object box.

| Component concept | Pd |
|---|---|
| Component | Abstraction — a `.pd` file |
| Props | Creation arguments — `$1`, `$2` **in object boxes** |
| Public interface | `[inlet]` / `[outlet]`, `[inlet~]` / `[outlet~]` |
| Module-private scope | **`$0`** |
| Rendering N of something | `[clone]` |
| Event bus | `[send]` / `[receive]` |
| Component's own view | Graph-on-Parent |

The analogy breaks in five places, and each one causes real bugs:

1. **No return values.** Everything is a push. "Fetch a value" is a cold-inlet store plus a
   bang, never a call.
2. **No local variables.** `[f ]` with a cold inlet *is* the variable. `$0` scopes *names*, not
   values.
3. **Execution is eager, synchronous, depth-first, right-to-left.** Not reactive. A message
   runs its entire subtree to completion before the next sibling fires.
4. **Two domains.** Message objects are event-driven; signal (`~`) objects run every 64-sample
   block regardless. They are separately scheduled graphs.
5. **The patch is static.** Dynamic patching exists but is banned here — see *Banned* below.

---

## File naming

Abstraction names occupy a **global namespace and shadow built-in objects**. A file named
`filter.pd` redefines `filter` for the whole patch. So everything is prefixed.

Cut It uses **rjlib's type prefixes** — battle-tested, self-documenting, and they happen to map
cleanly onto this rig's structure:

| Prefix | Holds | Cut It examples |
|---|---|---|
| `e_` | Effects and filters — the signal chain | `e_chop`, `e_pitch`, `e_trem`, `e_verb` |
| `m_` | Mapping: device events → parameters | `m_launchpad`, `m_nano`, `m_keys` |
| `c_` | Control data generation | `c_grainclock`, `c_drunk`, `c_sputter` |
| `g_` | Display and GUI | `g_grid`, `g_oled`, `g_err` |
| `u_` | Utilities | `u_scale`, `u_tempo`, `u_err` |
| `s_` | Sound sources | *(unused — Cut It generates no sound of its own)* |

*(judgment call)* rjlib's scheme was chosen over a project prefix like `ci-` because the type
letter earns its place every time you read a patch, whereas a project prefix only pays off if
these abstractions ever leave the repo — which they won't.

`main.pd` keeps its name; the Organelle requires it as the entry point.

**One abstraction per file, named for what it is.** No `utils.pd` grab-bags.

---

## Abstraction or subpatch

| Use | When |
|---|---|
| **Abstraction** (`e_chop.pd`) | Instantiated more than once, **or** it is a named concept in the design |
| **Subpatch** (`[pd voice-alloc]`) | Purely visual folding *inside* one abstraction |

**Never reuse by copying a subpatch.** A subpatch is saved inside its parent — two copies are
two independent codebases that will diverge silently. Anything you'd copy is an abstraction.

The second half of the abstraction rule matters as much as the first: `e_verb` gets its own
file even if instantiated once, because "the reverb stage" is a thing the design talks about,
and a file boundary is where the design and the code stay aligned.

---

## `$0` — mandatory

**Every `send`, `receive`, `send~`, `receive~`, `table`, `array`, `delwrite~` and `value` name
created inside an abstraction is prefixed `$0-`.** No exceptions outside the global allowlist
below.

`$0` expands to a per-instance unique number, so `$0-grain` is private to one instance. Without
it, two instances of `e_chop` silently share state through a global name — and the failure is
invisible, intermittent, and looks like a DSP bug.

Framing to keep in mind: **`$0` is private, `$1…$n` are public.**

**The `$1` trap:** in an *object* box `$1` is a creation argument, resolved once at load. In a
*message* box `$1` is the first element of the incoming message, resolved per message. Same
glyph, unrelated meaning. When a message box needs a creation argument, capture it into the
patch at load time and store it.

### The global name allowlist

Bare (unprefixed) names are reserved for genuinely application-wide state. **This list is
exhaustive — adding to it is a deliberate change to this file, not a local decision.**

| Name | Carries | Source |
|---|---|---|
| `mode` | compose / perform, and sub-mode | nano transport, Pd ch 18 |
| `tempo` | BPM, as a float | `u_tempo` |
| `clock` | beat bang | `u_tempo` |
| `start` / `stop` | transport | nano transport |
| `panic` | all-notes-off, clear all state | any |
| `err` | error and status reporting → OLED | any |
| `screenLine1`…`screenLine4` | OLED text | owned by `mother.pd` — not ours to rename |

Everything else is `$0-`, or a wire.

---

## Wires vs send/receive

Wires are traceable; `[s]`/`[r]` are action-at-a-distance and Pd gives you no tooling to find
the other end.

- **Signal flow is always wires.** The four-stage chain is visibly a chain.
- **`$0-` sends inside an abstraction** are fine for avoiding cord spaghetti locally.
- **Global sends only from the allowlist.**

The failure mode to avoid is a patch where any control can affect anything, with no visible
path. That is unrestricted global mutable state with extra steps.

---

## `[trigger]` on every fan-out

When one outlet connects to several destinations, firing order is **creation order** — invisible
in the patch and unrecoverable from reading it.

**Every fan-out goes through `[t]`.** `[t b f]`, `[t f f]`, `[t b b]`. Even when the current
order happens to work.

This is the single highest-value convention in Pd. Treat an unmediated fan-out as a bug during
review, the same way you'd treat a race condition.

Related discipline: **the leftmost inlet is hot**, everything else is cold. When an object needs
two values before it acts, the cold ones are set first — which means they come from the
*rightmost* outlets of the `[t]` feeding them.

---

## Timing and the two domains

**Grain timing is audio-domain, always.** Pd's message clock is quantised to a 64-sample block
(~1.45 ms), which is ~20% of a 256th note at 120 BPM. Grain clocks come from `phasor~`;
envelopes from `vline~`. Never `metro` or `line~` at grain rate.

**Signal-domain feedback requires a block boundary** — `[send~]`/`[receive~]` or
`[delwrite~]`/`[delread~]`. A direct signal loop is a DSP-sort error, not a sound.

**Normalise time units to Hz at the edge.** BPM-mode and MS-mode are a *units* choice, not two
engines: `bpm/60 × subdivisions` or `1000/ms`, then one `phasor~`. Do the conversion once, at
the parameter, not throughout the patch.

---

## Instancing: `[clone]`

Use `[clone]` for anything needing N copies — sample slots, voices, per-stage duplicates — before
hand-rolling allocation.

`[clone e_chop 4]` creates four instances; messages are routed by prepending the instance index,
and `all` broadcasts. Each instance still gets its own `$0`.

**Verified available:** `[clone]` ships from Pd **0.47** onward. Checked by listing
`doc/5.reference` in the `pure-data/pure-data` repo at tags `0.47-0` and `0.49-0` —
`clone-help.pd` is present in both.

---

## State and persistence

- **Runtime state lives in objects** — `[f ]`, `[i ]`, arrays, `[text]`. There is nowhere else
  for it to live.
- **Per-instance persistence: `[savestate]`.** Saves a parameter list into the parent patch, so
  different instances of an abstraction restore different values.

  **Verified available in 0.49-0** — `savestate-help.pd` is present at tag `0.49-0` and absent
  at `0.47-0`. A widely-repeated forum claim that `[savestate]` arrived in 0.49.1 is **wrong**;
  do not let it talk you out of using it.
- **Patterns and presets are plain text files** in the patch folder, via `[text define]` +
  `[text write]`. Git-diffable and editable outside Pd. This was already decided in
  [plan-software.md](plan-software.md) and stands.
- **Capture everything in one device-agnostic event format** — `time, note, velocity, duration` —
  so nothing downstream cares whether a pattern came from the Launchpad, the keyboard or the
  404.

---

## Development workflow

Two devices, neither with a usable console, both reachable over the network.

```
edit in repo  →  syntax check on the Mac  →  push to device  →  reload
```

**Syntax-check before every deploy.** Pd 0.49-1 is installed locally, the same version the
Organelle runs:

```sh
/Applications/Pd-0.49-1.app/Contents/Resources/bin/pd \
    -nogui -noaudio -send "pd quit" path/to/main.pd
```

Silence means it parsed and every object instantiated. This catches the entire class of
load-time errors — misspelled objects, malformed iemgui lines, bad connections — that would
otherwise vanish into tty1 on a device with no console. **It costs a second and it is not
optional.**

| Target | Deploy |
|---|---|
| Organelle | `scp` to `/sdcard/Patches/!/<name>/main.pd`, then Storage → Reload |
| iPhone (PdParty) | `curl -T <file> http://<phone>:9000/<scene>/_main.pd` over WebDAV |

Neither needs a cable. See [plan-display.md](plan-display.md) for addresses and ports.

**What the check cannot catch** is runtime behaviour — wrong message types, silent OSC
failures, logic errors. That is what the error bus below and the PdParty remote console are
for.

## Errors must reach the OLED

**The Organelle runs Pd with `-nogui`. There is no console.** Patch errors go to stdout on
tty1, which VNC does not show. An error you cannot see is a silent failure, and Pd's failure
mode for a wrong message is to print and continue.

*(judgment call)* **This is treated as an architecture requirement, not a debugging
inconvenience.** Build `u_err` / `g_err` as part of the first infrastructure pass, before there
is anything to debug:

- Any abstraction reports via `[s err]` with a symbol identifying itself and the condition.
- A single `g_err` owns one OLED line and displays the most recent message.
- It costs almost nothing early and is painful to retrofit across every abstraction later.

This does not catch Pd's *own* runtime errors — those still go to tty1. It catches the ones we
raise, which is the majority of what will actually go wrong.

---

## Patch layout

Layout is not cosmetic in Pd; it is the only structural documentation the language has.

- **Signal flows top to bottom, control left to right.** Where it can't, comment saying so.
- **Don't cross cords.** A crossed cord is a refactor signal.
- **Every abstraction opens with a comment block** stating creation arguments, inlets and
  outlets, in order. This replaces per-abstraction help patches *(judgment call — help patches
  are a library convention, and this is an instrument, not a library)*.
- Keep abstractions small enough to read without scrolling.

**`.pd` files store absolute coordinates**, so moving a box is a real diff. Two consequences:
small abstractions diff better than large canvases, and gratuitous rearranging costs review
effort. Don't tidy and change behaviour in the same commit.

---

## Banned

| Don't | Why |
|---|---|
| **Dynamic patching** (messages to the canvas that create objects) | Fragile, unreadable, undebuggable without a console. `[clone]` covers the legitimate cases. |
| **Bare global sends outside the allowlist** | Invisible coupling |
| **Unmediated fan-out** | Undefined order in practice |
| **`[value]` / `[v]` for anything but the allowlist** | Global mutable state |
| **Copying a subpatch to reuse it** | Two codebases, silent divergence |
| **Saving from plugdata** | Corrupts the file format for Pd 0.49 — see [CLAUDE.md](CLAUDE.md) |
| **Objects newer than Pd 0.49** | The device can never be upgraded — see [CLAUDE.md](CLAUDE.md) |

---

## Proposed abstraction boundaries

A starting decomposition, following the above. Not yet built — revise freely as the rewrite
proceeds, but keep the shape.

```
main.pd                 entry point; wiring only, no logic
  u_wire                aconnect calls via [shell] at load (see tools/self-wire.pd)
  u_tempo               tempo → clock, MIDI clock out, start/stop
  u_err                 error bus → OLED

  m_nano                Pd ch 17/18 → parameters and mode
  m_launchpad           Pd ch 1 → pads, pressure; owns Programmer Mode SysEx
  m_404                 Pd ch 33 → pad/pattern capture
  m_keys                Organelle keyboard → notes or filter control, by mode

  e_chop                sampler / chop            ┐
  e_pitch               filter and pitch          │ the four stages,
  e_trem                tremolo                   │ right to left
  e_verb                reverb / freeze           ┘

  c_grainclock          phasor~-derived grain timing
  c_drunk               drunkenness / sputter modulation

  g_grid                Launchpad LED state
  g_oled                OLED display
```

The `m_` layer is the load-bearing idea: **device mapping is separated from everything it
controls.** Nothing in `e_*` knows a nanoKONTROL exists. That is what makes the compose/perform
mode split tractable, since the same surfaces mean different things in each mode — and it is
the one boundary that is genuinely expensive to retrofit.
