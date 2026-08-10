#!/usr/bin/env python3
"""The bench tables, as the runner sees them. Imported by run.py.

⛔ THE LIST OF BENCHES IS DERIVED, NEVER RETYPED. bench-gen.py's BENCHES table is
the only list there is, and bench-verify.py already reads it rather than carrying
its own copy -- because it used to carry one, and missing an entry meant a bench
was generated but NEVER FIDELITY-CHECKED. A third copy here would reintroduce
exactly that, one layer up: a bench that generates, verifies, and is invisible to
the runner.

⚠️ THE HYPHENATED NEIGHBOURS LOAD THROUGH importlib. A hyphen is not a legal
Python identifier, so bench-gen.py and bench-extract.py cannot be imported by
name; bench_steps.py and this file can, and that is the whole reason for the
inconsistent punctuation across test/.
"""
import importlib.util
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BENCH_DIR = os.path.join(ROOT, "test", "bench")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ⚠️ bench-gen.py writes files only under `if __name__ == "__main__"`, so
# importing it here generates nothing.
_gen = _load("bench_gen", os.path.join(BENCH_DIR, "bench-gen.py"))
_steps = _load("bench_steps", os.path.join(BENCH_DIR, "bench_steps.py"))

WINDOW_MS = _steps.WINDOW_MS
MEASURE_SUFFIX = _steps.MEASURE_SUFFIX

# ⛔ RE-EXPORTED, NEVER RE-DECLARED. The console protocol is one agreement
# between the generator that writes these lines and the runner that reads them,
# and it lives in bench_steps.py beside the format strings it has to match.
# Writing the regexes again here would be the second copy, and the failure it
# produces is the nastiest kind: the runner stops recognising a step, reports a
# stall, and the bench on the other end is working perfectly.
SAY_STEP = _steps.SAY_STEP
SAY_PROMPT = _steps.SAY_PROMPT
SAY_FIRED = _steps.SAY_FIRED
SAY_FIRED_LAST = _steps.SAY_FIRED_LAST
SAY_COMPLETE = _steps.SAY_COMPLETE
RE_STEP = _steps.RE_STEP
RE_FIRED = _steps.RE_FIRED
RE_COMPLETE = _steps.RE_COMPLETE

# ---------------------------------------------------------------------------
# ⛔ WHAT EACH BENCH'S VERDICTS ACTUALLY DEPEND ON, and it is PER BENCH.
#
# The obvious implementation -- hash all of "Cut It/" -- makes every bench stale
# on every patch commit. A staleness signal that is always lit is one nobody
# reads, which is the same disease as a gate that lies, so the dependency is
# named rather than assumed. Then "you changed u_tempo.pd" can say exactly whose
# verdicts stopped applying.
#
# ⚠️ ERR ON THE SIDE OF LISTING. A dependency left out means a verdict stays
# green across a change that invalidated it, which is the failure that matters;
# one listed too many costs a re-run.
#
# ⚠️ THE THREE PRESENCE FILES ARE ON THREE BENCHES BECAUSE THREE BENCHES NOW ASK
# A HOT-SWAP QUESTION. u_present owns the shared bound, c_presence is the
# per-device clock inside each m_, and c_devid is the manufacturer-byte matcher
# that decides whether a reply was this device's -- so a change to any of them
# invalidates "the warn appeared" and "it came back within 60 seconds" on every
# one of them.
DEPS = {
    "display":     ["Cut It/g_oled.pd", "Cut It/u_err.pd"],
    "launchpad":   ["Cut It/g_grid.pd", "Cut It/m_launchpad.pd",
                    "Cut It/c_clock.pd", "Cut It/u_err.pd",
                    "Cut It/u_present.pd", "Cut It/c_presence.pd",
                    "Cut It/c_devid.pd"],
    "midi":        ["Cut It/m_404.pd", "Cut It/m_volca.pd", "Cut It/u_map.pd",
                    "Cut It/cut-it-map.txt", "Cut It/g_oled.pd",
                    "Cut It/u_present.pd", "Cut It/c_presence.pd",
                    "Cut It/c_devid.pd"],
    "nanokontrol": ["Cut It/m_nano.pd", "Cut It/g_oled.pd", "Cut It/u_err.pd",
                    "Cut It/u_present.pd", "Cut It/c_presence.pd",
                    "Cut It/c_devid.pd"],
    "phone":       ["Cut It/u_net.pd", "Cut It/u_err.pd"],
    "state":       ["Cut It/u_state.pd", "Cut It/u_store.pd", "Cut It/u_init.pd"],
    "tempo":       ["Cut It/u_tempo.pd", "Cut It/c_clock.pd", "Cut It/u_map.pd"],
}


class Step(object):
    __slots__ = ("n", "of", "title", "pass_if", "actions", "meta")

    def __init__(self, n, of, title, pass_if, actions, meta):
        self.n, self.of = n, of
        self.title, self.pass_if = title, pass_if
        self.actions, self.meta = actions, meta

    @property
    def hands(self):
        """⛔ THE FLAG IS A FIELD, NEVER A SUBSTRING TEST ON PROSE. bench-gen's
        `"HANDS" in title.upper()` is measurably wrong: it misses all three
        `THE NANO --` steps, both tempo `BY HAND` steps and four of the six state
        steps -- nine in total. The presence of a `do` is the authority."""
        return bool(self.meta.get("do"))

    @property
    def watch(self):
        """What to look for. Defaults to the PASS IF with its prefix stripped,
        because that is what the prose already says and restating it in meta
        would be a second copy free to drift."""
        w = self.meta.get("watch")
        if w:
            return w
        p = self.pass_if
        return p[len("PASS IF:"):].strip() if p.startswith("PASS IF:") else p

    @property
    def measure(self):
        """Does this step arm a timed count? Then the window has to be waited
        out before the number means anything."""
        return any(b.endswith(MEASURE_SUFFIX) for _m, b in self.actions)


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
        """⛔ NO ACTIONS ANYWHERE MEANS NO PATCH IS NEEDED AT ALL -- no Pd, no
        ssh, no `killall pd`, and therefore no Launchpad stranded in Programmer
        Mode. `state` and `midi` are both like this, which is 20 steps that can
        be run with none of the device machinery. Phase 8's run was driven this
        way by hand and that is exactly why it was painless."""
        return all(not s.actions for s in self.steps)


def names():
    return sorted(_gen.BENCHES)


def load(name):
    return Bench(name)


def check_inventory():
    """⛔ EVERY BENCH MUST DECLARE ITS DEPENDENCIES.

    Without this a bench added to bench-gen's table gets no deps entry, and the
    obvious implementation -- default to [] -- would make its verdicts
    permanently fresh: never stale, whatever changes in the patch. Fresh forever
    is worse than stale forever, because it is believed.
    """
    missing = sorted(set(names()) - set(DEPS))
    extra = sorted(set(DEPS) - set(names()))
    problems = []
    if missing:
        problems.append("benches with no DEPS entry: %s" % ", ".join(missing))
    if extra:
        problems.append("DEPS names no such bench: %s" % ", ".join(extra))
    return problems
