#!/usr/bin/env python3
"""What every capture-reading analyzer needs: the check tally, and the parser.

Imported, never run:

    import lib_assert as A
    A.check("the thing holds", ok, detail)
    sys.exit(1 if A.report() else 0)
"""
import re
import sys

import lib_drive

fails = 0
total = 0
verbose = "-v" in sys.argv


def check(name, ok, detail=""):
    """One assertion. Prints PASS or FAIL, and the detail whenever it is useful
    -- always on a failure, and on a pass only under -v. The detail may be any
    value: a list handed in raw must not turn a failing check into a traceback."""
    global fails, total
    detail = str(detail) if detail is not None else ""
    total += 1
    if not ok:
        fails += 1
    print("  %s  %s%s" % ("PASS" if ok else "FAIL", name,
                          "" if (ok and not verbose) else ("   -- " + detail if detail else "")))
    return bool(ok)


def note(text):
    """Something worth printing that is not an assertion. If it can be wrong,
    it should be a check."""
    print("  note  " + text)


def report():
    """Print the tally and return the failure count, for sys.exit. The total is
    what proves no assertion went missing; "0 failed" alone could mean none ran.
    """
    print("\n%d checks, %d failed" % (total, fails))
    return fails


# ---------------------------------------------------------------------------
# KITOUT is t_kit's: the drums c_steps sends c_kit, pad and velocity.
_MIDI = re.compile(r"^(NOTEOUT|CTLOUT|PGMOUT|MIDIOUT|KITOUT):\s+(-?[\d.]+(?:\s+-?[\d.]+)*)$")
# Built from lib_drive's labels, never typed: a label with no pattern here is a
# bus whose lines are silently dropped.
_BUS = re.compile(r"^(%s):\s+(.*)$" % lib_drive.TAP_LABEL_RE)


def parse(cap, tag):
    """-> (marks in order, {mark: [(kind, values)]})

    `tag` is the driver's print label -- the MARK lines read "<tag>: MARK NAME".
    Only the MARK separates one window from the next, so lib_drive prints it
    before the actions it labels.

    MIDI values come back as floats and bus traffic as a list of atoms.
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
    """parse(), plus the check that the driver reached every window.

    A driver that died early leaves the later windows empty, and every "nothing
    in this window" assertion then passes. Exact, not "at least", so a count
    that falls behind its driver is caught too.
    """
    order, by = parse(cap, tag)
    check("the driver reached every window", len(order) == expected,
          "saw %d of %d marks: %s" % (len(order), expected, " ".join(order)))
    return order, by


def require_capture(cap):
    """A gate handed an empty capture must FAIL, not report nothing and exit 0."""
    if not cap.strip():
        check("a capture was supplied", False, "stdin was empty")
        sys.exit(1)
    return cap
