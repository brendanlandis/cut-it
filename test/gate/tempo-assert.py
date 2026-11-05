#!/usr/bin/env python3
"""The tempo reference's analyser -- ref/module/tempo.md. Reads a capture on stdin.

It counts System Real-Time bytes (>= 248), which no SysEx byte can be, so the
Launchpad's grid frames can share the capture. Not lib_grid.parse, which skips
the bytes >= 248 this gate wants. Then tap tempo, from page 1's tap pad, and the
phone's tempo, read off the tempo bus.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_assert as A                                         # noqa: E402
import lib_pd                                                  # noqa: E402

UTEMPO = "Cut It/u_tempo.pd"
CLOCK, START, CONTINUE, STOP = 248, 250, 251, 252
PORTS = [1]                     # the Launchpad. Port 3 was the SP-404's, and gets nothing
PPQN = 24
BPM_LO, BPM_HI = 5, 600         # the LEGAL range, wider than knob 1's 10..500
TOLERANCE = 0.12                # +/- 12 % on a real-time count


def static_lint():
    """The two constants, read out of the patch.

    The wire cannot pin the bound: the pulse ceiling is 344 Hz
    (ref/module/tempo.md), so 5000 BPM saturates at ~338, and a clamp widened to
    650 BPM (260 Hz) sits inside a 12 % band on 240. Reading the literal makes the
    bound exact; the rate check proves the clamp is in the signal path.
    """
    print("\n=== A. the constants, checked by READING -- no Pd involved ===")
    src = lib_pd.read(UTEMPO)

    m = next((m for m in (re.match(r"^#X obj \d+ \d+ clip (-?[\d.]+) (-?[\d.]+);$", rec)
                          for rec in src) if m), None)
    if A.check("u_tempo still clamps the BPM with a literal [clip]", m is not None,
               "expected a 'clip <lo> <hi>' box in " + UTEMPO):
        lo, hi = float(m.group(1)), float(m.group(2))
        A.check("⛔ the legal range is EXACTLY %d..%d BPM" % (BPM_LO, BPM_HI),
                (lo, hi) == (float(BPM_LO), float(BPM_HI)),
                "the patch says %g..%g" % (lo, hi))

    mults = [m.group(1) for m in (re.match(r"^#X obj \d+ \d+ \* (\d+);$", rec)
                                  for rec in src) if m]
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
    order, by = A.windows(cap, "CLK", 27)
    W = lambda k: by.get(k, [])
    # Report only the ERR traffic: a window also holds every grid repaint byte.
    errs = lambda k: [e for e in W(k) if e[0] == "ERR"]

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

    # The stronger half: a ratio of two equal windows cancels the scheduler, and
    # a clock that ignored tempo would sit at 1.0 with both counts plausible.
    if counts["RATE-60"]:
        ratio = counts["RATE-120"] / float(counts["RATE-60"])
        A.check("⛔ halving the tempo halves the pulse rate",
                1.8 <= ratio <= 2.2, "ratio was %.3f (%d / %d)"
                % (ratio, counts["RATE-120"], counts["RATE-60"]))
    else:
        A.check("⛔ halving the tempo halves the pulse rate", False,
                "no pulses at all in the 60 BPM window")

    # An exact set: port 3 was the SP-404's until it left the rig (2026-11-04), and
    # whatever takes it next must not be handed a clock it never asked for.
    clock_ports = sorted({v[1] for v in rt(W("RATE-120"), byte=CLOCK)})
    A.check("⛔ the clock leaves on port 1 ALONE -- nothing on port 3",
            clock_ports == PORTS, "saw the clock on ports %s" % clock_ports)

    print("\n--- the clamp ---")
    # In the signal path; static_lint owns the bound.
    n = len(rt(W("TOO-HIGH"), byte=CLOCK, port=PORTS[0]))
    want = nominal(BPM_HI, 1.0)
    A.check("⛔ 5000 BPM reaches the wire CLAMPED -- the clip is in the signal path",
            want * (1 - TOLERANCE) <= n <= want * (1 + TOLERANCE),
            "counted %d in 1 s, wanted about %.0f. Unclamped saturates at ~338" % (n, want))
    A.check("... and it warns bpm-out-of-range on err", bool(warned(W("TOO-HIGH"))),
            repr(errs("TOO-HIGH")))
    A.check("0 BPM warns too -- the clamp reports at BOTH ends",
            bool(warned(W("TOO-LOW"))), repr(errs("TOO-LOW")))
    # [change] sits on the value, not the verdict: filtering the flag would warn
    # on a 500 and not on a 5 sent straight after it.
    A.check("⛔ an IN-RANGE tempo does not warn at all", not warned(W("IN-RANGE")),
            repr(errs("IN-RANGE")))

    print("\n--- the transport ---")
    A.check("start sends %d (FA)" % START, bool(rt(W("START"), byte=START)),
            repr(rt(W("START"))))
    A.check("stop sends %d (FC)" % STOP, bool(rt(W("STOP"), byte=STOP)),
            repr(rt(W("STOP"))))
    A.check("panic sends %d too" % STOP, bool(rt(W("PANIC"), byte=STOP)),
            repr(rt(W("PANIC"))))
    # ⛔ PANIC REACHES ONE MORE PORT THAN THE TRANSPORT DOES, and the pair of
    # checks below is the whole of that claim -- one of them alone would pass
    # over the bug in either direction. Item 279 measured realtime-out feeding
    # ports 1 and 3 only, so the Volca on port 4 kept sequencing through a panic
    # and nothing said so. It is fed now, from its own receive, by the panic
    # branch alone. ⚠️ EXACT PORT SETS, never "at least one": a fan-out that
    # accidentally handed the CLOCK to port 4 as well would satisfy any
    # non-zero test here and would be exactly the widening plan-v04 parks.
    # Port 3 is in neither set: it was the SP-404's.
    panic_ports = sorted({v[1] for v in rt(W("PANIC"), byte=STOP)})
    A.check("⛔ panic's STOP reaches ports 1 AND 4, and not 3", panic_ports == [1, 4],
            "saw ports %s -- port 4 is the Volca's DIN interface, item 279"
            % panic_ports)
    stop_ports = sorted({v[1] for v in rt(W("STOP"), byte=STOP)})
    A.check("⛔ ...and the plain transport STOP still reaches ONLY port 1",
            stop_ports == PORTS,
            "saw ports %s. Widening the clock and transport to more ports is a "
            "v0.4 sound question parked in plan-v04, NOT this" % stop_ports)
    # Continue resumes from a stored position, which nothing here has
    # (ref/module/tempo.md).
    cont = [v for m in order for v in rt(W(m), byte=CONTINUE)]
    A.check("⛔ Continue (%d) is NEVER sent" % CONTINUE, not cont, repr(cont))

    print("\n--- stop does not halt the clock ---")
    # The transport pauses the subscribers, not the timer: a synced device would
    # lose tempo the moment you stop.
    n = len(rt(W("AFTER-STOP"), byte=CLOCK, port=PORTS[0]))
    want = nominal(120, 1.5)
    A.check("⛔ the clock KEEPS RUNNING after a stop",
            want * (1 - TOLERANCE) <= n <= want * (1 + TOLERANCE),
            "counted %d in the 1.5 s after the stop, wanted about %.0f" % (n, want))

    print("\n--- tap tempo, from page 1's tap pad ---")
    bpms = lambda k: [float(e[1][0]) for e in W(k) if e[0] == "TEMPO" and e[1]]
    A.check("the first tap starts the count, and sets nothing", bpms("TAP-1") == [],
            bpms("TAP-1"))
    A.check("⛔ the second, 400 ms on, sets the tempo bus to 150", bpms("TAP-2") == [150.0],
            "the tempo bus carried %s -- nothing means the pad never reached u_tempo's "
            "timer through u_map's arrangement row" % bpms("TAP-2"))
    A.check("... and the third, 400 ms on again, 150", bpms("TAP-3") == [150.0], bpms("TAP-3"))
    A.check("⛔ a tap 2.5 s after the last starts over, and sets nothing",
            bpms("TAP-GAP") == [], bpms("TAP-GAP"))
    A.check("... the next, 600 ms on, counts from it alone: 100", bpms("TAP-AFTER") == [100.0],
            bpms("TAP-AFTER"))
    n = len(rt(W("TAP-AFTER"), byte=CLOCK, port=PORTS[0]))
    A.check("... and the clock follows it", 0 < n, "no pulses in that window")

    print("\n--- knob 1 is held at a tapped tempo ---")
    # Brendan, 2026-11-04: a tap or the phone sets the tempo, and knob 1 waits to
    # be turned through it, as c_steps' knobs 2 and 4 wait for the phone's.
    rows = lambda k: [e[1] for e in W(k) if e[0] == "DISP" and e[1][:1] == ["bpm"]]
    A.check("knob 1 is live before the taps -- turned through 120, 0.4 sets 100",
            bpms("KNOB-LIVE")[-1:] == [100.0], "the tempo bus carried %s" % bpms("KNOB-LIVE"))
    A.check("⛔ after the taps' 150, knob 1's next turn moves NOTHING -- it is held at 150",
            bpms("KNOB-HELD") == [], "the tempo bus carried %s: the knob jumped the tempo "
            "back to where it sits" % bpms("KNOB-HELD"))
    A.check("⛔ ...and its row says so: bpm 150 (105), the tap's tempo and the knob's own",
            rows("KNOB-HELD") == [["bpm", "150", "(105)"]], "bpm rows: %s" % rows("KNOB-HELD"))
    A.check("... and turned through 150 it is live again: 0.68 sets 170",
            bpms("KNOB-THROUGH") == [170.0] and rows("KNOB-THROUGH") == [["bpm", "170"]],
            "tempo %s, rows %s" % (bpms("KNOB-THROUGH"), rows("KNOB-THROUGH")))

    print("\n--- the phone's tempo ---")
    A.check("⛔ /cutit tempo 133 from the phone puts 133 on the tempo bus, through u_tempo",
            bpms("PHONE") == [133.0], "the tempo bus carried %s" % bpms("PHONE"))
    A.check("⛔ ...and holds knob 1 there too: 0.7 moves nothing, and reads bpm 133 (175)",
            bpms("KNOB-PHONE") == [] and rows("KNOB-PHONE") == [["bpm", "133", "(175)"]],
            "tempo %s, rows %s" % (bpms("KNOB-PHONE"), rows("KNOB-PHONE")))
    A.check("... 900 is 600, the legal range's top, before it reaches the bus",
            bpms("PHONE-HIGH") == [600.0], bpms("PHONE-HIGH"))
    A.check("... and a tempo that is no number sets nothing and is fail u_tempo bad-tempo",
            bpms("PHONE-BAD") == [] and [e[1] for e in errs("PHONE-BAD")]
            == [["fail", "u_tempo", "bad-tempo"]], "tempo %s err %s"
            % (bpms("PHONE-BAD"), errs("PHONE-BAD")))
    A.check("⛔ on page 2 cell 21 is a drum pad: two taps there set nothing",
            bpms("PAGE-2-TAPS") == [], bpms("PAGE-2-TAPS"))
    # The presence layer's routine reports share err in every window; these are the
    # tap's and the phone's path.
    other = [e for k in ("TAP-1", "TAP-2", "TAP-3", "TAP-GAP", "TAP-AFTER", "PHONE",
                         "PHONE-HIGH", "PAGE-2-TAPS") for e in errs(k)
             if e[1][1:2] and e[1][1] in ("u_tempo", "u_map", "u_net", "g_grid")
             and "bpm-out-of-range" not in " ".join(e[1])]
    A.check("nothing from u_map, u_tempo, u_net or g_grid reaches err while tapping and from "
            "the phone", not other, other)

    return A.report()


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
