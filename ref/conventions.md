<!-- schema: rules -->
# Cut It — Pd Conventions

How this patch is written: file naming, encapsulation, message discipline, and the handful of
rules that keep a Pd project legible past a few hundred objects.

**These are decisions, not options.** Where a choice was genuinely arguable it is marked
*(judgment call)* with the reasoning, so it can be overruled deliberately rather than drifted
away from.

Companion to [architecture.md](architecture.md) (how the modules compose), [rig.md](rig.md) (the
boxes and cables) and the pages under [device/](device/) (the wire format). Hard constraints — Pd version, plugdata, vanilla-only — are in [AGENTS.md](AGENTS.md).
What Pd itself does, which most of these rules work around, is on its Reference page,
`~/Sites/!reference/pure-data.md`: a rule here says why in a line and points there.

## The rules, in one screen

If you read nothing else here, read this. Each links to its reasoning below.

| ID | Rule | |
|---|---|---|
| **C-1** | **`$0-` every send, receive, table and array name** inside an abstraction | [→](#0--mandatory) |
| **C-2** | **Bare global names only from the allowlist** — `mode` `tempo` `clock` `start`/`stop` `panic` `recover` `param` `err` `disp` `state` `presence`, plus mother's own | [→](#the-global-name-allowlist) |
| **C-3** | **`[trigger]` on every fan-out**, even when the current order happens to work | [→](#trigger-on-every-fan-out) |
| **C-4** | **Never `adc~` / `dac~`** — `[r~ inL]`/`[r~ inR]` in, `[throw~ outL]`/`[throw~ outR]` out | [→](#audio-io--never-adc-never-dac) |
| **C-5** | **One owner per display surface** — `oscOut` / `screenLine*` are `g_oled`'s, `led` is its own. Everything else asks via `disp` | [→](#the-display-bus-and-who-owns-the-screen) |
| **C-6** | **Finish assembled messages with `[list trim]`**, and `[list append]` after a `route` | [→](#four-traps-around-route-every-one-silent) |
| **C-7** | **Clear optional fields on every message** — `[list split n]` on exactly *n* atoms sends an empty remainder, which a `[symbol]` store refuses | [→](#four-traps-around-route-every-one-silent) |
| **C-8** | **`[t b]` in front of anything behind a reject outlet** — a reject carries DATA, not a bang | [→](#four-traps-around-route-every-one-silent) |
| **C-9** | **Every `[print]` in a deployed abstraction sits behind `[del 2000]`** — `tools/deploy.sh` gates on output | [→](#editing-a-pd-file-by-hand) |
| **C-10** | **Append boxes at the end of a `.pd`, and move the `#X connect`s with them** | [→](#editing-a-pd-file-by-hand) |
| **C-11** | **Grain timing is audio-domain** — `phasor~` and `vline~`, never `metro` / `line~` | [→](#timing-and-the-two-domains) |
| **C-12** | **Report on `[s err]`** as `<level> <source> <text>` — `info` logs, `warn` draws in compose, `fail` always. Text one symbol ≤ 21 chars | [→](#errors-must-reach-the-oled--built) |
| **C-13** | **No dynamic patching, no `[value]`, no copied subpatches** | [→](#banned) |
| **C-14** | **Edit a `#X text` by replacing the WHOLE LINE** — escaped `\;` is legal inside one, so scanning for "the next `;`" splits the comment | [→](#editing-a-pd-file-by-hand) |

Prefixes: `e_` effects · `m_` device mapping · `c_` control generation · `g_` display ·
`u_` utilities.

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

Abstraction names are looked up along the same path as externals, and **a built-in always wins
over a file of the same name** (Reference, *A built-in always wins*): a `moses.pd` would never load,
and a `shell.pd` in the patch folder would shadow the real external. So everything is prefixed.

Cut It uses **rjlib's type prefixes** — battle-tested, self-documenting, and they happen to map
cleanly onto this rig's structure:

| Prefix | Holds | Cut It examples |
|---|---|---|
| `e_` | Effects and filters — the signal chain | `e_chop`, `e_pitch`, `e_trem`, `e_verb` |
| `m_` | Mapping: device events → named controls | `m_launchpad`, `m_nano`, `m_organelle` |
| `c_` | Control data generation | `c_clock`, `c_drunk`, `c_sputter` |
| `g_` | Display and GUI | `g_grid`, `g_oled`, `g_led` |
| `u_` | Utilities | `u_map`, `u_tempo`, `u_err` |
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

**Rule C-1.** Cite it by ID from a `.pd` comment, where a link cannot be followed.

**Every `send`, `receive`, `send~`, `receive~`, `table`, `array`, `delwrite~` and `value` name
created inside an abstraction is prefixed `$0-`.** No exceptions outside the global allowlist
below.

`$0` expands to a per-instance unique number, so `$0-grain` is private to one instance. Without
it, two instances of `e_chop` silently share state through a global name — and the failure is
invisible, intermittent, and looks like a DSP bug.

Framing to keep in mind: **`$0` is private, `$1…$n` are public.**

⚠️ **Object box: `$0` and `$1` mean what you expect. Message box: neither does** — there `$1` is
the incoming message's first atom and `$0` is **0**, which is easier to miss because `$0-name` is
everywhere. Measured, and Pd's: Reference, *`$` arguments*. When a message box needs a creation
argument, capture it at load — `[symbol $1]` in an *object* box, banged when needed.

What does work in an object box is composing an argument: `[u_store $1/cut-it-auto.txt]` is how
`u_state` hands each of its two stores a path.

### The global name allowlist

**Rule C-2.** Cite it by ID from a `.pd` comment, where a link cannot be followed.

Bare (unprefixed) names are reserved for genuinely application-wide state. **This list is
exhaustive — adding to it is a deliberate change to this file, not a local decision.**

| Name | Carries | Source |
|---|---|---|
| `mode` | **`<class> <name>`** — `compose`/`perform` then the sub-mode, e.g. `compose mode-1` | ✅ `u_map`, from the nano's transport row |
| `tempo` | **master reference** BPM, as a float | any → `u_tempo` |
| `clock` | **master reference** beat bang | `u_tempo` |
| `start` / `stop` | transport, carried as a **bang** | any → `u_tempo` |
| `panic` | all-notes-off, clear all state | any |
| `recover` | a **bang** — panic, then reload the patch. Panic's second tier | `u_map` → `u_init` |
| `param` | `<name> <value>` — a control **changed** | any `m_` → `u_map` |
| `err` | `<level> <source> <text>`, level ∈ `warn` `fail` | any → `u_err` |
| `disp` | display requests: `<name> <value> [unit]` | any → `g_oled`, `g_led`, `g_grid`, `u_net` |
| `state` | persistence, **three selectors** — see below | any ↔ `u_state` |
| `presence` | device presence, **six selectors** — see below | any ↔ `u_present` |

**Four of these are request buses, not publications.** `tempo`, `start`/`stop`, `mode` and
`param` are written by whoever has something to say and *consumed* by one owner, exactly as `err`
and `disp` are — so the Source column names the consumer. `u_tempo` owns the BPM value and the
transport state; it does not own the right to change them. **`clock` is the exception**: only
`u_tempo` writes it, because it is a publication of something already decided.

**`param` is a control changing; `disp` is a request to show it**, and an `m_` layer publishes a
control on `param` only. **The row a control draws is `u_map`'s alone**, because it is the only file
that knows what the control means — item 317. **Why there are two buses rather than one** is on
[architecture.md](architecture.md) under *Request buses and publications*.

Two consequences bind whoever writes an `m_` layer, and both are deliberate:

- ⛔ **Names on `param` are physical, never functional** — `slider-1`, `og-knob-1`, `xport-2`. What
  a control *does* is not knowable at the `m_` layer and must not be guessed there.
- **`u_map` is the only file allowed to turn a `param` name into anything else**, and since v0.3 it
  does it with **a table plus a hardcoded allowlist of destinations**.

  ⛔ **The table never names a `[send]`** — it names a destination that must exist as a literal
  argument on a `route` box, feeding a handler you can see. A data-driven send could write any
  global name with no evidence of it on the canvas, which defeats an allowlist that is audited by
  reading. **That guard is the whole of what makes a table acceptable, and skipping it costs
  nothing visible**: nothing fails and no test notices.

  Everything else about the map — the row format, the destinations, the divisor, the boot races —
  is on [map.md](module/map.md).

✅ **`mode` is driven from the Launchpad's top row**, CC 91–96, which `g_grid` lights as the mode
lamps — the only device Pd can light, so the state is visible rather than remembered. It carries
**two atoms**, a class and a sub-mode, which is why `u_err`'s `[route compose perform]` works
untouched: `route` matches the selector and its branches feed message boxes, which fire on
anything. `u_map` seeds one at load behind a spigot that any real mode closes, so the seed fills a
silence rather than setting a default.

**`tempo` and `clock` are the master reference, not "the clock".** See *Poly-tempo* below —
this distinction is load-bearing and easy to lose.

### `state` — the persistence bus

**One name, three selectors, disjoint per side**, so the whole protocol fits in one allowlist entry
with no loop. Contributors `[route save restore]`; `u_state` routes `put`.

**A contributor names its own key and declares its own policy**, which is what lets an abstraction
written long after `u_state` persist itself with no change to `u_state`. `auto` is a running value;
`manual` is a committed take you could abandon by not saving.

⚠️ **A `manual` answer MUST be synchronous**, and it is the one rule a contributor can break
invisibly — the failure is a short file rather than an error.

The message table, the two stores, the file format and the rest of the traps are on
[state.md](module/state.md).

### `presence` — the device-presence bus

**One name, six selectors, disjoint per side**, the same shape as `state` and for the same reason.
An `m_` layer registers itself once at load with `expect <src> <kind>`; `u_present` broadcasts
`tick`; a `c_presence` inside the `m_` answers with `lost <src>` or `back <src>` on the transition
only. A **passive** layer — one that cannot be polled — publishes `seen <src>` instead. **The sixth
is `re-wire`**, the phone's button, and it is the only selector written by a file that owns no
device — see [phone.md](device/phone.md).

**Self-registration is what makes it extensible**: an `m_` written long after `u_present` is covered
with no change to `u_present`, exactly as a `state` contributor is.

⛔ **`<src>` is the ABSTRACTION's name and never the device's** — `m_nano`, not "nanoKONTROL". That
is the `m_` boundary, and it adds nothing new to the world because `err`'s `source` field already
carries the same names across the same boundary.

The kinds, the manufacturer bytes, the bounded re-wire and its arithmetic are on
[presence.md](module/presence.md).

**Owned by `mother.pd`** — not ours to rename, and reserved: every name it sends or receives,
enumerated from the file itself on the Organelle's Reference page
(`~/Sites/!reference/critter-guitari-organelle-1.md`, under *The `mother.pd` interface*).

**`[r quitting]` is the shutdown hook, and it is the only one** (Pd 0.49 has no `closebang`). Its
budget is mother's ~100 ms before Pd quits (same page, under *`quitting`, and how long a patch
has*): enough for a nine-byte SysEx, not for anything clever.

⛔ **`quitting` fires on every PATCH LOAD, not only on shutdown, and that is what makes menu
probes safe.** Swapping patches from the menu gives the outgoing patch the same ~100 ms to hand
hardware back that a shutdown does, and Pd is then killed and relaunched rather than reused (item
252, same page).

**One abstraction is allowed to send on the `mother.pd` names: `u_mother-stub`.** It exists to
impersonate `mother.pd` when the patch runs on the Mac, where `mother.pd` does not exist, so
sending on reserved names *is* its function. It is instantiated by `main-dev.pd` only —
`main.pd` never touches it, so the hardware never sees a second source for `knob1`–`knob4`.
**This is the only exception, and adding another is a change to this file.**

Everything else is `$0-`, or a wire.

### Output devices are WIRED from `u_map`, not given a bus

⛔ **No bare global name carries a sounding note**, and none is being added. `m_volca` and `m_404`
are told what to play on a **cord** from `u_map`, one outlet per output device, carrying a
selector-prefixed message. The reasoning and the two rejected alternatives are on
[architecture.md](architecture.md).

⚠️ **A device layer's `route` reject is a REAL error and goes to `[s err]`** — the opposite of
`u_map`'s reject, where an unmapped control is normal and silent.

### Poly-tempo

⛔ **`clock` being on the allowlist does not mean there is one tempo.** Cut It runs multiple
simultaneous tempi, and **nothing downstream may assume the global `clock` is its clock** — a part
that needs a beat instantiates its own `c_clock`. What that commits you to when writing one is on
[tempo.md](module/tempo.md) under *`u_tempo` is a reference, `c_clock` is a clock*.

---

## Wires vs send/receive

Wires are traceable; `[s]`/`[r]` are action-at-a-distance and Pd gives you no tooling to find
the other end.

- **Signal flow is always wires.** The four-stage chain is visibly a chain.
- **`$0-` sends inside an abstraction** are fine for avoiding cord spaghetti locally.
- **Global sends only from the allowlist.**

The failure mode to avoid is a patch where any control can affect anything, with no visible
path. That is unrestricted global mutable state with extra steps.

### GUI binding is the one carve-out

**Every iemgui carries `send` and `receive` symbols in its creation arguments, and a control
surface is allowed to use them instead of a wire.** A slider whose `send` is `knob1` needs no
cord and no `[s knob1]` object.

*(judgment call)* The rule above protects patch **logic**. A control binding to the name it
represents is not action-at-a-distance — the name *is* the control's meaning, and it is visible
in the object's properties dialog. Forcing wires onto a panel produces a diagram nobody can
read, which is the very thing the rule exists to prevent.

Two limits stay hard:

- **Nothing in the signal or control path may do this.** A `[t]` between two processing stages
  is still a wire. This applies to GUI objects binding to their own name, and to nothing else.
- The names in question are `mother.pd`'s reserved ones, so it lives inside `u_mother-stub` —
  still the one sanctioned exception, unchanged.

The payoff is not tidiness. **Graph-on-parent draws no object or message boxes and no cords**
(Reference), so binding by name rather than by cord is exactly what lets `u_mother-stub`'s panel
appear inline on `main-dev.pd`.

---

## `[trigger]` on every fan-out

**Rule C-3.** Cite it by ID from a `.pd` comment, where a link cannot be followed.

When one outlet connects to several destinations, they fire in **creation order**, which the patch
does not show (Reference, *Order*).

**Every fan-out goes through `[t]`.** `[t b f]`, `[t f f]`, `[t b b]`. Even when the current
order happens to work.

This is the single highest-value convention in Pd. Treat an unmediated fan-out as a bug during
review, the same way you'd treat a race condition.

Related discipline: **the leftmost inlet is hot**, everything else is cold. When an object needs
two values before it acts, the cold ones are set first — which means they come from the
*rightmost* outlets of the `[t]` feeding them.

---

## Timing and the two domains

**Rule C-11.** Cite it by ID from a `.pd` comment, where a link cannot be followed.

**Grain timing is audio-domain, always.** Pd's message clock moves a 64-sample block at a time
(~1.45 ms; Reference), which is ~20% of a 256th note at 120 BPM. Grain clocks come from `phasor~`;
envelopes from `vline~`. Never `metro` or `line~` at grain rate.

⚠️ **`threshold~` behind a `phasor~` takes debounces of 0.** Its debounce is counted in blocks, so
any debounce caps the pulse train it makes — 344 Hz at zero, about 170 Hz at 2 ms (measured, and
Pd's: Reference) — and 2 ms is a clock that looks fine at every ordinary tempo and loses pulses
above about 430 BPM. A `phasor~` cannot bounce.

**Normalise time units to Hz at the edge.** BPM-mode and MS-mode are a *units* choice, not two
engines: `bpm/60 × subdivisions` or `1000/ms`, then one `phasor~`. Do the conversion once, at
the parameter, not throughout the patch.

---

## Audio I/O — never `adc~`, never `dac~`

**Rule C-4.** Cite it by ID from a `.pd` comment, where a link cannot be followed.

**`mother.pd` owns the sound card.** A patch that reaches for `adc~` or `dac~` is going around it.
The interface is four names — `[r~ inL]` / `[r~ inR]` in, `[throw~ outL]` / `[throw~ outR]` out.

⛔ **`adc~` in a patch happens to work; `dac~` is a real bug**: it bypasses the volume knob and
mother's limiter, and nothing reports it. **And mother turns DSP on**, so a patch must not. Both,
and mother's whole audio path, are on the Organelle's Reference page
(`~/Sites/!reference/critter-guitari-organelle-1.md`, under *Audio*).

The I/O contract, the measured level scale and the rest are on [audio.md](module/audio.md).

---

## The display bus, and who owns the screen

**Rule C-5.** Cite it by ID from a `.pd` comment, where a link cannot be followed.

⛔ **Exactly one abstraction may write any display surface.** `g_oled` owns `oscOut` and
`screenLine1`–`5`; `g_grid` owns the Launchpad's LEDs; `g_led` owns the aux button. Everything else
asks by sending to `disp` and **does not know or care how it is drawn** — including `u_err`, which
filters and forwards rather than drawing.

**Callers send semantics, never layout.** `led running`, not a colour. `modal wiring`, not a font
size.

⚠️ **A new selector on `disp` costs one `route` argument in every consumer that has a fallthrough**,
because everything unrecognised is a parameter by definition. Today that is two: `g_oled` and
`u_net`.

The message format, the reserved names, the layer model and every trap around them are on
[display.md](module/display.md).

### Four traps around `route`, every one silent

**Rule C-6, C-7 and C-8.** Cite it by ID from a `.pd` comment, where a link cannot be followed.

All four cost real debugging time on this project. Why each happens is Pd's, measured in 0.49:
Reference, *Selectors, lists and `route`*.

| You have | You get | Fix |
|---|---|---|
| `[list prepend foo]` → `route foo` | no match, silent | `[list trim]` before sending |
| `route foo` → `[symbol]` / `[t l l]` | `expected 'symbol'` / `can only convert 's'` | `[list append]` after route |
| `[list split n]` on exactly *n* atoms | an **empty** remainder, which a `[symbol]` or `[f]` store refuses — the old value stays | write the field unconditionally first |
| a **reject** outlet feeding something that wants a bang | the rejected **data** arrives instead | `[t b]` in between |

**1 — sending.** Without the `[list trim]`, every message assembled with `[list …]` leaves
`route`'s rightmost outlet, usually into nothing, and the display just shows zero.

**2 — receiving.** `status v0.3-ready` arrives as selector `v0.3-ready`. This is why every branch
out of `g_oled`'s `route` begins with `[list append]`.

**3 — the nasty one**, because nothing on the screen says anything went wrong. It is what made
`chop-size 43 %` followed by `grain 12` draw as `grain 12 %`. **Any optional field must be cleared
on every message, not written on some.**

**4 — not `route`-specific, but the same shape**, and every instance here was silent: a `[select …]`
reject overwrote a stored value through an `[f]`'s hot inlet, and `moses`'s left outlet passed
`text search`'s `-1` into `text set` as a line number. **Anything behind such an outlet that expects
a bang gets a `[t b]` in front of it.**

**Rate limiting belongs to the display, not the caller.** Senders push whenever they have
something to say; the display redraws on its own clock. ✅ And because every layer holds
**state** rather than a queue of draw calls, this needs no coalescing logic at all — 877 `disp`
messages in five seconds produced exactly 51 frames, the drawn value advancing by 20 each time.
The guaranteed trailing edge falls out for free.

---

## Instancing: `[clone]`

Use `[clone]` for anything needing N copies — sample slots, voices, per-stage duplicates — before
hand-rolling allocation.

`[clone e_chop 4]` creates four instances, each with its own `$0`. That it is in 0.49, and how a
message reaches one instance or all of them, are Pd's: Reference, *`[clone]` is in 0.49*.

---

## State and persistence

- **Runtime state lives in objects** — `[f ]`, `[i ]`, arrays, `[text]`. There is nowhere else for it
  to live.
- **`u_state` is the only file that decides when any of it is written.** The `state` bus, the two
  policies, the file format and every trap in them are on [state.md](module/state.md).
- ⛔ **Nothing writes into the patch folder.** The instrument's data lives in `/sdcard/cut-it-state/`,
  outside it, so a deploy cannot touch it. A **relative** `[text write]` mutates the deployed patch
  immediately — see `~/Sites/!reference/critter-guitari-organelle-1.md` under *Saving*.

---

## Development workflow

**Moved.** The deploy loop, the by-hand SSH console and how a phase runs are on
[workflow.md](workflow.md). This page is the Pd rules; that one is how you run them.

## Errors must reach the OLED

**Rule C-12.** Cite it by ID from a `.pd` comment, where a link cannot be followed.

**The Organelle runs Pd with `-nogui`, so an error you cannot see is a silent failure** — and Pd's
failure mode for a wrong message is to print and continue.

⛔ **Any abstraction reports via `[s err]` as `<level> <source> <text>`** — source a symbol naming
the abstraction, text **one symbol of ≤ 21 characters**. Use a **message box**, which already
carries the level as its selector; anything built with `[list prepend]` needs `[list trim]` (C-6).

**Three levels, and they differ only in what the SCREEN does.** Every one of them is logged:
`u_err`'s logfile tap hangs off the trigger *above* the mode route, so the bus is unfiltered
whatever the display is doing.

| Level | Logged | Drawn | For |
|-------|--------|-------|-----|
| `info` | yes | **never** | Diagnostic detail — a thing that happened, not a thing to act on |
| `warn` | yes | compose only | Something is wrong and the operator may want to know |
| `fail` | yes | **always** | Something is wrong and the operator must know |

⛔ **`info` is not a quieter `warn` — it is the level for detail that would otherwise drown the
screen.** `u_present` forks `wire.sh` up to eight times per recovery episode and every one belongs
in the log; nine alerts on a 21-character display mid-set does not.

⚠️ **A level that is none of the three is a real error**, printed on `err-BAD-LEVEL` rather than
swallowed — a typo must not silently disable a report.

`u_err` filters by mode, never draws, and leaves the bus itself unfiltered — the design and its
reasoning are on [architecture.md](architecture.md).

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

### Editing a `.pd` file by hand

**Rules C-9, C-10 and C-14.** Cite them by ID from a `.pd` comment, where a link cannot be followed.

⛔ **C-14 — a `#X text` record cannot be edited by scanning for the next `;`**: a comment can hold
an escaped `\;`, so the scan stops in the middle of it and the tail becomes a record with no `#X`
prefix.

**Fix:** replace the whole line. `test/gate/pd-layout-check.py` reports
`MALFORMED RECORD -- does not start with '#'` on the signature, so the fault is named rather than
showing up as a canvas-size complaint.

The format's traps are Pd's: Reference, *The `.pd` file*. What each one asks of an edit here:

- **A `#X connect` names boxes by position, so append at the end**, honoring `#N canvas` /
  `#X restore` nesting: a top-level object goes before the first connect *at depth 1*. If a box
  really must be replaced, replace it in place so no index moves. `test/gate/pd-layout-check.py`
  reports the damage as *"indices are probably off by one"*.
- **Records are read in order, so when you append boxes, the connects move down with them** — a
  connect above its target fails at load, and Pd still exits 0.
- **Keep commas and semicolons out of any assembled string** — a message box splits on them however
  the file escapes them, and a `PASS IF` line in a bench is the usual casualty.
- ⚠️ **AN UNESCAPED `;` ENDS A RECORD — INCLUDING A COMMENT**, and in a message box `; pd quit`
  takes every following `#X connect` with it, so the patch loads, runs, and does nothing at all —
  indistinguishable from a negative result. **Write `\;`, or use a dash; it reads the same and
  cannot break anything.**

**Every `[print]` in a deployed abstraction sits behind `[del 2000]`.** `tools/deploy.sh` gates on
*output*, so a diagnostic that fires at `loadbang` breaks the deploy; behind a delay the syntax
check quits before it fires while the by-hand console still sees it.

✅ **Measured: `-send "pd quit"` returns in 735 ms**, with an undelayed control print appearing and
a delayed one not. ⚠️ **This covers more than `[print]`.** Pd's *own* file errors print too — a
`[text read]` of a missing file, a `[text write]` to a missing directory (Reference, item 143). **Anything
that touches a file that may not exist belongs behind the same delay**, which is why the state
restore is staged rather than run at `loadbang`.

**Never open or save any of this in plugdata** — see [AGENTS.md](AGENTS.md).

---

## Banned

**Rule C-13.** Cite it by ID from a `.pd` comment, where a link cannot be followed.

| Don't | Why |
|---|---|
| **Dynamic patching** (messages to the canvas that create objects) | Fragile, unreadable, undebuggable without a console. `[clone]` covers the legitimate cases. |
| **Bare global sends outside the allowlist** | Invisible coupling |
| **Unmediated fan-out** | Undefined order in practice |
| **`[value]` / `[v]` for anything but the allowlist** | Global mutable state |
| **Copying a subpatch to reuse it** | Two codebases, silent divergence |
| **`adc~` / `dac~` in a deployed patch** | `mother.pd` owns the sound card; `dac~` bypasses the volume knob and the limiter — see *Audio I/O* |
| **`oscOut` / `screenLine*` / `led` outside their display abstraction** | Two writers, one surface |
| **Saving from plugdata** | Corrupts the file format for Pd 0.49 — see [AGENTS.md](AGENTS.md) |
| **Objects newer than Pd 0.49** | The device can never be upgraded — see [AGENTS.md](AGENTS.md) |

---

## Where the abstractions go

The decomposition that follows from all of the above — which abstraction exists and what each
holds — is [architecture.md](architecture.md), and the order the remaining ones
get built in is [plan-v04.md](plan-v04.md)'s *The shape of v0.3*.

⛔ **The one boundary that constrains how everything else may be written: nothing in `e_*` may know
that a nanoKONTROL exists.** Why it is the expensive one, and what it costs to get wrong, are on
[architecture.md](architecture.md) under *The `m_` boundary is the expensive thing*.

### `mac-stubs/` is a sibling of the patch folder, and cannot move into it

⛔ **Do not tidy `mac-stubs/` into `Cut It/`.** Two independent reasons, either one fatal:

1. `Cut It/u_err.pd` and `Cut It/u_init.pd` carry `#X declare -path ../mac-stubs`, and
   `tools/deploy.sh` passes `-path mac-stubs` from the repo root. **The relative path is the
   mechanism** — it only resolves from outside.
2. Its own header records the trap: **a file named `shell.pd` reaching the patch folder SHADOWS
   the real external, and MIDI wiring silently stops happening.** Pd resolves a class from the
   patch directory before it reaches the externals path, so the stub would win on the device — and
   nothing would report it, because a do-nothing `[shell]` creates cleanly and returns nothing.

**It has exactly one member and always will.** Everything else the patch needs is a built-in
class, and a built-in cannot be shadowed by a file at all — which is why `test/stubs/` exists as a
separate mechanism with a different shape: a gate swaps *those* in by rewriting object boxes inside
a scratch copy, because there is no path trick that would work. **One directory per mechanism, and
the two mechanisms are not interchangeable.**
