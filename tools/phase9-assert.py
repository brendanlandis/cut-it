#!/usr/bin/env python3
"""Phase 9's analyser: the static map lint, and the assertions over a captured run.

Two halves, and the FIRST ONE NEEDS NO Pd AT ALL.

  1. THE STATIC LINT reads Cut It/cut-it-map.txt and the literal route box in
     Cut It/u_map.pd and checks that every destination a row can name exists as
     an argument on that route. THAT IS THE ALLOWLIST GUARD, ENFORCED BY READING
     -- the same way the project audits its global sends. It is the cheapest and
     strongest check here, and it is the one that stays true as the table grows.

  2. THE RUN ASSERTIONS read a capture produced by phase9-assert.sh, which
     rewrote noteout/ctlout/pgmout/notein to printing stubs in a scratch copy.

Reads the capture on stdin. Exits non-zero on any failure.
"""
import re
import sys

MAP = "Cut It/cut-it-map.txt"
UMAP = "Cut It/u_map.pd"
MODES = ["mode-%d" % n for n in range(1, 7)]

fails = 0
verbose = "-v" in sys.argv


def check(name, ok, detail=""):
    global fails
    if not ok:
        fails += 1
    print("  %s  %s%s" % ("PASS" if ok else "FAIL", name,
                          "" if (ok and not verbose) else ("   -- " + detail if detail else "")))


def note(text):
    print("  note  " + text)


# --------------------------------------------------------------- static lint
def route_destinations():
    """The literal allowlist: the arguments of u_map's destination route box."""
    for line in open(UMAP):
        m = re.match(r"^#X obj \d+ \d+ route (tempo .*);$", line.strip())
        if m:
            return m.group(1).split()
    return None


def static_lint():
    print("\n=== A. the map, checked by READING -- no Pd involved ===")
    dests = route_destinations()
    check("u_map still has a literal destination route box", dests is not None,
          "expected a box starting 'route tempo ...' in " + UMAP)
    if dests is None:
        return
    note("allowlist is %d destinations: %s" % (len(dests), " ".join(dests)))

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
        if f[0] not in MODES:
            bad_mode.append((n, f[0]))

    check("every row is exactly 4 atoms", not bad_width,
          "; ".join("line %d: %r" % b for b in bad_width))
    check("⛔ every destination exists on u_map's route (THE GUARD)", not bad_dest,
          "; ".join("line %d names %r" % b for b in bad_dest))
    check("every mode is one of the six", not bad_mode,
          "; ".join("line %d: %r" % b for b in bad_mode))

    seen, dupes = {}, []
    for n, f in rows:
        if len(f) < 2:
            continue
        key = (f[0], f[1])
        if key in seen:
            dupes.append((n, key, seen[key]))
        else:
            seen[key] = n
    check("no duplicate (mode, control) pair", not dupes,
          "; ".join("line %d repeats %s from line %d" % (n, " ".join(k), o)
                    for n, k, o in dupes))
    if dupes:
        note("text search returns only the FIRST match, so a repeat is DEAD and silent -- item 229")
    note("%d rows, %d distinct controls" % (len(rows), len({f[1] for _, f in rows if len(f) > 1})))


# --------------------------------------------------------------- run assertions
def parse(cap):
    """-> (marks in order, {mark: [(kind, [floats])]})"""
    order, by, cur = [], {}, "PRE"
    by[cur] = []
    pat = re.compile(r"^(NOTEOUT|CTLOUT|PGMOUT):\s+(-?[\d.]+(?:\s+-?[\d.]+)*)$")
    for line in cap.splitlines():
        line = line.strip()
        m = re.match(r"^PH9:\s+MARK\s+(\S+)$", line)
        if m:
            cur = m.group(1); order.append(cur); by.setdefault(cur, [])
            continue
        m = pat.match(line)
        if m:
            by[cur].append((m.group(1), [float(v) for v in m.group(2).split()]))
            continue
        m = re.match(r"^(PARAM|DISP|ERR|TEMPO):\s+(.*)$", line)
        if m:
            by[cur].append((m.group(1), m.group(2).split()))
    return order, by


def run_asserts(cap):
    order, by = parse(cap)
    W = lambda k: by.get(k, [])
    midi = lambda k: [e for e in W(k) if e[0] in ("NOTEOUT", "CTLOUT", "PGMOUT")]
    ons = lambda k: [e for e in W(k) if e[0] == "NOTEOUT" and e[1][1] > 0]

    print("\n=== B. the run ===")
    check("the driver reached every window", len(order) >= 15,
          "saw %d marks: %s" % (len(order), " ".join(order)))

    # --- the map -----------------------------------------------------------
    print("\n--- the mode table ---")
    # ⛔ THE REGRESSION TEST FOR ITEM 234. mother pushes knobs.txt at BOOT, long
    # before any window here used to start, and the map has to be usable by then --
    # both the table AND the lookup key's mode. It was not, the instrument booted at
    # u_tempo's own 120 instead of the saved 57, and NOTHING reported it.
    early = [e for e in W("EARLY") if e[0] == "TEMPO"]
    check("⛔ a control moved at 300 ms ALREADY MAPS -- table and mode key ready at load",
          any(abs(float(e[1][0]) - 57) < 1.5 for e in early if e[1]),
          "tempo in that window: %s" % [e[1] for e in early])
    check("a mapped control reaches its destination",
          any(e[0] == "CTLOUT" and e[1][1] == 41 for e in W("VOLCA-CC")),
          repr(W("VOLCA-CC")))
    check("⛔ the SAME control in another mode does NOTHING (mode-dependence)",
          not midi("MODE-DEP"), repr(midi("MODE-DEP")))
    check("⛔ a row naming an unknown destination emits NO MIDI",
          not midi("BAD-DEST"), repr(midi("BAD-DEST")))
    check("⛔ ... and reports unknown-dest on err",
          any(e[0] == "ERR" and "unknown-dest" in " ".join(e[1]) for e in W("BAD-DEST")),
          repr(W("BAD-DEST")))

    # --- the Volca ---------------------------------------------------------
    print("\n--- m_volca ---")
    cc = [e for e in W("VOLCA-CC") if e[0] == "CTLOUT"]
    check("CC carries controller and channel", cc and cc[0][1][1:] == [41.0, 49.0],
          repr(cc))
    nt = ons("VOLCA-NOTE")
    check("a note reaches the Volca on channel 49", nt and nt[0][1][0] == 48 and nt[0][1][2] == 49,
          repr(nt))
    pg = [e for e in W("VOLCA-PROG") if e[0] == "PGMOUT"]
    check("⛔ pgmout gets arg+1, so the WIRE value is the number asked for (item 228)",
          pg and pg[0][1] == [6.0, 49.0], repr(pg))

    # --- the 404, transmit -------------------------------------------------
    print("\n--- m_404 transmit ---")
    want = [48, 49, 50, 51, 44, 45, 46, 47, 40, 41, 42, 43, 36, 37, 38, 39]
    got = [int(e[1][0]) for e in ons("PADS-A")]
    check("⛔ ALL SIXTEEN pads of bank A map to the right notes", got == want,
          "want %s got %s" % (want, got))
    if got != want and len(got) == len(want):
        bad = [i + 1 for i, (a, b) in enumerate(zip(got, want)) if a != b]
        note("pads wrong: %s -- if this is 5..16 only, it is the 47+n error" % bad)
    check("every bank-A pad went out on channel 33",
          all(e[1][2] == 33 for e in ons("PADS-A")), repr(ons("PADS-A")))
    c1 = ons("PADS-C")
    check("bank C pad 1 is note 48 on CHANNEL 35 (bank sets the channel)",
          c1 and c1[0][1][0] == 48 and c1[0][1][2] == 35, repr(c1))
    # channel-specific: an earlier window's Volca note-off (channel 49) lands in
    # this window too, 200 ms behind its own note-on
    offs = [e for e in W("PADS-A")
            if e[0] == "NOTEOUT" and e[1][1] == 0 and e[1][2] == 33]
    check("every bank-A note-on is matched by a note-off ON THE SAME CHANNEL",
          len(offs) == 16, "%d offs on channel 33" % len(offs))

    # --- the rate limit ----------------------------------------------------
    print("\n--- the rate limit ---")
    n = len(ons("BURST"))
    check("⛔ 20 triggers in ONE logical instant emit exactly 1 -- it DROPS, never queues",
          n == 1, "emitted %d" % n)
    # ⚠️ The burst above proves it drops rather than queues, and NOTHING MORE. It
    # cannot see a disarmed limiter: [del 0] still defers to the next scheduler
    # tick, so the gate stays shut for the whole logical instant either way. Two
    # triggers 2 ms apart straddle the 5 ms interval and can.
    pair = len(ons("PAIR"))
    check("⛔ two triggers 2 ms apart emit exactly 1 -- the INTERVAL is real",
          pair == 1, "emitted %d" % pair)

    # --- the 404, receive --------------------------------------------------
    print("\n--- m_404 receive (only t_notein can reach this) ---")
    p = [e for e in W("RX-B5") if e[0] == "PARAM"]
    d = [e for e in W("RX-B5") if e[0] == "DISP"]
    check("a pad press names its BANK and PAD", p and p[0][1] == ["sp-b5", "90"], repr(p))
    check("... and reports TWO stable disp rows, both FLOAT values",
          ["sp-bank", "2"] in [e[1] for e in d] and ["sp-pad", "5"] in [e[1] for e in d],
          repr(d))
    pr = [e for e in W("RX-RELEASE") if e[0] == "PARAM"]
    dr = [e for e in W("RX-RELEASE") if e[0] == "DISP"]
    check("a RELEASE reaches param", pr and pr[0][1] == ["sp-b5", "0"], repr(pr))
    check("... and does NOT reach disp",
          not [e for e in dr if e[1] and e[1][0] in ("sp-bank", "sp-pad")], repr(dr))
    pa = [e for e in W("RX-A1") if e[0] == "PARAM"]
    check("a different bank gives a different name", pa and pa[0][1] == ["sp-a1", "77"], repr(pa))
    da = [e for e in W("RX-A1") if e[0] == "DISP"]
    check("... and the BANK is now on the display too, not just on param",
          ["sp-bank", "1"] in [e[1] for e in da], repr(da))
    # only sp-* names are m_404's; other disp traffic in the window is unrelated
    check("⛔ a channel outside the 404's ten is IGNORED",
          not [e for e in W("RX-REJECT")
               if e[0] in ("PARAM", "DISP") and e[1] and e[1][0].startswith("sp-")],
          repr(W("RX-REJECT")))

    # --- panic -------------------------------------------------------------
    print("\n--- panic ---")
    ch = sorted(int(e[1][2]) for e in W("PANIC")
                if e[0] == "CTLOUT" and e[1][1] == 123)
    check("⛔ All Notes Off covers ALL TEN banks, not just bank A",
          ch == list(range(33, 43)), "channels %s" % ch)


def main():
    static_lint()
    cap = sys.stdin.read()
    if cap.strip():
        run_asserts(cap)
    else:
        check("a capture was supplied", False, "stdin was empty")
    print("\n%d checks failed" % fails)
    return fails


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
