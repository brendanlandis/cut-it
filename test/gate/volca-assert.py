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
    order, by = A.windows(cap, "VOLCA", 4)
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

    # ⚠️ EVERY ONE OF THE THREE, ON ONE CHANNEL. Asserting the channel on the note
    # alone would let a CC on the wrong channel through, and the failure on
    # hardware is a Volca that ignores half of what it is sent.
    wrong = [e for k in ("VOLCA-CC", "VOLCA-NOTE", "VOLCA-PROG") for e in W(k)
             if e[0] in ("NOTEOUT", "CTLOUT", "PGMOUT") and e[1][-1] != CHANNEL]
    A.check("nothing at all leaves m_volca on another channel", not wrong, repr(wrong))


if __name__ == "__main__":
    run_asserts(A.require_capture(sys.stdin.read()))
    sys.exit(1 if A.report() else 0)
