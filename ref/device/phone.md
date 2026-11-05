<!-- schema: device -->
# The phone — TouchOSC and the link

**Files:** `Cut It/u_net.pd`, `Cut It/phone-ip.sh`, `tools/touchosc/build.py`, `tools/touchosc/push.sh` · **Gate:** `test/gate/phone-assert.sh`, `test/gate/touchosc-assert.sh` · **Checklist:** `test/checklists/phone.md`

An iPhone running TouchOSC on the same network (from 2026-11-04; PdParty until then). What TouchOSC
is and does — its file, how it draws, its scripts, its connections, the editor sync that deploys to
it — is in Reference: `~/Sites/!reference/touchosc.md`; what was measured with PdParty stays on
`~/Sites/!reference/pdparty.md`. This page is the link Cut It builds on them.

**The phone controls the Launchpad's current page, and the OLED is not copied to it** (Brendan,
2026-11-04). The OLED has the alerts and warnings, the levels and the name of a control as it
moves; the phone has a page for each of the Launchpad's eight, and shows the one the Launchpad is
on: page 1's global controls (the tempo, which lives on the phone alone, the time signature, the
global last step, the swing and the drunkenness), page 2's drum screen, page 3's synths screen, and
a blank page under its tab for each of the rest. Each page has tabs of its own, one each for now. It
was a mirror of `disp` until then, with a remote screen of diagnostic buttons, and both went with
the split: that reverses the decision on [display.md](../module/display.md) that the phone stays a
mirror, which was right for a readout and is not for a control surface.

`u_net.pd` is the only file that talks to it, and it reads nothing on `disp`. Outbound it carries
six addresses — a heartbeat, the mode, the sequencer's state, the synth choice, the velocity switch
and the tempo — each sent when it changes and again on every heartbeat, and it rebuilds its own
socket, which a phone leaving the network destroys outright. Inbound it takes **a closed
vocabulary of five commands** (one for the checklist page, one for the drum and arrangement
screens' controls, two for the synths screen, one for the tempo), acknowledges the ones a button
shows, and drops everything else in silence. ⚠️ **UDP over WiFi arrives unevenly**, visibly so in
the heartbeat counter and measured under *Broadcast* in Reference and below; that is the evidence
anything time-critical would have to answer to.

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
/cutit/hb        <counter> <test mode, 0 or 1>      every 500 ms
/cutit/mode      <page>                             on change and every 500 ms
/cutit/drums     <42 numbers>                       c_steps' state, on change and every 500 ms
/cutit/synth     <fm or strings>                    c_synth's choice, on change and every 500 ms
/cutit/velocity  <on or off>                        c_synth's velocity switch, the same
/cutit/tempo     <bpm>                              u_tempo's, coalesced at 20 Hz, and every 500 ms
/cutit/ack       <command> [<what>]                 once per command a button shows

phone -> Organelle
/cutit           <command> [<argument> ...]         port 9001, anything else dropped
```

Each of the state addresses is empty, no arguments, until its first value arrives, and the phone
leaves its screen as it was on one. `/cutit/param`, `/cutit/status` and `/cutit/alert` are gone
with the mirror (Brendan, 2026-11-04), and `phone-assert` requires that none of them ever leaves.

⚠️ **The command travels as ARGUMENTS of `/cutit`, not as address components.** `[oscparse]`
flattens `/cutit/drums` and `/cutit` carrying the string `drums` to the same list, so this is
simply the cheaper of the two to build — one `[oscformat cutit]` on the phone rather than one per
button.

### The inbound vocabulary

<!-- check: pd-route "Cut It/u_net.pd" result -->

| Command | Does | Evidence | Item |
|---------|------|----------|------|
| `result` | A step's verdict, `<checklist>-<n>-<pass or fail>`, logged as `info phone <verdict>`, in test mode or not; answered `ack result` | unknown | — |
| `drums` | A drum or arrangement screen control, passed on whole: whatever follows `drums` goes out `u_net`'s first outlet to `c_steps`, which refuses one it does not know as `fail c_steps bad-selector`, so a new control needs nothing in `u_net` (Brendan, 2026-11-04). `sync`, `snap` and `select` are answered `ack drums <action>`, the rest not, since the state shows them | verified | — |
| `synth` | The synth choice, passed on whole: whatever follows `synth` goes out `u_net`'s second outlet to `c_synth`, which refuses a synth it does not know as `fail c_synth bad-synth`, so a new synth needs nothing in `u_net` but its acknowledgment. `fm` and `strings` are answered `ack synth <choice>`; the phone lights the chosen button from `/cutit/synth`, not from the answer ([synths.md](../module/synths.md)) | unknown | — |
| `tempo` | The arrangement screen's tempo, `tempo <bpm>`, passed on whole out `u_net`'s third outlet to `u_tempo`, which puts it on the tempo bus, whole and within 5–600 BPM, and refuses anything but a number as `fail u_tempo bad-tempo` ([tempo.md](../module/tempo.md)). Not answered: the tempo coming back says it | unknown | — |
| `velocity` | The synths screen's velocity switch, passed on whole out `u_net`'s second outlet to `c_synth`, which refuses anything but the two below as `fail c_synth bad-velocity`; each of them is answered `ack velocity <setting>` | unknown | — |

`re-wire`, `clear-alert` and `test-note` went with the remote screen (Brendan, 2026-11-04), and
`phone-assert` sends each and requires it to reach nothing: no answer, no bus, no outlet. The
re-wire is still on the `presence` bus, from a Send line ([presence.md](../module/presence.md)).

What the drum and arrangement screens send after `drums`, each one `c_steps`' own (`R.presses` in
`c_steps.lua`). `touchosc-assert` checks the layout against that table, and `u_net`'s
acknowledgments against the layout.

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
| `set-swing` | The swing, `set-swing <25-75>`, as it stands: knob 4's own `swing` is a knob position that passes the knob's latch, so the phone has its own, and knob 4 is held again at the phone's value | unknown | — |
| `set-last` | The global last step, `set-last <1-32>`, the same way beside knob 2's `last` | unknown | — |

What the synths screen and the checklist page send after `synth`, `c_synth.lua`'s `R.SYNTHS`, each
acknowledged by `u_net`. `touchosc-assert` checks the layout and `u_net` against `c_synth`.

<!-- check: pd-route "Cut It/u_net.pd" fm -->

| Synth | Is | Evidence | Item |
|-------|----|----------|------|
| `fm` | The Volca FM ([volca.md](volca.md)) | unknown | — |
| `strings` | The Waldorf Streichfett ([streichfett.md](streichfett.md)) | unknown | — |

What the velocity switch sends after `velocity`, each acknowledged by `u_net`. `touchosc-assert`
checks the switch asks for exactly these.

<!-- check: pd-route "Cut It/u_net.pd" on -->

| Setting | Is | Evidence | Item |
|---------|----|----------|------|
| `on` | A key's velocity reaches the synth, as before the switch | unknown | — |
| `off` | Every note-on goes out at 127, on either synth; a release stays 0 (Brendan, 2026-11-04) | unknown | — |

| Property | Value | Evidence | Item |
|----------|-------|----------|------|
| `hb` | Sent **unconditionally at 2 Hz**, and at once on a flip of test mode | verified | — |
| The state | `mode`, `drums`, `synth`, `velocity` and `tempo` go again on every heartbeat **on top of** their sends on change | unknown | — |
| Late or returning phone | Repopulates within half a second with nothing moving | unknown | — |
| `tempo` | Coalesced into **one slot** at 20 Hz: `u_tempo` hands on every BPM the tempo bus carries, and one sweep of knob 1 is some 200 a second. `phone-assert` sweeps 401 and requires at most ~60 datagrams and the last BPM | unknown | — |
| Socket recovery | `u_net` rebuilds within about five seconds of the phone coming back, nothing touched on the instrument | verified | 119 |
| Backgrounding the phone's app | PdParty's cost the link nothing, only a full quit closed the port (Reference, item 120); TouchOSC's is untested | unknown | 120 |

### The pages: one TouchOSC layout

**Every page is one layout**, `tools/touchosc/CutIt.tosc`, **generated** by `tools/touchosc/build.py`:
edit that, never the file. Each control sends from a script of its own; the root's script takes
everything that comes in.

**The design is Brendan's** (2026-11-04, iterated from mockups): TouchOSC's own controls and its own
tab bar, never a stack of shapes standing in for one; black, with bright red (`#FF1F3F`) the lead
accent and teal the second; monospaced type for every value, TouchOSC's default font for every label;
and every text and control at **WCAG AA**, which `touchosc-assert` audits from the file.

| | | Evidence |
|---|---|---|
| The pages | An outer pager, one page per Launchpad page and the checklist page last, each holding a pager of its own whose tabs are that page's (Brendan, 2026-11-04: "Each page will potentially have more than one tab"); one tab each for now, named for the page: arrangement, drums, synths, page 4 … page 7, songs. The root's script turns the outer pager to the page `/cutit/mode` names, a mode off the eight to page 1, and hides its tab bar at `init`, so the phone shows the page's own tabs. The phone never turns the Launchpad's page | unknown |
| In the editor | The outer pager's tab bar is on in the file, and no control is hidden, so TouchOSC's editor, where no script runs, reaches every page by its tab ([tools/README.md](../../tools/README.md), *Working on the layout*). `touchosc-assert` holds both: before 2026-11-04 the drum and synths screens were groups a script showed, and Brendan could not open them to edit | unknown |
| Test mode | Coming on, the outer pager turns to the checklist page, under a tab bar of its own; going off turns it back to the Launchpad's page (Brendan, 2026-11-04). A mode chosen on the Launchpad turns it off, so the mode's page is what shows next. A flip sends a heartbeat at once, so the page turns with the tap rather than at the next of the 2 Hz beats | unknown |
| The grid | Every control on a page sits on TouchOSC's 20-point editor grid, so one moved in the editor snaps to where a build puts it (Brendan, 2026-11-04). ⛔ The editor anchors its grid at the document's center, not its corner, so on a page, under the editor's two tab bars, its lines run at x 8 and y 7 plus whole steps (`build.py`'s `OX` and `OY`, worked out from the screen's size). A page is a left panel 300 wide and a right panel of two 240-point columns, a step apart, from 28 to 848 across, clear of the notch, and 27 to 327 down. A control's name is a caption a step tall, grey, flush left just above it; values and button words are centered in their controls; a lamp and its words share the bottom row, the link's in the same place on every page. `touchosc-assert` holds the grid, the margins and the captions | verified |
| The arrangement screen, page 1 | Left: the tempo, large and red, a box dragged up and down a BPM at a time, 5 to 600, about 10 points a BPM (Brendan, 2026-11-04: "Tempo should live on phone only, and should be editable on the phone as well"); under it a tap button: the phone times the taps itself as the finger lands, since WiFi delivers unevenly, by `u_tempo.lua`'s own rules (read from it at build time), and sends the tempo they make as the box does; playing or stopped with its lamp; the link. Right: the time signature as [n] / [d], each box dragged a step at a time (Brendan, 2026-11-04), about 21 points a step for the top number's 32, 24 for the bottom's 5; the global last step, a box of 1 to 32 beside it; ring knobs for the swing, 25% to 75%, and the drunkenness. Knob 1, the tap pad and knobs 2 and 4 keep working, and the phone shows the value whichever set it | unknown |
| The drum screen, page 2 | What is per track (Brendan, 2026-11-04): the sixteen pads as the Launchpad lays them out, pad 1 at the bottom left, read from `cut-it-drum-page.txt`, each labeled with its last step: red following the global one, teal with a dot (• 5) with its own, lit when selected; a tap selects. ⛔ A pad the state lights never sends: when it did, four pads pressed at once on the Launchpad lit in turn on the phone, each selecting itself again, and the selection bounced between Cut It and the phone for as long as they were held (2026-11-04). Right: sync first steps and snap to global, a line while one waits for step 1, ring knobs for the selected track's skip and move, the link | unknown |
| The synths screen, page 3 | Two large buttons, FM and STRINGS, the chosen one lit, its label black on the lit fill; under them the velocity switch, lit when on (Brendan, 2026-11-04); the link. A tap sends `/cutit synth fm` or `strings`, or `/cutit velocity` with the setting the switch is not showing | unknown |
| A synth button, a pad or the switch | Lit by the state, through `notify('lit')`, never by its own value, and a lit one never sends what it shows: so the state coming back, and its repeat on every heartbeat, cannot send it again, and a tap on the chosen synth sends nothing. The switch acts on a finger's touch, asking for the other setting | unknown |
| Pages 4 to 7, page 8 | Blank under the tab named for the page: nothing is on them yet (Brendan, 2026-11-04) | unknown |
| The checklist page | The line check a step at a time, from `test/checklists/linecheck.md` ([the checklists' README](../../test/checklists/README.md), *The line check*): its position and title, its text, Pass and Fail, Back and Next; and FM and STRINGS beside its position, the synths screen's two buttons small, so the line check plays either synth without leaving test mode (Brendan, 2026-11-04) | unknown |
| An answer | `/cutit/ack` flashes its button teal for 300 ms, by its color, never its value, so it can't send the command again | unknown |
| A knob or a box | Sends when a finger moves it off the value it knows, its own or the one the state handed it, so the state is never sent back; for a second after a touch the state leaves it alone. A time signature box sends `num` or `den` once a step, as `c_steps` takes them; the tempo and last step boxes send the value as it stands. The tempo box is handed the tempo whole, so a tempo that is not, set from elsewhere, is shown as it is and never sent back rounded | unknown |
| `/cutit/drums` | `c_steps`' `R.phone`: playing, the global last step, the selected track, pending (0, 1 sync, 2 snap), the sixteen last steps, then 1 for each track with its own, then the time signature's two numbers, the drunkenness, the selected track's skip and move chances, and the swing. Sent by `c_steps` when it changes, through `u_root`'s cord into `u_net`'s second inlet. The drum screen shows what is per track, the arrangement screen the rest | unknown |
| A short or empty state | Fewer than 42 numbers draws nothing, so the empty repeat before the first state leaves the screen as it was | unknown |
| Deploying | `./tools/touchosc/push.sh` rebuilds the layout and opens it in the Mac's TouchOSC, restarting that with its editor server on if it is off; the phone, connected once as an editor client of the Mac, takes it live, and `push.sh` says when it has dropped off. While the screens are being built, `tools/touchosc/watch.py` pushes on every save and folds the editor's changes back ([tools/README.md](../../tools/README.md), *Working on the layout*) | verified |
| The phone's setup, once | Editor network: a client of the Mac (port 6666). OSC connection 1 as above | verified |

### The phone controls the page, and does not copy the OLED

**Brendan split the two on 2026-11-04**: the OLED for alerts and warnings, levels and the name of a
control as it moves; the phone for the Launchpad's current page. Until then `u_net` subscribed to
`disp` and forwarded every parameter row, the footer's status and the held alert, and the phone
drew a remote screen of them with three diagnostic buttons. All of it went: `u_net` holds no `[r
disp]`, and `phone-assert` puts a sweep, a row, an alert and a meter on `disp` and requires
nothing of them on the wire. What the phone shows now is each module's state, handed to `u_net` on a
cord, which is what a control surface needs and a mirror never had.

### The tempo lives on the phone

The arrangement screen's tempo is the only place the BPM is shown as a number and set by a drag
(Brendan, 2026-11-04). It is `u_tempo`'s, the clamped value whatever set it — knob 1, the tap pad,
the phone itself, a Send line — on a cord out of `u_tempo` into `u_net`'s fourth inlet, so the phone
shows the tempo in force, not one it asked for. The status string the footer carried, until the
footer went too, was the wrong vehicle: one slot shared with every other status, and a word.

The phone's drag goes to `u_tempo` by a cord, and `u_tempo` writes the bus, so nothing from the phone
reaches a bus by itself (*The inbound vocabulary is closed*, below).

### Two instruments will fight over one phone

⛔ With the Organelle running Cut It **and** `main-dev.pd` running on the Mac, both connect to the
same phone and its screens **flutter between two states**, the page turning back and forth with the
heartbeats.

**`u_net` is the sole owner of the phone WITHIN an instrument; nothing arbitrates ACROSS machines**,
and the symptom looks nothing like contention.

**Fix:** none in the patch. **It will recur during off-device development with the device still
powered** — close one of them.

### A phone joining mid-session saw blanks

⛔ Sent only on change, state leaves a screen opened later showing **nothing until something
moves**.

**Fix:** every state address goes again on every heartbeat, on top of its sends on change, so a
phone that joins or comes back late catches up within half a second. Item 121 measured the cost of
the first repeat, at 2 s, well below the 124/s noise floor.

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

### A lit button a finger let go of went deaf

⛔ A finger lifting off a lit button puts it out while the button's own lit flag stays set, so the
root, comparing the button's value alone with what the state wanted, never told it again when the
state put it out: the next tap on it sent nothing, or for the velocity switch the wrong setting.

**Fix:** the root keeps what it last told each pad, synth button and the switch, and tells it again
when that differs or the value does. `touchosc-assert` taps the lit switch, puts it out from the
state and requires the next tap to ask for on.

### The inbound port is armed late, and the Mac has its own

A second bind of the same UDP port prints a real line on stdout (Pure Data, in Reference, item 307),
and **stdout is the oracle** both `tools/deploy.sh` and the suite's silence gate use, so a patch that
bound at `loadbang` would turn every run red whenever a copy was already open in Pd.

**Fix:** two things, each independently sufficient for its own case. The `listen` is armed at
**2000 ms**, past the ~735 ms at which the deploy check quits, so neither it nor the syntax gate ever
binds at all. And `main-dev.pd` takes **9002** where `main.pd` takes 9001, so a long-running gate
cannot collide with the dev patch. ⚠️ **The phone's controls therefore drive the device, not the
Mac** — point the phone's TouchOSC at 9002 if you want them to reach `main-dev.pd`.

### An AP session cannot be driven interactively

⚠️ A laptop joined to the Organelle's own access point is offline, so nothing Mac-side can reach the
phone or the device during a stage session.

**Fix:** stage everything beforehand — the checklist is on [wifi.md](../wifi.md).

### Send state, never events

Every message out carries the complete current value — the tempo is 133, never one more. A dropped
packet then **self-corrects on the next send** instead of leaving the display permanently and
silently wrong. UDP will drop packets; the protocol has to not care. The phone sends the tempo, the
last step and the swing as they stand for the same reason; the time signature's boxes send steps,
`c_steps`' own `num` and `den`, and the state that comes back corrects a lost one.

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
every screen with a link lamp says `no link` rather than continuing to present a stale value as
current.

⚠️ **The default label is `no link`, not `link`.** It must assume the worst until traffic proves
otherwise, or a layout opened before the Organelle is running looks connected when it is not.

The heartbeat keeps flowing even when nothing is happening, because it is the only thing
distinguishing *idle* from *dead*.

### The Organelle never waits for the phone

Fire and forget over `[netsend -u]`. Phone off, phone crashed, WiFi gone — **the instrument plays
identically.**

### The inbound vocabulary is closed, and the closure is the design

Five commands, every one of them a **literal argument on a `route` box you can read**, with
everything else falling out of an unconnected reject. That is the same allowlist guard `u_map` uses
for its destinations and it is here for the same reason: the set of things a datagram can reach
stays the set of boxes you can read. **`drums`, `synth`, `tempo` and `velocity` pass on what
follows them**: `c_steps`, `c_synth` and `u_tempo` hold those lists and refuse the rest, as
`bad-selector`, `bad-synth`, `bad-tempo` and `bad-velocity`, so a new drum control or synth needs
nothing here but an acknowledgment (Brendan, 2026-11-04).

⚠️ **Nothing here may be built on a sender identity that is not available** — `[netreceive]` in
0.49 cannot supply one (Reference, *Pure Data*), and a bidirectional link does not change that.
0.57's can, with `-f` (above).

⛔ **Nothing from the phone reaches the buses by itself** (Brendan, 2026-11-04). A `send` command
once carried a checklist's Send line to `u_inject`, in test mode only, so the phone could run any
checklist alone; it went when the checklists split into two suites, since the line check, the one
the phone carries, sends nothing, and the development checklists' lines go from the Mac. The tempo
the phone sets goes to `u_tempo` by a cord, and `u_tempo`, which owns the tempo, writes it.

**Test mode puts the line check up.** It is flipped with a tap on the Launchpad's Setup button
(`lp-setup`) or at the Organelle itself (`aux` and the second key from the bottom, `og-shift-61`),
starts off at every load, goes off when a mode is chosen, and rides on the heartbeat so the phone
shows the Organelle's own state; a flip sends a heartbeat at once rather than waiting for the next.
Turning it on warns, so the OLED says so and the log keeps it.

⛔ **A full status dump was considered and rejected as a command.** Every state address repeats on
the heartbeat, so a phone joining late repopulates on its own within half a second — item 121. It
would have been a button that does what waiting does.

**The phone drives something musical now**: the tempo, the time signature, the swing and the
sequencer's settings. Brendan's call of 2026-08-11, that it might one day, came with the two
properties recorded above — how unevenly the link delivers, and that the instrument plays
identically without it — and those are what each control answers to: every one sends a value the
state corrects, and none is needed to play.

## Open

- ⬜ **The pages have not been seen in TouchOSC.** That the root's script hides the outer pager's
  tab bar on the phone, where the pages then sit, how a 9-point-a-BPM drag feels, and that the
  velocity switch's touch reaches its script, are judged by `test/checklists/phone.md` on the
  phone, and the editor's tabs by opening the layout on the Mac. `cut-it/pages-and-displays`.
