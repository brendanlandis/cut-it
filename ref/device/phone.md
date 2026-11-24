<!-- schema: device -->
# The phone — the Cut It app and the link

**Files:** `Cut It/u_net.pd`, `Cut It/phone-ip.sh`, `phone/CutIt/Link.swift`, `phone/CutIt/Cut.swift`, `phone/CutIt/LineCheck.swift`, `phone/state-at.py` · **Gate:** `test/gate/phone-assert.sh`, `test/gate/app-assert.sh` · **Checklist:** `test/checklists/phone.md`

An iPhone running the Cut It app, `phone/` in this repo, on the same network (from 2026-11-19;
TouchOSC from 2026-11-04, and PdParty before it). What was measured with those two stays on their
Reference pages, `~/Sites/!reference/touchosc.md` and `~/Sites/!reference/pdparty.md`; the app's
design is on its card (`cut-it/cut-it-app`). This page is the link Cut It builds on it.

**The phone controls the Launchpad's current page, and the OLED is not copied to it** (Brendan,
2026-11-04). The OLED has the alerts and warnings, the levels and the name of a control as it
moves; the phone shows the page `u_voices` names on `/cutit/voices`: `perform`, the controls in
play; `drums`, the drum screen; `harmony`, `melody`, `keys` and `sound`, a voice's pages; `songs`,
the songs and the sections, where the tempo, the last step, the time signature, the swing and the
drunkenness are set; and `diag`, which Setup opens. The Launchpad's two columns run down either
side of it, and a press on either moves both (`cut-it/cut-it-app`). It was a mirror of `disp`
until 2026-11-04, with a remote screen of diagnostic buttons, and both went with the split: that
reverses the decision on [display.md](../module/display.md) that the phone stays a mirror, which
was right for a readout and is not for a control surface.

`u_net.pd` is the only file that talks to it, and it reads nothing on `disp`. Outbound it carries
a heartbeat and each module's state — the sequencer's, the synth choice, the velocity switch, the
tempo, the song's lists, the generator's and its notes, the voices and the page, the controls in
play and the sounds — each sent when it changes and again on every heartbeat, and the chord
loop's place on each step (*The wire format*, below); and it rebuilds its
own socket, which a phone leaving the network destroys
outright. Inbound it takes **a closed vocabulary of commands**, each a literal on one `route`
box (*The inbound vocabulary*, below), and drops everything else in silence. ⚠️ **UDP over WiFi arrives unevenly**, visibly so in
the heartbeat counter and measured under *Broadcast* in Reference and below; that is the evidence
anything time-critical would have to answer to.

**The one decision this page turns on: the inbound vocabulary is closed, and the closure is the
feature.** An inbound socket is an attack surface on a shared network, and a set small enough to read
in one line is what makes the first one safe to reason about.

## Design

### Addresses and ports

| Device | Address | Notes | Evidence | Item |
|--------|---------|-------|----------|------|
| Organelle | `192.168.1.15` | Listens on **9001**. The S2 (from 2026-11-19) sets it itself on the house network, the router reserves it, and its own access point takes the same address (`device/s2/README.md`), so the phone's send host is set once | verified | — |
| iPhone | `192.168.1.9` | `u_net` sends to the Cut It app's OSC receive, **8001**. Reserved for it on the house router (Brendan, 2026-11-03); `192.168.1.5` until then, which turned out to be the printer | unknown | — |
| Mac | `192.168.1.6` | Dev machine, by DHCP and not reserved (seen 2026-11-03; `192.168.1.16` earlier) | verified | — |

**The Organelle is `192.168.1.15` on both networks**: on the house network the S2 sets it in its
saved `hildegard` connection and the router reserves it, and its own access point uses it too (from
2026-11-03 on the Organelle 1, whose factory AP was `192.168.12.1`; on the S2 from 2026-11-19). The phone's address is
the house network's at home and whatever the access point leases it at a gig.

**Nothing in the patch is configured with either** — `phone-ip.sh` resolves it at load. See
*The phone cannot announce itself* under **Design** for why, and what it costs to change.

| Port | Status | Evidence | Item |
|------|--------|----------|------|
| 4001–4003 | **Do not use** — mother's (Reference, `~/Sites/!reference/critter-guitari-organelle-1.md`, *Ports*) | verified | — |
| 8001 | The Cut It app's OSC receive, on the phone. `u_root` passes it to `u_net` as arg 2 | verified | — |
| 9001 | The Organelle's OSC receive. `u_root` passes it to `u_net` as arg 3 | verified | — |
| 9002 | **The Mac's**, so `main-dev.pd` and a suite run cannot fight over one socket | verified | 307 |

The app's two ends are fixed in `phone/CutIt/Link.swift`: it sends to `192.168.1.15`, port 9001,
and listens on 8001; `-host <address>` at launch points it elsewhere, as the tests do. ⛔ **A wrong
send host fails silently while receiving still works**: the phone shows everything, so the link
looks fine, and nothing it sends arrives (seen with TouchOSC, 2026-11-04).

**So the phone's send host is `192.168.1.15` everywhere**, set once. PdParty could not send to the
broadcast address or resolve a name (Reference, item 312), so a fixed address was the only way to
stop re-pointing it, and the app is set the same way; on the house network that took the router's
reservation (Brendan, 2026-11-03). The
instrument still discovers the *phone* by itself, with `phone-ip.sh`, and this is the one direction
that cannot be discovered — see *The phone cannot announce itself* under **Design**.

### The wire format

```
Organelle -> phone
/cutit/hb        <counter> <test mode, 0 or 1>      every 500 ms
/cutit/drums     <148 numbers>                      c_steps' state, on change and every 500 ms
/cutit/synth     <fm or strings>                    c_synth's choice, on change and every 500 ms
/cutit/velocity  <on or off>                        c_synth's velocity switch, the same
/cutit/tempo     <bpm>                              u_tempo's, coalesced at 20 Hz, and every 500 ms
/cutit/lists     <R.lists' atoms>                   u_song's setlists, songs and sections, on change and every 500 ms
/cutit/melody    <R.phone's atoms>                  c_melody's state, the same
/cutit/notes     <R.phone_notes' atoms>             c_melody's notes, the same
/cutit/voices    <page> <kind> <row> <24 atoms>     u_voices' page and voices, the same
/cutit/perform   <113 atoms>                        u_perform's controls in play, the same
/cutit/sound     <R.phone's atoms>                  u_sound's sounds, the same
/cutit/here      <step> <melody step>               the chord loop's place and the melody's, -1 stopped, each step of 40 ms or more
/cutit/once      <seq>                              the answer to a press (A press, once)
/cutit/ack       result                             the answer to a line check's verdict

phone -> Organelle
/cutit           <command> [<argument> ...]         port 9001, anything else dropped
```

Each of the state addresses is empty, no arguments, until its first value arrives, and the phone
leaves its screen as it was on one. `/cutit/param`, `/cutit/status` and `/cutit/alert` are gone
with the mirror (Brendan, 2026-11-04), and `/cutit/mode`, `/cutit/sections` and `/cutit/songs`
with the TouchOSC layout, whose pages they drew: the app takes the page from `/cutit/voices` and
the songs and sections from `/cutit/lists`. `phone-assert` requires that none of the six ever
leaves.

| Address | Carries | Evidence |
|---|---|---|
| `/cutit/drums` | `c_steps`' `R.phone`: playing, the global last step, the selected track, pending (0, 1 sync, 2 snap), the sixteen last steps, then 1 for each track with its own, then the time signature's two numbers, the drunkenness and the swing, then the sixteen volumes, pitches and randomnesses, then the selected track's effects, drive, tone, mix, note, feel, feedback, level, send and character, and the reverb's size and damping, then each track's mute and each track's solo, then the reverb's type, 0 to 2, then each track's random pitch, 1 or 0: 148 numbers. Sent by `c_steps` when it changes, through `u_root`'s cord into `u_net`'s second inlet. | unknown |
| `/cutit/melody` | `c_melody.lua`'s `R.phone`: the chords' controls, the slot sounding, whether each part is on, the key and mode, the grid's length and the pattern's last step, each of the eight slots' name, spelling, numeral and start, the two voices, then the melody's controls, modal or functional and bass only. | unknown |

⚠️ **The command travels as ARGUMENTS of `/cutit`, not as address components.** `[oscparse]`
flattens `/cutit/drums` and `/cutit` carrying the string `drums` to the same list, so this is
simply the cheaper of the two to build — one `[oscformat cutit]` on the phone rather than one per
button.

### A press, once

**OSC here is UDP, and a press lost on stage is a press that didn't happen.** The app sends a one-time press as `once <seq> <words...>` to `/cutit`, again every 120 ms, up to eight more times, until it hears `/cutit/once <seq>` back. `u_once` answers every copy and lets through only the first, so a press whose answer was lost isn't doubled. A knob or a drag isn't sent this way: the next value follows. (`Cut It/u_once.pd`, `u_once.lua`.)

### The inbound vocabulary

<!-- check: pd-route "Cut It/u_net.pd" result -->

| Command | Does | Evidence | Item |
|---------|------|----------|------|
| `result` | A step's verdict, `<checklist>-<n>-<pass or fail>`, logged as `info phone <verdict>`, in test mode or not; answered `ack result`. The app's line check sends it, as a press, from Pass and Fail (*Test mode*, below) | unknown | — |
| `drums` | A drum or arrangement screen control, passed on whole: whatever follows `drums` goes out `u_net`'s first outlet to `c_steps`, which refuses one it does not know as `fail c_steps bad-selector`, so a new control needs nothing in `u_net` (Brendan, 2026-11-04). Not answered: the state shows them | verified | — |
| `synth` | The synth choice, passed on whole: whatever follows `synth` goes out `u_net`'s second outlet to `c_synth`, which refuses a synth it does not know as `fail c_synth bad-synth`, so a new synth needs nothing in `u_net`. Not answered: the choice comes back as `/cutit/synth` ([synths.md](../module/synths.md)) | unknown | — |
| `tempo` | The arrangement screen's tempo, `tempo <bpm>`, passed on whole out `u_net`'s third outlet to `u_tempo`, which puts it on the tempo bus, whole and within 5–1000 BPM, and refuses anything but a number as `fail u_tempo bad-tempo` ([tempo.md](../module/tempo.md)). Not answered: the tempo coming back says it | unknown | — |
| `velocity` | The keyboard tab's velocity switch, passed on whole out `u_net`'s second outlet to `c_synth`, which refuses anything but the two below as `fail c_synth bad-velocity`. Not answered: the switch comes back as `/cutit/velocity` | unknown | — |
| `sections` | The app's sections, passed on whole out `u_net`'s fourth outlet to `u_song`, which refuses one it does not know as `fail u_song bad-selector` ([songs.md](../module/songs.md)). Not answered: the lists show them | unknown | — |
| `songs` | The app's songs and setlists, passed on out the same fourth outlet with `songs` kept in front, so `u_song` tells them from the sections', and refuses one it does not know as `fail u_song bad-selector`. Not answered: the lists show them | unknown | — |
| `melody` | The harmony, rhythm and melody tabs, passed on whole out `u_net`'s fifth outlet to `c_melody`, which refuses one it does not know as `fail c_melody bad-selector`: `set <control> <value>`, `audition <slot> <1 or 0>`, `move <slot> <start>`, `chord-pin <slot>` from a chord's box held 700 ms, and `roll-chords`, `roll-melody`, `roll-rhythm`, `on-h`, `on-m`, `style` and `bass`, each with a 1 ([synths.md](../module/synths.md), *The generator*). Not answered: the state shows them | unknown | — |
| `voices` | The app's rails and voice page, passed on out `u_net`'s sixth outlet to `u_voices` ([voices.md](../module/voices.md)) | unknown | — |
| `perform` | The app's performance page, passed on out `u_net`'s seventh outlet to `u_perform` ([voices.md](../module/voices.md)) | unknown | — |
| `sound` | The app's voice setup page, passed on out `u_net`'s eighth outlet to `u_sound` ([voices.md](../module/voices.md)) | unknown | — |

What the app sends of these, every word in a command's place, `app-assert` reads from its Swift and
checks against `u_net`'s routes and the tables behind them, so a misspelling fails in the gates
rather than on the rig as `bad-selector` ([test/README.md](../../test/README.md)).

`re-wire`, `clear-alert` and `test-note` went with the remote screen (Brendan, 2026-11-04), and
`phone-assert` sends each and requires it to reach nothing: no answer, no bus, no outlet. The
re-wire is still on the `presence` bus, from a Send line ([presence.md](../module/presence.md)).

What `drums` carries, each one `c_steps`' own (`R.presses` in `c_steps.lua`). The app doesn't
send `den`: the bottom number changes nothing, so the app has no control for it (Brendan,
2026-11-19).

| Drum action | Does | Evidence | Item |
|-------------|------|----------|------|
| `sync` | "sync first steps": every track back to its step 1 together when the global loop next comes round to its own, each keeping its own last step ([sequencer.md](../module/sequencer.md)) | verified | — |
| `snap` | "snap to global": the same, and at that step every track takes the global last step | verified | — |
| `select` | A pad on the drum screen, `select <n>`: selects track *n* without playing it | verified | — |
| `num` | The time signature's top number, `num <-1 or 1>`: one down or up, 1 to 32 | verified | — |
| `den` | Its bottom number, `den <-1 or 1>`: one down or up through 1 2 4 8 16, kept for the record and changing nothing else ([sequencer.md](../module/sequencer.md)) | verified | — |
| `drunk` | Drunkenness, `drunk <0-100>`: how often a step strays and how far, at the top every step, by up to two steps ([sequencer.md](../module/sequencer.md)) | verified | — |
| `vol` | A pad dragged while the pads show volume, `vol <track> <dB>`: that track's volume as it stands, −30 to +6 | verified | — |
| `pitch` | The same for pitch, `pitch <track> <semitones>`, −12 to +12 | verified | — |
| `set-track-last` | The same for the last step, `set-track-last <track> <1-32>`: that track's own, as knob 3 sets the selected track's | verified | — |
| `randomness` | The same for randomness, `randomness <track> <0-100>`, in fives from the phone | verified | — |
| `drive` | The selected track's distortion, `drive <track> <0-100>`, from its knob; and `tone` and `dist`, its mix, the same way (Brendan, 2026-11-05) | verified | — |
| `char` | Its distortion's character, `char <track> <1-4>`, soft, hard, fold or crush, from the radio over its knobs (Brendan, 2026-11-05) | verified | — |
| `delay-note` | The selected track's delay time, `delay-note <track> <1-5>`, 1/2 to 1/32, from the time radio's top row; and `delay-feel <track> <1-3>`, straight, triplet or dotted, from its bottom row | verified | — |
| `feedback` | Its delay's feedback, `feedback <track> <0-100>`, and `delay`, its level, the same way | verified | — |
| `send` | Its send to the reverb, `send <track> <0-100>` | verified | — |
| `size` | The reverb's size, `size <0-100>`, the kit's, no track; and `damping`, the same way | verified | — |
| `verb-type` | The reverb's type, `verb-type <0-2>`, the kit's, no track: 0 the plate, 1 gigaverb, 2 freeverb, from its radio (Brendan, 2026-11-05) ([sequencer.md](../module/sequencer.md)) | verified | — |
| `mute` | A track's mute, `mute <track> <0 or 1>`, from the M under its pad: muted, its hits stop and its tails ring out ([sequencer.md](../module/sequencer.md)) (Brendan, 2026-11-05) | verified | — |
| `solo` | Its solo, `solo <track> <0 or 1>`, from the S: with any track soloed only the soloed play, the mutes ignored | verified | — |
| `rnd-pitch` | The selected track's random pitch, `rnd-pitch <track> <0 or 1>`, from **rnd pitch** beside sync and snap, lit while it's on and asking for the opposite of what it shows: a hit its randomness rolls takes a pitch of its own (Brendan, 2026-11-05) ([sequencer.md](../module/sequencer.md)) | verified | — |
| `set-swing` | The swing, `set-swing <50-75>`, as it stands. The swing is the phone's alone since knob 4 became rush (Brendan, 2026-11-05); `swing <0-1>`, a knob position that passes a latch, stays for a map row that wants it | unknown | — |
| `set-last` | The global last step, `set-last <1-32>`, the same way beside knob 2's `last`, clipped to the time signature's reach ([sequencer.md](../module/sequencer.md)) | unknown | — |

What `sections` carries, each one `u_song`'s own (`R.phone_cmds` in `u_song.lua`); what each does
is in [songs.md](../module/songs.md). A name is one OSC string, spaces and all.

| Action | Is | Evidence | Item |
|--------|----|----------|------|
| `select <n>` | A row tapped: section *n* selected | unknown | — |
| `new` | A copy of the selected section | unknown | — |
| `saveas` | What's playing, as it stands, as a new section | verified | — |
| `up` | Move it up | unknown | — |
| `down` | Move it down | unknown | — |
| `length <0-64>` | Its length in bars | unknown | — |
| `delete` | Delete it | unknown | — |
| `name <name>` | Its new name | unknown | — |
| `tweaks <0 or 1>` | Whether the voices' sounds carry on into it, 1, or snap back, 0 ([voices.md](../module/voices.md)) | unknown | — |

What `songs` carries, each one `u_song`'s own (`R.songs_cmds` in `u_song.lua`).

| Action | Is | Evidence | Item |
|--------|----|----------|------|
| `select <n>` | A song's row tapped: song *n* selected | unknown | — |
| `load` | Load the selected song | unknown | — |
| `new` | A new song | unknown | — |
| `add` | Add it to the setlist | unknown | — |
| `delete` | Delete it | unknown | — |
| `name <name>` | The song's new name | unknown | — |
| `choose <n>` | Setlist *n* chosen, its first entry selected | unknown | — |
| `entry <n>` | An entry's row tapped: entry *n* selected | unknown | — |
| `up` | Move the selected entry up | unknown | — |
| `down` | Move it down | unknown | — |
| `new-set` | A new setlist | unknown | — |
| `remove` | Take the entry out | unknown | — |
| `set-name <name>` | The setlist's new name | unknown | — |

What `synth` carries, `c_synth.lua`'s `R.SYNTHS`. The app sends
neither: a voice's machine chooses the synth (`voices`).

| Synth | Is | Evidence | Item |
|-------|----|----------|------|
| `fm` | The M-VAVE FM-1 ([fm1.md](fm1.md)) | unknown | — |
| `strings` | The Waldorf Streichfett ([streichfett.md](streichfett.md)) | unknown | — |

What the keys page's velocity button sends after `velocity`, `c_synth.lua`'s `R.VELOCITY`.

| Setting | Is | Evidence | Item |
|---------|----|----------|------|
| `on` | A key's velocity reaches the synth, as before the switch | unknown | — |
| `off` | Every note-on goes out at 127, on either synth; a release stays 0 (Brendan, 2026-11-04) | unknown | — |

| Property | Value | Evidence | Item |
|----------|-------|----------|------|
| `hb` | Sent **unconditionally at 2 Hz**, and at once on a flip of test mode | verified | — |
| The state | `drums`, `synth`, `velocity`, `tempo`, `lists`, `melody`, `notes`, `voices`, `perform` and `sound` go again on every heartbeat **on top of** their sends on change | unknown | — |
| Late or returning phone | Repopulates within half a second with nothing moving | unknown | — |
| `tempo` | Coalesced into **one slot** at 20 Hz: `u_tempo` hands on every BPM the tempo bus carries, and one sweep of knob 1 is some 200 a second. `phone-assert` sweeps 401 and requires at most ~60 datagrams and the last BPM | unknown | — |
| Socket recovery | `u_net` rebuilds within about five seconds of the phone coming back, nothing touched on the instrument | verified | 119 |
| Backgrounding the phone's app | PdParty's cost the link nothing, only a full quit closed the port (Reference, item 120). iOS closes the Cut It app's sockets while it is away, and the app makes new ones when it comes back (`phone/CutIt/Link.swift`): the prototype came back fine (Brendan, 2026-11-06), and the app is to be tried on the rig (`cut-it/cut-it-app`) | unknown | 120 |

### The app

**`phone/`, a native iPhone app**, landscape and drawn for the iPhone 11 (`cut-it/cut-it-app`).
`phone/install.sh` builds the working tree and puts it on the phone over Wi-Fi; `phone/testflight.sh`
sends a pushed commit to TestFlight, which installs it on the phone by itself. What each page shows
and sends is its own code, `phone/CutIt/Pages.swift` and the views beside it.

### The app reads each state by name

**A state's fields are named once, in the Lua that writes it, and the app's places come from that
table.** The drums' state, the generator's, its notes', `u_perform`'s and `u_voices`' each go out
as one flat list, and the app reads a list by position. The Lua names a list's fields in order,
each with how many atoms it takes (`R.PHONE_FIELDS` in `c_steps.lua`, `c_melody.lua`,
`u_perform.lua` and `u_voices.lua`, and `c_melody`'s `R.NOTES_FIELDS`), and writes the list by
running that table, so the table and the list can't differ. `phone/state-at.py` writes where each
field begins into `phone/CutIt/StateAt.swift`, and the app reads only there:
`a[MelodyAt.home]`, `cut.drum(DrumsAt.vol, track: 3)`.

⛔ **A field added to a state moves every read after it, and the two ends deploy apart.** So
`app-assert` fails while `StateAt.swift` is not what the Lua's tables give today, when the app
reads one of these states at a number of its own, and when it names a place the file hasn't. After
changing a state's fields, run `python3 phone/state-at.py`, build the app and put it on the phone
when the patch is deployed: an app built before the change reads the new list at the old places.

`g_grid.lua` reads the generator's two states by position as well, at indices of its own, which
`g_grid_test.lua` holds by painting from what `c_melody`'s `R.phone` and `R.phone_notes` write.

### The phone controls the page, and does not copy the OLED

**Brendan split the two on 2026-11-04**: the OLED for alerts and warnings, levels and the name of a
control as it moves; the phone for the Launchpad's current page. Until then `u_net` subscribed to
`disp` and forwarded every parameter row, the footer's status and the held alert, and the phone
drew a remote screen of them with three diagnostic buttons. All of it went: `u_net` holds no `[r
disp]`, and `phone-assert` puts a sweep, a row, an alert and a meter on `disp` and requires
nothing of them on the wire. What the phone shows now is each module's state, handed to `u_net` on a
cord, which is what a control surface needs and a mirror never had.

### The tempo lives on the phone

The phone shows the BPM as a number and sets it (Brendan, 2026-11-04: "Tempo should live on phone
only, and should be editable on the phone as well"): the performance page's readout, and the songs
page's tempo, a BPM a step. It is `u_tempo`'s, the clamped value whatever set it — knob 1, the tap
pad, the phone itself, a Send line — on a cord out of `u_tempo` into `u_net`'s fourth inlet, so the phone
shows the tempo in force, not one it asked for. The status string the footer carried, until the
footer went too, was the wrong vehicle: one slot shared with every other status, and a word.

The phone's tempo goes to `u_tempo` by a cord, and `u_tempo` writes the bus, so nothing from the phone
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

### The inbound port is armed late, and the Mac has its own

A second bind of the same UDP port prints a real line on stdout (Pure Data, in Reference, item 307),
and **stdout is the oracle** both `tools/deploy.sh` and the suite's silence gate use, so a patch that
bound at `loadbang` would turn every run red whenever a copy was already open in Pd.

**Fix:** two things, each independently sufficient for its own case. The `listen` is armed at
**2000 ms**, past the ~735 ms at which the deploy check quits, so neither it nor the syntax gate ever
binds at all. And `main-dev.pd` takes **9002** where `main.pd` takes 9001, so a long-running gate
cannot collide with the dev patch. ⚠️ **The phone's controls therefore drive the device, not the
Mac**: the app sends to 9001 alone (`phone/CutIt/Link.swift`), so it reaches `main-dev.pd` only
from a build changed to send to 9002.

### An AP session cannot be driven interactively

⚠️ A laptop joined to the Organelle's own access point is offline, so nothing Mac-side can reach the
phone or the device during a stage session.

**Fix:** stage everything beforehand — the checklist is on [wifi.md](../wifi.md).

### Send state, never events

Every message out carries the complete current value — the tempo is 133, never one more. A dropped
packet then **self-corrects on the next send** instead of leaving the display permanently and
silently wrong. UDP will drop packets; the protocol has to not care. The phone sends the tempo, the
last step, the swing and a pad's dragged value as they stand for the same reason; the time
signature's boxes send steps, `c_steps`' own `num` and `den`, and the state that comes back
corrects a lost one.

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
on it. The app checks how long it is since the last heartbeat; past 1500 ms a red `no link` bar
tops every page rather than presenting a stale value as current (`phone/CutIt/Cut.swift`).

⚠️ **The app starts unlinked.** It must assume the worst until traffic proves otherwise, or an app
opened before the Organelle is running looks connected when it is not.

The heartbeat keeps flowing even when nothing is happening, because it is the only thing
distinguishing *idle* from *dead*.

### The app can hear and not be heard

⚠️ **A page that shows the instrument's state and ignores every press is iOS blocking what the app
sends.** The `no link` bar reads the heartbeat alone, so it stays away: the state still arrives,
and no press leaves the phone. So the app reports its presses too: one given up after its tries
(*A press, once*) puts a red `not heard` bar where `no link` goes, until a press of its own is
answered (`phone/CutIt/Cut.swift`). **Fix:** on the phone, in Settings, Privacy & Security, Local Network, switch Cut It off and on,
then quit the app and open it. The switch can read on while it blocks (iOS, in Reference). With the
switch off outright the bar is `not heard` too, the phone checklist's step 17.

### A socket that can't send keeps what it's given

⛔ **A press given to a socket that can't send acts late.** iOS keeps what such a socket is handed
and sends all of it once it can (iOS, in Reference): two presses tapped while the app was blocked
turned the page twice, at once, when the block lifted. **Fix:** `Link.send` gives the socket
nothing unless it is ready and has a way out. A press is sent again by `resend` and, unanswered,
given up (*The app can hear and not be heard*); a drag's next value follows. A sending socket that
fails is made again by itself, the listener left hearing (`phone/CutIt/Link.swift`). That nothing
arrives late on the phone is the phone checklist's step 17.

### The Organelle never waits for the phone

Fire and forget over `[netsend -u]`. Phone off, phone crashed, WiFi gone — **the instrument plays
identically.**

### The inbound vocabulary is closed, and the closure is the design

Eleven commands, every one of them a **literal argument on a `route` box you can read**, with
everything else falling out of an unconnected reject. That is the same allowlist guard `u_map` uses
for its destinations and it is here for the same reason: the set of things a datagram can reach
stays the set of boxes you can read. **All but `result` pass on what follows them**: `c_steps`,
`c_synth`, `u_tempo`, `u_song`, `c_melody`, `u_voices`, `u_perform` and `u_sound` hold those lists
and refuse the rest, as `bad-selector`, `bad-synth`, `bad-tempo` and `bad-velocity`, so a new drum control or synth
needs nothing here (Brendan, 2026-11-04).

⚠️ **Nothing here may be built on a sender identity that is not available** — `[netreceive]` in
0.49 cannot supply one (Reference, *Pure Data*), and a bidirectional link does not change that.
0.57's can, with `-f` (above).

⛔ **Nothing from the phone reaches the buses by itself** (Brendan, 2026-11-04). A `send` command
once carried a checklist's Send line to `u_inject`, in test mode only, so the phone could run any
checklist alone; it went when the checklists split into two suites, since the line check, the one
the phone carried, sends nothing, and the development checklists' lines go from the Mac. The tempo
the phone sets goes to `u_tempo` by a cord, and `u_tempo`, which owns the tempo, writes it.

**Test mode** is flipped with the diagnostics page's second pad, `pad-82`, which the Launchpad's
Setup button opens (`lp-setup`), or the diag page's test mode button; it starts off at every load,
goes off when a page is chosen, and rides on the heartbeat; a flip sends a heartbeat at once rather
than waiting for the next. Turning it on warns, so the OLED says so and the log keeps it. The app
reads it from the heartbeat and puts the line check in place of the page while it's on
(`phone/CutIt/LineCheck.swift`), so a page chosen, which turns it off, brings the page back. The
line check is `test/checklists/linecheck.md` as it is, carried in the app (`phone/project.yml`), a step
at a time: its title and its Need, Do, Check and Pass if, the Notes left in the file. Pass and Fail
send `result linecheck-<n>-<pass or fail>` and go on to the next step, the button flashing at
`ack result`; FM and STRINGS send `synth fm` and `synth strings`, lit from `/cutit/synth`, so steps 5
and 6 play either synth without a voice's page, which would end test mode.

⛔ **A full status dump was considered and rejected as a command.** Every state address repeats on
the heartbeat, so a phone joining late repopulates on its own within half a second — item 121. It
would have been a button that does what waiting does.

**The phone drives something musical now**: the tempo, the time signature, the swing and the
sequencer's settings. Brendan's call of 2026-08-11, that it might one day, came with the two
properties recorded above — how unevenly the link delivers, and that the instrument plays
identically without it — and those are what each control answers to: every one sends a value the
state corrects, and none is needed to play.

## Open

What the TouchOSC layout did that the app does not, as of 2026-11-19 when the layout went. The
app is to take on its line check, random pitch, chord pins and command gate (Brendan, 2026-11-19),
but not its tap tempo, since the Launchpad's tap pad and the nanoKONTROL's LOOP still tap, nor its
control for the time signature's bottom number:

- ⬜ **No choosing the nanoKEY's synth but by a voice's page** (`cut-it/cut-it-app`), outside the
  line check, whose FM and STRINGS send `synth fm` and `synth strings` in test mode: the layout's
  keyboard tab sent them too, which `c_synth` puts in the section, so the choice survived a reload.
  A voice's page sends `machine`, which isn't put, and the setup page's machine changes the voice
  itself. The synths checklist's steps 8 to 10 use the keys page instead.

And one of the app's own:

- ⬜ **The phone checklist's step 17 hasn't been run on a build with the fix** (`cut-it/cut-it-app`,
  *A socket that can't send keeps what it's given*): `app-assert` holds the guard in the code, and
  only the phone can block the app, so that a tap made while blocked never arrives isn't measured.

