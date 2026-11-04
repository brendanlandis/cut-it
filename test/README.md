# The tests

**Everything that decides whether Cut It works.** Two kinds, and the difference is the *oracle* —
who or what says pass:

| | Verdict from | Runs |
|---|---|---|
| `gate/` | **a program**, unattended | every commit, in about a minute, on the Mac |
| [`checklists/`](checklists/README.md) | **a person**, with the rig plugged in | when hardware behavior needs judging |

⛔ **A gate is not trusted until it has FAILED.** Reintroduce the bug, watch it go red, revert. This
project has shipped a gate that passed a broken patch 15/15, and one that had run its own driver
generator exactly never. Both looked green. See the **`gate`** skill.

⚠️ **The Mac is not the device.** The Phase 6 gate passed 25/25 on the Mac twice and shipped three
bugs. These prove a change did not break what was working; hands on the hardware are still the last
word.

## One gate per module

Twenty-three gates, and each answers for exactly one page: under `ref/`, or for `u_inject` and the
phone's checklist page, the checklists' guide. That is the whole organizing principle: **a page that names a gate should be able
to name one whose entire subject is that page**, or say `none` honestly. Five pages once named a single `phase6-assert.sh`, and two of those claims
were false.

| Gate | Checks | Answers for |
|---|---|---|
| `midi-emitters-assert.sh` | 7 | **no page** — see below |
| `init-assert.sh` | 16 | `module/boot` |
| `audio-assert.sh` | 12 | `module/audio` |
| `err-assert.sh` | 24 | `module/error` |
| `display-assert.sh` | 32 | `module/display` — the grid |
| `oled-assert.sh` | 63 | `module/display` — the OLED |
| `led-assert.sh` | 12 | `module/display` and `device/organelle` — the aux LED |
| `tempo-assert.sh` | 19 | `module/tempo` — `u_tempo` |
| `clock-assert.sh` | 22 | `module/tempo` — `c_clock` |
| `map-assert.sh` | 157: 86 in Lua, 71 in Pd | `module/map` |
| `recover-assert.sh` | 30 | `module/map` and `module/boot` — panic's second tier |
| `state-assert.sh` | 15 | `module/state` |
| `presence-assert.sh` | 43 | `module/presence` |
| `launchpad-assert.sh` | 19 | `device/launchpad` |
| `nano-assert.sh` | 65: 39 in Lua, 26 in Pd | `device/nanokontrol` |
| `organelle-assert.sh` | 56: 35 in Lua, 21 in Pd | `device/organelle` |
| `phone-assert.sh` | 102 | `device/phone` |
| `inject-assert.sh` | 9 | `test/checklists/README.md`, *Send lines* — `u_inject` |
| `touchosc-assert.sh` | 60: 9 read, 51 in Lua | `device/phone` — the phone's TouchOSC layout, the checklist page included |
| `sp404-assert.sh` | 62: 43 in Lua, 19 in Pd | `device/sp404` |
| `volca-assert.sh` | 10 | `device/volca` |
| `debug-assert.sh` | 35 | `module/debug` — the SECOND deployable |
| `sequencer-assert.sh` | 171: 115 in Lua, 56 in Pd | `module/sequencer` |

**1041 checks.** ⚠️ **Twenty-two of the twenty-three gates print their own `N checks` line and one does
not** — `midi-emitters-assert.sh` prints an inventory instead, so its 7 is hand-maintained and the
total cannot be derived from a run by summing. Totaling the run gives **1034**; the difference is
that gate. `sequencer-assert.sh`, `map-assert.sh`, `nano-assert.sh`, `organelle-assert.sh` and
`sp404-assert.sh` print two each, one per half: the Lua tests', then the analyzer's;
`touchosc-assert.sh` two as well, the reading first.
Worth knowing before trusting an arithmetic check of this number against a log.

⚠️ **`presence-assert.sh`'s 43 come from TWO Pd runs and one tally**, which is the only entry here
that does. The first run is the schedule at the shipped tick; the second scales `u_present`'s settle
and tick by ten and leaves its **counts** exactly as shipped, so the eighth re-wire and the give-up
actually happen — inside nine seconds rather than seventy-two. ⛔ **One analyzer reads both
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

### The shared machinery

| | |
|---|---|
| `lib_scratch.py` | imported by every gate that copies the patch. Holds the **one** `MIDI_EXPECT`, the stub rewrite, the private state directory and port, `u_net`'s sink, the generator status check and the watchdog. ⛔ It counts and rewrites boxes **by record**, through `lib_pd.py`, and forks nothing to do it |
| `scratch-gates.py` | one short recipe per scratch-copy gate: its required files, map rows, rewrites, driver and watchdog. Each `<gate>-assert.sh` is its header and one `exec` into it, so the path every page names still runs it |
| `lib_assert.py` | the check tally, the capture parser, and `require_capture` — a gate handed an empty capture must FAIL, not report nothing and exit 0 |
| `lib_drive.py` | window table → driver patch. Absolute delays off one `loadbang`, one delay per action, the `MARK` on the highest outlet |
| `lib_grid.py` | reassembles Launchpad SysEx. ⛔ Skips realtime bytes ≥ 248, which are legal *inside* a SysEx stream — `u_tempo` emits 96 a second |

⚠️ **The underscore in the four `lib_` files is not a slip.** A hyphen is not a legal Python
identifier, so a module that is *imported* cannot have one; a script that is only *run* can.

⚠️ **`u_net`'s sink is a socket in the gate's own process**, bound before Pd starts and held until
the gate exits, so its OSC lands somewhere known. Under Pd 0.49 a port with nothing bound answered
with ICMP and `u_net` raised `net-link-down` mid-run; 0.57 keeps the socket and that warning is gone
(2026-11-03). On macOS a second bind on a held port fails even with `SO_REUSEADDR`, so the bind is
checked.

⛔ **`MIDI_EXPECT` is an EXACT count per class, never "not zero".** A lower count means assertions
have gone vacuous; a higher one means an emitter no gate knows about. The gate it replaced checked
only for non-zero and its comment claimed five `[midiout]` where the patch has six — the count
drifted and nothing noticed.

## Running everything

```sh
./test/run.sh                every gate in one command, ~1 min, exit non-zero on any failure
```

**The gates run side by side**, all of them at once, each printed whole in table order, so the log
reads as a serial run's did. `CUTIT_JOBS=1 ./test/run.sh`
runs them one at a time. Each module gate's `main-dev.pd` copy gets its own inbound UDP port
(`CUTIT_INPORT`), and each gate's Pd runs with an empty `HOME` so it skips the Mac's Pd preferences —
see `test/runner/gates.py`.

Layout and graph structure, the documentation, all three entry points loading in silence, the MIDI
inventory, and one gate per module — the boot sequence, the audio path, the error bus, the display
arbiter, the OLED, the aux LED, the tempo reference, the clock, the map, panic's second tier, the
data store, the Launchpad, the nanoKONTROL, the Organelle's own panel, the phone, the SP-404, the
Volca and the debug patch. **Mac
only — it touches no device**, so it is safe to run at any time, including with the Organelle
switched off.

⚠️ **Run it before calling anything done.** Phase 8 edited `u_map`, `u_init` and `u_root` — files
Phases 5, 6 and 7 all rest on — and came within one step of shipping without re-running *their*
gates. The gates were all there, all passing, and all unused. **A gate you have to remember to run
is a gate that eventually does not run.**

⚠️ **`lp-monitor.pd` and `lp-step0.pd` are NOT here.** They were listed under
`test/` and they live in [tools/](../tools/README.md), where the directory-is-the-kind rule puts
them: they are probes a person runs, not tests with an oracle.

⛔ **`test/run.sh` runs nothing a person judges, and takes no options.** The hands-on half is
[checklists/](checklists/README.md), one Markdown file per area, read at the rig. It replaced the
bench runner on 2026-11-03: `--bench` and `--all`, the generated bench patches, `runner-assert.sh`
and the verdict file in `results/` all went, and every step's text is in the checklists.

## `display-assert.sh` and `launchpad-assert.sh` — no eyes and no hardware

```sh
./test/gate/display-assert.sh          32 checks, ~46 s — the ARBITER
./test/gate/launchpad-assert.sh        19 checks, ~15 s — the DEVICE
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
| `test/stubs/t_midiout.pd` | a stand-in for `[midiout]` that prints every byte with its port, and sends it on `t-midiout` for a driver playing the device |
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

**32 checks**: frame shape and the 1–108 span, the mode lamp index, mode 1's drum page with the
beat row giving way to it, the modal claiming all 108 specs, `fail` painting red and `warn` painting nothing, the alert expiring back to the modal
underneath, the beat row never leaving 11–18, the grid SURVIVING a panic, and
`m_launchpad`'s Programmer and Live SysEx.

✅ **It has been proven to fail.** Reintroducing the one-based beat bug in a scratch copy — the
beat-row offset back to `+ 11` — makes it report `lit outside every region: [(19, 3)]` and exit 1.
⚠️ **The three `home-*` checks still passed under that mutation**, which is exactly why *seven
beats out of eight looked perfect*: only the six-second beat-row window catches it. A gate that
cannot fail is worth nothing, so re-run that mutation if you ever change the analyzer.

**`launchpad-assert` plays the device for the Setup tap** (2026-11-04). Its driver watches
`t-midiout` and answers every Programmer Mode entry 1 ms later with the announcement the Launchpad
makes, until a window mutes it; between, it sends the announcement unasked, and three frames that
are not it. ✅ **Red on each of eight mutations:** the heartbeat raising no expected echo (1
failed: the echoes published), the init raising none (3), the 250 ms forget cut (2), the match
waiting for another layout (4), a mismatch never clearing the match (2), mode 1's `lp-setup` row
gone from the map (2), `t_midiout` not sending on `t-midiout` (1: nothing was answered) and the
driver never muting (1: the forget's witness).

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
`[threshold~]`. With DSP off every count is zero, which reads exactly like a dead clock; `-noaudio`
does not turn it off (item 280).

**What it protects:** 24 PPQN at two tempos and the **ratio** between them (which cancels the
real-time scheduler entirely); that the clock leaves on **both** ports, since a fan-out that lost one
would look perfect on the other; the clamp warning at both ends and *not* warning in range; start
250, stop 252, panic 252, and ⛔ that **Continue (251) is never sent**; and ⛔ that **stop does not
halt the clock** — the transport pauses the subscribers, it does not clear the timer.

## `map-assert.sh`, `sp404-assert.sh`, `volca-assert.sh` — the map and the output devices

```sh
./test/gate/map-assert.sh            86 + 71 checks, ~19 s — u_map's rules in Lua, then the lookup and the static lint
./test/gate/sp404-assert.sh          43 + 19 checks, ~7 s — the 404's decode in Lua, then BOTH directions
./test/gate/volca-assert.sh          10 checks, ~5 s — four destinations, one channel
```

Each takes `-v` for the detail behind every check and `--keep` to leave the scratch directory and
capture behind. **They were one gate, and it claimed three pages at once** — the map's page, the
404's and the Volca's — which is exactly the false-coverage this refactor exists to remove. The
split reconciles upward: 28 checks became 34, because each gate could then say things the shared one
had no window for.

⚠️ **`map-assert` uses `volca-cc` and asserts nothing about the Volca.** A lookup has to land
somewhere; what the destination then does with the value is the device gate's business.

**`map-assert` runs the map's Lua tests first**: `test/gate/lua/u_map_test.lua`, with lua.org's Lua
5.4 and no Pd, drives the rules in `Cut It/u_map.lua` (the table, the lookup per mode, the divisor,
the mode guard, every pickup transition, the raw row and its two exemptions) and `u_map-lua.pd_lua`
through `test/gate/lua/lib_test.lua`'s stand-in for pdlua (reading the table from its patch's
folder, `map-empty`, `bad-selector`, a throwing rule caught as `fail u_map lua-param`). The Pd half
below is unchanged since the lookup was Pd: **it is the proof the Lua port changed nothing.** The
gate fails if either half does.

**Half of the Pd half is a STATIC LINT.** It parses the literal `route` box out of `u_map.pd` and the rows
out of `cut-it-map.txt` and asserts that **every destination a row can name exists as an argument on
that route** — the allowlist guard, enforced by reading, exactly the way this project audits its
global sends. It also catches a **duplicate `(mode, control)` pair**, which the lookup resolves
to the *first* row only, so a repeat is dead and silent. And it reads every `m_` file's `[s disp]`
count, **exactly** — zero everywhere but `m_organelle`'s one, which carries aux's modal — because a
device layer posting a control's row beside `u_map`'s draws that control twice, and a duplicate of an
*unmapped* control's row is invisible on the screen (item 317). That half runs without Pd at all.

The other half of each gate rewrites the MIDI object boxes in a scratch copy — **all seven classes, from the one
`MIDI_EXPECT` in `test/gate/lib_scratch.py`**, shared with every other gate that makes a copy. ⛔
**`[midiout]` alone was never enough**: `m_volca` and `m_404` emit through `noteout` / `ctlout` /
`pgmout`, so a rewrite of `midiout` only finds nothing in them and every assertion about them passes
**vacuously**. ⛔ **And the two input stubs are not optional**: every *output* path can be driven from
a bus, but `m_404`'s receive side sits behind `[notein]` and `m_nano`'s *entire surface* sits behind
`[ctlin]`, and **no bus reaches a MIDI input**. ⛔ **`[polytouchin]` is the one class left with no
stub, and it was in NEITHER list until `scan_unknown` asked the question as a closed one** —
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
scheduler tick, so it proved *drops-rather-than-queues* and nothing about the interval. Since the
limiter became a token bucket (16 at once, one per 5 ms), the burst asserts exactly 16 of 20, and a
refill window drains the bucket and fires two more pads 2 and 12 ms after it: the first must drop
and the second pass. Red against the old 5 ms gap, an instant refill, and an uncapped bucket.

**One row per control** (item 317) was made to fail against the `m_nano`, `m_404` and `m_launchpad`
that still posted their own rows: four red in `nano-assert` — an unmapped slider drawn twice, a
mapped one drawn as `slider-1` beside `volca-cc41`, the 404's CTRL knob and a Launchpad ring button —
two in `sp404-assert`, and the static count; the file-set check went red on a stray `m_` file.
**The pressure exemption** (item 318) went red against the `u_map` without it, with the key and
pressure tests swapped so the key test reopened the spigot, and — on the witness pad, then `pad-15` and now `pad-45` — with a
test wide enough to silence every raw row.

✅ **And again against the Lua**, both halves red on each of six mutations of `u_map.lua` (Lua
failures, then Pd): the lookup reading mode 1's rows in every mode (3, 3), pickup arming on the wrong
side (2, 2), the mode guard taking one atom (6, 5), pressure drawing a raw row (1, 1), no release on
reaching a rail target (1, 1) and the boot window never shutting (2, 1); a `live` that sets nothing
turned the Lua (3) and `recover-assert` (1) red. Knob 1 held at 120 with no `knobs.txt`
(2026-11-04): the face never asking for the file turned the Lua (1) and the Pd half's no-`knobs.txt`
run (5) red, and an empty `R.UNSAVED` the Lua (an error) and that run (2). The
allowlist stayed a Pd `route`, so its mutations are there: the reject cut from `unknown-dest` turned
the Pd half red (1), and a destination added to the route that nothing handles turned `docs-check`
red, as the guard's three sides intend.

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
trick), no hardware. It works entirely inside its own scratch directory and never touches
`Cut It/`, `/sdcard/cut-it-state` or the device.

**What it protects, stated as properties rather than proxies:** the two policies never leak into
each other; re-putting a key REPLACES its line; **a contributor answering behind a `[del]` is
absent from the file** — the synchronous contract itself; manual is replayed before auto so auto
wins a duplicate key; **a boot does not overwrite saved state before reading it**; and both entry
points load in **silence**, which is `tools/deploy.sh`'s own gate.

⚠️ **It passed the broken patch on its first can-it-fail run** — the driver banged the restore at
600 ms when the bug needs it after 3000 ms, and the final check asserted against a value nothing
drove. **The 3600 ms in the driver is load-bearing**; shortening it re-blinds the gate. Proven
both ways now: 15/15 clean, 2 failures with the bug reintroduced. The driver is an OUTPUT,
generated into the scratch directory on every run — edit `state-assert-drive-gen.py`. None is
committed.

## `phone-assert.sh` — the same idea, and much cheaper

```sh
./test/gate/phone-assert.sh            # ~60 s, exits non-zero on any failure
```

**Phase 7's gate needs no scratch copy and rewrites nothing.** `[midiout]` is a built-in class
with no side channel, which is the whole reason `display-assert.sh` has to swap it for a stand-in
in a throwaway copy of the patch. **`u_net` already emits to a socket** — so the gate binds
`127.0.0.1:9995`, instantiates `u_net 127.0.0.1 9995 9994` and reads the real datagrams, then sends
commands *into* 9994 to drive the inbound half. `Cut It/` is never touched.

**The other end of the inbound vocabulary, what the phone's buttons send, is `touchosc-assert`'s**
(below): the layout and `u_net` deploy by different routes, and their spellings must not drift.

| Piece | |
|---|---|
| `phone-assert-drive-gen.py` | generates the driver into the scratch directory on every run — it instantiates `u_net` and pushes synthetic traffic onto `disp`. **Edit this**; no driver is committed |
| `phone-assert.py` | binds the port, launches Pd, decodes OSC, does the reasoning |

⚠️ **The analyzer owns the lifecycle, and that is not tidiness.** It binds the socket *before*
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
✅ **And for the drums lane** (2026-11-04): `u_net`'s cord from it to `c_steps` cut, 9 failed. In
`map-assert` a drums row naming `lastt` failed its lint, and `u_map` dropping the knob's value
(`list split 1`) failed `sequencer-assert`'s Pd half (14).

## `touchosc-assert.sh` — the phone's layout, read and run

```sh
./test/gate/touchosc-assert.sh       9 + 51 checks, ~1 s — the layout read, then its scripts run
```

**Two halves, two tallies.** First, by reading `tools/touchosc/CutIt.tosc`: it is `build.py`'s
output; every control has a name of its own, since a script finds a control by name and TouchOSC
returns the first of two; and what its buttons send equals what `u_net` routes and `c_steps` takes,
**the inbound vocabulary read from both ends**. The phone is the only sender there is, and the
layout and `u_net` deploy by different routes, `push.sh` and `tools/deploy.sh`, so their spellings
could drift apart with nothing failing until somebody is at the rig. Every acknowledgment `u_net`
sends must light a button. **And every pairing meets WCAG AA contrast as TouchOSC draws it**: each
label against what lies under it, 4.5:1 or 3:1 for large text, each control's outline against the
page, 3:1, and each tab's text and states, from the resting fill TouchOSC draws at 26% of a color
(measured, TouchOSC's Reference page).

Then the layout's own scripts, unpacked into the scratch directory and run by
`test/gate/lua/touchosc_test.lua` under `test/gate/lua/lib_touchosc.lua`, a stand-in for TouchOSC as
`lib_test.lua` is for pdlua: the tabs following the mode, test mode bringing up the checklists and
sending them back, the drum screen's state and sliders (a value from Cut It never sent back), the
remote screen's rows and buttons, the checklist page's Send, Pass, Fail, Back and Next, worked out
from the checklists themselves, and NO-LINK. **What it cannot judge is how TouchOSC draws**; the
phone checklist is the oracle for that.

✅ **Proven red** (2026-11-04): test mode never changing the tab (Lua 1 failed), a pad sending
`drums selec` (read 2, Lua 1), and the checklist page sending a Send line's numbers as text (Lua 1).
✅ **And again for the redesign**: grey text too dim for AA (read 1, Lua 1), a time signature box
sending one step for a drag across two (Lua 1), and answers lighting a button by its value rather
than its color, which sends its command again (Lua 9).
✅ **And for the pads** (2026-11-04): a pad sending when the state lights it, which bounced four
selections between Cut It and the phone, failed 2; the old `u_net`, with no heartbeat on a flip of
test mode, failed `phone-assert`'s two "at once" checks, 299 and 99 ms late; and with no cord
from a mode to the flip, a mode chosen in test mode left it on, failing 3.

## `sequencer-assert.sh` — the drum machine, from the outside

```sh
./test/gate/sequencer-assert.sh      115 + 56 checks, ~31 s — c_steps' rules in Lua, then the drum page and the pattern on disk
```

**Two halves, two tallies.** First `test/gate/lua/c_steps_test.lua`, with lua.org's Lua 5.4 and no
Pd: the rules in `Cut It/c_steps.lua` press by press (the levels, the step rule's three cases, the
selected track, which pads fire, the restore), and `c_steps-lua.pd_lua` through
`test/gate/lua/lib_test.lua`'s stand-in for pdlua (its inlets and outlets, `bad-selector`, a
throwing rule caught as `fail c_steps lua-fire`). Then the Pd half below, on a running copy of the
instrument, which is unchanged since the rules were Pd: **it is the proof the Lua port changed
nothing.** The gate fails if either half does.

It plays mode 1's drum page on `param`, as `m_launchpad` publishes it, from a state directory
seeded with a pattern, and reads only what leaves the patch: the 404's notes, the grid's frames, the
state bus and `cut-it-auto.txt`. **A note's step is the playhead of the frame painted after it** —
`c_steps` sends a step's notes and its playhead in one logical instant, and the frame clock paints
within 20 ms, six times inside a sixteenth at 120 BPM — so every step's exact notes are asserted
without a timestamp. The tempo is set by the driver, and PLAY to STOP is counted: 21 steps. Knob 2
is held at 16 and then sets the last step to 3 before PLAY again, which must walk 1 2 3 1 2. Then
knob 3 gives track 2 a last step of 6, and nine steps are checked against two loops, 3 and 6, note
by note. Last, the drum screen's `snap` is sent as the phone sends it, OSC to `u_net`'s own port
(`CUTIT_INPORT`), so the cord from `u_net` to `c_steps` in `u_root` is under test too.

✅ **Proven red before it was trusted**: with `c_steps` absent (the known exit 2), against the patch
before the sequencer was wired (20 of 28), and on eight mutations — the step rule inverted, PLAY not
parking the counter, no put after a restore, panic ignored, eighths for sixteenths, `m_404`'s old
5 ms gap, the brightness ramp one hue off, and two velocity rows swapped in the layout table.
✅ **And again against the Lua**, both halves red on each of three mutations of `c_steps.lua`: the
step rule inverted (Lua 6 failed, Pd 12), the velocity levels off by one (5, 9), and a step reading
the next step's notes (5, 3). A rule that throws turns the Pd half red with `fail c_steps lua-fire`
on `err`, and a syntax error with silence (18 failed); the Lua half dies on both with a traceback.
✅ **And for the level `c_steps` sends** (2026-11-04): velocities sent to the page as they were
before (Lua 5 failed, Pd 12), and every level one too high (3, 12).
✅ **And for one velocity row** (2026-11-03), against the old step rule and the old color ramp
together: Lua 1 failed, Pd 12; with the old map, a press on the freed row was a `layout-miss`.
✅ **And for the last step**: PLAY parking the counter at 15, as it did, started PLAY again on step 2
with the last step at 3 (4 failed). 3, not 4, because a last step that divides 16 hides it. Without
`u_root`'s cord from `u_net` to `c_steps`, the snap never landed (3 failed).

⚠️ **The layout table is read, not restated**, so a frame is decoded with the same table the patch
paints from. The analyzer's expectations are what keeps that honest: the driver presses `pad-26`
and expects level 2, so a table that moves the button is caught.

## The device layers' Lua halves

```sh
./test/gate/nano-assert.sh           39 + 26 checks, ~17 s — the decode in Lua, then the channel gate
./test/gate/organelle-assert.sh      35 + 21 checks, ~20 s — the keyboard's names in Lua, then the panel
./test/gate/sp404-assert.sh          43 + 19 checks, ~7 s — the pad map both ways and the budget, then the 404
```

**A device layer whose decoding is Lua runs its Lua tests first**, as the map and the sequencer do,
with lua.org's Lua 5.4 and no Pd. `test/gate/lua/m_nano_test.lua` drives `Cut It/m_nano.lua`: all
fifty names by tens and units, a button's press as 1 and its release as nothing, the unmapped
warning, and that no name outlives its message. `test/gate/lua/m_organelle_test.lua` drives
`Cut It/m_organelle.lua`: each key's name, the layer `aux` held when it went down, a chord across a
change of modifier. `test/gate/lua/m_404_test.lua` drives `Cut It/m_404.lua`: the pad map read both
ways, the ten bank letters, a note outside the map naming nothing, the bank's channel, and the
budget's size, refill and cap. Each also drives its face through `lib_test.lua`'s stand-in for pdlua: its
inlets and outlets, `bad-selector`, and a throwing rule caught as `fail <layer> lua-<bus>`. Each Pd
half is unchanged since its layer was Pd: **it is the proof the port changed nothing.**

✅ **Both halves red on each of four mutations of `m_nano.lua`** (Lua failures, then Pd): a button's
release passed (4, 1), the units digit off by one (18, 14), the transport row continuous (2, 2) and
an unmapped CC silent (8, 1). **On each of three of `m_organelle.lua`**: no latch, the live
modifier naming every edge (3, 1); the latch rewritten on the release (3, 1); and the release dropped
(7, 3). **And on each of five of `m_404.lua`**: the `47 + n` map (12, 5, and `docs-check` red from
pad 5), a bucket of 20 (2, 2), the bank one channel high (10, 3), the bank
letters shifted (10, 7), and the refill added only after a drop (7, 5).

✅ **And `lua-face.lua`, which all five faces share** (2026-11-04): with no bang on `init`, each of
the five Lua tests went red (1 to 3 failed); with a rule run outside `pcall`, each died on its
throwing rule.

## `stubs/` — stand-ins the gates need

`t_midiout.pd` replaces `[midiout]` so a headless run can read back every byte the patch emits,
and sends each on `t-midiout`, so a driver can answer as a device would: `launchpad-assert`'s
answers every Programmer Mode entry with the announcement the Launchpad makes.
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

## The checklists

**[checklists/README.md](checklists/README.md)** has the list, how to read a step, how to put a
**Send** line on the buses from the Mac, and the rules for writing one. A step there is a promise
about something a person sees, hears or reads on the rig; whatever a program can check without eyes
belongs in a gate here instead.

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

Reports overlapping boxes, **connections drawn through unrelated boxes**, content that extends past
the saved canvas size, and ⛔ **connects that name a box defined LATER in the file**. Exits non-zero
on any of them.

⛔ **That last one is C-10's second half, and Pd is silent about it in every way that matters.** The
rule says append boxes at the end and move the connects with them — and it is easy to move the NEW
connects while an EDITED one still sits in the original block, hundreds of lines above the box it
now names. Pd replays a canvas top to bottom, finds no such object, drops the cord, and **loads
anyway**. The patch is simply not wired.

⚠️ **Pd does print `connect: no such object`, and that is not a defense.** A menu-launched patch
runs `-nogui` with stdout on tty1, `tools/deploy.sh` gates on output only before ~735 ms, and a gate
reading a capture is not looking for it. It caused two silent miswirings in one session — a presence
publish that never fired, and mode selection that stopped working outright — and both looked exactly
like a logic error in the new code. The check is exact rather than heuristic: it is what Pd itself
does.

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
