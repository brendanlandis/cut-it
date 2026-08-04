# Generates tools/phase6-assert-drive.pd -- the timed driver for the headless
# assertion run. It prints a MARK before each window so phase6-assert.py knows
# what the frames in that window are supposed to look like.
#
# Every delay hangs off the ONE loadbang with an absolute time. Chaining them
# would make each wait the SUM of everything before it, which is the kind of
# arithmetic that silently drifts as steps are added.
B, C = [], []


def obj(x, y, s):
    B.append("#X obj %d %d %s;" % (x, y, s))
    return len(B) - 1


def msg(x, y, s):
    B.append("#X msg %d %d %s;" % (x, y, s))
    return len(B) - 1


def txt(x, y, s, f=90):
    B.append("#X text %d %d %s, f %d;" % (x, y, s, f))
    return len(B) - 1


def con(a, ao, b, bi):
    C.append("#X connect %d %d %d %d;" % (a, ao, b, bi))


txt(20, 20,
    "phase6-assert-drive -- the driver half of the headless assertion run. It "
    "touches nothing in the deployed patch: it pushes onto mode \\, disp \\, err \\, "
    "tempo \\, start and panic exactly as a controller would \\, and prints a MARK "
    "before each window so tools/phase6-assert.py knows what the frames arriving "
    "in that window are supposed to look like.", 110)
txt(20, 150,
    "RUN IT THROUGH tools/phase6-assert.sh \\, never by hand -- the whole point is "
    "that [midiout] has been rewritten to [t_midiout] in a scratch copy first \\, so "
    "every byte the patch emits reaches stdout. Run it against the real Cut It and "
    "the frames are invisible and every assertion passes vacuously.", 110)
txt(20, 280,
    "DSP IS OFF FOR THE FIRST WINDOW ON PURPOSE. With no clock the grid has nothing "
    "to redraw \\, so that window is what proves the dirty flag really does gate the "
    "repaint: the boot frame \\, and then silence. Everything after it needs DSP \\, "
    "because the beat row hangs off threshold~.", 110)

mark_r = obj(2600, 60, "r \\$0-mark")
mark_p = obj(2600, 120, "print MARK")
con(mark_r, 0, mark_p, 0)

# (absolute_ms, mark, [(message, bus_or_None), ...])
SEQ = [
    (4000,  "idle-dsp-off",  []),
    (8000,  "dsp-on",        [("\\; pd dsp 1", None)]),
    (8600,  "settling",      [("120", "tempo"), ("compose mode-1", "mode")]),
    (11000, "home-mode-1",   []),
    (14000, "home-mode-4",   [("perform mode-4", "mode")]),
    (17000, "modal-45",      [("grid modal 45", "disp")]),
    (20000, "warn-ignored",  [("warn u_bench quiet", "err")]),
    (23000, "alert-red",     [("fail u_bench boom", "err")]),
    (25500, "alert-expired", []),
    (28000, "home-again",    [("grid modal-off", "disp")]),
    (31000, "beat-row",      [("bang", "start")]),
    (38000, "after-panic",   [("bang", "panic")]),
    (42000, "done",          []),
]

lb = obj(20, 380, "loadbang")
# one column per window: the delays sit in a ROW so the loadbang's fan-out never
# has to be drawn through them, and each window's boxes hang below its own delay
PITCH, IX, IY = 1400, 400, 110
for i, (when, mark, actions) in enumerate(SEQ):
    x = 220 + i * PITCH
    d = obj(x, 460, "del %d" % when)
    con(lb, 0, d, 0)
    items = ([("MARK", mark)] if mark else []) + [("BUS", a) for a in actions]
    tr = obj(x, 540, "t " + " ".join(["b"] * len(items)))
    con(d, 0, tr, 0)
    # outlets fire right to left, so the MARK is on the highest outlet and prints
    # before anything it describes happens
    for j, (kind, payload) in enumerate(items):
        outlet = len(items) - 1 - j
        bx, by = x + j * IX, 630 + j * IY
        if kind == "MARK":
            mm = msg(bx, by, payload)
            ms = obj(bx, by + 50, "s \\$0-mark")
            con(tr, outlet, mm, 0)
            con(mm, 0, ms, 0)
        else:
            m, bus = payload
            am = msg(bx, by, m)
            con(tr, outlet, am, 0)
            if bus:
                asnd = obj(bx, by + 50, "s %s" % bus)
                con(am, 0, asnd, 0)

y = 630 + 4 * IY + 200
qd = obj(20, 460, "del 43000")
qm = msg(20, 540, "\\; pd quit")
con(lb, 0, qd, 0)
con(qd, 0, qm, 0)

open("tools/phase6-assert-drive.pd", "w").write(
    "#N canvas 20 20 %d %d 12;\n" % (220 + len(SEQ) * PITCH + 400, y + 250) + "\n".join(B + C) + "\n")
print("boxes", len(B), "connects", len(C))
