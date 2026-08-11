# The tests

**Everything that decides whether Cut It works.** Two kinds, and the difference is the *oracle* —
who or what says pass:

| | Verdict from | Runs |
|---|---|---|
| `gate/` | **a program**, unattended | every commit, in ~5 minutes, on the Mac |
| `bench/` | **a person**, with the rig plugged in | when hardware behaviour needs judging |

⛔ **A gate is not trusted until it has FAILED.** Reintroduce the bug, watch it go red, revert. This
project has shipped a gate that passed a broken patch 15/15, and one that had run its own driver
generator exactly never. Both looked green. See the **`gate`** skill.

⚠️ **The Mac is not the device.** The Phase 6 gate passed 25/25 on the Mac twice and shipped three
bugs. These prove a change did not break what was working; hands on the hardware are still the last
word.

## One gate per module

Nineteen gates, and each answers for exactly one page under `ref/`. That is the whole organising
principle: **a page that names a gate should be able to name one whose entire subject is that page**,
or say `none` honestly. Five pages once named a single `phase6-assert.sh`, and two of those claims
were false.

| Gate | Checks | Answers for |
|---|---|---|
| `runner-assert.sh` | 164 | **no page** — it answers for this one |
| `midi-emitters-assert.sh` | 7 | **no page** — see below |
| `init-assert.sh` | 16 | `module/boot` |
| `audio-assert.sh` | 12 | `module/audio` |
| `err-assert.sh` | 24 | `module/error` |
| `display-assert.sh` | 31 | `module/display` — the grid |
| `oled-assert.sh` | 43 | `module/display` — the OLED |
| `led-assert.sh` | 12 | `module/display` and `device/organelle` — the aux LED |
| `tempo-assert.sh` | 17 | `module/tempo` — `u_tempo` |
| `clock-assert.sh` | 22 | `module/tempo` — `c_clock` |
| `map-assert.sh` | 39 | `module/map` |
| `state-assert.sh` | 15 | `module/state` |
| `presence-assert.sh` | 36 | `module/presence` |
| `launchpad-assert.sh` | 8 | `device/launchpad` |
| `nano-assert.sh` | 23 | `device/nanokontrol` |
| `organelle-assert.sh` | 17 | `device/organelle` |
| `phone-assert.sh` | 28 | `device/phone` |
| `sp404-assert.sh` | 17 | `device/sp404` |
| `volca-assert.sh` | 10 | `device/volca` |

**541 checks.** ⚠️ **Eighteen of the nineteen gates print their own `N checks` line and one does
not** — `midi-emitters-assert.sh` prints an inventory instead, so its 7 is hand-maintained and the
total cannot be derived from a run by summing. Totalling the run gives **534**; the difference is
that gate. Worth knowing before trusting an arithmetic check of this number against a log.

⚠️ **`presence-assert.sh`'s 36 come from TWO Pd runs and one tally**, which is the only entry here
that does. The first run is the schedule at the shipped tick; the second scales `u_present`'s settle
and tick by ten and leaves its **counts** exactly as shipped, so the eighth re-wire and the give-up
actually happen — inside nine seconds rather than seventy-two. ⛔ **One analyser reads both
captures**, because two would print two `N checks` lines and this number is what proves no assertion
went missing.

 ⚠️ Three pages name more than one gate, and that is the rule working rather than
bending: `module/display` covers three surfaces with three different owners, `module/tempo` covers the
master reference and the clock cut from it, and `device/organelle` covers a front panel and an LED.
**A gate whose subject is two abstractions is what the split was for**; a page whose subject is two
surfaces gets two gates for the same reason.

**No page declares `Gate: none` any more.** `module/audio`, `device/nanokontrol` and
`device/organelle` were the last three, and each has its own gate now. ⛔ **`audio-assert.sh` is the
only one that reads a SIGNAL back** — it records `u_root`'s output to a soundfile and asserts the
passthrough is not silent, not swapped and not attenuated. Every other gate here asserts on messages,
which is what made the audio path invisible for as long as it was.

**`midi-emitters-assert.sh` belongs to no device on purpose.** Its only claim is structural — *these
are all the MIDI objects in the patch* — and a new `[noteout]` in some future `e_` stage is not the
SP-404's business or the Volca's, but very much the instrument's. It needs no Pd and takes ~200 ms.

**`runner-assert.sh` belongs to no page for a different reason: its subject is `test/run.sh`,** which
is not part of the instrument. Inventing a `ref/` page for it would put a claim about test tooling on
the same shelf as claims about the hardware. ⛔ **It is the only thing that ever exercises the
runner's failure paths** — a hardware bench run that goes well never stalls, never desyncs, is never
interrupted and never meets an empty console, so without it all four branches could be dead code and
every run would look identical and green.

⚠️ **Its fixture set was written by mutation, not by guessing.** The first version had seven
fixtures and looked complete; deleting the runner's fired-line check, its marker check and its
mid-run stall handler left it **fully green** in all three cases — one fixture was tripping two
guards at once and so only ever tested the first to fire, and one stall handler had no fixture that
reached it at all. Four more fixtures, each corrupting exactly one thing. ⛔ **A fixture that trips
two guards tests one of them.**

⚠️ **And every fixture drove `run_bench_driven`, so the OTHER loop was ungated.** `run_bench` — paper
mode, no stream at all — had no fixture until it was found evaluating predicates against an empty
window. There is one now, and it needs `CUTIT_RESULTS` pointed at a scratch directory: ⛔ **a paper
run is a NORMAL run and rolls its verdicts up into `latest.json`**, which is committed and describes
hardware. The replay path refuses to roll up at all; this one is redirected, and a check proves the
redirect held rather than merely being passed.

### The shared machinery

| | |
|---|---|
| `lib-scratch.sh` | sourced by every gate that copies the patch. Holds the **one** `MIDI_EXPECT`, the stub rewrite, the private state directory, the generator status check and the watchdog |
| `lib_assert.py` | the check tally, the capture parser, and `require_capture` — a gate handed an empty capture must FAIL, not report nothing and exit 0 |
| `lib_drive.py` | window table → driver patch. Absolute delays off one `loadbang`, one delay per action, the `MARK` on the highest outlet |
| `lib_grid.py` | reassembles Launchpad SysEx. ⛔ Skips realtime bytes ≥ 248, which are legal *inside* a SysEx stream — `u_tempo` emits 96 a second |

⚠️ **The underscore in three of those is not a slip.** A hyphen is not a legal Python identifier, so
a module that is *imported* cannot have one; a script that is only *run* can.

⛔ **`MIDI_EXPECT` is an EXACT count per class, never "not zero".** A lower count means assertions
have gone vacuous; a higher one means an emitter no gate knows about. The gate it replaced checked
only for non-zero and its comment claimed five `[midiout]` where the patch has six — the count
drifted and nothing noticed.

## Running everything

```sh
./test/run.sh                every gate in one command, ~5 min, exit non-zero on any failure
./test/run.sh --all          and then the benches -- needs the rig, and a person
```

Layout and graph structure, both entry points loading in silence, the bench step text, the MIDI
inventory, and one gate per module — the boot sequence, the audio path, the error bus, the display
arbiter, the OLED, the aux LED, the tempo reference, the clock, the map, the data store, the
Launchpad, the nanoKONTROL, the Organelle's own panel, the phone, the SP-404 and the Volca. **Mac
only — it touches no device**, so it is safe to run at any time, including with the Organelle
switched off.

⚠️ **Run it before calling anything done.** Phase 8 edited `u_map`, `u_init` and `u_root` — files
Phases 5, 6 and 7 all rest on — and came within one step of shipping without re-running *their*
gates. The gates were all there, all passing, and all unused. **A gate you have to remember to run
is a gate that eventually does not run.**

⚠️ **`lp-monitor.pd` and `lp-step0.pd` are NOT here.** They were listed under
`test/` and they live in [tools/](../tools/README.md), where the directory-is-the-kind rule puts
them: they are probes a person runs, not tests with an oracle.

## `test/run.sh` — the entry point, and both halves

```sh
./test/run.sh                              the gates. Mac-only, ~5 min, the default
./test/run.sh --all                        the gates, then every bench
./test/run.sh --bench midi                 one bench
./test/run.sh --bench tempo --target mac   run the patch here rather than on the device
./test/run.sh --bench phone --target mac --auto-only
./test/run.sh --from 8                     resume a bench part-way
./test/run.sh --list                       what would run, and how fresh each verdict is
```

⛔ **Run bare it is the gate half and nothing else** — Mac-only, touching nothing on the Organelle,
safe with the device off. Benches are behind a flag on purpose: ⚠️ **a check that costs twenty
minutes stops being run**, which is the failure this command exists to fix.

⛔ **`--target` says WHERE the patch runs; `--auto-only` says whether a PERSON is watching.** Two
axes, not one — welding them together makes an unattended run on the real rig unreachable, and that
is worth having.

| `--target` | Is | Can judge |
|---|---|---|
| `device` | **Default.** The real rig, over ssh | everything |
| `mac` | `main-dev.pd` plus the bench here; `u_mother-stub` draws the panel and decodes the OLED | display, nanokontrol, tempo |
| `paper` | no Pd at all | **`file` predicates only** — the evidence is on disk. Auto-selected for `state`, the one bench that needs nothing on the other end |

### Nothing a person does is timed

⛔ **The only clock in a bench run measures SILENCE FROM THE DEVICE**, and it exists for one case:
the patch is gone — the instrument crashed, the ssh dropped, the bench never loaded. Then nothing
ever arrives and without a bound the runner would sit forever, indistinguishable from waiting. On a
live Organelle the console never goes quiet, because the level reports keep coming, so five seconds
of real silence does mean it is dead.

⚠️ **Reading, sweeping and deciding are not timed and never have been.** A stall that says otherwise
is reporting the wrong bound — see the flush above.

⛔ **A step whose oracle is missing is a SKIP WITH A REASON, never a pass** — whether the reason is
the target, the absence of a person, or **a predicate that needs a console in paper mode**.

⛔ **THREE THINGS NEED A PATCH ON THE OTHER END, and only one of them is an action.** A predicate
that reads a console has nothing to read without one, and a `reload` step is the runner *owning* the
process it restarts. The auto-selection asked only about actions for as long as those two happened
to travel with them — so `midi` came up `paper` and every recorded run of it passed `--target
device` by hand, and `nanokontrol` joined it the day it was cut back to six hands-on steps that send
nothing at all.

⚠️ **Run `midi` on paper anyway and it still cannot reach a clean PASS, which is honest.** Four of
its steps read a bus, and no bus exists where no Pd is running; they skip, naming the kind that
could not be judged. They used to be evaluated against an **empty window** and report AUTO FAIL —
four red steps on a working rig.

### Three keys, and Ctrl-C

```
verdict? [p]ass  [f]ail  [r]epeat :
```

**`r` fires the current step again and advances nothing** — the control to reach for when an OLED row
aged out before you finished reading the sentence about it. ⛔ **Enter is not a verdict.** Every path
out of that prompt is something a person typed; a default on empty input would be the runner
inventing an answer, which is the one thing that would make it worthless.

⛔ **Ctrl-C is the only way to leave, and what it records depends on whether the step RAN.** Stopped
at the read prompt, before GO: nothing is recorded and whatever that step last answered stands.
Stopped after it fired: `interrupted`, because it ran and nobody judged it. ⚠️ **That distinction is
load-bearing** — `roll_up` is last-write-wins, so a row carrying the absence of a verdict *overwrites*
a real one. Three fresh passes were destroyed that way in one afternoon (tempo 5, launchpad 8 and 17,
2026-08-11) by a session that ended one step past the ones it came to re-run.

**Four keys were removed on 2026-08-11** and each was dead or a second spelling of something else:
`[q]uit` was Ctrl-C with the worse failure mode above, `[u]ndo` did nothing on six of the seven
benches because nothing can walk a running patch backwards (`--from N` re-runs a step properly), `[?]`
reprinted the PASS IF already on screen, and `[s]kip` answered *"I cannot judge this today"* — a
question a bench run does not ask, since the rig is plugged in or there is no session. ⚠️ **The
AUTOMATIC skips are a different thing and all three remain**: a target that cannot judge a step, a
predicate with no console, `--auto-only` with nobody watching. Those are the runner declining to
invent a verdict rather than a person declining to give one.

### Sixteen steps judge themselves

A step may carry an optional **fourth element**, a dict: `need` and `do` (what to have at hand, what
to press), `watch`, `check` (a predicate), `wait`, and `targets`. ⛔ **It never reaches the `.pd`** —
emitting it would reopen every hardware-verified step text to the comma/semicolon fragmentation
hazard the generator exists to prevent, so `bench-verify.py` still diffs three fields.

⛔ **`watch` is gone entirely.** It replaced the line labelled `PASS IF:` with something else, so on
two steps that label named text the verdict was not recorded against — which is the only reason the
prompt ever needed a `[?]` key. `midi` 7's restated its PASS IF in other words and `launchpad` 14's
explained the Mac dev panel to somebody standing at the rig. **The count a predicate wants is printed
by the predicate**, on the line above the verdict prompt, from the one source that cannot drift from
it. `bench-verify.py` diffs two fields now, not three.

⛔ **A predicate that needs the OSC mirror is skipped on the device — the STEP is not.** Only
`--target mac` repoints `u_net` at a socket the runner binds, so on the rig the window carries no
`OSC:` line and every `has` finds nothing. ⚠️ **`phone` 2 and 8 carried `targets: ('mac',)` to dodge
that**, which skips the whole step: two steps of the one bench whose subject is a screen in your hand,
never judged by anyone on the rig, while the comment beside them claimed *"the device run keeps its
human verdict"*. Derived from the predicate's kind in `predicates.MIRROR_KINDS`, never listed per
step.

**`bench-tap.pd`** is generated beside the benches and loaded with them: `[r bus] → [print LABEL]`
and `[r oscOut] → [print OLED]`, and **it sends nothing**. C-5 gives `g_oled` sole ownership of
`oscOut`, but ownership governs *writing* — Pd delivers a message to every receiver of a name, so a
listener cannot change what any other subscriber sees. ⛔ **Do not "fix" it by routing its output
anywhere.** `clock` is deliberately not tapped: two beats a second forever.

⛔ **The generator refuses a predicate that cannot fail.** A purely negative one needs an
independent liveness witness beside it; a bus predicate may not name a bus its own step writes;
`bus-count` takes an exact `n` and rejects a range. ⚠️ **`oled` is exempt from the self-write rule
and must be** — display 3 writes `disp` and asserts on what `g_oled` *drew*, which is downstream,
not an echo.

⛔ **And it refuses a predicate that disagrees with its own prose.** A step has two oracles now, a
person reading the PASS IF and a program reading the bus, and nothing else stops them drifting apart.

⚠️ **`wait` is what makes the three hot-swap unplug steps work at all.** The runner drains for
`wait` seconds *after* GO, and a `device-lost` warn is three missed polls behind the cable coming
out — up to 8 s. The default is 0.4 s, so those three carry `'wait': 12` and their `do` text says to
press enter **as soon as the cable is out**: a person who unplugs, counts to ten and then presses
enter would get an AUTO FAIL out of entirely correct hardware.

⛔ **Four of the eight hot-swap steps cannot judge themselves and must not pretend to.** The Volca's
two are **by ear** — it transmits nothing, so there is no readback of any kind — and the two
absent-at-load recoveries are judged by a lit grid and a moving slider, neither of which any bus
carries.

### Results, and freshness

Per-run records go to `test/results/runs/` (gitignored), fsynced before the next step is described.
The roll-up in `test/results/latest.json` is **committed**, which is what makes *"when did phone step
12 last pass, and against what code?"* a `git log` question.

A verdict is **fresh** only if the sha of its title and `pass_if` is unchanged, the target matches,
it is under 30 days old, and its **per-bench dependency sha** is unchanged. ⛔ **Per bench, not the
whole tree** — hashing all of `Cut It/` would mark every bench stale on every patch commit, and a
signal that is always lit is one nobody reads.

## `display-assert.sh` and `launchpad-assert.sh` — no eyes and no hardware

```sh
./test/gate/display-assert.sh          31 checks, ~46 s — the ARBITER
./test/gate/launchpad-assert.sh         8 checks, ~4 s  — the DEVICE
```

Both take `--keep` to leave the byte capture behind to read. **They were one gate**, which is why
five pages once named it and two of those claims were false: it tested nothing about the
nanoKONTROL and nothing about the OLED.

**This is the part that asserts what the grid is actually showing.** The bench used to claim in its
own header that *"there is no way to read back what the LEDs are actually showing"* — too strong,
and it conflated three different things. Pd cannot ask the Launchpad what is lit, but **the bytes
the patch sends are completely knowable**, and that is the right level to test our own code at.

⚠️ **The split is not cosmetic — it is 46 seconds.** `display-assert` needs DSP, because the beat
row hangs off `threshold~`; the two SysEx checks about the *device* need no clock at all and were
paying that bill for no reason. `launchpad-assert` now runs in four seconds and gained three checks
it could not previously afford: the **order** of the mode switch against the first painted frame,
which neither message existing implies. LED writes sent in Live Mode do not appear, so a patch that
painted first and switched second would send both messages and still come up dark.

| Piece | |
|---|---|
| `test/stubs/t_midiout.pd` | a stand-in for `[midiout]` that prints every byte with its port |
| the drivers | generated into the scratch directory on every run by `display-assert-drive-gen.py` and `launchpad-assert-drive-gen.py`. Not committed |
| `test/gate/lib_grid.py` | reassembles the SysEx frames — shared, because both gates read the same byte stream and want different frames out of it |
| `display-assert.py` | the arbiter: which layer owns the surface, and what happens when one gives it up |
| `launchpad-assert.py` | the device: what the hardware is told, and in what order |

⚠️ **The stand-in cannot be supplied by search path.** `mac-stubs/` works because `shell` is an
*external absent on the Mac*, so Pd falls through to an abstraction. `midiout` is a **built-in
class**, and Pd resolves the class table before it looks for a file — ✅ measured both ways, and a
`midiout.pd` on the path is simply ignored. So the object name has to change, which means
rewriting the box. **`Cut It/` is never touched**; the scratch copy is thrown away.

The script counts the boxes it rewrote and **refuses to run if it found none** — otherwise every
assertion would pass vacuously, which is worse than failing.

**31 checks**: frame shape and the 1–108 span, the mode lamp index, the modal claiming all 108
specs, `fail` painting red and `warn` painting nothing, the alert expiring back to the modal
underneath, the beat row never leaving 11–18, the grid SURVIVING a panic, and
`m_launchpad`'s Programmer and Live SysEx.

✅ **It has been proven to fail.** Reintroducing the one-based beat bug in a scratch copy — the
beat-row offset back to `+ 11` — makes it report `lit outside every region: [(19, 3)]` and exit 1.
⚠️ **The three `home-*` checks still passed under that mutation**, which is exactly why *seven
beats out of eight looked perfect*: only the six-second beat-row window catches it. A gate that
cannot fail is worth nothing, so re-run that mutation if you ever change the analyser.

## `tempo-assert.sh` — two kinds of check, because neither is enough

```sh
./test/gate/tempo-assert.sh          17 checks, ~16 s
```

`u_tempo` is the instrument's interval timer: it publishes a beat on a bus that `g_grid`, every
`c_clock` and every future effect stage subscribe to, and writes MIDI clock to the wire at 24 pulses
per quarter note. **Nothing read those bytes back** until this existed.

| Half | Owns |
|---|---|
| a **static lint** — reads `[clip 5 600]` and `[* 24]` out of `u_tempo.pd`, ~1 ms, no Pd | the **bounds** |
| a **rate count** — System Real-Time bytes over a known window | whether the clamp is in the **signal path** |

⛔ **Neither can do the other's job, and that was found by trying to break it.** The pulse ceiling is
~344 Hz — `threshold~` decrements its dead time once per DSP block — so 600 BPM is 240 Hz and
**5000 BPM saturates at ~338 rather than reaching 2000**. A clamp widened to 5000 is caught easily; a
clamp widened to **650** reads 260 Hz, inside a 12 % band on 240, and is caught *only* by the lint.
Widening the tolerance would not have helped. The wire cannot resolve it.

⚠️ **It needs DSP**, like `display-assert`, because the pulse is a `[phasor~]` read by a
`[threshold~]`. Under `-noaudio` every count is zero, which reads exactly like a dead clock.

**What it protects:** 24 PPQN at two tempos and the **ratio** between them (which cancels the
real-time scheduler entirely); that the clock leaves on **both** ports, since a fan-out that lost one
would look perfect on the other; the clamp warning at both ends and *not* warning in range; start
250, stop 252, panic 252, and ⛔ that **Continue (251) is never sent**; and ⛔ that **stop does not
halt the clock** — the transport pauses the subscribers, it does not clear the timer.

## `map-assert.sh`, `sp404-assert.sh`, `volca-assert.sh` — the map and the output devices

```sh
./test/gate/map-assert.sh            38 checks, ~7 s — the lookup, and the static lint
./test/gate/sp404-assert.sh          17 checks, ~7 s — the 404 in BOTH directions
./test/gate/volca-assert.sh          10 checks, ~5 s — four destinations, one channel
```

Each takes `-v` for the detail behind every check and `--keep` to leave the scratch directory and
capture behind. **They were one gate, and it claimed three pages at once** — the map's page, the
404's and the Volca's — which is exactly the false-coverage this refactor exists to remove. The
split reconciles upward: 28 checks became 34, because each gate could then say things the shared one
had no window for.

⚠️ **`map-assert` uses `volca-cc` and asserts nothing about the Volca.** A lookup has to land
somewhere; what the destination then does with the value is the device gate's business.

**Half of `map-assert` is a STATIC LINT.** It parses the literal `route` box out of `u_map.pd` and the rows
out of `cut-it-map.txt` and asserts that **every destination a row can name exists as an argument on
that route** — the allowlist guard, enforced by reading, exactly the way this project audits its
global sends. It also catches a **duplicate `(mode, control)` pair**, which `text search` resolves
to the *first* match only, so a repeat is dead and silent. That half runs without Pd at all.

The other half of each gate rewrites the MIDI object boxes in a scratch copy — **all seven classes, from the one
`MIDI_EXPECT` in `test/gate/lib-scratch.sh`**, shared with every other gate that makes a copy. ⛔
**`[midiout]` alone was never enough**: `m_volca` and `m_404` emit through `noteout` / `ctlout` /
`pgmout`, so a rewrite of `midiout` only finds nothing in them and every assertion about them passes
**vacuously**. ⛔ **And the two input stubs are not optional**: every *output* path can be driven from
a bus, but `m_404`'s receive side sits behind `[notein]` and `m_nano`'s *entire surface* sits behind
`[ctlin]`, and **no bus reaches a MIDI input**. ⛔ **`[polytouchin]` is the one class left with no
stub, and it was in NEITHER list until `midi_scan_unknown` asked the question as a closed one** —
walking every MIDI class Pd has and checking it against the inventory, rather than checking the
inventory against itself. `[sysexin]` had no stub either until `t_sysexin` landed with the
hot-swap work, because a device-inquiry reply is the only evidence of presence there is and it
arrives on a MIDI input.

⚠️ **The count is EXACT per class, never "not zero".** A **lower** count means assertions have gone
vacuous; a **higher** one means an emitter no gate knows about. `test/gate/midi-emitters-assert.sh`
asserts the same inventory on its own, without Pd, so the claim has an owner that belongs to no
device.

⚠️ **Each owns its state directory**, and every gate that loads `main-dev.pd` now does. `main-dev.pd`
passes `/tmp`, shared by every run on the machine, and `u_init` restores saved state at ~3.5 s — so
one test that changes mode silently rewrites the starting conditions of every test after it. That
cost a wrong diagnosis once: item 232.

**Proven to fail** — the shared gate was, on a `47 + n` pad map (12 of 16 pads, both directions), a row naming a
non-existent destination, and a duplicate row. ⛔ **It PASSED a disarmed rate limiter on the first
try** — the burst window fires in one logical instant and `[del 0]` still defers to the next
scheduler tick, so it proved *drops-rather-than-queues* and nothing about the interval. A window of
two triggers **2 ms apart** was added, which straddles the 5 ms gate: 1 armed, 2 disarmed.

⛔ **It also HUNG once instead of failing** — the driver generator errored, its exit status was
unchecked, Pd was handed a file that did not exist, and the `; pd quit` that lives *inside that file*
never fired. **A gate that hangs is worse than one that fails.** The generator's status and the
driver's existence are checked now, behind a 40 s watchdog.

Each driver is an OUTPUT, generated into the scratch directory on every run — edit `map-assert-drive-gen.py`, `sp404-assert-drive-gen.py` or `volca-assert-drive-gen.py`. None is committed.

## `state-assert.sh` — the data store, and the cheapest oracle in the suite

```sh
./test/gate/state-assert.sh          15 checks, ~12 s, exit non-zero on any failure
./test/gate/state-assert.sh -v       and the detail behind every check
```

`u_state` writes a **file**, so this gate reads what landed on disk. No scratch copy (Phase 6
needed one, because `[midiout]` is a built-in class with no side channel), no socket (Phase 7's
trick), no hardware. It works entirely inside `/tmp/cut-it-state-gate` and never touches
`Cut It/`, `/sdcard/cut-it-state` or the device.

**What it protects, stated as properties rather than proxies:** the two policies never leak into
each other; re-putting a key REPLACES its line; **a contributor answering behind a `[del]` is
absent from the file** — the synchronous contract itself; manual is replayed before auto so auto
wins a duplicate key; **a boot does not overwrite saved state before reading it**; and both entry
points load in **silence**, which is `tools/deploy.sh`'s own gate.

⚠️ **It passed the broken patch on its first can-it-fail run** — the driver banged the restore at
600 ms when the bug needs it after 3000 ms, and the final check asserted against a value nothing
drove. **The 3600 ms in the driver is load-bearing**; shortening it re-blinds the gate. Proven
both ways now: 15/15 clean, 2 failures with the bug reintroduced. `state-assert-drive.pd` is an
OUTPUT — edit `state-assert-drive-gen.py`, never the `.pd`.

## `phone-assert.sh` — the same idea, and much cheaper

```sh
./test/gate/phone-assert.sh            # ~25 s, exits non-zero on any failure
```

**Phase 7's gate needs no scratch copy and rewrites nothing.** `[midiout]` is a built-in class
with no side channel, which is the whole reason `display-assert.sh` has to swap it for a stand-in
in a throwaway copy of the patch. **`u_net` already emits to a socket** — so the gate binds
`127.0.0.1:9995`, instantiates `u_net 127.0.0.1 9995` and reads the real datagrams. `Cut It/` is
never touched.

| Piece | |
|---|---|
| `phone-assert-drive-gen.py` | generates the driver. **Edit this, never the `.pd`** |
| `phone-assert-drive.pd` | instantiates `u_net` and pushes synthetic traffic onto `disp` |
| `phone-assert.py` | binds the port, launches Pd, decodes OSC, does the reasoning |

⚠️ **The analyser owns the lifecycle, and that is not tidiness.** It binds the socket *before*
Pd starts, because a UDP connect to a port with nothing listening survives exactly one datagram
(item 114). Start the driver by hand and you get one packet and then silence — which looks
exactly like a broken rate limiter.

**The window marks travel as datagrams**, to the same port, through the driver's own `netsend`.
A mark on stdout would have to be correlated with socket timestamps afterwards; a mark *in* the
stream arrives in true order with the data around it.

**28 checks**: the four OSC addresses and nothing else, a monotonic heartbeat, silence on both
idle windows, the coalescer's rate ceiling, **a per-name trailing edge on two simultaneous
sweeps**, `status` limited on its own address, the alert arriving as repeated state, and the
reserved selectors never leaking onto `/cutit/param`.

✅ **It was proven to fail before it was trusted, and for free.** `u_net` was built plumbing-first
with no coalescer, and that build failed exactly three checks — the three rate ceilings — at
401, 802 and 401 packets, while every shape check passed. Adding the store took those to 42, 84
and 42. No mutation had to be invented afterwards, which is the one weakness of Phase 6's
equivalent.

## `stubs/` — stand-ins the gates need

`t_midiout.pd` replaces `[midiout]` so a headless run can read back every byte the patch emits.
⚠️ **It cannot be supplied by search path**, which is why `display-assert.sh` rewrites boxes in a
scratch copy — see that gate below.

**Phase 9 added four more, because `[midiout]` is not the only way this patch emits MIDI:**

| | |
|---|---|
| `t_noteout.pd` | `[noteout]` — prints `pitch velocity channel` |
| `t_ctlout.pd` | `[ctlout]` — prints `value controller channel` |
| `t_pgmout.pd` | `[pgmout]` — prints `program channel`. ⚠️ **It cannot answer the 0-based/1-based question** (item 228): it prints what Pd was *given*, not the byte on the wire |
| `t_notein.pd` | ⛔ **a SOURCE, not a sink** — the only way to test a receive path. Drive it with `; t-notein <pitch> <velocity> <channel>` |

⛔ **`m_volca` and `m_404` emit through `noteout`/`ctlout`/`pgmout`, not `midiout`**, so
`display-assert.sh`'s rewrite finds nothing in them and every assertion about them would pass
**vacuously**. ⚠️ **And phase 6's regex is anchored so the class name must END the line** — it
silently skips any box carrying creation arguments, of which the patch has one:
`[ctlout 123 33]`. A phase 9 rewriter has to take a trailing argument list, and the stubs
therefore read creation args too.

⛔ **`t_notein` exists because the receive side is otherwise untestable.** Every *output* path can
be driven from a bus, but `m_404`'s entire receive side sits behind `[notein]` and **there is no
bus behind a MIDI input** — the channel gate, the note-to-pad lookup, the bank name builder and
the `param`/`disp` split would all go unexercised. Its outlet order reproduces the real object's
(channel, then velocity, then pitch) rather than approximating it; get that backwards and the
stub tests itself instead of the patch.

## The benches

### A bench belongs to whatever its steps TOUCH

⛔ **The bench a step lives in is decided by what a person has to have in front of them, not by what
was convenient when the table was written.** `nanokontrol` carried fourteen steps that never touched
the nanoKONTROL — every action was a `disp`, `err` or `mode` message the bench sent itself, and the
controller could have been unplugged for all fourteen. Nine were byte-identical to `display` steps
but for one warn string.

⚠️ **The cost was not the duplication, it was `latest.json`.** The same OLED claim was being judged
twice under two names, so the record of what had been verified reported more coverage than existed —
the same disease as a gate that lies, one level up. The OLED ladder moved to `display`, the
duplicates went, and `nanokontrol` is now the six steps that need a hand on the controller.

**The test before adding a step: could this run with the named device unplugged?** If yes, it is not
that device's step.

### A bench suits a SURFACE, not a store

⚠️ Worth knowing before writing `STEPS9`. The bench framework prints a `PASS IF` and waits for a
human to look at something — which works beautifully for the OLED, the Launchpad and the phone,
and not at all for a feature whose entire output is a **file**. The data store's five steps are the
minimum that hardware can actually show (the front-panel Save, a real power cycle, the mode lamp);
its logic is proven by `state-assert.sh` instead, headlessly, in twelve seconds.

Phase 8's run was also driven **from the Mac by hand rather than by loading the bench**, because
every one of its steps carries no actions. That avoided the by-hand console entirely — and
therefore `killall pd`, and therefore stranding the Launchpad in Programmer Mode. **If a phase's
steps have no actions, you do not need to load the bench at all.**

### They are stepped by hand

**All seven benches are generated by `bench-gen.py` from the step tables in `bench_steps.py`**
(`STEPS_DISPLAY` through `STEPS_MIDI`). Edit the table and re-run the generator; **never edit a
`phaseN-bench.pd`.**

```sh
python3 test/bench/bench-gen.py        # writes all seven, plus bench-tap.pd
python3 test/bench/bench-verify.py     # proves the step text survived
python3 test/bench/bench-extract.py test/bench/tempo-bench.pd   # recover a bench's step table
```

`bench-extract.py` is what made the conversion safe: it recovers the step text from a `.pd` by its
`=== STEP-NN-of-M ===` markers, so the hand-authored, hardware-verified benches could be diffed
before and after rebuilding their box graphs. Zero differences was the gate. `bench-verify.py` is
that same check, run against the table.

They no longer drive themselves on a timer. The old shape put the console text and the physical
device in motion **at the same moment**, so you could read one or watch the other and not both.
Now:

```
press GO  →  the step that was just described runs
press GO  →  the next step is described, and nothing moves
```

The prompt line always says what the next press will do, so **one control is enough** — which is
what makes the device half work at all, since the Organelle's encoder click is the only free
control there is.

| GO | |
|---|---|
| the `bng` at the top of the patch | Mac |
| **the Organelle's encoder click** | both — `u_mother-stub` sends `encbut` on the Mac, and nothing in Cut It consumes it |
| `echo "go;" \| nc -u -w0 organelle.local 9998` | device, from the SSH window |

Turning the encoder **repeats** the current step without advancing — for when you looked away.

⚠️ **A timed assertion starts its clock at RUN, not at the press after it.** A step that zeroes a
beat counter arms a 10 s window, latches the count and prints it, so the number covers exactly ten
seconds however long you take to judge the step. The latch starts at **-1**, so a count read before
its window closed says so instead of lying.

⚠️ **On the Mac, tick `enable-DSP` first.** `c_clock` hangs off `threshold~`, so with DSP off the
beat row never moves and every count reads 0 — which looks exactly like a dead clock.

### Running a bench on the device

Any of the seven benches loads as a **third patch** after `mother.pd` and `main.pd`, which is what
gives it a real console. This is the launch line:

```sh
scp test/bench/tempo-bench.pd root@organelle.local:/tmp/
ssh root@organelle.local
  killall pd; sleep 1
  cd /tmp/patch
  nohup pd -nogui -rt -audiobuf 6 -path /root/Pd/externals \
      -path '/sdcard/Patches/!/Cut It' \
      /root/fw_dir/mother.pd main.pd /tmp/tempo-bench.pd > /tmp/bench.txt 2>&1 &
  tail -f /tmp/bench.txt          # Ctrl-C when the last step prints
  killall pd
```

⚠️ **Single quotes around that path, never double.** The patch folder is `/sdcard/Patches/!/…`, and
`!` inside double quotes is a history event in interactive zsh — you get `zsh: event not found:
/Cut` before anything reaches the device.

⚠️ **The second `-path` is what lets a bench find an abstraction from `Cut It/`.** No bench needs one
today — `tempo-bench` was the last, and it stopped when its `c_clock` counters were cut — but a
bench that gains one resolves it from `/sdcard` and not from the patch folder, so leaving the flag
in the launch line costs nothing and its absence is silent.

⚠️ **THE ENCODER DOES NOT ADVANCE A BENCH ON THE DEVICE.** The plan that chose a single
alternating control assumed it would. `mother` forwards `encbut` only to patches that have sent
`/enableEncoder`, and **nothing in Cut It ever does** — `m_organelle` leaves the encoder out
deliberately. On the Mac `u_mother-stub` sends it unconditionally, which is what hid this. Use:

```sh
./test/run.sh --bench tempo --target device      # the runner sends GO itself
./test/run.sh --bench tempo --target device --from 13
```

⚠️ **Not netcat.** The benches used to print `echo "go;" | nc -u -w0 organelle.local 9998`, and on
macOS that **silently does nothing** — BSD `nc` exits before the datagram is flushed at `-w0`, and
`-w1` was measured to fail too, while the port *is* bound and the bench *is* fine. It looks exactly
like a dead bench. The device cannot send to itself either: busybox here has no `nc` at all.

⚠️ **`killall pd` strands the Launchpad in Programmer Mode** — see `lp-live.sh` below. Restore
normal operation with `./tools/deploy.sh`, which reloads through the menu path and *does* run the safe
exit.

**Two of these live on the device**, left there deliberately after the Phase 6 hardware run:
`/sdcard/launchpad-bench.pd` and `/sdcard/dsp-toggle.pd`. They sit *outside* the patch folder, so
`tools/deploy.sh` never touches them and they cannot affect what loads. Re-`scp` only if you have
changed them locally.

⚠️ **`/tmp` is wiped on reboot**, which is why these live on `/sdcard`. A bench copied to `/tmp`
vanishes with a restart, and the by-hand launch then runs `mother.pd` + `main.pd` with **no
bench** — the GO port is never bound and the bench looks frozen at step 1. Item 134.

### `launchpad-bench.pd` — the Launchpad acceptance run

**Twenty-six steps** covering the mode bus, the grid arbiter, the layer priorities and TTLs, the
first `c_clock` instance, the ring map, hot-swap and the safe exit. Steps needing hands are marked in
their own prompt line.

⛔ **Steps 21 and 22 replaced the replug-hazard step, which asserted the opposite of what the
instrument now does.** It read *"the device returns in Live Mode but `m_launchpad` still believes it
owns the surface"* and closed *"Not built yet"* — presence drops ownership on the third missed poll
and the bounded re-wire brings the device back with Programmer Mode re-asserted.

⛔ **Step 21 has to set `compose` itself, and could not be judged until it did.** `u_err` shows every
error in compose and only `fail` in perform, so a `warn` is correctly **invisible** on the OLED in
perform — and step 20 asks a person to press all six transport keys, which leaves the rig on mode-6.
The step then asked for an alert the instrument was right to suppress: the bus carried it, the eyes
did not, and the runner recorded both halves disagreeing. **Every step sets up its own
preconditions**, and a mode is one.

⚠️ **Its beat counter used to be dead.** `[r $0-zero]` and `[r $0-read]` existed, the comment beside
them claimed the tempo steps drove them, and **nothing anywhere sent to either name** — so the one
automated assertion in the Phase 6 bench never fired. Same shape as `tempo-bench`'s `[r $0-say]`
that was never connected to its `[print]`. Fixed by driving them from the step table.

⛔ **Panic KEEPS the surface — it does not hand it back**, and `m_launchpad` never sees `panic` at
all. Handing it back set `want 0`, so the watchdog stopped re-asserting Programmer Mode and **the
grid stayed dead until a reload** — at the one moment you most need the instrument. Worse, in Live
Mode the device floods MIDI port 1 with clock and `wire.sh` connects that port to Pd's Midi-In 1, so
a panic also buried Cut It's primary MIDI input (item 250). Silencing notes has nothing to do with
surrendering a surface.

⛔ **Three bench steps asserted the old behaviour until 2026-08-11 and failed on the rig**, while
`display-assert` had asserted the current one all along — *"the grid SURVIVES a panic — it must keep
painting"*. **A gate and a bench testing opposite claims is the disagreement worth catching**, and
only the bench could be wrong: the patch carries a comment forbidding the old wiring in capitals.

### `nanokontrol-bench.pd` — the nanoKONTROL acceptance run

**Six steps, and every one of them needs a hand on the controller** — nothing but the real device can
exercise `[ctlin]`. Load it as a third patch after `mother.pd` and `main.pd`. Steps 1–3 sweep the
surface; **4, 5 and 6 need your hands on the cable**. The fourteen steps that used to sit here never
touched the nanoKONTROL and moved to `display`, which is what they were always about.

⛔ **Hot-swap is THREE cases and it read as two.** 4 is a loss being SEEN, 5 is a device that was
never there being recovered, and **6 is the one that happens by accident** — a device you were
playing goes away and comes back. The first two sit either side of it and between them look like
full coverage: one proves the loss is noticed and the other proves some recovery happens, and
neither proves the controller under your hands comes back. Only `midi` had this case, for the Volca,
and only because the Volca's recovery is parasitic on another device being missing at the same time
(item 275). It is closed for the Launchpad (step 23) and the SP-404 (`midi` step 16) as well.

⚠️ **There is no SP-404 bench and no Volca bench.** Both live inside `midi`, which is named for the
concern — the mode-dependent map and both output devices — where `nanokontrol` and `launchpad` are
named for a device. `ref/device/sp404.md` and `ref/device/volca.md` both declare
`test/bench/midi-bench.pd`, so the pages resolve; the naming is the inconsistency, not the coverage.

Step 2 and step 6 are the regression gate on the display rewrite. Steps 7–14 are `display-bench`'s
assertions, re-run because the param layer they sit next to was rewritten.

⚠️ **No commas or semicolons in a message box** — both are message separators, so a comma in a
`PASS IF` string splits it and the remainder goes somewhere unhelpful (`canvas: no method for
'then'`). `display-bench.pd` says so and it caught this one out too.

⛔ **And no sentence may end on a bare number.** Pd parses `40.` as the float 40 and the full stop
**disappears from the printed line**, running two sentences together with nothing to show for it
(item 122). `bench-gen.py` asserted this from 2026-08-10, when the copy-edit below removed the last
eleven cases; before that it could only warn, because the transcribed text was full of them.

### `tempo-bench.pd` — the tempo acceptance run

Same shape again: thirteen steps, stepped by hand, a printed `PASS IF` before each one, covering
parameter pickup, the transport, the clamp and the 404 link. **Steps 1–11 drive themselves; 12 and
13 need your hands on the Organelle itself** — the aux button and knob 1 are the only controls
involved, and neither exists on a laptop.

⚠️ **The aux step's text carried two escaped commas inside its `PASS IF`.** `\,` satisfies the .pd
*parser*, but a message box still treats the comma atom as a separator — so that line printed as
**three fragments**. Both are now ` -- `.

⛔ **The three beat-count steps are gone, and they are the clearest case of the duplication rule
this project keeps rediscovering.** *Beat counts while stopped* asserted `c_clock`'s 1.5 ratio and
*Beat counts after stopping* asserted that a stop does not halt the timer — both already owned, more
tightly and in ~16 s, by `clock-assert.py` and `tempo-assert.py`. **Neither touched a device**: the
counters lived in the bench patch and printed to the runner's own terminal, so both step texts had to
admit there was nothing on the instrument to look at. *Zero the beat counters* armed them and nothing
else. ⚠️ **The cost of keeping them was `latest.json`** — one claim judged twice under two names
reports more coverage than exists, which is the `nanokontrol` duplication above, one level up.

**So `tempo-bench` no longer loads `c_clock`**, and the `#X declare` search path went with the
counters. Nothing it does now needs an abstraction from `Cut It/`.

Three steps carry the load:

| Step | Proves |
|---|---|
| **2** | **parameter pickup holds a restored knob.** The row reads `bpm 57 (10)` — the saved position, then where the knob is now — and the footer does not move. ⛔ Needs a `knobs.txt` saved off the rail or only the released branch is reachable |
| **5** | out-of-range clamps to the 5–600 legal range and warns **once per distinct value** — send the same value twice and the second must be silent |
| **9** | **the 404 follows a tempo change**, at 180 BPM. ⛔ Not 240: the 404 follows only between 40 and 200 and pins outside that window |

### `phone-bench.pd` — the phone acceptance run

**Fourteen steps, and the first bench whose subject is not the Organelle** — every `PASS IF`
describes what the *phone* shows. **PdParty has to be open on the `CutItRemote` scene before
step 1**, and step 1 exists to confirm that before anything depends on it.

Steps 8–11 are the ones whose correct result is that **nothing happens**: the level meters, the
grid vocabulary and the aux LED are all on `disp` and all deliberately dropped by `u_net`. A line
that starts reading `in-l` means the reserved branch is broken and the rate budget has gone to a
meter the phone does not draw.

⚠️ **The rate limit is not tested here and cannot be.** A step table pushes discrete messages; a
flood needs a metro. `phone-assert.sh` is what proves the coalescer. **Step 12 is the closest a
person can get** — a real fader, and the question of whether the phone *settles* on the value you
stopped at rather than one from the middle of the sweep.

**Steps 13 and 14 are the only way to reach item 114 on real hardware.** Closing PdParty makes the
phone answer with an ICMP port-unreachable, which destroys the socket; reopening it must bring the
display back within about five seconds **with nothing touched on the Organelle**. A link that could
not recover would be dead for the rest of the set and nothing on the instrument would say so.

## Reading a patch's box indices

### `--boxes` — ask, don't count

```sh
python3 test/gate/pd-layout-check.py --boxes "Cut It/u_state.pd"
```

Prints the index of every box exactly as `#X connect` counts them. **Use it before writing a
connect block by hand.** Pd numbers boxes by position in the FILE: comments count, `#X declare`
does not, a subpatch's contents do not but its closing `#X restore` does. Getting any of that
wrong shifts every later index and silently rewires the patch — which has bitten this project
five times, plus two near-misses while Phase 8 was written, both caught only by re-deriving the
indices by hand. That is what this flag is for.

The check itself now separates **PROBLEM** (structural — exits non-zero) from **note**
(cosmetic — does not). A crossed cord has never once meant the patch was wrong; a cord landing on
a comment always has.

### `pd-layout-check.py`

Not a patch — a static check on `.pd` files:

```sh
python3 test/gate/pd-layout-check.py "Cut It"/*.pd
```

Reports overlapping boxes, **connections drawn through unrelated boxes**, and content that
extends past the saved canvas size. Exits non-zero on any of them.

Layout is the only structural documentation Pd has, and the failure it was written for is
specific: a comment placed between the logic and a message column gets cords drawn straight
through it, which is invisible until you open the patch. Box sizes are estimated from the text
rather than measured, so it is a smell detector, not a renderer.

The diagnostic patches above predate it and do not pass — they are working references, not
examples of layout.

### Re-running `m_nano`'s decode test without the hardware

`m_nano`'s decode was verified by swapping `[ctlin]` for a three-outlet stand-in driven by
`nano-ch`, `nano-cc`, `nano-val` **in that order** — which is `ctlin`'s measured firing order made
explicit. To repeat it: copy `Cut It/` aside, replace the `ctlin` line in `m_nano.pd` with a
stand-in abstraction of that shape, and drive it. All 21 cases and the bug it found are recorded in
item 31. The firing order itself is item 23 and needs the real
device.
