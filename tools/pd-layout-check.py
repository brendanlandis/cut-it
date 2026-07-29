#!/usr/bin/env python3
"""Static layout check for Pd patches.

Reports three things, none of which Pd itself will tell you:

  BOX/BOX    two boxes overlap
  CORD/BOX   a connection is drawn straight through an unrelated box
  TOO SMALL  content extends past the saved canvas size

Layout is the only structural documentation Pd has, and a comment placed
between the logic and a message column gets cords drawn through it. That is
invisible until you open the patch and look, which on this project means a
round trip. Run this instead:

    python3 tools/pd-layout-check.py "Cut It"/*.pd

Exits non-zero if anything is wrong. Box sizes are ESTIMATED from the text
(7 px/char, 18 px/line) since Pd computes them from font metrics at load, so
treat a couple of pixels either way as noise -- it is a smell detector, not a
renderer.
"""
import re, sys
CW, LH = 7.0, 18.0

def _size(kind, rest, fw):
    first = rest.split(' ')[0]
    if kind == 'floatatom':      return 45, 22
    if first == 'hsl':           return 138, 23
    if first == 'hradio':        return 53, 23
    if first in ('bng', 'tgl'):  return 23, 23
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
    for ln in open(path):
        ln = ln.rstrip('\n').rstrip(';')
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
            cur['conns'].append(tuple(int(g) for g in c.groups())); continue
        m = re.match(r'#X (obj|msg|text|floatatom) (-?\d+) (-?\d+) ?(.*)$', ln)
        if not m: continue
        kind, x, y, rest = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4)
        fw = None
        fm = re.search(r',\s*f (\d+)$', rest)
        if fm: fw = int(fm.group(1)); rest = rest[:fm.start()]
        rest = rest.replace('\\,', ',')
        w, h = _size(kind, rest, fw)
        cur['boxes'].append({'k':kind,'x':x,'y':y,'w':w,'h':h,'t':rest[:40]})
    return ctxs

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

def check(path):
    ctxs = parse(path)
    allok = True
    for ci, ctx in enumerate(ctxs):
        boxes, conns, label = ctx['boxes'], ctx['conns'], ctx['label']
        if not boxes: continue
        probs = []
        hit = lambda a,b: not (a['x']+a['w']<=b['x'] or b['x']+b['w']<=a['x']
                            or a['y']+a['h']<=b['y'] or b['y']+b['h']<=a['y'])
        for i in range(len(boxes)):
            for j in range(i+1, len(boxes)):
                if hit(boxes[i], boxes[j]):
                    probs.append(f"BOX/BOX  {boxes[i]['k']}@({boxes[i]['x']},{boxes[i]['y']}) '{boxes[i]['t']}'\n"
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
                    probs.append(f"CORD/BOX cord {s_}:{so} -> {d}:{di} crosses "
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
        print(f"{label:34} {len(boxes):3} boxes {len(conns):3} cords  {len(probs)} problems  "
              f"{size}{'' if fits else '  <-- TOO SMALL'}")
        for p_ in probs: print("   ", p_.replace("\n", "\n    "))
    return allok

ok = all([check(f) for f in sys.argv[1:]])
sys.exit(0 if ok else 1)
