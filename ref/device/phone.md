<!-- schema: module -->
# The phone — PdParty and the status link

**Files:** `Cut It/u_net.pd`, `Cut It/phone-ip.sh`, `tools/pdparty-scene/CutItRemote/` · **Gate:** `test/gate/phone-assert.sh` · **Bench:** `test/bench/phone-bench.pd`

## What it is

An iPhone running PdParty on the same network, used as **an unlimited plain-English display** — and,
more valuable, as the answer to the Organelle having no Pd console.

`u_net.pd` is the fourth display surface and the only file that talks to it. It consumes `disp` like
the `g_` arbiters but **owns no selector on it**, so adding it cost `g_oled`'s route nothing. It
coalesces per name at 20 Hz with a guaranteed trailing edge, holds the last alert as *state* and
repeats it, and rebuilds its own socket — which a phone leaving the network destroys outright.

**Status display, diagnostics and remote console — not performance control.** UDP over WiFi arrives
unevenly, visibly so in the heartbeat counter. Fine for a readout, unacceptable for note timing.

## Facts

### Addresses and ports

| Device | Address | Notes | Evidence | Item |
|--------|---------|-------|----------|------|
| Organelle | `organelle.local` | Listens on **9001**. The IPv4 address is DHCP-assigned and **not stable** — seen as both `.15` and `.18`. Use the name | verified | — |
| iPhone | `192.168.1.5` | OSC receive **8000**, WebDAV **9000** | verified | — |
| Mac | `192.168.1.16` | Dev machine | verified | — |

⚠️ **Those are HOUSE-NETWORK addresses. On the Organelle's own access point the whole subnet
changes** — the Organelle is `192.168.12.1` and hands the phone `192.168.12.109`.

**Nothing in the patch is configured with either** — `phone-ip.sh` resolves it at load. See
*The phone cannot announce itself* under **Design** for why, and what it costs to change.

| Port | Status | Evidence | Item |
|------|--------|----------|------|
| 9000 | **Do not use for OSC** — it is PdParty's WebDAV server (`GCDWebDAVServer`) | verified | — |
| 4001–4003 | **Do not use** — they belong to `mother` | verified | — |
| 8000 | PdParty's OSC receive | verified | — |
| 9001 | The Organelle's OSC receive | verified | — |

### The wire format

```
/cutit/param   <name> <value> <unit>              coalesced per NAME at 20 Hz
/cutit/status  <symbol>                           coalesced, one slot
/cutit/hb      <counter>                          every 500 ms
/cutit/alert   <count> <level> <source> <text>    every 500 ms, always present
```

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

### The network

| Fact | Evidence | Item |
|------|----------|------|
| The Organelle hosts the network itself — `start-ap.sh` reads `$USER_DIR/ap.txt` and calls `create_ap`, and **`Start AP` is already in System → WiFi Setup**. It is the vendor's own path, not a hostapd project | verified | — |
| The rig runs `organelle`, password in `/sdcard/ap.txt`; two clients joined and the phone display worked over it | verified | — |
| **The AP has no internet** — `create_ap` is called with `-n` and the Organelle has one radio, so it cannot be both AP and client | verified | — |
| Airplane mode then re-enabling WiFi is standard iOS behaviour — cellular stays off, WiFi works, the setting persists | verified | — |

**Why not USB.** iOS will not present itself as a USB MIDI device or network interface to a Linux
host — Apple's USB MIDI support is host-side only. Personal Hotspot over USB requires cellular, which
defeats airplane mode. `usbmuxd`/`iproxy` could tunnel TCP over Lightning but would mean installing
libimobiledevice on a 2015-vintage Arch ARM with a read-only rootfs. 📄

**An AP the Organelle hosts needs neither cellular nor anything else in the room**, which is what
makes airplane mode workable — and airplane mode suppresses notifications at the source, so Do Not
Disturb is not the answer to them.

### Scene structure and layout

| Property | Value | Evidence | Item |
|----------|-------|----------|------|
| A scene | A **folder containing `_main.pd`**. A bare `.pd` also works as a "patch scene", but without background image support | doc | — |
| Orientation | Inferred from the canvas aspect ratio — wider than tall gives landscape, and PdParty locks the device to match. There is no `info.json` key for it | doc | — |
| `info.json` keys | *author*, *description*, *name*, *category* — that is all | doc | — |
| iPhone 11 landscape | **896×414 points.** A canvas of **448×207** — exactly half — fills the screen edge to edge, everything rendering at 2× | verified | — |
| iOS 14+ | Requires Settings → Privacy → **Local Network** permission, and the entry only appears after the app first attempts an outbound local connection. Until granted, OSC fails silently | doc | — |

## Traps

Each is a claim and its fix. How any of them was found is in the git history.

### Two instruments will fight over one phone

⛔ With the Organelle running Cut It **and** `main-dev.pd` running on the Mac, both connect to the
same phone and the status row **flutters between two values**. The bus is innocent — a `[r disp]` tap
shows four messages and no repeats.

**`u_net` is the sole owner of the phone WITHIN an instrument; nothing arbitrates ACROSS machines**,
and the symptom looks nothing like contention.

**Fix:** none in the patch. **It will recur during off-device development with the device still
powered** — close one of them.

### A phone joining mid-session saw blanks

⛔ Parameters and status were sent only on change, so a scene opened later showed **empty rows until
something moved**. The alert never had this problem, and the OLED never had it either, because it
redraws held state every frame. **`u_net` was the only surface where a late viewer saw nothing.**

**Fix:** a 2 s repeat of the last parameter and status, on top of the event-driven sends — well below
the 124/s noise floor. Item 121.

### ⛔ `warn u_net net-link-down` is not a wifi fault, and it reads exactly like one

The alert names the *link*, the Organelle's only link is wireless, and
[wifi.md](../wifi.md) documents a real fault that drops it — so the obvious reading is that the
network has gone. It is almost always wrong. **`u_net`'s watchdog watches a SOCKET**, and the
socket dies the moment nothing is listening on the phone's port (item 114 below): PdParty closed,
backgrounded by the phone, or on the wrong scene. The wifi can be perfectly healthy — verifiable in
one line, because `ssh root@organelle.local` uses the same radio.

**It is also the most common line in the error log by a wide margin**, appearing in most sessions,
which is what makes it easy to read as a symptom of something worsening.

**Fix:** before suspecting the network, check that PdParty is open on the `CutItRemote` scene, then
`ping organelle.local` or `ssh` to it. A reachable device with `net-link-down` on screen is the
phone, not the wifi. ⚠️ **The real roam fault has a different signature** — the *whole device* goes
unreachable, `ssh` included — and it is on [wifi.md](../wifi.md) with a reproduction.

### A UDP `connect` to a port with nothing listening survives EXACTLY ONE datagram

⛔ **The measurement that changed the design** (item 114). Twenty datagrams at 5 Hz to a port with no
listener: the `connect` **succeeds**, the first datagram **goes out**, and then the socket dies —
`error: recv: Connection refused` — and everything after it is silently discarded.

**So a socket that reports connected proves nothing**, and a phone that leaves the network destroys
the link without the patch hearing about it.

**Fix:** rebuild the socket rather than trusting it. `u_net` reconnects on a timer.

### `[s #osc-out]` takes raw OSC bytes, and the obvious alternative sends nothing

⛔ A message with the address as selector — `[list prepend /cutit/fader]` → `[list trim]` — sends
**nothing at all, silently.**

**Fix:** use `[oscformat]`.

```
[r $0-fader-out]  →  [oscformat cutit fader]  →  [s #osc-out]
```

PdParty's own `tests/pdparty/Osc` scene is the reference; the message boxes in it that resemble the
wrong approach are labelled *"test that sending other message types doesn't crash pdparty"*.

### `[r #osc-in]` delivers the address as bare symbols, with no slashes

`/cutit/hb 210` arrives as `cutit hb 210`.

**Fix:** route as `[route cutit]` → `[route hb]`, never `[route /cutit/hb]`.

### PdParty only renders iemguis that have send/receive names

⛔ With `empty` or `-` they parse, instantiate, participate in the patch — and are **invisible**.
The symptom is a scene showing only comments. This is documented nowhere.

**Fix:** give every GUI object both names, `$0-` prefixed, exactly as PdParty's bundled
`tests/all_pd_guis.pd` does.

### `[print]` is transmitted as `/pdparty/print` OSC

⛔ Accidentally a free remote console, and accidentally a flood — a single `[print]` on a 2 Hz
message stream produced **138 packets** in the time it took to drag a fader once.

**Fix:** do not leave prints in a running scene.

### Non-GUI objects still occupy canvas space

A column of `[r]`, `[route]` and `[unpack]` objects down the left of the canvas produces a large
empty region on the phone and pushes the visible content downward. Long comments do the same thing
horizontally, and get clipped.

**Fix:** keep the main canvas GUI-only and put all plumbing in a `[pd guts]` subpatch — which is what
PdParty's own bundled scenes do.

### The notch eats the edge, and PdParty does not inset for it

⛔ In landscape the iPhone 11's speaker and camera cover roughly **44 points — 22 canvas units** off
one end of a full-width row. A scene laid out edge to edge loses whatever is under it, **silently,
and only in landscape.**

**Fix:** inset **one** side, not both — which edge the notch lands on depends on which way the phone
is turned, so pick an orientation and hold it. `CutItRemote` keeps content at `x = 4` and stops at
`x = 426`, leaving the 22 units on the right, worth 26 units of extra width over insetting
symmetrically. Leave the bottom clear too; 17 canvas units clears the home indicator.

### The WebDAV server is not running just because PdParty is

⚠️ With the app open and demonstrably listening — a `[netsend -u -b]` delivered 20 datagrams to port
8000 with no ICMP teardown, which is positive proof of a listener — **port 9000 refused the
connection outright.** It has to be switched on in the app, and it does not necessarily survive the
app being backgrounded. So the phone deploy path has a precondition.

**Fix:** `nc -z <phone> 9000` before assuming a scene was updated. The failure is at least loud —
`curl` exits 7.

⚠️ **`nc -z` on port 8000 proves nothing** — OSC is UDP and a bare `nc -z` tests TCP. Use a real
datagram and watch for the ICMP teardown instead.

### The unit field must be written on every param message

⛔ `disp` treats the unit as optional, and **`[list split 3]` on exactly three atoms never fires its
right outlet** — so a field written on some messages and not others keeps its old value.
`chop-size 43 %` followed by `grain 12` draws as `grain 12 %`.

**Fix:** `u_net` appends the dash *before* splitting, making the optional field mandatory by
construction. The unit is written on every message, as `-` when there is none.

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

⛔ `255.255.255.255` **works** — Linux permits it, PdParty accepts it, and 19–20 of 20 datagrams
arrive. **But wifi access points buffer broadcast frames and release them on beacon boundaries.**

| | Unicast | Broadcast |
|---|---|---|
| Arrival | Every 200 ms, as sent | Bursts of three or four |
| Worst gap | — | ⛔ **up to 819 ms** |
| Throughput | identical | identical |

**Throughput is identical and latency is not**, which is why a delivery test saw nothing wrong and a
person moving a knob saw it immediately. One 819 ms gap also eats most of the phone's **1500 ms**
`NO-LINK` margin.

### The address resolves at 1550 ms on the device and 2200 on the Mac

⚠️ **Anything armed earlier fires into an empty host.** The reconnect metro was armed at 1600 ms and
banged the address store **before resolution**, sending `connect` with an empty host and printing
`bad host?` on **every single boot** — harmless, and invisible to `tools/deploy.sh` because the syntax
check quits first.

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

### The name is the parameter, not the control

Knob 2 sends `grain`, not `knob2`. The display says what *changed* rather than which physical control
moved, so the same knob can mean different things in different modes without the display lying.

## Open

**Nothing.** Rate limiting, the `nbx` chrome and the Organelle-hosted access point are all done, and
the venue sequence runs with no laptop and no venue WiFi, with the phone in airplane mode.
