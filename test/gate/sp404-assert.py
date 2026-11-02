#!/usr/bin/env python3
"""The SP-404's analyser -- ref/device/sp404.md. Reads a capture on stdin.

The device in both directions:

  transmit   all sixteen pads of bank A, the bank choosing the channel, matched
             note-offs, the trigger budget from two sides, and All Notes Off
  receive    a press naming its bank and pad, a press and its release each
             drawing ONE row -- u_map's, never m_404's -- and a channel outside
             the ten being ignored
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_assert as A                                         # noqa: E402

BANK_A = 33                     # bank A's Pd channel; each bank is the next one up
BANKS = list(range(33, 43))     # ten banks, A..J
# Not 47 + n: the pads are four rows of four counting upward from the bottom row,
# so 47 + n is right for pads 1-4 only.
PADS_A = [48, 49, 50, 51, 44, 45, 46, 47, 40, 41, 42, 43, 36, 37, 38, 39]


def run_asserts(cap):
    order, by = A.windows(cap, "SP404", 11)
    W = lambda k: by.get(k, [])
    ons = lambda k: [e for e in W(k) if e[0] == "NOTEOUT" and e[1][1] > 0]

    print("\n--- before u_map reads its table ---")
    # Item 234: windows that open before the code is ready.
    A.check("⛔ a pad mapped at 300 ms ALREADY reaches the 404",
            bool(ons("EARLY-TX")), repr(W("EARLY-TX")))
    A.check("⛔ an incoming pad at 700 ms is ALREADY decoded",
            any(e[0] == "PARAM" and e[1] and e[1][0] == "sp-a1" for e in W("EARLY-RX")),
            repr(W("EARLY-RX")))

    print("\n--- transmit ---")
    got = [int(e[1][0]) for e in ons("PADS-A")]
    if not A.check("⛔ ALL SIXTEEN pads of bank A map to the right notes", got == PADS_A,
                   "want %s got %s" % (PADS_A, got)) and len(got) == len(PADS_A):
        bad = [i + 1 for i, (a, b) in enumerate(zip(got, PADS_A)) if a != b]
        A.note("pads wrong: %s -- if this is 5..16 only, it is the 47+n error" % bad)
    A.check("every bank-A pad went out on channel %d" % BANK_A,
            all(e[1][2] == BANK_A for e in ons("PADS-A")), repr(ons("PADS-A")))
    c1 = ons("PADS-C")
    A.check("bank C pad 1 is note 48 on CHANNEL 35 (bank sets the channel)",
            bool(c1) and c1[0][1][0] == 48 and c1[0][1][2] == 35, repr(c1))
    # Channel-specific: an earlier window's note-off can land here, 200 ms late.
    offs = [e for e in W("PADS-A")
            if e[0] == "NOTEOUT" and e[1][1] == 0 and e[1][2] == BANK_A]
    A.check("every bank-A note-on is matched by a note-off ON THE SAME CHANNEL",
            len(offs) == 16, "%d offs on channel %d" % (len(offs), BANK_A))

    print("\n--- the trigger budget ---")
    # Sixteen at once is a sequencer step with every drum track on.
    n = len(ons("BURST"))
    A.check("⛔ 20 triggers in ONE logical instant emit exactly 16 -- a whole step "
            "passes, the excess DROPS", n == 16, "emitted %d" % n)
    # The burst proves drops-not-queues and nothing more; only triggers a real
    # millisecond apart can see the refill.
    note = lambda k, p: len([e for e in ons(k) if int(e[1][0]) == p])
    A.check("the drain in the refill window is a whole step too -- 16 of pad 1",
            note("REFILL", PADS_A[0]) == 16, "pad 1 (note %d) emitted %d"
            % (PADS_A[0], note("REFILL", PADS_A[0])))
    A.check("⛔ drained, a trigger 2 ms later is DROPPED -- the budget refills at "
            "200 a second, not at once", note("REFILL", PADS_A[1]) == 0,
            "pad 2 (note %d) emitted %d" % (PADS_A[1], note("REFILL", PADS_A[1])))
    A.check("... and one 12 ms later passes -- the bucket does refill",
            note("REFILL", PADS_A[2]) == 1,
            "pad 3 (note %d) emitted %d" % (PADS_A[2], note("REFILL", PADS_A[2])))

    print("\n--- receive (only t_notein can reach this) ---")
    p = [e for e in W("RX-B5") if e[0] == "PARAM"]
    A.check("a pad press names its BANK and PAD",
            bool(p) and p[0][1] == ["sp-b5", "90"], repr(p))
    # One row per event, u_map's raw row (item 317): m_404 posts nothing to disp,
    # and every sp-* row in the window is counted.
    sp = lambda k: [e[1] for e in W(k) if e[0] == "DISP" and e[1] and e[1][0].startswith("sp-")]
    A.check("⛔ ... and draws ONE row -- u_map's sp-b5 90, no sp-pad or sp-bank",
            sp("RX-B5") == [["sp-b5", "90"]], repr(sp("RX-B5")))
    pr = [e for e in W("RX-RELEASE") if e[0] == "PARAM"]
    A.check("a RELEASE reaches param", bool(pr) and pr[0][1] == ["sp-b5", "0"], repr(pr))
    # u_map's raw row carries the value, so the release updates the press's row
    # to 0 in place.
    A.check("... and its row is the SAME one at velocity 0 -- sp-b5 0",
            sp("RX-RELEASE") == [["sp-b5", "0"]], repr(sp("RX-RELEASE")))
    pa = [e for e in W("RX-A1") if e[0] == "PARAM"]
    A.check("a different bank gives a different name",
            bool(pa) and pa[0][1] == ["sp-a1", "77"], repr(pa))
    A.check("... and that name is the row -- sp-a1 77, and only that",
            sp("RX-A1") == [["sp-a1", "77"]], repr(sp("RX-A1")))
    # only sp-* names are m_404's; other disp traffic in the window is unrelated
    A.check("⛔ a channel outside the 404's ten is IGNORED",
            not [e for e in W("RX-REJECT")
                 if e[0] in ("PARAM", "DISP") and e[1] and e[1][0].startswith("sp-")],
            repr(W("RX-REJECT")))

    print("\n--- panic ---")
    # Scoped to this device's channels: m_volca answers panic too, on 49.
    ch = sorted(int(e[1][2]) for e in W("PANIC")
                if e[0] == "CTLOUT" and e[1][1] == 123
                and 33 <= int(e[1][2]) <= 42)
    A.check("⛔ All Notes Off covers ALL TEN banks, not just bank A",
            ch == BANKS, "channels %s" % ch)


if __name__ == "__main__":
    run_asserts(A.require_capture(sys.stdin.read()))
    sys.exit(1 if A.report() else 0)
