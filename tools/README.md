# Operational tools and probes

**Everything here is run by a PERSON, on purpose, when something needs doing or diagnosing.**
Nothing is run by a gate, nothing is deployed with the patch, and nothing here is a test — the tests
are in [../test/](../test/README.md).

⚠️ **These are not Organelle patches** unless the table below says so. They don't load `mother.pd`
and aren't meant for the device menu; they run over SSH so that `[print]` output is visible, which
matters because the Organelle launches Pd with `-nogui` and there is no console otherwise.

## What is here

| | |
|---|---|
| **Getting data back off the device** | `fetch-state.sh` `fetch-errors.sh` |
| **The wifi investigation** — an OPEN fault | `find-organelle.sh` `wifi-watch.sh` `wifi-poll.sh` `wifi-report.sh` `wifi-reassociate.sh` |
| **Driving and rescuing hardware** | `go.sh` `lp-live.sh` `dsp.sh` + `dsp-toggle.pd` |
| **Measuring the device** | `display-cpu.sh` `display-diag.pd` |
| **Probes still worth running** | `lp-monitor.pd` `lp-step0.pd` `alert-buffer-probe.pd` `self-wire.pd` |
| **Answering a device** — does it reply at all | `stage-patches/Inquiry Probe/` |
| **Watching a device animate** — does it still track the clock | `stage-patches/Anim Probe/` |
| **Worked examples** — a technique, kept as the proof | `audio-probe/` `oled-probe/` `osc-bridge/` `status-display/` |
| **The phone side** | `pdparty-scene/` — a PdParty scene, not an Organelle patch |
| **Menu patches** | `stage-patches/` — see below |

⚠️ **Eighteen one-off probes were deleted on 2026-08-07** — seven for the SP-404 rate ceiling alone,
three July MIDI probes superseded by the `m_` layers, and a `wire.sh` here that was a 42-line-behind
ancestor of `Cut It/wire.sh` with no `|| true` on any line. Every finding is on a `ref/` page and
most are now asserted by a gate. They are all in git history; `plan-cleanup.md` lists them.

⛔ **The test was "would you run it again", not "is it used".** A script mentioned in no document is
fine.

## Getting data back off the device

### `fetch-state.sh` — the instrument's own data

```sh
./tools/fetch-state.sh              copy /sdcard/cut-it-state/ into device-state/
./tools/fetch-state.sh --show       print it instead
./tools/fetch-state.sh --diff       show what would change, copy nothing
```

`u_state` deliberately writes OUTSIDE the patch folder so `deploy.sh`, `--clean` and a power cycle
cannot touch it. The cost is that the data then lives in exactly one place, on an SD card, in a
device that has already lost its network once. This is the other half of that bargain. It commits
nothing — git is Brendan's.

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

## The wifi fault

### `find-organelle.sh` — which failure is this?

```sh
./tools/find-organelle.sh          # the ladder, then a named verdict
./tools/find-organelle.sh -q       # the verdict line only
```

⚠️ **"Cannot reach it" is the most misread observation in this project.** Four states all present as
a failed `ssh`, and they want opposite responses. This runs the ladder — mDNS, an IPv4 sweep of the
Mac's own `/24`, IPv6 neighbour discovery, and an AP-mode SSID scan — and names one of
**REACHABLE** · **ASSOCIATED-NO-LEASE** · **AP-MODE** · **ABSENT**.

⛔ **`ASSOCIATED-NO-LEASE` is the documented fault and `ABSENT` is not.** Item 81 leaves the device
associated, so ssh over IPv6 link-local keeps working the whole time — nothing answering *anywhere*
means powered off, adapter down, or a different SSID. Telling those two apart is the whole point.

⚠️ **The identity signal is the ssh banner** — OS 4.0 ships **OpenSSH 7.1** and everything else on
this network answers 8.2 or newer. It is a heuristic; override with `ORG_BANNER=` if the image
changes. ⛔ The first version tried mother's OSC port 4001 instead, and `nc -z` tests **TCP** while
4001 is **UDP** — so it found the Organelle and dismissed it. The first version also reported a NAS
as the documented fault, because it probed every IPv6 neighbour and believed whichever answered
first. **Both bugs were found by running it against the live network, not by reading it.**

⬜ Only the `REACHABLE` and `ABSENT` branches have been exercised against real hardware.
`ASSOCIATED-NO-LEASE` and `AP-MODE` are written from the recorded evidence and unproven.

### Chasing it — items 81, 133 and 146–168

The fault is that the Organelle loses its **IPv4 lease** while staying **associated**, and
⚠️ **ssh keeps working over IPv6 throughout**, so a login proves nothing. The check is
`ip addr show wlan0 | grep "inet "`.

⚠️ **Uptime-to-failure is NOT constant** — measured at **~3 h 12 m** and **2 h 09 m**, which
already argues against plain lease expiry. An earlier version of this line said "roughly an hour"
and that was never measured.

| | |
|---|---|
| `wifi-watch.sh` | **Runs ON the device.** Polls `wlan0` every 20 s and logs every IPv4 transition with `dmesg`, association and process state. On a failure it runs **two probes** and then a **recovery ladder**, recording which rung works. Copy to `/sdcard/` and launch with `setsid`. Also carries an **optional preferred-AP steer**, off by default — see below. |
| `wifi-reassociate.sh` | **Rung 3, and runnable by hand.** Mirrors what the front panel's own `wifi_control.py` does, with the real credentials from `/sdcard/wifi.txt`. ⚠️ **bash, not sh** — it uses process substitution and the device's `/bin/sh` is busybox ash. |
| `wifi-poll.sh` | **Runs on the Mac.** Leave it in a terminal. Redraws a small block every minute and answers one question: *anything new since I started, y/n.* Rings the bell and raises a macOS notification. |
| `wifi-report.sh` | Pulls the evidence off the device and summarises it. **`--mark` first**, then it reports only what happened after the mark. |
| `../plan-v04.md` | What each outcome **means** and what to do about it. Hand it to an agent along with `wifi-report.sh`'s output. |

**The two probes are the point of the current rig**, because they split the fault before anything
tries to repair it:

| Probe | Asks | ✅ Answer so far |
|---|---|---|
| **link probe** | assigns the last-known-good address and route, pings the gateway | **`LINK IS FINE`** — 0% loss. The radio, the association and the path are healthy; the fault is **DHCP-side**. Item 159 |
| **DHCP probe** | `dhcpcd -T` — a full exchange that configures nothing | an **offer** means the server answers and the daemon is wedged; **no offer** means the server is not answering this client |

**The ladder is now STRONGEST-FIRST**, which is the reverse of how it started:

```
1. bash /sdcard/wifi-reassociate.sh     90 s   <- the only rung ever observed to work
2. dhcpcd -n wlan0                      45 s
3. dhcpcd -b -x wlan0 ; dhcpcd -b wlan0 45 s
```

⚠️ **Rungs 2 and 3 have each been measured failing on this fault four times**, at 45 s apiece —
over two and a half minutes of dead network before reaching the one that helps. Neither changes
which AP you are on, and that is what has to change. **They are kept, not deleted:** a future fault
with a different cause may well be fixed by them, and removing them discards the discriminator that
made these captures readable.

⚠️ **THREE SEPARATE DEFECTS HAVE PRODUCED A WRONG `UNRECOVERED` VERDICT** — read every historical
one as *"no address within the timeout"*, never as *"recovery failed"*:

1. rung 3 ran a **stale factory template** hardcoded to SSID `name`, killing a working supplicant
   and replacing it with nothing (item 161)
2. rung 2 used `dhcpcd -k`, which only **releases** the lease where `-x` **exits** the daemon
   (item 161)
3. ⚠️ **the winning rung's timeout was shorter than the recovery it was waiting for** — it printed
   `UNRECOVERED` about a rung that had just worked (item 178)

### The preferred-AP steer — present, proven, and OFF

`wifi-watch.sh` can steer the device back to a chosen BSSID on every healthy poll, preventing the
fault instead of recovering from it. ✅ **Measured working: satellite → router in 13 s.**

```sh
PREFER_BSSID=a6:40:a0:5e:a2:01 sh /sdcard/wifi-watch.sh    # enable
```

⛔ **It is off by default, deliberately.** Two reasons that only appeared once it ran:

- ⚠️ **The steer drops IPv4 itself** — a roam is a carrier change, so `dhcpcd` deconfigures every
  time it fires. That trades one rare long outage for frequent short ones.
- ⚠️ **IT HIDES THE ANSWER.** Keeping the device off the satellite means the fault can never recur,
  so the Orbi firmware update could never be evaluated. **The prevention masks the experiment.**

⚠️ **It is a PREFERENCE, NOT A PIN** — if the target is not in the scan it does nothing, so it
cannot strand the device the way a hard `bssid=` would.

⚠️ **And its visibility guard needs `iw dev wlan0 scan dump`, not `iw dev wlan0 scan`** — the bare
form *triggers* a scan and contended with `wpa_cli scan`, reporting NOT VISIBLE for an AP at
−47 dBm. **A false negative there is silent and total**: the steer would decline every time and
look installed while doing nothing. Item 187.

⚠️ **`wifi-poll.sh` does not rely on reachability.** The fault can drop and recover between two
polls and the Mac would never see it, so it reads the **transition count** out of the device-side
log — any increase means a drop happened whether or not anything was watching.

⚠️ **Liveness is a file, not a process match.** `pgrep -f wifi-watch` also matches the ssh command
that goes looking for it — that self-match made a running watcher look dead, and a `pkill -f` on the
same pattern killed the ssh session outright. The watcher writes `/sdcard/wifi-watch.pid` and
touches `/sdcard/wifi-watch.alive` every poll; **check the mtime.**

⚠️ **The self-match trap has now bitten three times, and the third was the worst** (item 163). A
hand-rolled `/proc/*/cmdline` scan has the same flaw, and so does a `case` pattern — **any** check
whose own command line contains the string matches itself. Worse, a sweep that **scans and
relaunches in one command** carries the script's path in its launch line, so it kills the shell
doing the sweeping: three `ssh` exits with status 255 before the cause was spotted. **Scan and
launch must be separate commands, and the sweep must skip its own `$$`.** The only reliable dodge
in a pattern is to split the literal: `PAT="wifi-""watch.sh"`.

⚠️ **Do not `rm` the pidfile to clean up** — that disarms the single-instance guard, and
`wifi-poll.sh` relaunches whenever the stamp goes stale, so two watchers appear. Kill the process
and let its `EXIT` trap remove the file. Item 167.

⚠️ **Never edit these while they are running.** `sh` reads a script incrementally by byte offset,
so an edit under a live interpreter is genuinely unsafe — restart the poll after changing it.

## Driving and rescuing hardware

### `go.sh` — the only way to drive a bench on the Organelle

One UDP datagram to the bench's `[netreceive 9998]`. Python's socket send rather than netcat, for
the reason above. `-n N` fires N of them half a second apart, which is how you walk a bench to a
particular step without judging every one on the way.

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

## Measuring, and probes still worth running

### `display-cpu.sh` — the repaint budget on the device

```sh
./tools/display-cpu.sh -n 3
```

item 94. Wraps the `/proc` arithmetic from [../ref/device-os.md](../ref/device-os.md)
→ *Measuring the running patch* and says WITHIN or OVER against the **11.2 %** budget — Phase 5's
10.2 % idle baseline plus one point. ⚠️ `pgrep -nx pd`, never a bare `pgrep`: the substring match
hits a kernel thread on this device.

### `display-diag.pd` — a real console for the display arbiter

These three load **alongside** a running `mother.pd` + `main.pd` (see *Running one* below).
None of them touches the deployed patch: they only read `oscOut` or push onto `disp`, `err`
and `mode`, exactly as a controller would.

| Patch | What it does |
|---|---|
| `display-bench.pd` | **The acceptance run.** Fourteen steps, **stepped by hand** — see *The benches are stepped by hand* below. Each prints what it is sending and a **PASS IF** line *before* the screen moves, including the steps whose correct result is that nothing happens. Run it in the **foreground** and watch the OLED. |
| `display-diag.pd` | Counts rather than dumps. `FRAMES` and `MESSAGES` are cumulative totals printed once a second, so the rate is the gap between lines — expect +10 and +100. Printing every OSC message instead would slow down the thing being measured. |
| `alert-buffer-probe.pd` | ✅ **Answered:** draws into the ALERT buffer (screen 4), `setscreen 4`, waits six seconds, `setscreen 3`. All of it works — but `g_oled` still doesn't use buffer 4, for the reasons in [ref-display.md](../ref/module/display.md). Keep it as the re-check if that ever gets revisited. |

### `lp-step0.pd` — the Launchpad index map, items 82–87

Everything Phase 6 needed to stop guessing about: the ring's CC numbers, how many colour specs
one SysEx really carries, whether that SysEx lights the ring as well as the pads, and what the
layout-select command actually does. All of it is now recorded in
the git history. Keep it as the re-check if a Launchpad is ever
swapped.

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

Findings from all of them are written up in [../ref/module/display.md](../ref/module/display.md).

### `stage-patches/` — menu patches for the venue

Organelle patches for things that can only be done **at the device with no laptop attached**.

⚠️ **None of them is deployed any more.** As of 2026-08-07 `/sdcard/Patches/!/` holds `Cut It` and
nothing else — at a venue you should scroll past nothing to reach the instrument. Each was confirmed
byte-identical to the copy here before it was removed, so any of them is one `scp` from coming back.
⬜ When the laptop-free debugging system in [plan-v04.md](../plan-v04.md) gets built, it goes in a
`! debug` directory rather than back into `!`.

| | |
|---|---|
| `Inquiry Probe/` | **Does a device answer a universal device inquiry?** It wires itself through `[shell]`, then asks one device every four seconds — Launchpad, nanoKONTROL, SP-404 — packing the phase number alongside every byte `[sysexin]` receives, and writes `/sdcard/inquiry-probe.log`. ⛔ **It asks the Launchpad FIRST and that is the whole method**: the Launchpad is known to answer, so phase 1 proves the channel. A silence from the other two means nothing until phase 1 has answered **in the same run**. ⛔ Its `inquiry-wire.sh` creates a **`Pure Data:5 → nanoKONTROL` link that has never existed anywhere in this project** — Cut It's `wire.sh` wires an input from the nano and no output to it, so the nano has never been sent a byte. [plan-v03.4.md](../plan-v03.4.md) branches on the answer. |
| `Anim Probe/` | ✅ **It answered item 77 on 2026-08-08, and the answer was "it never tracks at all"** — in Programmer Mode the Launchpad ignores incoming MIDI clock and flashes at ≈118 BPM regardless (item 257). Kept because it is the only thing in the project that exercises the animation channels, and a firmware update could change that. **Where does the Launchpad stop tracking the clock?** Item 77. Knob 1 sweeps an emitted MIDI clock from 5 to 1000 BPM on an exponential map, and four pads answer by eye: 43 and 47 are blinked **by the patch** at one and two beats, 44 and 48 are flashed and pulsed **by the device** at the same two rates. ⛔ **A ruler pad beside each animated one is the whole method** — the eye is bad at estimating a rate and excellent at seeing two things lap each other, so nothing has to be judged in absolute terms or remembered. ⛔ **The OLED's `act` line is the probe checking itself**: it counts the clock bytes actually emitted, and if `act` stops following `req` then the limit just found is Pd's, not the Launchpad's. ⛔ 120 BPM is the one tempo it cannot measure — 📄 the documented fallback *is* 120, so there a tracking device and a reverted one look identical. Aux marks the current pair into `/sdcard/anim-probe.log` and sends a Start, which is the other half of item 77. It takes Programmer Mode and hands it back on `quitting` like `m_launchpad` does, so leaving it from the menu is safe (item 252); **knob 4 releases the surface mid-session** so the Launchpad's own Settings menu — which Programmer Mode locks out — stays reachable without dropping the probe. |
| `AP Probe/` | ✅ Records what can only be seen **while the access point is up** — which is exactly when a Mac joined to it has no internet and nobody can watch. It logs to `/sdcard/ap-probe.log` and reads the phone's address from the dnsmasq lease file **or**, if dnsmasq has already exited, from `/proc/net/arp`. ⚠️ **That second strategy is what saved the run** (item 129) — a single-strategy probe would have returned `none` and taught us nothing. |
| `Start AP/` | ⛔ **A dead end, kept as the record of why.** ⚠️ It *does* have a `main.pd` — this page claimed otherwise until 2026-08-07 — but loading it does not work: `create_ap`, `hostapd` and `dnsmasq` all die with the Pd that spawned them **even behind `setsid nohup`**, so an AP cannot be started from a patch. Use **System → WiFi Setup → Start AP**. Item 129. Its password line is a **placeholder**; the live value is in `/sdcard/ap.txt`, because this repo is public. |
| `State Probe/` | Phase 8's on-device state probe. |
| `PGM Probe/` | ✅ Phase 9 Step 0B — **it proved Pd's `pgmout` is 1-based** (item 228). It loops `pgmout 20` every six seconds while `aplaymidi` sends raw `0xC0 20` from the shell, so the readout is **binary — does the program name move?** — rather than asking anyone to compare two names from memory. ⚠️ **It must `aconnect` Pd's Midi-Out 4 to the Uno after loading**, because a patch load drops the connection (see [../ref/device-os.md](../ref/device-os.md)); without that it measures silence and looks like a clean negative. |

**A menu patch is the CHEAP way to run a Pd-side MIDI probe, and `PGM Probe` is the pattern.**
The documented alternative is the by-hand three-patch console, which needs `killall pd` — and that
**strands the Launchpad in Programmer Mode every time** (item 96), costing a `tools/lp-live.sh`
recovery afterwards. `oscsend localhost 4001 /loadPatch s "!/<name>"` swaps the patch and swaps back
with no signal, so `quitting` fires normally and the Launchpad is never touched. Use it for anything
that only needs MIDI **sent**; use the console when you need `[print]` output back.

⚠️ **One side effect.** Loading this way leaves `!/Cut It` in `/tmp/curpatchname` where a menu
selection would leave `Cut It`, so **System → Save New afterwards makes a folder called `! 2`**.
Select the patch from the menu once before using Save New. Plain Save is unaffected — it works off
the `/tmp/patch` symlink. Same caveat as `deploy.sh`'s own load.

### Running one of these by hand

```sh
scp tools/lp-monitor.pd root@organelle.local:/tmp/

ssh root@organelle.local
  killall pd 2>/dev/null; sleep 1
  cd /tmp
  nohup pd -alsamidi -midiindev 1,2,3,4 -midioutdev 1,2,3,4 \
        -nogui -noaudio /tmp/lp-monitor.pd > /tmp/out.txt 2>&1 &
  sleep 2
  aconnect 'Launchpad Pro MK3':0 'Pure Data':0    # -> Pd device 1, channels 1-16
  aconnect 'Pure Data':4 'Launchpad Pro MK3':0    # LEDs and SysEx back out
  cat /tmp/out.txt
```

Stop with `killall pd`. ⚠️ **Then run `./tools/lp-live.sh`** — `killall pd` strands the Launchpad in
Programmer Mode every time, because Pd 0.49 has no `closebang` and only `mother.pd` sends `quitting`.

✅ **`lp-monitor.pd` was repaired on 2026-08-08 and prints three things it did not before.** It had
**no `[sysexin]`**, so a device-inquiry reply — or an announcement of a mode change made *by hand* —
arrived and was silently discarded, which is the one thing item 100 needs. It had **no `[ctlin]`**,
so the entire outer function ring was invisible to it. And its Live Mode escape was a **click-only**
message box, useless on a device that runs Pd with `-nogui` and has no mouse. Send any datagram to
port **9996** and the device is handed back:

```sh
python3 -c "import socket; socket.socket(socket.AF_INET, socket.SOCK_DGRAM).sendto(b'live;', ('organelle.local', 9996))"
```

⛔ **Not `nc`.** BSD `nc -u -w0` on macOS exits before the datagram is flushed and looks exactly like
a dead patch — the same reason `go.sh` and `dsp.sh` are Python. `tools/lp-live.sh` remains the
fallback that needs no running patch at all.

## Things these patches taught us

Findings specific to working *in this folder*. The Launchpad's own behaviour — palette,
animation modes, LED state, `polytouchin` ordering — is catalogued in
[../ref/device/](../ref/device/). Pd message-discipline traps (`[list trim]`, `route`'s
selector rules, `sendtyped` arity, `quitting`) are in
[../ref/conventions.md](../ref/conventions.md), and the OSC ones in
[../ref/module/display.md](../ref/module/display.md).

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
