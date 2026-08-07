# Cut It — Design Notes

How the instrument works: architecture, timing model, and the decisions behind them.

Companion to [ref-hardware.md](ref-hardware.md), which covers the physical rig — boxes, cables,
signal flow, and verified device behaviour. The rule of thumb: **if it describes what the
hardware does, it's in the rig plan; if it describes what we decided to build, it's here.**

See also [ref-midi.md](ref-midi.md) for the MIDI message reference,
[ref-conventions.md](ref-conventions.md) for how the Pd is actually written,
[README.md](<! v0.1 plans/README.md>) for musical intent and the v0.1 control layout, and
[CLAUDE.md](CLAUDE.md) for the hard constraints on writing Pd for this device.

---

## Moved to `ref/`

**This file is now a pointer stub.** Everything in it has a home under [ref/](ref/README.md), where
the unit of a page is a module rather than a topic.

| Looking for | Now on |
|---|---|
| The composition diagram, the `m_` boundary, the buses, `u_err`, the load-bearing decisions, division of labour | [ref/architecture.md](ref/architecture.md) |
| The audio chain, the I/O contract, the level meter | [ref/module/audio.md](ref/module/audio.md) |
| Tempo, the clock, poly-tempo, the rate ceilings | [ref/module/tempo.md](ref/module/tempo.md) |
| The map and what a control means | [ref/module/map.md](ref/module/map.md) |
| The display arbiter and the `disp` bus | [ref/module/display.md](ref/module/display.md) |
| The Launchpad's three-tier decision | [ref/device/launchpad.md](ref/device/launchpad.md) |
| The 404's audio split and its measurements | [ref/device/sp404.md](ref/device/sp404.md) |
| How the Pd is written, C-1..C-14 | [ref/conventions.md](ref/conventions.md) |

**What is still open** — including tempo propagation under fast modulation, the compose/perform
consequences, and the three storage decisions for capture — is in [plan-v03.md](plan-v03.md) §4.
