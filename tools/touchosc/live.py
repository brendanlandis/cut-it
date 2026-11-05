#!/usr/bin/env python3
"""Put the layout into the document the Mac's TouchOSC has open, by editing it in place, so
TouchOSC keeps one copy open (Brendan, 2026-11-05: "I notice more and more documents opening in
the Mac app. We should probably keep one copy open at a time").

    python3 tools/touchosc/live.py              make the open CutIt document what CutIt.tosc holds
    python3 tools/touchosc/live.py --diff       say how it differs, and change nothing
    python3 tools/touchosc/live.py --force      and over edits made in TouchOSC's editor, unsaved
    python3 tools/touchosc/live.py FILE.tosc    another layout instead of CutIt.tosc

push.sh runs it after build.py. `open` added a document every time (ten had piled up), and
nothing in TouchOSC closes one. Its MCP server edits the open one instead: TouchOSC 1.5.4,
launched with --mcp.enabled=true, at http://127.0.0.1:13579/mcp, JSON-RPC over HTTP
(~/Sites/!reference/touchosc.md, *MCP server*). TOUCHOSC_MCP_PORT points it at another port.

A push reads the whole document, every control's properties, values and messages, in one
JSON-RPC batch (~50 ms for 139 controls), matches the build's controls to the document's by name
(every name is its own: touchosc-assert holds it) and sends only what differs. Each edit reaches
the phone at once through the editor server, but not at one price: a property or a value goes as a
few hundred bytes, while a control created, moved or deleted resends the whole document (~110 KB;
measured 2026-11-05). So a control already there is moved, not made again; one of the same type
under the same parent, named for nothing in the build, is renamed into a missing one; and the
deletions go in one call. Then it reads the document back, and exits 0 only when it is the build.

What is compared is what the file holds: the tree (each control's parent and its place among its
siblings, later ones drawing on top), each property with its type, each value's default and
flags, the messages (the build has none: its scripts call sendOSC), and the document's size,
color and routing. A value's current state is not: the editor's own tabs move a pager's page. A
property the file leaves out has TouchOSC's load default, "" for `tag` and `script`; one TouchOSC
has and the file can't name is left alone.

It edits only a CutIt document (one opened from a CutIt.tosc), making it TouchOSC's active one
first, and refuses anything else. When more than one is open it says so: it can't close one.
Edits need TouchOSC's EDITOR mode; in CONTROL_SURFACE mode it switches for the push and back.
It never calls undo: the undo history is shared with Brendan's edits.

Edits made in TouchOSC's editor and not saved are kept from a push, as build.py keeps a saved
one: a push that would change something the last push didn't leave, and the build doesn't want,
is refused (exit 4) with what it is. File > Save keeps it, for diff.py and build.py; --force
discards it. What the last push left is in .pushed, untracked.

Exit status: 0 the document is the build; 2 nothing to push to (no MCP server answering, or no
CutIt document open), so push.sh opens the file as before; 4 unsaved edits in the way; 1 anything
else, with what still differs.
"""
import collections
import http.client
import json
import os
import sys
import time
import xml.etree.ElementTree as ET
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "CutIt.tosc")
PUSHED = os.path.join(HERE, ".pushed")    # what the last push left in TouchOSC, untracked
HOST, PORT = "127.0.0.1", int(os.environ.get("TOUCHOSC_MCP_PORT", "13579"))

TYPES = {"b": "BOOLEAN", "i": "INTEGER", "f": "FLOAT", "s": "STRING", "c": "COLOR",
         "r": "RECTANGLE"}
# What TouchOSC gives a property the file leaves out, read off the document opened from the build
# (2026-11-05): every control has these two, and the build writes a script only where it has one.
UNWRITTEN = {"tag": ("STRING", ""), "script": ("STRING", "")}
# A value's type where the document hasn't the control yet to say (a radio's x is an INTEGER).
VALUE_TYPES = {"touch": "BOOLEAN", "text": "STRING", "page": "INTEGER"}
# The document's routing when the file gives none, as the one opened from the build has it.
ROUTING = {s: ["local", "midi", "osc"] for s in ("gamepad", "local", "midi", "osc", "touch")}


class Unreachable(Exception):
    """Nothing to push to: push.sh opens the file instead."""


class Failed(Exception):
    """TouchOSC refused an edit or a read."""


# ------------------------------------------------------------------ the MCP server
class MCP:
    """TouchOSC's MCP server: JSON-RPC over one kept-alive HTTP connection. Requests batch, a list
    of calls in one POST answered in order, which is what makes reading every control cheap."""

    def __init__(self):
        self.n = 0
        self.conn = http.client.HTTPConnection(HOST, PORT, timeout=1)
        try:
            self.conn.connect()
        except OSError as e:
            raise Unreachable("TouchOSC's MCP server is not answering at %s:%d (%s)"
                              % (HOST, PORT, e.strerror or e))
        self.conn.sock.settimeout(60)
        self.post({"jsonrpc": "2.0", "id": 0, "method": "initialize",
                   "params": {"protocolVersion": "2025-03-26", "capabilities": {},
                              "clientInfo": {"name": "cut-it live.py", "version": "1"}}})

    def post(self, body):
        try:
            self.conn.request("POST", "/mcp", json.dumps(body),
                              {"Content-Type": "application/json",
                               "Accept": "application/json, text/event-stream"})
            r = self.conn.getresponse()
            data = r.read().decode("utf-8")
        except OSError as e:
            raise Unreachable("TouchOSC's MCP server stopped answering (%s)" % e)
        if r.status != 200:
            raise Unreachable("TouchOSC's MCP server answered HTTP %d" % r.status)
        if "text/event-stream" in (r.getheader("Content-Type") or ""):
            data = "".join(line[5:] for line in data.splitlines() if line.startswith("data:"))
        return json.loads(data)

    def batch(self, calls):
        """[(tool, arguments)] -> their results in order; Failed names every one refused, the
        rest having run."""
        if not calls:
            return []
        first = self.n + 1
        self.n += len(calls)
        out = self.post([{"jsonrpc": "2.0", "id": first + i, "method": "tools/call",
                          "params": {"name": t, "arguments": a}}
                         for i, (t, a) in enumerate(calls)])
        out = sorted(out if isinstance(out, list) else [out], key=lambda r: r.get("id") or 0)
        results, bad = [], []
        for (tool, args), r in zip(calls, out):
            if "error" in r:
                bad.append("%s: %s" % (tool, r["error"].get("message")))
                results.append(None)
                continue
            text = "".join(c.get("text", "") for c in r["result"].get("content", []))
            if r["result"].get("isError"):
                bad.append("%s %s: %s" % (tool, json.dumps(args)[:120], text))
                results.append(None)
                continue
            try:
                results.append(json.loads(text))
            except ValueError:
                results.append(text)
        if len(out) != len(calls):
            bad.append("%d calls sent, %d answered" % (len(calls), len(out)))
        if bad:
            raise Failed("TouchOSC refused:\n  " + "\n  ".join(bad))
        return results

    def call(self, tool, **args):
        return self.batch([(tool, args)])[0]


# ------------------------------------------------------------------ the two trees
class Node:
    def __init__(self, id_, name, type_, parent=None):
        self.id, self.name, self.type, self.parent = id_, name, type_, parent
        self.children, self.props, self.values, self.messages = [], {}, {}, {}

    def walk(self):
        yield self
        for c in self.children:
            yield from c.walk()


def number(typ, v):
    if typ == "COLOR":
        return {k: float(v.find(k).text) for k in "rgba"}
    if typ == "RECTANGLE":
        return {k: float(v.find(k).text) for k in "xywh"}
    if typ == "BOOLEAN":
        return (v.text or "").strip() in ("1", "true")
    if typ == "INTEGER":
        return int(float(v.text))
    if typ == "FLOAT":
        return float(v.text)
    return v.text or ""


def target(path):
    """The layout in a .tosc file, as a tree of Nodes, its values' defaults still text."""
    lexml = ET.fromstring(zlib.decompress(open(path, "rb").read()).decode("utf-8"))

    def walk(el, parent):
        n = Node(el.get("ID"), None, el.get("type"), parent)
        for p in el.find("properties") if el.find("properties") is not None else ():
            typ = TYPES[p.get("type")]
            n.props[p.find("key").text] = (typ, number(typ, p.find("value")))
        for v in el.find("values") if el.find("values") is not None else ():
            n.values[v.find("key").text] = {
                "default": v.findtext("default") or "",
                "locked": v.findtext("locked") == "1",
                "lockedDefaultCurrent": v.findtext("lockedDefaultCurrent") == "1",
                "pullDefault": int(v.findtext("defaultPull") or 0)}
        if el.find("messages") is not None and len(el.find("messages")):
            sys.exit("live: %s has MIDI or OSC messages, and a live push doesn't carry them yet"
                     % os.path.basename(path))
        n.name = n.props.get("name", ("STRING", ""))[1]
        kids = el.find("children")
        n.children = [walk(k, n) for k in kids] if kids is not None else []
        return n

    root = walk(lexml.find("node"), None)
    names = collections.Counter(n.name for n in root.walk())
    twice = sorted(k for k, c in names.items() if c > 1)
    if twice:
        sys.exit("live: %s names more than one control %s: they are matched by name"
                 % (os.path.basename(path), ", ".join(twice)))
    return root


def read(m):
    """The active document: (its get_document, its tree of Nodes, every control's details)."""
    doc = m.call("get_document")

    def walk(c, parent):
        n = Node(c["id"], c["name"], c["type"], parent)
        n.children = [walk(k, n) for k in c.get("children", [])]
        return n

    root = walk(doc["root"], None)
    nodes = list(root.walk())
    for n, c in zip(nodes, m.batch([("get_control", {"id": n.id}) for n in nodes])):
        n.props = {k: (p["type"], p["value"]) for k, p in c["properties"].items()}
        n.values = c["values"]
        n.messages = c.get("messages", {})
    return doc, root


# ------------------------------------------------------------------ comparing
def norm(typ, v):
    """A value as compared: a color in 0-255 steps, a frame and a float to what the file holds."""
    if typ == "COLOR":
        return [round(v.get(k, 1.0) * 255) for k in "rgba"]
    if typ == "RECTANGLE":
        return [round(v[k], 2) for k in "xywh"]
    if typ == "FLOAT":
        return round(float(v), 4)
    if typ == "INTEGER":
        return int(v)
    if typ == "BOOLEAN":
        return bool(v)
    return v


def as_type(typ, text):
    """A value's default as the file has it, text, in the type TouchOSC gives it."""
    if typ == "FLOAT":
        return float(text or 0)
    if typ == "INTEGER":
        return int(float(text or 0))
    if typ == "BOOLEAN":
        return text.strip().lower() in ("1", "true")
    return text


def facts(root, doc=None, types=None):
    """Everything compared, flat: {(control, what, key): value}. doc is the live document's
    get_document, for its routing and the rest; a build's tree has none, and takes its values'
    types from types, the live tree's {name: Node}."""
    f = {}
    if doc is not None:
        f[("", "size")] = [round(doc["size"]["w"], 2), round(doc["size"]["h"], 2)]
        f[("", "color")] = norm("COLOR", doc["color"])
        f[("", "routing")] = {s: sorted(t) for s, t in doc.get("routing", {}).items()}
        f[("", "includes")] = sorted(i if isinstance(i, str) else i.get("name", "?")
                                     for i in doc.get("scriptIncludes", []))
        f[("", "creator")], f[("", "comments")] = doc.get("creator", ""), doc.get("comments", "")
    else:
        fr = root.props["frame"][1]
        f[("", "size")] = [round(fr["w"], 2), round(fr["h"], 2)]
        f[("", "color")] = norm("COLOR", root.props["color"][1])
        f[("", "routing")] = ROUTING
        f[("", "includes")] = []
        f[("", "creator")], f[("", "comments")] = "", ""
    count = collections.Counter(n.name for n in root.walk())
    seen = set()
    for n in root.walk():
        if n.name in seen:
            continue
        seen.add(n.name)
        k = n.name
        f[(k, "count", "")] = count[k]
        f[(k, "type", "")] = n.type
        f[(k, "parent", "")] = n.parent.name if n.parent else ""
        f[(k, "index", "")] = n.parent.children.index(n) if n.parent else 0
        props = dict(UNWRITTEN) if doc is None else {}
        props.update(n.props)
        live = (types or {}).get(k)
        for p, (typ, v) in props.items():
            # A property the live control hasn't got at all, a knob's bar or cursor say, TouchOSC
            # can't hold: settle() warns of each and leaves it out, as opening the file does, so
            # it isn't a difference either (2026-11-05: the effect knobs failed every push).
            if live is not None and p not in live.props and p not in UNWRITTEN:
                continue
            f[(k, "p", p)] = [typ, norm(typ, v)]
        for key, v in n.values.items():
            if doc is not None:
                typ = v["type"]
                d = v["default"]
            else:
                typ = (live.values[key]["type"] if live is not None and key in live.values
                       else VALUE_TYPES.get(key, "FLOAT"))
                d = as_type(typ, v["default"])
            f[(k, "v", key)] = [typ, norm(typ, d), bool(v["locked"]),
                                bool(v["lockedDefaultCurrent"]), int(v["pullDefault"])]
        f[(k, "messages", "")] = sum(len(v) for v in n.messages.values())
    return f


def differing(have, want):
    """The keys where the document (have) isn't the build (want). A property or value the
    document has and the file can't name is TouchOSC's own, and not compared."""
    out = []
    for k in sorted(set(have) | set(want)):
        if k not in want and len(k) == 3 and k[1] in ("p", "v"):
            continue
        if have.get(k) != want.get(k):
            out.append(k)
    return out


def show(v):
    if isinstance(v, list) and len(v) == 2 and v[0] in ("COLOR", "RECTANGLE"):
        if v[0] == "COLOR":
            r, g, b, a = v[1]
            return "%d %d %d %.2g" % (r, g, b, a / 255)
        return " ".join("%g" % x for x in v[1])
    if isinstance(v, list) and len(v) == 2 and isinstance(v[0], str) and v[0].isupper():
        v = v[1]
    if isinstance(v, list) and len(v) == 5:
        v = "%r%s%s" % (v[1], " locked" if v[2] else "", " (current follows)" if v[3] else "")
    s = v if isinstance(v, str) else json.dumps(v)
    return (s[:40] + "…") if len(s) > 41 else s


def lines(keys, have, want):
    """Readable lines, one a difference: + in the build and not in TouchOSC, - the other way,
    ~ changed, shown as TouchOSC has it -> as the build has it."""
    out, whole = [], set()
    for k in keys:
        if k[1] == "count" and k not in want:
            out.append("- %s  a %s in TouchOSC, not in the build" % (k[0], have[(k[0], "type", "")]))
            whole.add(k[0])
        elif k[1] == "count" and k not in have:
            out.append("+ %s  a %s not in TouchOSC" % (k[0], want[(k[0], "type", "")]))
            whole.add(k[0])
    for k in keys:
        if k[0] in whole:
            continue
        h, w = have.get(k), want.get(k)
        if (k[1] in ("p", "v") and isinstance(h, list) and isinstance(w, list)
                and h[0] != w[0]):
            out.append("~ %s  %s%s: a %s, the build's a %s" % (k[0], "value " if k[1] == "v"
                                                                else "", k[2], h[0], w[0]))
            continue
        what = {"count": "controls of that name", "type": "type", "parent": "in",
                "index": "place among its siblings", "messages": "messages"}.get(k[1], k[-1])
        if k[0] == "":
            out.append("~ the document  %s: %s -> %s" % (k[1], show(have.get(k)), show(want.get(k))))
        elif k[1] == "p" and k[2] == "script":
            out.append("~ %s  its script differs" % k[0])
        else:
            out.append("~ %s  %s%s: %s -> %s" % (k[0], "value " if k[1] == "v" else "", what,
                                                 show(have.get(k, "(none)")),
                                                 show(want.get(k, "(none)"))))
    return out


# ------------------------------------------------------------------ the document
def choose(m, edit):
    """Make a CutIt document TouchOSC's active one, and return its get_document. Raises
    Unreachable when none is open. Says so when more than one is."""
    docs = m.call("list_documents")
    ours = [d for d in docs if os.path.basename(d.get("file") or "") == "CutIt.tosc"]
    if not ours:
        raise Unreachable("TouchOSC has no CutIt document open (it has %s)"
                          % (", ".join(d["name"] for d in docs) or "none"))
    pick = next((d for d in ours if d.get("active")), ours[-1])
    if len(ours) > 1:
        print("TouchOSC has %d CutIt documents open (%s); this pushes to #%d, the %s one. Nothing "
              "here can close one: close the others in TouchOSC, or quit it and push, which "
              "drops the phone until it is connected again by hand."
              % (len(ours), ", ".join("#%d" % d["index"] for d in ours), pick["index"],
                 "active" if pick.get("active") else "last"), file=sys.stderr)
    if not pick.get("active"):
        if not edit:
            raise Failed("CutIt isn't TouchOSC's active document, and --diff changes nothing")
        m.call("set_active_document", index=pick["index"])
    doc = m.call("get_document", depth=0)
    if os.path.basename(doc.get("file") or "") != "CutIt.tosc" or doc.get("index") != pick["index"]:
        raise Failed("TouchOSC's active document is %r (%s), not CutIt: not editing it"
                     % (doc.get("name"), doc.get("file") or "no file"))
    return doc


def restructure(m, want, root):
    """Create, move, rename and delete controls until the document's tree is the build's, a level
    at a time (a control is made inside one made the level before). Returns {name: live id}
    and the number of edits. The document's tree, root, is kept in step with each edit."""
    names = {n.name for n in want.walk()}
    byname = collections.defaultdict(list)
    for n in root.walk():
        byname[n.name].append(n)
    claim, taken = {want.name: root}, {id(root)}
    edits, level, fresh = 0, [want], []

    def inside(n, p):
        while p is not None:
            if p is n:
                return True
            p = p.parent
        return False

    def find(t, lp):
        cands = [n for n in byname.get(t.name, ()) if id(n) not in taken and n.type == t.type]
        here = [n for n in cands if n.parent is lp]
        if here:
            return here[0]
        if lp.type == "PAGER":       # a page can't move between pagers, nor a control into one
            return None
        return next((n for n in cands if n.parent is not None and n.parent.type != "PAGER"
                     and not inside(n, lp)), None)

    def reorder(lp, lc, i, calls):
        j = lp.children.index(lc)
        if j == i:
            return
        lp.children.insert(i, lp.children.pop(j))
        if lp.type == "PAGER":
            calls.append(("move_page", {"pagerID": lp.id, "from": j, "to": i}))
        else:
            calls.append(("move_control", {"id": lc.id, "index": i}))

    while level:
        if fresh:    # a new pager comes with pages of its own, to be renamed into the build's
            for n, c in zip(fresh, m.batch([("get_control", {"id": n.id}) for n in fresh])):
                n.children = [Node(k["id"], k["name"], k["type"], n) for k in c.get("children", [])]
            fresh = []
        calls, made = [], []
        for tp in level:
            lp = claim[tp.name]
            for i, t in enumerate(tp.children):
                lc = find(t, lp)
                if lc is None:
                    lc = next((c for c in lp.children if id(c) not in taken and c.type == t.type
                               and c.name not in names), None)
                    if lc is not None:
                        calls.append(("set_control_properties",
                                      {"id": lc.id, "properties": {"name": t.name}}))
                        lc.name = t.name
                if lc is not None and lc.parent is not lp:
                    calls.append(("move_control", {"id": lc.id, "parentID": lp.id, "index": i}))
                    lc.parent.children.remove(lc)
                    lp.children.insert(i, lc)
                    lc.parent = lp
                elif lc is not None:
                    reorder(lp, lc, i, calls)
                elif lp.type == "PAGER":
                    lc = Node(None, t.name, t.type, lp)
                    calls.append(("add_page", {"pagerID": lp.id}))
                    made.append((len(calls) - 1, lc))
                    lp.children.append(lc)
                    reorder(lp, lc, i, calls)
                else:
                    lc = Node(None, t.name, t.type, lp)
                    calls.append(("create_control", {"type": t.type, "parentID": lp.id, "index": i,
                                                     "name": t.name,
                                                     "frame": t.props["frame"][1]}))
                    made.append((len(calls) - 1, lc))
                    lp.children.insert(i, lc)
                if lc.id is None and t.type == "PAGER":
                    fresh.append(lc)
                taken.add(id(lc))
                claim[t.name] = lc
        if calls:
            res = m.batch(calls)
            for k, n in made:
                n.id = res[k]["id"]
            edits += len(calls)
        level = [c for tp in level for c in tp.children if c.children or c.type == "PAGER"]
    # Whatever is left unclaimed goes: the topmost of it, the rest with it. Pages one at a time,
    # from the last, so the indexes hold; everything else in one call.
    calls, dead = [], []
    for n in list(root.walk()):
        if id(n) in taken or n.parent is None or id(n.parent) not in taken:
            continue
        if n.parent.type == "PAGER":
            calls.append((n.parent.children.index(n), n))
        else:
            dead.append(n)
    calls = [("delete_page", {"pagerID": n.parent.id, "index": i})
             for i, n in sorted(calls, key=lambda c: -c[0])]
    if dead:
        calls.append(("delete_controls", {"ids": [n.id for n in dead]}))
    if calls:
        m.batch(calls)
        edits += len(calls)
    return {k: n.id for k, n in claim.items()}, edits


def settle(m, want, doc, root, ids):
    """Set every property, value and message that differs, a call per control and value, all in
    one batch. Returns the number of edits, and warnings."""
    byid = {n.id: n for n in root.walk()}
    calls, warn = [], []
    have = facts(root, doc)
    wantf = facts(want, types={n.name: n for n in root.walk()})
    for key in ("size", "color", "routing", "includes"):
        if have[("", key)] == wantf[("", key)]:
            continue
        if key == "size":
            calls.append(("set_document_size", {"width": wantf[("", key)][0],
                                                "height": wantf[("", key)][1]}))
        elif key == "color":
            calls.append(("set_document_color", {"color": want.props["color"][1]}))
        elif key == "routing":
            calls.append(("set_document_routing", {"routing": ROUTING}))
        else:
            calls += [("delete_script_include", {"name": i}) for i in have[("", key)]]
    meta = {k: "" for k in ("creator", "comments") if have[("", k)] != ""}
    if meta:
        calls.append(("set_document_meta", meta))
    for t in want.walk():
        n = byid[ids[t.name]]
        props = dict(UNWRITTEN)
        props.update(t.props)
        if t.parent is None:            # the root's frame and color are the document's
            props.pop("frame", None)
            props.pop("color", None)
        send = {}
        for p, (typ, v) in props.items():
            if p not in n.props:
                if p not in UNWRITTEN:
                    warn.append("%s: TouchOSC has no %s on a %s, so it is left out, as it is when "
                                "the file is opened" % (t.name, p, t.type))
                continue
            if n.props[p][0] != typ:
                warn.append("%s: the build writes %s as a %s, and TouchOSC has it as a %s"
                            % (t.name, p, typ, n.props[p][0]))
                continue
            if norm(typ, n.props[p][1]) != norm(typ, v):
                send[p] = v
        if send:
            calls.append(("set_control_properties", {"id": n.id, "properties": send}))
        for key, v in t.values.items():
            if key not in n.values:
                warn.append("%s: TouchOSC has no value %s on a %s" % (t.name, key, t.type))
                continue
            lv = n.values[key]
            w = {"default": as_type(lv["type"], v["default"]), "locked": v["locked"],
                 "lockedDefaultCurrent": v["lockedDefaultCurrent"],
                 "pullDefault": v["pullDefault"]}
            change = {f: w[f] for f in ("locked", "lockedDefaultCurrent", "pullDefault")
                      if lv[f] != w[f]}
            if norm(lv["type"], lv["default"]) != norm(lv["type"], w["default"]):
                change["default"] = change["current"] = w["default"]
            if change:
                calls.append(("set_control_value", dict(id=n.id, key=key, **change)))
        for kind, msgs in n.messages.items():
            calls += [("remove_message", {"id": n.id, "kind": kind, "index": i})
                      for i in reversed(range(len(msgs)))]
    try:
        res = m.batch(calls)
    except Failed:
        # One bad property refuses its control's whole call: set those a property at a time, so
        # the rest land and the bad one is named.
        res = []
        for tool, args in calls:
            if tool == "set_control_properties" and len(args["properties"]) > 1:
                for p, v in args["properties"].items():
                    try:
                        res.append(m.call(tool, id=args["id"], properties={p: v}))
                    except Failed as e:
                        warn.append(str(e))
            else:
                try:
                    res.append(m.call(tool, **args))
                except Failed as e:
                    warn.append(str(e))
    for r in res:
        if isinstance(r, dict) and r.get("scriptStatus", {}).get("ok") is False:
            warn.append("a script doesn't compile: %s" % r["scriptStatus"].get("error"))
    return len(calls), warn


def record(f):
    with open(PUSHED, "w") as fh:
        json.dump([[list(k), v] for k, v in f.items()], fh)


def recorded():
    try:
        return {tuple(k): v for k, v in json.load(open(PUSHED))}
    except (OSError, ValueError):
        return None


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    diff_only, force = "--diff" in sys.argv, "--force" in sys.argv
    path = os.path.abspath(args[0]) if args else OUT
    t0 = time.time()
    want = target(path)
    try:
        m = MCP()
        mode = m.call("get_document", depth=0).get("mode")
        switched = False
        if mode != "EDITOR" and not diff_only:
            m.call("set_mode", mode="EDITOR")
            switched = True
        try:
            return push(m, want, path, diff_only, force, t0)
        finally:
            if switched:
                m.call("set_mode", mode=mode)
    except Unreachable as e:
        print("%s: not pushing live" % e, file=sys.stderr)
        return 2
    except Failed as e:
        print(str(e), file=sys.stderr)
        return 1


def push(m, want, path, diff_only, force, t0):
    head = choose(m, not diff_only)
    doc, root = read(m)
    types = {n.name: n for n in root.walk()}
    have, wantf = facts(root, doc), facts(want, types=types)
    keys = differing(have, wantf)
    name = os.path.basename(path)
    if diff_only:
        print("\n".join(lines(keys, have, wantf)) if keys else
              "no differences: TouchOSC's CutIt is %s" % name)
        return 0
    if head.get("modified") and keys and not force:
        # Edited since it was opened or saved. What the last push left is ours; what the build
        # wants is no loss; anything else is an edit made in the editor and not saved.
        last = recorded()
        theirs = [k for k in keys if last is None or have.get(k) != last.get(k)]
        if theirs:
            print("TouchOSC's CutIt has %s made in its editor and not saved, which this push would "
                  "undo:\n  %s\nSave them with File > Save (diff.py then lists them for build.py), "
                  "or push with --force to discard them."
                  % ("changes" if last else "changes (no push has been made to it to compare "
                     "with)", "\n  ".join(lines(theirs, have, wantf))), file=sys.stderr)
            return 4
    if not keys:
        record(have)
        print("TouchOSC's CutIt is already %s (%.1f s)" % (name, time.time() - t0))
        return 0
    ids, edits = restructure(m, want, root)
    if edits:
        doc, root = read(m)
    more, warn = settle(m, want, doc, root, ids)
    edits += more
    doc, root = read(m)
    have = facts(root, doc)
    record(have)
    wantf = facts(want, types={n.name: n for n in root.walk()})
    left = differing(have, wantf)
    for w in warn:
        print("warning: " + w, file=sys.stderr)
    if left:
        print("pushed %d edits, but TouchOSC's CutIt still differs from %s:\n  %s"
              % (edits, name, "\n  ".join(lines(left, have, wantf))), file=sys.stderr)
        return 1
    print("pushed %s into TouchOSC's open CutIt: %d difference(s), %d edit(s), %.1f s"
          % (name, len(keys), edits, time.time() - t0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
