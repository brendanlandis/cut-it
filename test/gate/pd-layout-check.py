#!/usr/bin/env python3
"""Static layout check for Pd patches.

    python3 test/gate/pd-layout-check.py "Cut It"/*.pd     check
    python3 test/gate/pd-layout-check.py --boxes FILE      list box INDICES

A PROBLEM is structural and exits non-zero:
    BAD CONNECT      a cord names a box that does not exist
    CONNECT/COMMENT  a cord lands on a comment -- indices are off by one
    FORWARD CONNECT  a cord names a box defined later in the file (C-10)
    TOO SMALL        content extends past the saved canvas
    MALFORMED RECORD a record that does not start with '#' (C-14)
A note (BOX/BOX, CORD/BOX) is cosmetic and does not fail the run.

Box sizes are estimated from the text (7 px/char, 18 px/line), not Pd's font
metrics, so a couple of pixels either way is noise. test/README.md has the rest.
"""
import re, sys

import lib_pd
CW, LH = 7.0, 18.0

def _size(kind, rest, fw):
    first = rest.split(' ')[0]
    # atom boxes: "<width> <lo> <hi> <labelpos> <label> <recv> <send>", width in chars
    if kind in ('floatatom', 'symbolatom'):
        try:               return int(rest.split()[0]) * CW + 10, 22
        except Exception:  return 45, 22
    # cnv: "cnv <selectable_size> <width> <height> <send> <recv> <label> ..."
    if first == 'cnv':
        try:               return int(rest.split()[2]), int(rest.split()[3])
        except Exception:  return 100, 60
    # iemguis carry their own dimensions -- read them rather than guessing, or a
    # 25-cell hradio reports the footprint of a 3-cell one and its neighbors look clear
    a = rest.split()
    def _n(i, d):
        try:    return int(float(a[i]))
        except Exception: return d
    if first == 'hsl':           return _n(1, 128) + 10, _n(2, 15) + 8
    if first == 'vsl':           return _n(1, 15) + 8,   _n(2, 128) + 10
    if first == 'hradio':        return _n(1, 15) * _n(4, 8) + 4, _n(1, 15) + 8
    if first == 'vradio':        return _n(1, 15) + 8,   _n(1, 15) * _n(4, 8) + 4
    if first == 'vu':            return _n(1, 15) + 18,  _n(2, 120) + 28
    if first in ('bng', 'tgl'):  return _n(1, 15) + 8,   _n(1, 15) + 8
    if fw:
        words, lines, cur = rest.split(), 1, 0
        for wd in words:
            if cur and cur + 1 + len(wd) > fw: lines += 1; cur = len(wd)
            else: cur += (1 if cur else 0) + len(wd)
        return fw*CW + 10, lines*LH + 8
    return len(rest)*CW + 10, 22

def parse(path):
    """Return [(label, boxes, conns), ...] -- one context per canvas.

    Subpatches are their own coordinate space. A [pd name] box appears in the
    PARENT at the coordinates on its #X restore line, and its contents are
    checked separately."""
    root = {'label': path, 'boxes': [], 'conns': []}
    ctxs, stack = [root], [root]
    depth = 0
    for ln in lib_pd.read(path):
        ln = ln.rstrip(';')
        if ln.startswith('#N canvas'):
            depth += 1
            if depth > 1:
                sub = {'label': None, 'boxes': [], 'conns': []}
                ctxs.append(sub); stack.append(sub)
            continue
        cur = stack[-1]
        r = re.match(r'#X restore (-?\d+) (-?\d+) (.*)$', ln)
        if r and len(stack) > 1:
            sub = stack.pop(); depth -= 1
            sub['label'] = f"{path} [{r.group(3)}]"
            x, y, txt = int(r.group(1)), int(r.group(2)), r.group(3)
            w, h = _size('obj', txt, None)
            stack[-1]['boxes'].append({'k':'obj','x':x,'y':y,'w':w,'h':h,'t':txt[:40]})
            continue
        c = re.match(r'#X connect (\d+) (\d+) (\d+) (\d+)$', ln)
        if c:
            cur['conns'].append(tuple(int(g) for g in c.groups()))
            # How many boxes existed when Pd read this line, for forward_refs.
            cur.setdefault('cseen', []).append(len(cur['boxes']))
            continue
        # symbolatom is a box in Pd's index; leaving it out shifts every later one.
        m = re.match(r'#X (obj|msg|text|floatatom|symbolatom) (-?\d+) (-?\d+) ?(.*)$', ln)
        if not m: continue
        kind, x, y, rest = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4)
        fw = None
        fm = re.search(r',\s*f (\d+)$', rest)
        if fm: fw = int(fm.group(1)); rest = rest[:fm.start()]
        rest = rest.replace('\\,', ',')
        w, h = _size(kind, rest, fw)
        cur['boxes'].append({'k':kind,'x':x,'y':y,'w':w,'h':h,'t':rest[:40]})
    return ctxs

def forward_refs(ctxs):
    """Connects that name a box defined later in the file, which Pd drops while
    loading the rest without complaint worth reading (C-10, test/README.md).
    Exact, not a heuristic: it is what Pd itself does."""
    out = []
    for ctx in ctxs:
        for (src, _, dst, _), nseen in zip(ctx['conns'], ctx.get('cseen', [])):
            late = [n for n in (src, dst) if n >= nseen]
            if late:
                out.append((ctx['label'], src, dst, sorted(late), nseen))
    return out


def seg_rect(p, q, r):
    # does segment p-q intersect axis-aligned rect r (x,y,w,h)?
    x0,y0,x1,y1 = r['x'], r['y'], r['x']+r['w'], r['y']+r['h']
    def code(px,py):
        c = 0
        if px < x0: c |= 1
        elif px > x1: c |= 2
        if py < y0: c |= 4
        elif py > y1: c |= 8
        return c
    (ax,ay),(bx,by) = p,q
    ca, cb = code(ax,ay), code(bx,by)
    for _ in range(64):
        if not (ca | cb): return True
        if ca & cb: return False
        c = ca or cb
        if c & 8:   px, py = ax+(bx-ax)*(y1-ay)/(by-ay), y1
        elif c & 4: px, py = ax+(bx-ax)*(y0-ay)/(by-ay), y0
        elif c & 2: px, py = x1, ay+(by-ay)*(x1-ax)/(bx-ax)
        else:       px, py = x0, ay+(by-ay)*(x0-ax)/(bx-ax)
        if c == ca: ax, ay, ca = px, py, code(px,py)
        else:       bx, by, cb = px, py, code(px,py)
    return False

def malformed_records(path):
    """Records that do not begin with '#'. There should never be any.

    The signature of a '#X text' rewritten by scanning for the next ';' (C-14),
    named here because otherwise the orphaned tail shows up only as TOO SMALL.
    """
    src = open(path, encoding='utf-8').read()
    out = []
    for rec in re.split(r'(?<!\\);', src):
        rec = rec.strip()
        if rec and not rec.startswith('#'):
            out.append(rec.replace('\n', ' ')[:70])
    return out


def check(path):
    bad = malformed_records(path)
    if bad:
        print(f"{path}")
        for b in bad:
            print(f"    PROBLEM MALFORMED RECORD -- does not start with '#': {b!r}")
        print("      A '#X text' was almost certainly split by an UNESCAPED ';'.")
        print("      Escaped semicolons are legal inside a comment and this repo")
        print("      uses them, so never rewrite one by scanning for the next ';'")
        print("      -- replace the whole line. See C-14.")
        return False
    ctxs = parse(path)
    allok = True
    fwd = forward_refs(ctxs)
    if fwd:
        print(f"{path}")
        for label, src, dst, late, nseen in fwd:
            print(f"    PROBLEM FORWARD CONNECT {src} -> {dst} in {label}: "
                  f"box {late} is defined LATER in the file "
                  f"(only {nseen} boxes existed at that line)")
        print("      Pd replays a canvas top to bottom, so it drops this cord and")
        print("      loads anyway -- the patch is not wired and nothing says so.")
        print("      C-10: append boxes at the end AND MOVE EVERY CONNECT THAT")
        print("      NAMES THEM with it, including ones you only EDITED in place.")
        allok = False
    for ci, ctx in enumerate(ctxs):
        boxes, conns, label = ctx['boxes'], ctx['conns'], ctx['label']
        if not boxes: continue
        probs, notes = [], []
        hit = lambda a,b: not (a['x']+a['w']<=b['x'] or b['x']+b['w']<=a['x']
                            or a['y']+a['h']<=b['y'] or b['y']+b['h']<=a['y'])
        for i in range(len(boxes)):
            for j in range(i+1, len(boxes)):
                if hit(boxes[i], boxes[j]):
                    notes.append(f"BOX/BOX  {boxes[i]['k']}@({boxes[i]['x']},{boxes[i]['y']}) '{boxes[i]['t']}'\n"
                                 f"      vs {boxes[j]['k']}@({boxes[j]['x']},{boxes[j]['y']}) '{boxes[j]['t']}'")
        nout, nin = {}, {}
        for s_,so,d,di in conns:
            nout[s_] = max(nout.get(s_,0), so); nin[d] = max(nin.get(d,0), di)
        for s_,so,d,di in conns:
            if s_ >= len(boxes) or d >= len(boxes):
                probs.append(f"BAD CONNECT {s_} {so} {d} {di} (only {len(boxes)} boxes)"); continue
            a, b = boxes[s_], boxes[d]
            if a['k'] == 'text' or b['k'] == 'text':
                probs.append(f"CONNECT/COMMENT cord {s_}:{so} -> {d}:{di} touches a comment "
                             f"-- indices are probably off by one "
                             f"({a['k']} '{a['t'][:24]}' -> {b['k']} '{b['t'][:24]}')")
                continue
            ax = a['x'] + 7 + (so * (a['w']-14) / max(1, nout.get(s_,0)))
            bx = b['x'] + 7 + (di * (b['w']-14) / max(1, nin.get(d,0)))
            p, q = (ax, a['y']+a['h']), (bx, b['y'])
            for k, r in enumerate(boxes):
                if k in (s_,d): continue
                if seg_rect(p, q, r):
                    notes.append(f"CORD/BOX cord {s_}:{so} -> {d}:{di} crosses "
                                 f"{r['k']}@({r['x']},{r['y']}) '{r['t']}'")
        mx = max(b['x']+b['w'] for b in boxes); my = max(b['y']+b['h'] for b in boxes)
        fits = True
        if ci == 0:
            cm = re.match(r'#N canvas \d+ \d+ (\d+) (\d+)', open(path).readline())
            cw, ch = int(cm.group(1)), int(cm.group(2))
            fits = mx <= cw and my <= ch
            size = f"extent {mx:.0f}x{my:.0f} canvas {cw}x{ch}"
        else:
            size = f"extent {mx:.0f}x{my:.0f}"
        if probs or not fits: allok = False
        nprob = len(probs) + (0 if fits else 1)
        print(f"{label:34} {len(boxes):3} boxes {len(conns):3} cords  "
              f"{nprob} problems  {len(notes)} notes  "
              f"{size}{'' if fits else '  <-- TOO SMALL (PROBLEM)'}")
        for p_ in probs: print("    PROBLEM", p_.replace("\n", "\n      "))
        for n_ in notes: print("    note   ", n_.replace("\n", "\n      "))
    return allok

def list_boxes(path):
    """Print the index of every box, exactly as `#X connect` counts them:
    comments count, `#X declare` does not, a subpatch's contents do not but its
    `#X restore` does."""
    for ctx in parse(path):
        if not ctx['boxes']: continue
        print(f"--- {ctx['label']}")
        for i, b in enumerate(ctx['boxes']):
            t = b['t'] if len(b['t']) <= 58 else b['t'][:55] + "..."
            print(f"  {i:3}  {b['k']:<11} @({b['x']:>5},{b['y']:>5})  {t}")


args = sys.argv[1:]
if args and args[0] == "--boxes":
    for f in args[1:]:
        list_boxes(f)
    sys.exit(0)

# No patches is a failure, not a pass: all([]) is True, and gates.py feeds this
# through a shell glob that can stop matching.
if not args:
    sys.exit("pd-layout-check: no patches to check. The glob that feeds this "
             "matched nothing, which is a failure and not a pass -- run it from "
             "the repo root as: python3 test/gate/pd-layout-check.py \"Cut It\"/*.pd")

ok = all([check(f) for f in args])

# The count, so a drop in files checked is visible.
print(f"\n{len(args)} patch(es) checked")
sys.exit(0 if ok else 1)
