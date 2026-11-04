#!/usr/bin/env python3
"""The Volca's analyser -- ref/device/volca.md. Reads a capture on stdin.

⛔ [pgmout] is 1-based on its inlet and the wire is 0-based, so m_volca adds one
and the device gets the number the map asked for (item 228). It reads as an
off-by-one bug without this check beside it.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_assert as A                                         # noqa: E402

CHANNEL = 49                    # the Volca's Pd channel -- device 4, (4-1)*16+1


def run_asserts(cap):
    print("\n=== m_volca ===")
    order, by = A.windows(cap, "VOLCA", 8)
    W = lambda k: by.get(k, [])
    ons = lambda k: [e for e in W(k) if e[0] == "NOTEOUT" and e[1][1] > 0]

    # Before u_map reads its table (item 234).
    A.check("⛔ a mapped control at 300 ms already reaches the Volca",
            any(e[0] == "CTLOUT" for e in W("EARLY")), repr(W("EARLY")))

    cc = [e for e in W("VOLCA-CC") if e[0] == "CTLOUT"]
    A.check("CC carries controller and channel",
            bool(cc) and cc[0][1][1:] == [41.0, float(CHANNEL)], repr(cc))

    nt = ons("VOLCA-NOTE")
    A.check("a note reaches the Volca on channel %d" % CHANNEL,
            bool(nt) and nt[0][1][0] == 48 and nt[0][1][2] == CHANNEL, repr(nt))

    pg = [e for e in W("VOLCA-PROG") if e[0] == "PGMOUT"]
    A.check("⛔ pgmout gets arg+1, so the WIRE value is the number asked for (item 228)",
            bool(pg) and pg[0][1] == [6.0, float(CHANNEL)], repr(pg))

    # volca-key, because volca-note cannot be a keyboard (ref/device/volca.md):
    # here the release comes from the key, as velocity 0.
    on = ons("VOLCA-KEY-ON")
    A.check("a key press reaches the Volca as a note-on with its velocity",
            len(on) == 1 and on[0][1][0] == 60 and on[0][1][1] == 100
            and on[0][1][2] == CHANNEL,
            "wanted one noteout 60 100 %d, got %s" % (CHANNEL, on))

    # Every other destination gates on non-zero; this one must let 0 through.
    offs = [e for e in W("VOLCA-KEY-OFF")
            if e[0] == "NOTEOUT" and e[1][1] == 0]
    A.check("⛔ a key RELEASE reaches it as a note-off -- velocity 0, same note",
            len(offs) == 1 and offs[0][1][0] == 60 and offs[0][1][2] == CHANNEL,
            "wanted one noteout 60 0 %d, got %s. Without this the note-on has no "
            "partner and the Volca sounds forever -- which is exactly what "
            "makenote was protecting against before this path bypassed it"
            % (CHANNEL, W("VOLCA-KEY-OFF")))

    # The only check that tells a key from makenote, since both put an on and then
    # an off on the wire. The held window straddles makenote's 200 ms.
    held = [e for e in W("VOLCA-KEY-HELD")
            if e[0] == "NOTEOUT" and e[1][0] == 60]
    A.check("⛔ a HELD key stays down -- nothing releases it on a timer",
            not held,
            "note 60 saw %s while the key was still held. A fixed duration means "
            "a held key releases itself, which is exactly why volca-note cannot "
            "be a keyboard" % (held,))

    # Scoped to this channel, so another device layer answering panic on its
    # own channels (m_404 did, on ten, until the SP-404 left) cannot pass it.
    pan = [e for e in W("VOLCA-PANIC")
           if e[0] == "CTLOUT" and e[1][-1] == float(CHANNEL)]
    A.check("⛔ panic sends All Notes Off -- CC 123, on the Volca's channel",
            len(pan) == 1 and pan[0][1] == [0.0, 123.0, float(CHANNEL)],
            "wanted one ctlout 0 123 %d, got %s. The key path bypasses makenote, "
            "so this is the only thing that can silence a stuck note"
            % (CHANNEL, pan))

    # Not VOLCA-PANIC, where another device layer's panic would be its own.
    wrong = [e for k in ("VOLCA-CC", "VOLCA-NOTE", "VOLCA-PROG",
                         "VOLCA-KEY-ON", "VOLCA-KEY-HELD", "VOLCA-KEY-OFF")
             for e in W(k)
             if e[0] in ("NOTEOUT", "CTLOUT", "PGMOUT") and e[1][-1] != CHANNEL]
    A.check("nothing at all leaves m_volca on another channel", not wrong, repr(wrong))


if __name__ == "__main__":
    run_asserts(A.require_capture(sys.stdin.read()))
    sys.exit(1 if A.report() else 0)
