#!/usr/bin/env python3
"""Where the app reads each state, written from the Lua that sends it.

    python3 phone/state-at.py            write phone/CutIt/StateAt.swift
    python3 phone/state-at.py --print    print it instead

The patch sends the phone each state as one flat list, and the app reads it by position. A list's
fields are named once, in the Lua that writes it (R.PHONE_FIELDS in c_steps, c_melody, u_perform and
u_voices, and c_melody's R.NOTES_FIELDS). This writes each field's place as a Swift constant, 0 the
first atom, so a field added in the Lua moves the app's reads with it: run this, and build the app.
test/gate/app-assert.py fails while the file is behind, and when the app reads one of these states
at a number of its own. ref/device/phone.md, *The app reads each state by name*.
"""
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "phone", "CutIt", "StateAt.swift")
# The Lua the gates run, test/gate/lib_scratch.py's: LUA= points a run at another.
LUA_BIN = os.environ.get("LUA") or shutil.which("lua5.4") or shutil.which("lua") or "lua"

# Each state: the enum the app reads it through, its OSC address, the Lua that writes it and the
# table there that names its fields.
STATES = [
    ("DrumsAt", "/cutit/drums", "c_steps", "PHONE_FIELDS"),
    ("MelodyAt", "/cutit/melody", "c_melody", "PHONE_FIELDS"),
    ("NotesAt", "/cutit/notes", "c_melody", "NOTES_FIELDS"),
    ("PerformAt", "/cutit/perform", "u_perform", "PHONE_FIELDS"),
    ("VoicesAt", "/cutit/voices", "u_voices", "PHONE_FIELDS"),
]

LUA = r"""
for mod, name in string.gmatch(os.getenv("STATE_AT"), "(%S+):(%S+)") do
  local R = dofile("Cut It/" .. mod .. ".lua")
  for _, f in ipairs(R[name]) do
    print(mod, name, f[1], f[2], table.concat(f[4] or {}, " "))
  end
end
"""


def camel(name):
    """chord-lock as chordLock."""
    head, *rest = name.split("-")
    return head + "".join(w[:1].upper() + w[1:] for w in rest)


def fields():
    """{(module, table): [(name, atoms, [a group's members])]}, from the Lua itself."""
    wanted = " ".join("%s:%s" % (mod, name) for _, _, mod, name in STATES)
    try:
        run = subprocess.run([LUA_BIN, "-e", LUA], cwd=ROOT, capture_output=True, text=True,
                             env=dict(os.environ, STATE_AT=wanted))
    except OSError as e:
        sys.exit("state-at: no Lua: %s" % e)
    if run.returncode != 0:
        sys.exit("state-at: lua failed: %s" % run.stderr.strip())
    out = {}
    for line in run.stdout.splitlines():
        mod, name, field, atoms, members = (line.split("\t") + [""])[:5]
        out.setdefault((mod, name), []).append((field, int(atoms), members.split()))
    return out


def render():
    got = fields()
    lines = ["// Written by phone/state-at.py from the Lua that sends each state: don't edit it.",
             "// Where each field of a state begins in its list, 0 the first atom. A field of groups (a slot, a",
             "// voice) has an enum of its own: where each part is within a group, and a group's width.",
             ""]
    for enum, address, mod, name in STATES:
        rows = got.get((mod, name))
        if not rows:
            sys.exit("state-at: %s.lua has no R.%s" % (mod, name))
        seen = set()
        lines.append("/// %s, from %s.lua's R.%s." % (address, mod, name))
        lines.append("enum %s {" % enum)
        at = 0
        for field, atoms, members in rows:
            const = camel(field)
            if not re.fullmatch(r"[a-z][A-Za-z0-9]*", const) or const in seen or const == "count":
                sys.exit("state-at: %s.%s: %r is no name for a constant" % (mod, name, field))
            seen.add(const)
            lines.append("    static let %s = %d" % (const, at))
            if members:
                if atoms % len(members):
                    sys.exit("state-at: %s.%s: %s is %d atoms, in groups of %d"
                             % (mod, name, field, atoms, len(members)))
                lines.append("    enum %s {" % (const[:1].upper() + const[1:]))
                for k, member in enumerate(members):
                    lines.append("        static let %s = %d" % (camel(member), k))
                lines.append("        static let width = %d" % len(members))
                lines.append("    }")
            at += atoms
        lines.append("    static let count = %d" % at)
        lines.append("}")
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def main():
    text = render()
    if "--print" in sys.argv[1:]:
        sys.stdout.write(text)
        return
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(text)
    print("wrote %s" % os.path.relpath(OUT, ROOT))


if __name__ == "__main__":
    main()
