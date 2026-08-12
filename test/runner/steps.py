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
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# ⚠️ KIND KNOWLEDGE STAYS IN predicates.py. `paper` has to know whether a
# predicate can be judged with no console, and asking the module that owns the
# kinds is what stops a second list of them growing here.
import predicates                                               # noqa: E402

# ⛔ THE SIGNATURE OF A STEP THAT TESTS A TIMEOUT, and it is deliberately wide.
# A false positive costs one step its hold and a person presses r; a false
# NEGATIVE re-fires a decay test forever and it can never fail again. When in
# doubt this must say "decay", so it matches the word forms the step text
# actually uses -- digits and spelled-out numbers both, because the Launchpad
# bench says "about two seconds" where the display bench says "about 2 s".
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
SAY_WHERE = _steps.SAY_WHERE
RE_WHERE = _steps.RE_WHERE

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
    # ⚠️ THE ONLY ENTRY THAT NAMES NOTHING UNDER "Cut It", and that is right:
    # the debug patch is a second deployable and a change to the instrument
    # cannot invalidate a verdict about it. The two SHELL SCRIPTS ARE IN HERE
    # DELIBERATELY -- steps 5 and 6 judge what err-tail.sh and net-probe.sh put on
    # the screen, so an edit to either is an edit to what those steps asserted.
    # ⚠️ wire.sh is here as the debug patch's COPY, not the instrument's. The two
    # are held identical by debug-assert.sh, so editing the instrument's does
    # reach this list -- through the copy that has to follow it.
    "debug":       ["Cut It Debug/main.pd", "Cut It Debug/wire.sh",
                    "Cut It Debug/err-tail.sh", "Cut It Debug/net-probe.sh"],
    "display":     ["Cut It/g_oled.pd", "Cut It/u_err.pd"],
    # ⚠️ u_tempo WAS MISSING HERE AND THE OMISSION WAS PRE-EXISTING. Step 14
    # counts BEATS off `r clock`, and u_tempo is the only writer of that bus --
    # so every beat-row verdict would have stayed green across a change to the
    # clock's own source. Found while editing u_tempo for something unrelated.
    # ⛔ ADDING IT STALES 26 VERDICTS ONCE. That is the bill for a signal that
    # tells the truth from here on, and it is the cheaper half of the trade:
    # fresh forever is worse than stale forever, because it is believed.
    "launchpad":   ["Cut It/g_grid.pd", "Cut It/m_launchpad.pd",
                    "Cut It/c_clock.pd", "Cut It/u_tempo.pd", "Cut It/u_err.pd",
                    "Cut It/u_present.pd", "Cut It/c_presence.pd",
                    "Cut It/c_devid.pd"],
    "midi":        ["Cut It/m_404.pd", "Cut It/m_volca.pd", "Cut It/u_map.pd",
                    "Cut It/cut-it-map.txt", "Cut It/g_oled.pd",
                    "Cut It/u_present.pd", "Cut It/c_presence.pd",
                    "Cut It/c_devid.pd"],
    "nanokontrol": ["Cut It/m_nano.pd", "Cut It/g_oled.pd", "Cut It/u_err.pd",
                    "Cut It/u_present.pd", "Cut It/c_presence.pd",
                    "Cut It/c_devid.pd"],
    # ⚠️ THE TWO OUTPUT LAYERS ARE IN HERE FOR THE TEST-NOTE STEPS. The phone can
    # fire a probe note at each of them through a cord out of u_net, and those
    # two verdicts are "the Volca sounded" and "the 404 sounded" -- so a change to
    # either layer invalidates them. u_present is here for the re-wire button.
    "phone":       ["Cut It/u_net.pd", "Cut It/u_err.pd", "Cut It/u_present.pd",
                    "Cut It/m_volca.pd", "Cut It/m_404.pd"],
    # ⚠️ u_tempo IS IN HERE FOR THE VOLCA STEP, not for the tempo. panic's STOP
    # is the only thing u_tempo sends to port 4, and step 2 is the only place
    # anything asserts that the Volca hears it.
    "recover":     ["Cut It/u_map.pd", "Cut It/u_init.pd", "Cut It/recover.sh",
                    "Cut It/cut-it-map.txt", "Cut It/u_tempo.pd",
                    "Cut It/state-dir.sh"],
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
        """What to look for: the PASS IF with its prefix stripped, always.

        ⛔ meta HAD A `watch` THAT REPLACED THIS, and it is gone. A step could
        put anything it liked on the line labelled PASS IF, so the label was a
        promise the runner did not keep -- which is the only reason the prompt
        ever needed a [?] key to show the real one. The last two overrides were
        removed on 2026-08-11: midi 7's restated its PASS IF in other words, and
        launchpad 14's explained the Mac dev panel to a person standing at the
        rig. The count a predicate wants is printed by the predicate itself, on
        the line above the verdict prompt, from the only source that cannot
        drift from it.
        """
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

        ⛔ AND A STEP MAY REFUSE OUTRIGHT WITH `hold: False`. The derivation
        below asks whether the step is ABOUT a decay; it cannot ask whether the
        step's own actions are idempotent. tempo 4 sends `120` to tempo and then
        a knob that maps to tempo, so every re-fire walks the footer from 120
        back down to 10 in front of somebody trying to read it -- measured, six
        times in five seconds. That is a property of the action list and it
        belongs beside the action list, not in a pattern over prose.

        ⛔ A PARAMETER ROW IS ON THE OLED FOR ABOUT 1.3 s. g_oled ages it out --
        the instrument working, and what stops a performance screen filling with
        stale rows -- so a step whose result is a row gives you barely a glance.
        Re-sending resets that timer, so the runner holds the picture up while
        the verdict is open.

        ⛔ AND FOR ROUGHLY TEN STEPS THAT WOULD DESTROY THE ASSERTION, because
        the thing being tested IS the decay: "about 2 s later it vanishes",
        "clears itself after 30 s", "the other four fade out". Re-firing those
        keeps resetting the very timer under test and they would pass forever.
        ⚠️ SO THE EXEMPTION IS DERIVED FROM THE TEXT RATHER THAN HAND-KEPT. A
        hand-maintained list is a second place to forget, and forgetting here
        does not fail loudly -- it makes a timeout test unfalsifiable.

        Three ways out, and the first two are structural:
          * no actions at all -- there is nothing to re-send
          * a measure step -- re-firing re-arms or re-reads a beat counter
          * the prose claims something happens after a delay
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
        """Can this bench run with NO PATCH ON THE OTHER END at all?

        ⛔ NO PD, NO ssh, NO `killall pd`, and therefore no Launchpad stranded in
        Programmer Mode. `state` is like this, which is five steps that can be
        run with none of the device machinery. Phase 8's run was driven this way
        by hand and that is exactly why it was painless.

        ⛔ AND "NO ACTIONS" IS NOT THE SAME QUESTION, which is what this used to
        ask. Three separate things need a patch, and only the first is an
        action: a PREDICATE that reads a console has nothing to read, and a
        `reload` step is the runner OWNING the process it is asked to restart.
        The proxy held only while those two happened to travel with actions --
        and it broke the moment nanokontrol was cut back to its six hands-on
        steps, which have no actions at all and are entirely about a running
        instrument. `midi` had the same shape already and every recorded run of
        it passed `--target device` by hand to work around exactly this.
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
