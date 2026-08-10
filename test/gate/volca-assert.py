#!/usr/bin/env python3
"""The Volca's analyser -- ref/device/volca.md. Reads a capture on stdin.

Three destinations and one channel. The gate is small because m_volca is: it
takes a mapped value and puts it on the wire, and the only place that is
non-obvious is pgmout.

⛔ [pgmout] IS 1-BASED ON ITS INLET AND THE WIRE IS 0-BASED. m_volca adds one, so
the number that reaches the device is the number the map asked for. Item 228, and
it is the kind of fact that reads as an off-by-one bug to anyone who finds it
later without this check standing next to it.
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

    # ⛔ Before u_map reads its table. Not a fact about the Volca -- a fact about
    # whether this gate's schedule is derived from the implementation it tests.
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

    # ---- ⛔ volca-key: A REAL NOTE-ON AND A REAL NOTE-OFF -------------------
    # volca-note cannot be a keyboard. Its `<arg>` is the PITCH -- fixed, one per
    # row -- and on a keyboard the KEY is the pitch; and its duration is a fixed
    # 200 ms, so A HELD KEY WOULD RELEASE ITSELF. Here the release comes from the
    # key, as velocity 0, and that is the entire difference.
    on = ons("VOLCA-KEY-ON")
    A.check("a key press reaches the Volca as a note-on with its velocity",
            len(on) == 1 and on[0][1][0] == 60 and on[0][1][1] == 100
            and on[0][1][2] == CHANNEL,
            "wanted one noteout 60 100 %d, got %s" % (CHANNEL, on))

    # ⛔ THE HALF THAT IS EASY TO LOSE, and losing it leaves the Volca droning
    # for the rest of the set. Every other destination gates on non-zero, because
    # a release means nothing to them; this one must let 0 through.
    offs = [e for e in W("VOLCA-KEY-OFF")
            if e[0] == "NOTEOUT" and e[1][1] == 0]
    A.check("⛔ a key RELEASE reaches it as a note-off -- velocity 0, same note",
            len(offs) == 1 and offs[0][1][0] == 60 and offs[0][1][2] == CHANNEL,
            "wanted one noteout 60 0 %d, got %s. Without this the note-on has no "
            "partner and the Volca sounds forever -- which is exactly what "
            "makenote was protecting against before this path bypassed it"
            % (CHANNEL, W("VOLCA-KEY-OFF")))

    # ⛔ A HELD KEY MUST NOT RELEASE ITSELF, and this is the only check here that
    # can tell a keyboard from a makenote. Both put a note-on and then a note-off
    # on the wire, so the two MESSAGES say nothing about who produced the off --
    # the first version of this check asserted that and passed with makenote
    # spliced into the path. The HELD window opens 150 ms after the press and stays open past
    # volca-note's fixed 200 ms -- it has to STRADDLE that duration, not follow it -- and nothing is sent in it.
    held = [e for e in W("VOLCA-KEY-HELD")
            if e[0] == "NOTEOUT" and e[1][0] == 60]
    A.check("⛔ a HELD key stays down -- nothing releases it on a timer",
            not held,
            "note 60 saw %s while the key was still held. A fixed duration means "
            "a held key releases itself, which is exactly why volca-note cannot "
            "be a keyboard" % (held,))

    # ---- ⛔ PANIC -----------------------------------------------------------
    # Nothing here could leave a note sounding until the key path existed --
    # makenote always scheduled its own off -- so the Volca needed no panic and
    # had none. Bypassing makenote brings the risk back.
    # ⚠️ SCOPED TO THIS DEVICE'S CHANNEL, because panic is a BUS message and
    # m_404 answers it too -- correctly, on all ten of its banks. An unscoped
    # sweep here reads the 404's ten All Notes Off as this file's.
    pan = [e for e in W("VOLCA-PANIC")
           if e[0] == "CTLOUT" and e[1][-1] == float(CHANNEL)]
    A.check("⛔ panic sends All Notes Off -- CC 123, on the Volca's channel",
            len(pan) == 1 and pan[0][1] == [0.0, 123.0, float(CHANNEL)],
            "wanted one ctlout 0 123 %d, got %s. The key path bypasses makenote, "
            "so this is the only thing that can silence a stuck note"
            % (CHANNEL, pan))

    # ⚠️ EVERY ONE OF THEM, ON ONE CHANNEL. Asserting the channel on the note
    # alone would let a CC on the wrong channel through, and the failure on
    # hardware is a Volca that ignores half of what it is sent.
    # ⚠️ VOLCA-PANIC IS DELIBERATELY NOT IN THIS LIST. panic is a bus message,
    # so that window legitimately carries m_404's ten channels as well, and a
    # sweep including it would report correct 404 behaviour as a Volca fault.
    wrong = [e for k in ("VOLCA-CC", "VOLCA-NOTE", "VOLCA-PROG",
                         "VOLCA-KEY-ON", "VOLCA-KEY-HELD", "VOLCA-KEY-OFF")
             for e in W(k)
             if e[0] in ("NOTEOUT", "CTLOUT", "PGMOUT") and e[1][-1] != CHANNEL]
    A.check("nothing at all leaves m_volca on another channel", not wrong, repr(wrong))


if __name__ == "__main__":
    run_asserts(A.require_capture(sys.stdin.read()))
    sys.exit(1 if A.report() else 0)
