#!/usr/bin/env python3
"""The tempo reference's analyser -- ref/module/tempo.md. Reads a capture on stdin.

u_tempo is the instrument's master reference and NOT its clock: it owns the BPM,
the pulse oscillator that MIDI clock is cut from, and the transport. Every part
that needs a beat owns a c_clock instance aligned to it.

WHAT WAS UNTESTED UNTIL THIS EXISTED. Every other gate asserts on messages, and
u_tempo's most important output is not a message -- it is a RATE on a wire that
nothing in the patch reads back. A clock running at half speed, or on one port
instead of two, or one that stopped when the transport did, would be silent on
the Mac and obvious only at a gig.

⛔ IT COUNTS SYSTEM REAL-TIME BYTES, WHICH ARE UNAMBIGUOUS. Anything >= 248 in a
MIDI stream is System Real-Time; SysEx data bytes are 0-127 and its framing is
240 and 247. So the Launchpad's 332-byte grid frames can share this capture
without a single byte of them ever being mistaken for clock.

⚠️ Do NOT reach for lib_grid.parse here. That one deliberately SKIPS bytes >= 248
while reassembling SysEx, because they are legal inside a SysEx stream. This gate
wants exactly what that one discards.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_assert as A                                         # noqa: E402

UTEMPO = "Cut It/u_tempo.pd"
CLOCK, START, CONTINUE, STOP = 248, 250, 251, 252
PORTS = [1, 3]                  # 1 = the Launchpad, 3 = the SP-404
PPQN = 24
BPM_LO, BPM_HI = 5, 600         # the LEGAL range, wider than knob 1's 10..500
TOLERANCE = 0.12                # +/- 12 % on a real-time count


# ----------------------------------------------------------- the static lint
def static_lint():
    """The two constants, read out of the patch. No Pd, about a millisecond.

    ⛔ THIS EXISTS BECAUSE THE RATE CHECK BELOW CANNOT DO IT. Measured: the pulse
    ceiling is about 344 Hz -- threshold~ decrements its dead time once per DSP
    block, so 44100/64/2 is the floor of two blocks per pulse. 600 BPM is 240 Hz
    and 5000 BPM SATURATES at ~338 rather than reaching 2000. So a clamp widened
    to 5000 is caught easily, and a clamp widened to 650 (260 Hz, inside a 12 %
    band on 240) is NOT. The wire simply cannot resolve it.

    Pinning the literal here makes the bound exact, and the rate check keeps the
    job it is uniquely good at: proving the clamp is in the SIGNAL PATH rather
    than merely present in the file. Two checks, two different failure modes.
    """
    print("\n=== A. the constants, checked by READING -- no Pd involved ===")
    src = open(UTEMPO).read()

    m = re.search(r"^#X obj \d+ \d+ clip (-?[\d.]+) (-?[\d.]+);$", src, re.M)
    if A.check("u_tempo still clamps the BPM with a literal [clip]", m is not None,
               "expected a 'clip <lo> <hi>' box in " + UTEMPO):
        lo, hi = float(m.group(1)), float(m.group(2))
        A.check("⛔ the legal range is EXACTLY %d..%d BPM" % (BPM_LO, BPM_HI),
                (lo, hi) == (float(BPM_LO), float(BPM_HI)),
                "the patch says %g..%g" % (lo, hi))

    # BPM / 60 * 24 -- the 24 is PPQN, and it is the one number in this file that
    # every synced device agrees on by standard rather than by choice.
    mults = re.findall(r"^#X obj \d+ \d+ \* (\d+);$", src, re.M)
    A.check("⛔ the pulse multiplier is %d -- PPQN, and it is a STANDARD" % PPQN,
            str(PPQN) in mults, "the [* n] boxes in the file are %s" % mults)


def nominal(bpm, seconds):
    """Pulses expected on ONE port over a window. BPM / 60 * PPQN is the rate."""
    return bpm / 60.0 * PPQN * seconds


def rt(win, byte=None, port=None):
    """System Real-Time bytes in a window, optionally filtered."""
    out = []
    for kind, v in win:
        if kind != "MIDIOUT" or len(v) < 2 or v[0] < 248:
            continue
        if byte is not None and v[0] != byte:
            continue
        if port is not None and v[1] != port:
            continue
        out.append(v)
    return out


def warned(win):
    return [e for e in win
            if e[0] == "ERR" and "bpm-out-of-range" in " ".join(e[1])]


def main():
    static_lint()

    cap = A.require_capture(sys.stdin.read())
    print("\n=== B. the clock, measured on the wire ===")
    order, by = A.windows(cap, "CLK", 13)
    W = lambda k: by.get(k, [])
    # ⚠️ Report the ERR traffic only, never the whole window. A tempo window holds
    # every grid repaint byte too, and a failing check that dumps 900 of them
    # buries the one line that explains it.
    errs = lambda k: [e for e in W(k) if e[0] == "ERR"]

    # ---- the rate ---------------------------------------------------------
    print("\n--- 24 PPQN, measured on the wire ---")
    counts = {}
    for mark, bpm, seconds in (("RATE-120", 120, 2.0), ("RATE-60", 60, 2.0)):
        n = len(rt(W(mark), byte=CLOCK, port=PORTS[0]))
        counts[mark] = n
        want = nominal(bpm, seconds)
        lo, hi = want * (1 - TOLERANCE), want * (1 + TOLERANCE)
        A.check("⛔ %d PPQN at %d BPM -- %d pulses in %.0f s" % (PPQN, bpm, want, seconds),
                lo <= n <= hi,
                "counted %d, wanted %.0f (%.0f..%.0f)" % (n, want, lo, hi))

    # ⛔ THE RATIO IS THE STRONGER HALF. An absolute count depends on a real-time
    # scheduler and a machine that might be busy; the ratio between two windows
    # of the same length cancels all of that, and a clock that ignored tempo
    # entirely would sit at 1.0 with both counts individually plausible.
    if counts["RATE-60"]:
        ratio = counts["RATE-120"] / float(counts["RATE-60"])
        A.check("⛔ halving the tempo halves the pulse rate",
                1.8 <= ratio <= 2.2, "ratio was %.3f (%d / %d)"
                % (ratio, counts["RATE-120"], counts["RATE-60"]))
    else:
        A.check("⛔ halving the tempo halves the pulse rate", False,
                "no pulses at all in the 60 BPM window")

    # ⚠️ TWO PORTS, COUNTED SEPARATELY. A fan-out that quietly lost one would look
    # perfect on the other, and the failure on hardware is one device following
    # the tempo while the other does not.
    per_port = [len(rt(W("RATE-120"), byte=CLOCK, port=p)) for p in PORTS]
    A.check("the clock leaves on BOTH MIDI ports, not one",
            per_port[0] > 0 and per_port[0] == per_port[1],
            "port 1 saw %d, port 3 saw %d" % tuple(per_port))

    # ---- the clamp, proven on the wire ------------------------------------
    print("\n--- the clamp ---")
    # ⚠️ THIS PROVES THE CLAMP IS IN THE SIGNAL PATH, not what its bound is -- the
    # static lint above owns the bound, because the wire cannot resolve it. See
    # static_lint's note on the ~344 Hz ceiling.
    n = len(rt(W("TOO-HIGH"), byte=CLOCK, port=PORTS[0]))
    want = nominal(BPM_HI, 1.0)
    A.check("⛔ 5000 BPM reaches the wire CLAMPED -- the clip is in the signal path",
            want * (1 - TOLERANCE) <= n <= want * (1 + TOLERANCE),
            "counted %d in 1 s, wanted about %.0f. Unclamped saturates at ~338" % (n, want))
    A.check("... and it warns bpm-out-of-range on err", bool(warned(W("TOO-HIGH"))),
            repr(errs("TOO-HIGH")))
    A.check("0 BPM warns too -- the clamp reports at BOTH ends",
            bool(warned(W("TOO-LOW"))), repr(errs("TOO-LOW")))
    # ⛔ [change] SITS ON THE VALUE, NOT ON THE VERDICT, and getting that backwards
    # was a real bug: filtering the out-of-range FLAG means 500 warns and a 5 sent
    # straight after it does not, because the flag never changed.
    A.check("⛔ an IN-RANGE tempo does not warn at all", not warned(W("IN-RANGE")),
            repr(errs("IN-RANGE")))

    # ---- the transport ----------------------------------------------------
    print("\n--- the transport ---")
    A.check("start sends %d (FA)" % START, bool(rt(W("START"), byte=START)),
            repr(rt(W("START"))))
    A.check("stop sends %d (FC)" % STOP, bool(rt(W("STOP"), byte=STOP)),
            repr(rt(W("STOP"))))
    A.check("panic sends %d too" % STOP, bool(rt(W("PANIC"), byte=STOP)),
            repr(rt(W("PANIC"))))
    # ⛔ PANIC REACHES A THIRD PORT AND THE TRANSPORT DOES NOT, and the pair of
    # checks below is the whole of that claim -- one of them alone would pass
    # over the bug in either direction. Item 279 measured realtime-out feeding
    # ports 1 and 3 only, so the Volca on port 4 kept sequencing through a panic
    # and nothing said so. It is fed now, from its own receive, by the panic
    # branch alone. ⚠️ EXACT PORT SETS, never "at least one": a fan-out that
    # accidentally handed the CLOCK to port 4 as well would satisfy any
    # non-zero test here and would be exactly the widening plan-v04 parks.
    panic_ports = sorted({v[1] for v in rt(W("PANIC"), byte=STOP)})
    A.check("⛔ panic's STOP reaches ports 1, 3 AND 4", panic_ports == [1, 3, 4],
            "saw ports %s -- port 4 is the Volca's DIN interface, item 279"
            % panic_ports)
    stop_ports = sorted({v[1] for v in rt(W("STOP"), byte=STOP)})
    A.check("⛔ ...and the plain transport STOP still reaches ONLY 1 and 3",
            stop_ports == [1, 3],
            "saw ports %s. Widening the clock and transport to all four is a "
            "v0.4 sound question parked in plan-v04, NOT this" % stop_ports)
    # ⛔ CONTINUE IS NEVER SENT, ANYWHERE IN THE RUN. A device that receives FB
    # resumes from where it was rather than from the top, and this instrument has
    # no concept of a resume position -- so sending it would be a lie about state
    # that only shows up as a sequencer starting in the wrong place.
    cont = [v for m in order for v in rt(W(m), byte=CONTINUE)]
    A.check("⛔ Continue (%d) is NEVER sent" % CONTINUE, not cont, repr(cont))

    # ---- and the thing that reads as a bug until you know it ---------------
    print("\n--- stop does not halt the clock ---")
    # ⛔ THE TRANSPORT PAUSES THE SUBSCRIBERS, IT DOES NOT CLEAR THE TIMER. A
    # running phasor nobody reads is silent, and halting it is the consumer's
    # business -- the same contract c_clock states. If this ever goes red the
    # symptom on hardware is every synced device losing tempo the moment you stop.
    n = len(rt(W("AFTER-STOP"), byte=CLOCK, port=PORTS[0]))
    want = nominal(120, 1.5)
    A.check("⛔ the clock KEEPS RUNNING after a stop",
            want * (1 - TOLERANCE) <= n <= want * (1 + TOLERANCE),
            "counted %d in the 1.5 s after the stop, wanted about %.0f" % (n, want))

    return A.report()


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
