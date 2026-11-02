# Cut It

A cut-up / harsh-noise instrument for the original Critter & Guitari Organelle (Organelle 1),
written in Pure Data. How to work on it is in [AGENTS.md](AGENTS.md).

## Changelog

**v0.4, the instrument (next).** The sound itself: four filter stages (chop, filter and pitch,
tremolo, reverb and freeze), the drum mode, the sampler and compose-time capture, each reached
from a control by a row of the map that v0.3 built.

**v0.3.x, the last of the groundwork (August 7–12, 2026).** A one-command test runner, a gate for
every module, a cleanup of `tools/` and the device, hot-swapping devices, a panic that can
reload the whole patch, and diagnostics on the OLED and the phone for debugging without a laptop.
Before it, the documentation was cut from ten root files to the `ref/` pages and a gate that
checks them.

**v0.3, the blank slate (August 6, 2026).** Every device addressable and every control
assignable: `u_map` looks up what a control does in each mode from a table, and the SP-404 and
the Volca became devices Cut It plays.

**v0.2, the rewrite (July 28 – August 5, 2026).** Cut It rebuilt from scratch for the new rig:
the nanoKONTROL, Launchpad and Organelle controls, MIDI clock, saved state, the OLED and the
phone, with headless tests and hardware checks. It passes audio through and knows what every
control is doing, but makes no sound of its own.

**v0.1, the first sketch (2020–2024).** The original idea, a chain of four "pedals" played from
the Organelle's keys: a sampler that loops and chops, Chop Shop, tremolo, and reverb and freeze.
Only a tremolo, sample playback and MIDI clock were built before it was set aside; the rest
stayed a design on paper.
