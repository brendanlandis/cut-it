#!/usr/bin/env python3
"""The OLED's analyzer -- ref/module/display.md. Reads a capture on stdin.

It asserts on what the screen was told, not on how it looks: legibility and the
meters are the display checklist's (test/checklists/display.md).

The message, read off a real capture:

    sendtyped /oled/gPrintln iiiiis 3 2 12 24 1 43
                             ^tag   ^s ^x ^y ^sz ^col ^words...

A frame is everything between two gFlips. Pick the frame with care: a layer
raised in a window appears only at the next repaint, so the first frame still
shows what came before, and a TTL shorter than the window has expired by the
last.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_assert as A                                         # noqa: E402

# The number of windows oled-assert-drive-gen.py's SEQ opens.
MARKS = 25

# The five rows the store holds, in the order they are first touched.
FIVE = ["gate-a", "gate-b", "gate-c", "gate-d", "gate-e"]

# Every source that publishes `expect`, exactly: a layer missing here is
# invisible on the diag screen, and m_404's line went with the SP-404
# (2026-11-04). Six since m_nanokey registered, passive (2026-11-04), the six
# rows the layer holds. presence-assert.sh asserts the same six.
DIAG_SOURCES = ["m_launchpad", "m_nano", "m_organelle", "m_volca", "m_streich", "m_nanokey"]

# The two passive layers: never polled, so `never` until they first speak.
PASSIVE = ["m_organelle", "m_nanokey"]

# The three that are POLLED, and therefore the three a `lost` can name.
ACTIVE = ["m_launchpad", "m_nano", "m_streich"]

# The alert layer's border, read off g_oled.pd rather than guessed.
BORDER = ["sendtyped", "/oled/gBox", "iiiiii", "3", "0", "0", "127", "63", "1"]

_FLIP = ["sendtyped", "/oled/gFlip"]


def run_asserts(cap):
    order, by = A.windows(cap, "OLED", MARKS)
    W = lambda k: by.get(k, [])

    def frames(mark):
        """Complete frames in the window -- gFlip closes one. The leading
        partial belongs to a repaint begun before the mark, so it is dropped."""
        out, cur, started = [], [], False
        for lab, v in W(mark):
            if lab != "OLED":
                continue
            if v[:2] == _FLIP:
                if started:
                    out.append(cur)
                started, cur = True, []
            else:
                cur.append(v)
        return out

    def rows(frame):
        """-> [(y, size, [words])] for every gPrintln, top of the screen first."""
        out = []
        for v in frame:
            if v[:2] != ["sendtyped", "/oled/gPrintln"] or len(v) < 9:
                continue
            try:
                out.append((int(v[5]), int(v[6]), v[8:]))
            except ValueError:
                continue
        return sorted(out)

    def words(frame):
        return [w for _, _, ws in rows(frame) for w in ws]

    def last(mark):
        fs = frames(mark)
        return fs[-1] if fs else []

    def first(mark):
        fs = frames(mark)
        return fs[0] if fs else []

    def live(mark):
        """Every window's own liveness witness: the screen repainted at all."""
        return A.check("%s: the screen repainted" % mark, bool(frames(mark)),
                       "no complete frame in the window -- the 10 Hz clock is "
                       "the only thing that draws, so silence here means the run "
                       "died rather than that the layer was empty")

    # ---- home, which is never cleared and has no TTL ----------------------
    print("--- home ---")
    if live("HOME"):
        # The readouts name what u_level reads, Cut It's output (2026-11-04).
        heads = [ws[0] for y, sz, ws in rows(last("HOME")) if sz == 8 and ws and y < 50]
        A.check("⛔ the meters' readouts are out-l and out-r, top to bottom",
                heads == ["out-l", "out-r"],
                "the 8px readouts drew %s. in-l and in-r were the input's" % heads)
        # Home is the meters and nothing else: the OLED is for alerts, the
        # output's levels and a moving control's name (Brendan, 2026-11-04).
        A.check("⛔ home draws the two readouts, at y=0 and y=32, and no other text",
                [(y, sz, ws[:1]) for y, sz, ws in rows(last("HOME"))]
                == [(0, 8, ["out-l"]), (32, 8, ["out-r"])],
                "drew %s. A third line is a footer, which went with the tempo at rest"
                % rows(last("HOME")))
        A.check("⛔ no tempo at rest: 140 on the tempo bus draws nothing",
                not [w for w in words(last("HOME")) if "140" in w],
                "drew %s. The tempo is the phone's to show" % words(last("HOME")))
        fills = sorted((int(v[5]), int(v[7])) for v in last("HOME")
                       if v[:2] == ["sendtyped", "/oled/gFillArea"] and len(v) >= 9)
        A.check("...and its two bars are 18 px tall at y=10 and y=42, under them",
                fills == [(10, 18), (42, 18)], "gFillArea (y, height): %s" % fills)
        # The gate marks were a gBox each under the meters: the input's noise
        # floor and a gate window, which an output meter has neither of.
        boxes = [v for v in last("HOME") if v[:2] == ["sendtyped", "/oled/gBox"]]
        A.check("⛔ no gate marks: home draws no gBox at all",
                not boxes, "drew %s" % boxes)

    # ---- a parameter, and its 1200 ms TTL ---------------------------------
    print("\n--- the param layer, and its TTL ---")
    # One mover is a two-line layout, not a row, so the geometry is asserted.
    if live("PARAM"):
        A.check("a lone parameter draws name 8px at y=0 and value 24px at y=12",
                rows(last("PARAM")) == [(0, 8, ["gate-p1"]), (12, 24, ["11"])],
                "drew %s" % rows(last("PARAM")))
    if live("PARAM-GONE"):
        A.check("⛔ ...and 1.2 s after the hands stop, it is gone",
                "gate-p1" not in words(last("PARAM-GONE")),
                "still drawing %s. The TTL is one retriggered [delay], so a "
                "parameter that never expires means the screen keeps a stale "
                "value under a moving control" % words(last("PARAM-GONE")))
        A.check("...and the home layer is showing again",
                "out-l" in words(last("PARAM-GONE")),
                "drew %s -- home is priority 0 and is never cleared, so it must "
                "be what is left" % words(last("PARAM-GONE")))

    # The store ages separately from the layer flag (13 frames against
    # 1200 ms), so a broken aging redraws the old row beside the new one.
    if live("PARAM-AGAIN"):
        drawn = words(last("PARAM-AGAIN"))
        A.check("a new parameter draws", "gate-p2" in drawn, "drew %s" % drawn)
        A.check("⛔ ...and the expired one does NOT come back with it",
                "gate-p1" not in drawn,
                "drew %s -- the store aged the layer out but kept the row" % drawn)
    if live("PARAM-AGED"):
        A.check("and it ages out of the STORE too, not only off the screen",
                not [w for w in ("gate-p1", "gate-p2")
                     if w in words(last("PARAM-AGED"))],
                "drew %s" % words(last("PARAM-AGED")))

    # ---- five rows, and the sixth that is refused -------------------------
    print("\n--- the store holds five, and refuses a sixth ---")
    if live("FIVE"):
        got = [ws[0] for _, _, ws in rows(last("FIVE")) if ws]
        A.check("five controls moving at once give five rows, in touch order",
                got == FIVE, "drew %s" % got)
        # The meter strip starts at y=54: a drifted pitch overlaps it, silently.
        A.check("...at 8px, on the y=0 9 18 27 36 pitch, clear of the meters",
                [(y, sz) for y, sz, _ in rows(last("FIVE"))]
                == [(0, 8), (9, 8), (18, 8), (27, 8), (36, 8)],
                "drew %s" % [(y, sz) for y, sz, _ in rows(last("FIVE"))])
    if live("SIXTH"):
        got = [ws[0] for _, _, ws in rows(last("SIXTH")) if ws]
        A.check("⛔ a SIXTH is refused, and the five keep their rows",
                got == FIVE,
                "drew %s. The sixth must wait for a row to free up rather than "
                "push one out -- with 18 continuous controls, moving two faders "
                "together is ordinary use" % got)

    # Rows are stable: a re-touched control must not jump to the bottom.
    if live("IN-PLACE"):
        drawn = [ws for _, _, ws in rows(last("IN-PLACE"))]
        got = [ws[0] for ws in drawn if ws]
        A.check("⛔ re-touching all five in REVERSE order changes no row's place",
                got == FIVE,
                "drew %s. Driven e,d,c,b,a, a store that reordered on update "
                "would answer e,d,c,b,a -- so this is the one arrangement where "
                "the right answer and the wrong one cannot be confused" % got)
        A.check("...and every value did change",
                drawn == [["gate-a", "99"], ["gate-b", "22"], ["gate-c", "33"],
                          ["gate-d", "44"], ["gate-e", "55"]],
                "drew %s" % drawn)

    # ---- modal outranks param ---------------------------------------------
    print("\n--- layer priority: modal over param ---")
    if live("MODAL"):
        A.check("a modal claims the screen",
                "gate-modal" in words(last("MODAL")),
                "drew %s" % words(last("MODAL")))
    if live("MODAL-PARAM"):
        drawn = words(last("MODAL-PARAM"))
        A.check("⛔ a parameter moving UNDER a modal does not reach the screen",
                "gate-p9" not in drawn and "gate-modal" in drawn,
                "drew %s. Priority is a [select 1] cascade, so it reads top to "
                "bottom in exactly priority order" % drawn)

    # ---- alert outranks modal, and hands it back --------------------------
    # The window outlasts the 2 s warn: its first frame and its last.
    print("\n--- layer priority: alert over modal, and the TTL ---")
    if live("ALERT"):
        drawn = words(first("ALERT"))
        A.check("an alert outranks the modal",
                "gate-alert" in drawn and "gate-modal" not in drawn,
                "drew %s" % drawn)
        A.check("...with its level and its source, not just the text",
                "warn" in drawn and "u_gate" in drawn, "drew %s" % drawn)
        A.check("...and a border around the whole screen",
                BORDER in first("ALERT"),
                "no %s in the frame" % " ".join(BORDER[1:2] + BORDER[3:]))
        A.check("⛔ a warn expires inside its own 2 s and gives the modal back",
                "gate-modal" in words(last("ALERT")),
                "the last frame of a 3 s window drew %s -- the TTL never fired "
                "and an alert would cover the screen forever" % words(last("ALERT")))
    if live("ALERT-GONE"):
        A.check("...and stays given back",
                "gate-modal" in words(last("ALERT-GONE"))
                and "gate-alert" not in words(last("ALERT-GONE")),
                "drew %s" % words(last("ALERT-GONE")))

    # Without these, a g_oled using 2 s for both levels would pass.
    print("\n--- and a fail lasts twice as long ---")
    if live("FAIL"):
        A.check("a fail claims the screen too",
                "gate-fail" in words(first("FAIL")),
                "drew %s" % words(first("FAIL")))
    if live("FAIL-STILL"):
        A.check("⛔ still up 2.5 s later -- where a warn would already be gone",
                "gate-fail" in words(first("FAIL-STILL")),
                "drew %s. warn is 2 s and fail is 4 s; one value for both means "
                "the errors that matter most are the ones you get least time to "
                "read" % words(first("FAIL-STILL")))
    if live("FAIL-GONE"):
        A.check("...and gone by 4.8 s",
                "gate-fail" not in words(last("FAIL-GONE")),
                "drew %s" % words(last("FAIL-GONE")))

    # ---- modal-off ---------------------------------------------------------
    print("\n--- modal-off, and the two reserved selectors ---")
    if live("MODAL-OFF"):
        drawn = words(last("MODAL-OFF"))
        A.check("modal-off clears the modal and home comes back",
                "gate-modal" not in drawn and "out-l" in drawn,
                "drew %s" % drawn)

    # led and grid are routed and thrown away: anything g_oled does not
    # recognize is a parameter, so without them on the route an LED request
    # would draw as a parameter row.
    if live("RESERVED"):
        drawn = words(last("RESERVED"))
        strays = [w for w in ("led", "running", "grid", "45") if w in drawn]
        A.check("⛔ `led` and `grid` never draw as parameters",
                not strays,
                "drew %s. They belong to g_led and g_grid; g_oled matches them "
                "only to discard them" % strays)
        A.check("...and the screen is still live while ignoring them",
                "out-l" in drawn,
                "drew %s -- without this, ignoring them is indistinguishable "
                "from a dead screen" % drawn)

    # ---- the diag layer ----------------------------------------------------
    # On a Mac every device is absent: by 26 s the three active layers have been
    # declared lost without ever answering, so the roster is three `never`, one
    # `unchecked`, and m_organelle silent until something moves.
    print("\n--- the diag layer, and the roster it draws ---")

    def state(mark, which=last):
        """-> {source: word} off the drawn rows, ignoring anything else."""
        return {ws[0]: ws[1] for _, _, ws in rows(which(mark))
                if len(ws) == 2 and ws[0] in DIAG_SOURCES}

    # Every row shaped like a roster line, known source or not: filtered to
    # DIAG_SOURCES, a fifth line (m_404's, put back) drew unseen and passed.
    WORDS = ("here", "gone", "never", "unchecked")
    roster = lambda mark: [(y, sz, ws[0]) for y, sz, ws in rows(last(mark))
                           if len(ws) == 2 and ws[1] in WORDS]

    if live("DIAG"):
        A.check("the diag layer draws one row per registered source, and no other",
                sorted(s for _, _, s in roster("DIAG")) == sorted(DIAG_SOURCES),
                "drew %s -- the roster is whatever `expect` published at load, "
                "and every m_ layer publishes exactly one" % roster("DIAG"))
        # The five-row store's pitch, one row further: the sixth ends at y=52.
        A.check("⛔ ...at 8px on the y=0 9 18 27 36 45 pitch, SIX rows",
                [(y, sz) for y, sz, _ in roster("DIAG")]
                == [(0, 8), (9, 8), (18, 8), (27, 8), (36, 8), (45, 8)],
                "drew %s" % [(y, sz) for y, sz, _ in rows(last("DIAG"))])
        # The strip went down to make room: two 4 px bars from y=54, clear of
        # the sixth row's last line at 52, where a 5 px strip at 48 sat on it.
        strip = sorted((int(v[5]), int(v[7])) for v in last("DIAG")
                       if v[:2] == ["sendtyped", "/oled/gFillArea"] and len(v) >= 9)
        A.check("⛔ ...with the meter strip below the sixth, 4 px at y=54 and y=59",
                strip == [(54, 4), (59, 4)], "gFillArea (y, height): %s" % strip)
        A.check("...and the two passive layers, never polled, read `never` until they speak",
                [state("DIAG").get(s) for s in PASSIVE] == ["never", "never"],
                "drew %s" % state("DIAG"))
        A.check("⛔ a device that has never answered reads `never`, not `gone`",
                [state("DIAG").get(s) for s in ACTIVE] == ["never"] * len(ACTIVE),
                "drew %s. c_presence publishes `lost` UNARMED because that is "
                "what drives the re-wire, so on the bus an absent device and a "
                "vanished one are identical -- telling them apart is the whole "
                "point of this screen" % state("DIAG"))
        A.check("...and a device nothing can ever check reads `unchecked`",
                state("DIAG").get("m_volca") == "unchecked",
                "drew %s. m_volca registers `none`: it is never polled and can "
                "never be lost, so drawing it as healthy would be a claim "
                "nothing has ever tested" % state("DIAG"))

    if live("DIAG-SEEN"):
        A.check("`seen` moves an active source to `here`",
                state("DIAG-SEEN").get("m_nano") == "here",
                "drew %s" % state("DIAG-SEEN"))
        A.check("⛔ ...and so does the PASSIVE layer's own `seen`, off one knob",
                state("DIAG-SEEN").get("m_organelle") == "here",
                "drew %s. m_organelle publishes `seen` on the bus rather than "
                "through a c_presence, and this is the only consumer it has" %
                state("DIAG-SEEN"))
        A.check("⛔ ...and the nanoKEY's own `seen`, off one key on its channel block",
                state("DIAG-SEEN").get("m_nanokey") == "here",
                "drew %s. m_nanokey is passive: it is never polled, since its identity "
                "reply carries the nanoKONTROL's byte, so a key is all that says it is "
                "there" % state("DIAG-SEEN"))
        A.check("...and no other row moved with it",
                [state("DIAG-SEEN").get(s) for s in ("m_launchpad", "m_volca", "m_streich")]
                == ["never", "unchecked", "never"],
                "drew %s" % state("DIAG-SEEN"))

    if live("DIAG-GONE"):
        A.check("`lost` on a source that HAS answered moves it to `gone`",
                state("DIAG-GONE").get("m_nano") == "gone",
                "drew %s" % state("DIAG-GONE"))

    # The only check here a layer that always wrote `gone` would fail.
    if live("DIAG-NEVER"):
        got = state("DIAG-NEVER")
        A.check("⛔ `lost` on a source that never answered leaves it `never`",
                got.get("m_launchpad") == "never",
                "drew %s. Both `lost` messages are byte-identical on the bus; "
                "only the row's own history tells them apart" % got)
        A.check("...and the row that really did go missing is still `gone`",
                got.get("m_nano") == "gone",
                "drew %s -- if the write had landed on the wrong row this is "
                "where it would show" % got)

    print("\n--- and an alert covers the diagnostic ---")
    if live("DIAG-ALERT"):
        drawn = words(first("DIAG-ALERT"))
        A.check("⛔ an alert covers the diag layer completely",
                "gate-diagx" in drawn and not [s for s in DIAG_SOURCES
                                               if s in drawn],
                "drew %s. A diagnostic that hides an alert is worse than no "
                "diagnostic, and a layer that always wins passes every "
                "positive test above" % drawn)
    if live("DIAG-BACK"):
        A.check("...and the diag layer is still there underneath when it clears",
                sorted(state("DIAG-BACK", first)) == sorted(DIAG_SOURCES),
                "drew %s. The alert's TTL fired at 2 s and diag's own 8 s is "
                "still running, so the screen must come back to the roster "
                "rather than to home" % words(first("DIAG-BACK")))
    # Home is recognized by its meters' readouts.
    if live("DIAG-TTL"):
        drawn = words(last("DIAG-TTL"))
        A.check("...and diag expires on its own TTL and gives home back",
                not [s for s in DIAG_SOURCES if s in drawn]
                and "out-l" in drawn and "out-r" in drawn,
                "drew %s. It is a summoned readout on a retriggered [delay], "
                "not a modal: nothing clears it explicitly" % drawn)

    A.note("windows reached: %s" % " ".join(order))


if __name__ == "__main__":
    run_asserts(A.require_capture(sys.stdin.read()))
    sys.exit(1 if A.report() else 0)
