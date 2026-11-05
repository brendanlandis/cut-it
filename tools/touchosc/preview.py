#!/usr/bin/env python3
"""Draw the phone's pages as the phone shows them, to look at a layout without the phone.

    python3 tools/touchosc/preview.py [OUT_DIR]        one SVG a page, and index.html with them all

Each page is drawn at the phone's size in points (an iPhone 11 in landscape): its own tab bar at
the top, the outer bar hidden as the root's script hides it, then its controls where build.py puts
them, a button's resting fill at 26% of its color as TouchOSC draws it. The editor's 20-point
grid, anchored at the document's center as TouchOSC anchors it, is laid over the page in faint
lines, and the notch's margin in a red one, so what is off the
grid or too close to the edge shows at a glance.

It draws from build.py's output, not from CutIt.tosc, and approximates TouchOSC's drawing (fonts,
corner radii, a knob's arc): the phone is the oracle for how it looks; this is for layout.
"""
import html
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("diff_touchosc", os.path.join(HERE, "diff.py"))
D = importlib.util.module_from_spec(spec)
spec.loader.exec_module(D)
B = D.B

DIM = 66 / 255          # a resting fill's share of its color, as the gate's contrast audit has it
GRID = 20               # TouchOSC's editor grid, editor.grid.step in its app.cfg


def rgba(s, alpha=None):
    r, g, b, a = s.split()
    a = float(a) if alpha is None else alpha
    return "rgba(%s,%s,%s,%.3f)" % (r, g, b, a)


def frame(p):
    return [float(v) for v in p.get("frame", "0 0 0 0").split()]


def draw(kind, p, v, x, y, w, h):
    """SVG for one control at absolute x, y."""
    out = []
    col = p.get("color", "0 0 0 1")
    if kind == "BUTTON":
        on = float(v.get("x") or 0) >= 0.5
        circle = p.get("shape") == "2"
        fill = rgba(col) if on else rgba(col, DIM * float(col.split()[3]))
        stroke = rgba(col) if p.get("outline") == "1" else "none"
        if circle:
            out.append('<circle cx="%g" cy="%g" r="%g" fill="%s" stroke="%s"/>'
                       % (x + w / 2, y + h / 2, min(w, h) / 2, fill, stroke))
        else:
            out.append('<rect x="%g" y="%g" width="%g" height="%g" rx="3" fill="%s" stroke="%s"/>'
                       % (x, y, w, h, fill, stroke))
    elif kind == "FADER":
        fill = rgba(col, DIM) if p.get("background") != "0" else "none"
        stroke = rgba(col) if p.get("outline") != "0" else "none"
        out.append('<rect x="%g" y="%g" width="%g" height="%g" rx="3" fill="%s" stroke="%s"/>'
                   % (x, y, w, h, fill, stroke))
    elif kind == "RADIO":
        # a segment each, the selected one at full strength, the rest at their resting fill
        n, sel = int(p.get("steps") or 1), int(float(v.get("x") or 0))
        across = p.get("orientation") == "1"
        for i in range(n):
            sx, sy, sw, sh = ((x + i * w / n, y, w / n, h) if across
                              else (x, y + i * h / n, w, h / n))
            out.append('<rect x="%g" y="%g" width="%g" height="%g" fill="%s" stroke="%s"/>'
                       % (sx, sy, sw, sh, rgba(col) if i == sel else rgba(col, DIM), rgba(col)))
    elif kind == "RADIAL":
        r = min(w, h) / 2
        out.append('<circle cx="%g" cy="%g" r="%g" fill="%s" stroke="%s" stroke-width="2"/>'
                   % (x + w / 2, y + h / 2, r - 1, rgba(col, DIM), rgba(col)))
    elif kind in ("LABEL", "TEXT"):
        text = v.get("text", "")
        size = float(p.get("textSize") or 15)
        ink = rgba(p.get("textColor", "240 240 240 1"))
        mono = p.get("font") == "1"
        fam = "Menlo, monospace" if mono else "Ubuntu, Helvetica, Arial, sans-serif"
        align = p.get("textAlignH", "2")
        anchor, tx = {"1": ("start", x + 4), "3": ("end", x + w - 4)}.get(align,
                                                                        ("middle", x + w / 2))
        if p.get("background") == "1":
            out.append('<rect x="%g" y="%g" width="%g" height="%g" fill="%s"/>'
                       % (x, y, w, h, rgba(col, DIM)))
        lines = text.split("\n") if kind == "TEXT" else [text]
        if kind == "TEXT":
            for i, line in enumerate(lines):
                out.append('<text x="%g" y="%g" font-family="%s" font-size="%g" fill="%s" '
                           'text-anchor="%s">%s</text>'
                           % (tx, y + size * 1.2 * (i + 1), fam, size, ink, anchor,
                              html.escape(line)))
        else:
            out.append('<text x="%g" y="%g" font-family="%s" font-size="%g" fill="%s" '
                       'text-anchor="%s" dominant-baseline="central">%s</text>'
                       % (tx, y + h / 2, fam, size, ink, anchor, html.escape(text)))
    return "".join(out)


def pages(xml):
    """[(page name, tab label, [(kind, props, values, x, y, w, h)], [its pager's tab labels])]
    as the phone shows each: every tab of every Launchpad page."""
    c = D.controls(xml)
    out, tabs = {}, {}
    for path, (kind, p, v) in c.items():
        parts = path.split("/")
        # root/pages/<outer page>/<inner pager>/<page>[/<control>...]
        if len(parts) < 5 or parts[1] != "pages":
            continue
        key = (parts[2], parts[4])
        if len(parts) == 5:
            tab = p.get("tabLabel", parts[4])
            tabs.setdefault(parts[2], []).append(tab)
            out[key] = (parts[4], tab, [], tabs[parts[2]])
            continue
        # the control's own frame, plus every enclosing group's below the page
        x = y = 0
        for i in range(6, len(parts)):
            g = frame(c["/".join(parts[:i])][1])
            x, y = x + g[0], y + g[1]
        f = frame(p)
        out[key][2].append((kind, p, v, x + f[0], B.TAB + y + f[1], f[2], f[3]))
    return [out[k] for k in out]


def svg(name, tab, items, grid=True, tabs=None):
    W, H, TAB = B.W, B.H, B.TAB
    s = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">'
         % (W, H, W, H), '<rect width="%d" height="%d" fill="#000"/>' % (W, H)]
    # the page's own tab bar: its pager's tabs side by side, this one active
    tabs = tabs or [tab]
    tw = W / len(tabs)
    for i, t in enumerate(tabs):
        on = t == tab
        s.append('<rect x="%g" y="0" width="%g" height="%d" fill="%s" stroke="#000"/>'
                 % (i * tw, tw, TAB, rgba("255 31 63 1") if on else rgba("34 34 34 1")))
        s.append('<text x="%g" y="%g" font-family="Ubuntu, Helvetica, Arial, sans-serif" '
                 'font-size="22" fill="%s" text-anchor="middle" dominant-baseline="central">%s'
                 '</text>' % (i * tw + tw / 2, TAB / 2, "#000" if on else "#f0f0f0",
                              html.escape(t)))
    if grid:
        # the editor's grid is anchored at the document's center: B.OX and B.OY in a page's
        # coordinates, which start under the tab bar here
        for gx in range(B.OX, W + 1, GRID):
            s.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="rgba(255,255,255,0.07)"/>'
                     % (gx, TAB, gx, H))
        for gy in range(B.OY, H - TAB + 1, GRID):
            s.append('<line x1="0" y1="%d" x2="%d" y2="%d" stroke="rgba(255,255,255,0.07)"/>'
                     % (TAB + gy, W, TAB + gy))
        s.append('<line x1="%d" y1="0" x2="%d" y2="%d" stroke="rgba(255,60,60,0.5)" '
                 'stroke-dasharray="4 4"/>' % (W - B.R, W - B.R, H))
    for kind, p, v, x, y, w, h in items:
        s.append(draw(kind, p, v, x, y, w, h))
    s.append("</svg>")
    return "\n".join(s)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "preview")
    os.makedirs(out, exist_ok=True)
    doc = ['<!doctype html><meta charset="utf-8"><title>Cut It phone preview</title>',
           '<body style="background:#222;color:#ddd;font:14px Helvetica;margin:16px">']
    for name, tab, items, tabs in pages(B.build()):
        with open(os.path.join(out, name + ".svg"), "w", encoding="utf-8") as fh:
            fh.write(svg(name, tab, items, tabs=tabs))
        doc.append('<h3>%s</h3><img src="%s.svg" width="%d" style="max-width:100%%">'
                   % (html.escape(tab), name, B.W))
    with open(os.path.join(out, "index.html"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(doc))
    print("wrote %s" % os.path.join(out, "index.html"))


if __name__ == "__main__":
    main()
