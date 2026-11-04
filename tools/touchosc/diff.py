#!/usr/bin/env python3
"""What was changed in TouchOSC's editor: CutIt.tosc as saved from the editor, against what
build.py makes, control by control.

    python3 tools/touchosc/diff.py            the changes, or "no changes"
    python3 tools/touchosc/diff.py FILE.tosc  another saved copy instead of CutIt.tosc

The workflow (Brendan, 2026-11-04): he moves, resizes or recolors something in TouchOSC on the
Mac and saves; this says what changed; the change goes into build.py, which is the layout's
source; the next build writes CutIt.tosc again. build.py refuses to overwrite a CutIt.tosc saved
from the editor until then, so a tweak is never lost.

Controls are matched by name, so a renamed control reads as one removed and one added. A frame
prints as x y w h, a color as 0-255 r g b and alpha, so a value can go straight into build.py.
"""
import importlib.util
import os
import sys
import xml.dom.minidom
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("build_touchosc", os.path.join(HERE, "build.py"))
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)


def text_of(el):
    return "".join(c.data for c in el.childNodes
                   if c.nodeType in (c.TEXT_NODE, c.CDATA_SECTION_NODE)).strip()


def value_of(p):
    t, v = p.getAttribute("type"), p.getElementsByTagName("value")[0]
    if t == "c":
        r, g, b, a = (float(text_of(v.getElementsByTagName(k)[0])) for k in "rgba")
        return "%d %d %d %.2g" % (round(r * 255), round(g * 255), round(b * 255), a)
    if t == "r":
        return " ".join("%g" % float(text_of(v.getElementsByTagName(k)[0])) for k in "xywh")
    if t == "f":
        return "%g" % float(text_of(v) or 0)
    return text_of(v)


def controls(xml_text):
    """{path: (type, {property: value}, {value key: default})}, a control's path being its
    ancestors' names and its own, so two controls of one name in different groups stay apart."""
    doc = xml.dom.minidom.parseString(xml_text)
    out = {}

    def walk(n, path):
        props, vals = {}, {}
        for c in n.childNodes:
            if c.nodeName == "properties":
                for p in c.getElementsByTagName("property"):
                    if p.parentNode is c:
                        props[text_of(p.getElementsByTagName("key")[0])] = value_of(p)
            elif c.nodeName == "values":
                for v in c.getElementsByTagName("value"):
                    if v.parentNode is c:
                        d = v.getElementsByTagName("default")
                        vals[text_of(v.getElementsByTagName("key")[0])] = \
                            text_of(d[0]) if d else ""
        name = props.get("name") or "(unnamed %s)" % n.getAttribute("type")
        here = path + [name]
        out["/".join(here)] = (n.getAttribute("type"), props, vals)
        for c in n.childNodes:
            if c.nodeName == "children":
                for k in c.childNodes:
                    if k.nodeName == "node":
                        walk(k, here)

    walk(doc.getElementsByTagName("node")[0], [])
    return out


def changes(saved_xml, built_xml):
    """Readable lines, one a change; empty when the two lay out the same."""
    a, b = controls(built_xml), controls(saved_xml)
    lines = []
    for path in sorted(set(b) - set(a)):
        t, p, _ = b[path]
        lines.append("+ %s  a new %s at %s" % (path, t, p.get("frame", "?")))
    for path in sorted(set(a) - set(b)):
        lines.append("- %s  removed" % path)
    for path in sorted(set(a) & set(b)):
        (ta, pa, va), (tb, pb, vb) = a[path], b[path]
        if ta != tb:
            lines.append("~ %s  type %s -> %s" % (path, ta, tb))
        for k in sorted(set(pa) | set(pb)):
            if k == "script":
                if pa.get(k) != pb.get(k):
                    lines.append("~ %s  its script was edited" % path)
            elif k in pa and k in pb and pa[k] != pb[k]:
                lines.append("~ %s  %s: %s -> %s" % (path, k, pa[k], pb[k]))
            elif k in pb and k not in pa:
                lines.append("~ %s  %s: set to %s" % (path, k, pb[k]))
        for k in sorted(set(va) & set(vb)):
            if va[k] != vb[k]:
                lines.append("~ %s  value %s: %s -> %s" % (path, k, va[k], vb[k]))
    return lines


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else B.OUT
    saved = zlib.decompress(open(path, "rb").read()).decode("utf-8")
    lines = changes(saved, B.build())
    print("\n".join(lines) if lines else "no changes: %s is what build.py makes"
          % os.path.basename(path))


if __name__ == "__main__":
    main()
