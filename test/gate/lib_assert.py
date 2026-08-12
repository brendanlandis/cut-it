#!/usr/bin/env python3
"""What every capture-reading analyser needs: the check tally, and the parser.

Imported, never run:

    import lib_assert as A
    A.check("the thing holds", ok, detail)
    sys.exit(1 if A.report() else 0)

⚠️ THE MODULE NAME HAS AN UNDERSCORE and every other file here has a hyphen.
That is not inconsistency -- a hyphen is not a legal Python identifier, so a
module that is IMPORTED cannot have one, while a script that is only ever RUN
can. The bench tooling loads its hyphenated neighbours through importlib for
exactly this reason; a library does not have to.

WHY IT EXISTS. Splitting the old phase 9 gate into three -- the map, the SP-404
and the Volca -- would otherwise have made three copies of the tally, the parser
and the window index. Three copies of a parser is how a fix reaches one gate and
not the other two, which is the same failure the documentation refactor existed
to remove.
"""
import re
import sys

fails = 0
total = 0
verbose = "-v" in sys.argv


def check(name, ok, detail=""):
    """One assertion. Prints PASS or FAIL, and the detail whenever it is useful
    -- always on a failure, and on a pass only under -v."""
    global fails, total
    total += 1
    if not ok:
        fails += 1
    print("  %s  %s%s" % ("PASS" if ok else "FAIL", name,
                          "" if (ok and not verbose) else ("   -- " + detail if detail else "")))
    return bool(ok)


def note(text):
    """Something worth printing that is NOT an assertion. ⛔ A note must never
    stand in for a check -- if it can be wrong, it should be a check."""
    print("  note  " + text)


def report():
    """Print the tally and return the failure count, for sys.exit.

    ⛔ IT PRINTS THE TOTAL, NOT ONLY THE FAILURES. A gate that says "0 failed"
    says nothing about whether it ran twelve checks or none -- and this suite has
    been split and re-split, so the count is what proves no assertion was lost on
    the way. Watch it go UP.
    """
    print("\n%d checks, %d failed" % (total, fails))
    return fails


# ---------------------------------------------------------------------------
_MIDI = re.compile(r"^(NOTEOUT|CTLOUT|PGMOUT|MIDIOUT):\s+(-?[\d.]+(?:\s+-?[\d.]+)*)$")
# ⛔ THIS MUST MATCH EVERY LABEL IN lib_drive.TAP_LABELS. A tap whose label has
# no pattern here produces lines this parser silently drops, and every assertion
# about that bus is then answered by an empty list rather than by a fact -- the
# first way a gate passes vacuously, arrived at by punctuation.
# ⚠️ MODE was added with test/bench/bench-tap.pd. No existing driver taps mode,
# so no capture written before that change can contain a MODE: line.
# ⚠️ AND LED, STATE, OLED, MIDIINGATE, MIDIOUTGATE ARE MOTHER'S NAMES, added for
# the g_led, u_init and g_oled gates. They are how a test reads back what a
# display surface or mother's MIDI gating was TOLD -- see lib_drive.TAP_LABELS,
# which this must always match.
# ⛔ PRESENCE WAS MISSING FOR A DAY AND THE WARNING ABOVE IS WHY IT MATTERED. The
# label went into TAP_LABELS with the hot-swap work and never arrived here, so
# every `PRESENCE:` line this parser was handed went silently on the floor --
# exactly the failure the comment above describes, applied to the very next label
# anyone added. presence-assert.py did not notice because it carries its own
# regex for that bus; the next gate would have.
# ⚠️ AND SL1..SL5 AND GOHOME ARRIVED WITH THE DEBUG PATCH, which draws with
# mother's screenLine names rather than through a g_oled it does not have. Same
# rule as every label above: it goes in both places or the lines are dropped in
# silence.
_BUS = re.compile(r"^(PARAM|DISP|ERR|TEMPO|START|STOP|MODE"
                  r"|LED|STATE|OLED|MIDIINGATE|MIDIOUTGATE|PRESENCE"
                  r"|SL[1-5]|GOHOME):\s+(.*)$")


def parse(cap, tag):
    """-> (marks in order, {mark: [(kind, values)]})

    `tag` is the driver's print label -- the MARK lines read "<tag>: MARK NAME".

    ⚠️ THE MARK IS THE ONLY THING SEPARATING ONE WINDOW FROM THE NEXT, and the
    driver fires it on its trigger's HIGHEST outlet so it lands in the capture
    BEFORE the actions it labels. Triggers fire right to left. Get that wrong and
    every assertion is reading the previous window's traffic.

    MIDI values come back as floats and bus traffic as a list of atoms, because
    that is what each is: a note number is arithmetic, a parameter name is not.
    """
    mark_re = re.compile(r"^%s:\s+MARK\s+(\S+)$" % re.escape(tag))
    order, by, cur = [], {}, "PRE"
    by[cur] = []
    for line in cap.splitlines():
        line = line.strip()
        m = mark_re.match(line)
        if m:
            cur = m.group(1); order.append(cur); by.setdefault(cur, [])
            continue
        m = _MIDI.match(line)
        if m:
            by[cur].append((m.group(1), [float(v) for v in m.group(2).split()]))
            continue
        m = _BUS.match(line)
        if m:
            by[cur].append((m.group(1), m.group(2).split()))
    return order, by


def windows(cap, tag, expected):
    """parse(), plus the bookkeeping check that the driver got all the way through.

    ⛔ WITHOUT THIS EVERY OTHER ASSERTION CAN PASS VACUOUSLY IN THE SAME WAY: a
    driver that died at window three leaves windows four onward empty, and an
    assertion of the form "no MIDI in this window" is then answered by an empty
    list rather than by a fact. Every gate here has at least one of those.
    """
    order, by = parse(cap, tag)
    check("the driver reached every window", len(order) >= expected,
          "saw %d of %d marks: %s" % (len(order), expected, " ".join(order)))
    return order, by


def require_capture(cap):
    """A gate handed an empty capture must FAIL, not report nothing and exit 0."""
    if not cap.strip():
        check("a capture was supplied", False, "stdin was empty")
        sys.exit(1)
    return cap
