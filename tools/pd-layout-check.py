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

def parse(path):
    boxes, conns = [], []
    for ln in open(path):
        ln = ln.rstrip('\n').rstrip(';')
        c = re.match(r'#X connect (\d+) (\d+) (\d+) (\d+)$', ln)
        if c:
            conns.append(tuple(int(g) for g in c.groups())); continue
        m = re.match(r'#X (obj|msg|text|floatatom) (-?\d+) (-?\d+) ?(.*)$', ln)
        if not m: continue
        kind, x, y, rest = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4)
        fw = None
        fm = re.search(r',\s*f (\d+)$', rest)
        if fm: fw = int(fm.group(1)); rest = rest[:fm.start()]
        rest = rest.replace('\\,', ',')
        first = rest.split(' ')[0]
        if kind == 'floatatom':   w, h = 45, 22
        elif first == 'hsl':      w, h = 138, 23
        elif first == 'hradio':   w, h = 53, 23
        elif first in ('bng','tgl'): w, h = 23, 23
        elif fw:
            words, lines, cur = rest.split(), 1, 0
            for wd in words:
                if cur and cur + 1 + len(wd) > fw: lines += 1; cur = len(wd)
                else: cur += (1 if cur else 0) + len(wd)
            w, h = fw*CW + 10, lines*LH + 8
        else: w, h = len(rest)*CW + 10, 22
        boxes.append({'k':kind,'x':x,'y':y,'w':w,'h':h,'t':rest[:40]})
    return boxes, conns

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
    boxes, conns = parse(path)
    probs = []
    hit = lambda a,b: not (a['x']+a['w']<=b['x'] or b['x']+b['w']<=a['x']
                        or a['y']+a['h']<=b['y'] or b['y']+b['h']<=a['y'])
    for i in range(len(boxes)):
        for j in range(i+1, len(boxes)):
            if hit(boxes[i], boxes[j]):
                probs.append(f"BOX/BOX  {boxes[i]['k']}@({boxes[i]['x']},{boxes[i]['y']}) '{boxes[i]['t']}'\n"
                             f"      vs {boxes[j]['k']}@({boxes[j]['x']},{boxes[j]['y']}) '{boxes[j]['t']}'")
    nout, nin = {}, {}
    for s,so,d,di in conns:
        nout[s] = max(nout.get(s,0), so); nin[d] = max(nin.get(d,0), di)
    for s,so,d,di in conns:
        if s >= len(boxes) or d >= len(boxes): 
            probs.append(f"BAD CONNECT {s} {so} {d} {di}"); continue
        a, b = boxes[s], boxes[d]
        ax = a['x'] + 7 + (so * (a['w']-14) / max(1, nout.get(s,0)))
        bx = b['x'] + 7 + (di * (b['w']-14) / max(1, nin.get(d,0)))
        p, q = (ax, a['y']+a['h']), (bx, b['y'])
        for k, r in enumerate(boxes):
            if k in (s,d): continue
            if seg_rect(p, q, r):
                probs.append(f"CORD/BOX cord {s}:{so} -> {d}:{di} crosses "
                             f"{r['k']}@({r['x']},{r['y']}) '{r['t']}'")
    mx = max(b['x']+b['w'] for b in boxes); my = max(b['y']+b['h'] for b in boxes)
    cm = re.match(r'#N canvas \d+ \d+ (\d+) (\d+)', open(path).readline())
    cw, ch = int(cm.group(1)), int(cm.group(2))
    fits = mx <= cw and my <= ch
    print(f"{path:22} {len(boxes):3} boxes {len(conns):3} cords  {len(probs)} problems  "
          f"extent {mx:.0f}x{my:.0f} canvas {cw}x{ch}{'' if fits else '  <-- TOO SMALL'}")
    for p_ in probs: print("   ", p_.replace("\n", "\n    "))
    return not probs and fits

ok = all([check(f) for f in sys.argv[1:]])
sys.exit(0 if ok else 1)
