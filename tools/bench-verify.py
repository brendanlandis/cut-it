#!/usr/bin/env python3
"""THE FIDELITY GATE for the bench conversion.

    python3 tools/bench-verify.py

phase3/4/5-bench.pd were hand-authored and are verified on the Organelle.
bench-gen.py rebuilds their box graph completely, so the only honest way to be
sure the conversion changed how a step is DRIVEN and not what it CLAIMS is to
read the step text back out of the generated file and diff it against the table
it was generated from. Zero differences is the pass.

Exits non-zero on any difference, so it can gate a commit.
"""
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


be = _load("bench_extract", os.path.join(HERE, "bench-extract.py"))
steps_mod = _load("bench_steps", os.path.join(HERE, "bench_steps.py"))


def norm(table):
    return [[t, p, [list(a) for a in acts]] for t, p, acts in table]


def main():
    bad = 0
    for phase in (3, 4, 5, 6, 7, 8):
        want = norm(getattr(steps_mod, "STEPS%d" % phase))
        path = os.path.join(HERE, "phase%d-bench.pd" % phase)
        got = norm(be.extract(path))

        if want == got:
            print("phase%d  %2d steps  IDENTICAL" % (phase, len(want)))
            continue

        bad += 1
        print("phase%d  DIFFERS" % phase)
        if len(want) != len(got):
            print("   step count: table %d, generated %d" % (len(want), len(got)))
        for i, (w, g) in enumerate(zip(want, got), 1):
            if w == g:
                continue
            for field, wv, gv in zip(("title", "pass_if", "actions"), w, g):
                if wv != gv:
                    print("   step %d %s:" % (i, field))
                    print("      table     %s" % json.dumps(wv))
                    print("      generated %s" % json.dumps(gv))
    print()
    if bad:
        print("FAIL -- %d bench(es) differ from their step table" % bad)
        return 1
    print("PASS -- every step's text and actions survived the conversion")
    return 0


if __name__ == "__main__":
    sys.exit(main())
