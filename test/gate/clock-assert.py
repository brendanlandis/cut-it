#!/usr/bin/env python3
"""c_clock's analyser -- ref/module/tempo.md. Reads a capture on stdin.

⛔ WHAT THIS IS FOR. c_clock is the file that makes "poly-tempo" mean something,
and its two creation arguments had never been read by anything but a human off a
bench print. u_tempo has had a gate since Phase 7; the page that names it covers
BOTH files, and the analyser next door mentions c_clock only in a comment.

⚠️ IT HAS ITS OWN PARSER, AND THAT IS NOT DUPLICATION FOR ITS OWN SAKE.
lib_assert.parse reads BUSES, and c_clock deliberately writes to none: its output
is four outlets, which only a [print] in a harness can see. The mark protocol is
the shared one -- same "<tag>: MARK NAME" lines, same window semantics -- so what
is local here is one regex, not a second idea of what a window is.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_assert as A                                         # noqa: E402

# ⛔ THE NUMBER OF WINDOWS clock-assert-drive-gen.py's SEQ OPENS.
MARKS = 11

# The counting window, and the tempo driven into it. Kept beside each other
# because the expected beat count is entirely a function of the two.
RATE_S = 6.0
BPM = 120.0

# ⚠️ THE SAME TOLERANCE tempo-assert USES, and for the same reason: these are
# real-time measurements on a machine that might be busy, and threshold~ resolves
# to a DSP block rather than to a sample.
TOLERANCE = 0.15

_LINE = re.compile(r"^(CLK[ABC]-[A-Z]+|ERR):\s*(.*)$")
_MARK = re.compile(r"^CLK:\s+MARK\s+(\S+)$")


def split(cap):
    """-> (marks in order, {mark: [(label, atoms)]}), with the bookkeeping check.

    ⛔ THE BOOKKEEPING CHECK IS THE POINT OF DOING THIS HERE RATHER THAN INLINE.
    Half the assertions below are counts, and a count in a window the driver
    never reached is 0 -- which is indistinguishable from a clock that stopped,
    and reads as a confident verdict either way.
    """
    order, by, cur = [], {"PRE": []}, "PRE"
    for line in cap.splitlines():
        line = line.strip()
        m = _MARK.match(line)
        if m:
            cur = m.group(1); order.append(cur); by.setdefault(cur, [])
            continue
        m = _LINE.match(line)
        if m:
            by[cur].append((m.group(1), m.group(2).split()))
    A.check("the driver reached every window", len(order) >= MARKS,
            "saw %d of %d marks: %s" % (len(order), MARKS, " ".join(order)))
    return order, by


def run_asserts(cap):
    order, by = split(cap)
    W = lambda k: by.get(k, [])
    n = lambda k, label: len([1 for lab, _ in W(k) if lab == label])
    vals = lambda k, label: [v for lab, v in W(k) if lab == label]
    every = lambda label: [v for k in by for lab, v in by[k] if lab == label]

    # ---- ⛔ THE RATIO ARGUMENT, WHICH NOTHING HAS EVER READ ----------------
    print("\n--- creation arg 1: the ratio to master tempo ---")
    want = BPM / 60.0 * RATE_S                      # 12 beats at ratio 1
    lo, hi = want * (1 - TOLERANCE), want * (1 + TOLERANCE)
    a = n("RATE", "CLKA-BEAT")
    b = n("RATE", "CLKB-BEAT")
    c = n("RATE", "CLKC-BEAT")

    A.check("ratio 1 at %d BPM -- %.0f beats in %.0f s" % (BPM, want, RATE_S),
            lo <= a <= hi, "counted %d, wanted %.0f (%.0f..%.0f)" % (a, want, lo, hi))
    A.check("ratio 1.5 at %d BPM -- %.0f beats in %.0f s"
            % (BPM, want * 1.5, RATE_S),
            lo * 1.5 <= b <= hi * 1.5,
            "counted %d, wanted %.0f" % (b, want * 1.5))

    # ⛔ THE RATIO IS THE STRONGER HALF, exactly as in tempo-assert. An absolute
    # count depends on a real-time scheduler; the ratio between two instances
    # measured over the SAME window cancels all of that -- and an instance that
    # ignored its ratio argument entirely would sit at 1.0 with both counts
    # individually plausible.
    A.check("⛔ the two instances run at 1.5x each other -- THIS is poly-tempo",
            a and 1.35 <= b / float(a) <= 1.65,
            "ratio was %s (%d / %d)" % ("%.3f" % (b / float(a)) if a else "n/a", b, a))

    # ---- bad arguments are corrected immediately and reported late --------
    print("\n--- bad arguments: corrected at load, reported at 2 s ---")
    A.check("⛔ a bad ratio is CORRECTED to 1, not left dead",
            a and 0.85 <= c / float(a) <= 1.15,
            "the c_clock 0 0 instance counted %d beats against %d -- a ratio of "
            "0 would have left phasor~ at 0 Hz and the clock silent" % (c, a))

    errs = [" ".join(v) for v in every("ERR")]
    A.check("a bad ratio raises warn c_clock bad-ratio exactly once",
            errs.count("warn c_clock bad-ratio") == 1,
            "saw %d of them in %s" % (errs.count("warn c_clock bad-ratio"), errs))
    A.check("a bad beats-per-bar raises warn c_clock bad-beats exactly once",
            errs.count("warn c_clock bad-beats") == 1,
            "saw %d of them in %s" % (errs.count("warn c_clock bad-beats"), errs))
    # ⚠️ AND THE TWO GOOD INSTANCES SAY NOTHING. Without this, a file that warned
    # on every instance whatever its arguments would pass both checks above.
    A.check("⛔ the two well-formed instances raise nothing at all",
            len(errs) == 2, "the error bus carried %d messages: %s" % (len(errs), errs))

    # ---- creation arg 2: beats per bar ------------------------------------
    # ⛔ READ OFF THE BEAT-NUMBER OUTLET, NOT OFF A BEATS-PER-BAR RATIO. The
    # first version of this gate divided the beat count by the bar count, and it
    # was wrong in a way worth recording: a 6-second window at 120 BPM holds 12
    # beats, which is 1.5 bars at 8 beats to the bar, so the bar count was 1 and
    # the "measurement" was 12. A ratio needs many whole bars to mean anything.
    # The number outlet gives the same fact EXACTLY and in any window: it walks
    # 1..bpb and nothing else, whatever the tempo and however long you watch.
    print("\n--- creation arg 2: beats per bar ---")
    for label, bpb in (("A", 8), ("B", 4)):
        nums = sorted({v[0] for v in vals("RATE", "CLK%s-NUM" % label)}, key=int)
        A.check("instance %s counts 1..%d and nothing else" % (label, bpb),
                nums == [str(k) for k in range(1, bpb + 1)],
                "saw %s" % nums)
    nums_c = sorted({v[0] for v in vals("RATE", "CLKC-NUM")}, key=int)
    A.check("⛔ a bad beats-per-bar is CORRECTED to 4",
            nums_c == ["1", "2", "3", "4"],
            "the c_clock 0 0 instance counted %s" % nums_c)

    # ---- the bar bang, and where it falls ---------------------------------
    # ⚠️ EXACT, AND WINDOW-LENGTH INDEPENDENT. The bar bang and the beat number
    # are cut from the same [t f f f], so a bar must fall on beat 1 and on no
    # other beat -- which makes "how many bars" a question with an exact answer
    # in any window: as many as there were beat 1s.
    print("\n--- the bar outlet falls on beat 1, and only there ---")
    for label in ("A", "B", "C"):
        ones = len([v for v in vals("RATE", "CLK%s-NUM" % label) if v == ["1"]])
        bars = n("RATE", "CLK%s-BAR" % label)
        A.check("instance %s bars exactly once per beat 1" % label,
                bars == ones and bars > 0,
                "%d bar bang(s) against %d beat-1s" % (bars, ones))

    # ---- ⛔ VALUES FIRST, EVENT LAST ---------------------------------------
    # The bar chain hangs off the trigger's RIGHT outlet and the beat bang off
    # its left, so beat-in-bar is already updated when the beat arrives. A
    # consumer that reads the number on the beat gets THIS beat, not the last
    # one -- which is a one-cord distinction that would otherwise be invisible.
    seq = [lab for lab, _ in W("RATE") if lab in ("CLKA-NUM", "CLKA-BEAT")]
    pairs = list(zip(seq[::2], seq[1::2]))
    A.check("⛔ the beat NUMBER is published before the beat BANG, every time",
            bool(pairs) and all(p == ("CLKA-NUM", "CLKA-BEAT") for p in pairs),
            "the interleaving was %s" % seq[:8])

    # ---- the signal outlet ------------------------------------------------
    # ⚠️ SAMPLED ACROSS MORE THAN ONE FULL CYCLE, so "it sweeps" is a fact about
    # the ramp rather than about where the samples happened to land.
    print("\n--- outlet 0: the raw beat phase, as a signal ---")
    ph = [float(v[0]) for v in vals("PHASE", "CLKA-PHASE") if v]
    A.check("the snapshot burst read the signal outlet at all", len(ph) >= 10,
            "got %d snapshots -- without these the two checks below are vacuous"
            % len(ph))
    A.check("every sample is inside a phasor's range, 0 to 1",
            bool(ph) and all(0.0 <= p < 1.0 for p in ph),
            "range was %s..%s" % (min(ph) if ph else "-", max(ph) if ph else "-"))
    A.check("...and it RAMPS -- the sweep reaches both ends",
            bool(ph) and min(ph) < 0.15 and max(ph) > 0.85,
            "range was %.3f..%.3f, which is not a full ramp"
            % (min(ph), max(ph)) if ph else "no samples")

    # ---- ⛔ START RESETS, STOP DOES NOT HALT -------------------------------
    print("\n--- the transport ---")
    after = n("AFTER-STOP", "CLKA-BEAT")
    want_stop = BPM / 60.0 * 2.0
    A.check("⛔ stop does NOT halt the clock",
            want_stop * (1 - TOLERANCE) <= after <= want_stop * (1 + TOLERANCE),
            "counted %d beats in the 2 s after a stop, wanted about %.0f. "
            "Halting is the consumer's business -- the same reason u_tempo keeps "
            "sending clock while stopped" % (after, want_stop))

    # ⛔ THE RESET BEAT ARRIVES ~10 ms AFTER THE start MESSAGE, NOT ON THE NEXT
    # TICK, and that is why this reads the RESTART window rather than the one
    # after it. start sets the pulse counter to 23, so the very next pulse --
    # one forty-eighth of a beat later -- rolls it to 0 and fires beat 1
    # immediately. The first version of this gate looked in AFTER-RESTART and
    # found beat 2, having missed the reset by 200 ms.
    restart = vals("RESTART", "CLKA-NUM")
    A.check("⛔ start RESETS -- it fires beat 1 at once, mid-bar, and nothing else",
            restart == [["1"]],
            "the RESTART window held %s. The start reset is the only thing "
            "aligning instances to each other and to master; after it, equal "
            "frequencies from the same arithmetic hold the alignment alone"
            % (restart or "nothing at all"))
    A.check("...and the bar bang goes with it",
            n("RESTART", "CLKA-BAR") == 1,
            "%d bar bang(s) in the window that reset to beat 1"
            % n("RESTART", "CLKA-BAR"))
    A.check("...and the count carries on from there",
            vals("AFTER-RESTART", "CLKA-NUM")[:1] == [["2"]],
            "the beat after the reset was %s"
            % (vals("AFTER-RESTART", "CLKA-NUM")[:1] or "nothing"))

    A.note("windows reached: %s" % " ".join(order))
    A.note("beats in the %.0f s window: A=%d B=%d C=%d" % (RATE_S, a, b, c))


if __name__ == "__main__":
    run_asserts(A.require_capture(sys.stdin.read()))
    sys.exit(1 if A.report() else 0)
