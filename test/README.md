# The tests

**Everything that decides whether Cut It works.** Two kinds, and the difference is the *oracle* —
who or what says pass:

| | Verdict from | Runs |
|---|---|---|
| `gate/` | **a program**, unattended | every commit, in about a minute, on the Mac |
| [`checklists/`](checklists/README.md) | **a person**, with the rig plugged in | when hardware behavior needs judging |

⛔ **A gate is not trusted until it has FAILED.** Reintroduce the bug, watch it go red, revert. This
project has shipped a gate that passed a broken patch 15/15, and one that had run its own driver
generator exactly never. Both looked green. See the **`gate`** skill. **One proof per behavior, once
Brendan likes what he hears** (`AGENTS.md`, *How work ships*): not one per check, and not written
down here; git has the old lists.

⚠️ **The Mac is not the device.** The Phase 6 gate passed 25/25 on the Mac twice and shipped three
bugs. These prove a change did not break what was working; hands on the hardware are still the last
word.

## One gate per module

Twenty-six gates, and each answers for exactly one page: under `ref/`, or for `u_inject` and the
phone's line check page, the checklists' guide. That is the whole organizing principle: **a page that names a gate should be able
to name one whose entire subject is that page**, or say `none` honestly. Five pages once named a single `phase6-assert.sh`, and two of those claims
were false.

| Gate | Answers for |
|---|---|
| `midi-emitters-assert.sh` | **no page** — see below |
| `init-assert.sh` | `module/boot` |
| `audio-assert.sh` | `module/audio` |
| `err-assert.sh` | `module/error` |
| `display-assert.sh` | `module/display` — the grid and its painter, every page |
| `oled-assert.sh` | `module/display` — the OLED |
| `led-assert.sh` | `module/display` and `device/organelle` — the aux LED |
| `tempo-assert.sh` | `module/tempo` — `u_tempo`, tap tempo and the phone's tempo |
| `clock-assert.sh` | `module/tempo` — `c_clock` |
| `map-assert.sh` | `module/map` |
| `recover-assert.sh` | `module/map` and `module/boot` — panic's second tier |
| `state-assert.sh` | `module/state` |
| `song-assert.sh` | `module/songs` — the songs, the setlists, the keys and the next arrow, the sections, the top row, save and revert, the files |
| `voices-assert.sh` | `module/voices` — the song's voices, the page, and the controls in play |
| `presence-assert.sh` | `module/presence` |
| `launchpad-assert.sh` | `device/launchpad` |
| `nano-assert.sh` | `device/nanokontrol` |
| `organelle-assert.sh` | `device/organelle` |
| `phone-assert.sh` | `device/phone` |
| `inject-assert.sh` | `test/checklists/README.md`, *Send lines* — `u_inject` |
| `touchosc-assert.sh` | `device/phone` — the phone's TouchOSC layout, the line check's page included |
| `volca-assert.sh` | `device/volca` |
| `debug-assert.sh` | `module/debug` — the SECOND deployable |
| `sequencer-assert.sh` | `module/sequencer` |
| `kit-assert.sh` | `module/sequencer` — the kit and its effects, the reverb's three types among them, as a signal |
| `synths-assert.sh` | `module/synths`, and `device/streichfett` and `device/nanokey`, its two layers |

⚠️ **`presence-assert.sh` tallies TWO Pd runs as one**, which is the only entry here
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
`device/organelle` were the last three, and each has its own gate now. ⛔ **`audio-assert.sh` and
`kit-assert.sh` are the two that read a SIGNAL back** — the first records `u_root`'s output to a
soundfile and asserts the passthrough is not silent, not swapped and not attenuated, that a drum
reaches the left alone, and that nothing reports a level, since the info bar is the meter; the second
records `c_kit`'s drums and asserts their levels, silences and retrigger, and a track's volume and
pitch, read back as a level, a frequency and a length, and the distortion's: more drive never
quieter, a sample driven by its own peak, and soft, hard, fold and crush each a shape of its own,
read back as a level, a crest, a lopsidedness, crossings a cycle and whether a 441 Hz sine still
repeats every hundred samples, and the reverb's three types, each told apart by when a click's
reverb starts. Every other gate here
asserts on messages, which is what made the audio path invisible for as long as it was.

**`midi-emitters-assert.sh` belongs to no device on purpose.** Its only claim is structural — *these
are all the MIDI objects in the patch* — and a new `[noteout]` in some future `e_` stage is not the
Volca's business, but very much the instrument's. It needs no Pd and takes ~200 ms.

### The shared machinery

| | |
|---|---|
| `lib_scratch.py` | imported by every gate that copies the patch. Holds the **one** `MIDI_EXPECT`, the stub rewrite, the private state directory and port, `u_net`'s sink, the generator status check and the watchdog. ⛔ It counts and rewrites boxes **by record**, through `lib_pd.py`, and forks nothing to do it |
| `scratch-gates.py` | one short recipe per scratch-copy gate: its required files, map rows, rewrites, driver and watchdog. Each `<gate>-assert.sh` is its header and one `exec` into it, so the path every page names still runs it |
| `lib_assert.py` | the check tally, the capture parser, and `require_capture` — a gate handed an empty capture must FAIL, not report nothing and exit 0 |
| `lib_drive.py` | window table → driver patch. Absolute delays off one `loadbang`, one delay per action, the `MARK` on the highest outlet; `extra` adds boxes a window reaches by name, as `synths-assert`'s socket into `u_net` |
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

**The gates in `scratch-gates.py` run under Pd's `-batch`**, which computes as fast as it can, so a
gate that plays 46 seconds of logical time takes under 2, and a busy Mac can't make one miss its
windows (2026-11-05). `GATE_REALTIME=1` runs them on the clock, to compare. `-batch` polls no socket,
so a driver's OSC reaches `u_net` through `lib_scratch`'s `net_direct`, the same bytes into the same
`oscparse`. `phone-assert` (about 67 s, and so the suite's floor), `inject-assert` and
`state-assert` keep real time: real UDP is what the first two are for.

**The gates run side by side**, all of them at once, each printed whole in table order, so the log
reads as a serial run's did. `CUTIT_JOBS=1 ./test/run.sh`
runs them one at a time. Each module gate's `main-dev.pd` copy gets its own inbound UDP port
(`CUTIT_INPORT`), and each gate's Pd runs with an empty `HOME` so it skips the Mac's Pd preferences —
see `test/runner/gates.py`.

Layout and graph structure, the documentation, all three entry points loading in silence, the MIDI
inventory, and one gate per module — the boot sequence, the audio path, the error bus, the display
arbiter, the OLED, the aux LED, the tempo reference, the clock, the map, panic's second tier, the
data store, the songs, the voices, the Launchpad, the nanoKONTROL, the Organelle's own panel, the phone and its layout, the
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
./test/gate/display-assert.sh          66 + 46 checks, ~46 s — the drum page's painter in Lua, then the ARBITER
./test/gate/launchpad-assert.sh        19 checks, ~15 s — the DEVICE
```

Both take `--keep` to leave the byte capture behind to read. **They were one gate**, which is why
five pages once named it and two of those claims were false: it tested nothing about the
nanoKONTROL and nothing about the OLED.

**This is the part that asserts what the grid is actually showing.** The bench used to claim in its
own header that *"there is no way to read back what the LEDs are actually showing"* — too strong,
and it conflated three different things. Pd cannot ask the Launchpad what is lit, but **the bytes
the patch sends are completely knowable**, and that is the right level to test our own code at.

⚠️ **The split is not cosmetic — it is 46 seconds.** `display-assert` needs DSP, because the beats repaint
an idle page; the two SysEx checks about the *device* need no clock at all and were
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

**It checks:** frame shape and the 1–108 span, a page saved at power-off being the first painted, the voices' lamps,
each page through a press, the columns', aux's and Setup's, the modal claiming all 108 specs, `fail` painting red and
`warn` painting nothing, the alert expiring back underneath, PLAY bringing up the performance page, the grid SURVIVING a panic, and
`m_launchpad`'s Programmer and Live SysEx.

**It runs the drum page's painter's Lua tests first** (2026-11-05): `test/gate/lua/g_grid_test.lua`,
with no Pd, drives `g_grid.lua` and its face through `lib_test`'s stand-in for pdlua, which carries
a `pd.Table` over arrays the test makes. **66 checks**: the colors read through `g_grid.pd`'s own
RGB table and held to the page's, the layout's 60 cells in its order, every cell at load, the rows
of steps at 4/4, 3/4, 9/8, 7/8, 5/4 and `bar 0`, the levels, a step past the last step dark, the
playhead, the buttons, the pads and the repeat pads, the pads whose tracks won't play, dim, what
changes nothing, `init`, and the face: the writes into the frame buffer and nowhere else, a buffer
made after it, `bad-selector`, `no-surface`, a missing layout, a throw, and `g_grid.pd` making it
and no longer reading the layout itself. What reaches the Launchpad is the Pd half's, and
`sequencer-assert`'s.

**`launchpad-assert` plays the device for the Setup tap** (2026-11-04). Its driver watches
`t-midiout` and answers every Programmer Mode entry 1 ms later with the announcement the Launchpad
makes, until a window mutes it; between, it sends the announcement unasked, and three frames that
are not it. ✅ **Red on each of eight mutations:** the heartbeat raising no expected echo (1
failed: the echoes published), the init raising none (3), the 250 ms forget cut (2), the match
waiting for another layout (4), a mismatch never clearing the match (2), the `lp-setup` row
gone from the map (2), `t_midiout` not sending on `t-midiout` (1: nothing was answered) and the
driver never muting (1: the forget's witness).

## `tempo-assert.sh` — two kinds of check, because neither is enough

```sh
./test/gate/tempo-assert.sh          33 + 35 checks, ~24 s — tap tempo's rules in Lua, then the clock, the taps and the phone's tempo
```

**It runs tap tempo's Lua tests first**: `test/gate/lua/u_tempo_test.lua`, with no Pd, drives
`Cut It/u_tempo.lua` (the first tap, the average of the last four intervals, the two-second gap,
two taps in one instant, the clamp, the phone's tempo and `bad-tempo`) and `u_tempo-lua.pd_lua`
through `lib_test.lua`'s stand-in for pdlua, and reads `[clip 5 1000]` out of `u_tempo.pd` so the
Lua's range cannot drift from the patch's. The gate fails if either half does.

`u_tempo` is the instrument's interval timer: it publishes a beat on a bus that `g_grid`, every
`c_clock` and every future effect stage subscribe to, and writes MIDI clock to the wire at 24 pulses
per quarter note. **Nothing read those bytes back** until this existed.

| Half | Owns |
|---|---|
| a **static lint** — reads `[clip 5 1000]` and `[* 24]` out of `u_tempo.pd`, ~1 ms, no Pd | the **bounds** |
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
real-time scheduler entirely); ⛔ that the clock leaves on **port 1 alone**, and the transport's STOP
too, with panic's on 1 and 4 — exact sets, so nothing reaches port 3, the SP-404's until it left the
rig; the clamp warning at both ends and *not* warning in range; start 250, stop 252, panic 252, and
⛔ that **Continue (251) is never sent**; and ⛔ that **stop does not halt the clock** — the transport
pauses the subscribers, it does not clear the timer. Then **tap tempo through the running
instrument**: the nanoKONTROL's LOOP pressed as `param xport-4`, 400 ms apart, puts 150 on the tempo bus
from the second tap, and ⛔ **knob 1 held at it**: turned short of 150 it moves nothing and reads
`bpm 150 (105)`, turned through it it sets 170; 2.5 s later a tap sets nothing, and the next, 600 ms
on, 100; a pad on the drum page, cell 21, sets nothing; and **the phone's tempo** as a
datagram into `u_net`'s port, 133 to the bus, knob 1 held at it too, 900 clamped to 600, and a word
refused as `bad-tempo`.

## `map-assert.sh` and `volca-assert.sh` — the map and the output device

```sh
./test/gate/map-assert.sh            103 + 86 checks, ~19 s — u_map's rules in Lua, then the lookup and the static lint
./test/gate/volca-assert.sh          10 checks, ~5 s — four destinations, one channel
```

Each takes `-v` for the detail behind every check and `--keep` to leave the scratch directory and
capture behind. **They were one gate, and it claimed three pages at once** — the map's page, the
404's and the Volca's — which is exactly the false-coverage this refactor exists to remove. The
split reconciles upward: 28 checks became 34, because each gate could then say things the shared one
had no window for. The third, `sp404-assert`, went with the SP-404 when it left the rig
(Brendan, 2026-11-04), and so did `map-assert`'s `404-pad` row.

⚠️ **`map-assert` uses `volca-cc` and asserts nothing about the Volca.** A lookup has to land
somewhere; what the destination then does with the value is the device gate's business.

**`map-assert` runs the map's Lua tests first**: `test/gate/lua/u_map_test.lua`, with lua.org's Lua
5.4 and no Pd, drives the rules in `Cut It/u_map.lua` (the table, the lookup per page, an `all` row and `pad-*`, every
row's arg against what its destination takes, the divisor, the page guard, every pickup transition, what `u_perform` hears, an
unmapped control leaving nothing) and `u_map-lua.pd_lua`
through `test/gate/lua/lib_test.lua`'s stand-in for pdlua (reading the table from its patch's
folder, `map-empty`, `bad-selector`, a throwing rule caught as `fail u_map lua-param`). The Pd half
below is unchanged since the lookup was Pd: **it is the proof the Lua port changed nothing.** The
gate fails if either half does.

**Half of the Pd half is a STATIC LINT.** It parses the literal `route` box out of `u_map.pd` and the rows
out of `cut-it-map.txt` and asserts that **every destination a row can name exists as an argument on
that route** — the allowlist guard, enforced by reading, exactly the way this project audits its
global sends. It also catches a **duplicate `(page, control)` pair**, which the lookup resolves
to the *first* row only, so a repeat is dead and silent. And it reads every `m_` file's `[s disp]`
count, **exactly** — zero everywhere — because a
device layer posting a control's row beside `u_map`'s draws that control twice, or names an unmapped
one, which draws nothing since 2026-11-04 (item 317). That half runs without Pd at all.

The other half of each gate rewrites the MIDI object boxes in a scratch copy — **all seven classes, from the one
`MIDI_EXPECT` in `test/gate/lib_scratch.py`**, shared with every other gate that makes a copy. ⛔
**`[midiout]` alone was never enough**: `m_volca` emits through `noteout` / `ctlout` / `pgmout`, as
`m_404` did, so a rewrite of `midiout` only finds nothing in it and every assertion about it passes
**vacuously**. ⛔ **And the two input stubs are not optional**: every *output* path can be driven from
a bus, but the Launchpad's pads sit behind `[notein]` and `m_nano`'s *entire surface* sits behind
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
one test that changes the page silently rewrites the starting conditions of every test after it. That
cost a wrong diagnosis once: item 232.

**Proven to fail** — the shared gate was, on a `47 + n` pad map (12 of 16 pads, both directions), a row naming a
non-existent destination, and a duplicate row. ⛔ **It PASSED a disarmed rate limiter on the first
try** — the SP-404's, whose burst window fired in one logical instant, and `[del 0]` still defers to
the next scheduler tick, so it proved *drops-rather-than-queues* and nothing about the interval. Any
rate limit tested again needs two events a real millisecond or two apart.

**One row per control** (item 317) was made to fail against the `m_nano`, `m_404` and `m_launchpad`
that still posted their own rows: four red in `nano-assert` — an unmapped slider drawn twice, a
mapped one drawn as `slider-1` beside `volca-cc41`, the 404's CTRL knob and a Launchpad ring button —
two in `sp404-assert`, and the static count; the file-set check went red on a stray `m_` file, and
again with `m_404.pd` put back after the SP-404 left the rig (2026-11-04).
**The pressure exemption** (item 318) went red against the `u_map` without it, with the key and
pressure tests swapped so the key test reopened the spigot, and — on the witness pad, then `pad-15` and now `pad-45` — with a
test wide enough to silence every raw row.

⛔ **It also HUNG once instead of failing** — the driver generator errored, its exit status was
unchecked, Pd was handed a file that did not exist, and the `; pd quit` that lives *inside that file*
never fired. **A gate that hangs is worse than one that fails.** The generator's status and the
driver's existence are checked now, behind a 40 s watchdog.

Each driver is an OUTPUT, generated into the scratch directory on every run — edit `map-assert-drive-gen.py` or `volca-assert-drive-gen.py`. None is committed.

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
./test/gate/phone-assert.sh            # ~65 s, exits non-zero on any failure
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
| `phone-assert-drive-gen.py` | generates the driver into the scratch directory on every run — it instantiates `u_net`, feeds its four inlets as `u_root`'s cords would, taps its three outlets, and puts the OLED's traffic on `disp` to prove `u_net` ignores it. **Edit this**; no driver is committed |
| `phone-assert.py` | binds the port, launches Pd, decodes OSC, does the reasoning |

⚠️ **The analyzer owns the lifecycle, and that is not tidiness.** It binds the socket *before*
Pd starts, because a UDP connect to a port with nothing listening survives exactly one datagram
(item 114). Start the driver by hand and you get one packet and then silence — which looks
exactly like a broken rate limiter.

**The window marks travel as datagrams**, to the same port, through the driver's own `netsend`.
A mark on stdout would have to be correlated with socket timestamps afterwards; a mark *in* the
stream arrives in true order with the data around it.

**It checks:** the known addresses and nothing else, `/cutit/melody`, a heartbeat's repeat, and `/cutit/here` among them; **no `[r disp]` in `u_net`, and no
`/cutit/param`, `/cutit/status` or `/cutit/alert` ever on the wire**, with a sweep, a status, an
alert, a meter and `diag` put on `disp` (Brendan, 2026-11-04: the phone stopped copying the OLED); a
monotonic heartbeat at 2 Hz; the tempo from `u_tempo`'s cord at once, on every heartbeat, coalesced
at 20 Hz with its trailing edge; `re-wire`, `clear-alert` and `test-note` reaching nothing, as six
malformed commands do; test mode, `result` and the gone `send`; every drum and arrangement command
out the first outlet as it came, acknowledged or not as the screens need; `synth` and `velocity`
out the second, `tempo` out the third, each passing on what it does not know for its owner to
refuse; `sections` out the fourth, each of the sections page's commands as it came, a name with a
space as one string, the buttons' five acknowledged and the rest not; `songs` out the same fourth,
`songs` kept in front, its sixteen commands in order, the buttons' ten acknowledged and the rest
not; and the mode, `c_steps`' numbers, the choice, the velocity switch, `u_song`'s 22 atoms and its
songs page's 47 at once and on every heartbeat, the two pages each on its own address. Its rate-limit history, below, is the old mirror's, whose coalescer the tempo now uses.

## `touchosc-assert.sh` — the phone's layout, read and run

```sh
./test/gate/touchosc-assert.sh       ~1 s — the layout read, then its scripts run
```

**Two halves, two tallies.** First, by reading `tools/touchosc/CutIt.tosc`: it is `build.py`'s
output; every control has a name of its own, since a script finds a control by name and TouchOSC
returns the first of two; **every screen is a page of a pager and nothing is hidden**, so the
editor, which runs no script, reaches each by its tab: the root holds one pager, its tab bar on in
the file, whose pages are the Launchpad's eight, as many as `u_map.lua`'s `R.PAGES`, then the
checklist page, each holding a pager of its own with one tab named for the page, but the synths
page's four, the sections page's two and the songs page's three, and pages 4 to 6 blank (Brendan,
2026-11-04 and 2026-11-05);
no diagnostic command is left; and what its buttons send equals what `u_net` routes and `c_steps`
and `c_synth` take, **the inbound vocabulary read from both ends**: the velocity switch asks for
exactly the settings `u_net` acknowledges, and every synth button sends a synth `c_synth.lua`'s
`R.SYNTHS` names, `u_net` acknowledges exactly those, and there is one on the keyboard tab and one
on the checklist page for each. The drum screen's sixteen pads each drag their own track's volume,
pitch, last step and randomness, the four its radio chooses between; the radio is TouchOSC's own,
vertical, its first segment on top, a word over each, and sends nothing, and so is the effect radio
beside it, distortion, delay and reverb (Brendan, 2026-11-05), whose controls sit to its right and
send exactly the effect commands `c_steps` takes, the distortion's character a horizontal radio of
`c_steps.lua`'s `R.CHARS` over its knobs; under each pad its M and S, 30 by 20, M red and S
teal, each sending its own track's `mute` or `solo`; and a pad is a relative fader, about 20 points
of drag a step. **Every control sits on the editor's 20-point grid**, inside the margins, **but the
drum screen's pads and their M and S**, 112 controls named one by one, which step by 10 and start 10
points into the top margin, ending on the bottom one inside the page's 334-point frame (Brendan,
2026-11-05), **and the harmony tab's words, radios and two knobs**, named one by one too, each
required to be there and off the grid, so the list can't outlive its reason. The songs page sends
exactly the commands `u_song.lua`'s `R.songs_cmds` takes, its name tab both `name` and `set-name`,
and its starts switch is a radio asking for exactly `R.STARTS`. The phone is the only sender there
is, and the layout and `u_net` deploy by different routes, `push.sh` and `tools/deploy.sh`, so their
spellings could drift apart with nothing failing until somebody is at the rig. Every acknowledgment
`u_net` sends must light a button. **And every pairing meets WCAG AA contrast as TouchOSC draws
it**: each label against what lies under it, 4.5:1 or 3:1 for large text, each control's outline
against the page, 3:1, and each tab's text and states, from the resting fill TouchOSC draws at 26%
of a color (measured, TouchOSC's Reference page), but an empty chord box's dash, an inactive
control. Each effect's controls are audited against their
own effect's and the screen's alone, since the phone shows one effect's at a time, as a pager one
page, where the file shows every one in the same place for the editor, and each of the rhythm grid's
cells over one blue band at most, since the root moves them apart. **No script holds `//` or `pcall`**:
TouchOSC's Lua lacks both, one stopping the script loading, and the stand-in's 5.4 runs both.

Then the layout's own scripts, unpacked into the scratch directory and run by
`test/gate/lua/touchosc_test.lua` under `test/gate/lua/lib_touchosc.lua`, a stand-in for TouchOSC as
`lib_test.lua` is for pdlua: the outer bar hidden by the root's script, the pages following the
mode and each tab's name, test mode turning to the checklist page and back, `c_melody`'s own state
drawn on the generator's tabs, a chord box sounding the chord in its place, the loop's place moving
its cell, the arrangement
screen's tempo, time signature, last step, swing and drunkenness (a value from Cut It never sent
back, a tempo that is not whole never sent back rounded, the last step's box reaching exactly as
far as `c_steps.lua`'s `R.reach` lets the last step for every top number, 1 to 32), the drum screen's pads (the number its
radio chooses, a tap that selects, a drag that sends its track's value as it stands, and the state
never sent back, a last step dragged no further than `R.reach`), its M and S (lit by the state
and never sending it back, a tap asking for the other setting, a 98-number state leaving them as
they were), its effects (the chosen
effect's controls shown and the others hidden, each handed the selected track's value and sending
for that track, the reverb's size and damping for none) and buttons, the keyboard tab and the checklist page's FM and STRINGS, and the velocity switch, lit by
the state and never sending when lit, the songs page (its rows lit by the state and a lit one
sending nothing, load, new song, add to set, delete asking twice and lapsing after three seconds,
the setlists tab's rows, pager and starts switch, the state's starts never sent back, and its name
tab naming the song or the setlist by the tab it was opened from, the sections page's still
naming a section), the checklist page's Pass, Fail, Back and Next, nothing drawn
from a parameter, a status or an alert, and NO-LINK. The
page is driven on a development checklist with a step on two pages, built for the run, since every
line-check step may fit on one; the reading half holds the line check to having no Send line. **What it cannot judge is how TouchOSC draws**; the
phone checklist is the oracle for that.

## `sequencer-assert.sh` — the drum machine, from the outside

```sh
./test/gate/sequencer-assert.sh      ~40 s — c_steps' rules in Lua, then the drum page and the pattern in the song's draft
```

**Two halves, two tallies.** First `test/gate/lua/c_steps_test.lua`, with lua.org's Lua 5.4 and no
Pd: the rules in `Cut It/c_steps.lua` press by press (the levels, the step rule's three cases, the
selected track, which pads fire, swing, drunkenness's curve, randomness's coin with seeded dice, the
drum screen's pads, mute and solo (a muted track's hits, its coins and its repeats silent, its dice
still rolled, a solo winning over the mutes, the page told which pads won't play only when that
changes, and the lines saved before them loading unmuted), the repeat pads (a held repeat playing
exactly what was played, its coins and its drunk lengths, with no die rolled, mute and solo heard
live in it, a pattern edit and a section's restore under it unheard until it is let go, one pressed
short of its length since PLAY filled first, and let go, rolling again), the bar, the time signature's rows, a
press landing on the step its row and column mean, the reach that clips every last step, the bottom
number changing nothing but the save, a section's restore starting every loop again, the restore,
lines saved before the randomness and before sections included), and `c_steps-lua.pd_lua` through
`test/gate/lua/lib_test.lua`'s stand-in for pdlua (its inlets and outlets, `bad-selector`, a
throwing rule caught as `fail c_steps lua-fire`). Then the Pd half below, on a running copy of the
instrument, which is unchanged since the rules were Pd: **it is the proof the Lua port changed
nothing.** The gate fails if either half does.

It plays the drum page on `param`, as `m_launchpad` publishes it, from a state directory
seeded with a song whose one section holds a pattern, and reads only what leaves the patch: the pads
for `c_kit`, the grid's frames, the state bus and the song's draft. First the time signature, over
OSC as the phone sends it: 9/8 and 3/4 set the page's rows and blue steps, at 3/4 the second
row's first cell is step 7 and the top row's seventh does nothing, and back to the seed's 7/8,
whose rows of seven every later frame is read in. **A note's step is the playhead of the frame painted after it** —
`c_steps` sends a step's notes and its playhead in one logical instant, and the frame clock paints
within 20 ms, six times inside a sixteenth at 120 BPM — so every step's exact notes are asserted
without a timestamp. The tempo is set by the driver, and PLAY to STOP is counted: 21 steps. Knob 2
is held at 16 and then sets the last step to 3 before PLAY again, which must walk 1 2 3 1 2. Then
knob 3 gives track 2 a last step of 6, and nine steps are checked against two loops, 3 and 6, note
by note. Then the drum screen's `snap` is sent as the phone sends it, OSC to `u_net`'s own port
(`CUTIT_INPORT`), so the cord from `u_net` to `c_steps` in `u_root` is under test too. The swing press,
which a map row could give a knob, is held at 50% until turned all the way down, and at 75% puts step 2 three quarters through its pair;
the global last step and the swing are put as they change, a section's. Knob 4's rush runs through the
running patch from its hold to the loop's rate, `pad-38` home and knob 1 taking over, with nothing of it
put in the section.
The drum screen's pads come over OSC too: a track's volume and pitch reach `c_kit`'s stand-in,
`test/stubs/t_kit.pd`, which prints them, as every track's do at the restore, and the seed's
effects, four tracks' and the reverb's size, reach it at the restore too, those alone, since
`c_kit` was told the rest at load, and come back whole in the song's draft; a track at full
randomness plays a coin on every step, at a level's velocity, while the rest play as written; with
four tracks at full randomness, repeat pad 2 held after step 3 replays steps 2, 3 and 2 with
exactly the hits and velocities their coins fell to, and let go, the loop of 3 goes on at 1; and
at full drunkenness at most 60 of 96 sixteenths hold exactly one step. Then track 1 is muted and
then soloed as well, over OSC: muted, it is silent while track 2 plays, soloed, it plays though
muted while track 2 is silent, each is put as a 743-number line, and the Launchpad shows the pads
that won't play dim, pink or the selected red at a quarter. Then track 4's distortion is made fold,
over OSC: it is put as a 759-number line, its character after the mutes and solos, and `c_kit`'s
stand-in hears `char 4 3` and nothing else; the song's draft ends with all three.

⚠️ **The layout table is read, not restated**, so a frame is decoded with the same table the patch
paints from. The analyzer's expectations are what keeps that honest: the driver presses `pad-26`
and expects level 2, so a table that moves the button is caught.

## `synths-assert.sh` — the nanoKEY and the two synths

```sh
./test/gate/synths-assert.sh         ~11 s — c_synth's and c_melody's rules in Lua, then the nanoKEY through the instrument
```

**Three tallies.** First `test/gate/lua/c_synth_test.lua`, with lua.org's Lua 5.4 and no
Pd: the choice, where a key goes, a switch while keys are held, a key's numbers, the velocity
switch, the restores, and
`c_synth-lua.pd_lua` through `lib_test.lua`'s stand-in for pdlua (its outlets, `bad-synth`,
`bad-selector`, a throwing rule caught as `fail c_synth lua-list`). Then
`test/gate/lua/c_melody_test.lua`, the generator's rules, one proof per behavior: a restore from
Pd's floats, a line saved before the later fields, the locks at 100 and 0, a chord changing on the
step its start says, the loop's last chord before the first start, move and swap, a new span,
bass only and a Pd voice per note. How a loop sounds is the ear's. Then a running copy of the
instrument, with a song whose one section holds `synth strings` and `velocity off`: the nanoKEY's keys go in through
`t-notein`, the voices' buttons as `param lp-cc-NN`, and the phone's `/cutit synth <choice>` as a datagram
into `u_net`'s own port, from a socket the driver builds with `lib_drive`'s `extra`.

**It checks:** the saved choice and switch restored and put back, the first key on the
Streichfett's channel alone, at 127, the phone's `velocity on` and `off` put, a voice's button choosing its machine and putting nothing, any channel of the nanoKEY's port playing, a key held through the
phone's switch releasing on the Volca, only a press choosing (two buttons held), notes on four other
ports playing nothing, the choice holding on the performance page, `bad-synth` from
the phone, and `bad-velocity`, a soft key at 127 with the switch off and its release at 0, panic's
CC 123 on channel 33, nothing on another channel, nothing else on `err`, and `synth strings` and
`velocity off` in the song's draft at the end.

## The device layers' Lua halves

```sh
./test/gate/nano-assert.sh           39 + 25 checks, ~17 s — the decode in Lua, then the channel gate
./test/gate/organelle-assert.sh      35 + 21 checks, ~20 s — the keyboard's names in Lua, then the panel
```

**A device layer whose decoding is Lua runs its Lua tests first**, as the map and the sequencer do,
with lua.org's Lua 5.4 and no Pd. `test/gate/lua/m_nano_test.lua` drives `Cut It/m_nano.lua`: all
fifty names by tens and units, a button's press as 1 and its release as nothing, the unmapped
warning, and that no name outlives its message. `test/gate/lua/m_organelle_test.lua` drives
`Cut It/m_organelle.lua`: each key's name. The SP-404's layer had a third, until it left the rig (2026-11-04). Each also
drives its face through `lib_test.lua`'s stand-in for pdlua: its
inlets and outlets, `bad-selector`, and a throwing rule caught as `fail <layer> lua-<bus>`. Each Pd
half is unchanged since its layer was Pd: **it is the proof the port changed nothing.**

## `song-assert.sh` — the song store, played from the Launchpad's edges

```sh
./test/gate/song-assert.sh           ~50 s — u_song's rules in Lua, then four runs of the instrument
```

**Two halves, two tallies.** First `test/gate/lua/u_song_test.lua`, with lua.org's Lua 5.4 and no
Pd: a fresh load, the files' text both ways, a load from the draft, the saved song or both, the top
row stopped and playing, lengths and the last one with a length, the six buttons scrolling, the
sections page's commands, names, save and revert, the phone's state; several songs, the index both
ways, a load with and without one, the songs tab's and the setlists tab's commands, the keys stopped
and playing, the next arrow, a song left keeping its draft, the songs page's state; and
`u_song-lua.pd_lua` through `lib_test.lua`'s stand-in for pdlua, reading and writing real files in a
folder of its own, across reloads, a song's own files made, flushed and deleted, a write that fails,
and a throwing rule. Then **four runs of a scratch copy of the instrument**, one analyzer reading
them all:

- **The song**, booted on the drum page with three sections saved, intro, verse of two loops and chorus,
  each with every part: the top row pressed as the Launchpad sends it, the transport on its buses, a
  change as a tempo on the bus. At load section 1 starts; stopped, a button starts its section at
  once, its programs out to both synths; a change lights save and revert, revert and save put them
  out; playing, verse hands over by itself on chorus's step 1, the drum page's playhead showing it;
  a section pressed blinks on the beat and starts when the pattern comes round; the arrows; a button
  with no section. Both files on disk after it.
- **A reload** of what the first left: the draft comes back, unsaved, and revert takes it to the
  save.
- **A first load from a state directory before sections**: the auto file's 579-number pattern, synth
  and switch become section 1's, and the auto file lets the old keys go. This run and the first
  start with no index, as a state directory from before several songs, and both end with one: song
  1, the opener of set 1.
- **Three songs**, booted on the songs page with a setlist, gig, saved: the Organelle's keys pressed as
  `m_organelle` publishes them, stopped, then playing. Stopped, a key
  loads at once; a song changed and left keeps its change as its draft,
  and comes back with it, unsaved; playing, the next arrow blinks while the song waits and it loads on the
  step 1; a key past the setlist's end does nothing. The index and the songs' own files on disk after it.

⚠️ **The driver turns DSP on**: the steps are cut from a `phasor~`, and the queued lamp blinks on
the grid's own clock, which is one too. Without it the transport plays nothing and no bar comes.

## `voices-assert.sh` — the voices and the controls in play

**It runs the rules' Lua tests first**, with lua.org's Lua 5.4 and no Pd: `test/gate/lua/u_voices_test.lua` the seed,
every button's page, aux and Setup over each other, PLAY, the engines, too many of a method, the phone's voice page and a
page waiting for its song; `test/gate/lua/u_perform_test.lua` arm, heard and bind, pickup, a section's list, toggle and hit,
what a lane shows and the phone. Then **a scratch copy of the instrument with no song saved**, driven on `param` and over
OSC, which proves the cords: a press through the map to the page on the `mode` bus, the song's voices into its draft,
tempo taken into play and moved through `map-route`, a roll reaching its own engine by name from the performance page,
the columns' colors, and a new section's list waiting, then caught.

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

⛔ **`m_volca` emits through `noteout`/`ctlout`/`pgmout`, not `midiout`**, as `m_404` did, so
`display-assert.sh`'s rewrite finds nothing in it and every assertion about it would pass
**vacuously**. ⚠️ **And phase 6's regex is anchored so the class name must END the line** — it
silently skips any box carrying creation arguments, of which the patch has one: `m_volca`'s
`[ctlout 123]`. A phase 9 rewriter has to take a trailing argument list, and the stubs
therefore read creation args too.

⛔ **`t_notein` exists because the receive side is otherwise untestable.** Every *output* path can
be driven from a bus, but the Launchpad's pads sit behind `[notein]`, as `m_404`'s whole receive
side did, and **there is no bus behind a MIDI input** — a channel gate and the decode behind it
would go unexercised. Its outlet order reproduces the real object's
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
