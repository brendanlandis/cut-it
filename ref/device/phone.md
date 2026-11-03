<!-- schema: device -->
# The phone — PdParty and the status link

**Files:** `Cut It/u_net.pd`, `Cut It/phone-ip.sh`, `tools/pdparty-scene/CutItRemote/` · **Gate:** `test/gate/phone-assert.sh` · **Checklist:** `test/checklists/phone.md`

An iPhone running PdParty on the same network, used as **an unlimited plain-English display** — and,
more valuable, as the answer to the Organelle having no Pd console. What PdParty and the phone are —
ports, scene structure, rendering quirks, the OSC bridge, network behavior — is in Reference:
`~/Sites/!reference/pdparty.md` (and the Pd objects it exercises in `~/Sites/!reference/pure-data.md`).
This page is the status link Cut It builds on them.

`u_net.pd` is the fourth display surface and the only file that talks to it. It consumes `disp` like
the `g_` arbiters but **owns no selector on it**, so adding it cost `g_oled`'s route nothing. It
coalesces per name at 20 Hz with a guaranteed trailing edge, holds the last alert as *state* and
repeats it, and rebuilds its own socket — which a phone leaving the network destroys outright.

**The link runs both ways.** Outbound it carries four addresses — parameters, status, a heartbeat and
a held alert. Inbound it takes **a closed vocabulary of five commands** (three diagnostic, two for the
checklist page), acknowledges each one, and drops everything else in silence. ⚠️ **UDP over WiFi arrives unevenly**, visibly so in
the heartbeat counter and measured under *Broadcast* in Reference and below; that is the evidence anything
time-critical would have to answer to.

**The one decision this page turns on: the inbound vocabulary is closed, and the closure is the
feature.** An inbound socket is an attack surface on a shared network, and a set small enough to read
in one line is what makes the first one safe to reason about.

## Design

### Addresses and ports

| Device | Address | Notes | Evidence | Item |
|--------|---------|-------|----------|------|
| Organelle | `192.168.1.15` | Listens on **9001**. Reserved for it on the house router, and its own access point takes the same address (`device/start-ap.sh`), so PdParty's send host is set once | verified | — |
| iPhone | `192.168.1.5` | `u_net` sends to PdParty's OSC receive, **8000** | verified | — |
| Mac | `192.168.1.16` | Dev machine | verified | — |

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

PdParty's own ports (8000 OSC receive, 9000 WebDAV) and its OSC *send* settings, including that the
host must be a literal address, are in Reference (item 312).

**So PdParty's send host is `192.168.1.15` everywhere**, set once. PdParty cannot send to the
broadcast address or resolve a name (Reference), so a fixed address is the only way to stop
re-pointing it; on the house network that took the router's reservation (Brendan, 2026-11-03). The
instrument still discovers the *phone* by itself, with `phone-ip.sh`, and this is the one direction
that cannot be discovered — see *The phone cannot announce itself* under **Design**.

### The wire format

```
Organelle -> phone
/cutit/param   <name> <value> <unit>              coalesced per NAME at 20 Hz
/cutit/status  <symbol>                           coalesced, one slot
/cutit/hb      <counter> <test mode, 0 or 1>      every 500 ms
/cutit/alert   <count> <level> <source> <text>    every 500 ms, always present
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
| `send` | A checklist's Send line, one message, `<bus> <message>`, from the phone's checklist page: out a cord to `u_inject` **in test mode only**, answered `ack send`, or `ack test-off` while it is off | unknown | — |
| `result` | A step's verdict, `<checklist>-<n>-<pass or fail>`, logged as `info phone <verdict>`, in test mode or not; answered `ack result` | unknown | — |

<!-- check: pd-route "Cut It/u_net.pd" m_volca -->

| Device | Probe | Evidence | Item |
|--------|-------|----------|------|
| `m_volca` | `notes 60 100 200` — middle C, 200 ms, released by `makenote` | verified | 306 |
| `m_404` | `pad 1 100` — bank A pad 1 | verified | 306 |

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
| Backgrounding PdParty | Costs the link nothing; only a full quit closes the port (Reference, item 120) | verified | 120 |

**One address for all parameters.** Adding a parameter costs one `[list prepend <name>]` on the
Organelle and nothing at all on the phone — this scales to the nanoKONTROL's 18 continuous controls
without redesign.

### Two instruments will fight over one phone

⛔ With the Organelle running Cut It **and** `main-dev.pd` running on the Mac, both connect to the
same phone and the status row **flutters between two values**. The bus is innocent — a `[r disp]` tap
shows four messages and no repeats.

**`u_net` is the sole owner of the phone WITHIN an instrument; nothing arbitrates ACROSS machines**,
and the symptom looks nothing like contention.

**Fix:** none in the patch. **It will recur during off-device development with the device still
powered** — close one of them.

### A phone joining mid-session saw blanks

⛔ Sent only on change, parameters and status leave a scene opened later showing **empty rows until
something moves**. The alert never has this problem, and the OLED never has it either, because it
redraws held state every frame. **`u_net` is the one surface where a late viewer could see nothing.**

**Fix:** a 2 s repeat of the last parameter and status, on top of the event-driven sends — well below
the 124/s noise floor. Item 121.

### ⛔ `warn u_net net-link-down` is not a wifi fault, and it reads exactly like one

The alert names the *link*, the Organelle's only link is wireless, and
[wifi.md](../wifi.md) documents a real fault that drops it — so the obvious reading is that the
network has gone. It is almost always wrong. **`u_net`'s watchdog watches a SOCKET**, and the
socket dies the moment nothing is listening on the phone's port (item 114, in Reference): PdParty
quit, or the phone off or off the network. Backgrounding the app or leaving the scene does not do it:
PdParty keeps the port bound while it runs at all (item 120, in Reference). The wifi can be perfectly
healthy — verifiable in one line, because `ssh root@organelle.local` uses the same radio.

**It is also the most common line in the error log by a wide margin**, appearing in most sessions,
which is what makes it easy to read as a symptom of something worsening.

**Fix:** before suspecting the network, check that PdParty is running on the phone, then
`ping organelle.local` or `ssh` to it. A reachable device with `net-link-down` on screen is the
phone, not the wifi. ⚠️ **The real roam fault has a different signature** — the *whole device* goes
unreachable, `ssh` included — and it is on [wifi.md](../wifi.md) with a reproduction.

⚠️ **All of this is 0.49's.** Under Pd 0.57 the socket survives an ICMP refusal, measured on the Mac
(2026-11-03; Pure Data, in Reference), so if the device's 0.57 does the same, `net-link-down` no
longer fires, and closing PdParty can't reach it. Untested on the device.

### Rebuild the socket

A UDP `connect` to a port with nothing listening survives exactly one datagram (Pure Data, in
Reference), so a socket that reports connected proves nothing, and a phone that leaves the network
destroys the link without the patch hearing about it. `u_net` reconnects on a timer. ⚠️ That is
0.49's behavior: 0.57 on the Mac keeps the socket and delivers again once something listens (Pure
Data, in Reference); untested on the device.

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

### The button and its lamp are two objects

A `bng` re-sends when it receives (Pure Data, in Reference, item 309), so a button lit by its own ack
would loop. The button sends on `-press` and receives on `-nc`, which nothing ever writes; the lamp
receives on `-ack` and sends to `-lamp`, which nothing reads. Both carry both names because PdParty
renders neither without them. `phone-assert.sh` asserts that no `bng` in the scene both transmits and
is lit.

### The inbound port is armed late, and the Mac has its own

A second bind of the same UDP port prints a real line on stdout (Pure Data, in Reference, item 307),
and **stdout is the oracle** both `tools/deploy.sh` and the suite's silence gate use, so a patch that
bound at `loadbang` would turn every run red whenever a copy was already open in Pd.

**Fix:** two things, each independently sufficient for its own case. The `listen` is armed at
**2000 ms**, past the ~735 ms at which the deploy check quits, so neither it nor the syntax gate ever
binds at all. And `main-dev.pd` takes **9002** where `main.pd` takes 9001, so a long-running gate
cannot collide with the dev patch. ⚠️ **The phone's buttons therefore drive the device, not the Mac**
— point PdParty at 9002 if you want them to reach `main-dev.pd`.

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
and latency is not, and one 819 ms gap eats most of the phone's **1500 ms** `NO-LINK` margin.

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
on it. The phone restarts a 1500 ms timer on every incoming message; if it ever fires, the display
says `NO-LINK` rather than continuing to present a stale value as current.

⚠️ **The default label is `NO-LINK`, not `ok`.** It must assume the worst until traffic proves
otherwise, or a scene opened before the Organelle is running looks connected when it is not.

The heartbeat keeps flowing even when nothing is happening, because it is the only thing
distinguishing *idle* from *dead*.

### The Organelle never waits for the phone

Fire and forget over `[netsend -u]`. Phone off, phone crashed, WiFi gone — **the instrument plays
identically.**

### The inbound vocabulary is closed, and the closure is the design

Five commands and two device names, every one of them a **literal argument on a `route` box you can
read**, with everything else falling out of an unconnected reject. That is the same allowlist guard
`u_map` uses for its destinations and it is here for the same reason: the set of things a datagram
can reach stays the set of boxes you can read.

⚠️ **Nothing here may be built on a sender identity that is not available** — `[netreceive]` in
0.49 cannot supply one (Reference, *Pure Data*), and a bidirectional link does not change that.
0.57's can, with `-f` (above).

⛔ **`send` is the one that reaches further, so it has a switch of its own** (Brendan, 2026-11-03).
It carries a checklist's Send line to `u_inject`'s eight buses (`test/checklists/README.md`), so the
phone can run a rig checklist alone. `u_net` passes it only in **test mode**, which is flipped at the
Organelle itself (`aux` and the second key from the bottom, `og-shift-61`), starts off at every load,
and rides on the heartbeat so the phone shows the Organelle's own state. Turning it on warns, so
the OLED says so in compose and the log keeps it.

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
