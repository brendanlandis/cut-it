<!-- schema: rules -->
# Cut It — Pd Conventions

How this patch is written: file naming, encapsulation, message discipline, and the handful of
rules that keep a Pd project legible past a few hundred objects.

**These are decisions, not options.** Where a choice was genuinely arguable it is marked
*(judgment call)* with the reasoning, so it can be overruled deliberately rather than drifted
away from.

Companion to [architecture.md](architecture.md) (how the modules compose), [rig.md](rig.md) (the
boxes and cables) and the pages under [device/](device/) (the wire format). Hard constraints — Pd version, plugdata, vanilla-only — are in [CLAUDE.md](CLAUDE.md).

## The rules, in one screen

If you read nothing else here, read this. Each links to its reasoning below.

| ID | Rule | |
|---|---|---|
| **C-1** | **`$0-` every send, receive, table and array name** inside an abstraction | [→](#0--mandatory) |
| **C-2** | **Bare global names only from the allowlist** — `mode` `tempo` `clock` `start`/`stop` `panic` `param` `err` `disp` `state` `presence`, plus mother's own | [→](#the-global-name-allowlist) |
| **C-3** | **`[trigger]` on every fan-out**, even when the current order happens to work | [→](#trigger-on-every-fan-out) |
| **C-4** | **Never `adc~` / `dac~`** — `[r~ inL]`/`[r~ inR]` in, `[throw~ outL]`/`[throw~ outR]` out | [→](#audio-io--never-adc-never-dac) |
| **C-5** | **One owner per display surface** — `oscOut` / `screenLine*` are `g_oled`'s, `led` is its own. Everything else asks via `disp` | [→](#the-display-bus-and-who-owns-the-screen) |
| **C-6** | **Finish assembled messages with `[list trim]`**, and `[list append]` after a `route` | [→](#four-traps-around-route-every-one-silent) |
| **C-7** | **Clear optional fields on every message** — `[list split n]` on exactly *n* atoms never fires | [→](#four-traps-around-route-every-one-silent) |
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

Abstraction names occupy a **global namespace and shadow built-in objects**. A file named
`filter.pd` redefines `filter` for the whole patch. So everything is prefixed.

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

**The `$1` trap:** in an *object* box `$1` is a creation argument, resolved once at load. In a
*message* box `$1` is the first element of the incoming message, resolved per message. Same
glyph, unrelated meaning. When a message box needs a creation argument, capture it into the
patch at load time and store it — `[symbol $1]` in an *object* box, banged when needed.

⚠️ **And `$0` has the same trap, which is easier to miss because `$0-name` is everywhere.** In a
*message* box `$0` is **not** the patch id — it resolves to **0**. A `write -wave … $0-buf`
message silently addressed a table called `0-buf`, every write failed with `no such table`, and
because a failed write is *fast* the timing it reported looked excellent. Only a
`FRAMES-WRITTEN: 0` control made it visible. **Object box: `$0` and `$1` mean what you expect.
Message box: neither does.** Measured while building Phase 8.

✅ **What DOES work in an object box is composing an argument**: `[u_store $1/cut-it-auto.txt]`
expands correctly, which is how `u_state` hands each of its two stores a path.

### `polytouchin`'s outlets are value, note, channel

⚠️ **Not the note-first order the name suggests**, and the odd one out — `[ctlin]` is channel,
controller, value (item 23) and `[notein]` is channel, velocity, pitch. Measured, item 86.

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
| `param` | `<name> <value>` — a control **changed** | any `m_` → `u_map` |
| `err` | `<level> <source> <text>`, level ∈ `warn` `fail` | any → `u_err` |
| `disp` | display requests: `<name> <value> [unit]` | any → `g_oled`, `g_led`, `g_grid`, `u_net` |
| `state` | persistence, **three selectors** — see below | any ↔ `u_state` |
| `presence` | device presence, **four selectors** — see below | any ↔ `u_present` |

**Four of these are request buses, not publications.** `tempo`, `start`/`stop`, `mode` and
`param` are written by whoever has something to say and *consumed* by one owner, exactly as `err`
and `disp` are — so the Source column names the consumer. `u_tempo` owns the BPM value and the
transport state; it does not own the right to change them. **`clock` is the exception**: only
`u_tempo` writes it, because it is a publication of something already decided.

**`param` is a control changing; `disp` is a request to show it**, and an `m_` layer publishes to
both off one `[t a a]`, action first and report second. **Why there are two buses rather than one**
is on [architecture.md](architecture.md) under *Request buses and publications*.

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

✅ **`mode` got its driver in Phase 6**: the nanoKONTROL's six transport keys, shown as a lit
lamp on the Launchpad's top row — the only device Pd can light, so the state is visible rather
than remembered. It carries **two atoms**, a class and a sub-mode, which is why `u_err`'s
`[route compose perform]` still works untouched: `route` matches the selector and its branches
feed message boxes, which fire on anything. `u_map` seeds one at load behind a spigot that any
real mode closes, so the seed fills a silence rather than setting a default.

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

**One name, four selectors, disjoint per side**, the same shape as `state` and for the same reason.
An `m_` layer registers itself once at load with `expect <src> <kind>`; `u_present` broadcasts
`tick`; a `c_presence` inside the `m_` answers with `lost <src>` or `back <src>` on the transition
only. A **passive** layer — one that cannot be polled — publishes `seen <src>` instead.

**Self-registration is what makes it extensible**: an `m_` written long after `u_present` is covered
with no change to `u_present`, exactly as a `state` contributor is.

⛔ **`<src>` is the ABSTRACTION's name and never the device's** — `m_nano`, not "nanoKONTROL". That
is the `m_` boundary, and it adds nothing new to the world because `err`'s `source` field already
carries the same names across the same boundary.

The kinds, the manufacturer bytes, the bounded re-wire and its arithmetic are on
[presence.md](module/presence.md).

**Owned by `mother.pd`** — not ours to rename, and reserved:

| Direction | Names |
|---|---|
| To the patch | `knob1`–`knob4` (+`Raw`/`Override`), `notes`, `notesRaw`, `enc`, `encbut`, `aux`, `auxRaw`, `vol`, `exp`/`expRaw`/`expOverride`, `fs`/`fsRaw`, `saveState`, `recallState`, `oscIn`, **`quitting`** |
| From the patch | `screenLine1`–`screenLine5`, `led`, `goHome`, `oscIn`, `oscOut`, `enableSubMenu`, `footSwitchPolarity`, **`midiInGate`** / `midiOutGate` / `midiCh` / `midiOutCh` |

✅ Enumerated from `mother.pd` itself rather than from documentation — every `[s]` and `[r]` in
the file.

**`quitting` is the shutdown hook, and it is the only one.** `mother.pd` sends it on
`/quitpd`, then waits **100 ms** before `; pd quit`. `killpatch.sh` then SIGTERMs after 120 ms.
That is the entire budget for putting hardware back in a sane state — enough for a nine-byte
SysEx, not for anything clever. **Pd 0.49 has no `closebang`** (checked: `closebang` and
`initbang` both fail to create), so `[r quitting]` is it.

⛔ **`quitting` fires on every PATCH LOAD, not only on shutdown, and that is what makes menu
probes safe.** `/loadPatch` calls `MainMenu::runPatch`, which runs `killpatch.sh` *before* launching
anything — and that script's first line is `oscsend localhost 4000 /quitpd i 1`, straight into the
send above. So swapping patches from the menu gives the outgoing patch the same ~100 ms to hand
hardware back that a shutdown does, and **Pd is then killed and relaunched** rather than reused
(item 252). Read from `mother.pd`, `MainMenu.cpp` and `killpatch.sh` on the device, not inferred.

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

The payoff is not tidiness. **Graph-on-parent renders iemguis and atom boxes and nothing
else** — no message boxes, no object boxes, no comments — so removing the cords is exactly what
lets `u_mother-stub`'s panel appear inline on `main-dev.pd`. ✅ `$0` expands in iemgui `send` and
`receive` names, verified in 0.49 with two instances of a test abstraction rather than assumed.

---

## `[trigger]` on every fan-out

**Rule C-3.** Cite it by ID from a `.pd` comment, where a link cannot be followed.

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

**Rule C-11.** Cite it by ID from a `.pd` comment, where a link cannot be followed.

**Grain timing is audio-domain, always.** Pd's message clock is quantised to a 64-sample block
(~1.45 ms), which is ~20% of a 256th note at 120 BPM. Grain clocks come from `phasor~`;
envelopes from `vline~`. Never `metro` or `line~` at grain rate.

⚠️ **`threshold~`'s debounce is counted in DSP blocks, not milliseconds.** It decrements its dead
time once per block, so *any* non-zero debounce costs a full 1.45 ms per state change — and a
trigger/rest pair costs two. This is what caps a `phasor~`-derived pulse train: **at zero debounce
the limit is two blocks per cycle, measured at 344 Hz = 44100/64/2**; at 2 ms it drops to about
170 Hz, silently. ✅ Found the hard way in Phase 5, where the clock lost pulses above 430 BPM and
looked fine at every tempo anyone had tried. A `phasor~` cannot bounce, so set the debounces to 0.

**Signal-domain feedback requires a block boundary** — `[send~]`/`[receive~]` or
`[delwrite~]`/`[delread~]`. A direct signal loop is a DSP-sort error, not a sound.

**Normalise time units to Hz at the edge.** BPM-mode and MS-mode are a *units* choice, not two
engines: `bpm/60 × subdivisions` or `1000/ms`, then one `phasor~`. Do the conversion once, at
the parameter, not throughout the patch.

---

## Audio I/O — never `adc~`, never `dac~`

**Rule C-4.** Cite it by ID from a `.pd` comment, where a link cannot be followed.

**`mother.pd` owns the sound card.** A patch that reaches for `adc~` or `dac~` is going around it.
The interface is four names — `[r~ inL]` / `[r~ inR]` in, `[throw~ outL]` / `[throw~ outR]` out.

⛔ **`adc~` in a patch happens to work; `dac~` is a real bug.** The output path applies the volume
knob and a `clip~ -1 1` limiter, and writing to `dac~` bypasses both — the knob stops working and
the patch can clip the converter. Nothing reports it.

**mother enables DSP.** `pd init` fires `; pd dsp 1` 200 ms after load. A patch must not.

The full chain, the measured level scale and the rest are on [audio.md](module/audio.md).

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

All four cost real debugging time on this project. The first two are the same underlying
fact — Pd distinguishes a message's **selector** from its **arguments**, and the `list` objects
move an atom across that boundary.

| You have | You get | Fix |
|---|---|---|
| `[list prepend foo]` → `route foo` | no match, silent | `[list trim]` before sending |
| `route foo` → `[symbol]` / `[t l l]` | `expected 'symbol'` / `can only convert 's'` | `[list append]` after route |
| `[list split n]` on exactly *n* atoms | right outlet **never fires** — the old value stays | write the field unconditionally first |
| a **reject** outlet feeding something that wants a bang | the rejected **data** arrives instead | `[t b]` in between |

**1 — sending.** `[route in-l]` matches a message whose *selector* is `in-l`; it does not match
a `list` whose first element is. `[list prepend in-l]` produces the second kind, so finish with
`[list trim]`. Without it every message leaves `route`'s rightmost outlet, usually into nothing,
and the display just shows zero. A message box typed `in-l 42 dB` is already the right shape;
anything assembled with `[list …]` is not.

**2 — receiving.** Measured in 0.49, and **wider than this document once claimed** — the old
wording said the trap applied only when the remainder was a single symbol. The real rule: when
`route` matches, **the remainder is emitted as a message whenever its first atom is a symbol**,
that symbol becoming the selector. So `status v0.3-ready` arrives as selector `v0.3-ready`, and
`alert warn u_init x` as selector `warn` with two arguments; only a remainder starting with a
**float** is really a list. This is why every branch out of `g_oled`'s `route` begins with
`[list append]`.

**3 — the nasty one**, because it is a silent non-event rather than a wrong value. It is what
makes `chop-size 43 %` followed by `grain 12` draw as `grain 12 %`. **Any optional field must
be cleared on every message, not written on some.**

**4 — not `route`-specific, but the same shape.** A **reject, left, or non-matching outlet
carries the data that failed to match**, not a bang — `route`, `select`, `moses` and `spigot`
all do this. Four separate instances in this repo's history, every one silent: `[select 1 2 3 4 5 6]`'s
reject overwrote a stored CC through an `[f]`'s hot inlet, and `moses`'s left outlet passed
`text search`'s `-1` into `text set` as a line number. **Anything behind such an outlet that
expects a bang gets a `[t b]` in front of it.**

**Rate limiting belongs to the display, not the caller.** Senders push whenever they have
something to say; the display redraws on its own clock. ✅ And because every layer holds
**state** rather than a queue of draw calls, this needs no coalescing logic at all — 877 `disp`
messages in five seconds produced exactly 51 frames, the drawn value advancing by 20 each time.
The guaranteed trailing edge falls out for free.

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

- **Runtime state lives in objects** — `[f ]`, `[i ]`, arrays, `[text]`. There is nowhere else for it
  to live.
- **`u_state` is the only file that decides when any of it is written.** The `state` bus, the two
  policies, the file format and every trap in them are on [state.md](module/state.md).
- ⛔ **Nothing writes into the patch folder.** The instrument's data lives in `/sdcard/cut-it-state/`,
  outside it, so a deploy cannot touch it. A **relative** `[text write]` mutates the deployed patch
  immediately — see [organelle.md](device/organelle.md) under *Saving*.

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
in the log; nine alerts on a 21-character display mid-set does not. It was built as `warn` first and
`oled-assert.sh` caught it drawing over a modal inside one run.

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

⛔ **C-14 — a `#X text` record cannot be edited by scanning for the next `;`.** Pd splits a file
into records on **unescaped** semicolons, and a comment legitimately contains escaped ones (`\;`).
Anything that rewrites a comment by finding "the next `;`" stops in the middle of it, and the tail
becomes a record with no `#X` prefix. **This has broken the patch three times.**

**Fix:** replace the whole line. `test/gate/pd-layout-check.py` now reports
`MALFORMED RECORD -- does not start with '#'` on the signature, so the fault is named rather than
showing up as a canvas-size complaint.

The format is a flat, ordered record list, and three of its properties are traps. All three have
bitten this project, most of them more than once.

- **A `#X connect` names boxes by INDEX, and the index is position in the file.** Inserting or
  deleting *anything* — including a comment — shifts every later box and silently rewires the
  patch. **Append at the end**, honouring `#N canvas` / `#X restore` nesting: a top-level object
  goes before the first connect *at depth 1*. If a box really must be replaced, replace it in
  place so no index moves. `test/gate/pd-layout-check.py` reports the damage as *"indices are
  probably off by one"*, which is how it was caught each time.
- **Records are processed strictly in order**, so a `#X connect` that appears *before* its target
  box is defined fails at load with `connection failed` — and Pd still exits 0. When you append
  boxes, the connects have to move down with them.
- **A comma or semicolon in a message box is a message separator**, whatever the file does with
  escaping. `\,` satisfies the *parser*; the message box still splits on the comma atom. Keep
  both out of any assembled string — a `PASS IF` line in a bench is the usual casualty.
- ⚠️ **AND AN UNESCAPED `;` ENDS A RECORD — INCLUDING A COMMENT.** This bit twice in one session,
  both times in ordinary prose: `Outlet 1 is the beat bang; outlet 0 is a signal phase` **ends the
  `#X text` at the semicolon** and turns the remainder into a new record, which Pd then tries to
  instantiate — `error: outlet: no such object`. ⚠️ **In a message box it is worse**: `; pd quit`
  ends the box early and **takes every following `#X connect` with it**, so the patch loads, runs,
  and does nothing at all — indistinguishable from a negative result. **Write `\;`, or use a dash;
  it reads the same and cannot break anything.**

**Every `[print]` in a deployed abstraction sits behind `[del 2000]`.** `tools/deploy.sh` gates on
*output*, so a diagnostic that fires at `loadbang` breaks the deploy; behind a delay the syntax
check quits before it fires while the by-hand console still sees it.

✅ **Measured: `-send "pd quit"` returns in 735 ms**, with an undelayed control print appearing and
a delayed one not. ⚠️ **This covers more than `[print]`.** Pd's *own* file errors go to the same
stream — `[text read]` of a missing file prints three lines, and `[text write]` to a missing
directory prints `write failed` rather than failing silently, which a plan in this repo asserted
it did. **Anything that touches a file that may not exist belongs behind the same delay**, which
is why the state restore is staged rather than run at `loadbang`.
item 143.

**Never open or save any of this in plugdata** — see [CLAUDE.md](CLAUDE.md).

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
| **Saving from plugdata** | Corrupts the file format for Pd 0.49 — see [CLAUDE.md](CLAUDE.md) |
| **Objects newer than Pd 0.49** | The device can never be upgraded — see [CLAUDE.md](CLAUDE.md) |

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
