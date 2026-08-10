#!/usr/bin/env python3
"""The SP-404's analyser -- ref/device/sp404.md. Reads a capture on stdin.

⛔ THE ONLY GATE HERE THAT TESTS A DEVICE IN BOTH DIRECTIONS, and it is the whole
argument for splitting the old phase 9 gate along the module axis rather than
along transmit/receive: a page says what its device does, and for this device
that is two paths, one rate limiter and a panic.

  transmit   all sixteen pads of bank A, the bank choosing the channel, matched
             note-offs, the 5 ms limiter from two sides, and All Notes Off
  receive    a press naming its bank and pad, a release that reaches param but
             not the display, and a channel outside the ten being ignored
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_assert as A                                         # noqa: E402

BANK_A = 33                     # bank A's Pd channel; each bank is the next one up
BANKS = list(range(33, 43))     # ten banks, A..J
# ⛔ NOT 47 + n. The pad map is four rows of four counting UPWARD from the bottom,
# so it runs 48..51, 44..47, 40..43, 36..39 -- and the 47+n formula that reads so
# plausibly is right for pads 1-4 and wrong for the other twelve.
PADS_A = [48, 49, 50, 51, 44, 45, 46, 47, 40, 41, 42, 43, 36, 37, 38, 39]


def run_asserts(cap):
    order, by = A.windows(cap, "SP404", 11)
    W = lambda k: by.get(k, [])
    ons = lambda k: [e for e in W(k) if e[0] == "NOTEOUT" and e[1][1] > 0]

    # --- from load ---------------------------------------------------------
    print("\n--- before u_map reads its table ---")
    # ⛔ Both directions at 300 and 700 ms. The gate this was split out of started
    # every window at 2400 because the code was ready at 2000, which is why it
    # could not see the boot race the hardware found. Item 234.
    A.check("⛔ a pad mapped at 300 ms ALREADY reaches the 404",
            bool(ons("EARLY-TX")), repr(W("EARLY-TX")))
    A.check("⛔ an incoming pad at 700 ms is ALREADY decoded",
            any(e[0] == "PARAM" and e[1] and e[1][0] == "sp-a1" for e in W("EARLY-RX")),
            repr(W("EARLY-RX")))

    # --- transmit ----------------------------------------------------------
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
    # ⚠️ CHANNEL-SPECIFIC ON PURPOSE. A note-off from an earlier window can land in
    # this one, 200 ms behind its own note-on; counting every off would count that.
    offs = [e for e in W("PADS-A")
            if e[0] == "NOTEOUT" and e[1][1] == 0 and e[1][2] == BANK_A]
    A.check("every bank-A note-on is matched by a note-off ON THE SAME CHANNEL",
            len(offs) == 16, "%d offs on channel %d" % (len(offs), BANK_A))

    # --- the rate limit ----------------------------------------------------
    print("\n--- the rate limit ---")
    n = len(ons("BURST"))
    A.check("⛔ 20 triggers in ONE logical instant emit exactly 1 -- it DROPS, never queues",
            n == 1, "emitted %d" % n)
    # ⚠️ The burst above proves it drops rather than queues, and NOTHING MORE. It
    # cannot see a disarmed limiter: [del 0] still defers to the next scheduler
    # tick, so the gate stays shut for the whole logical instant either way. Two
    # triggers 2 ms apart straddle the 5 ms interval and can.
    pair = len(ons("PAIR"))
    A.check("⛔ two triggers 2 ms apart emit exactly 1 -- the INTERVAL is real",
            pair == 1, "emitted %d" % pair)

    # --- receive -----------------------------------------------------------
    print("\n--- receive (only t_notein can reach this) ---")
    p = [e for e in W("RX-B5") if e[0] == "PARAM"]
    d = [e for e in W("RX-B5") if e[0] == "DISP"]
    A.check("a pad press names its BANK and PAD",
            bool(p) and p[0][1] == ["sp-b5", "90"], repr(p))
    # ⛔ TWO ROWS, AND BOTH FLOATS. g_oled formats a parameter value with
    # makefilename %g, which REFUSES a symbol -- so "sp-hit b5" is impossible and
    # the bank has to be its own numeric row.
    A.check("... and reports TWO stable disp rows, both FLOAT values",
            ["sp-bank", "2"] in [e[1] for e in d] and ["sp-pad", "5"] in [e[1] for e in d],
            repr(d))
    pr = [e for e in W("RX-RELEASE") if e[0] == "PARAM"]
    dr = [e for e in W("RX-RELEASE") if e[0] == "DISP"]
    A.check("a RELEASE reaches param", bool(pr) and pr[0][1] == ["sp-b5", "0"], repr(pr))
    A.check("... and does NOT reach disp",
            not [e for e in dr if e[1] and e[1][0] in ("sp-bank", "sp-pad")], repr(dr))
    pa = [e for e in W("RX-A1") if e[0] == "PARAM"]
    A.check("a different bank gives a different name",
            bool(pa) and pa[0][1] == ["sp-a1", "77"], repr(pa))
    da = [e for e in W("RX-A1") if e[0] == "DISP"]
    A.check("... and the BANK is now on the display too, not just on param",
            ["sp-bank", "1"] in [e[1] for e in da], repr(da))
    # only sp-* names are m_404's; other disp traffic in the window is unrelated
    A.check("⛔ a channel outside the 404's ten is IGNORED",
            not [e for e in W("RX-REJECT")
                 if e[0] in ("PARAM", "DISP") and e[1] and e[1][0].startswith("sp-")],
            repr(W("RX-REJECT")))

    # --- panic -------------------------------------------------------------
    print("\n--- panic ---")
    # ⚠️ SCOPED TO THIS DEVICE'S OWN CHANNEL BLOCK, because panic is a BUS
    # message and m_volca answers it too now -- correctly, on channel 49. An
    # unscoped sweep reads another device's All Notes Off as a bank of this one,
    # and the list this asserts is exact, so it went red the day the Volca
    # gained a panic path of its own.
    ch = sorted(int(e[1][2]) for e in W("PANIC")
                if e[0] == "CTLOUT" and e[1][1] == 123
                and 33 <= int(e[1][2]) <= 42)
    A.check("⛔ All Notes Off covers ALL TEN banks, not just bank A",
            ch == BANKS, "channels %s" % ch)


if __name__ == "__main__":
    run_asserts(A.require_capture(sys.stdin.read()))
    sys.exit(1 if A.report() else 0)
