#!/usr/bin/env python3
"""What a step can assert about itself, as data. Imported by run.py.

A predicate is a dict in a step's meta, so bench-gen.py's vacuity lint can read
it before a patch is generated, and it survives into the result file: "want
20..22, got 0" a month later says more than "failed".

The window ends at the fired line, which bench-gen sends last, so everything a
step caused synchronously is already in it.
"""
import os
import re
import subprocess
import sys

# One list of tap labels, shared with every headless gate's driver and parser.
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "gate"))
import lib_drive                                                # noqa: E402

KINDS = ("print", "ratio", "bus", "bus-count", "bus-not", "oled",
         "osc", "osc-rate", "file", "all")

# Which kinds can be judged with no console. Every kind but `file` reads lines
# Pd printed, and paper mode has none: against an empty window they would fail
# a working rig.
OFFLINE_KINDS = ("file",)

# Which kinds need the OSC mirror, which only the Mac target has (u_net
# repointed at a socket the runner binds). On the device the predicate is
# skipped and a person still judges the step. Derived from the kind, never
# listed per step.
MIRROR_KINDS = ("osc", "osc-rate")

# Built from lib_drive.TAP_LABELS, as bench-tap.pd is, so the bus kinds read
# every label it emits. A label with no pattern is dropped without an error.
_BUS_LINE = re.compile(
    r"(?:^|\s)(%s):\s+(.*?)\s*$" % lib_drive.TAP_LABEL_RE)

# The OLED as u_mother-stub decodes it: g_oled writes rows through oscOut, and
# the stub turns /oled/gPrintln into the panel's eight rows.
_OLED_ANY = re.compile(r"/oled/(gPrintln|gClear|gFlip)\b(.*?)\s*$")


class BadSpec(Exception):
    """A predicate that cannot be understood fails, never skips or passes: a
    typo in a kind would otherwise disable an assertion and leave the step
    looking checked."""


def _numbers(window, name):
    """Every value Pd printed under `[print NAME]`, in order. The label is
    anchored, so `BEATS` does not also read a counter named `M-BEATS`."""
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
    """The words of one gPrintln, with the geometry discarded.

    `/oled/gPrintln iiiiiss 3 2 12 24 1 43 %` is x, y, size and then the text,
    so a raw match would let `12` be satisfied by a font size. g_oled builds
    the typetag with one letter per word, so its `s` count is exact.
    """
    atoms = args_str.split()
    if not atoms:
        return ""
    tag, args = atoms[0], atoms[1:]
    if tag and set(tag) <= set("ifs"):
        n = tag.count("s")
        return " ".join(args[len(args) - n:]) if n else ""
    # No recognizable typetag: keep it, so a malformed frame shows up in the
    # `got` rather than vanishing.
    return " ".join(atoms)


def _oled_rows(window):
    """The rows of the last complete frame (gClear ... gFlip), not the whole
    window: g_oled repaints on a [metro 100], so a window holds frames from
    before the step and after it, and they contradict each other. A
    half-written frame at the end is the repaint we interrupted.
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


def _one(spec, window, ctx=None):
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
            # Nothing printed fails: the counter never fired, the window was
            # read too early, or DSP is off.
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
            # Exactly n, never "at least": tempo's second 5000 must be silent,
            # and "one or more alerts" is satisfied by two.
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
        # has_row is exact and has a substring: the stale-unit bug is a value
        # row reading `12 %` where it should read `12`, and `12` is in both.
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
            # An empty screen fails rather than satisfying has_not, which
            # nothing drawn would make trivially true.
            return False, want, "the OLED wrote nothing in this window"
        bad = []
        if missing:
            bad.append("missing " + ", ".join(repr(s) for s in missing))
        if present:
            bad.append("should not be there: " + ", ".join(repr(s) for s in present))
        return not bad, want, ("; ".join(bad) + " -- saw: " + blob) if bad else blob

    if kind in ("osc", "osc-rate"):
        addr = spec["addr"]
        lines = [ln.split(":", 1)[1].strip() for ln in window
                 if ln.startswith("OSC: ")]
        mine = [ln[len(addr):].strip() for ln in lines if ln.startswith(addr)]
        if kind == "osc":
            need = spec.get("has", [])
            absent = spec.get("has_not", [])
            if not mine and "has" in spec:
                # No datagram where traffic was asserted fails. A purely
                # negative spec is satisfied by silence, which is safe only
                # because the lint refuses a bare has_not.
                return (False, "%s carries %s" % (addr, need or "traffic"),
                        "nothing arrived on %s" % addr)
            blob = " | ".join(mine)
            missing = [s for s in need if s not in blob]
            present = [s for s in absent if s in blob]
            want = "%s carries %s" % (addr, ", ".join(map(repr, need)) or "traffic")
            if absent:
                want += " and never %s" % ", ".join(map(repr, absent))
            bad = []
            if missing:
                bad.append("missing " + ", ".join(map(repr, missing)))
            if present:
                bad.append("should not be there: " + ", ".join(map(repr, present)))
            return not bad, want, ("; ".join(bad) + " -- saw: " + blob) if bad else blob
        # osc-rate: the coalescer's job is that a flood does not become a
        # flood on the wire.
        secs = spec.get("over", 1.0)
        hz = len(mine) / float(secs)
        return (hz <= spec["max_hz"],
                "%s stays at or under %g Hz" % (addr, spec["max_hz"]),
                "%d packets in %gs = %.1f Hz" % (len(mine), secs, hz))

    if kind == "file":
        path = spec["path"]
        # A timestamp is read on the device, never off the fetched copy:
        # fetch-state.sh's scp has no -p, so the local mtime is the fetch.
        # Epoch seconds, since the device runs UTC and the Mac local time.
        if spec.get("remote"):
            rpath = spec["remote"]
            host = os.environ.get("ORGANELLE", "root@organelle.local")
            p = subprocess.run(
                ["ssh", "-o", "ConnectTimeout=8", "-o", "BatchMode=yes", host,
                 "date +%%s -r %s 2>/dev/null || echo missing" % rpath],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            got = p.stdout.decode().strip()
            want = "%s has a NEW timestamp on the device" % os.path.basename(rpath)
            if not got.isdigit():
                return False, want, "could not stat %s on %s (%r)" % (rpath, host, got)
            ref = spec["newer_than"]
            if ref == "step-start":
                ref = (ctx or {}).get("step_start", 0)
            age = int(got) - int(ref)
            return (int(got) > int(ref), want,
                    "device mtime is %+ds relative to the start of this step"
                    % age)
        # The runner fetches it: the instrument writes to /sdcard/cut-it-state/,
        # outside the patch folder.
        if spec.get("fetch") == "state":
            rc = subprocess.run(["./tools/fetch-state.sh"],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.STDOUT).returncode
            if rc != 0:
                return (False, "the file %s" % path,
                        "tools/fetch-state.sh failed (rc=%d) -- the device may "
                        "be unreachable, which is not a verdict about the "
                        "patch" % rc)
        try:
            body = open(path, encoding="utf-8", errors="replace").read()
        except OSError as e:
            return False, "the file %s" % path, "could not read it: %s" % e
        if "contains" in spec:
            want = spec["contains"]
            return (want in body, "%s contains %r" % (os.path.basename(path), want),
                    (body.strip() or "(empty)")[:200])
        if "newer_than" in spec:
            # An unchanged timestamp means saveState never arrived; the file
            # may legitimately be empty, so its contents cannot say.
            try:
                mtime = os.path.getmtime(path)
            except OSError as e:
                return False, "a fresh %s" % path, "could not stat it: %s" % e
            ref = spec["newer_than"]
            # `step-start` is resolved by the runner: the question is whether
            # this step rewrote the file, and a literal timestamp in the table
            # would stop meaning that on a second run.
            if ref == "step-start":
                ref = (ctx or {}).get("step_start", 0)
            return (mtime > ref,
                    "%s has a NEW timestamp" % os.path.basename(path),
                    "mtime %s, needed newer than %s"
                    % (int(mtime), int(ref)))
        raise BadSpec("a `file` predicate needs `contains` or `newer_than`")

    if kind == "ratio":
        a, b = spec["a"], spec["b"]
        want_r, tol = spec["want"], spec.get("tol", 0.1)
        va, vb = _numbers(window, a), _numbers(window, b)
        want = "%s / %s = %g +/- %g" % (a, b, want_r, tol)
        if not va or not vb:
            return False, want, "%s printed %s, %s printed %s" % (
                a, va or "nothing", b, vb or "nothing")
        if vb[-1] == 0:
            # Zero is a dead clock or DSP off: fail, rather than raise.
            return False, want, "%s = 0 -- a dead clock, or DSP is off" % b
        r = va[-1] / vb[-1]
        return abs(r - want_r) <= tol, want, "%s / %s = %g / %g = %.3f" % (
            a, b, va[-1], vb[-1], r)

    raise BadSpec(kind)


def offline(spec):
    """Can this predicate be judged with no console? -> (ok, [kinds that cannot]).

    Asked before evaluate, never instead of a verdict: an absent oracle is a
    skip whose reason names the kinds. An `all` is offline only if every leaf
    is, or the rest would be judged against an empty window and fail.
    """
    kind = spec.get("kind")
    if kind == "all":
        bad = []
        for part in spec.get("of", []):
            bad.extend(offline(part)[1])
        # dict.fromkeys keeps the step's own order in the reason.
        bad = list(dict.fromkeys(bad))
        return (not bad), bad
    if kind not in KINDS:
        # Not ours to answer: a typo in a kind must reach BadSpec in evaluate()
        # and fail the step, not be skipped here.
        return True, []
    return (kind in OFFLINE_KINDS), ([] if kind in OFFLINE_KINDS else [kind])


def needs_mirror(spec):
    """Does this predicate need the OSC mirror? -> (needs, [kinds that do]).
    Asked as offline() is; an `all` needs it if any leaf does."""
    kind = spec.get("kind")
    if kind == "all":
        bad = []
        for part in spec.get("of", []):
            bad.extend(needs_mirror(part)[1])
        return bool(bad), list(dict.fromkeys(bad))
    return (kind in MIRROR_KINDS), ([kind] if kind in MIRROR_KINDS else [])


def evaluate(spec, window, ctx=None):
    """-> (ok, want, got). `all` is how a negative assertion gets its witness."""
    ok, want, got, _rows = report(spec, window, ctx)
    return ok, want, got


def report(spec, window, ctx=None):
    """-> (ok, want, got, rows). `rows` is [(ok, got, want)], one per leaf.

    The joined strings are what latest.json keeps; the rows are what a person
    reads. Split here rather than in the runner, so a record's shape is as it
    always was.
    """
    if spec.get("kind") == "all":
        parts = spec["of"]
        if not parts:
            raise BadSpec("an `all` with nothing in it asserts nothing")
        results = [_one(p, window, ctx) for p in parts]
        return (all(r[0] for r in results),
                " AND ".join(r[1] for r in results),
                " / ".join(r[2] for r in results),
                [(r[0], r[2], r[1]) for r in results])
    ok, want, got = _one(spec, window, ctx)
    return ok, want, got, [(ok, got, want)]
