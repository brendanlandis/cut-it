#!/usr/bin/env python3
"""List, delete or rewrite the comments in a .pd file, keeping every cord.

    python3 tools/pd-comments.py list "Cut It/u_root.pd"              # each comment, numbered
    python3 tools/pd-comments.py apply "Cut It/u_root.pd" edits.json  # delete or rewrite them

A `#X connect` names boxes by their place in their canvas, and a comment is a
box, so deleting one by hand renumbers every box after it (C-10). This works
record by record (C-14): it drops or rewrites the comments asked for, renumbers
each canvas's connects to match, and leaves every other record byte for byte.

edits.json maps a comment's number from `list` to null (delete it) or to its new
text as it should read; commas, semicolons and dollar signs are escaped here. A
rewritten comment keeps its place and its width. Before writing, the result is
read back and must hold the same boxes and the same cords as the original, or
nothing is written.
"""
import json
import re
import sys

# The records that are boxes, and so take a place in their canvas's numbering.
# `restore` is a subpatch's box, counted in the parent where the subpatch closes.
BOXES = ("obj", "msg", "text", "floatatom", "symbolatom", "listbox", "restore",
         "array", "scalar")
CONNECT = re.compile(r"^#X connect (\d+) (\d+) (\d+) (\d+);\s*$")
# Pd writes a comment's width as an UNESCAPED `, f 58` after the text; an
# escaped ` \, ` is a comma in the text itself.
WIDTH = re.compile(r"(?<!\\), f (\d+)$")


def raw_records(src):
    """The file as raw records, each with the whitespace that follows it, so
    joining them gives back the file exactly."""
    out, start, i = [], 0, 0
    while i < len(src):
        ch = src[i]
        if ch == "\\":
            i += 2
            continue
        i += 1
        if ch == ";":
            while i < len(src) and src[i] in " \t\r\n":
                i += 1
            out.append(src[start:i])
            start = i
    if start < len(src):
        out.append(src[start:])
    return out


def kind(rec):
    """`#X obj` -> 'obj', `#N canvas` -> 'canvas', and so on."""
    parts = rec.split(None, 2)
    return parts[1].rstrip(";") if len(parts) > 1 else ""


def walk(recs):
    """Number every box in its canvas. -> list of (canvas id, index or None)
    per record, where a box's index is its place in its canvas."""
    stack, counts, out, next_id = [0], {0: 0}, [], 1
    for rec in recs:
        k = kind(rec)
        if rec.startswith("#N canvas") and out:
            stack.append(next_id)
            counts[next_id] = 0
            next_id += 1
            out.append((stack[-1], None))
            continue
        if rec.startswith("#X restore"):
            stack.pop()
        if rec.startswith("#X ") and k in BOXES:
            canvas = stack[-1]
            out.append((canvas, counts[canvas]))
            counts[canvas] += 1
        else:
            out.append((stack[-1], None))
    return out


def comments(recs):
    """[(number, record index)] for every `#X text`, in file order."""
    return list(enumerate(i for i, r in enumerate(recs) if r.startswith("#X text ")))


def unescape(body):
    return (body.replace(" \\,", ",").replace(" \\;", ";").replace("\\$", "$")
            .replace("\\,", ",").replace("\\;", ";"))


def escape(text):
    text = " ".join(text.split())
    text = text.replace("\\", "").replace("$", "\\$")
    text = re.sub(r"\s*,", " \\,", text)
    text = re.sub(r"\s*;", " \\;", text)
    return text


def comment_text(rec):
    body = rec.strip()[:-1]                      # the closing ;
    body = body.split(None, 4)[4] if len(body.split(None, 4)) > 4 else ""
    body = WIDTH.sub("", body)
    return unescape(" ".join(body.split()))


def rewrite(rec, text):
    # Pd reads `40.` as the float 40, so a sentence ending on a bare number
    # loses its stop (item 122).
    bare = re.search(r"(?:^|\s)(-?\d+\.)(?:\s|$)", text)
    if bare:
        sys.exit("%r ends a sentence on a bare number, and Pd would drop the stop"
                 % bare.group(1))
    head = rec.strip()[:-1]
    parts = head.split(None, 4)
    width = WIDTH.search(head)
    new = "#X text %s %s %s" % (parts[2], parts[3], escape(text))
    if width:
        new += ", f %s" % width.group(1)
    trail = rec[len(rec.rstrip()):]
    return new + ";" + trail


def shape(recs):
    """What must survive: every non-comment record in order, and the cords as
    (canvas, from-box, outlet, to-box, inlet) named by the boxes' own records."""
    places = walk(recs)
    boxes = {}
    for (canvas, idx), rec in zip(places, recs):
        if idx is not None:
            boxes[(canvas, idx)] = " ".join(rec.split())
    keep = [" ".join(r.split()) for r in recs
            if not r.startswith(("#X text ", "#X connect "))]
    cords = []
    for (canvas, _), rec in zip(places, recs):
        m = CONNECT.match(rec.strip())
        if m:
            a, o, b, i = map(int, m.groups())
            cords.append((canvas, boxes[(canvas, a)], o, boxes[(canvas, b)], i))
    return keep, sorted(cords)


def apply(recs, edits):
    numbered = dict(comments(recs))
    unknown = [n for n in edits if n not in numbered]
    if unknown:
        sys.exit("no comment numbered %s" % unknown)
    drop = {numbered[n] for n, t in edits.items() if t is None}
    places = walk(recs)
    # old index -> new index, per canvas
    remap, gone = {}, set()
    shift = {}
    for r, (canvas, idx) in enumerate(places):
        if idx is None:
            continue
        if r in drop:
            shift[canvas] = shift.get(canvas, 0) + 1
            gone.add((canvas, idx))
        else:
            remap[(canvas, idx)] = idx - shift.get(canvas, 0)
    out = []
    for r, rec in enumerate(recs):
        if r in drop:
            continue
        n = next((n for n, ri in numbered.items() if ri == r), None)
        if n is not None and n in edits:
            out.append(rewrite(rec, edits[n]))
            continue
        m = CONNECT.match(rec.strip())
        if m:
            canvas = places[r][0]
            a, o, b, i = map(int, m.groups())
            if (canvas, a) in gone or (canvas, b) in gone:
                sys.exit("record %d is a cord onto a comment: %s" % (r, rec.strip()))
            trail = rec[len(rec.rstrip()):]
            out.append("#X connect %d %d %d %d;%s"
                       % (remap[(canvas, a)], o, remap[(canvas, b)], i, trail))
            continue
        out.append(rec)
    return out


def main():
    if len(sys.argv) < 3 or sys.argv[1] not in ("list", "apply"):
        sys.exit(__doc__)
    path = sys.argv[2]
    src = open(path, encoding="utf-8").read()
    recs = raw_records(src)
    if "".join(recs) != src:
        sys.exit("%s: could not split it into records losslessly" % path)
    if sys.argv[1] == "list":
        places = walk(recs)
        for n, r in comments(recs):
            parts = recs[r].split(None, 4)
            print("%d\t[canvas %d] %s %s\t%s" % (n, places[r][0], parts[2], parts[3],
                                                comment_text(recs[r])))
        return
    edits = {int(k): v for k, v in json.load(open(sys.argv[3])).items()}
    out = apply(recs, edits)
    before, after = shape(recs), shape(raw_records("".join(out)))
    if before != after:
        sys.exit("%s: the result would not hold the same boxes and cords -- nothing written"
                 % path)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("".join(out))
    dropped = sum(1 for v in edits.values() if v is None)
    print("%s: %d comment(s) deleted, %d rewritten" % (path, dropped, len(edits) - dropped))


if __name__ == "__main__":
    main()
