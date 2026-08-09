#!/usr/bin/env python3
"""What a step can assert about itself, as DATA rather than as code.

Imported by run.py. A predicate is a dict in a step's meta, so the vacuity lint
in bench-gen.py can read it before a patch is ever generated, and so the whole
thing survives into the result file -- "want 20..22, got 0" a month later is
worth more than "failed".

⛔ THE WINDOW ENDS AT THE FIRED LINE, AND THAT IS NOT ARBITRARY. bench-gen sends
a step's actions off the trigger's high outlets and the "--- step N fired ---"
line off outlet 0, LAST, precisely so the line cannot arrive before the thing it
describes. So everything a step caused is already in the window by the time the
marker closing it shows up.
"""
import re

KINDS = ("print", "ratio", "bus", "bus-count", "bus-not", "oled", "all")

# ⛔ THE BUS KINDS READ WHAT lib_assert's PARSER ALREADY MATCHES. bench-tap.pd
# emits lib_drive.TAP_LABELS, which is the same map every headless gate's driver
# taps with, so there is one parser for both. Two would be how a fix reaches one
# and not the other.
_BUS_LINE = re.compile(r"(?:^|\s)(PARAM|DISP|ERR|TEMPO|START|STOP|MODE):\s+(.*?)\s*$")

# The OLED as u_mother-stub decodes it: g_oled writes rows through oscOut, and
# the stub's oled-decode subpatch turns /oled/gPrintln into the eight cnv rows
# drawn on the panel. That decode is what makes a screen assertion possible at
# all -- Pd cannot ask an OLED what it is showing, but what it was TOLD to show
# is completely knowable.
_OLED_ANY = re.compile(r"/oled/(gPrintln|gClear|gFlip)\b(.*?)\s*$")


class BadSpec(Exception):
    """⛔ A predicate that cannot be understood is a FAILURE, never a skip and
    never a silent pass. A typo in a kind name would otherwise disable an
    assertion while leaving the step looking checked."""


def _numbers(window, name):
    """Every value Pd printed under `[print NAME]`, in order.

    ⚠️ THE LABEL IS ANCHORED AT A WORD BOUNDARY, not searched loosely. `BEATS`
    appears inside `M-BEATS`, `C1-BEATS-ratio-1` and `C2-BEATS-ratio-1.5`, so a
    loose match on the Launchpad bench's `BEATS` would silently read the tempo
    bench's counters as well and average three clocks into one number.
    """
    rx = re.compile(r"(?:^|\s)%s:\s+(-?[\d.]+)\s*$" % re.escape(name))
    out = []
    for line in window:
        m = rx.search(line.strip())
        if m:
            out.append(float(m.group(1)))
    return out


def _bus_lines(window, bus):
    """Every tap line for one bus, as the text that followed the label."""
    out = []
    for line in window:
        m = _BUS_LINE.search(line)
        if m and m.group(1) == bus:
            out.append(m.group(2))
    return out


def _oled_text(args_str):
    """The WORDS of one gPrintln, with the geometry discarded.

    ⛔ AND DISCARDING IT IS THE WHOLE POINT. A gPrintln reads
    `/oled/gPrintln iiiiiss 3 2 12 24 1 43 %` -- x, y, size, and only then the
    text. Matching a predicate against the raw line would let `12` be satisfied
    by a FONT SIZE, so a screen showing nothing of the sort would pass. The
    typetag says how many trailing atoms are symbols, and g_oled builds that
    typetag itself with one letter per word, so counting its `s` letters is
    exactly as authoritative as the message.
    """
    atoms = args_str.split()
    if not atoms:
        return ""
    tag, args = atoms[0], atoms[1:]
    if tag and set(tag) <= set("ifs"):
        n = tag.count("s")
        return " ".join(args[len(args) - n:]) if n else ""
    # No recognisable typetag: keep it, so a malformed frame shows up in the
    # `got` rather than vanishing.
    return " ".join(atoms)


def _oled_rows(window):
    """The rows of the LAST COMPLETE FRAME, not of the whole window.

    ⛔ A WINDOW HOLDS SEVERAL FRAMES AND THEY CONTRADICT EACH OTHER. g_oled
    repaints on a [metro 100] and brackets every frame with gClear ... gFlip, so
    a window opened around one step spans the repaint boundary: the frames
    before the step still show what was there, the frames after show the result.
    Evaluated together, display step 3 reported BOTH `grain 12` and the previous
    step's `43 %` -- and its whole point is that the % must be gone. Measured
    exactly that way before this existed.

    ⚠️ COMPLETE means gClear ... gFlip. A half-written frame at the end of the
    window is the repaint we interrupted, not the screen.
    """
    frames, cur, closed = [], None, []
    for line in window:
        m = _OLED_ANY.search(line)
        if not m:
            continue
        kind, args = m.group(1), m.group(2)
        if kind == "gClear":
            cur = []
        elif kind == "gFlip":
            if cur is not None:
                closed.append(cur)
            cur = None
        elif kind == "gPrintln" and cur is not None:
            t = _oled_text(args)
            if t:
                cur.append(t)
    frames = closed
    if frames:
        return frames[-1]
    # No complete frame: fall back to every gPrintln seen, so the failure
    # message shows what DID arrive rather than claiming the screen was blank.
    out = []
    for line in window:
        m = _OLED_ANY.search(line)
        if m and m.group(1) == "gPrintln":
            t = _oled_text(m.group(2))
            if t:
                out.append(t)
    return out


def _sample(lines, n=4):
    if not lines:
        return "(nothing on that bus in this window)"
    head = "; ".join(lines[:n])
    return head + (" ... (%d more)" % (len(lines) - n) if len(lines) > n else "")


def _one(spec, window):
    kind = spec.get("kind")
    if kind not in KINDS:
        raise BadSpec("unknown predicate kind %r -- known kinds are %s"
                      % (kind, ", ".join(KINDS)))

    if kind == "print":
        name = spec["name"]
        lo, hi = spec["min"], spec["max"]
        got = _numbers(window, name)
        want = "%s between %g and %g" % (name, lo, hi)
        if not got:
            # ⛔ NOTHING PRINTED IS A FAILURE, NOT AN EMPTY PASS. This is the
            # single most likely way this predicate would go vacuous: the
            # counter never fired, the window was read too early, or DSP is off
            # -- and "no number" answered as "no number outside the range" is
            # exactly the shape of a gate that lies.
            return False, want, "%s never printed" % name
        v = got[-1]
        return lo <= v <= hi, want, "%s = %g" % (name, v)

    if kind in ("bus", "bus-count", "bus-not"):
        bus = spec["bus"]
        lines = _bus_lines(window, bus)
        if kind == "bus":
            need = spec["has"]
            missing = [s for s in need if not any(s in ln for ln in lines)]
            return (not missing,
                    "%s carries %s" % (bus, " and ".join(repr(s) for s in need)),
                    ("missing %s -- saw: %s"
                     % (", ".join(repr(s) for s in missing),
                        _sample(lines))) if missing else _sample(lines))
        if kind == "bus-count":
            # ⛔ EXACTLY n, NEVER "at least". A count that has drifted is the
            # failure this project keeps catching, and "at least" cannot catch
            # it: the whole point of tempo's double-5000 step is that the SECOND
            # one must be silent, and "one or more alerts" is satisfied by two.
            match, n = spec["match"], spec["n"]
            hits = [ln for ln in lines if match in ln]
            return (len(hits) == n,
                    "exactly %d %s line(s) carrying %r" % (n, bus, match),
                    "%d: %s" % (len(hits), _sample(hits)))
        absent = spec["absent"]
        present = [s for s in absent if any(s in ln for ln in lines)]
        return (not present,
                "%s carries none of %s" % (bus, ", ".join(repr(s) for s in absent)),
                ("saw %s" % ", ".join(repr(s) for s in present)) if present
                else "none of them, in %d %s line(s)" % (len(lines), bus))

    if kind == "oled":
        rows = _oled_rows(window)
        blob = " | ".join(rows)
        has = spec.get("has", [])
        has_not = spec.get("has_not", [])
        # ⛔ has_row IS EXACT AND has IS A SUBSTRING, AND THE DIFFERENCE MATTERS.
        # g_oled draws a parameter as two rows, the name and the value, so the
        # stale-unit bug shows up as a VALUE ROW reading `12 %` where it should
        # read `12`. A substring test for `12` is satisfied by both. An exact row
        # is also independent of what else is on screen, which a screen showing
        # up to five parameters at once very much is.
        has_row = spec.get("has_row", [])
        missing = ([s for s in has if s not in blob]
                   + [s for s in has_row if s not in rows])
        present = [s for s in has_not if s in blob]
        want = "the screen shows %s" % (
            ", ".join([repr(s) for s in has]
                      + ["a row reading exactly %r" % s for s in has_row]) or "-")
        if has_not:
            want += " and NOT %s" % ", ".join(repr(s) for s in has_not)
        if not rows:
            # ⛔ AN EMPTY SCREEN IS A FAILURE, NOT A SATISFIED has_not. This is
            # the one way an OLED predicate goes vacuous: nothing was drawn, so
            # every "must not contain" is trivially true and the step passes
            # having proved nothing at all.
            return False, want, "the OLED wrote nothing in this window"
        bad = []
        if missing:
            bad.append("missing " + ", ".join(repr(s) for s in missing))
        if present:
            bad.append("should not be there: " + ", ".join(repr(s) for s in present))
        return not bad, want, ("; ".join(bad) + " -- saw: " + blob) if bad else blob

    if kind == "ratio":
        a, b = spec["a"], spec["b"]
        want_r, tol = spec["want"], spec.get("tol", 0.1)
        va, vb = _numbers(window, a), _numbers(window, b)
        want = "%s / %s = %g +/- %g" % (a, b, want_r, tol)
        if not va or not vb:
            return False, want, "%s printed %s, %s printed %s" % (
                a, va or "nothing", b, vb or "nothing")
        if vb[-1] == 0:
            # ⚠️ A ZERO DENOMINATOR IS THE DSP-OFF SIGNATURE, and it must fail
            # loudly rather than raise: under -noaudio every count reads 0,
            # which looks exactly like a dead clock.
            return False, want, "%s = 0 -- a dead clock, or DSP is off" % b
        r = va[-1] / vb[-1]
        return abs(r - want_r) <= tol, want, "%s / %s = %g / %g = %.3f" % (
            a, b, va[-1], vb[-1], r)

    raise BadSpec(kind)


def evaluate(spec, window):
    """-> (ok, want, got). `all` is how a negative assertion gets its witness."""
    if spec.get("kind") == "all":
        parts = spec["of"]
        if not parts:
            raise BadSpec("an `all` with nothing in it asserts nothing")
        results = [_one(p, window) for p in parts]
        ok = all(r[0] for r in results)
        return (ok,
                " AND ".join(r[1] for r in results),
                " / ".join(r[2] for r in results))
    return _one(spec, window)
