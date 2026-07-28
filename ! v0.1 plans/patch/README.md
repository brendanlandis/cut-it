# The v0.1 patch — archived

The deployable patch as it stood before the v0.2 rewrite. Kept because it records **what the
instrument was trying to do**, and because the git history is worth following.

**Do not lift code from here.** All of it predates
[plan-conventions.md](../../plan-conventions.md) — no `$0` discipline, no `[trigger]` on
fan-outs, no prefixed abstraction names, global sends outside the allowlist. Assume it is naive
until proven otherwise. `keyboard.pd` in particular is 22 KB of heavy duplication.

Two files get looked at again during the rewrite, **for intent only**:

| File | Read during | For |
|---|---|---|
| `midiclock.pd` | Phase 5 (`u_tempo`) | Which MIDI realtime bytes went where, and when |
| `keyboard.pd` | Phase 6 (`m_keys`) | What the Organelle keyboard was mapped to |

Phases 5 and 6 are **rewrites, not ports**.

`three.aiff` is the sample `playfile.pd` loaded. Nothing in v0.2 uses it yet.

These are Pd 0.49 files — the plugdata rule in [CLAUDE.md](../../CLAUDE.md) still applies if you
open them.
