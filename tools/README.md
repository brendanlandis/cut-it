# Diagnostic patches

Standalone Pd patches for testing the rig. **Not** Organelle patches — they don't use
`mother.pd` and aren't meant to be loaded from the device menu. They run manually over SSH so
that `print` output is visible, which matters because the Organelle launches Pd with `-nogui`
and there is no console otherwise.

Hand-authored in Pd 0.49 format except the four benches and three rigs that are **generated** —
`bench-gen.py`, `phase6-assert-drive-gen.py` and `phase7-assert-drive-gen.py` write them, and the
`.pd` is an output. Edit the generator. Do not open any of it in plugdata — see
[../CLAUDE.md](../CLAUDE.md).

| Patch | What it does |
|---|---|
| `midi-monitor.pd` | Prints incoming notes and CCs with their Pd channel. Use to confirm device channel offsets (device *n* → channel `(n-1)*16+1`). |
| `midi-drive.pd` | Sweeps notes 47–62 on channel 33 to trigger SP-404 pads, and monitors incoming. |
| `lp-monitor.pd` | Puts the Launchpad in Programmer Mode, echoes pad presses back as LEDs, prints velocity and polyphonic aftertouch. |
| `lp-flicker.pd` | Fills the Launchpad with random monochrome noise via per-pad RGB SysEx. Press any pad to toggle grey ↔ blue. Demo, but a working reference for RGB SysEx and `until` loops. |
| `lp-modes.pd` | Lights three pads static / flashing / pulsing — the device's three LED animation modes. |
| `lp-step0.pd` | **Phase 6's Step 0 measurements, in one patch** — items 82–87. Prints incoming notes, **CC** and aftertouch with their channel, sends a batch colour SysEx of 64 / 99 / 120 specs, and switches layout. `lp-monitor.pd` cannot answer item 82 because it has no `[ctlin]`. Run it on the **Mac** with the Launchpad plugged in, in the foreground. |
| `self-wire.pd` + `wire.sh` | **The pattern the real patch needs.** Shows a patch wiring its own ALSA MIDI connections at load time via `[shell]`. |

## phase8-assert.sh — the Phase 8 gate, and the cheapest of the three

```sh
./tools/phase8-assert.sh          15 checks, ~12 s, exit non-zero on any failure
./tools/phase8-assert.sh -v       and the detail behind every check
```

`u_state` writes a **file**, so this gate reads what landed on disk. No scratch copy (Phase 6
needed one, because `[midiout]` is a built-in class with no side channel), no socket (Phase 7's
trick), no hardware. It works entirely inside `/tmp/cut-it-phase8-gate` and never touches
`Cut It/`, `/sdcard/cut-it-state` or the device.

**What it protects, stated as properties rather than proxies:** the two policies never leak into
each other; re-putting a key REPLACES its line; **a contributor answering behind a `[del]` is
absent from the file** — the synchronous contract itself; manual is replayed before auto so auto
wins a duplicate key; **a boot does not overwrite saved state before reading it**; and both entry
points load in **silence**, which is `deploy.sh`'s own gate.

⚠️ **It passed the broken patch on its first can-it-fail run** — the driver banged the restore at
600 ms when the bug needs it after 3000 ms, and the final check asserted against a value nothing
drove. **The 3600 ms in the driver is load-bearing**; shortening it re-blinds the gate. Proven
both ways now: 15/15 clean, 2 failures with the bug reintroduced. `phase8-assert-drive.pd` is an
OUTPUT — edit `phase8-assert-drive-gen.py`, never the `.pd`.

## fetch-state.sh — back the instrument's own data up into the repo

```sh
./tools/fetch-state.sh              copy /sdcard/cut-it-state/ into device-state/
./tools/fetch-state.sh --show       print it instead
./tools/fetch-state.sh --diff       show what would change, copy nothing
```

`u_state` deliberately writes OUTSIDE the patch folder so `deploy.sh`, `--clean` and a power cycle
cannot touch it. The cost is that the data then lives in exactly one place, on an SD card, in a
device that has already lost its network once. This is the other half of that bargain. It commits
nothing — git is Brendan's.

## Phase 3 — testing the display on hardware

These three load **alongside** a running `mother.pd` + `main.pd` (see *Running one* below).
None of them touches the deployed patch: they only read `oscOut` or push onto `disp`, `err`
and `mode`, exactly as a controller would.

| Patch | What it does |
|---|---|
| `phase3-bench.pd` | **The acceptance run.** Fourteen steps, **stepped by hand** — see *The benches are stepped by hand* below. Each prints what it is sending and a **PASS IF** line *before* the screen moves, including the steps whose correct result is that nothing happens. Run it in the **foreground** and watch the OLED. |
| `phase3-diag.pd` | Counts rather than dumps. `FRAMES` and `MESSAGES` are cumulative totals printed once a second, so the rate is the gap between lines — expect +10 and +100. Printing every OSC message instead would slow down the thing being measured. |
| `alert-buffer-probe.pd` | ✅ **Answered:** draws into the ALERT buffer (screen 4), `setscreen 4`, waits six seconds, `setscreen 3`. All of it works — but `g_oled` still doesn't use buffer 4, for the reasons in [ref-display.md](../ref-display.md). Keep it as the re-check if that ever gets revisited. |

## `pd-layout-check.py`

Not a patch — a static check on `.pd` files:

```sh
python3 tools/pd-layout-check.py "Cut It"/*.pd
```

Reports overlapping boxes, **connections drawn through unrelated boxes**, and content that
extends past the saved canvas size. Exits non-zero on any of them.

Layout is the only structural documentation Pd has, and the failure it was written for is
specific: a comment placed between the logic and a message column gets cords drawn straight
through it, which is invisible until you open the patch. Box sizes are estimated from the text
rather than measured, so it is a smell detector, not a renderer.

The diagnostic patches above predate it and do not pass — they are working references, not
examples of layout.

## Organelle patches

The first four **are** Organelle patches — they load `mother.pd` and run from the device menu,
unlike everything above. Deploy with `scp` to `/sdcard/Patches/!/<name>/main.pd`. The fifth is
the phone side and is not an Organelle patch at all.

| Patch | What it proves |
|---|---|
| `oled-probe/` | The OLED **graphics** API is reachable from a patch via `[s oscOut]`. Measures the font (21 chars, monospace, 8px) and redraws live from knob 1. |
| `osc-bridge/` | Bidirectional OSC between Organelle and an iPhone running PdParty. Sends a heartbeat and `knob1`; draws whatever arrives on `/cutit/fader` big on the OLED. |
| `status-display/` | The performance status protocol: four knobs sending **named parameters** (`chop-size`, `grain`, `speed`, `drunk`) plus a heartbeat. |
| `audio-probe/` | `env~` levels for `adc~ 1` and `adc~ 2` drawn large on the OLED. Used to verify the TRS input split; still the quickest way to check what is arriving at the inputs. |
| `pdparty-scene/CutItRemote/` | The phone side — landscape, big text, link-loss detection. **Not** an Organelle patch: deploy over WebDAV with `curl -T http://<phone>:9000/CutItRemote/_main.pd`. |

Findings from all of them are written up in [../ref-display.md](../ref-display.md).

## Running one

```sh
scp tools/lp-flicker.pd root@organelle.local:/tmp/

ssh root@organelle.local
  killall pd 2>/dev/null; sleep 1
  cd /tmp
  nohup pd -alsamidi -midiindev 1,2,3,4 -midioutdev 1,2,3,4 \
        -nogui -noaudio /tmp/lp-flicker.pd > /tmp/out.txt 2>&1 &
  sleep 2
  aconnect 'Launchpad Pro MK3':0 'Pure Data':0    # -> Pd device 1, channels 1-16
  aconnect 'Pure Data':4 'Launchpad Pro MK3':0    # LEDs and SysEx back out
  cat /tmp/out.txt
```

Stop with `killall pd`.

## Things these patches taught us

Findings specific to working *in this folder*. The Launchpad's own behaviour — palette,
animation modes, LED state, `polytouchin` ordering — is catalogued in
[../ref-midi.md](../ref-midi.md). Pd message-discipline traps (`[list trim]`, `route`'s
selector rules, `sendtyped` arity, `quitting`) are in
[../ref-conventions.md](../ref-conventions.md), and the OSC ones in
[../ref-display.md](../ref-display.md).

- **`loadbang` fires before ALSA connections exist.** Initialisation SysEx sent on `loadbang`
  goes nowhere. Use `[loadbang] → [del 2000]` or longer. Repeated here because every patch in
  this folder has to obey it.
- **`aconnect` by name, never by client number.** Client 28 was the Launchpad, then became the
  SP-404 when devices were swapped. Names are stable, numbers are not.
- **`amidi` and Pd cannot both hold a port.** Once ALSA seq has subscribed a device,
  `amidi -p hw:x,y,z` fails with "Device or resource busy". Use `aseqdump`, which coexists.
- **`[random]` takes a bang, not a float.** Feeding it a float errors once per event, which at
  grid-refresh rates produced 2,500 errors/sec.
- **A patch can wire its own `aconnect` calls** via `[shell]`, but put the commands in a shell
  script — Pd message boxes and shell quoting do not mix well.
- **`route` passes the matched message's ARGUMENTS on, and they are rarely what you want next.**
  `route /oled/gClear` emits `ii 3 1` — the typetag and its args. Feeding that to a float inlet
  prints `float: no method for 'ii'` on every message, which at a 10 Hz redraw is an endless
  console scroll. Put `[t b]` in between when you only care that the message happened.

## Phase 4

### `phase4-bench.pd` — the Phase 4 acceptance run

Same shape as `phase3-bench.pd`: eighteen steps, stepped by hand, and a printed `PASS IF` for
every step **including the ones whose correct result is that nothing happens**. Load it as a third
patch after `mother.pd` and `main.pd`. Steps 1–14 drive themselves off the `disp`, `err` and `mode`
buses; **15–17 need your hands on the nanoKONTROL**, because nothing but the real controller can
exercise `[ctlin]`.

Step 2 and step 6 are the regression gate on the display rewrite. Steps 7–14 are `phase3-bench`'s
assertions, re-run because the param layer they sit next to was rewritten.

⚠️ **No commas or semicolons in a message box** — both are message separators, so a comma in a
`PASS IF` string splits it and the remainder goes somewhere unhelpful (`canvas: no method for
'then'`). `phase3-bench.pd` says so and it caught this one out too.

## Phase 5

### `phase5-bench.pd` — the Phase 5 acceptance run

Same shape again: fifteen steps, stepped by hand, a printed `PASS IF` before each one, covering
the clock, the transport, the map and the aux LED. **Steps 1–12 drive themselves; 13 and 14 need
your hands on the Organelle itself** — the aux button and knob 1 are the only controls involved,
and neither exists on a laptop. Step 15 just says to stop.

⚠️ **One line of its text changed in the conversion, and it was a bug fix.** The aux step carried
two escaped commas inside its `PASS IF`. `\,` satisfies the .pd *parser*, but a message box still
treats the comma atom as a separator — so that line printed as **three fragments**. Both are now
` -- `. Everything else survived verbatim, which `bench-verify.py` proves.

**It finds `c_clock` itself**, through `#X declare -path ../Cut\ It` — the escaped space survives
Pd's parser ✅ — so opening it straight from Pd's File menu works and no `-path` is needed. If the
console ever says `c_clock ... couldn't create`, the two `c_clock` counts will read **0** and mean
nothing, which looks like a dead clock rather than a missing search path.

⚠️ **On the Mac, tick the panel's `enable-DSP` toggle first.** `threshold~` is a signal object,
so with DSP off the beat counters read **0** — which looks exactly like a broken clock. On the
device `mother.pd` turns DSP on 200 ms after load and this does not arise.

Three steps carry the load:

| Step | Proves |
|---|---|
| **3** | 24 PPQN is right, and `c_clock` at ratios 1 and 1.5 gives 20 and 30 beats in 10 s at 120 BPM |
| **9–10** | **the clock keeps running when the transport stops.** A zero here is the bug the step exists for — stop the pulse stream and the 404 stretches to a stale tempo |
| **7** | out-of-range clamps to the 5–600 legal range and warns **once per distinct value** — press the same button twice and the second press must be silent |

### `panic-poke.pd` — the only way to raise a panic on the device

**Nothing on the Organelle sends `panic`.** It has consumers — `u_init`'s safe exit and
`u_tempo` — but the only writers are the bench and the Mac dev panel, so there is no way to
provoke one by hand. This fires `panic` every 25 s as a third patch, and prints what the OLED is
being told (`FOOTER` and `LED`) so the console and the screen can be compared directly.

Written to retest one specific bug: **the footer used to stay on `panic` after the transport had
visibly restarted**. Press aux after a poke — the button must go green *and* the footer must
return to the BPM.

### `midiout-probe.pd` — which half of the MIDI path is broken

Written when the 404 appeared not to follow the clock. It talks straight to the MIDI ports and
touches no Cut It code, so it splits "is Pd emitting?" from "is the device listening?":

| Group | Answers |
|---|---|
| **A** | raw bytes out of `[midiout]` with the port in the cold inlet — **`u_tempo`'s exact mechanism** |
| **B** | the same pad via `[noteout 1]`, which reaches the port by *channel* instead. A dead + B alive = the port inlet is the fault |
| **C** | the same bytes on port 3, which must stay **silent** on a one-output Mac. If it fires, the port inlet is ignored and every byte goes everywhere |
| **D** | a hand-rolled 24 PPQN clock from `[metro]`, sharing no code with `u_tempo`, plus Start and Stop |

✅ **It closed the `[midiout]` port question** (item 63) and then showed the 404 had been following
all along — the wrong number was being read (item 64). **`250` on its own starting the pattern
sequencer is the unambiguous "is it listening" test**; a tempo display is not.

### `fetch-errors.sh` — read the error log back off the device

`u_err` now keeps a persistent log, so an error raised mid-set can be read the next day:

```sh
./tools/fetch-errors.sh              # summary, then detail, newest session first
./tools/fetch-errors.sh --follow     # poll the live session
./tools/fetch-errors.sh --clear      # read it, then truncate (asks first)
HOST=root@192.168.1.15 ./tools/fetch-errors.sh
```

It reads **both** `/sdcard/cut-it-err.log` (every rolled session) and `/sdcard/cut-it-err.cur` (the
one running now, or the last one if the patch has not been reloaded since — the normal case, because
power-cycling the Organelle does not reload the patch). It also md5-compares the deployed patch
against the repo and says so loudly if they differ, because an error from a build you no longer have
is a trap.


## Chasing the wifi fault — items 81 and 133

Three pieces. The fault is that the Organelle loses its **IPv4 lease** after roughly an hour while
staying **associated**, and ⚠️ **ssh keeps working over IPv6 throughout**, so a login proves nothing.

| | |
|---|---|
| `wifi-watch.sh` | **Runs ON the device.** Polls `wlan0` every 20 s, logs every IPv4 transition with `dmesg`, association and process state, then walks a **recovery ladder** — renew, release+restart, `wpa_supplicant` restart — recording which rung works. Copy to `/sdcard/` and launch with `setsid`. |
| `wifi-poll.sh` | **Runs on the Mac.** Leave it in a terminal. Redraws a small block every minute and answers one question: *anything found yet, y/n.* Rings the bell and raises a macOS notification when it finds something. |
| `../wifi-analysis.md` | What each outcome **means** and what to do about it. Hand it to an agent along with `wifi-report.sh`'s output. |
| `wifi-report.sh` | Pulls the evidence off the device and summarises it into the shape the analysis needs. |

⚠️ **`wifi-poll.sh` does not rely on reachability.** The fault can drop and recover between two
polls and the Mac would never see it, so it reads the **transition count** out of the device-side
log — any increase means a drop happened whether or not anything was watching.

⚠️ **Liveness is a file, not a process match.** `pgrep -f wifi-watch` also matches the ssh command
that goes looking for it — that self-match made a running watcher look dead, and a `pkill -f` on the
same pattern killed the ssh session outright. The watcher writes `/sdcard/wifi-watch.pid` and
touches `/sdcard/wifi-watch.alive` every poll; **check the mtime.**

## The benches are stepped by hand

**All four benches are generated by `bench-gen.py` from the step tables in `bench_steps.py`.**
Edit the table and re-run the generator; **never edit a `phaseN-bench.pd`.**

```sh
python3 tools/bench-gen.py        # writes all four
python3 tools/bench-verify.py     # proves the step text survived
```

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

### `phase6-bench.pd` — the Phase 6 acceptance run

**Twenty-five steps** covering the mode bus, the grid arbiter, the layer priorities and TTLs, the
first `c_clock` instance, the ring map and the safe exit. Steps needing hands are marked in their
own prompt line.

⚠️ **Its beat counter used to be dead.** `[r $0-zero]` and `[r $0-read]` existed, the comment beside
them claimed the tempo steps drove them, and **nothing anywhere sent to either name** — so the one
automated assertion in the Phase 6 bench never fired. Same shape as `phase5-bench`'s `[r $0-say]`
that was never connected to its `[print]`. Fixed by driving them from the step table.

⚠️ **The panic step hands the surface back and the grid does not come back.** Nothing re-enters
Programmer Mode except `u_init`'s boot, so the grid stays the device's own until you reload.
Deliberate, and stated in the step.

### `phase7-bench.pd` — the Phase 7 acceptance run

**Fifteen steps, and the first bench whose subject is not the Organelle** — every `PASS IF`
describes what the *phone* shows. **PdParty has to be open on the `CutItRemote` scene before
step 1**, and step 1 exists to confirm that before anything depends on it.

Steps 8–11 are the ones whose correct result is that **nothing happens**: the level meters, the
grid vocabulary and the aux LED are all on `disp` and all deliberately dropped by `u_net`. A line
that starts reading `in-l` means the reserved branch is broken and the rate budget has gone to a
meter the phone does not draw.

⚠️ **The rate limit is not tested here and cannot be.** A step table pushes discrete messages; a
flood needs a metro. `phase7-assert.sh` is what proves the coalescer. **Step 12 is the closest a
person can get** — a real fader, and the question of whether the phone *settles* on the value you
stopped at rather than one from the middle of the sweep.

**Steps 13 and 14 are the only way to reach item 114 on real hardware.** Closing PdParty makes the
phone answer with an ICMP port-unreachable, which destroys the socket; reopening it must bring the
display back within about five seconds **with nothing touched on the Organelle**. A link that could
not recover would be dead for the rest of the set and nothing on the instrument would say so.

## `phase6-assert.sh` — the headless gate, no eyes and no hardware

```sh
./tools/phase6-assert.sh            # ~45 s, exits non-zero on any failure
./tools/phase6-assert.sh --keep     # and leaves the byte capture to read
```

**This is the part that asserts what the grid is actually showing.** `phase6-bench.pd` used to
claim in its own header that *"there is no way to read back what the LEDs are actually showing"* —
too strong, and it conflated three different things. Pd cannot ask the Launchpad what is lit, but
**the bytes the patch sends are completely knowable**, and that is the right level to test our own
code at.

| Piece | |
|---|---|
| `test-stubs/t_midiout.pd` | a stand-in for `[midiout]` that prints every byte with its port |
| `phase6-assert-drive.pd` | the timed driver — pushes onto the buses and prints a `MARK` before each window. Generated by `phase6-assert-drive-gen.py` |
| `phase6-assert.py` | reassembles the SysEx frames and does all the reasoning |
| `phase6-assert.sh` | copies the patch to a scratch dir, rewrites the `[midiout]` boxes, runs it, pipes the capture to the analyser |

⚠️ **The stand-in cannot be supplied by search path.** `mac-stubs/` works because `shell` is an
*external absent on the Mac*, so Pd falls through to an abstraction. `midiout` is a **built-in
class**, and Pd resolves the class table before it looks for a file — ✅ measured both ways, and a
`midiout.pd` on the path is simply ignored. So the object name has to change, which means
rewriting the box. **`Cut It/` is never touched**; the scratch copy is thrown away.

The script counts the boxes it rewrote and **refuses to run if it found none** — otherwise every
assertion would pass vacuously, which is worse than failing.

**29 checks**: frame shape and the 1–108 span, the mode lamp index, the modal claiming all 108
specs, `fail` painting red and `warn` painting nothing, the alert expiring back to the modal
underneath, the beat row never leaving 11–18, the grid going silent after a panic, and
`m_launchpad`'s Programmer and Live SysEx.

✅ **It has been proven to fail.** Reintroducing the one-based beat bug in a scratch copy — the
beat-row offset back to `+ 11` — makes it report `lit outside every region: [(19, 3)]` and exit 1.
⚠️ **The three `home-*` checks still passed under that mutation**, which is exactly why *seven
beats out of eight looked perfect*: only the six-second beat-row window catches it. A gate that
cannot fail is worth nothing, so re-run that mutation if you ever change the analyser.

## `phase7-assert.sh` — the same idea, and much cheaper

```sh
./tools/phase7-assert.sh            # ~25 s, exits non-zero on any failure
```

**Phase 7's gate needs no scratch copy and rewrites nothing.** `[midiout]` is a built-in class
with no side channel, which is the whole reason `phase6-assert.sh` has to swap it for a stand-in
in a throwaway copy of the patch. **`u_net` already emits to a socket** — so the gate binds
`127.0.0.1:9995`, instantiates `u_net 127.0.0.1 9995` and reads the real datagrams. `Cut It/` is
never touched.

| Piece | |
|---|---|
| `phase7-assert-drive-gen.py` | generates the driver. **Edit this, never the `.pd`** |
| `phase7-assert-drive.pd` | instantiates `u_net` and pushes synthetic traffic onto `disp` |
| `phase7-assert.py` | binds the port, launches Pd, decodes OSC, does the reasoning |

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

### `phase6-cpu.sh` — the repaint budget on the device

```sh
./tools/phase6-cpu.sh -n 3
```

plan-tests.md item 94. Wraps the `/proc` arithmetic from [../ref-hardware.md](../ref-hardware.md)
→ *Measuring the running patch* and says WITHIN or OVER against the **11.2 %** budget — Phase 5's
10.2 % idle baseline plus one point. ⚠️ `pgrep -nx pd`, never a bare `pgrep`: the substring match
hits a kernel thread on this device.

### `lp-step0.pd` — the Phase 6 Step 0 measurements

Everything Phase 6 needed to stop guessing about: the ring's CC numbers, how many colour specs
one SysEx really carries, whether that SysEx lights the ring as well as the pads, and what the
layout-select command actually does. All of it is now recorded in
[../plan-tests.md](../plan-tests.md) Session 7. Keep it as the re-check if a Launchpad is ever
swapped.

### Running a bench on the device

Any of the four benches loads as a **third patch** after `mother.pd` and `main.pd`, which is what
gives it a real console. This is the launch line:

```sh
scp tools/phase5-bench.pd root@organelle.local:/tmp/
ssh root@organelle.local
  killall pd; sleep 1
  cd /tmp/patch
  nohup pd -nogui -rt -audiobuf 6 -path /root/Pd/externals \
      -path '/sdcard/Patches/!/Cut It' \
      /root/fw_dir/mother.pd main.pd /tmp/phase5-bench.pd > /tmp/bench.txt 2>&1 &
  tail -f /tmp/bench.txt          # Ctrl-C when the last step prints
  killall pd
```

⚠️ **Single quotes around that path, never double.** The patch folder is `/sdcard/Patches/!/…`, and
`!` inside double quotes is a history event in interactive zsh — you get `zsh: event not found:
/Cut` before anything reaches the device.

⚠️ **The second `-path` is not optional for `phase5-bench`.** Its own `declare` is `../Cut\ It`,
which resolves from `tools/` on the Mac but not from `/tmp/` on the device. Without it `c_clock`
fails to create and both its counts read **0** — which looks exactly like a dead clock rather than
a missing search path.

⚠️ **THE ENCODER DOES NOT ADVANCE A BENCH ON THE DEVICE.** The plan that chose a single
alternating control assumed it would. `mother` forwards `encbut` only to patches that have sent
`/enableEncoder`, and **nothing in Cut It ever does** — `m_organelle` leaves the encoder out
deliberately. On the Mac `u_mother-stub` sends it unconditionally, which is what hid this. Use:

```sh
./tools/go.sh              # one GO
./tools/go.sh -n 25        # walk the bench forward
```

⚠️ **Not netcat.** The benches used to print `echo "go;" | nc -u -w0 organelle.local 9998`, and on
macOS that **silently does nothing** — BSD `nc` exits before the datagram is flushed at `-w0`, and
`-w1` was measured to fail too, while the port *is* bound and the bench *is* fine. It looks exactly
like a dead bench. The device cannot send to itself either: busybox here has no `nc` at all.

⚠️ **`killall pd` strands the Launchpad in Programmer Mode** — see `lp-live.sh` below. Restore
normal operation with `./deploy.sh`, which reloads through the menu path and *does* run the safe
exit.

**Two of these live on the device**, left there deliberately after the Phase 6 hardware run:
`/sdcard/phase6-bench.pd` and `/sdcard/dsp-toggle.pd`. They sit *outside* the patch folder, so
`deploy.sh` never touches them and they cannot affect what loads. Re-`scp` only if you have
changed them locally.

⚠️ **`/tmp` is wiped on reboot**, which is why these live on `/sdcard`. A bench copied to `/tmp`
vanishes with a restart, and the by-hand launch then runs `mother.pd` + `main.pd` with **no
bench** — the GO port is never bound and the bench looks frozen at step 1. Item 134.

### `go.sh` — the only way to drive a bench on the Organelle

One UDP datagram to the bench's `[netreceive 9998]`. Python's socket send rather than netcat, for
the reason above. `-n N` fires N of them half a second apart, which is how you walk a bench to a
particular step without judging every one on the way.

### `dsp-toggle.pd` + `dsp.sh` — turn the audio engine off on a running patch

```sh
./tools/dsp.sh 0     # off
./tools/dsp.sh 1     # on
```

Load `dsp-toggle.pd` as a third patch beside `mother.pd` and `main.pd`. It touches no bus and owns
no surface; all it can do is set Pd's global DSP state.

**Why it exists.** Item 75 recorded that the Phase 5 clock roughly doubled Pd's CPU and blamed the
96 ALSA MIDI writes a second — marked ⬜ *not confirmed by isolation*. This is that isolation, and
it overturned the conclusion: **DSP on 11.8 %, DSP off 4.9 %**, so the DSP costs **6.9 points** and
the MIDI clock **0.43**. Wrong by a factor of sixteen.

⚠️ **With DSP off the patch is silent and the beat row freezes** — `c_clock` is cut from a phasor,
so the grid stops walking and the transport stops counting. Expected, not a fault.

### `lp-live.sh` — rescue a Launchpad stranded in Programmer Mode

```sh
./tools/lp-live.sh
```

Sends the Live Mode SysEx with `amidi`, **needs no Pd at all**, and looks the port up by name
because `hw:N` numbering shifts like the ALSA client numbers do.

**Why it is needed.** `m_launchpad`'s safe exit hooks `[r quitting]`, which only `mother.pd` sends
— right before mother itself quits Pd, with a 100 ms budget. Pd 0.49 has no `closebang`, so that is
the only shutdown hook there is. **Every other way a session can end leaves the device stranded**: a
crash, power loss, or `killall pd` — which the by-hand console workflow does every single time.
Programmer Mode locks out the Launchpad's own Settings menu, so the front panel cannot recover it.

Measured 2026-08-03: `killall pd` left the grid frozen in Programmer Mode, and this brought it back
with no power cycle. `deploy.sh` is unaffected — it loads through `/loadPatch`, so `quitting` fires
normally.

### Re-running `m_nano`'s decode test without the hardware

`m_nano`'s decode was verified by swapping `[ctlin]` for a three-outlet stand-in driven by
`nano-ch`, `nano-cc`, `nano-val` **in that order** — which is `ctlin`'s measured firing order made
explicit. To repeat it: copy `Cut It/` aside, replace the `ctlin` line in `m_nano.pd` with a
stand-in abstraction of that shape, and drive it. All 21 cases and the bug it found are recorded in
[plan-tests.md](../plan-tests.md) item 31. The firing order itself is item 23 and needs the real
device.
