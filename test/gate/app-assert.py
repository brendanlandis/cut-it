#!/usr/bin/env python3
"""The Cut It app's commands, read against the patch's -- ref/device/phone.md. No Pd, no phone, ~1 s.

    python3 test/gate/app-assert.py [-v]     (run it as app-assert.sh)

Everything the app's Swift sends the patch, every cut.press, cut.send and cut.control in
phone/CutIt/, is read from the source and checked, word by word, against what takes it: u_net's
route of commands, then the Lua tables behind each outlet -- c_steps'
presses, c_synth's synths and velocity, u_tempo's number, u_song's sections and songs, c_melody's
inputs, u_voices', u_perform's and u_sound's phone commands -- and, for a control the app moves
through u_perform, u_map's route of destinations and the destination's own table. The two ends
deploy by different routes (TestFlight, tools/deploy.sh), so a misspelled command fails here, not
on the rig as bad-selector. touchosc-assert did this for the TouchOSC layout until it went
(2026-11-19).

What the app reads is checked too, where it reads a state by position (ref/device/phone.md, *The
app reads each state by name*): phone/CutIt/StateAt.swift is what phone/state-at.py writes from the
Lua's field tables today, the app reads those five states and the drums' numbers only at places
that file names, and every place it names is one the file has. So a field added to a state in the
Lua fails here until StateAt.swift is written again, and the app's reads move with it.

The patch's side is read by loading its Lua under lua.org's Lua 5.4, so a key made in a loop
(c_steps' vol-1 to vol-16) is there as Pd sees it; the Swift's by reading, every argument a
literal, an interpolated string (its \\( ) parts any text), a choice of two literals, or an
expression. An expression where a command's word goes is read through RESOLVE below, from the
Swift that supplies it, or fails: a new one can't pass unread.
"""
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_assert as A                                         # noqa: E402
import lib_pd                                                   # noqa: E402
import lib_scratch as S                                         # noqa: E402

ROOT = S.ROOT
SWIFT = os.path.join(ROOT, "phone", "CutIt")
CUT = "Cut.swift"
UNET = os.path.join(ROOT, "Cut It", "u_net.pd")
UMAP = os.path.join(ROOT, "Cut It", "u_map.pd")

# The Lua tables each command's words are looked up in, as each module's face does
# (Cut It/*-lua.pd_lua's answer(sel, R.<table>[sel], ...)).
LUA_DUMP = r"""
local function dump(mod, name, t, list)
  if type(t) ~= "table" then print(mod .. " " .. name .. " MISSING") return end
  if list then
    for _, v in ipairs(t) do print(mod .. " " .. name .. " " .. tostring(v)) end
  else
    for k in pairs(t) do print(mod .. " " .. name .. " " .. tostring(k)) end
  end
end
local wanted = {
  { "c_steps", { "presses" } }, { "c_synth", { "inputs", "VELOCITY", SYNTHS = true } },
  { "u_tempo", { "inputs" } }, { "u_song", { "phone_cmds", "songs_cmds" } },
  { "c_melody", { "inputs", ORDER = true } }, { "u_voices", { "phone_cmds", BEHAVIORS = true, INSTRUMENTS = true } },
  { "u_perform", { "phone_cmds" } }, { "u_sound", { "phone_cmds" } },
}
for _, w in ipairs(wanted) do
  local R = dofile("Cut It/" .. w[1] .. ".lua")
  for k, v in pairs(w[2]) do
    if type(k) == "number" then dump(w[1], v, R[v], false) else dump(w[1], k, R[k], true) end
  end
end
"""


def lua_tables():
    """{(module, table): set of keys, or a list for an ordered one}, or None if Lua failed."""
    try:
        p = subprocess.run([S.LUA, "-e", LUA_DUMP], cwd=ROOT, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as e:
        return None, str(e)
    out = p.stdout.decode("utf-8", "replace")
    if p.returncode != 0:
        return None, out.strip()
    t = {}
    for line in out.splitlines():
        mod, name, key = line.split(" ", 2)
        if key == "MISSING":
            return None, "%s.lua has no R.%s" % (mod, name)
        t.setdefault((mod, name), []).append(key)
    return t, ""


def route_of(path, first):
    """The arguments of the one `route <first> ...` box in a file, or None."""
    want = re.compile(r"^#X obj -?\d+ -?\d+ route (" + re.escape(first) + r"(?: [^;,]*)?)(?:, f \d+)?;$")
    hits = [m.group(1) for m in (want.match(r) for r in lib_pd.read(path)) if m]
    return hits[0].split() if len(hits) == 1 else None


# ------------------------------------------------------------------ reading the Swift
# Where a call to the patch starts: cut.press( and its kin anywhere, and inside Cut.swift the bare
# press( and send( that Cut's own methods make, but not their definitions or link.send(.
CALL = re.compile(r"(?<![\w.])cut\.(press|send|control)\(")
BARE = re.compile(r"(?<![\w.])(press|send)\(")


def args_at(src, i):
    """The arguments of the call whose ( is at src[i], split at top-level commas, and the index
    after its ). Strings (with \\( ) interpolation in them) and brackets are stepped over whole."""
    depth, j, start, out = 0, i, i + 1, []
    while j < len(src):
        c = src[j]
        if c == '"':
            j = string_end(src, j)
            continue
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
            if depth == 0:
                out.append(src[start:j].strip())
                return [a for a in out if a], j + 1
        elif c == "," and depth == 1:
            out.append(src[start:j].strip())
            start = j + 1
        j += 1
    return None, j


def string_end(src, j):
    """The index after the string literal opening at src[j]."""
    j += 1
    while j < len(src):
        c = src[j]
        if c == "\\" and src[j + 1] == "(":
            depth, j = 1, j + 2
            while depth:
                if src[j] == '"':
                    j = string_end(src, j)
                    continue
                depth += {"(": 1, ")": -1}.get(src[j], 0)
                j += 1
            continue
        if c == "\\":
            j += 2
            continue
        if c == '"':
            return j + 1
        j += 1
    return j


LIT = re.compile(r'"((?:[^"\\]|\\.)*)"')
NUM = re.compile(r"-?\d+(?:\.\d+)?")


def word(a):
    """One argument as what it can be: [("lit", text)], [("pat", regex, text)], [("num", text)],
    [("expr", text)], or a choice of two literals' both."""
    t = re.fullmatch(r"(.+?) \? (.+) : (.+)", a)
    if t and all(LIT.fullmatch(x.strip()) for x in t.groups()[1:]):
        return [x for part in t.groups()[1:] for x in word(part.strip())]
    m = LIT.fullmatch(a)
    if m:
        s = m.group(1)
        if "\\(" not in s:
            return [("lit", s)]
        rx, k = "", 0
        while k < len(s):
            if s.startswith("\\(", k):
                k = close_interp(s, k)
                rx += ".+"
            else:
                rx += re.escape(s[k])
                k += 1
        return [("pat", rx, s)]
    if NUM.fullmatch(a):
        return [("num", a)]
    return [("expr", a)]


def close_interp(s, k):
    """The index after the \\( ) starting at s[k]."""
    depth, k = 1, k + 2
    while depth and k < len(s):
        depth += {"(": 1, ")": -1}.get(s[k], 0)
        k += 1
    return k


def control_body(src):
    """(params, call args) of Cut's func control: the one call it makes, which the gate inlines for
    every cut.control(...)."""
    m = re.search(r"func control\(([^)]*)\)\s*\{\s*send\(", src)
    if not m:
        return None
    params = [p.split(":")[0].split()[-1] for p in m.group(1).split(",")]
    a, _ = args_at(src, m.end() - 1)
    return params, a


def calls():
    """[(file, line, kind, [argument text])] for every call to the patch, and how many such
    calls a plain search finds, which the read ones must equal."""
    found, plain, inline = [], 0, None
    for f in sorted(os.listdir(SWIFT)):
        if not f.endswith(".swift"):
            continue
        src = open(os.path.join(SWIFT, f), encoding="utf-8").read()
        plain += len(CALL.findall(src))
        hits = [(m, m.group(1)) for m in CALL.finditer(src)]
        if f == CUT:
            inline = control_body(src)
            for m in BARE.finditer(src):
                head = src[max(0, m.start() - 5):m.start()]
                if head.endswith("func ") or in_func(src, m.start(), "control"):
                    continue
                plain += 1
                hits.append((m, m.group(1)))
        for m, kind in hits:
            a, _ = args_at(src, m.end() - 1)
            if a is not None:
                found.append((f, src.count("\n", 0, m.start()) + 1, kind, a))
    return found, plain, inline


def in_func(src, i, name):
    """Is src[i] inside the body of func <name>?"""
    m = None
    for m in re.finditer(r"func (\w+)\(", src[:i]):
        pass
    if not m or m.group(1) != name:
        return False
    body = src.index("{", m.end())
    _, end = args_at(src, body)
    return i < end


# Expressions in a command word's place, and the Swift each is read from. Keyed by file, the
# command's first two words, and the expression; each reads the source, so a value added there is
# checked like a literal.
def swift_list(f, pattern):
    src = open(os.path.join(SWIFT, f), encoding="utf-8").read()
    return [s for m in re.finditer(pattern, src) for s in LIT.findall(m.group(1))]


RESOLVE = {
    # The harmony page's knobs: knob(<label>, <arg>, ...), arg the generator's control.
    ("Pages.swift", "perform ctl", "arg"): lambda: swift_list("Pages.swift", r'\bknob\("[^"]*", ("[^"]*")'),
    # The melody page's rows of knobs: row([<control>, ...]).
    ("Pages.swift", "perform ctl", "n"): lambda: swift_list("Pages.swift", r"\brow\(\[([^\]]*)\]\)"),
    # The setup page's choices, from its own lists.
    ("Pages.swift", "voices behavior", "m"): lambda: swift_list("Pages.swift", r"static let behaviors = \[([^\]]*)\]"),
    ("Pages.swift", "voices instrument", "m"): lambda: swift_list("Pages.swift", r"static let instruments = \[([^\]]*)\]"),
    ("Pages.swift", "voices instrument", "sure"): lambda: swift_list("Pages.swift", r"static let instruments = \[([^\]]*)\]"),
    # A voice not made yet: its two columns' choices, from the same lists.
    ("Pages.swift", "voices add", "behavior"): lambda: swift_list("Pages.swift", r"static let behaviors = \[([^\]]*)\]"),
    ("Pages.swift", "voices add", "instrument"): lambda: swift_list("Pages.swift", r"static let instruments = \[([^\]]*)\]"),
}


# ------------------------------------------------------------------ where the app reads a state
STATE_AT = os.path.join(ROOT, "phone", "state-at.py")
AT_FILE = "StateAt.swift"
# Each state the app reads by position: its address, and the enum phone/state-at.py writes for it.
READS = [("/cutit/notes", "NotesAt"), ("/cutit/melody", "MelodyAt"), ("/cutit/drums", "DrumsAt"),
         ("/cutit/voices", "VoicesAt"), ("/cutit/perform", "PerformAt")]
ENUMS = [e for _, e in READS]
NUMBER = re.compile(r"(?<![\w$.])\d")
NAMED = re.compile(r"\b(%s)((?:\.[A-Za-z]\w*)+)" % "|".join(ENUMS))


def written():
    """StateAt.swift as phone/state-at.py would write it now, or (None, why)."""
    try:
        p = subprocess.run([sys.executable, STATE_AT, "--print"], cwd=ROOT, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, timeout=30, env=dict(os.environ, LUA=S.LUA or ""))
    except (OSError, subprocess.TimeoutExpired) as e:
        return None, str(e)
    if p.returncode != 0:
        return None, p.stderr.decode("utf-8", "replace").strip()
    return p.stdout.decode("utf-8"), ""


def places(text):
    """Every place StateAt.swift names: DrumsAt.vol, MelodyAt.Slot.name."""
    out, path = set(), []
    for line in text.splitlines():
        m = re.match(r"\s*enum (\w+) \{", line)
        if m:
            path.append(m.group(1))
        elif line.strip() == "}":
            path.pop()
        else:
            m = re.match(r"\s*static let (\w+) = \d+$", line)
            if m:
                out.add(".".join(path + [m.group(1)]))
    return out


def state_reads():
    """(reads counted, [a read at a number of the app's own], [a place named that the file hasn't])."""
    sources = {f: open(os.path.join(SWIFT, f), encoding="utf-8").read()
               for f in sorted(os.listdir(SWIFT)) if f.endswith(".swift") and f != AT_FILE}
    known = places(open(os.path.join(SWIFT, AT_FILE), encoding="utf-8").read())
    n, own, unknown = 0, [], []

    def line(f, i):
        return "%s:%d" % (f, sources[f].count("\n", 0, i) + 1)

    # Each state's case in Cut's heard(): its guard and every a[...] in it.
    src = sources[CUT]
    for address, enum in READS:
        m = re.search(r'\n( *)case "%s":\n' % re.escape(address), src)
        if not m:
            own.append("%s has no case for %s" % (CUT, address))
            continue
        end = re.compile(r"\n%s(case |default:)" % m.group(1)).search(src, m.end())
        block, at = src[m.end():end.start() if end else len(src)], m.end()
        lets = dict(re.findall(r"\blet (\w+) = ([^\n]+)", block))
        for other in ENUMS:
            if other != enum and other + "." in block:
                own.append("%s reads %s at %s's places" % (address, address, other))
        g = re.search(r"guard a\.count ([^\n]*)", block)
        if not g or NUMBER.search(g.group(1)) or enum + "." not in g.group(1):
            own.append("%s: its guard is not %s's: %s" % (address, enum, g.group(0) if g else "none"))
        for i in re.finditer(r"(?<![\w.])a\[", block):
            index, _ = args_at(block, i.end() - 1)
            text = " ".join(index or [])
            # A let the index is built from is read with it.
            whole = text + " " + " ".join(v for k, v in lets.items() if re.search(r"\b%s\b" % k, text))
            n += 1
            if index is None or NUMBER.search(whole) or enum + "." not in whole:
                own.append("%s a[%s]" % (line(CUT, at + i.start()), text))

    # The drums' numbers, kept whole and read by the pages: cut.drum(<a place>[, track:]).
    for f, s in sources.items():
        for m in re.finditer(r"(?<!\w)drum\(", s):
            if s[max(0, m.start() - 5):m.start()] == "func ":
                continue
            a, _ = args_at(s, m.end() - 1)
            n += 1
            if not a or not re.fullmatch(r"DrumsAt\.[a-z]\w*", a[0]) \
                    or (len(a) > 1 and not a[1].startswith("track:")) or len(a) > 2:
                own.append("%s drum(%s)" % (line(f, m.start()), ", ".join(a or [])))
        for m in re.finditer(r"drumRaw\[", s):
            if not (f == CUT and in_func(s, m.start(), "drum")):
                own.append("%s reads drumRaw itself" % line(f, m.start()))
        for m in NAMED.finditer(s):
            if (m.group(1) + m.group(2)) not in known:
                unknown.append("%s %s%s" % (line(f, m.start()), m.group(1), m.group(2)))
    return n, own, unknown


def main():
    print("\n=== the app's commands, read against the patch's -- no Pd, no phone ===")
    t, why = lua_tables()
    top = route_of(UNET, "result")
    uonce = route_of(UNET, "once")
    dests = route_of(UMAP, "tempo")
    A.check("u_net's routes, u_map's destinations and the Lua's tables are all readable",
            None not in (t, top, uonce, dests),
            "lua: %s  u_net: %r / %r  u_map: %r" % (why or "ok", top, uonce, dests))
    if None in (t, top, uonce, dests):
        return A.report()

    def keys(mod, name):
        return set(t.get((mod, name), []))

    found, plain, inline = calls()
    per = {}
    for f, *_ in found:
        per[f] = per.get(f, 0) + 1
    A.check("⛔ every call the app makes to the patch is read, none skipped",
            found and len(found) == plain,
            "%d read of %d found: %s" % (len(found), plain, per))
    A.note("%d calls read, %s" % (len(found), ", ".join("%s %d" % kv for kv in sorted(per.items()))))

    src = open(os.path.join(SWIFT, CUT), encoding="utf-8").read()
    A.check("⛔ cut.press sends once <n> before its words, which u_net's route once takes",
            re.search(r'let message: \[OSCValue\] = \[\.text\("once"\), \.number\(Float\(seq\)\)\] \+ '
                      r"values\(words\)", src) is not None and uonce == ["once"],
            "u_net: route %s" % uonce)
    # ref/device/phone.md, The app can hear and not be heard: the state can arrive while no press leaves.
    gave_up = re.search(r"if entry\.tries >= Self\.maxTries \{[^}]*\bunheard = true\b", src)
    answered = re.search(r'case "/cutit/once":[^}]*waiting\.removeValue\(forKey: id\) != nil \{ unheard = false \}', src)
    app = open(os.path.join(SWIFT, "App.swift"), encoding="utf-8").read()
    bar = re.search(r"if !cut\.linked \|\| cut\.unheard \{", app)
    A.check("⛔ a press given up unanswered shows on the page, until a press of the app's own is answered",
            None not in (gave_up, answered, bar),
            "given up sets it: %s  an answer clears it: %s  the bar reads it: %s"
            % (bool(gave_up), bool(answered), bool(bar)))
    # ref/device/phone.md, A socket that can't send keeps what it's given: a press must never leave late.
    link = open(os.path.join(SWIFT, "Link.swift"), encoding="utf-8").read()
    sends = re.findall(r"\bout\?\.send\(", link)
    kept = re.search(r"func send\(_ args: \[OSCValue\]\) \{[^}]*queue\.async \{[^}]*guard ready, viable else \{ return \}"
                     r"\s*out\?\.send\(", link)
    A.check("⛔ nothing is given to a socket that can't send now, which would send it late",
            kept is not None and len(sends) == 1,
            "Link.send's guard: %s  places that send: %d" % (bool(kept), len(sends)))
    A.check("⛔ cut.control sends perform ctl <row> <dest> <arg> <value>, as u_perform's ctl takes it",
            inline is not None and inline[0] == ["dest", "arg", "value"]
            and inline[1][:2] == ['"perform"', '"ctl"'] and inline[1][3:] == inline[0],
            "func control(%s) sends %s" % inline if inline else "no func control found in Cut.swift")
    if inline is None:
        return A.report()

    # Every call as its words, each a list of what it can be; control's inlined.
    sent = []
    for f, line, kind, a in found:
        if kind == "control":
            sub = dict(zip(inline[0], a))
            a = [sub.get(x, x) for x in inline[1]]
        sent.append((f, line, [word(x) for x in a]))

    bad = {}
    unread = []

    def fail(what, f, line, text):
        bad.setdefault(what, []).append("%s:%d %s" % (f, line, text))

    def literals(f, line, words, k):
        """What words[k] can be, as literal text and patterns; an expression read through RESOLVE,
        or reported unread."""
        out = []
        for w in words[k]:
            if w[0] in ("lit", "num"):
                out.append(("lit", w[1]))
            elif w[0] == "pat":
                out.append(w)
            else:
                head = " ".join(x[0][1] for x in words[:2] if x[0][0] == "lit")
                r = RESOLVE.get((f, head, w[1]))
                if r is None:
                    unread.append("%s:%d %s ... %s" % (f, line, head, w[1]))
                else:
                    vals = r()
                    if not vals:
                        unread.append("%s:%d %s ... %s reads nothing" % (f, line, head, w[1]))
                    out += [("lit", v) for v in vals]
        return out

    def takes(what, f, line, words, k, allowed):
        """Check words[k] is in allowed: a literal exactly, a pattern by matching at least one."""
        seen[what] = seen.get(what, 0) + 1
        if k >= len(words):
            fail(what, f, line, "(nothing at word %d)" % (k + 1))
            return []
        got = literals(f, line, words, k)
        for g in got:
            if g[0] == "lit" and g[1] not in allowed:
                fail(what, f, line, g[1])
            if g[0] == "pat" and not any(re.fullmatch(g[1], x) for x in allowed):
                fail(what, f, line, g[2])
        return [g[1] for g in got if g[0] == "lit"]

    seen = {}
    cmds = set()
    for f, line, words in sent:
        cmd = takes("top", f, line, words, 0, set(top))
        cmds.update(cmd)
        c = cmd[0] if len(cmd) == 1 else None
        if c == "drums":
            takes("drums", f, line, words, 1, keys("c_steps", "presses"))
        elif c == "synth":
            takes("synth", f, line, words, 1, keys("c_synth", "SYNTHS"))
        elif c == "velocity":
            takes("velocity", f, line, words, 1, keys("c_synth", "VELOCITY"))
        elif c == "tempo":
            seen["tempo"] = seen.get("tempo", 0) + 1
            if len(words) < 2 or any(w[0] in ("lit", "pat") for w in words[1]):
                fail("tempo", f, line, "tempo with no number")
        elif c == "sections":
            takes("sections", f, line, words, 1, keys("u_song", "phone_cmds"))
        elif c == "songs":
            takes("songs", f, line, words, 1, keys("u_song", "songs_cmds"))
        elif c == "melody":
            sub = takes("melody", f, line, words, 1, keys("c_melody", "inputs"))
            if sub == ["set"]:
                takes("melody set", f, line, words, 2, keys("c_melody", "ORDER") | {"arrive", "octave"})
        elif c == "voices":
            sub = takes("voices", f, line, words, 1, keys("u_voices", "phone_cmds"))
            if sub == ["behavior"]:
                takes("voices behavior", f, line, words, 3, keys("u_voices", "BEHAVIORS"))
            elif sub == ["instrument"]:
                takes("voices instrument", f, line, words, 3, keys("u_voices", "INSTRUMENTS"))
            elif sub == ["add"]:
                takes("voices add", f, line, words, 3, keys("u_voices", "BEHAVIORS"))
                takes("voices add", f, line, words, 4, keys("u_voices", "INSTRUMENTS"))
        elif c == "perform":
            sub = takes("perform", f, line, words, 1, keys("u_perform", "phone_cmds"))
            if sub == ["ctl"]:
                dest = takes("perform ctl", f, line, words, 3, set(dests))
                # drums and melody: the destination's own table, as u_map hands the arg on (a
                # melody arg as e<engine>-<arg>, which c_melody's face takes off). instrument's are
                # the instrument's parameters, which the patch tells the app: data, not words.
                if dest == ["drums"]:
                    takes("perform ctl drums", f, line, words, 4, keys("c_steps", "presses"))
                elif dest == ["melody"]:
                    takes("perform ctl melody", f, line, words, 4, keys("c_melody", "inputs"))
        elif c == "sound":
            takes("sound", f, line, words, 1, keys("u_sound", "phone_cmds"))

    A.check("⛔ every word in a command's place is one the gate can read",
            not unread, "add how to read it to RESOLVE: %s" % "; ".join(unread))
    A.check("⛔ the app sends EXACTLY the commands u_net routes",
            not bad.get("top") and cmds == set(top),
            "the app sends %s, u_net routes %s; unknown: %s -- whichever side is short is a button "
            "that does nothing, or a route nothing uses"
            % (" ".join(sorted(cmds)), " ".join(top), bad.get("top")))
    for what, who in [
            ("drums", "c_steps takes (R.presses)"),
            ("synth", "c_synth takes (R.SYNTHS)"),
            ("velocity", "c_synth takes (R.VELOCITY)"),
            ("tempo", "u_tempo takes: a number"),
            ("sections", "u_song takes (R.phone_cmds)"),
            ("songs", "u_song takes after songs (R.songs_cmds)"),
            ("melody", "c_melody takes (R.inputs)"),
            ("melody set", "c_melody's set knows (R.ORDER, arrive and octave)"),
            ("voices", "u_voices takes (R.phone_cmds)"),
            ("voices behavior", "u_voices has (R.BEHAVIORS)"),
            ("voices instrument", "u_voices has (R.INSTRUMENTS)"),
            ("voices add", "u_voices has (R.BEHAVIORS, then R.INSTRUMENTS)"),
            ("perform", "u_perform takes (R.phone_cmds)"),
            ("perform ctl", "u_map routes (its destination route)"),
            ("perform ctl drums", "c_steps takes (R.presses)"),
            ("perform ctl melody", "c_melody takes (R.inputs)"),
            ("sound", "u_sound takes (R.phone_cmds)")]:
        n = seen.get(what, 0)
        A.check("⛔ every %s the app sends is one %s" % (what, who),
                not bad.get(what) and n > 0,
                "%d calls; not taken: %s" % (n, "; ".join(bad.get(what, [])) or "-"))

    print("\n=== where the app reads each state ===")
    want, why = written()
    have = open(os.path.join(SWIFT, AT_FILE), encoding="utf-8").read() \
        if os.path.exists(os.path.join(SWIFT, AT_FILE)) else None
    A.check("⛔ %s is what phone/state-at.py writes from the Lua's fields today" % AT_FILE,
            want is not None and want == have,
            why or "a state's fields changed in the Lua: run python3 phone/state-at.py, and build "
                   "the app")
    if have is None:
        return A.report()
    n, own, unknown = state_reads()
    A.note("%d reads by position" % n)
    A.check("⛔ the app reads each state at the places %s names, never at a number of its own" % AT_FILE,
            n > 0 and not own, "; ".join(own) or "%d reads" % n)
    A.check("⛔ every place the app names is one %s has" % AT_FILE,
            not unknown, "; ".join(unknown) or "-")
    return A.report()


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
