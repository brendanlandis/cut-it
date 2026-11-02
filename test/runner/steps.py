#!/usr/bin/env python3
"""The bench tables, as the runner sees them. Imported by run.py.

The list of benches is bench-gen.py's BENCHES, never a copy: a bench missing
from a copy would generate and verify and be invisible here.

bench-gen.py and bench-extract.py load through importlib, since a hyphen is not
a legal Python identifier.
"""
import importlib.util
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# What a predicate kind needs stays in predicates.py, so `paper` asks it rather
# than keeping a second list.
import predicates                                               # noqa: E402

# Deliberately wide: a false positive costs a step its hold, a false negative
# re-fires a decay test until it can never fail. Digits and spelled-out numbers
# both, since the steps say "about two seconds" and "about 2 s".
DECAY_RE = re.compile(
    r"\b(later|fades?|fade out|vanish\w*|clears? itself|on its own|"
    r"by itself|returns? after|times? out|timed out|settles?|persists?|"
    r"still reads|keeps? walking|after about|seconds?|30 s|35 s|"
    r"\d+(\.\d+)?\s*s\b)", re.I)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BENCH_DIR = os.path.join(ROOT, "test", "bench")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# bench-gen.py writes only under __main__, so importing it generates nothing.
_gen = _load("bench_gen", os.path.join(BENCH_DIR, "bench-gen.py"))
_steps = _load("bench_steps", os.path.join(BENCH_DIR, "bench_steps.py"))

WINDOW_MS = _steps.WINDOW_MS
MEASURE_SUFFIX = _steps.MEASURE_SUFFIX

# Re-exported, never re-declared: the console protocol lives in bench_steps.py
# beside the format strings it must match, and a drifted copy would report a
# working bench as stalled.
SAY_STEP = _steps.SAY_STEP
SAY_PROMPT = _steps.SAY_PROMPT
SAY_FIRED = _steps.SAY_FIRED
SAY_FIRED_LAST = _steps.SAY_FIRED_LAST
SAY_COMPLETE = _steps.SAY_COMPLETE
RE_STEP = _steps.RE_STEP
RE_FIRED = _steps.RE_FIRED
RE_COMPLETE = _steps.RE_COMPLETE
SAY_WHERE = _steps.SAY_WHERE
RE_WHERE = _steps.RE_WHERE

# ---------------------------------------------------------------------------
# What each bench's verdicts depend on (records.deps_sha). Err on the side of
# listing: a dependency left out keeps a verdict green across a change that
# invalidated it, and one too many costs a re-run. The three presence files are
# on every bench that asks a hot-swap question.
DEPS = {
    # Nothing under "Cut It": a change to the instrument cannot invalidate a
    # verdict about the debug patch. Steps 5 and 6 judge what err-tail.sh and
    # net-probe.sh draw. debug-assert.sh holds this wire.sh identical to the
    # instrument's, so an edit to either reaches this list.
    "debug":       ["Cut It Debug/main.pd", "Cut It Debug/wire.sh",
                    "Cut It Debug/err-tail.sh", "Cut It Debug/net-probe.sh"],
    "display":     ["Cut It/g_oled.pd", "Cut It/u_err.pd"],
    # u_tempo is the only writer of `clock`, which the beat-row step counts.
    # u_map and the map for the rows: m_launchpad posts none of its own (item
    # 317), and the ring step names the buttons the map binds.
    "launchpad":   ["Cut It/g_grid.pd", "Cut It/m_launchpad.pd",
                    "Cut It/c_clock.pd", "Cut It/u_tempo.pd", "Cut It/u_err.pd",
                    "Cut It/u_present.pd", "Cut It/c_presence.pd",
                    "Cut It/c_devid.pd", "Cut It/u_map.pd",
                    "Cut It/cut-it-map.txt"],
    "midi":        ["Cut It/m_404.pd", "Cut It/m_volca.pd", "Cut It/u_map.pd",
                    "Cut It/c_mapped.pd",
                    "Cut It/cut-it-map.txt", "Cut It/g_oled.pd",
                    "Cut It/u_present.pd", "Cut It/c_presence.pd",
                    "Cut It/c_devid.pd"],
    # Every row the first step reads is u_map's, and slider-1's in mode 1 is
    # c_mapped's volca-cc41.
    "nanokontrol": ["Cut It/m_nano.pd", "Cut It/g_oled.pd", "Cut It/u_err.pd",
                    "Cut It/u_present.pd", "Cut It/c_presence.pd",
                    "Cut It/c_devid.pd", "Cut It/u_map.pd",
                    "Cut It/c_mapped.pd", "Cut It/cut-it-map.txt"],
    # The two output layers for the test-note steps ("the Volca sounded", "the
    # 404 sounded"); u_present for the re-wire button.
    "phone":       ["Cut It/u_net.pd", "Cut It/u_err.pd", "Cut It/u_present.pd",
                    "Cut It/m_volca.pd", "Cut It/m_404.pd"],
    # u_tempo for the Volca step: panic's stop is all it sends to port 4.
    "recover":     ["Cut It/u_map.pd", "Cut It/u_init.pd", "Cut It/recover.sh",
                    "Cut It/cut-it-map.txt", "Cut It/u_tempo.pd",
                    "Cut It/state-dir.sh"],
    "state":       ["Cut It/u_state.pd", "Cut It/u_store.pd", "Cut It/u_init.pd"],
    # c_mapped builds the bpm row this bench reads off the OLED.
    "tempo":       ["Cut It/u_tempo.pd", "Cut It/c_clock.pd", "Cut It/u_map.pd",
                    "Cut It/c_mapped.pd"],
}


class Step(object):
    __slots__ = ("n", "of", "title", "pass_if", "actions", "meta")

    def __init__(self, n, of, title, pass_if, actions, meta):
        self.n, self.of = n, of
        self.title, self.pass_if = title, pass_if
        self.actions, self.meta = actions, meta

    @property
    def hands(self):
        """A field, never a substring test on prose: bench-gen's
        `"HANDS" in title.upper()` misses steps whose title says otherwise. A
        `do` is the authority."""
        return bool(self.meta.get("do"))

    @property
    def watch(self):
        """What to look for: the PASS IF with its prefix stripped, always. A
        predicate prints the count it wants itself, above the verdict prompt."""
        p = self.pass_if
        return p[len("PASS IF:"):].strip() if p.startswith("PASS IF:") else p

    @property
    def measure(self):
        """Does this step arm a timed count? Then the window has to be waited
        out before the number means anything."""
        return any(b.endswith(MEASURE_SUFFIX) for _m, b in self.actions)

    @property
    def holds(self):
        """May the runner re-fire this step while a person reads it?

        A parameter row is on the OLED for about 1.3 s, so re-sending holds the
        picture up while the verdict is open. A step whose subject is the decay
        ("about 2 s later it vanishes") would keep resetting the timer under
        test and pass forever, so that exemption is derived from the prose
        (DECAY_RE): a hand-kept list would fail silently.

        Not held: no actions, a measure step (re-firing re-arms the counter),
        prose claiming a delay, or `hold: False` for actions that are not
        idempotent (tempo 4 would walk the footer from 120 down to 10 on every
        re-fire).
        """
        if not self.actions or self.measure:
            return False
        if self.meta.get("hold") is False:
            return False
        return not DECAY_RE.search(self.pass_if)


class Bench(object):
    def __init__(self, name):
        self.name = name
        table = _gen.BENCHES[name]["steps"]
        self.steps = [
            Step(i, len(table), *_steps.norm(s))
            for i, s in enumerate(table, 1)]
        self.deps = DEPS[name]

    @property
    def paper(self):
        """Can this bench run with no patch on the other end: no Pd, no ssh, no
        `killall pd`, no Launchpad stranded in Programmer Mode?

        Not the same question as "no actions": a predicate that reads a console
        and a `reload` step need a running patch too.
        """
        if any(s.actions for s in self.steps):
            return False
        if any(s.meta.get("reload") for s in self.steps):
            return False
        for s in self.steps:
            spec = s.meta.get("check")
            if spec and not predicates.offline(spec)[0]:
                return False
        return True


def names():
    return sorted(_gen.BENCHES)


def load(name):
    return Bench(name)


def check_inventory():
    """Every bench declares its dependencies: one defaulting to [] would be
    fresh forever, which is worse than stale forever because it is believed."""
    missing = sorted(set(names()) - set(DEPS))
    extra = sorted(set(DEPS) - set(names()))
    problems = []
    if missing:
        problems.append("benches with no DEPS entry: %s" % ", ".join(missing))
    if extra:
        problems.append("DEPS names no such bench: %s" % ", ".join(extra))
    return problems
