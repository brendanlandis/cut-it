<!-- schema: device -->
# The phone — TouchOSC and the status link

**Files:** `Cut It/u_net.pd`, `Cut It/phone-ip.sh`, `tools/touchosc/build.py`, `tools/touchosc/push.sh` · **Gate:** `test/gate/phone-assert.sh`, `test/gate/touchosc-assert.sh` · **Checklist:** `test/checklists/phone.md`

An iPhone running TouchOSC on the same network (from 2026-11-04; PdParty until then), used as **an
unlimited plain-English display** — and, more valuable, as the answer to the Organelle having no Pd
console. What TouchOSC is and does — its file, how it draws, its scripts, its connections, the editor
sync that deploys to it — is in Reference: `~/Sites/!reference/touchosc.md`; what was measured with
PdParty stays on `~/Sites/!reference/pdparty.md`. This page is the status link Cut It builds on them.

`u_net.pd` is the fourth display surface and the only file that talks to it. It consumes `disp` like
the `g_` arbiters but **owns no selector on it**, so adding it cost `g_oled`'s route nothing. It
coalesces per name at 20 Hz with a guaranteed trailing edge, holds the last alert as *state* and
repeats it, and rebuilds its own socket — which a phone leaving the network destroys outright.

**The phone is part of the instrument** (Brendan, 2026-11-03), no longer only a monitor: its screen
follows the Launchpad's mode: in mode 1 the drum screen, beside the drum page; in every other mode,
the remote screen. The checklist page is a page of its own, holding the line check, which test mode
puts in their place (Brendan, 2026-11-04). **The link runs both ways.** Outbound it carries six addresses — parameters,
status, a heartbeat, a held alert, the mode and the drum screen's state. Inbound it takes **a closed
vocabulary of five commands** (three diagnostic, one for the checklist page, one for the drum screen),
acknowledges each one, and drops everything else in silence. ⚠️ **UDP over WiFi arrives unevenly**, visibly so in
the heartbeat counter and measured under *Broadcast* in Reference and below; that is the evidence anything
time-critical would have to answer to.

**The one decision this page turns on: the inbound vocabulary is closed, and the closure is the
feature.** An inbound socket is an attack surface on a shared network, and a set small enough to read
in one line is what makes the first one safe to reason about.

## Design

### Addresses and ports

| Device | Address | Notes | Evidence | Item |
|--------|---------|-------|----------|------|
| Organelle | `192.168.1.15` | Listens on **9001**. Reserved for it on the house router, and its own access point takes the same address (`device/start-ap.sh`), so the phone's send host is set once | verified | — |
| iPhone | `192.168.1.9` | `u_net` sends to TouchOSC's OSC receive, **8000**. Reserved for it on the house router (Brendan, 2026-11-03); `192.168.1.5` until then, which turned out to be the printer | unknown | — |
| Mac | `192.168.1.6` | Dev machine, by DHCP and not reserved (seen 2026-11-03; `192.168.1.16` earlier) | verified | — |

**The Organelle is `192.168.1.15` on both networks**: the house router reserves it, and its own
access point uses it too (from 2026-11-03; the factory AP was `192.168.12.1`). The phone's address is
the house network's at home and whatever the access point leases it at a gig.

**Nothing in the patch is configured with either** — `phone-ip.sh` resolves it at load. See
*The phone cannot announce itself* under **Design** for why, and what it costs to change.

| Port | Status | Evidence | Item |
|------|--------|----------|------|
| 4001–4003 | **Do not use** — mother's (Reference, `~/Sites/!reference/critter-guitari-organelle-1.md`, *Ports*) | verified | — |
| 9001 | The Organelle's OSC receive. `u_root` passes it to `u_net` as arg 3 | verified | — |
| 9002 | **The Mac's**, so `main-dev.pd` and a suite run cannot fight over one socket | verified | 307 |

TouchOSC's connections are set in the app, not in the layout (Reference): OSC connection 1, UDP,
host `192.168.1.15`, send port 9001, receive port 8000. ⛔ **A wrong send host fails silently while
receiving still works**: the phone shows everything, so the link looks fine, and nothing it sends
arrives (2026-11-04).

**So the phone's send host is `192.168.1.15` everywhere**, set once. PdParty could not send to the
broadcast address or resolve a name (Reference, item 312), so a fixed address was the only way to
stop re-pointing it, and TouchOSC is set the same way; on the house network that took the router's
reservation (Brendan, 2026-11-03). The
instrument still discovers the *phone* by itself, with `phone-ip.sh`, and this is the one direction
that cannot be discovered — see *The phone cannot announce itself* under **Design**.

### The wire format

```
Organelle -> phone
/cutit/param   <name> <value> <unit>              coalesced per NAME at 20 Hz
/cutit/status  <symbol>                           coalesced, one slot
/cutit/hb      <counter> <test mode, 0 or 1>      every 500 ms
/cutit/alert   <count> <level> <source> <text>    every 500 ms, always present
/cutit/mode    <class> <mode-n>                   on change and every 500 ms
/cutit/drums   <41 numbers>                       c_steps' state, on change and every 500 ms
/cutit/ack     <command> [<device>]               once per command accepted

phone -> Organelle
/cutit         <command> [<device>]               port 9001, anything else dropped
```

⚠️ **The command travels as ARGUMENTS of `/cutit`, not as address components.** `[oscparse]`
flattens `/cutit/re-wire` and `/cutit` carrying the string `re-wire` to the same list, so this is
simply the cheaper of the two to build — one `[oscformat cutit]` on the phone rather than one per
button.

### The inbound vocabulary

<!-- check: pd-route "Cut It/u_net.pd" re-wire -->

| Command | Does | Evidence | Item |
|---------|------|----------|------|
| `re-wire` | Publishes `re-wire` on the `presence` bus, and `u_present` forks `wire.sh` — see [presence.md](../module/presence.md) | verified | 306 |
| `clear-alert` | Writes the empty alert to `u_net`'s held store, so the 2 Hz repeat goes back to `none` / `-` | verified | 306 |
| `test-note` | Fires one probe at a sounding device, out a cord. Takes the device below | verified | 306 |
| `result` | A step's verdict, `<checklist>-<n>-<pass or fail>`, logged as `info phone <verdict>`, in test mode or not; answered `ack result` | unknown | — |
| `drums` | A drum screen control, passed on whole: whatever follows `drums` goes out `u_net`'s third outlet to `c_steps`, which refuses one it does not know as `fail c_steps bad-selector`, so a new drum control needs nothing in `u_net` (Brendan, 2026-11-04). `sync`, `snap` and `select` are answered `ack drums <action>`, the rest not, since the state shows them | verified | — |

<!-- check: pd-route "Cut It/u_net.pd" m_volca -->

| Device | Probe | Evidence | Item |
|--------|-------|----------|------|
| `m_volca` | `notes 60 100 200` — middle C, 200 ms, released by `makenote` | verified | 306 |
| `m_404` | `pad 1 100` — bank A pad 1 | verified | 306 |

What the drum screen sends after `drums`, each one `c_steps`' own (`R.presses` in `c_steps.lua`).
`touchosc-assert` checks the layout against that table, and `u_net`'s acknowledgments against the layout.

| Drum action | Does | Evidence | Item |
|-------------|------|----------|------|
| `sync` | "sync first steps": every track back to its step 1 together when the global loop next comes round to its own, each keeping its own last step ([sequencer.md](../module/sequencer.md)) | verified | — |
| `snap` | "snap to global": the same, and at that step every track takes the global last step | verified | — |
| `select` | A pad on the drum screen, `select <n>`: selects track *n* without playing it | verified | — |
| `num` | The time signature's top number, `num <-1 or 1>`: one down or up, 1 to 32 | verified | — |
| `den` | Its bottom number, `den <-1 or 1>`: one down or up through 1 2 4 8 16 | verified | — |
| `drunk` | Drunkenness, `drunk <0-100>`: how often a step strays, up to one in three, and how far, up to a whole step | verified | — |
| `skip` | The selected track's skip chance, `skip <0-100>` | verified | — |
| `move` | The selected track's move chance, `move <0-100>`: a step early or late | verified | — |

**The two sounding devices are the whole set**, and it is `u_map`'s: the Launchpad and the
nanoKONTROL are inputs. ⛔ **A device name off that list is dropped exactly like an unknown command.**

⚠️ **The 404 probe starts whatever pad A1 holds, and a LOOPING sample keeps playing.** `m_404`
schedules its note-off correctly — the loop is the 404's own sample setting, not a stuck note — so
nothing in the patch can end it and All Notes Off will not either. **Press the pad on the device to
stop it.** Pad A1 is kept anyway: the probe's job is to make a noise you can identify, and a loop is
easy to identify. Item 311.

| Property | Value | Evidence | Item |
|----------|-------|----------|------|
| `alert` and `hb` | Repeated **unconditionally at 2 Hz** | verified | — |
| `param` and `status` | Repeated every 2 s **on top of** their event-driven sends | verified | — |
| Late or returning phone | Repopulates in about two seconds with nothing moving | verified | — |
| Rate limiting | 401 `disp` messages a second measured down to **42 datagrams** | verified | — |
| `status` | Coalesced into **one slot** like a parameter: `u_tempo` writes the BPM into the footer, so one sweep of knob 1 put **201** `status` messages on `disp` in a second, as many as every parameter together | verified | — |
| Socket recovery | `u_net` rebuilds within about five seconds of the phone coming back, nothing touched on the instrument | verified | 119 |
| Backgrounding the phone's app | PdParty's cost the link nothing, only a full quit closed the port (Reference, item 120); TouchOSC's is untested | unknown | 120 |

**One address for all parameters.** Adding a parameter costs one `[list prepend <name>]` on the
Organelle and nothing at all on the phone — this scales to the nanoKONTROL's 18 continuous controls
without redesign.

### The screens: one TouchOSC layout

**Every screen is one layout**, `tools/touchosc/CutIt.tosc`, **generated** by `tools/touchosc/build.py`:
edit that, never the file. Each control sends from a script of its own; the root's script takes
everything that comes in.

**The design is Brendan's** (2026-11-04, iterated from mockups): TouchOSC's own controls and its own
tab bar, never a stack of shapes standing in for one; black, with bright red (`#FF1F3F`) the lead
accent and teal the second; monospaced type for every value, TouchOSC's default font for every label;
and every text and control at **WCAG AA**, which `touchosc-assert` audits from the file.

| | | Evidence |
|---|---|---|
| The tabs | TouchOSC's own tab bar, holding the mode's screen and saying which: drums in mode 1, remote in every other mode. One tab each for now; a mode may have more | unknown |
| Test mode | Coming on, the checklist page, under a tab bar of its own, stands in for the tabs; going off takes it away (Brendan, 2026-11-04). A mode chosen on the Launchpad turns it off, so the mode's tab is what shows next (Brendan, 2026-11-04). A flip sends a heartbeat at once, so the page turns with the tap rather than at the next of the 2 Hz beats | unknown |
| The drum screen | Left: the tempo, large, playing or stopped with its lamp, the global last step, the link lamp, the alert. Middle: the sixteen pads as the Launchpad lays them out, pad 1 at the bottom left (Brendan, 2026-11-04), read from `cut-it-drum-page.txt`, each labeled with its last step: red following the global one, teal with a dot (• 5) with its own, lit when selected; a tap selects. ⛔ A pad the state lights never sends: when it did, four pads pressed at once on the Launchpad lit in turn on the phone, each selecting itself again, and the selection bounced between Cut It and the phone for as long as they were held (2026-11-04). Right: sync first steps and snap to global, a line while one waits for step 1, ring knobs for drunk and the selected track's skip and move, and the time signature as [n] / [d], each box dragged up or down a step at a time (Brendan, 2026-11-04), about 20 points a step for the top number's 32, 26 for the bottom's 5 | unknown |
| The remote screen | Left: the last parameter's name and its value large, with its unit (`120 (29)` for a held tempo), the tempo, the alert with its lamp, the link. Right: re-wire, clear alert, test Volca, test 404 | unknown |
| The checklist page | The line check a step at a time, from `test/checklists/linecheck.md` ([the checklists' README](../../test/checklists/README.md), *The line check*): its position and title, its text, Pass and Fail, Back and Next | unknown |
| An answer | `/cutit/ack` flashes its button teal for 300 ms, by its color, never its value, so it can't send the command again | unknown |
| A knob or a time signature box | Sends when a finger moves it off the value it knows, its own or the one the state handed it, so the state is never sent back; for a second after a touch the state leaves it alone. A box sends `num` or `den` once a step, as `c_steps` takes them | unknown |
| `/cutit/drums` | `c_steps`' `R.phone`: playing, the global last step, the selected track, pending (0, 1 sync, 2 snap), the sixteen last steps, then 1 for each track with its own, then the time signature's two numbers, the drunkenness, and the selected track's skip and move chances. Sent by `c_steps` when it changes, through `u_root`'s cord into `u_net`'s second inlet | verified |
| A short or empty state | Fewer than 41 numbers draws nothing, so the empty repeat before the first state leaves the screen as it was | unknown |
| Deploying | `./tools/touchosc/push.sh` rebuilds the layout and opens it in the Mac's TouchOSC, restarting that with its editor server on if it is off; the phone, connected once as an editor client of the Mac, takes it live | verified |
| The phone's setup, once | Editor network: a client of the Mac (port 6666). OSC connection 1 as above | verified |

### Two instruments will fight over one phone

⛔ With the Organelle running Cut It **and** `main-dev.pd` running on the Mac, both connect to the
same phone and the status row **flutters between two values**. The bus is innocent — a `[r disp]` tap
shows four messages and no repeats.

**`u_net` is the sole owner of the phone WITHIN an instrument; nothing arbitrates ACROSS machines**,
and the symptom looks nothing like contention.

**Fix:** none in the patch. **It will recur during off-device development with the device still
powered** — close one of them.

### A phone joining mid-session saw blanks

⛔ Sent only on change, parameters and status leave a screen opened later showing **empty rows until
something moves**. The alert never has this problem, and the OLED never has it either, because it
redraws held state every frame. **`u_net` is the one surface where a late viewer could see nothing.**

**Fix:** a 2 s repeat of the last parameter and status, on top of the event-driven sends — well below
the 124/s noise floor. Item 121.

### A lost phone is the phone's to report

**The Organelle does not warn when the phone goes** (Brendan, 2026-11-03). Under Pd 0.49 `u_net`
warned `net-link-down` once per load when its socket died with nothing listening on the phone's port.
Under 0.57 the socket survives that, on the device too (measured 2026-11-03: a throwaway 0.57 sent at
a port nothing bound for 15 s and never noticed, where 0.49 warned within two seconds), so the
warning could no longer fire and was taken out. The phone's own no link, from the heartbeat's
silence, is the report: the phone is the display that went.

### Rebuild the socket

Under 0.49 a UDP `connect` to a port with nothing listening survived exactly one datagram (Pure
Data, in Reference), and the socket died. Under 0.57 it survives and delivers again once something
listens, on the Mac and on the device. `u_net` still reconnects on a timer until a connect first
succeeds, for a phone that was not on the network at load.

### The unit field is written on every param message

`disp` treats the unit as optional, and a message without one is too short for `u_net`'s
`[list split 3]`, which passes it out of its rightmost outlet alone (Pure Data, in Reference). **Fix:** `u_net` appends the dash *before* splitting, making the
optional field mandatory by construction. The unit is written on every message, as `-` when there is
none.

### `test-note` takes symbols

`[route 404]` matches a float and can never match the device name (Pure Data, in Reference, item
308): `[route volca 404]` rejected `test-note 404` while accepting `test-note volca`, both spellings
driven over a real socket. **Fix:** the devices are `m_volca` and `m_404`, which are symbols whatever else is true. That is
also the name the `presence` bus and `err`'s `source` field already carry across the `m_` boundary.

### A button's lamp is its own cell, lit by the answer

Each button is a box under its label, with a touch over both: the touch sends and never receives,
and the root script lights the box when the Organelle acknowledges, so no answer can re-send a
command. (PdParty's `bng` re-sent what it received, item 309, which once made this a rule with a
gate of its own.) `touchosc-assert.sh` checks every acknowledgment `u_net` sends lights a cell.

### The inbound port is armed late, and the Mac has its own

A second bind of the same UDP port prints a real line on stdout (Pure Data, in Reference, item 307),
and **stdout is the oracle** both `tools/deploy.sh` and the suite's silence gate use, so a patch that
bound at `loadbang` would turn every run red whenever a copy was already open in Pd.

**Fix:** two things, each independently sufficient for its own case. The `listen` is armed at
**2000 ms**, past the ~735 ms at which the deploy check quits, so neither it nor the syntax gate ever
binds at all. And `main-dev.pd` takes **9002** where `main.pd` takes 9001, so a long-running gate
cannot collide with the dev patch. ⚠️ **The phone's buttons therefore drive the device, not the Mac**
— point the phone's TouchOSC at 9002 if you want them to reach `main-dev.pd`.

### An AP session cannot be driven interactively

⚠️ A laptop joined to the Organelle's own access point is offline, so nothing Mac-side can reach the
phone or the device during a stage session.

**Fix:** stage everything beforehand — the checklist is on [wifi.md](../wifi.md).

### Send state, never events

Every message carries the complete current value — `chop-size is 43`, never `chop-size +1`. A dropped
packet then **self-corrects on the next send** instead of leaving the display permanently and
silently wrong. UDP will drop packets; the protocol has to not care.

### Broadcast was tried and rejected, and the reason is latency not throughput

It works and 19–20 of 20 datagrams arrive, but access points release broadcast frames on beacon
boundaries: bursts of three or four, up to **819 ms** between them (Reference). Throughput is identical
and latency is not, and one 819 ms gap eats most of the phone's **1500 ms** `no link` margin.

### The address resolves at 1550 ms on the device and 2200 on the Mac

⚠️ **Anything armed earlier fires into an empty host.** A reconnect metro that bangs the address
store **before resolution** sends `connect` with an empty host and prints `bad host?` on **every
boot** — harmless, and invisible to `tools/deploy.sh` because the syntax check quits first.

**Fix:** arm at **3000 ms**, past both platforms. A `[metro]` fires the moment it starts (Pure
Data, in Reference), so "armed at" means "fires at". On the Mac a `[del 700]` fallback covers a `[shell]` that never answers.

### The phone cannot announce itself, so the Organelle looks the address up

⚠️ **`[netreceive]` in 0.49 cannot tell you who sent a datagram.** Checked before designing around
it, and it is why the obvious answer — the phone announcing its own address — was not available.
**0.57 can**: `[netreceive -u -b -f]` puts the sender's address and port on a second outlet
(measured on the Mac, 2026-11-03; Pure Data, in Reference).

`phone-ip.sh` reads the DHCP lease the Organelle handed out on its own access point, and falls back
to the creation argument on any other network. **There was never a discovery problem to solve; the
Organelle already knew the answer.**

⛔ **Hardcoding a phone address is the mistake `phone-ip.sh` exists to prevent.** Discovered rather
than configured means **one build works everywhere and no conditional lives in the patch** — which
is the property worth protecting if this is ever changed.

### The display must show its own staleness

**A frozen display looks exactly like a working one**, and mid-performance you will read it and act
on it. The phone's script checks every frame how long it is since the last heartbeat; past 1500 ms
the display says `no link` rather than continuing to present a stale value as current.

⚠️ **The default label is `no link`, not `link`.** It must assume the worst until traffic proves
otherwise, or a layout opened before the Organelle is running looks connected when it is not.

The heartbeat keeps flowing even when nothing is happening, because it is the only thing
distinguishing *idle* from *dead*.

### The Organelle never waits for the phone

Fire and forget over `[netsend -u]`. Phone off, phone crashed, WiFi gone — **the instrument plays
identically.**

### The inbound vocabulary is closed, and the closure is the design

Six commands and two device names, every one of them a **literal argument on a `route` box you can
read**, with everything else falling out of an unconnected reject. That is the same allowlist guard
`u_map` uses for its destinations and it is here for the same reason: the set of things a datagram
can reach stays the set of boxes you can read. **`drums` is the one that passes on what follows it**:
`c_steps` holds that list and refuses the rest as `bad-selector`, so a new drum control needs nothing
here (Brendan, 2026-11-04).

⚠️ **Nothing here may be built on a sender identity that is not available** — `[netreceive]` in
0.49 cannot supply one (Reference, *Pure Data*), and a bidirectional link does not change that.
0.57's can, with `-f` (above).

⛔ **Nothing from the phone reaches the buses** (Brendan, 2026-11-04). A `send` command once carried
a checklist's Send line to `u_inject`, in test mode only, so the phone could run any checklist
alone; it went when the checklists split into two suites, since the line check, the one the phone
carries, sends nothing, and the development checklists' lines go from the Mac.

**Test mode puts the line check up.** It is flipped with a tap on the Launchpad's Setup button
(`lp-setup`) or at the Organelle itself (`aux` and the second key from the bottom, `og-shift-61`),
starts off at every load, goes off when a mode is chosen, and rides on the heartbeat so the phone
shows the Organelle's own state; a flip sends a heartbeat at once rather than waiting for the next.
Turning it on warns, so the OLED says so in compose and the log keeps it.

⛔ **A full status dump was considered and rejected as a command.** Parameters and status re-send
every two seconds and the alert repeats at 2 Hz, so a phone joining late repopulates on its own in
about two seconds — item 121. It would have been a button that does what waiting does.

**What this is not** is a rule about what the phone may ever do. Brendan's call, 2026-08-11: it may
well drive something musical one day. The two properties recorded above — how unevenly the link
delivers, and that the instrument plays identically without it — are what such a thing would have to
answer to, not a veto.

### `test-note` is the one command that answers *is it dead*

Everything else the instrument knows about a device is **last-heard** — the `diag` roster, the
`device-lost` warning, the whole presence bus. All of it answers *has it stopped talking to me*,
which is a different question, and for the Volca it cannot be asked at all: it transmits nothing, so
there is no evidence of its presence for any amount of code to find.

⚠️ **Prove the probe before believing the silence.** Hearing the device is the other half, and it is
the half only a person standing in the room can supply.

### The lamp flashes on the answer, not on the finger

Every accepted command echoes `/cutit/ack <command>`, and that is what lights the lamp beside the
button. A button that lights when pressed tells you the one thing never in doubt.

**Two of the three prove themselves anyway** — the alert row empties, the note sounds. `re-wire` has
nothing whatever to show for itself, and it is the reason the ack exists at all.

### What `re-wire` is actually for, now that the heartbeat exists

⚠️ **It is not "the only way back once the bound is spent".** The re-wire heartbeat hashes the ALSA
client names every ~16 s and is **unbounded** — see [presence.md](../module/presence.md) — so a
device that is unplugged and plugged back in is recovered on its own whether the eight scheduled
attempts are spent or not. Item 310.

What the button covers is the case the heartbeat cannot see: **the client names are unchanged and the
subscriptions are still wrong.** That is mother's own autoconnect landing a late device on the
Launchpad's channel block, a bystander whose subscription dipped, or simply not wanting to wait out
the interval. ⚠️ **So a checklist step of the form "unplug it, spend the bound, press the button" cannot
attribute anything** — the heartbeat gets there first.

`presence-assert.sh` is what proves the button forks at all, in the one window where nothing is
scheduled.

### The name is the parameter, not the control

Knob 2 sends `grain`, not `knob2`. The display says what *changed* rather than which physical control
moved, so the same knob can mean different things in different modes without the display lying.

## Open

**Nothing.**
