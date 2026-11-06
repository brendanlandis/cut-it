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
| **Driving and rescuing hardware** | `lp-live.sh` `dsp.sh` + `dsp-toggle.pd` |
| **A checklist's Send lines**, onto the instrument's buses | `send.sh` ([the checklists' README](../test/checklists/README.md), *Send lines*) |
| **Measuring the device** | `display-cpu.sh` `display-diag.pd` |
| **Probes still worth running** | `lp-monitor.pd` `lp-step0.pd` `alert-buffer-probe.pd` |
| **Answering a device** — does it reply at all | `stage-patches/Inquiry Probe/` |
| **Watching a device animate** — does it still track the clock | `stage-patches/Anim Probe/` |
| **Trying a 404 flourish** — a pad stuttering slower while its pitch falls; the SP-404 has left the rig (2026-11-04) | `stage-patches/Flourish Probe/` |
| **A mic straight into the Organelle** — its level and hiss | `stage-patches/Mic Probe/` |
| **Worked examples** — a technique, kept as the proof | `audio-probe/` `oled-probe/` `osc-bridge/` `status-display/` |
| **The phone side** | `touchosc/` — the phone's TouchOSC layout, every screen and the line check's page: `CutIt.tosc`, built by `build.py` from its own code and `test/checklists/linecheck.md`; `push.sh` puts it on the phone through the Mac's TouchOSC (below) |
| **Menu patches** | `stage-patches/` — see below |
| **Editing a patch's comments** — delete or rewrite them and keep every cord | `pd-comments.py` |

⚠️ **Eighteen one-off probes were deleted on 2026-08-07** — seven for the SP-404 rate ceiling alone,
three July MIDI probes superseded by the `m_` layers, and a `wire.sh` here that was a 42-line-behind
ancestor of `Cut It/wire.sh` with no `|| true` on any line. Every finding is on a `ref/` page and
most are now asserted by a gate. They are all in git history.

⛔ **The test was "would you run it again", not "is it used".** A script mentioned in no document is
fine.

## Getting data back off the device

### `fetch-state.sh` — the instrument's own data

```sh
./tools/fetch-state.sh              copy /sdcard/cut-it-state/ into device-state/
./tools/fetch-state.sh --show       print it instead
./tools/fetch-state.sh --diff       show what would change, copy nothing
```

`u_state` deliberately writes OUTSIDE the patch folder so `tools/deploy.sh`, `--clean` and a power cycle
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
Mac's own `/24`, IPv6 neighbor discovery, and an AP-mode SSID scan — and names one of
**REACHABLE** · **ASSOCIATED-NO-LEASE** · **AP-MODE** · **ABSENT**.

⛔ **`ASSOCIATED-NO-LEASE` is the documented fault and `ABSENT` is not.** Item 81 leaves the device
associated, so ssh over IPv6 link-local keeps working the whole time — nothing answering *anywhere*
means powered off, adapter down, or a different SSID. Telling those two apart is the whole point.

⚠️ **The identity signal is the ssh banner**, OpenSSH 7.1 against 8.2 or newer for everything else
on this network (Reference, `~/Sites/!reference/critter-guitari-organelle-1.md`, *Reaching it*). It
is a heuristic; override with `ORG_BANNER=` if the image changes. ⛔ The first version tried mother's
OSC port 4001 instead, which is UDP where `nc -z` tests TCP (Reference, *Ports*), so it found the
Organelle and dismissed it. The first version also reported a NAS
as the documented fault, because it probed every IPv6 neighbor and believed whichever answered
first. **Both bugs were found by running it against the live network, not by reading it.**

⬜ Only the `REACHABLE` and `ABSENT` branches have been exercised against real hardware.
`ASSOCIATED-NO-LEASE` and `AP-MODE` are written from the recorded evidence and unproven.
Exercising them means reproducing the wifi fault on purpose, which `cut-it/wifi-roam-fault` says
not to do unless it recurs. **If it does, these two branches get their proof for free** — the fault
is the fixture, and it is a step there.

### Chasing it

⛔ **What the fault is, what it is not, the evidence ledger, the reproduction and the wrong turns
are under *Wifi* on the Organelle's Reference page (`~/Sites/!reference/critter-guitari-organelle-1.md`)**; the tools and the stage procedure are on
[../ref/wifi.md](../ref/wifi.md); what to try next and the binding stopping rule are on `cut-it/wifi-roam-fault` in `!projects`. **This page is how to RUN the tools; the Reference page is the subject.** ⚠️ **Do not
restate any of it here.**

| | |
|---|---|
| `wifi-watch.sh` | **Runs ON the device.** Polls `wlan0` every 20 s and logs every IPv4 transition with `dmesg`, association and process state. On a failure it runs **two probes** and then a **recovery ladder**, recording which rung works, and **runs the ladder again every 5 minutes** while the address stays gone; its last rungs reload the dongle's driver (`rt2800usb`) and then reset it on USB, for the wedge a router restart left (2026-11-04). Copy to `/sdcard/` and launch with `setsid`. Also carries an **optional preferred-AP steer**, off by default — see below. |
| `wifi-reassociate.sh` | **Rung 1, and runnable by hand.** Mirrors what the front panel's own `wifi_control.py` does, with the real credentials from `/sdcard/wifi.txt`. ⚠️ **bash, not sh** — it uses process substitution and the device's `/bin/sh` is busybox ash. |
| `wifi-poll.sh` | **Runs on the Mac.** Leave it in a terminal. Redraws a small block every minute and answers one question: *anything new since I started, y/n.* Rings the bell and raises a macOS notification. |
| `wifi-report.sh` | Pulls the evidence off the device and summarizes it. **`--mark` first**, then it reports only what happened after the mark. |
| The Organelle's Reference page (`~/Sites/!reference/critter-guitari-organelle-1.md`), *Wifi* | What each outcome **means**, item by item. Hand it to an agent along with `wifi-report.sh`'s output. |

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
one as *"no address within the timeout"*, never as *"recovery failed"*. All three are in
*The evidence, item by item* on the Organelle's Reference page (`~/Sites/!reference/critter-guitari-organelle-1.md`), items 161 and 178.

### The preferred-AP steer — present, proven, and OFF

`wifi-watch.sh` can steer the device back to a chosen BSSID on every healthy poll, preventing the
fault instead of recovering from it. ✅ **Measured working: satellite → router in 13 s.**

```sh
PREFER_BSSID=a6:40:a0:5e:a2:01 sh /sdcard/wifi-watch.sh    # enable
```

⛔ **It is off by default and must stay off** — the two reasons are on
[../ref/wifi.md](../ref/wifi.md) under *If it recurs*, and they are why it is not a fallback.

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

### `tidy.sh` — what has accumulated on the device, and what is safe to remove

```sh
./tools/tidy.sh              # survey only. Touches nothing. THE DEFAULT
./tools/tidy.sh --delete     # the same list, then asks before removing it
```

**Four categories, and only the first three are ever deleted:** bench patches (`*-bench.pd`,
`bench-tap.pd`) that the bench runner copied to the device until it was retired for
[checklists](../test/checklists/README.md) on 2026-11-03, probe logs whose findings already carry an item number, and loose `.pd`
files on `/sdcard` **that also exist in `tools/`**. ⛔ A `.pd` this repo has never heard of is left
alone — it is something you put there and did not write down, and removing it would be the script
guessing.

⛔ **The fourth category is DRIFT, and it is reported rather than deleted.** A deployed folder whose
files differ from the repo's is fixed by a push; the script prints the exact `scp`.
⚠️ `tools/deploy.sh` sends **both** patch folders every time so those two stay level by construction
— but the stage probes in `! debug` are copied by hand and nothing re-sends them.

⛔ **It is not a flag on `deploy.sh`, deliberately.** `deploy.sh` is run twenty times a day and must
stay boring; this one deletes things. The two share nothing but an ssh connection.

⚠️ **It never touches a patch folder.** Files deleted locally are `deploy.sh --clean`'s business,
which is a question about one folder you are looking at rather than a sweep.

**What it will not remove, ever:** the wifi investigation's watcher, log, pid and heartbeat; the
credentials; `cut-it-state/` and the error log; and the vendor's own files. ⛔ **A candidate has to
match a cruft pattern AND survive a `KEEP` guard**, and a collision between the two is treated as a
bug in the script — it refuses and exits 3 without deleting anything.

### `lp-live.sh` — rescue a Launchpad stranded in Programmer Mode

```sh
./tools/lp-live.sh
```

Sends the Live Mode SysEx with `amidi`, **needs no Pd at all**, and looks the port up by name
because `hw:N` numbering shifts (Reference, *mother's autoconnect, and ALSA numbers that move*).

**Why it is needed.** `m_launchpad`'s safe exit hooks `[r quitting]`, which only `mother.pd` sends
— right before mother itself quits Pd, with a 100 ms budget. Pd has no `closebang`, 0.49 or 0.57, so
that is the only shutdown hook there is. **Every other way a session can end leaves the device stranded**: a
crash, power loss, or `killall pd` — which the by-hand console workflow does every single time.
Programmer Mode locks out the Launchpad's own Settings menu, so the front panel cannot recover it.

Measured 2026-08-03: `killall pd` left the grid frozen in Programmer Mode, and this brought it back
with no power cycle. `tools/deploy.sh` is unaffected — it loads through `/loadPatch`, so `quitting` fires
normally.

### `dsp-toggle.pd` + `dsp.sh` — turn the audio engine off on a running patch

```sh
./tools/dsp.sh 0     # off
./tools/dsp.sh 1     # on
```

Load `dsp-toggle.pd` as a third patch beside `mother.pd` and `main.pd`. It touches no bus and owns
no surface; all it can do is set Pd's global DSP state.

**Why it exists.** Item 75 recorded that the Phase 5 clock roughly doubled Pd's CPU and blamed the
96 ALSA MIDI writes a second, unconfirmed by isolation. This is that isolation, and
it overturned the conclusion — **the DSP is the budget, not the MIDI, and the original guess was
wrong by a factor of sixteen.** The three-way readings are on
[../ref/module/tempo.md](../ref/module/tempo.md), item 75.

⚠️ **With DSP off the patch is silent and the clock stops** — `c_clock` is cut from a phasor,
so the grid stops walking and the transport stops counting. Expected, not a fault.

## Measuring, and probes still worth running

### `display-cpu.sh` — the repaint budget on the device

```sh
./tools/display-cpu.sh -n 3
```

item 94. Wraps the `/proc` arithmetic from [../ref/device-os.md](../ref/device-os.md)
→ *Measuring the running patch* and says WITHIN or OVER against a budget of one point above the
newest baseline row on that page. ⛔ **The budget is stated there, not here** — it went stale once
by being written in three places at once. ⚠️ `pgrep -nx pd`, never a bare `pgrep`
(Reference, `~/Sites/!reference/critter-guitari-organelle-1.md`, *Measuring the running patch*).

### `display-diag.pd` — a real console for the display arbiter

These two load **alongside** a running `mother.pd` + `main.pd` (see *Running one* below).
Neither touches the deployed patch.

| Patch | What it does |
|---|---|
| `display-diag.pd` | Counts rather than dumps. `FRAMES` and `MESSAGES` are cumulative totals printed once a second, so the rate is the gap between lines — expect +10 and +100. Printing every OSC message instead would slow down the thing being measured. |
| `alert-buffer-probe.pd` | ✅ **Answered:** draws into the ALERT buffer (screen 4), `setscreen 4`, waits six seconds, `setscreen 3`. All of it works — but `g_oled` still doesn't use buffer 4, for the reasons in [ref-display.md](../ref/module/display.md). Keep it as the re-check if that ever gets revisited. |

### `lp-step0.pd` — the Launchpad index map, items 82–87

Everything Phase 6 needed to stop guessing about: the ring's CC numbers, how many color specs
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
| `osc-bridge/` | Bidirectional OSC between Organelle and an iPhone running PdParty, the phone app until 2026-11-04. Sends a heartbeat and `knob1`; draws whatever arrives on `/cutit/fader` big on the OLED. |
| `status-display/` | The performance status protocol: four knobs sending **named parameters** (`chop-size`, `grain`, `speed`, `drunk`) plus a heartbeat. |
| `audio-probe/` | `env~` levels for `adc~ 1` and `adc~ 2` drawn large on the OLED. Used to verify the TRS input split; still the quickest way to check what is arriving at the inputs. |

Findings from all of them are written up in [../ref/module/display.md](../ref/module/display.md).

**They stay, and the question is settled rather than open.** The argument for deleting them was
that the claim on the `ref/` page is now the artifact and the patch is not — reasonable, and wrong
here, because **each one is a working reference for something the project is about to build again**.
✅ `oled-probe/` and `osc-bridge/` were both read while
[the debug patch](../ref/module/debug.md) was written, within the week, and `audio-probe/` is still
the quickest way to see what is arriving at the inputs.

⛔ **The test is "would you run it again", not "is it used".** A patch mentioned in no document is
fine if you would reach for it; a patch nobody would open again is dead weight even if three pages
cite it. That is what retired `self-wire.pd` and keeps these four.

⚠️ **`touchosc/` was never part of that question** — [../ref/device/phone.md](../ref/device/phone.md)
names it as a `Files:` entry, so it is live by definition.

### Deploying the phone's layout

```sh
./tools/touchosc/push.sh
```

It rebuilds `touchosc/CutIt.tosc` and puts it into the Mac's TouchOSC, whose editor server pushes
it to the phone live (TouchOSC's Reference page, *Editor network sync*). TouchOSC keeps one copy
open (Brendan, 2026-11-05): `push.sh` edits the CutIt document it has open, through TouchOSC's MCP
server, until it is the build (`touchosc/live.py`), rather than opening the file, which added a
document every time. A small change takes about a second, all told.

- **What a push sends**: only what differs, controls matched by name. A changed property or value
  reaches the phone as a few hundred bytes; each control made, moved or deleted resends it the
  whole document, so a new screen costs more (the 127 controls of the sections page: 437 edits in
  1.1 s on the Mac, 18 MB to the phone, which stayed connected). Then `live.py` reads the document
  back and says what still differs, if anything: `python3 tools/touchosc/live.py --diff` does that
  alone, changing nothing.
- **When it opens the file instead**: TouchOSC not running, its MCP server off, or no CutIt
  document open. Both of TouchOSC's servers are off after every launch unless it is started with
  `--editor.network.state=SERVER --mcp.enabled=true`, so `push.sh` launches it with both, in the
  background, and when it runs without the editor server, quits and relaunches it with them. With
  the editor server on and the MCP server off it opens the file and says so: Preferences > MCP
  Server turns that on without a relaunch, which would drop the phone.
- **More than one CutIt open**: `live.py` pushes to the active one and says so. Nothing it can
  call closes a document: close the others in TouchOSC, or quit it and push.
- **After a push that changed it, TouchOSC counts CutIt as modified**: it compares the document
  with the file as it opened it, not as `build.py` has since written it. If quitting asks to save
  it, Don't Save: the file is `build.py`'s, and one saved from the editor stops the next build.

Then it checks the phone is still connected, and says so when it isn't (exit 3): a phone that
dropped off keeps the old layout and shows nothing wrong.

### Working on the layout

**Two workflows** (Brendan, 2026-11-04). This one is for development, at home, with the Mac and
the house WiFi. At a performance there is neither: the phone joins the Organelle's own access point
and runs the layout saved on it before leaving ([../ref/wifi.md](../ref/wifi.md), *The stage
procedure*).

**The development workflow**, for while the phone's screens are being built:

```sh
python3 tools/touchosc/watch.py
```

- **The phone follows the code.** Every save of `build.py`, the line check or
  `Cut It/cut-it-drum-page.txt` rebuilds the layout and pushes it.
- **A dropped phone is told**, in a line and a Mac notification, as it happens and as it comes back.
- **A change made in TouchOSC's editor comes back into the code.** Move, resize or recolor something
  in the Mac's TouchOSC (the phone takes it live, before any save) and save with **File > Save from
  the menu**; Cmd-S did nothing on 2026-11-04: the watcher lists the change (`python3 tools/touchosc/diff.py`
  does the same by hand), it goes into `build.py`, and the next build writes the file again.
  `build.py` refuses to write over a `CutIt.tosc` saved from the editor until then (`--force`
  discards the change), so a tweak is never lost, and stops the watcher pushing. A change made in
  the editor and not saved is kept the same way: a push that would undo it refuses (exit 4), says
  what it is, and the watcher tells it; save it, or `push.sh --force` discards it.
- **Look at a page without the phone**: `python3 tools/touchosc/preview.py` draws every page, and
  each of a page's tabs under its own tab bar, as the phone shows it, the drum screen once for each effect its effect radio shows, with the editor's 20-point grid over it and the notch's margin marked, into
  `tools/touchosc/preview/` (open its `index.html`). It approximates TouchOSC's drawing; the
  phone is the oracle for looks, this is for layout.
- **The design rules** (Brendan, 2026-11-04): every control on the editor's 20-point grid
  (anchored at the document's center, so its lines on a page run at 8 and 7 plus steps), inside
  the page's margins; captions flush left over their controls; values and button words centered;
  status on the bottom row. `ref/device/phone.md`, *The grid*, has the panels and columns. One
  exception (Brendan, 2026-11-05): the drum screen's pads and the M and S under each step by 10
  points and start 10 into the top margin, ending on the bottom one inside the page's 334-point frame; `touchosc-assert` names them, and nothing else.

**Every screen is a page, and the editor reaches each by its tab** (Brendan, 2026-11-04). No script
runs in the editor, so nothing in the layout is hidden for a script to show:

- **The top tab bar is the phone's pages**, the outer pager, `pages`: arrangement, drums,
  synths, page 4 to page 6, sections, songs, and line check last. Click a tab to open that page; on the phone
  the root's script hides this bar and turns the pager to the page the `mode` bus names, by `build.py`'s `MODE_PAGES`.
- **Under it is the page's own tab bar**, its pager (`tabs1` to `tabs8`, `checktabs`): one tab each,
  named for the page, and the page's controls under that, but the synths page's four, the sections
  page's two and the songs page's three. A second tab
  for a page is a second page in that pager, `build.py`'s `TABBED`.
- **To edit inside a page**, descend into the pager and then its page with Edit container (the
  Edit context menu, or the toolbar), and come back with Exit container, as TouchOSC's manual has it
  for any container; the controls' names are build.py's (`tempobox`, `pad5`, `svel`, …). The
  editor's pager navigation must be on, its default (Preferences, Editor); with its Alt-key option
  set, hold Alt to click a tab. The Document Tree selects any control by name.
- **Pages 4 to 6 are blank** under their tabs: nothing is on them yet. The sections page, page 7,
  has two tabs, sections and name, and the songs page, page 8, three, songs, setlists and name
  ([../ref/device/phone.md](../ref/device/phone.md)).

⚠️ **Judge spacing on the phone, not in the editor**: the editor shows both bars, and the phone
hides the outer one. Whether its pages then move up a bar or keep its place empty is unseen
([../ref/device/phone.md](../ref/device/phone.md), *Open*); the screens fit either way.

**The phone's setup, once:** in TouchOSC, connect to the Mac as an editor client (port 6666), and set
OSC connection 1: UDP, host `192.168.1.15`, send port 9001, receive port 8000.

⛔ **The send host must be right, and a wrong one fails silently while receiving still works**: the
phone shows everything, so the link looks fine, and nothing it sends arrives (2026-11-04). It is
`192.168.1.15` on both networks: the house router reserves it, and the Organelle's own access point
uses it too (`device/start-ap.sh`). Item 312: PdParty would not resolve `organelle.local`, so the
address has been literal since.

### `stage-patches/` — menu patches for the venue

Organelle patches for things that can only be done **at the device with no laptop attached**.

⚠️ **None of them is in the instrument's menu any more.** As of 2026-08-07 `/sdcard/Patches/!/` holds
`Cut It` and nothing else — at a venue you should scroll past nothing to reach the instrument. Each
was confirmed byte-identical to the copy here before it was moved, so any of them is one `scp` from
coming back.

✅ **`! debug/` is where they went, and it is a real directory on the device** — `Anim Probe` and
`Inquiry Probe` are in it today. It is the same folder
[the debug patch](../ref/module/debug.md) deploys into: **anything you might reach for *instead of*
playing belongs there rather than beside the instrument.** ⚠️ This page claimed none of them was
deployed at all until 2026-08-12, which was read straight off the device and was never quite true.

| | |
|---|---|
| `Inquiry Probe/` | **Does a device answer a universal device inquiry?** It wires itself through `[shell]`, then asks one device every four seconds — Launchpad, nanoKONTROL, SP-404 — packing the phase number alongside every byte `[sysexin]` receives, and writes `/sdcard/inquiry-probe.log`. ⛔ **It asks the Launchpad FIRST and that is the whole method**: the Launchpad is known to answer, so phase 1 proves the channel. A silence from the other two means nothing until phase 1 has answered **in the same run**. ⛔ Its `inquiry-wire.sh` creates a **`Pure Data:5 → nanoKONTROL` link that has never existed anywhere in this project** — Cut It's `wire.sh` wires an input from the nano and no output to it, so the nano has never been sent a byte. ✅ **The answer came back and it is item 249**: all three devices reply, and byte 5 discriminates all three — so every one of them gets active polling. ⛔ **The missing outbound link was real** — `wire.sh` gained a seventh `aconnect` and six links became seven, item 274. See [ref/module/presence.md](../ref/module/presence.md). |
| `Anim Probe/` | ✅ **It answered item 77 on 2026-08-08, and the answer was "it never tracks at all"** — in Programmer Mode the Launchpad ignores incoming MIDI clock and flashes at ≈118 BPM regardless (item 257). Kept because it is the only thing in the project that exercises the animation channels, and a firmware update could change that. **Where does the Launchpad stop tracking the clock?** Item 77. Knob 1 sweeps an emitted MIDI clock from 5 to 1000 BPM on an exponential map, and four pads answer by eye: 43 and 47 are blinked **by the patch** at one and two beats, 44 and 48 are flashed and pulsed **by the device** at the same two rates. ⛔ **A ruler pad beside each animated one is the whole method** — the eye is bad at estimating a rate and excellent at seeing two things lap each other, so nothing has to be judged in absolute terms or remembered. ⛔ **The OLED's `act` line is the probe checking itself**: it counts the clock bytes actually emitted, and if `act` stops following `req` then the limit just found is Pd's, not the Launchpad's. ⛔ 120 BPM is the one tempo it cannot measure — 📄 the documented fallback *is* 120, so there a tracking device and a reverted one look identical. Aux marks the current pair into `/sdcard/anim-probe.log` and sends a Start, which is the other half of item 77. It takes Programmer Mode and hands it back on `quitting` like `m_launchpad` does, so leaving it from the menu is safe (item 252); **knob 4 releases the surface mid-session** so the Launchpad's own Settings menu — which Programmer Mode locks out — stays reachable without dropping the probe. |
| `AP Probe/` | ✅ Records what can only be seen **while the access point is up** — which is exactly when a Mac joined to it has no internet and nobody can watch. It logs to `/sdcard/ap-probe.log` and reads the phone's address from the dnsmasq lease file **or**, if dnsmasq has already exited, from `/proc/net/arp`. ⚠️ **That second strategy is what saved the run** (item 129) — a single-strategy probe would have returned `none` and taught us nothing. |
| `Start AP/` | ⛔ **A dead end, kept as the record of why.** ⚠️ It *does* have a `main.pd` — this page claimed otherwise until 2026-08-07 — but loading it does not work: `create_ap`, `hostapd` and `dnsmasq` all die with the Pd that spawned them **even behind `setsid nohup`**, so an AP cannot be started from a patch. Use **System → WiFi Setup → Start AP**. Item 129. Its password line is a **placeholder**; the live value is in `/sdcard/ap.txt`, because this repo is public. |
| `State Probe/` | Phase 8's on-device state probe. |
| `Mic Probe/` | **Can a vocal mic go straight into the Organelle's input?** ✅ Yes (2026-11-04): an SM58 on the tip of the stereo input, with `Capture` 15 and the attenuator off, sang at -13 dBFS against hiss at -71 (Reference, Organelle page). Knob 1 adds Pd gain, knob 2 is a gate, knob 3 the chip's input gain; the lowest C records 10 s of the raw input to `/tmp/mic.wav`. It changes the codec's input gain; loading Cut It puts it back. |
| `Flourish Probe/` | ⚠️ **For the SP-404, which left the rig on 2026-11-04**: it plays Pd's port 3, now the Streichfett's, but wires only to `SP-404MKII`, so without the 404 it sends nowhere. **Can a 404 pad stutter slower and slower while its pitch falls?** Two ways, both retriggering on the 404 (Brendan, 2026-11-04): Pd fires pad A11 on a widening gap in milliseconds, at its own pitch or a semitone lower each hit on chromatic mode's channel 16; or it loads DJFX Looper on BUS 1, fires A11 once and lowers the looper's SPEED by CC. Nothing is set on the 404 by hand. Every run is recorded from the Organelle's input to `/tmp/flourish-<job>.wav`, so it can be copied back and checked from the Mac. The keys and knobs are in its `main.pd`, the rules and the CC map in `flourish.lua`. |
| `PGM Probe/` | ✅ Phase 9 Step 0B — **it proved Pd's `pgmout` is 1-based** (item 228). It loops `pgmout 20` every six seconds while `aplaymidi` sends raw `0xC0 20` from the shell, so the readout is **binary — does the program name move?** — rather than asking anyone to compare two names from memory. ⚠️ **It must `aconnect` Pd's Midi-Out 4 to the Uno after loading**, because a patch load drops the connection (see [../ref/device-os.md](../ref/device-os.md)); without that it measures silence and looks like a clean negative. |

**A menu patch is the CHEAP way to run a Pd-side MIDI probe, and `PGM Probe` is the pattern.**
The documented alternative is the by-hand three-patch console, which needs `killall pd` — and that
**strands the Launchpad in Programmer Mode every time** (item 96), costing a `tools/lp-live.sh`
recovery afterwards. `oscsend localhost 4001 /loadPatch s "!/<name>"` swaps the patch and swaps back
with no signal, so `quitting` fires normally and the Launchpad is never touched. Use it for anything
that only needs MIDI **sent**; use the console when you need `[print]` output back.

⚠️ **One side effect: System → Save New afterwards makes a folder called `! 2`** (Reference,
`~/Sites/!reference/critter-guitari-organelle-1.md`, *Loading a patch from the shell*). Select the
patch from the menu once before using Save New. Same caveat as `tools/deploy.sh`'s own load.

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
Programmer Mode every time, because Pd has no `closebang` and only `mother.pd` sends `quitting`.

✅ **`lp-monitor.pd` was repaired on 2026-08-08 and prints three things it did not before.** It had
**no `[sysexin]`**, so a device-inquiry reply — or an announcement of a mode change made *by hand* —
arrived and was silently discarded, which is the one thing item 100 needs. It had **no `[ctlin]`**,
so the entire outer function ring was invisible to it. And its Live Mode escape was a **click-only**
message box, useless on a device that runs Pd with `-nogui` and has no mouse. Send any datagram to
port **9996** and the device is handed back:

```sh
python3 -c "import socket; socket.socket(socket.AF_INET, socket.SOCK_DGRAM).sendto(b'live;', ('organelle.local', 9996))"
```

⛔ **Not `nc`**, which sends nothing and looks exactly like a dead patch (Reference, Organelle page,
*Sending the device a UDP datagram*) — the same reason `dsp.sh` is Python. `tools/lp-live.sh` remains the
fallback that needs no running patch at all.

## Things these patches taught us

Findings specific to working *in this folder*. The Launchpad's own behavior — palette,
animation modes, LED state — is on its Reference page
(`~/Sites/!reference/novation-launchpad-pro-mk3.md`); Pd's (`loadbang` before ALSA, `polytouchin`
ordering, what `route` passes on, `[random]`) on `~/Sites/!reference/pure-data.md`; the Organelle's
ALSA (names that stay put, numbers that move, `amidi` against Pd) on
`~/Sites/!reference/critter-guitari-organelle-1.md`. Pd message-discipline rules (`[list trim]`,
`route`'s selector rules, `sendtyped` arity, `quitting`) are in
[../ref/conventions.md](../ref/conventions.md), and the OSC ones in
[../ref/module/display.md](../ref/module/display.md).

- **Every patch here sends its init SysEx behind `[loadbang] → [del 2000]` or longer**, because
  `loadbang` fires before ALSA connections exist.
- **`aconnect` and `amidi` by name, never by number**, and **`aseqdump` to watch a port Pd holds**:
  `amidi` cannot open it.
- **`[random]` is banged, never fed a float**: at grid-refresh rates a float there produced 2,500
  errors a second.
- **A patch can wire its own `aconnect` calls** via `[shell]`, but put the commands in a shell
  script — Pd message boxes and shell quoting do not mix well.
- **`[t b]` after a `route` whose match you only need to count.** `route /oled/gClear` passes on
  `ii 3 1`, which a float inlet answers with `float: no method for 'ii'` on every message: an
  endless console scroll at a 10 Hz redraw.
