<!-- schema: device -->
# Korg nanoKEY (mk1)

**Files:** `Cut It/m_nanokey.pd` · **Gate:** `test/gate/synths-assert.sh` · **Checklist:** `test/checklists/synths.md`, `test/checklists/linecheck.md`

The rig's keyboard: 25 keys that play whichever synth is chosen, the Volca or the Streichfett, on
every page (Brendan, 2026-11-04; [synths.md](../module/synths.md)). What the nanoKEY is, its USB
and ALSA names, its channel and its identity reply are in Reference:
`~/Sites/!reference/korg-nanokey.md`. This page is how Cut It reads it.

**The one decision this page turns on: its keys go by cord to `c_synth`, not on `param`.** A
key means the same on every page, the chosen synth's note, so there is nothing for the map to look
up per page; `m_nanokey` hands `<note> <velocity>` to `c_synth`, which decides where it sounds.

## Design

### The port it shares

`wire.sh` connects `nanoKEY:0` to Pd's Midi-In 4, channels 49–64, which it shares with the Volca's
USB→DIN interface, whose DIN IN carries nothing ([boot.md](../module/boot.md), *The ALSA wiring*).
`m_nanokey` takes the block's first channel, `u_root`'s fifth argument, 49 on the device: the same
number as the Volca's output block, since the Volca's interface is port 4 both ways.

| | Value | Evidence |
|---|---|---|
| What it reads | `[notein]`, every note on Pd channels 49–64: **any channel of the port**, so a nanoKEY set to another channel still plays | unknown |
| What it sends | `<note> <velocity>` out its one outlet to `c_synth`; a release, note-off or note-on at velocity 0, as velocity 0 | unknown |
| What it ignores | Every other port: the Launchpad's, the nano's and the Streichfett's notes never reach it, nor would a fifth port's | unknown |
| The channel, printed | `m_nanokey-channel: 49`, two seconds in, behind `[del 2000]` (C-9) | unknown |

The gate is `0 <= channel - block < 16`, the nano's shape for its two channels. `synths-assert`
plays notes on channels 17, 33, 48 and 65 that must reach nothing, and one on 50 that must.

### Not polled, and not on the roster

`m_nanokey` registers nothing on the presence bus, not even `none`, so the diag screen has no row
for it. Two reasons, either enough:

- ⛔ **A sixth row breaks the diag layer's five-row bound**: g_oled draws the roster at y = 0, 9, 18,
  27 and 36, and a sixth at 45 runs into the meter strip ([display.md](../module/display.md)). The
  roster is five with `m_streich`. The OLED's revision lifts the bound
  (`cut-it/pages-and-displays`), and then the nanoKEY can register.
- ⛔ **Its identity reply carries Korg's byte, `42`, the nanoKONTROL's** (Reference). A poll would be
  answered as the nano by `[c_devid 66]`, so a nano that is gone would read as present whenever the
  nanoKEY answers. Telling them apart needs the family bytes, which `c_devid` does not read.

So a nanoKEY that comes unplugged is noticed by ear, and recovered by the re-wire heartbeat, which
re-runs `wire.sh` when the ALSA client names change ([presence.md](../module/presence.md)).

### Notes only

`[notein]` is the only MIDI object in the layer, so what the pitch bend and modulation buttons send
is not read.

## Open

- ⬜ **It has not played through Cut It on the rig.** `test/checklists/synths.md`,
  `cut-it/pages-and-displays`.
- ⬜ **Pitch bend and modulation are not passed on**; whether either synth should get them is
  `cut-it/pages-and-displays`'s.
