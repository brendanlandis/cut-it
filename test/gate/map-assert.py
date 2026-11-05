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
# Every m_ file and its exact [s disp] count. Only m_organelle has one, and it
# carries aux's modal, never a control's row. The file set is exact too: m_404
# went with the SP-404, and m_streich and m_nanokey came with the synths
# (2026-11-04).
DISP_EXPECT = {"m_launchpad": 0, "m_nano": 0, "m_organelle": 1, "m_volca": 0,
               "m_streich": 0, "m_nanokey": 0}
SYNTH_PAGE = "Cut It/cut-it-synth-page.txt"
ULUA = "Cut It/u_map.lua"
# The rows every page has (map.md): <control> <dest> <arg>.
EVERY_PAGE = [("og-knob-1", "tempo", "0"), ("xport-2", "start", "0"), ("xport-5", "stop", "0"),
              ("lp-cc-90", "recover", "0"), ("og-shift-60", "diag", "0"),
              ("og-shift-61", "test-mode", "0"), ("lp-setup", "test-mode", "0"),
              ("og-shift-72", "stop", "0"), ("og-shift-84", "recover", "0")]
# Both runs are counted against this one list, so neither passes a driver that
# died early.
WINDOWS = ["EARLY", "EARLY-2", "RAIL-ARM", "SUPPRESS", "MAPPED", "AWAY", "CROSS",
           "LIVE", "PLAY-1", "STOP-1", "PLAY-2", "KNOB-2", "LATE-KNOB", "BAD-DEST",
           "RAIL-UP", "RAIL-BACK", "MODE-4", "MODE-DEP", "MODE-4-RELEASE",
           "TOP-ROW-FREE", "UNMAPPED", "MODE-8", "BAD-MODE", "AFTER-BAD", "DIAG-DEST",
           "DIAG-RELEASE",
           "SHIFT-STOP", "MODE-1", "ROW-CC", "ROW-NOTE", "ROW-PROG",
           "ROW-KEY", "PRESSURE", "PRESSURE-MAPPED"]


# --------------------------------------------------------------- static lint
def route_destinations():
    """The literal allowlist: the arguments of u_map's destination route box."""
    for line in lib_pd.read(UMAP):
        m = re.match(r"^#X obj \d+ \d+ route (tempo .*);$", line)
        if m:
            return m.group(1).split()
    return None


def mode_keys():
    """The mode keys: the arguments of u_map's first route, the Launchpad's left column."""
    for line in lib_pd.read(UMAP):
        m = re.match(r"^#X obj \d+ \d+ route (lp-cc-\d+(?: lp-cc-\d+)*);$", line)
        if m:
            return m.group(1).split()
    return None


def pages():
    """R.PAGES in u_map.lua: how many pages the Lua takes, mode-1 to mode-<n>."""
    m = re.search(r"^R\.PAGES = (\d+)$", open(ULUA, encoding="utf-8").read(), re.M)
    return int(m.group(1)) if m else None


def steps_cmds():
    """The commands c_steps takes on its inlet: the keys of c_steps.lua's R.presses."""
    src = open(os.path.join(os.path.dirname(UMAP), "c_steps.lua"), encoding="utf-8").read()
    m = re.search(r"^R\.presses = \{\n(.*?)^\}", src, re.M | re.S)
    if not m:
        return None
    keys = re.findall(r'^  (?:\["([\w-]+)"\]|(\w+)) = function', m.group(1), re.M)
    return sorted(a or b for a, b in keys)


def synths():
    """The synths c_synth takes: c_synth.lua's R.SYNTHS."""
    src = open(os.path.join(os.path.dirname(UMAP), "c_synth.lua"), encoding="utf-8").read()
    m = re.search(r"^R\.SYNTHS = \{([^}]*)\}", src, re.M)
    return re.findall(r'"([\w-]+)"', m.group(1)) if m else None


def synth_layout():
    """{grid index: synth} from the synth page's layout, which u_map's synth handler and
    g_grid both read."""
    lay = {}
    for line in open(SYNTH_PAGE, encoding="utf-8"):
        f = line.split()
        if f:
            lay[f[0]] = f[1:]
    return lay


def static_lint():
    print("\n=== A. the map, checked by READING -- no Pd involved ===")
    dests = route_destinations()
    A.check("u_map still has a literal destination route box", dests is not None,
            "expected a box starting 'route tempo ...' in " + UMAP)
    if dests is None:
        return
    A.note("allowlist is %d destinations: %s" % (len(dests), " ".join(dests)))

    # The pages, counted twice: the keys that choose them and the Lua that
    # takes them. A key the Lua refuses says bad-mode; a page with no key can
    # never be chosen.
    keys, n = mode_keys(), pages()
    A.check("u_map's mode keys are the left column's eight, CC 80 down to 10",
            keys == ["lp-cc-%d" % c for c in range(80, 0, -10)],
            "route box: %s" % keys)
    A.check("⛔ u_map.lua takes exactly the pages the keys choose -- R.PAGES is %s"
            % len(keys or []), n is not None and keys and n == len(keys),
            "R.PAGES = %s, %d keys" % (n, len(keys or [])))
    modes = ["mode-%d" % k for k in range(1, (n or 0) + 1)]
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
    A.check("every row's mode is one of the %d pages" % len(modes), not bad_mode,
            "; ".join("line %d: %r" % b for b in bad_mode))
    # What works on every page: the tempo, the transport, recover, diag and test
    # mode. A page that lacked one would strand you there with no stop or recover
    # but the Launchpad's own, on a device that can be unplugged.
    missing = ["%s %s %s on %s" % (c, d, a, p) for c, d, a in EVERY_PAGE for p in modes
               if [p, c, d, a] not in [f for _, f in rows]]
    A.check("⛔ every page carries the %d rows every page shares" % len(EVERY_PAGE),
            modes and not missing, "missing: %s" % missing[:6])
    # drums passes its arg to c_steps as the command, so a misspelt one is a
    # knob that only says bad-selector when turned.
    takes = steps_cmds()
    drums = [(n, f[3]) for n, f in rows if len(f) == 4 and f[2] == "drums"]
    A.check("⛔ every drums row names a command c_steps takes",
            takes is not None and drums and all(a in takes for _, a in drums),
            "rows %s, c_steps takes %s" % (drums, takes))

    # synth passes its arg to the layout, which names the synth: a row the layout lacks
    # is layout-miss on the screen at the press, and a synth c_synth lacks bad-synth.
    lay, chooses = synth_layout(), synths()
    synth = [(n, f[3]) for n, f in rows if len(f) == 4 and f[2] == "synth"]
    A.check("⛔ every synth row's arg is a cell of %s" % os.path.basename(SYNTH_PAGE),
            synth and all(a in lay for _, a in synth),
            "rows %s, the layout holds %s" % (synth, sorted(lay)))
    A.check("⛔ ... and every cell there names one synth c_synth takes",
            chooses and lay and all(len(v) == 1 and v[0] in chooses for v in lay.values()),
            "the layout %s, c_synth takes %s" % (lay, chooses))
    A.check("... and every cell has its row on page 3, where the pads choose",
            sorted(a for _, a in synth) == sorted(lay)
            and all(f[0] == "mode-3" for _, f in rows if len(f) == 4 and f[2] == "synth"),
            "rows %s" % synth)

    seen, dupes = {}, []
    for n, f in rows:
        if len(f) < 2:
            continue
        key = (f[0], f[1])
        if key in seen:
            dupes.append((n, key, seen[key]))
        else:
            seen[key] = n
    A.check("no duplicate (mode, control) pair", not dupes,
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


# Other modules share disp in every window (u_tempo's footer, g_led, u_init's
# modal-off, u_net's alert), so "u_map drew nothing" is asked of u_map's rows
# alone. A gk-* row is an unmapped gate control's raw report.
RESERVED = {"in-l", "in-r", "status", "modal", "modal-off", "alert", "led", "grid", "diag"}


def umap_rows(events):
    return [e[1] for e in events
            if e[0] == "DISP" and e[1] and e[1][0] not in RESERVED
            and not e[1][0].startswith("gk-")]


# --------------------------------------------------------------- run assertions
def run_asserts(cap):
    print("\n=== B. the lookup, driven ===")
    order, by = A.windows(cap, "MAP", len(WINDOWS))
    W = lambda k: by.get(k, [])
    # [midiout] is not evidence: g_grid repaints the Launchpad off a [metro 100]
    # in every window. A mapped destination goes out by noteout, ctlout or pgmout.
    midi = lambda k: [e for e in W(k) if e[0] in ("NOTEOUT", "CTLOUT", "PGMOUT")]

    # Item 234: mother pushes knobs.txt at boot, and the table and the lookup
    # key's mode must both be ready for it. Knob 1's tempo is u_map.lua's
    # curve: 0.0958 is 29 bpm, 0.5 is 125, 0.9 is 350.
    early = [e for e in W("EARLY") if e[0] == "TEMPO"]
    A.check("⛔ a control moved at 300 ms ALREADY MAPS -- table and mode key ready at load",
            any(abs(float(e[1][0]) - 29) < 1.5 for e in early if e[1]),
            "tempo in that window: %s" % [e[1] for e in early])
    A.check("a mapped control reaches its destination",
            any(e[0] == "CTLOUT" and e[1][1] == 41 for e in W("MAPPED")),
            repr(W("MAPPED")))
    # The row is named for what the control means, and it is the only row.
    A.check("⛔ ... and draws its MAPPED row on disp -- volca-cc41 64",
            any(d == ["volca-cc41", "64"] for d in [e[1] for e in W("MAPPED") if e[0] == "DISP"]),
            "disp in that window: %s" % [e[1] for e in W("MAPPED") if e[0] == "DISP"])
    A.check("⛔ the SAME control in another mode does NOTHING (mode-dependence)",
            not midi("MODE-DEP"), repr(midi("MODE-DEP")))
    # The negative's witness: an unmapped control reports its raw value.
    A.check("... and it reports its RAW value on disp -- the witness for the line above",
            any(d[:2] == ["gk-cc", "64"]
                for d in [e[1] for e in W("MODE-DEP") if e[0] == "DISP"]),
            "disp in that window: %s" % [e[1] for e in W("MODE-DEP") if e[0] == "DISP"])
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
    # tempo on every page, page 8 here.
    A.check("⛔ ... and the lookup KEY SURVIVES IT -- 0.6 is still 150 bpm",
            any(e[0] == "TEMPO" and e[1] == ["150"] for e in W("AFTER-BAD")),
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

    A.check("⛔ CROSSING the stored value hands over -- 0.02 is 14 bpm",
            any(abs(t - 14) < 1.5 for t in tempos("CROSS")),
            "tempo in that window: %s" % tempos("CROSS"))
    A.check("and it tracks normally from then on -- 0.3 is 75 bpm",
            any(abs(t - 75) < 1.5 for t in tempos("LIVE")),
            "tempo in that window: %s" % tempos("LIVE"))

    # Buttons never pick up: a button given a slot would latch on its repeat.
    A.check("⛔ PLAY reaches start", any(e[0] == "START" for e in W("PLAY-1")),
            repr(W("PLAY-1")))
    # A button destination draws no row: the footer, LED and grid already say it.
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
            any(d[:2] == ["bpm", "29"] and d[2:] == ["(125)"] for d in disp("SUPPRESS")),
            "disp in that window: %s" % disp("SUPPRESS"))
    A.check("... and it follows the knob while still held -- 0.9 is 350",
            any(d[:2] == ["bpm", "29"] and d[2:] == ["(350)"] for d in disp("AWAY")),
            "disp in that window: %s" % disp("AWAY"))
    A.check("⛔ once LIVE the row is the mapped value alone -- no raw og-knob-1",
            any(d == ["bpm", "75"] for d in disp("LIVE"))
            and not any(d and d[0].startswith("og-knob") for d in disp("LIVE")),
            "disp in that window: %s" % disp("LIVE"))

    A.check("⛔ a knob first seen AFTER the boot window never arms -- both values pass",
            len(cc("LATE-KNOB", 43)) == 2,
            "cc 43 in that window: %s -- expected two, the no-Save case"
            % cc("LATE-KNOB", 43))

    # The held row uses its destination's scaling (item 240): knob 2 is armed at
    # 0.5 and mapped to volca-cc 42 in mode-1 by a gate row, so it never draws a bpm.
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
    # Held and unmapped at once: knob 2 is still armed and maps to nothing in
    # mode-4, and must still report (item 242).
    A.check("⛔ a HELD and UNMAPPED knob still reports its raw value",
            any(d[:2] == ["og-knob-2", "0.75"]
                for d in [e[1] for e in W("UNMAPPED") if e[0] == "DISP"]),
            "disp in that window: %s" % [e[1] for e in W("UNMAPPED") if e[0] == "DISP"])
    A.check("... and it is still silent on every bus -- the row above is the witness",
            not midi("UNMAPPED"), repr(midi("UNMAPPED")))

    A.check("⛔ ... and RETURNING TO the target releases it -- a rail has no beyond",
            len(cc("RAIL-BACK", 44)) == 1,
            "cc 44 in that window: %s -- a dead knob for the whole session"
            % cc("RAIL-BACK", 44))

    # The Launchpad's left column publishes both edges, so the release has to be
    # gated out before the mode branches, which have no test of their own.
    modes = lambda k: [e[1] for e in W(k) if e[0] == "MODE"]
    A.check("⛔ a lit left-column button selects its page, alone on the bus",
            modes("MODE-4") == [["mode-4"]],
            "mode in that window: %s" % modes("MODE-4"))
    A.check("⛔ ... and its RELEASE selects nothing at all",
            modes("MODE-4-RELEASE") == [],
            "mode in that window: %s -- a Launchpad CC button sends 127 then 0, "
            "so an ungated branch fires the same mode twice per press. It is "
            "idempotent, which is exactly why nothing would look wrong"
            % modes("MODE-4-RELEASE"))
    # A mode the old code saved, <class> <page>, restored at about 3.5 s:
    # scratch-gates.py leaves `mode compose mode-1` in the auto file. The class
    # goes before the bus, or every reader of it would take compose for a page.
    restored = [m for k in ("LIVE", "PLAY-1", "STOP-1", "PLAY-2", "KNOB-2", "LATE-KNOB",
                            "BAD-DEST", "RAIL-UP", "RAIL-BACK") for m in modes(k)]
    A.check("⛔ a mode the old code saved, compose mode-1, restores as mode-1 alone",
            restored == [["mode-1"]],
            "mode between 3.2 and 5 s: %s" % restored)
    # The bottom key of the left column, a press and its release in one window:
    # page 8, once. The windows after it run there, so the shipped rows every
    # page shares are driven on the last page.
    A.check("⛔ the left column's bottom key selects page 8, once for a press and release",
            modes("MODE-8") == [["mode-8"]],
            "mode in that window: %s" % modes("MODE-8"))
    # The top row held the mode keys before they moved to the left column.
    A.check("the top row's first button selects no mode any more",
            modes("TOP-ROW-FREE") == [],
            "mode in that window: %s" % modes("TOP-ROW-FREE"))
    A.check("... and, unmapped, it names itself -- lp-cc-91 127",
            ["lp-cc-91", "127"] in umap_rows(W("TOP-ROW-FREE")),
            "u_map's rows in that window: %s" % umap_rows(W("TOP-ROW-FREE")))

    # The lint proves diag is on the route; this proves the row reaches it.
    # og-shift-60 is mapped to diag on every page, page 8 here.
    diag = lambda k: [e[1] for e in W(k) if e[0] == "DISP" and e[1][:1] == ["diag"]]
    A.check("⛔ a row naming diag summons the diagnostic layer",
            len(diag("DIAG-DEST")) == 1,
            "disp in that window: %s" % [e[1] for e in W("DIAG-DEST")
                                         if e[0] == "DISP"])
    # Exactly one: firing on the release too would reset the TTL, and the
    # screen would outlive the button by its whole eight seconds.
    A.check("⛔ ... and the RELEASE does not summon it again",
            len(diag("DIAG-RELEASE")) == 0,
            "disp in that window: %s. A shifted key publishes BOTH edges, so "
            "every button destination's non-zero gate is load-bearing here in a "
            "way it never was for a nano button that only sent the press"
            % diag("DIAG-RELEASE"))
    # The transport is on the nano, so with it unplugged this shifted key is the
    # only stop left.
    A.check("⛔ a shifted key reaches stop, on the panel that cannot go missing",
            any(e[0] == "STOP" for e in W("SHIFT-STOP")), repr(W("SHIFT-STOP")))

    # ------------------------------------------------ every destination's row
    # One c_mapped per value destination, each drawing its own row in its own
    # units. Exact lists: a second row means two instances answered one control,
    # or the raw-row path fired for a mapped one.
    print("\n=== E. every value destination draws its mapped row ===")
    rows = lambda k: umap_rows(W(k))
    A.check("mode-1 is back for the rows",
            modes("MODE-1") == [["mode-1"]],
            "mode in that window: %s" % modes("MODE-1"))
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
            "note-ons in that window: %s. The keys have no row until they choose "
            "songs (Brendan, 2026-11-04)" % notes)
    # Pressure: an unmapped pad-NN-at draws no raw row, since a stream per held
    # pad would fill the screen (item 318). pad-36 is the witness, and proves
    # the test is not too wide.
    A.check("⛔ an UNMAPPED pad's pressure draws NO row -- pad-11-at is exempt",
            not [d for d in rows("PRESSURE") if d[:1] == ["pad-11-at"]],
            "disp in that window: %s" % disp("PRESSURE"))
    A.check("... while the pad's own press still draws its raw row -- pad-36 100",
            [d for d in rows("PRESSURE") if d[:1] == ["pad-36"]] == [["pad-36", "100"]],
            "disp in that window: %s" % disp("PRESSURE"))
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

    A.check("⛔ the boot push is HELD with no knobs.txt -- 0.0958 (29 bpm) reaches no tempo",
            not tempos("EARLY"), "tempo in that window: %s" % tempos("EARLY"))
    A.check("⛔ ... and draws the held row at 120 -- bpm 120 (29)",
            any(d == ["bpm", "120", "(29)"] for d in disp("EARLY")),
            "disp in that window: %s" % disp("EARLY"))
    A.check("... and that window was live -- knob 2's first value reached its destination",
            len(cc("EARLY-2", 42)) == 1, repr(W("EARLY-2")))
    A.check("⛔ turning knob 1 THROUGH 120 releases it -- 0.5 at 2400 ms is 125",
            any(abs(t - 125) < 1.5 for t in tempos("SUPPRESS")),
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
