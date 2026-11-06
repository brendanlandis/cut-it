#!/usr/bin/env python3
"""The map's analyzer -- ref/module/map.md. Two halves, and the first needs no Pd.

  1. The static lint reads Cut It/cut-it-map.txt and the literal route box in
     Cut It/u_map.pd and checks that every destination a row names is on that
     route: the allowlist guard, enforced by reading, in ~200 ms.

  2. The run assertions read a capture from map-assert.sh and test the lookup:
     a control maps at load, maps differently in another mode, and a row naming
     a destination off the route emits nothing and says so. What a destination
     does with the value is its device gate's.

Reads the capture on stdin. Exits non-zero on any failure.
"""
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_assert as A                                         # noqa: E402
import lib_pd                                                  # noqa: E402

MAP = "Cut It/cut-it-map.txt"
UMAP = "Cut It/u_map.pd"
# Every m_ file and its exact [s disp] count: none, since a control's row is u_map's. The file set
# is exact too: m_404 went with the SP-404, and m_streich and m_nanokey came with the synths
# (2026-11-04).
DISP_EXPECT = {"m_launchpad": 0, "m_nano": 0, "m_organelle": 0, "m_volca": 0,
               "m_streich": 0, "m_nanokey": 0}
ARRANGE_PAGE = "Cut It/cut-it-arrangement-page.txt"
DRUM_PAGE = "Cut It/cut-it-drum-page.txt"
CSTEPS = "Cut It/c_steps.lua"
UTEMPO = "Cut It/u_tempo.pd"
ULUA = "Cut It/u_map.lua"
# The rows every page shares (ref/module/map.md): <control> <dest> <arg>. The Organelle's knobs are the
# same on every page (Brendan, 2026-11-06).
EVERY_PAGE = [("og-knob-1", "tempo", "0"), ("og-knob-2", "drums", "last"),
              ("og-knob-3", "drums", "track-last"), ("og-knob-4", "rush", "0"),
              ("xport-2", "start", "0"), ("xport-5", "stop", "0"), ("xport-4", "arrangement", "21"),
              ("xport-6", "perform", "arm"), ("lp-cc-90", "recover", "0"),
              ("lp-setup", "voices", "setup"), ("og-aux", "voices", "aux")] + [
              # the top row, the two arrows then the six section buttons, and save and revert,
              # the bottom rows' rightmost (ref/module/songs.md)
              ("lp-cc-%d" % (90 + n), "section", "%d" % n) for n in range(1, 9)] + [
              ("lp-cc-108", "save", "0"), ("lp-cc-8", "revert", "0")] + [
              # the Organelle's keys choose songs, key 1 the lowest (Brendan, 2026-11-05)
              ("og-key-%d" % (59 + k), "song", "%d" % k) for k in range(1, 26)] + [
              # a row of the Launchpad is a voice (ref/module/voices.md)
              ("lp-cc-%d" % (90 - 10 * r), "voices", "left-%d" % r) for r in range(1, 9)] + [
              ("lp-cc-%d" % (99 - 10 * r), "voices", "right-%d" % r) for r in range(1, 9)] + [
              # the nanoKONTROL's eight groups are what this section assigned
              (c % g, "perform", c % g) for g in range(1, 9)
              for c in ("slider-%d", "knob-%d", "btn-a-%d", "btn-b-%d")]
# What a page may take back from the rows every page shares: the performance page's bottom rows are
# the nanoKONTROL's buttons, so save and revert aren't there (Brendan, 2026-11-06).
SHADOWED = {("perform", "lp-cc-108"), ("perform", "lp-cc-8")}
# Both runs are counted against this one list, so neither passes a driver that
# died early.
WINDOWS = ["EARLY", "EARLY-2", "RAIL-ARM", "SUPPRESS", "MAPPED", "AWAY", "CROSS",
           "LIVE", "PLAY-1", "STOP-1", "PLAY-2", "KNOB-2", "LATE-KNOB", "BAD-DEST",
           "RAIL-UP", "RAIL-BACK", "LEFT-2", "LEFT-2-RELEASE", "PAGE-DEP",
           "TOP-ROW", "UNMAPPED", "AUX", "BAD-MODE", "AFTER-BAD", "SETUP", "DIAG-DEST",
           "DIAG-RELEASE", "PERFORM", "ROW-CC", "ROW-NOTE", "ROW-PROG",
           "ROW-KEY", "PRESSURE", "PRESSURE-MAPPED"]


# --------------------------------------------------------------- static lint
def route_destinations():
    """The literal allowlist: the arguments of u_map's destination route box."""
    for line in lib_pd.read(UMAP):
        m = re.match(r"^#X obj \d+ \d+ route (tempo .*);$", line)
        if m:
            return m.group(1).split()
    return None


def pages():
    """R.PAGES in u_map.lua: the page names the Lua takes off the mode bus."""
    m = re.search(r"^R\.PAGES = \{(.*?)\}", open(ULUA, encoding="utf-8").read(), re.M | re.S)
    return re.findall(r"([\w-]+) = true", m.group(1)) if m else None


def steps_cmds():
    """The commands c_steps takes on its inlet: the keys of c_steps.lua's R.presses."""
    src = open(os.path.join(os.path.dirname(UMAP), "c_steps.lua"), encoding="utf-8").read()
    m = re.search(r"^R\.presses = \{\n(.*?)^\}", src, re.M | re.S)
    if not m:
        return None
    keys = re.findall(r'^  (?:\["([\w-]+)"\]|(\w+)) = function', m.group(1), re.M)
    return sorted(a or b for a, b in keys)


def arrange_layout():
    """{cell: [role]} from the arrangement's layout, which u_map's arrangement handler reads."""
    lay = {}
    for line in open(ARRANGE_PAGE, encoding="utf-8"):
        f = line.split()
        if f:
            lay[f[0]] = f[1:]
    return lay


def tempo_roles():
    """The roles u_tempo takes from the arrangement page: its literal [route tap ...] box."""
    for line in lib_pd.read(UTEMPO):
        m = re.match(r"^#X obj \d+ \d+ route (tap(?: [^;]*)?);$", line)
        if m:
            return m.group(1).split()
    return None


def static_lint():
    print("\n=== A. the map, checked by READING -- no Pd involved ===")
    dests = route_destinations()
    A.check("u_map still has a literal destination route box", dests is not None,
            "expected a box starting 'route tempo ...' in " + UMAP)
    if dests is None:
        return
    A.note("allowlist is %d destinations: %s" % (len(dests), " ".join(dests)))

    # The pages the table can name are the ones the Lua takes off the bus: a row for any other is a
    # row nothing can ever reach. all is every page's.
    names = pages()
    A.check("u_map.lua's R.PAGES names the eight pages u_voices can show",
            names is not None and sorted(names) == sorted(["perform", "drums", "harmony", "melody", "keys",
                                                           "sound", "songs", "diag"]),
            "R.PAGES: %s" % names)
    modes = (names or []) + ["all"]
    rows, bad_width, bad_dest, bad_mode = [], [], [], []
    for n, raw in enumerate(open(MAP), 1):
        line = raw.strip()
        if not line:
            continue
        f = line.split()
        rows.append((n, f))
        if len(f) != 4:
            bad_width.append((n, line))
            continue
        if f[2] not in dests:
            bad_dest.append((n, f[2]))
        if f[0] not in modes:
            bad_mode.append((n, f[0]))

    A.check("every row is exactly 4 atoms", not bad_width,
            "; ".join("line %d: %r" % b for b in bad_width))
    A.check("⛔ every destination exists on u_map's route (THE GUARD)", not bad_dest,
            "; ".join("line %d names %r" % b for b in bad_dest))
    A.check("every row's page is one of the %d pages, or all" % (len(modes) - 1), not bad_mode,
            "; ".join("line %d: %r" % b for b in bad_mode))
    # What works on every page: the knobs, the transport, recover, the columns, the top row, save
    # and revert. A page that took one back would strand you there with no stop or recover but the
    # Launchpad's own, on a device that can be unplugged.
    missing = ["%s %s %s" % r for r in EVERY_PAGE if ["all"] + list(r) not in [f for _, f in rows]]
    A.check("⛔ the all rows are the %d rows every page shares" % len(EVERY_PAGE),
            not missing, "missing: %s" % missing[:6])
    shared = {r[0] for r in EVERY_PAGE}
    taken = {(f[0], f[1]) for _, f in rows if len(f) == 4 and f[0] != "all" and f[1] in shared}
    A.check("⛔ ... and only the performance page takes any back: save's and revert's buttons",
            taken == SHADOWED, "pages' own rows for shared controls: %s" % sorted(taken))
    # The top row is the song's sections on every page, each button's arg its place on the
    # row (u_song.lua's R.press): a row naming another place moves a lamp off its button.
    sec = sorted((f[1], f[3]) for _, f in rows if len(f) == 4 and f[2] == "section")
    A.check("⛔ the top row's eight are the section destination, CC 91 to 98 its buttons 1 to 8, "
            "and nothing else names it", sec == sorted(("lp-cc-%d" % (90 + n), "%d" % n)
                                                       for n in range(1, 9)),
            "section rows: %s" % sorted(set(sec)))
    # The Organelle's keys load songs on every page, each key's arg its place from the lowest,
    # the nth song of the setlist chosen (u_song.lua's R.key): a key naming another place loads
    # another song than the one its place in the setlist shows.
    keys = sorted((f[1], f[3]) for _, f in rows if len(f) == 4 and f[2] == "song")
    A.check("⛔ the Organelle's 25 keys are the song destination, og-key-60 to 84 its keys 1 to 25, "
            "and nothing else names it", keys == sorted(("og-key-%d" % (59 + k), "%d" % k)
                                                        for k in range(1, 26)),
            "song rows: %s" % sorted(set(keys))[:6])
    # drums passes its arg to c_steps as the command, so a misspelt one is a
    # knob that only says bad-selector when turned.
    takes = steps_cmds()
    drums = [(n, f[3]) for n, f in rows if len(f) == 4 and f[2] == "drums"]
    A.check("⛔ every drums row names a command c_steps takes",
            takes is not None and drums and all(a in takes for _, a in drums),
            "rows %s, c_steps takes %s" % (drums, takes))

    # arrangement passes its arg to its layout, which names the cell's role, and the role
    # goes to u_tempo: a row the layout lacks is layout-miss at the press, and a role u_tempo's
    # route lacks reaches its Lua as bad-selector.
    alay, roles = arrange_layout(), tempo_roles()
    arr = [(n, f[3]) for n, f in rows if len(f) == 4 and f[2] == "arrangement"]
    A.check("⛔ every arrangement row's arg is a cell of %s" % os.path.basename(ARRANGE_PAGE),
            arr and all(a in alay for _, a in arr),
            "rows %s, the layout holds %s" % (arr, sorted(alay)))
    A.check("⛔ ... and every cell there names a role u_tempo's route takes",
            roles and alay and all(len(v) == 1 and v[0] in roles for v in alay.values()),
            "the layout %s, u_tempo routes %s" % (alay, roles))
    A.check("... and every cell has its row, on every page",
            sorted(a for _, a in arr) == sorted(alay)
            and all(f[0] == "all" for _, f in rows if len(f) == 4 and f[2] == "arrangement"),
            "rows %s" % arr)
    A.check("tap is the layout's one cell, the nanoKONTROL's LOOP", alay == {"21": ["tap"]},
            "the layout: %s" % alay)

    # drum-page passes its arg to the layout g_grid paints from, whose role goes to c_steps: a row
    # the layout lacks is layout-miss at the press, and a role c_steps lacks is bad-selector.
    dlay = {}
    for line in open(DRUM_PAGE, encoding="utf-8"):
        f = line.split()
        if f:
            dlay[f[0]] = f[1:]
    drum = [(n, f) for n, f in rows if len(f) == 4 and f[2] == "drum-page"]
    A.check("⛔ every drum-page row's arg is a cell of %s, its own pad's, on the drums page alone, and "
            "every cell has its row" % os.path.basename(DRUM_PAGE),
            sorted(f[3] for _, f in drum) == sorted(dlay)
            and all(f[0] == "drums" and f[1] == "pad-" + f[3] for _, f in drum),
            "%d rows, %d cells" % (len(drum), len(dlay)))
    with open(CSTEPS, encoding="utf-8") as fh:
        steps = fh.read()
    presses = re.search(r"^R\.presses = \{(.*?)^\}", steps, re.M | re.S).group(1)
    takes = set(re.findall(r"^  \[?\"?([\w-]+)\"?\]? = function", presses, re.M))
    roles = {v[0] for v in dlay.values()}
    A.check("⛔ ... and every role there is one c_steps takes", roles <= takes and len(roles) == 6,
            "roles %s, c_steps takes %s" % (sorted(roles), sorted(takes)))
    A.check("⛔ the second row of the right 4x4: pad-35 the 500 BPM repeat and pad-38 the saved tempo, "
            "under repeat pads 1 and 4", dlay.get("35") == ["fast", "1"]
            and dlay.get("38") == ["recall", "1"] and dlay.get("45") == ["rep", "1"]
            and dlay.get("48") == ["rep", "4"], "the layout's cells: %s"
            % {k: dlay.get(k) for k in ("35", "38", "45", "48")})
    named = [f for _, f in rows if len(f) >= 2 and f[1] in ("pad-36", "pad-37")]
    A.check("⛔ and pad-36 and pad-37 between them are nothing: no row on any page, no cell",
            not named and "36" not in dlay and "37" not in dlay, "rows %s" % named)
    # A page of pads is one row, its pad's number after its arg (u_map.lua's lookup): the harmony and
    # melody pages' in c_melody's h and m, the performance page's in u_perform's. What each takes is
    # u_map_test.lua's.
    stars = sorted((f[0], f[2], f[3]) for _, f in rows if len(f) == 4 and f[1] == "pad-*")
    A.check("⛔ pad-* is the harmony, melody and performance pages'",
            stars == [("harmony", "melody", "h"), ("melody", "melody", "m"),
                      ("perform", "perform", "pad-")], stars)

    seen, dupes = {}, []
    for n, f in rows:
        if len(f) < 2:
            continue
        key = (f[0], f[1])
        if key in seen:
            dupes.append((n, key, seen[key]))
        else:
            seen[key] = n
    A.check("no duplicate (page, control) pair", not dupes,
            "; ".join("line %d repeats %s from line %d" % (n, " ".join(k), o)
                      for n, k, o in dupes))
    if dupes:
        A.note("text search returns only the FIRST match, so a repeat is DEAD and silent -- item 229")
    # panic is on u_map's route for the tests and u_err's, but a control
    # bound to it could silence the instrument mid-set with no way back but a
    # reload. Only the map could bind one, so it is checked by reading.
    panic_rows = [(n, " ".join(f)) for n, f in rows if len(f) > 2 and f[2] == "panic"]
    A.check("⛔ no map row binds a control to panic", not panic_rows,
            "; ".join("line %d: %r" % b for b in panic_rows))
    A.note("%d rows, %d distinct controls" % (len(rows), len({f[1] for _, f in rows if len(f) > 1})))

    # A control's row is u_map's alone (item 317). A duplicate of an unmapped
    # control's row is invisible on the screen, since g_oled updates rows in
    # place by name, so it is read off the files. The file set is checked too,
    # so a new m_ file can't go unchecked.
    found = {}
    for path in sorted(glob.glob("Cut It/m_*.pd")):
        name = os.path.basename(path)[:-3]
        found[name] = sum(1 for line in lib_pd.read(path)
                          if re.match(r"^#X obj \d+ \d+ (s|send) disp( [^;]*)?;$", line))
    A.check("every m_ file is one this check knows", sorted(found) == sorted(DISP_EXPECT),
            "found %s, expected %s" % (sorted(found), sorted(DISP_EXPECT)))
    bad = ["%s has %d, want %d" % (n, found[n], w)
           for n, w in sorted(DISP_EXPECT.items()) if found.get(n) != w]
    A.check("⛔ no device layer posts a control's row to disp -- the row is u_map's (item 317)",
            not bad, "; ".join(bad))
    A.note("[s disp] per m_ file: %s" % " ".join("%s:%d" % kv for kv in sorted(found.items())))


# Other modules share disp in every window (g_led, u_init's modal-off, u_err's
# alert), so "u_map drew nothing" is asked of u_map's rows alone. No row is an
# unmapped control's since 2026-11-04, so a gk-* one counts.
RESERVED = {"modal", "modal-off", "alert", "led", "grid", "diag"}


def umap_rows(events):
    return [e[1] for e in events
            if e[0] == "DISP" and e[1] and e[1][0] not in RESERVED]


# --------------------------------------------------------------- run assertions
def run_asserts(cap):
    print("\n=== B. the lookup, driven ===")
    order, by = A.windows(cap, "MAP", len(WINDOWS))
    W = lambda k: by.get(k, [])
    # [midiout] is not evidence: g_grid repaints the Launchpad off a [metro 100]
    # in every window. A mapped destination goes out by noteout, ctlout or pgmout.
    midi = lambda k: [e for e in W(k) if e[0] in ("NOTEOUT", "CTLOUT", "PGMOUT")]

    # Item 234: mother pushes knobs.txt at boot, and the table and the lookup
    # key's page must both be ready for it. Knob 1's tempo is u_map.lua's
    # line: 0.0958 is 60 bpm, 0.5 is 145, 0.9 is 229.
    early = [e for e in W("EARLY") if e[0] == "TEMPO"]
    A.check("⛔ a control moved at 300 ms ALREADY MAPS -- table and page key ready at load",
            any(abs(float(e[1][0]) - 60) < 1.5 for e in early if e[1]),
            "tempo in that window: %s" % [e[1] for e in early])
    A.check("a mapped control reaches its destination",
            any(e[0] == "CTLOUT" and e[1][1] == 41 for e in W("MAPPED")),
            repr(W("MAPPED")))
    # The row is named for what the control means, and it is the only row.
    A.check("⛔ ... and draws its MAPPED row on disp -- volca-cc41 64",
            any(d == ["volca-cc41", "64"] for d in [e[1] for e in W("MAPPED") if e[0] == "DISP"]),
            "disp in that window: %s" % [e[1] for e in W("MAPPED") if e[0] == "DISP"])
    A.check("⛔ the SAME control on another page does NOTHING (the table is by page)",
            not midi("PAGE-DEP"), repr(midi("PAGE-DEP")))
    # Only a control the map binds names itself (Brendan, 2026-11-04): an
    # unmapped one draws no <name> <raw> row either.
    A.check("⛔ ... and DRAWS nothing either -- no gk-cc row on the harmony page",
            not [d for d in umap_rows(W("PAGE-DEP")) if d[:1] == ["gk-cc"]],
            "u_map's rows in that window: %s" % umap_rows(W("PAGE-DEP")))
    A.check("... and that window was live -- knob 1, tempo on every page, set 103 bpm",
            any(e[0] == "TEMPO" and e[1] and abs(float(e[1][0]) - 103) < 1.5
                for e in W("PAGE-DEP")),
            "tempo in that window: %s" % [e[1] for e in W("PAGE-DEP") if e[0] == "TEMPO"])
    A.check("⛔ a row naming an unknown destination emits NO MIDI",
            not midi("BAD-DEST"), repr(midi("BAD-DEST")))
    A.check("⛔ ... and reports unknown-dest on err",
            any(e[0] == "ERR" and "unknown-dest" in " ".join(e[1]) for e in W("BAD-DEST")),
            repr(W("BAD-DEST")))

    # ------------------------------------------ a mode the key-setter cannot use
    # Items 294 and 297, ref/module/map.md: a stored `compose` with no mode name
    # once emptied the lookup key, and every mapped control drew its raw row.
    A.check("⛔ a mode that names no page is REFUSED, and says so",
            any(e[0] == "ERR" and "bad-mode" in " ".join(e[1]) for e in W("BAD-MODE")),
            repr(W("BAD-MODE")))
    # The error alone would not catch it; the key must survive. og-knob-1 is
    # tempo on every page, songs here.
    A.check("⛔ ... and the lookup KEY SURVIVES IT -- 0.6 is still 166 bpm",
            any(e[0] == "TEMPO" and e[1] == ["166"] for e in W("AFTER-BAD")),
            "tempo in that window: %s -- a poisoned key sends nothing here and "
            "draws og-knob-1 0.6 on the screen instead"
            % [e[1] for e in W("AFTER-BAD") if e[0] == "TEMPO"])
    A.check("⛔ ... and it does not draw a raw knob row either",
            not any(d and d[0].startswith("og-knob")
                    for d in [e[1] for e in W("AFTER-BAD") if e[0] == "DISP"]),
            "disp in that window: %s"
            % [e[1] for e in W("AFTER-BAD") if e[0] == "DISP"])

    # ------------------------------------------------------- parameter pickup
    # Pickup holds a restored knob until it passes through its stored value
    # (ref/module/map.md). Every negative has a liveness witness in its own
    # window: A.windows proves only that the MARK landed, not the actions after.
    print("\n=== C. parameter pickup ===")
    tempos = lambda k: [float(e[1][0]) for e in W(k) if e[0] == "TEMPO" and e[1]]
    cc = lambda k, n: [e[1] for e in W(k) if e[0] == "CTLOUT" and e[1][1] == n]

    A.check("⛔ a knob that has NOT crossed its stored value moves nothing",
            not tempos("SUPPRESS"), "tempo in that window: %s" % tempos("SUPPRESS"))
    A.check("... and that window was LIVE -- another control reached its destination",
            len(cc("SUPPRESS", 41)) == 1, repr(W("SUPPRESS")))

    A.check("⛔ moving FURTHER AWAY does not hand over either",
            not tempos("AWAY"), "tempo in that window: %s" % tempos("AWAY"))
    A.check("... and that window was live too",
            len(cc("AWAY", 41)) == 1, repr(W("AWAY")))

    A.check("⛔ CROSSING the stored value hands over -- 0.02 is 44 bpm",
            any(abs(t - 44) < 1.5 for t in tempos("CROSS")),
            "tempo in that window: %s" % tempos("CROSS"))
    A.check("and it tracks normally from then on -- 0.3 is 103 bpm",
            any(abs(t - 103) < 1.5 for t in tempos("LIVE")),
            "tempo in that window: %s" % tempos("LIVE"))

    # Buttons never pick up: a button given a slot would latch on its repeat.
    A.check("⛔ PLAY reaches start", any(e[0] == "START" for e in W("PLAY-1")),
            repr(W("PLAY-1")))
    # A button destination draws no row: the LED and the grid already say it.
    A.check("⛔ ... and a button destination draws NO row",
            not umap_rows(W("PLAY-1")),
            "u_map's disp in that window: %s" % umap_rows(W("PLAY-1")))
    A.check("⛔ STOP reaches stop", any(e[0] == "STOP" for e in W("STOP-1")),
            repr(W("STOP-1")))
    A.check("⛔ ... and PLAY again starts AGAIN -- start is not a toggle",
            any(e[0] == "START" for e in W("PLAY-2")),
            "%s. A latched control would be silent the second time, and the "
            "transport would stick wherever it was" % (W("PLAY-2"),))

    # Knob 2 armed at 400 ms, inside the boot window, and has not crossed. Knob
    # 3's first value comes at 4200 ms, after it: a hand, not a restore, so it
    # never arms.
    A.check("⛔ pickup state is PER KNOB -- knob 2 is still held while knob 1 is live",
            len(cc("KNOB-2", 42)) == 0, "cc 42 in that window: %s" % cc("KNOB-2", 42))
    A.check("... and knob 2's window was live -- its first value DID land at 400 ms",
            len(cc("EARLY-2", 42)) == 1, repr(W("EARLY-2")))
    # The screen shows the mapped value, not the raw position (item 238).
    disp = lambda k: [e[1] for e in W(k) if e[0] == "DISP"]
    A.check("⛔ while HELD the row carries BOTH numbers -- bpm <latched> (<knob>)",
            any(d[:2] == ["bpm", "60"] and d[2:] == ["(145)"] for d in disp("SUPPRESS")),
            "disp in that window: %s" % disp("SUPPRESS"))
    A.check("... and it follows the knob while still held -- 0.9 is 229",
            any(d[:2] == ["bpm", "60"] and d[2:] == ["(229)"] for d in disp("AWAY")),
            "disp in that window: %s" % disp("AWAY"))
    A.check("⛔ once LIVE the row is the mapped value alone -- no raw og-knob-1",
            any(d == ["bpm", "103"] for d in disp("LIVE"))
            and not any(d and d[0].startswith("og-knob") for d in disp("LIVE")),
            "disp in that window: %s" % disp("LIVE"))

    A.check("⛔ a knob first seen AFTER the boot window never arms -- both values pass",
            len(cc("LATE-KNOB", 43)) == 2,
            "cc 43 in that window: %s -- expected two, the no-Save case"
            % cc("LATE-KNOB", 43))

    # The held row uses its destination's scaling (item 240): knob 2 is armed at
    # 0.5 and mapped to volca-cc 42 on the performance page by a gate row, so it never draws a bpm.
    A.check("⛔ a held knob draws ITS OWN destination's row -- volca-cc42 64 (114)",
            any(d == ["volca-cc42", "64", "(114)"] for d in disp("KNOB-2")),
            "disp in that window: %s" % disp("KNOB-2"))
    A.check("⛔ ... and never a bpm row -- the tempo scaling does not leak",
            not any(d[:1] == ["bpm"] for d in disp("KNOB-2")),
            "disp in that window: %s" % disp("KNOB-2"))
    A.check("... and that window was live -- another control reached its destination",
            len(cc("KNOB-2", 41)) == 1, repr(W("KNOB-2")))

    # Knob 4 armed at 0, so "crossed" (target <= value flipping) can never
    # happen, and returning to the target must release it.
    A.check("⛔ a knob armed against a target of 0 is still HELD on the way up",
            len(cc("RAIL-UP", 44)) == 0, "cc 44 in that window: %s" % cc("RAIL-UP", 44))
    A.check("... and that window was live too",
            len(cc("RAIL-UP", 41)) == 1, repr(W("RAIL-UP")))
    # Knob 2 is the drums' global last step on every page (Brendan, 2026-11-06):
    # on the harmony page it reaches c_steps, whose own latch holds it at 16 until it is
    # turned through it, and draws that held row. 0.75 is step 24.
    A.check("⛔ knob 2 works on the harmony page too: c_steps draws its held row, last-step 16 (24)",
            ["last-step", "16", "(24)"] in disp("UNMAPPED"),
            "disp in that window: %s" % disp("UNMAPPED"))
    A.check("⛔ an UNMAPPED control draws nothing -- gk-none, beside knob 2's row",
            not [d for d in disp("UNMAPPED") if d[:1] == ["gk-none"]],
            "disp in that window: %s" % disp("UNMAPPED"))
    A.check("... and it is silent on every bus too",
            not midi("UNMAPPED"), repr(midi("UNMAPPED")))

    A.check("⛔ ... and RETURNING TO the target releases it -- a rail has no beyond",
            len(cc("RAIL-BACK", 44)) == 1,
            "cc 44 in that window: %s -- a dead knob for the whole session"
            % cc("RAIL-BACK", 44))

    # The Launchpad's left column publishes both edges, so the release has to be
    # gated out before u_voices' rule, which has no test of its own.
    modes = lambda k: [e[1] for e in W(k) if e[0] == "MODE"]
    A.check("⛔ a left-column button selects its page, alone on the bus",
            modes("LEFT-2") == [["harmony"]],
            "mode in that window: %s" % modes("LEFT-2"))
    A.check("⛔ ... and its RELEASE selects nothing at all",
            modes("LEFT-2-RELEASE") == [],
            "mode in that window: %s -- a Launchpad CC button sends 127 then 0, "
            "so an ungated branch fires the same page twice per press" % modes("LEFT-2-RELEASE"))
    # A mode saved before pages had names, restored at about 3.5 s: scratch-gates.py leaves
    # `mode compose mode-1` in the auto file. Nothing hears that key, so nothing can take compose
    # for a page: the boot is on the performance page, and the song's load says so.
    restored = [m for k in ("LIVE", "PLAY-1", "STOP-1", "PLAY-2", "KNOB-2", "LATE-KNOB",
                            "BAD-DEST", "RAIL-UP", "RAIL-BACK") for m in modes(k)]
    A.check("⛔ a mode the old code saved means nothing now: the boot's page is the performance page",
            restored == [["perform"]],
            "mode between 3.2 and 5 s: %s" % restored)
    A.check("⛔ aux's press, through the table, opens the songs page, once",
            modes("AUX") == [["songs"]],
            "mode in that window: %s" % modes("AUX"))
    # The top row is sections, and never held a page's key on this table.
    A.check("the top row's first button selects no page",
            modes("TOP-ROW") == [],
            "mode in that window: %s" % modes("TOP-ROW"))
    A.check("⛔ ... and, a button, it draws nothing -- no lp-cc-91 row and no section row",
            not [d for d in umap_rows(W("TOP-ROW")) if d[:1] in (["lp-cc-91"], ["section"])],
            "u_map's rows in that window: %s" % umap_rows(W("TOP-ROW")))

    # The lint proves diag is on the route; this proves the row reaches it.
    A.check("⛔ Setup's press, through the table, opens the diagnostics page", modes("SETUP") == [["diag"]],
            "mode in that window: %s" % modes("SETUP"))
    diag = lambda k: [e[1] for e in W(k) if e[0] == "DISP" and e[1][:1] == ["diag"]]
    A.check("⛔ its first pad's row summons the diagnostic layer",
            len(diag("DIAG-DEST")) == 1,
            "disp in that window: %s" % [e[1] for e in W("DIAG-DEST")
                                         if e[0] == "DISP"])
    # Exactly one: firing on the release too would reset the TTL, and the
    # screen would outlive the button by its whole eight seconds.
    A.check("⛔ ... and the RELEASE does not summon it again",
            len(diag("DIAG-RELEASE")) == 0,
            "disp in that window: %s. A pad publishes BOTH edges, so every button "
            "destination's non-zero gate is load-bearing" % diag("DIAG-RELEASE"))

    # ------------------------------------------------ every destination's row
    # One c_mapped per value destination, each drawing its own row in its own
    # units. Exact lists: a second row means two instances answered one control,
    # or the raw-row path fired for a mapped one.
    print("\n=== E. every value destination draws its mapped row ===")
    rows = lambda k: umap_rows(W(k))
    A.check("⛔ closed in the order they opened: the songs page, row 2's, and the lit button again the "
            "performance page, back for the rows",
            modes("PERFORM") == [["songs"], ["harmony"], ["perform"]],
            "mode in that window: %s" % modes("PERFORM"))
    A.check("⛔ volca-cc draws volca-cc41 64", rows("ROW-CC") == [["volca-cc41", "64"]],
            "disp in that window: %s" % disp("ROW-CC"))
    A.check("⛔ volca-note draws volca-note60 100", rows("ROW-NOTE") == [["volca-note60", "100"]],
            "disp in that window: %s" % disp("ROW-NOTE"))
    A.check("... and the note itself still fires",
            any(e[0] == "NOTEOUT" and e[1][:2] == [60, 100] for e in W("ROW-NOTE")),
            repr(W("ROW-NOTE")))
    A.check("⛔ volca-prog draws volca-prog 20 -- the ARG, because the value is only a gate",
            rows("ROW-PROG") == [["volca-prog", "20"]],
            "disp in that window: %s" % disp("ROW-PROG"))
    A.check("... and the program change still fires",
            any(e[0] == "PGMOUT" for e in W("ROW-PROG")), repr(W("ROW-PROG")))
    # The exception: a key draws nothing, since 25 keys reporting both edges
    # would evict the five-row screen twice per note (item 293).
    A.check("⛔ volca-key draws NOTHING -- the keyboard exception, item 293",
            not disp("ROW-KEY"), "disp in that window: %s" % disp("ROW-KEY"))
    A.check("... and the key still sounds -- the window was live",
            any(e[0] == "NOTEOUT" and e[1][:2] == [60, 100] for e in W("ROW-KEY")),
            repr(W("ROW-KEY")))
    notes = [e[1] for e in W("ROW-KEY") if e[0] == "NOTEOUT" and e[1][1:2] != [0]]
    A.check("⛔ ... and the Organelle's own key plays nothing -- one note, gk-key's",
            len(notes) == 1,
            "note-ons in that window: %s. The keys choose songs, and play no note "
            "(Brendan, 2026-11-05)" % notes)
    # Pressure: an unmapped pad-NN-at draws no row (item 318), a stream per held
    # pad, and since 2026-11-04 nor does the pad's own press with nothing in play. gk-cc,
    # mapped on the performance page, is the witness that the window drew at all.
    A.check("⛔ neither an unmapped pad's pressure nor its press draws a row",
            rows("PRESSURE") == [["volca-cc41", "64"]],
            "u_map's rows in that window: %s -- volca-cc41 64 alone, gk-cc's" % rows("PRESSURE"))
    A.check("⛔ MAPPED pressure still draws its destination's row -- volca-cc45 64",
            rows("PRESSURE-MAPPED") == [["volca-cc45", "64"]],
            "disp in that window: %s" % disp("PRESSURE-MAPPED"))


# --------------------------------------------------------------- the no-Save run
def nosave_asserts(cap):
    """The same drive against a patch folder with no knobs.txt (item 239).

    mother pushes a value at boot either way, the saved position or the live
    one, and only the first is a restore. With none, knob 1 is held at 120,
    u_tempo's own, until it is turned through it (u_map.lua's R.UNSAVED), and
    every other knob is live. Each check here is the opposite of one above; if
    both runs agree, u_map is not reading the file.
    """
    print("\n=== D. no knobs.txt -- knob 1 held at 120, nothing else held ===")
    order, by = A.windows(cap, "MAP", len(WINDOWS))
    W = lambda k: by.get(k, [])
    tempos = lambda k: [float(e[1][0]) for e in W(k) if e[0] == "TEMPO" and e[1]]
    cc = lambda k, n: [e[1] for e in W(k) if e[0] == "CTLOUT" and e[1][1] == n]
    disp = lambda k: [e[1] for e in W(k) if e[0] == "DISP"]

    A.check("⛔ the boot push is HELD with no knobs.txt -- 0.0958 (60 bpm) reaches no tempo",
            not tempos("EARLY"), "tempo in that window: %s" % tempos("EARLY"))
    A.check("⛔ ... and draws the held row at 120 -- bpm 120 (60)",
            any(d == ["bpm", "120", "(60)"] for d in disp("EARLY")),
            "disp in that window: %s" % disp("EARLY"))
    A.check("... and that window was live -- knob 2's first value reached its destination",
            len(cc("EARLY-2", 42)) == 1, repr(W("EARLY-2")))
    A.check("⛔ turning knob 1 THROUGH 120 releases it -- 0.5 at 2400 ms is 145",
            any(abs(t - 145) < 1.5 for t in tempos("SUPPRESS")),
            "tempo in that window: %s -- still held at 120?" % tempos("SUPPRESS"))
    A.check("... and that window was live -- another control reached its destination",
            len(cc("SUPPRESS", 41)) == 1, repr(W("SUPPRESS")))
    A.check("⛔ knob 2 is live -- exactly one cc 42, where the armed run has none",
            len(cc("KNOB-2", 42)) == 1, "cc 42 in that window: %s" % cc("KNOB-2", 42))
    A.check("⛔ ... and its row is the mapped value ALONE -- volca-cc42 114, no bracket",
            any(d == ["volca-cc42", "114"] for d in disp("KNOB-2"))
            and not any(len(d) > 2 for d in disp("KNOB-2") if d[:1] == ["volca-cc42"]),
            "disp in that window: %s" % disp("KNOB-2"))

if __name__ == "__main__":
    static_lint()
    run_asserts(A.require_capture(sys.stdin.read()))
    if "--nosave" in sys.argv:
        nosave_asserts(A.require_capture(
            open(sys.argv[sys.argv.index("--nosave") + 1]).read()))
    sys.exit(1 if A.report() else 0)
