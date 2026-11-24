#!/usr/bin/env python3
"""The FM-1's analyser -- ref/device/fm1.md. Reads a capture on stdin.

⛔ [pgmout] is 1-based on its inlet and the wire is 0-based, so m_fm1 adds one
and the device gets the number the map asked for (item 228). It reads as an
off-by-one bug without this check beside it.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_assert as A                                         # noqa: E402

CHANNEL = 49                    # the FM-1's Pd channel -- device 4, (4-1)*16+1: its channel 1
EFFECTS = CHANNEL + 1            # its effects' controllers go to its channel 2


def run_asserts(cap):
    print("\n=== m_fm1 ===")
    order, by = A.windows(cap, "FM1", 8)
    W = lambda k: by.get(k, [])
    ons = lambda k: [e for e in W(k) if e[0] == "NOTEOUT" and e[1][1] > 0]

    # Before u_map reads its table (item 234).
    A.check("⛔ a mapped control at 300 ms already reaches the FM-1",
            any(e[0] == "CTLOUT" for e in W("EARLY")), repr(W("EARLY")))

    cc = [e for e in W("FM1-CC") if e[0] == "CTLOUT"]
    A.check("⛔ a CC carries its controller, one channel up: the FM-1's effect channel",
            bool(cc) and cc[0][1][1:] == [41.0, float(EFFECTS)], repr(cc))

    nt = ons("FM1-NOTE")
    A.check("a note reaches the FM-1 on channel %d" % CHANNEL,
            bool(nt) and nt[0][1][0] == 48 and nt[0][1][2] == CHANNEL, repr(nt))

    pg = [e for e in W("FM1-PROG") if e[0] == "PGMOUT"]
    A.check("⛔ pgmout gets arg+1, so the WIRE value is the number asked for (item 228)",
            bool(pg) and pg[0][1] == [6.0, float(CHANNEL)], repr(pg))

    # fm1-key, because fm1-note cannot be a keyboard (ref/device/fm1.md):
    # here the release comes from the key, as velocity 0.
    on = ons("FM1-KEY-ON")
    A.check("a key press reaches the FM-1 as a note-on with its velocity",
            len(on) == 1 and on[0][1][0] == 60 and on[0][1][1] == 100
            and on[0][1][2] == CHANNEL,
            "wanted one noteout 60 100 %d, got %s" % (CHANNEL, on))

    # Every other destination gates on non-zero; this one must let 0 through.
    offs = [e for e in W("FM1-KEY-OFF")
            if e[0] == "NOTEOUT" and e[1][1] == 0]
    A.check("⛔ a key RELEASE reaches it as a note-off -- velocity 0, same note",
            len(offs) == 1 and offs[0][1][0] == 60 and offs[0][1][2] == CHANNEL,
            "wanted one noteout 60 0 %d, got %s. Without this the note-on has no "
            "partner and the FM-1 sounds forever -- which is exactly what "
            "makenote was protecting against before this path bypassed it"
            % (CHANNEL, W("FM1-KEY-OFF")))

    # The only check that tells a key from makenote, since both put an on and then
    # an off on the wire. The held window straddles makenote's 200 ms.
    held = [e for e in W("FM1-KEY-HELD")
            if e[0] == "NOTEOUT" and e[1][0] == 60]
    A.check("⛔ a HELD key stays down -- nothing releases it on a timer",
            not held,
            "note 60 saw %s while the key was still held. A fixed duration means "
            "a held key releases itself, which is exactly why fm1-note cannot "
            "be a keyboard" % (held,))

    # Scoped to this channel, so another device layer answering panic on its
    # own channels (m_404 did, on ten, until the SP-404 left) cannot pass it.
    # The FM-1 ignores All Notes Off, so panic is a note-off for every note and
    # sustain off (ref/device/fm1.md).
    offs = [e[1] for e in W("FM1-PANIC")
            if e[0] == "NOTEOUT" and e[1][-1] == float(CHANNEL)]
    A.check("⛔ panic sends a note-off for every note, 0 to 127, on the FM-1's channel",
            offs == [[float(n), 0.0, float(CHANNEL)] for n in range(128)],
            "wanted noteout 0..127 at velocity 0 on %d, got %d: %s ... The key path "
            "bypasses makenote, so this is the only thing that can silence a stuck note"
            % (CHANNEL, len(offs), offs[:3]))

    pan = [e for e in W("FM1-PANIC")
           if e[0] == "CTLOUT" and e[1][-1] == float(CHANNEL)]
    A.check("⛔ ... and sustain off -- CC 64 at 0, on the same channel",
            len(pan) == 1 and pan[0][1] == [0.0, 64.0, float(CHANNEL)],
            "wanted one ctlout 0 64 %d, got %s. A held pedal keeps every note "
            "sounding through its note-off" % (CHANNEL, pan))

    # Not FM1-PANIC, where another device layer's panic would be its own.
    wrong = [e for k in ("FM1-CC", "FM1-NOTE", "FM1-PROG",
                         "FM1-KEY-ON", "FM1-KEY-HELD", "FM1-KEY-OFF")
             for e in W(k)
             if e[0] in ("NOTEOUT", "PGMOUT") and e[1][-1] != CHANNEL
             or e[0] == "CTLOUT" and e[1][-1] != EFFECTS]
    A.check("nothing at all leaves m_fm1 on a channel that isn't one of its two",
            not wrong, repr(wrong))


if __name__ == "__main__":
    run_asserts(A.require_capture(sys.stdin.read()))
    sys.exit(1 if A.report() else 0)
