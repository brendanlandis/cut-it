# Cut It — Pd Conventions

How this patch is written: file naming, encapsulation, message discipline, and the handful of
rules that keep a Pd project legible past a few hundred objects.

**These are decisions, not options.** Where a choice was genuinely arguable it is marked
*(judgment call)* with the reasoning, so it can be overruled deliberately rather than drifted
away from.

Companion to [ref-software.md](ref-software.md) (what the instrument does),
[ref-hardware.md](ref-hardware.md) (the rig) and [ref-midi.md](ref-midi.md) (the wire
format). Hard constraints — Pd version, plugdata, vanilla-only — are in [CLAUDE.md](CLAUDE.md).

## The rules, in one screen

If you read nothing else here, read this. Each links to its reasoning below.

| Rule | |
|---|---|
| **`$0-` every send, receive, table and array name** inside an abstraction | [→](#0--mandatory) |
| **Bare global names only from the allowlist** — `mode` `tempo` `clock` `start`/`stop` `panic` `param` `err` `disp` `state`, plus mother's own | [→](#the-global-name-allowlist) |
| **`[trigger]` on every fan-out**, even when the current order happens to work | [→](#trigger-on-every-fan-out) |
| **Never `adc~` / `dac~`** — `[r~ inL]`/`[r~ inR]` in, `[throw~ outL]`/`[throw~ outR]` out | [→](#audio-io--never-adc-never-dac) |
| **One owner per display surface** — `oscOut` / `screenLine*` are `g_oled`'s, `led` is its own. Everything else asks via `disp` | [→](#the-display-bus-and-who-owns-the-screen) |
| **Finish assembled messages with `[list trim]`**, and `[list append]` after a `route` | [→](#four-traps-around-route-every-one-silent) |
| **Clear optional fields on every message** — `[list split n]` on exactly *n* atoms never fires | [→](#four-traps-around-route-every-one-silent) |
| **`[t b]` in front of anything behind a reject outlet** — a reject carries DATA, not a bang | [→](#four-traps-around-route-every-one-silent) |
| **Every `[print]` in a deployed abstraction sits behind `[del 2000]`** — `deploy.sh` gates on output | [→](#editing-a-pd-file-by-hand) |
| **Append boxes at the end of a `.pd`, and move the `#X connect`s with them** | [→](#editing-a-pd-file-by-hand) |
| **Grain timing is audio-domain** — `phasor~` and `vline~`, never `metro` / `line~` | [→](#timing-and-the-two-domains) |
| **Report failures on `[s err]`** as `<level> <source> <text>`, text one symbol ≤ 21 chars | [→](#errors-must-reach-the-oled--built) |
| **No dynamic patching, no `[value]`, no copied subpatches** | [→](#banned) |

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

### The global name allowlist

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

**Four of these are request buses, not publications.** `tempo`, `start`/`stop`, `mode` and
`param` are written by whoever has something to say and *consumed* by one owner, exactly as `err`
and `disp` are — so the Source column names the consumer. `u_tempo` owns the BPM value and the
transport state; it does not own the right to change them. **`clock` is the exception**: only
`u_tempo` writes it, because it is a publication of something already decided.

**`param` is a control changing; `disp` is a request to show it.** ✅ Added in Phase 5, and the
distinction is the whole reason for a second bus: a device publishes what its surface *did*,
and `u_map` — the only consumer — decides what that *means*. `m_nano` and `m_organelle` both
publish to `param` and `disp` off one `[t a a]`, action first and report second. That duplicates
the data where teaching `g_oled` to listen on `param` would not, and it was the right trade:
not touching a hardware-verified display file beat saving a send.

Two consequences worth stating, because both are deliberate:

- **Names on `param` are physical, never functional** — `slider-1`, `og-knob-1`, `xport-2`. What
  a control *does* is not knowable at the `m_` layer and must not be guessed there.
- **`u_map` is the only file allowed to turn a `param` name into anything else**, and since v0.3 it
  does it with **a table plus a hardcoded allowlist of destinations** — `Cut It/cut-it-map.txt`,
  four atoms per row, `<mode> <control> <dest> <arg>`. The old one-branch-per-mapping rule was
  written with a "revisit past about ten mappings" condition, and 42 controls × six modes is far
  past it.

  ⛔ **The guard is the whole of what makes a table acceptable, and it is not optional.** A
  data-driven `[send]` could write any global name with no evidence of it on the canvas, which
  defeats an allowlist that is audited by reading. So **the table never names a send** — it names a
  destination that must exist as a **literal argument on a `route` box**, feeding a handler you can
  see. The set of things a control can reach is still the set of boxes you can read. **A row naming
  a destination that is not on that route goes to `err` as `unknown-dest` and emits nothing** —
  proven by test, and it is the only failure this design can have that nothing else would catch.
  ⚠️ **Skip the guard and the property is gone silently**: nothing fails and no test notices.

  ⚠️ **The table is code, not state.** It is not persisted through `u_state` — nothing rewrites it
  at runtime, so persisting it would only store a constant, and a restore could silently override
  the shipped file. Live re-assignment is v0.4 and brings its own persistence.

✅ **`mode` got its driver in Phase 6**: the nanoKONTROL's six transport keys, shown as a lit
lamp on the Launchpad's top row — the only device Pd can light, so the state is visible rather
than remembered. It carries **two atoms**, a class and a sub-mode, which is why `u_err`'s
`[route compose perform]` still works untouched: `route` matches the selector and its branches
feed message boxes, which fire on anything. `u_map` seeds one at load behind a spigot that any
real mode closes, so the seed fills a silence rather than setting a default.

**`tempo` and `clock` are the master reference, not "the clock".** See *Poly-tempo* below —
this distinction is load-bearing and easy to lose.

### `state` — the persistence bus ✅ Phase 8

**One name, three selectors, disjoint per side**, so the whole protocol fits in one allowlist
entry with no loop. Contributors `[route save restore]`; `u_state` routes `put`.

| Direction | Message | Meaning |
|---|---|---|
| contributor → `u_state` | `put auto <key> <atoms…>` | store now; flushed on a timer |
| `u_state` → all | `save` | broadcast at a commit — **answer now** |
| contributor → `u_state` | `put manual <key> <atoms…>` | the answer to a `save` |
| `u_state` → all | `restore <key> <atoms…>` | replayed at load, line by line |

**A contributor names its own key and declares its own policy**, which is what lets an
abstraction written long after `u_state` persist itself with no change to `u_state`. `auto` is a
running value; `manual` is a committed take you could abandon by not saving.

⚠️ **A `manual` answer MUST be synchronous.** Pd is eager, synchronous and depth-first, so by the
time the `save` broadcast returns, every honest answer is already stored — which is why the write
sits on the *left* outlet of the trigger and needs no settle timer. **A contributor answering from
behind a `[del]` is silently absent from the file**, and the failure is a short file rather than an
error. `tools/phase8-assert.sh` asserts this directly with a deliberately-late contributor,
because a rule nothing tests is a rule that quietly stops being true.

⚠️ **`u_state` must never write a file it has not yet read.** The auto flush is armed *by the
restore*, not by a `loadbang`. The first build armed it at 3 s while `u_init` restores at ~3.5 s,
so every boot overwrote the previous session with its own defaults — and the file looked entirely
plausible throughout. Found on the Mac before it reached hardware; item 152.

**Two files, because they have different lifecycles** — the same split, for the same reason, as
`u_err`'s `.cur` and `.log`. `text write` rewrites the whole file every time, so an auto flush
must not be able to corrupt a committed take.

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

**One abstraction is allowed to send on the `mother.pd` names: `u_mother-stub`.** It exists to
impersonate `mother.pd` when the patch runs on the Mac, where `mother.pd` does not exist, so
sending on reserved names *is* its function. It is instantiated by `main-dev.pd` only —
`main.pd` never touches it, so the hardware never sees a second source for `knob1`–`knob4`.
**This is the only exception, and adding another is a change to this file.**

Everything else is `$0-`, or a wire.

### Output devices are WIRED from `u_map`, not given a bus ✅ decided in v0.3

**`m_404` and `m_volca` are the project's first *output* device layers, and they run against the
grain of every `m_` file before them.** The existing three are input mappers — device events become
named controls on `param`, which `u_map` consumes. These two are *told what to play*.

⛔ **No bus carries that, and none was added.** `param` is device→map, `disp` is display requests,
and a sounding note is neither. **`u_map` grows one outlet per output device**, wired in `u_root` —
**one device, one cord.**

**The message is SELECTOR-PREFIXED, and the device layer routes it** — `notes 48 100 200`,
`cc 41 64`, `program 20`, `pad 23 96`. This is the same shape `state` uses to carry three selectors
on one name, and `disp` to carry every surface's vocabulary on one: **a device that learns a new
capability costs one `route` argument inside that device** and nothing anywhere else — not `u_map`'s
outlet count, not `u_root`'s cords, not this file.

⚠️ **The device's `route` reject is a REAL error and goes to `[s err]`** — the opposite of `u_map`'s
reject, where an unmapped control is normal and silent. An unrecognised selector means `u_map` and
the device disagree about the interface, and for an output-only device there is no other way to find
out: it transmits nothing, so a message that goes nowhere is indistinguishable from one that worked.

*(judgment call)* **One outlet per device *inlet* was considered and rejected.** It makes `u_map`'s
outlet count the sum of every device's capabilities — three for the Volca alone — and so crosses the
four-device threshold below with **two** devices. It also puts the fan-out on `u_root`'s canvas
rather than inside the file that owns the device.

*(judgment call)* A `voice` bus was considered and rejected. It would scale without touching
`u_root` — the way `disp` serves four surfaces — but **the allowlist is audited by reading**, and
what is carried here is the signal path rather than a request to show something. `u_root` already
sets the precedent: the only wires on that canvas come out of `u_init`, because the boot *order* is
`u_init`'s while the *action* belongs to the file at the other end. Same shape — `u_map` owns the
decision, the device owns the emission, and the cord between them is worth being able to see.

**Revisit if the output-device count passes about four**, where `u_root`'s canvas stops being the
clearer option. Same threshold reasoning as `u_map`'s route branches.

### Poly-tempo

Cut It runs **multiple simultaneous tempi**. Sequencers and samplers may deviate from master —
a different BPM, or ms-based timing instead of beat-based — and different parts of a drum
sequence may run different time signatures. The allowlist above must not be read as implying
one tempo and one beat.

- **`tempo` and `clock` are the master reference**: what MIDI clock out is derived from, and
  what parts *may* choose to follow. Nothing is obliged to.
- **Timing is per-instance.** Each grain clock, sequencer and sampler owns a `c_clock` instance
  with its own rate, optionally slaved to master by a ratio. **Nothing downstream may assume
  the global `clock` is its clock.**
- **Time signature is a `c_clock` concern** — bar length, accent pattern — not a global.
- *Normalise BPM and ms to Hz at the edge, feed one `phasor~`* generalises cleanly: N clocks is
  N `phasor~` objects, and ms-based versus beat-based parts stop being a special case.

**MIDI clock carries exactly one tempo**, so the SP-404 and Volca always follow master.
Poly-tempo is internal-only for anything leaving the box — which reinforces rather than
contradicts the "Pd sequences everything, timing rides in note events" decision in
[ref-software.md](ref-software.md).

**So `u_tempo` must be a master reference *plus* an instantiable `c_clock`, never a singleton.**
The cost of getting that wrong is tracked as a risk in [plan-v03.md](plan-v03.md).

---

## Wires vs send/receive

Wires are traceable; `[s]`/`[r]` are action-at-a-distance and Pd gives you no tooling to find
the other end.

- **Signal flow is always wires.** The four-stage chain is visibly a chain.
- **`$0-` sends inside an abstraction** are fine for avoiding cord spaghetti locally.
- **Global sends only from the allowlist.**

The failure mode to avoid is a patch where any control can affect anything, with no visible
path. That is unrestricted global mutable state with extra steps.

### GUI binding is the one carve-out ✅

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

**`mother.pd` owns the sound card.** A patch that reaches for `adc~` or `dac~` is going around
it. The interface is four names:

| Patch uses | Carries |
|---|---|
| `[r~ inL]` `[r~ inR]` | the two inputs — `inL` is the **tip**, `inR` the ring |
| `[throw~ outL]` `[throw~ outR]` | everything the patch wants heard |

✅ Read off the device from `mother.pd`'s `pd audioIO`, and cross-checked against **every**
stock effect in `/sdcard/Patches/Effects/` — they all use exactly this.

```
mother:  [adc~] ─→ [s~ inL] [s~ inR]
patch:   [r~ inL] [r~ inR] ─→ … ─→ [throw~ outL] [throw~ outR]
mother:  [catch~ outL/outR] ─→ [*~ vol²] ← [lop~ 5] ─→ [clip~ -1 1] ─→ [dac~]
```

**`adc~` in a patch happens to work; `dac~` is a real bug.** The output path applies the volume
knob (a **square law**, smoothed at 5 Hz) and a `clip~ -1 1` limiter. Writing to `dac~` bypasses
both — the volume knob stops working and the patch can clip the converter. `throw~`/`catch~`
also sums, so several stages can feed the output without a mixer.

**mother enables DSP.** `pd init` fires `; pd dsp 1` 200 ms after load. A patch must not.

**mother drives the VU meter**, from `inL`, `inR` and the *post-volume* outputs, via
`/oled/vumeter`. A patch never sends it. See [ref-display.md](ref-display.md) for why the
info bar is turned off anyway.

---

## The display bus, and who owns the screen

**Exactly one abstraction may send on `oscOut` and `screenLine1`–`5`.** ✅ That is `g_oled`.
Everything else asks for a display by sending to `disp` and does not know or care how it is
drawn — **including `u_err`, which filters and forwards onto `disp` rather than drawing.**
The Phase 4 plan originally had `u_err` writing to the ALERT buffer itself; where the two
disagreed, this rule won ([ref-build-log.md](ref-build-log.md)). Two writers, one screen.

**The same rule covers the aux button LED, and ✅ Phase 5 built it.** It is a display surface, so
it gets one owner — `g_led` — and callers send semantics rather than a colour: `led running` on
`disp`, never a number. `led` is `mother.pd`'s own name and is reserved below; the point is that
exactly one abstraction may write it. See [ref-display.md](ref-display.md) for the states.

⚠️ **`led` had to be added to `g_oled`'s `route` as well**, matched and left unconnected.
Everything `g_oled` does not recognise is a parameter by definition, so without a branch there
every LED request would have drawn as a nonsense parameter row called `led`. **A second display
surface on the same bus costs one route argument in the first one** — cheap, but not free.

✅ **The third surface arrived in Phase 6 and cost exactly the same two lines**: `grid` appended
to that `route` and the reject connection moved from outlet 7 to 8. The price is now known and it
is flat, which is the argument for keeping every surface on one bus — the dev panel's screen log
records all three interleaved, stamped with one frame number, so an interaction that spans the
OLED, the aux LED and the pads reads as a single sequence.

✅ **The fourth surface arrived in Phase 7 and cost nothing at all**, which breaks the pattern
above rather than continuing it. `u_net` — the phone — **owns no selector on `disp`**. It
subscribes, routes the reserved names into nothing, and forwards the rest; so `g_oled`'s `route`
is untouched and no reject connection moved. **The flat two-line price is the cost of a surface
with its own vocabulary, not the cost of a surface.** A consumer that mirrors the bus is free,
and that is the cheaper shape to reach for when the thing being added is a *readout* rather than
a device with commands of its own.

⚠️ **A mirror still has to know the reserved names.** `u_net`'s `route` lists all eight and
leaves six unconnected, for the same reason `g_oled` had to learn `led`: everything unrecognised
is a parameter *by definition*, so a selector with no branch falls out of the reject and is
forwarded as a nonsense parameter. Adding a selector to `disp` therefore means visiting every
consumer that has a fallthrough — which is now two.

**The `disp` message is `<name> <value> [unit]`, with the name as the *selector*.**

### The reserved names, and where a parameter comes from

`g_oled` routes six selectors. **Everything else is, by definition, a parameter** — there is no
registration step, and `m_nano` in Phase 4 needs no change to the display to show a new control.

| Selector | Carries | Layer |
|---|---|---|
| `in-l` `in-r` | `<dB>` from `u_level` | home |
| `status` | one symbol, the footer status | home |
| `modal` | one symbol — sticky until cleared | modal |
| `modal-off` | nothing | clears modal |
| `alert` | `<level> <source> <text>` — only `u_err` sends this | alert |
| `led` | one symbol, a **state** — `off` `stopped` `running` `panic` | *not the OLED at all* |
| `grid` | the Launchpad's own vocabulary — `grid modal <palette>`, `grid modal-off` | *not the OLED at all* |
| *anything else* | `<value> [unit]` | param |

*(judgment call)* Reserved-names-plus-fallthrough was chosen over tagging each message with its
layer, because ref-display.md's settled contract is that callers "send semantics, never
layout". The cost is that a mistyped `disp` name becomes a nonsense parameter on screen rather
than an error — which is the better failure, since you can see it.

**`modal` and `alert` text is ONE symbol**, and error text is ≤ 21 characters. `gPrintln` does
not wrap, 16px fits about ten characters across 128 px, and a message box has a fixed typetag.
Write `launchpad-silent`, not `launchpad silent`.

### Four traps around `route`, every one silent ✅

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
that symbol becoming the selector. So `status v0.2-ready` arrives as selector `v0.2-ready`, and
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

- **Runtime state lives in objects** — `[f ]`, `[i ]`, arrays, `[text]`. There is nowhere else
  for it to live.
- **Per-instance persistence: `[savestate]`.** Saves a parameter list into the parent patch, so
  different instances of an abstraction restore different values.

  **Verified available in 0.49-0** — `savestate-help.pd` is present at tag `0.49-0` and absent
  at `0.47-0`. A widely-repeated forum claim that `[savestate]` arrived in 0.49.1 is **wrong**;
  do not let it talk you out of using it. ⚠️ **Phase 8 evaluated it and did not use it** (item
  145): it writes into the **parent patch file** and needs a `menusave` that nothing on the
  device triggers. Orthogonal to the `state` bus rather than an alternative to it.
- **Patterns and presets are plain text files**, via `[text define]` + `[text write]` —
  git-diffable and editable outside Pd. ⚠️ **But NOT in the patch folder**, which is what an
  earlier version of this section said. ✅ Phase 8 put them in **`/sdcard/cut-it-state/`**,
  outside it, so `deploy.sh`, `deploy.sh --clean` and a power cycle cannot touch them;
  `tools/fetch-state.sh` is the other half of that bargain and copies them back into the repo.
  **`u_state` is the only file that decides when any of it is written** — see *`state` — the
  persistence bus* above.
- **The Organelle's own save mechanism is NOT how the instrument's data is delivered**, and
  knowing what it *does* do still matters, because `saveState` is what triggers the `manual`
  commit and because it is why `knobs.txt` appears. ✅ Verified end to end on the device —
  **`Storage → Save`** runs `save-patch.sh`, which:

  1. send OSC `/saveState 1` to Pd on port 4000 — arriving in the patch as `[r saveState]`
  2. **sleep** to let the patch write whatever it wants into **`/tmp/state/`**
  3. `cp -r /tmp/state/*` — everything written lands in the patch folder

  ⚠️ **`Storage` is a TOP-LEVEL menu, not a System submenu.** There is no Save under System, and
  a doc that said so cost a wasted trip to the device — [plan-tests.md](plan-tests.md) item 136.

  ⚠️ **The budget is 250 ms, not 500** — `save-patch.sh` sleeps `.5` but `save-new-patch.sh`
  sleeps `.25`. Item 135. ✅ **And it is now irrelevant to Cut It**: `u_state` writes straight to
  `/sdcard` with an **absolute** path, so nothing it does has to finish inside mother's sleep.
  The number still binds anything that writes into `/tmp/state/` and relies on the copy — which
  today is only `knobs.txt`, and mother writes that itself.

  ⚠️ **`saveState` arrives as a BANG, not as `1`.** `mother.pd` routes the OSC message through a
  `[t b b b]`, so the float is discarded — a `[route 1]` or `[select 1]` on it never fires. Item 137.

  On load the patch folder is copied to `/tmp/patch/`, so **write to `/tmp/state/`, read from
  `/tmp/patch/`**. ✅ `/tmp/state/` already exists — it is created *and cleared* at patch load.
  ⚠️ `/tmp` is **tmpfs**; the SD card is only touched by mother's `cp`, after the sleep. A
  2000-line write costs **~16 ms** either way, because the cost is Pd's serialisation rather than
  the storage. Item 141.

  ⚠️ **`/tmp/patch` is a SYMLINK to the patch folder**, and it is Pd's working directory — so a
  **relative** `[text write]` bypasses `/tmp/state` and the copy entirely and mutates the deployed
  patch immediately. Item 140.

  ✅ `mother.pd` uses this for the four knob positions (`knobs.txt`) — **which means every Save
  creates one**, so a patch cannot opt out by shipping without it. Item 139.

  ⛔ **`Storage → Save New` is DROPPED and is not part of this design.** It duplicates the entire
  patch folder under a numbered name, making preset variants separate menu entries — the wrong
  paradigm here, where a preset is a **record inside the store**. Dropping it deleted the whole
  `/tmp/curpatchname` / `! 2` / top-level-variant cluster unasked, and `deploy.sh` was not
  modified. Recorded so it is not rediscovered as an option: [plan-v03.md](plan-v03.md) *Deliberately
  deferred*, and item 144 for what it actually does.
- **Capture everything in one device-agnostic event format** — `time, note, velocity, duration` —
  so nothing downstream cares whether a pattern came from the Launchpad, the keyboard or the
  404.

---

## Development workflow

Two devices, neither with a usable console, both reachable over the network.

**Most work happens on the Mac, with the Organelle switched off.** Open `Cut It/main-dev.pd` in
Pd 0.49: `u_mother-stub` supplies `knob1`–`knob4`, `vol`, `notes`, `aux`, `enc` and `encbut` as
GUI controls, and previews everything the patch writes to `screenLine1`–`5` and `oscOut`. It
shows *what* is drawn, not *where* — pixel-accurate OLED rendering is deliberately out of
scope. Reach for the hardware when the thing you are testing is the hardware.

### `./deploy.sh` — the whole loop, one command

```
edit in repo  →  syntax check  →  scp  →  reload patch list  →  load the patch
```

No walking to the device, no Storage → Reload, no selecting from the menu.

| Env | Effect |
|---|---|
| `--clean` | wipe the remote copy first |
| `NOCHECK=1` | skip the syntax check |
| `NORELOAD=1` | skip refreshing the patch list (which uses `/reloadNoRemount` — see below) |
| `NOLOAD=1` | push but leave the running patch alone |
| `HOST=` `DEST=` `PD=` | target, destination, Pd binary |

**The syntax check is built in and blocking.** Pd 0.49-1 on the Mac is the same version the
Organelle runs:

```sh
/Applications/Pd-0.49-1.app/Contents/Resources/bin/pd \
    -nogui -noaudio -send "pd quit" path/to/main.pd
```

Silence means it parsed and every object instantiated. **Pd exits 0 even when objects fail to
create, so the gate is output, not exit status** — `deploy.sh` captures stdout and stderr and
refuses to copy anything if either is non-empty. This catches the entire class of load-time
errors — misspelled objects, malformed iemgui lines, bad connections — that would otherwise
vanish into tty1 on a device with no console.

**Refresh with `/reloadNoRemount`, never `reload.sh`.** `reload.sh` sends `/reload`, which also
runs `mount.sh`, which mounts the last `/dev/sd*` on `/usbdrive`. With a Launchpad attached that
is its write-protected onboarding drive, and mounting it moves `USER_DIR` onto a read-only
volume — breaking wifi config, Save and Save New. See [ref-hardware.md](ref-hardware.md).

**The load step needs the category folder in the name.** `mother`'s `/loadPatch` resolves
against its *current* patch directory (`MainMenu::runPatch` builds `getPatchDir() + "/" + arg`),
and `/reload` resets that to the default — `/usbdrive/Patches` if it exists, else
`/sdcard/Patches`. Since the patch lives in `/sdcard/Patches/!`, the argument is `!/Cut It`.
A bare `Cut It` loads nothing, silently. `deploy.sh` derives this from `DEST`.

| Target | Deploy |
|---|---|
| Organelle | `./deploy.sh` |
| iPhone (PdParty) | `curl -T <file> http://<phone>:9000/<scene>/_main.pd` over WebDAV |

Neither needs a cable. See [ref-display.md](ref-display.md) for addresses and ports.

**What the check cannot catch** is runtime behaviour — wrong message types, silent OSC
failures, logic errors. That is what the error bus below and the PdParty remote console are
for — and the run-it-yourself trick immediately below, which is better than both.

**Small macOS gotchas that have each cost a wasted command:** there is no `timeout` (use a
background PID and `kill`, or have the patch quit itself); `airport -I` is deprecated and reports
"not associated" even when Wi-Fi is up (`ipconfig getifaddr en0` instead); and `cat -A` is GNU —
use `cat -e`.

### There IS a console — launch the patch by hand ✅

"The Organelle has no Pd console" is true only of the **menu-launched** patch, whose stdout goes
to tty1. Launch it yourself over SSH and you get the real thing:

⚠️ **`killall pd` STRANDS THE LAUNCHPAD IN PROGRAMMER MODE.** The safe exit in `m_launchpad`
hooks `[r quitting]`, and only `mother.pd` ever sends that — right before *it* quits Pd. A signal
from the shell never produces it, and Pd 0.49 has no `closebang`, so there is no other hook.
Programmer Mode locks out the device's own Settings menu, so the grid stays frozen and the front
panel cannot recover it. **Run `./tools/lp-live.sh` afterwards** — it sends the Live Mode SysEx
with `amidi`, needs no Pd at all, and was measured recovering a stranded device with no power
cycle. `deploy.sh` is unaffected: it loads through mother's `/loadPatch`, so `quitting` fires
normally.

⭐ **If the probe only needs to SEND MIDI, do not use this at all — load a menu patch instead.**
`oscsend localhost 4001 /loadPatch s "!/<name>"` swaps the patch and swaps back through mother, so
`quitting` fires, the Launchpad is never stranded, and there is no `lp-live.sh` to remember.
`tools/stage-patches/PGM Probe/` is the worked example (item 228). ⚠️ **The probe must `aconnect`
Pd's output port for itself** — a patch load drops the connections, which is what `wire.sh` exists
to undo. Keep this section's console for when you need `[print]` output *back*.

```sh
ssh root@organelle.local
  killall pd; sleep 1        # ⚠️ then ./tools/lp-live.sh when you are done
  cd /tmp/patch
  nohup pd -nogui -rt -audiobuf 6 -path /root/Pd/externals \
      -path '/sdcard/Patches/!/Cut It' \
      /root/fw_dir/mother.pd main.pd /tmp/diag.pd > /tmp/diag.txt 2>&1 &
  sleep 6; killall pd
  cat /tmp/diag.txt
```

⚠️ **Single quotes around that path, not double.** The patch folder is `/sdcard/Patches/!/…`, and
**`!` inside double quotes is a history event in interactive zsh** — pasting the block gives
`zsh: event not found: /Cut` before anything reaches the device. Single quotes are literal in both
zsh and the device's busybox `ash`, so one form works everywhere. `deploy.sh` never hit this
because a script is not an interactive shell.

Loading `mother.pd` alongside `main.pd` gives the patch its real environment — `inL`/`inR` carry
live audio, `oscOut` reaches the display. A third patch (`diag.pd`) can tap any bus with
`[print]` without touching the deployed files: `[r disp] → [print DISP]`, `[r oscOut] →
[print OSCOUT]`.

Restore normal operation with `./deploy.sh`, which reloads and relaunches through the menu path.

**This found the `[list trim]` bug in Phase 1** — a `disp` message that `route` silently
rejected, showing as a plausible-looking zero on the OLED. Nothing else in the toolkit would
have caught it. Expect `error: /tmp/patch/knobs.txt: can't open` in the output; that is mother
looking for the optional knob-label file and is harmless.

### How a phase runs

Six phases have used the same shape and it is worth stating rather than rediscovering:

1. **A decisions table first**, with the *consequence* of each decision beside it — settled with
   Brendan before any code, because most of them change the shape of the work rather than its
   details.
2. **A Step 0 of measurements.** Anything the rest of the phase rests on that is currently 📄 or
   ⬜ gets measured *before* anything is built on it. **Every phase so far has had at least one
   assumption turn out wrong here**, and Phase 6's Step 0 changed two design decisions in an
   afternoon.
3. **Numbered build steps, each ending with both gates** before the next begins:

   ```sh
   python3 tools/pd-layout-check.py "Cut It"/*.pd
   /Applications/Pd-0.49-1.app/Contents/Resources/bin/pd -nogui -noaudio \
       -path mac-stubs -send "pd quit" "Cut It/main-dev.pd"     # silence == pass
   ```
4. **A `tools/phaseN-bench.pd`** — a printed `PASS IF` *before* each step **including the ones
   whose correct result is that nothing happens**, and honest about which steps need hands.
   **Stepped by hand, never on a timer**: a self-driving bench moves the console text and the
   physical device at the same moment, so you can read one or watch the other and not both. Press
   GO to run the described step, press GO again to describe the next. All four are generated from
   the step tables in `tools/bench_steps.py` — edit those and re-run `tools/bench-gen.py`.

   ⚠️ **A measuring rig is code and gets the same scrutiny as the thing it measures.** Phase 5 had
   two bugs in its own probes, one of which produced a confident wrong answer about the clock;
   Phase 6's bench had an automated assertion that **nothing ever drove**, with a comment beside it
   claiming otherwise. **Where the rig can assert without eyes, make it** —
   `tools/phase6-assert.sh` rewrites `[midiout]` in a scratch copy so a headless run can read back
   every byte the patch emits, and it is proven to fail by reintroducing a real bug.
5. **A verification section separating Mac from device**, so what has actually been proven is never
   in doubt.
6. **A landing checklist**, and it is not optional — see *Where the abstractions go* and the
   doc-hygiene rules in [CLAUDE.md](CLAUDE.md). Finished work moves to
   [ref-build-log.md](ref-build-log.md); the phase's section *leaves* [plan-v03.md](plan-v03.md)
   rather than being annotated; superseded designs are replaced, not annotated beside their
   replacement; anything unresolved moves to *Open questions*; and a new
   [plan-tests.md](plan-tests.md) session is added with items numbered **after the last used
   number in the file** — numbers are cited bare across documents, so **never reuse one**.
7. **The phase ends with a procedure, not a summary** — expected result stated *before* each
   action, for both machines. It lands in `plan-tests.md` **and** in chat, because chat is where
   it gets used.

**The bench proves the cases it contains and nothing else.** Phase 5's stickiest bugs — a stale
footer, a filter on the verdict instead of the value — were found by a person doing what a
performer would do. Budget hands-on time *after* the bench passes, not instead of it.

## Errors must reach the OLED ✅ built

**The Organelle runs Pd with `-nogui`, so an error you cannot see is a silent failure** — and
Pd's failure mode for a wrong message is to print and continue. `u_err` was built in the first
infrastructure pass rather than retrofitted *(judgment call: an architecture requirement, not a
debugging convenience)*.

- Any abstraction reports via `[s err]` as **`<level> <source> <text>`** — level `warn` or
  `fail`, source a symbol naming the abstraction, text **one symbol of ≤ 21 characters**. Use a
  **message box**, which already carries the level as its selector; anything built with
  `[list prepend]` needs `[list trim]`.
- **`u_err` filters by `mode`** — compose shows everything, perform only `fail`. One place, same
  bus, same callers. ✅ **It defaults to verbose**, which is what made an undriven `mode` safe
  through Phases 4 and 5. `u_map` drives the bus from Phase 6 on, and the filter needed no change:
  `route` matches on the selector, so two-atom `compose mode-1` sets verbose exactly as bare
  `compose` did.
- **`u_err` never draws.** It forwards onto `disp` as `alert <level> <source> <text>`; `g_oled`
  decides what an error looks like — see *The display bus* above.
- **The bus is unfiltered; only the screen is filtered.** An unconditional `[print err]` means
  the by-hand SSH console sees every error raised, even in perform mode.
- Errors **time out**; they are never modal. A stuck error covering the display mid-set is
  worse than a missed warning.

This does not catch Pd's *own* runtime errors — those still go to tty1. It catches the ones we
raise, which is most of what actually goes wrong.

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

The format is a flat, ordered record list, and three of its properties are traps. All three have
bitten this project, most of them more than once.

- **A `#X connect` names boxes by INDEX, and the index is position in the file.** Inserting or
  deleting *anything* — including a comment — shifts every later box and silently rewires the
  patch. **Append at the end**, honouring `#N canvas` / `#X restore` nesting: a top-level object
  goes before the first connect *at depth 1*. If a box really must be replaced, replace it in
  place so no index moves. `tools/pd-layout-check.py` reports the damage as *"indices are
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

**Every `[print]` in a deployed abstraction sits behind `[del 2000]`.** `deploy.sh` gates on
*output*, so a diagnostic that fires at `loadbang` breaks the deploy; behind a delay the syntax
check quits before it fires while the by-hand console still sees it.

✅ **Measured: `-send "pd quit"` returns in 735 ms**, with an undelayed control print appearing and
a delayed one not. ⚠️ **This covers more than `[print]`.** Pd's *own* file errors go to the same
stream — `[text read]` of a missing file prints three lines, and `[text write]` to a missing
directory prints `write failed` rather than failing silently, which a plan in this repo asserted
it did. **Anything that touches a file that may not exist belongs behind the same delay**, which
is why the state restore is staged rather than run at `loadbang`.
[plan-tests.md](plan-tests.md) item 143.

**Never open or save any of this in plugdata** — see [CLAUDE.md](CLAUDE.md).

---

## Banned

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
holds — is [ref-software.md](ref-software.md)'s *Architecture*, and the order the remaining ones
get built in is [plan-v03.md](plan-v03.md)'s *The shape of v0.3*.

The one boundary worth restating here, because it constrains how everything else may be
written: **the `m_` layer separates device mapping from everything it controls.** Nothing in
`e_*` may know that a nanoKONTROL exists. That is what makes the compose/perform split
tractable — the same surfaces mean different things in each mode — and it is the one boundary
that is genuinely expensive to retrofit.
