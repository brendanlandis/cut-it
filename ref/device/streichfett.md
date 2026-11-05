<!-- schema: device -->
# Waldorf Streichfett

**Files:** `Cut It/m_streich.pd` · **Gate:** `test/gate/synths-assert.sh`, `test/gate/presence-assert.sh` · **Checklist:** `test/checklists/synths.md`

The rig's string synthesizer, and one of the two synths the nanoKEY plays: `strings`, beside the
Volca's `fm` ([synths.md](../module/synths.md)). What the Streichfett is, its MIDI channel, its
identity reply and its global dump are in Reference: `~/Sites/!reference/waldorf-streichfett.md`.
This page is how Cut It drives it.

It reaches the Organelle over USB, on Pd's port 3: **Midi-In 3, channels 33–48, and Midi-Out 3**,
the SP-404's slot until the 404 left the rig ([boot.md](../module/boot.md), *The ALSA wiring*). Its
own channel 1 is Pd channel 33, `u_root`'s fourth argument.

**The one decision this page turns on: it is told what to play, like the Volca, and polled for
presence, unlike it.** `m_streich` takes the Volca's four selectors on one inlet and has no outlets;
and since the Streichfett answers the identity request, it is an `active` source on the presence
bus, as the Launchpad and the nano are.

## Design

### The inlet is the Volca's

| Selector | Does | Evidence |
|----------|------|----------|
| `notes <n> <v> <d>` | A note of a fixed duration, through `[makenote]`, safe because the Streichfett has one channel ([volca.md](volca.md), *`makenote` is safe here, and only here*) | unknown |
| `cc <c> <v>` | A control change, the controller held cold by `[t b f]` | unknown |
| `program <n>` | A program change, `[+ 1]` before `[pgmout]`, so `n` is the wire number (Pure Data, in Reference) | unknown |
| `note <n> <v>` | A held key: velocity 0 releases. Straight to the one `[noteout]`, as on the Volca | unknown |
| anything else | `fail m_streich bad-selector` on `err`: `c_synth` and this file disagree about the interface | unknown |

**Only `note` has a caller today**, `c_synth`, for the nanoKEY's keys. `notes`, `cc` and `program`
are there because the layer is the Volca's shape, so a map destination or a phone probe for the
Streichfett costs a `route` argument elsewhere and nothing here.

⛔ **Panic is All Notes Off, CC 123, on its channel.** The `note` path bypasses `makenote`, so a
key held while something goes wrong would drone; `[ctlout 123]` takes the channel on its second
inlet, set cold at load, and `synths-assert` asserts the channel.

**The channel is printed two seconds in**, `m_streich-channel: 33`, behind `[del 2000]` (C-9):
a wrong count of creation arguments loads in silence ([architecture.md](../architecture.md)).

### Presence: `active`

| | Value | Evidence |
|---|---|---|
| Kind | `active`, registered by its `c_presence` | unknown |
| `c_devid` argument | **62**, Waldorf's manufacturer byte `3E`, which nothing else in the rig sends | unknown |
| Stagger | **120 ms** after the tick, clear of the Launchpad's 0 and the nano's 60 | unknown |
| The inquiry's port | **3**, worked out from the channel block as `m_nano` does: `(33 - 1) / 16 + 1` | unknown |
| On the diag roster | `m_streich here`, `gone` or `never`, the fifth row of five ([display.md](../module/display.md)) | unknown |

⛔ **The argument is decimal and the reply is hex**, as for the nano: `[c_devid 3E]` would never
match, and an undetected device looks exactly like an absent one.

**`c_presence`'s second outlet is unconnected**: nothing here goes stale while the Streichfett is
away. A loss is `warn m_streich device-lost` and `u_present`'s shared re-wire, as for any active
layer ([presence.md](../module/presence.md)).

### Nothing it sends is read

Its replies and its panel arrive on Midi-In 3, channels 33–48, and nothing but `c_devid` listens
there: no `[notein]` or `[ctlin]` in Cut It takes channel 33 (`m_nanokey` gates on its own port,
and `synths-assert` plays a note on 33 that must reach nothing). Its own keys and knobs play it
directly, without Cut It.

### No clock and no transport

`u_tempo`'s clock goes to port 1 alone ([volca.md](volca.md), *No MIDI clock reaches this device*),
and `tempo-assert` holds the clock and panic's STOPs off port 3. The Streichfett has no sequencer to
stop, and its arpeggiator, if one is ever used, runs on its own clock.

## Open

- ⬜ **It has not played from Cut It on the rig**: the nanoKEY through `c_synth`, panic silencing a
  held note, its row on the diag screen. `test/checklists/synths.md`, `cut-it/pages-and-displays`.
- ⬜ **Whether it answers the inquiry every two seconds for hours** without a false loss, as the
  nano and the Launchpad did over 9.5 hours (item 282). `cut-it/pages-and-displays`.
