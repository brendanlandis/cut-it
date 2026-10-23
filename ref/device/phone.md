<!-- schema: module -->
# The phone — PdParty and the status link

**Files:** `Cut It/u_net.pd`, `Cut It/phone-ip.sh`, `tools/pdparty-scene/CutItRemote/` · **Gate:** `test/gate/phone-assert.sh` · **Bench:** `test/bench/phone-bench.pd`

## What it is

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
a held alert. Inbound it takes **a closed vocabulary of three diagnostic commands**, acknowledges
each one, and drops everything else in silence. ⚠️ **UDP over WiFi arrives unevenly**, visibly so in
the heartbeat counter and measured under *Broadcast* in Reference and below; that is the evidence anything
time-critical would have to answer to.

**The one decision this page turns on: the inbound vocabulary is closed, and the closure is the
feature.** An inbound socket is an attack surface on a shared network, and a set small enough to read
in one line is what makes the first one safe to reason about.

## Facts

What the app and phone do is in Reference. This is what is true of the link.

### Addresses and ports

| Device | Address | Notes | Evidence | Item |
|--------|---------|-------|----------|------|
| Organelle | `organelle.local` | Listens on **9001**. The IPv4 address is DHCP-assigned and **not stable**. Use the name | verified | — |
| iPhone | `192.168.1.5` | OSC receive **8000**, WebDAV **9000** | verified | — |
| Mac | `192.168.1.16` | Dev machine | verified | — |

⚠️ **Those are HOUSE-NETWORK addresses. On the Organelle's own access point the whole subnet
changes** — the Organelle is `192.168.12.1` and hands the phone `192.168.12.109`.

**Nothing in the patch is configured with either** — `phone-ip.sh` resolves it at load. See
*The phone cannot announce itself* under **Design** for why, and what it costs to change.

| Port | Status | Evidence | Item |
|------|--------|----------|------|
| 4001–4003 | **Do not use** — they belong to `mother` | verified | — |
| 9001 | The Organelle's OSC receive. `u_root` passes it to `u_net` as arg 3 | verified | — |
| 9002 | **The Mac's**, so `main-dev.pd` and a suite run cannot fight over one socket | verified | 307 |

PdParty's own ports (8000 OSC receive, 9000 WebDAV) and its OSC *send* settings, including that the
host must be a literal address, are in Reference (item 312).

⚠️ **Which makes the house network the awkward one, and the stage network the easy one.** The
Organelle's lease moves — seen as `.15`, `.18` and `.6` — so the phone has to be re-pointed whenever
it does. **On the Organelle's own access point it is always `192.168.12.1`**, so the configuration
that matters at a gig is the stable one. The instrument still discovers the *phone* by itself;
`phone-ip.sh` is unaffected, and this is the one direction that cannot be discovered — see *The phone
cannot announce itself* under **Design**.

### The wire format

```
Organelle -> phone
/cutit/param   <name> <value> <unit>              coalesced per NAME at 20 Hz
/cutit/status  <symbol>                           coalesced, one slot
/cutit/hb      <counter>                          every 500 ms
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
| Socket recovery | `u_net` rebuilds within about five seconds of the phone coming back, nothing touched on the instrument | verified | 119 |
| Backgrounding PdParty | Costs nothing — iOS keeps the app running and the UDP port bound. Only a full quit closes it | verified | — |

**One address for all parameters.** Adding a parameter costs one `[list prepend <name>]` on the
Organelle and nothing at all on the phone — this scales to the nanoKONTROL's 18 continuous controls
without redesign.

## Traps

Each is a claim and its fix. How any of them was found is in the git history. The app's and Pd's own
traps (a UDP `connect` that survives one datagram, `#osc-out`/`#osc-in`, invisible iemguis, `[print]`,
canvas space, the notch, WebDAV, `[route 404]`, the bng loop, the unit field) are in Reference.

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
socket dies the moment nothing is listening on the phone's port (item 114, in Reference): PdParty closed,
backgrounded by the phone, or on the wrong scene. The wifi can be perfectly healthy — verifiable in
one line, because `ssh root@organelle.local` uses the same radio.

**It is also the most common line in the error log by a wide margin**, appearing in most sessions,
which is what makes it easy to read as a symptom of something worsening.

**Fix:** before suspecting the network, check that PdParty is open on the `CutItRemote` scene, then
`ping organelle.local` or `ssh` to it. A reachable device with `net-link-down` on screen is the
phone, not the wifi. ⚠️ **The real roam fault has a different signature** — the *whole device* goes
unreachable, `ssh` included — and it is on [wifi.md](../wifi.md) with a reproduction.

### Rebuild the socket

A UDP `connect` to a port with nothing listening survives exactly one datagram (Pure Data, in
Reference), so a socket that reports connected proves nothing, and a phone that leaves the network
destroys the link without the patch hearing about it. `u_net` reconnects on a timer.

### The unit field is written on every param message

`disp` treats the unit as optional, and `[list split 3]` on exactly three atoms never fires its right
outlet (Pure Data, in Reference). **Fix:** `u_net` appends the dash *before* splitting, making the
optional field mandatory by construction. The unit is written on every message, as `-` when there is
none.

### `test-note` takes symbols

`[route 404]` matches a float and can never match the device name (Pure Data, in Reference, item
308). **Fix:** the devices are `m_volca` and `m_404`, which are symbols whatever else is true. That is
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

## Design

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

**Fix:** arm at **3000 ms**, past both platforms. `[metro]` fires the instant it is started, so
"armed at" means "fires at". On the Mac a `[del 700]` fallback covers a `[shell]` that never answers.

### The phone cannot announce itself, so the Organelle looks the address up

⚠️ **`[netreceive]` in 0.49 cannot tell you who sent a datagram.** Checked before designing around
it, and it is why the obvious answer — the phone announcing its own address — was not available.

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

Three commands and two device names, every one of them a **literal argument on a `route` box you can
read**, with everything else falling out of an unconnected reject. That is the same allowlist guard
`u_map` uses for its destinations and it is here for the same reason: the set of things a datagram
can reach stays the set of boxes you can read.

⚠️ **Nothing here may be built on a sender identity that is not available** — `[netreceive]` in
0.49 cannot supply one (Reference, *Pure Data*), and a bidirectional link does not change that.

⛔ **A fourth command was considered and rejected: a full status dump.** Parameters and status re-send
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
the interval. ⚠️ **So a bench step of the form "unplug it, spend the bound, press the button" cannot
attribute anything** — the heartbeat gets there first.

`presence-assert.sh` is what proves the button forks at all, in the one window where nothing is
scheduled.

### The name is the parameter, not the control

Knob 2 sends `grain`, not `knob2`. The display says what *changed* rather than which physical control
moved, so the same knob can mean different things in different modes without the display lying.

## Open

**Nothing.**
