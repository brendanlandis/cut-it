#!/usr/bin/env python3
"""The fidelity gate: proves every bench's step text survived generation.

    python3 test/bench/bench-verify.py

Reads title, PASS IF and actions back out of each generated .pd and diffs them
against bench_steps.py. Exits non-zero on any difference.
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
# The bench list is bench-gen's own table, never retyped (the gate skill,
# Benches). bench-gen writes files only under __main__, so importing it
# generates nothing.
gen = _load("bench_gen", os.path.join(HERE, "bench-gen.py"))
steps_mod = _load("bench_steps", os.path.join(HERE, "bench_steps.py"))


def norm(table):
    """A step table -> the three fields a .pd carries. The fourth, meta, never
    reaches a .pd, so it is not compared.
    """
    out = []
    for step in table:
        t, p, acts, _meta = steps_mod.norm(step)
        out.append([t, p, [list(a) for a in acts]])
    return out


def main():
    bad = 0
    names = sorted(gen.BENCHES)
    # The count is printed: a verifier that checked no bench would also pass.
    print("verifying %d bench(es): %s\n" % (len(names), " ".join(names)))
    for name in names:
        want = norm(gen.BENCHES[name]["steps"])
        path = os.path.join(HERE, "%s-bench.pd" % name)
        got = norm(be.extract(path))

        if want == got:
            print("%-12s %2d steps  IDENTICAL" % (name, len(want)))
            continue

        bad += 1
        print("%s  DIFFERS" % name)
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
