<!-- schema: device -->
# M-VAVE FM-1

**Files:** `Cut It/m_fm1.pd` · **Gate:** `test/gate/fm1-assert.sh` · **Checklist:** `test/checklists/midi.md`

**The rig's FM synth, `fm`, and an output-only device layer.** What the FM-1 is, what it receives on
its two channels, its voices, its SysEx and its traps are in Reference:
`~/Sites/!reference/m-vave-fm-1.md`. This page is how Cut It drives it. It took the Korg Volca FM's
place on 2026-11-24 (`~/Sites/!reference/korg-volca-fm.md`).

It reaches the Organelle over USB, straight into the hub, on Pd's port 4 out: **Pd channel 49** is
its own channel 1, for notes and program changes, and **Pd channel 50** its channel 2, for its
effects' controllers.

`m_fm1.pd` has **one inlet, selector-prefixed** (`notes` / `cc` / `program` / `note` / `byte`) and
**no outlets** — neither `param` (device-to-map) nor `disp` (display) fits a sounding note, so it is
wired from `u_map` rather than fed by a bus.

**The one decision this page turns on: nothing comes back from it.** The FM-1 sends its own keys,
arpeggiator and sequencer as notes, and `wire.sh` leaves them unwired, so the layer is told what to
play and hears nothing.

## Design

### Addressing

| Property | Value | Evidence |
|----------|-------|----------|
| Pd channel block | 49–64 (output slot 4): 49 its channel 1, 50 its channel 2 | verified |
| ALSA client | `FM-1`, one port, in and out | verified |
| `wire.sh` outbound | `Pure Data:7 → FM-1:0` | verified |
| `wire.sh` inbound | none. Its keys on Midi-In 4 would read as the nanoKEY's, which has that port to itself ([nanokey.md](nanokey.md)) | verified |

### Controllers go out one channel up

The FM-1 takes controllers for its effects alone, on its effect channel, and none for the FM voice
itself (Reference). So `cc <controller> <value>` leaves on `$1 + 1`, Pd channel 50, and notes and
program changes on `$1`. ✅ A key through the patch sounds it, and `reverb` set from the phone's path
puts a tail on the next key and takes it off again at 0 (2026-11-24, recorded from the FM-1's USB
audio).

⛔ **Both channels are the FM-1's own settings**, on its GLO page: MIDI channel ALL (or 1) and
effect channel 2, as it ships. Change either on the device and the notes or the effects stop,
with nothing in the patch to say so.

So the `fm` machine's parameters are its program, its effects and a DX7 voice of the library, sent
whole (below, *`byte` is a whole voice*); nothing of a voice's own parameters. Each effect's
amount carries that effect's own on-off, on above 0 and off at 0, and stops at the FM-1's top for
it: 100, the cutoff's 107, the Q's 10, a type's 2 ([voices.md](../module/voices.md), *Machines and
patches*).

`u_sound` says a machine's parameters in `cut-it-machines.txt`'s order, the program first: a
program change brings that voice's own effect settings with it (Reference), so what's set after it
is what stands, and a program or a DX7 voice moved on its own says what's been set again behind it
([voices.md](../module/voices.md), *Machines and patches*).

### Presence: `none`, and that is a fact rather than a gap

`m_fm1` registers as `none` on the presence bus and stops there — no poll, no last-heard clock, no
aging, and it can never be declared lost or back. **The FM-1 answers no device inquiry**
(Reference), and its keys are unwired, so there is no evidence of its presence for the patch to
find, and the alternative to recording that is a silence that reads as an oversight.

⛔ **THE BOUNDED RECOVERY CANNOT REACH THIS DEVICE ON ITS OWN.** `u_present` re-runs `wire.sh` only
while *some* source is lost — so through that path a replugged FM-1 comes back **only if a
detectable device is missing at the same time**. Unplug it on its own and nothing is lost, nothing
forks. **The re-wire heartbeat is what covers the FM-1**: it watches the ALSA client list and does
not care whether anything was lost — see [presence.md](../module/presence.md).

⚠️ **Nothing in the patch can confirm the FM-1 came back.** The heartbeat can say it re-wired —
`info u_present rewire-try` reaches the log — but whether the FM-1 is *sounding* is still only your
ears, which is why its checklist steps are judged by ear. See [presence.md](../module/presence.md).

### No MIDI clock reaches this device

`u_tempo`'s `realtime-out` feeds exactly **one** `[midiout]` with the clock, set at loadbang to
port **1**, the Launchpad. The FM-1 is port 4 and the nanoKONTROL is port 2, so neither receives a
clock byte from Cut It. ✅ Measured with `aseqdump` on Pd's Midi-Out 4: five seconds produce nothing
at all, across a patch reload included. Item 279.

The FM-1 would follow a clock, but only its own sequencer and arpeggiator do, and Cut It plays it
note by note.

✅ **`panic`'s realtime STOP reaches port 4**, through a receive that the panic branch is the sole
writer of — item 295. A synthesizer with a sequencer that keeps running through a panic is the case
panic exists for, and the mixer's master fader cannot stop it. 📄 The FM-1 takes Stop for its
sequencer and arpeggiator (Reference).

### Pd's `pgmout` is 1-based

A Pd fact, in `~/Sites/!reference/pure-data.md` (item 228). **Fix here:** `m_fm1.pd` carries a
`[+ 1]` before `[pgmout]`, so its `program <n>` inlet means the **wire** number: 0 is the voice the
FM-1's screen calls 001.

### ⛔ Absent at load, only the heartbeat ever wires this device

A `none` device has no clock, so it cannot be lost; and `u_present`'s bounded recovery is gated on
*something* being lost. Boot the instrument with the FM-1 unplugged and every pollable layer
answers, nothing is lost, the spigot stays shut, the counter never starts, and **no scheduled
`wire.sh` fork ever runs**; `u_init`'s boot fork ran before the cable went in.

⚠️ **This is the likelier direction in a room**: you power the rig up, *then* plug the FM-1 in, or
switch it on. There is no warning, because nothing is wrong from the instrument's point of view.

**Fix:** `u_present` forks **`wire-watch.sh`** on a heartbeat — every 8 ticks, so ~16 s. It hashes
the ALSA clients and their connections and runs `wire.sh` only when they change, so a device
appearing is wired whether or not anything was ever lost, and so is one switched off and on between
two heartbeats ([presence.md](../module/presence.md)). ✅ **So the checklist steps pull the FM-1 ALONE** — pulling a
detectable device alongside it goes through the loss path and proves nothing about the heartbeat.

| | Behavior | Evidence | Item |
|---|---|---|---|
| `none` device absent at load | enumerated, unsubscribed, never re-wired — 120 s observed, on the Volca's interface | verified | 285 |
| The heartbeat closes it | `wire-watch.sh` fires while **nothing** is lost, which no other fork in `u_present` can do | verified | 292 |
| On the FM-1 itself | Switched off and on by hand: wired 5.9 s after it came back. Taken off the USB bus and put back three times in software (its `authorized` file): 10.7, 11.7 and 9.1 s. Nothing lost meanwhile (2026-11-24) | verified | — |

### One selector-prefixed inlet, not one inlet per capability

`u_map` reaches the FM-1 on **one cord** carrying `notes 48 100 200`, `cc 7 64` or `program 3`,
routed inside the device layer. The alternative — one outlet per inlet — makes `u_map`'s outlet count
the sum of every device's capabilities, and crosses the "revisit past about four output devices"
threshold with two devices.

⛔ **An unrecognized selector is a real error**, reported as `fail m_fm1 bad-selector` on `err`. It
means `u_map` and this file disagree about the interface, and nothing else would notice.

### `makenote` is safe here, and only here

Notes go to **one** channel, set cold at load, so `[makenote]` → `[noteout]` cannot send a note-off
to the wrong place. ⛔ **A device with several channels cannot use this**: `makenote` schedules the
note-off, and by the time it fires `[noteout]`'s cold channel holds whatever the latest note set, so
two channels overlapping send the off to the wrong one. `m_404` carried the channel with the delayed
off through a `[pipe]`, for the SP-404's ten, until it left the rig (2026-11-04).

### The `note` selector bypasses `makenote`, and pays for it with a panic

⛔ **A keyboard cannot use `makenote`.** Its duration is fixed, so a **held key would release
itself** — which is also why the map's `fm1-note` destination cannot drive one. The `note`
selector goes straight to the same `[noteout]`, and the note-off comes from the key as velocity 0.

| | | Evidence | Item |
|---|---|---|---|
| `note <pitch> <velocity>` | a real note-on; velocity **0 is a real note-off** | verified | 293 |
| It reuses the **same** `[noteout]` | one channel, one object, so the layer adds one `noteout` to `MIDI_EXPECT`, as `m_streich`'s does | verified | 293 |
| `panic` → a note-off for every note, 0 to 127, then **CC 64** at 0 | the offs as lists into that `[noteout]`, sustain off through `[ctlout 64]`, channel cold from the loadbang chain | verified | — |

⛔ **The panic belongs with the `note` inlet, not after it.** `makenote` owns the note-offs, which is
what stops a dropped cord or a reload leaving the FM-1 droning; bypassing it brings that risk back,
and the note-offs are what replace it.

⛔ **All Notes Off is not a panic here.** The FM-1 ignores CC 123 and CC 120 (Reference), which is
what the Volca's layer sent and `m_streich` still does. ✅ 128 note-offs and sustain off silence a
held, sustained chord, and `aseqdump` on Pd's Midi-Out 4 shows a panic sending exactly those
(2026-11-24).

⚠️ **`[ctlout 64]`'s creation argument is the CONTROLLER, so the channel goes to inlet 2.** Wired
to inlet 1 it sets the controller instead, and panic's sustain off silently does nothing.
`fm1-assert.sh` asserts the channel.

### `byte` is a whole voice, into the one voice kept for it

`byte <b>` sends one raw byte out the FM-1's own port. `u_sound` sends a DX7 voice that way, a byte
at a time: one of the library's ([voices.md](../module/voices.md), *The DX7 library*) or one of the
diagnostics page's two test voices.

⛔ **A voice sent this way is written into the FM-1 for good**, over the voice it is on, and is
still there after a power cycle (Reference). So every one goes into **the FM-1's voice 128**
(program 127, the `dx7-voice` row's top in `cut-it-machines.txt`), which Cut It keeps for it: the
program change first, then the voice. ✅ Voice 002 sounded the same before and after, and 128 took
the voice (2026-11-24, recorded from the FM-1's USB audio).

⛔ **That program change goes as bytes too, `C0 7F`, never through `program`.** Pd writes
`[midiout]`'s bytes at once and queues `[pgmout]`'s (`~/Sites/!reference/pure-data.md`), so a
`program 127` sent just ahead of a voice arrives behind it, and the voice lands on whichever voice
the FM-1 was on. ✅ `aseqdump` on Pd's Midi-Out 4 showed the voice first that way; with the bytes,
the program change, the voice, then the effects' controllers (2026-11-24).

⚠️ **Each voice chosen is a write into the FM-1's memory**, so `u_sound` never sends the one it
sent last. How many writes its memory takes is not known (Reference).

### The layer stays Pd

**`m_fm1` has nothing to decode, so it has no Lua** (2026-11-03), where the nano and the
Organelle's keys do ([nanokontrol.md](nanokontrol.md), *The decode is Lua*). It is a `route`, two
`unpack`s, two `+ 1`s, `[makenote]`, the MIDI objects and panic's loop: what Lua would take is the
route and the sums, and the MIDI objects would still need their channels and controllers set cold in
Pd, in the order the file's `[t b f]` keeps. That is no simpler, and a pdlua call costs about 0.1 ms
on the Organelle where these boxes cost a few microseconds.

## Open

- ⬜ **A section's program reaches the FM-1 without its effects said again.** NO PLAN OWNS THIS.
  `c_synth` sends a section's `programs` straight to `m_fm1` ([synths.md](../module/synths.md)), and
  `u_sound`, which holds what's been set, doesn't hear of it: the voice arrives with its own effect
  settings until a control moves, and a row on a DX7 voice is left on the section's program, its own
  voice not sent again until another is chosen.
