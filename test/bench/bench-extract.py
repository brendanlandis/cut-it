#!/usr/bin/env python3
"""Reads a bench .pd back into its step table: title, PASS IF, and each action
message with the bus it is sent to. bench-verify.py diffs it against
bench_steps.py.

    python3 test/bench/bench-extract.py test/bench/tempo-bench.pd            # python source
    python3 test/bench/bench-extract.py test/bench/tempo-bench.pd --json     # for diffing

Steps are found by their "=== STEP-NN-of-M ===" marker, never by counting
"PASS IF" strings: the bench's header text says PASS IF too.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "gate"))
import lib_pd                                                   # noqa: E402


def records(path):
    """A .pd's records without their closing ';' (lib_pd keeps it)."""
    src = open(path, encoding="utf-8", errors="replace").read()
    return [r[:-1] if r.endswith(";") else r for r in lib_pd.records(src)]


BOX_KINDS = ("obj", "msg", "text", "floatatom", "symbolatom")
STEP_RE = re.compile(r"^===\s*STEP-(\d+)-of-(\d+)\s*===\s*(.*)$")
FIRED_RE = re.compile(r"^---\s*step\s+(\d+)\s+fired\b")
SAY = "\\$0-say"


def trigger_feeding(boxes, src_of, idx):
    """The [t ...] whose outlet fired this box."""
    for _bi, a in src_of.get(idx, []):
        if boxes[a][0] == "obj" and boxes[a][1].split()[:1] == ["t"]:
            return a
    return None


def outputs_of(boxes, dst_of, trig, skip):
    """Every message box a trigger fires, paired with the bus it is sent to.
    Yielded in firing order -- rightmost outlet first."""
    if trig is None:
        return
    for _ao, b in sorted(dst_of.get(trig, []), key=lambda p: -p[0]):
        if b == skip or boxes[b][0] != "msg":
            continue
        bus = None
        for _o, d in dst_of.get(b, []):
            words = boxes[d][1].split()
            if (boxes[d][0] == "obj" and words[:1] in (["s"], ["send"])
                    and len(words) > 1):
                bus = words[1]
        if bus:
            yield unescape(boxes[b][1]).strip(), bus


def parse(path):
    """Return (boxes, connects). Only top-level boxes are counted, in file order,
    because that is exactly what #X connect indexes against."""
    boxes, connects, depth = [], [], 0
    for rec in records(path):
        parts = rec.split()
        if not parts:
            continue
        if parts[0] == "#N" and len(parts) > 1 and parts[1] == "canvas":
            depth += 1
            continue
        if parts[0] == "#X" and len(parts) > 1:
            kind = parts[1]
            if kind == "restore":
                depth -= 1
                # a restored subpatch occupies a box slot in its PARENT
                if depth == 1:
                    boxes.append(("obj", " ".join(parts[2:])))
                continue
            if depth != 1:
                continue
            if kind == "connect":
                connects.append(tuple(int(v) for v in parts[2:6]))
            elif kind in BOX_KINDS:
                # obj/msg/text carry x y then content
                boxes.append((kind, " ".join(parts[4:])))
            elif kind in ("coords", "declare"):
                pass
    return boxes, connects


def unescape(s):
    return s.replace("\\,", ",").replace("\\;", ";").replace("\\$", "$")


def extract(path):
    boxes, connects = parse(path)
    # who feeds whom
    src_of = {}
    dst_of = {}
    for a, ao, b, bi in connects:
        dst_of.setdefault(a, []).append((ao, b))
        src_of.setdefault(b, []).append((bi, a))

    steps = {}
    for idx, (kind, content) in enumerate(boxes):
        if kind != "msg":
            continue
        m = STEP_RE.match(unescape(content).strip())
        if not m:
            continue
        num, total, title = int(m.group(1)), int(m.group(2)), m.group(3).strip()

        trig = trigger_feeding(boxes, src_of, idx)
        passif, actions = "", []
        for text, bus in outputs_of(boxes, dst_of, trig, skip=idx):
            if bus == SAY:
                # Prose: only the PASS IF is part of the step table, not the
                # >>> prompt.
                if text.startswith("PASS IF"):
                    passif = text
            else:
                actions.append((text, bus))
        steps[num] = [title, passif, actions, total]

    # The manually-stepped layout splits a step across two triggers: one
    # describes, one runs. Pick the actions off the run trigger, found by the
    # line it prints after firing.
    for idx, (kind, content) in enumerate(boxes):
        if kind != "msg":
            continue
        m = FIRED_RE.match(unescape(content).strip())
        if not m:
            continue
        num = int(m.group(1))
        if num not in steps:
            continue
        trig = trigger_feeding(boxes, src_of, idx)
        for text, bus in outputs_of(boxes, dst_of, trig, skip=idx):
            if bus != SAY:
                steps[num][2].append((text, bus))

    ordered = [steps[k] for k in sorted(steps)]
    if ordered:
        total = ordered[0][3]
        if len(ordered) != total:
            print("WARNING: %s declares %d steps, found %d"
                  % (path, total, len(ordered)), file=sys.stderr)
    return [(t, p, a) for (t, p, a, _n) in ordered]


def as_table(path):
    """The step table as plain data, for diffing one bench against another."""
    return [[t, p, [list(x) for x in a]] for t, p, a in extract(path)]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    as_json = "--json" in sys.argv
    for path in args:
        steps = extract(path)
        if as_json:
            print(json.dumps(steps, indent=1, sort_keys=True))
        else:
            print("# extracted from %s -- %d steps" % (path, len(steps)))
            print("STEPS = [")
            for title, passif, actions in steps:
                print(" (%r," % title)
                print("  %r," % passif)
                print("  %r)," % (actions,))
            print("]")


if __name__ == "__main__":
    main()
