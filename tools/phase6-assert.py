#!/usr/bin/env python3
"""Reads a phase6-assert run off stdin and asserts on what the patch ACTUALLY
emitted. Driven by tools/phase6-assert.sh; not much use on its own.

WHAT THIS IS FOR. Everything else that tests the grid is an eyeball check, and
phase6-bench.pd used to say so in its own header: "there is no way to read back
what the LEDs are actually showing". That was too strong. Pd cannot ask the
Launchpad what is lit -- but the bytes the patch SENDS are completely knowable,
and that is the level a test of our code should work at anyway. Rewriting
[midiout] to [t_midiout] in a scratch copy puts every one of them on stdout.

This is the layer that would have caught the one-based beat bug in a single run.
The bug lit index 19 -- a right-column ring button -- and blanked the beat row
once a bar, and SEVEN BEATS OUT OF EIGHT LOOKED PERFECT.

FRAME SHAPE: 332 bytes = 7 header + 108 * 3 + terminator. Spec k holds type at
7+3k, LED index at 8+3k and colour at 9+3k, so the colour at LED index i is byte
9 + 3*(i-1). Indices run 1..108.

THAT SPAN WIDENED FROM 10..108 AND THE OLD REASON WAS MEASURED FALSE. It stopped
at 10 on the belief that ~106 specs approached a documented cliff and that 120
was REJECTED OUTRIGHT -- a whole message dropped, which on a frame clock reads as
a frozen grid. Three broken probes produced that; a clean 120-spec message paints
the whole surface (item 105, 109). The reason to cover the span is that
an index OUTSIDE it can never be cleared: LED state survives the Programmer Mode
switch, so whatever Live Mode drew on CC 1-8 persisted into every session.

Index 0 -- Setup -- stays out, and that one IS measured: a valid one-spec frame
addressing it lights nothing and the button transmits nothing (item 110).

COLOURS, read out of g_grid.pd rather than guessed:
    home    fill 0 (dark)
            mode lamps  index 91..96, dim 1, the live one 21
            beat row    index 11..18, dim 1, the live one 3
    modal   every spec the requested palette
    alert   every spec 5 (red)
"""
import re
import sys

HEADER = [240, 0, 32, 41, 2, 14, 3]
TERM = 247
NSPEC = 108
FIRST_INDEX = 1
FRAME_LEN = len(HEADER) + NSPEC * 3 + 1          # 332

LAMP_LO, LAMP_HI = 91, 96
BEAT_LO, BEAT_HI = 11, 18
DIM, LAMP_ON, BEAT_ON, ALERT_RED = 1, 21, 3, 5

MODE_SYSEX = [240, 0, 32, 41, 2, 14, 14]         # 0E command: Programmer / Live

MIDI_RE = re.compile(r"^MIDIOUT:\s+(-?\d+)\s+(-?\d+)\s*$")
MARK_RE = re.compile(r"^MARK:\s+(\S+)\s*$")


class Frame(object):
    def __init__(self, data, mark):
        self.data = data
        self.mark = mark

    @property
    def is_lighting(self):
        return self.data[:7] == HEADER

    @property
    def is_mode(self):
        return self.data[:7] == MODE_SYSEX

    def colour(self, index):
        return self.data[9 + 3 * (index - FIRST_INDEX)]

    def colours(self):
        return [self.data[9 + 3 * k] for k in range(NSPEC)]

    def indices(self):
        return [self.data[8 + 3 * k] for k in range(NSPEC)]

    def types(self):
        return [self.data[7 + 3 * k] for k in range(NSPEC)]


def parse(stream):
    """Reassemble SysEx frames. Realtime bytes (>=248) are skipped rather than
    stored: they are legal inside a SysEx stream and u_tempo emits 96 a second."""
    frames, mark, buf, collecting = [], "(none)", [], False
    for line in stream:
        m = MARK_RE.match(line.strip())
        if m:
            mark = m.group(1)
            continue
        m = MIDI_RE.match(line.strip())
        if not m:
            continue
        byte = int(m.group(1))
        if byte == 240:
            buf, collecting = [240], True
            continue
        if not collecting or byte >= 248:
            continue
        buf.append(byte)
        if byte == TERM:
            frames.append(Frame(buf, mark))
            buf, collecting = [], False
    return frames


class Report(object):
    def __init__(self):
        self.rows = []
        self.notes = []

    def check(self, name, ok, detail=""):
        self.rows.append((bool(ok), name, detail))
        return ok

    def note(self, name, detail):
        """Something true and worth saying that is NOT a regression. A gate that
        cries wolf gets ignored, and a gate that hides a finding is worse."""
        self.notes.append((name, detail))

    def dump(self):
        for ok, name, detail in self.rows:
            print("%-5s %s%s" % ("PASS" if ok else "FAIL", name,
                                 "" if ok else "   <- " + detail))
        for name, detail in self.notes:
            print("%-5s %s   <- %s" % ("NOTE", name, detail))
        bad = sum(1 for ok, _, _ in self.rows if not ok)
        print()
        print("%d checks, %d failed, %d note(s)"
              % (len(self.rows), bad, len(self.notes)))
        return bad


def home_shape(frame):
    """Returns (problem_or_None, lamp_index, beat_index)."""
    lamp, beat, stray = None, None, []
    for k, colour in enumerate(frame.colours()):
        idx = FIRST_INDEX + k
        if LAMP_LO <= idx <= LAMP_HI:
            if colour == LAMP_ON:
                if lamp is not None:
                    return ("two mode lamps lit: %d and %d" % (lamp, idx)), lamp, beat
                lamp = idx
            elif colour != DIM:
                return ("mode lamp %d is colour %d" % (idx, colour)), lamp, beat
        elif BEAT_LO <= idx <= BEAT_HI:
            if colour == BEAT_ON:
                if beat is not None:
                    return ("two beat cells lit: %d and %d" % (beat, idx)), lamp, beat
                beat = idx
            elif colour != DIM:
                return ("beat cell %d is colour %d" % (idx, colour)), lamp, beat
        elif colour != 0:
            stray.append((idx, colour))
    if stray:
        return ("lit outside every region: %s" % stray[:6]), lamp, beat
    return None, lamp, beat


def main():
    frames = parse(sys.stdin)
    r = Report()

    lighting = [f for f in frames if f.is_lighting]
    mode = [f for f in frames if f.is_mode]
    r.check("the run produced lighting frames at all", lighting,
            "no frame ever reached [midiout] -- is the scratch copy rewritten?")
    if not lighting:
        return r.dump()

    # ---- structure, on every lighting frame ------------------------------
    bad_len = [len(f.data) for f in lighting if len(f.data) != FRAME_LEN]
    r.check("every frame is %d bytes" % FRAME_LEN, not bad_len,
            "saw lengths %s" % sorted(set(bad_len))[:5])
    r.check("every frame ends with %d" % TERM,
            all(f.data[-1] == TERM for f in lighting), "a frame was not terminated")
    ok_len = [f for f in lighting if len(f.data) == FRAME_LEN]
    r.check("every spec is a static type byte 0",
            all(set(f.types()) == {0} for f in ok_len), "a spec had a non-zero type")
    want = list(range(FIRST_INDEX, FIRST_INDEX + NSPEC))
    r.check("every frame spans LED index %d..%d" % (want[0], want[-1]),
            all(f.indices() == want for f in ok_len),
            "the painted span moved -- CC 1-8 must stay outside it")

    by = {}
    for f in ok_len:
        by.setdefault(f.mark, []).append(f)

    def window(name):
        return by.get(name, [])

    # ---- the dirty flag really does gate the repaint ----------------------
    # This window runs BEFORE "; pd dsp 1", so nothing is driving the beat row and
    # a correctly gated grid has nothing to redraw. It is the only assertion here
    # that tests the dirty flag rather than the arbiter.
    idle = window("idle-dsp-off")
    r.check("DSP off and idle: the grid stops repainting", not idle,
            "%d frames with no clock running -- the dirty flag is not gating"
            % len(idle))

    # ---- the boot frame, before any beat has arrived ----------------------
    boot = [f for f in ok_len if f.mark == "(none)"]
    if boot:
        problem, _lamp, _beat = home_shape(boot[0])
        if problem:
            r.note("the FIRST frame lights a cell outside every region",
                   "%s -- g_grid's beat store starts at 0 and 0+10 is LED index "
                   "10, a left-column ring button. Cosmetic and Mac-only: on the "
                   "device mother enables DSP at 200 ms so beats are already "
                   "flowing by the time ownership rises at ~3 s. Tracked in "
                   "plan-v04.md" % problem)

    # ---- home, and the mode lamp ------------------------------------------
    for mark, expect_lamp in (("home-mode-1", 91), ("home-mode-4", 94),
                              ("home-again", 94)):
        fs = window(mark)
        if not r.check("%s: the grid repainted" % mark, fs, "no frame in the window"):
            continue
        problem, lamp, _beat = home_shape(fs[-1])
        r.check("%s: nothing lit outside the lamp row and the beat row" % mark,
                problem is None, problem or "")
        r.check("%s: the lit mode lamp is index %d" % (mark, expect_lamp),
                lamp == expect_lamp, "lit lamp was %s" % lamp)

    # ---- modal claims the whole surface -----------------------------------
    fs = window("modal-45")
    if r.check("modal-45: the grid repainted", fs, "no frame in the window"):
        r.check("modal-45: all %d specs are palette 45" % NSPEC,
                set(fs[-1].colours()) == {45},
                "colours present: %s" % sorted(set(fs[-1].colours()))[:6])

    # ---- a warn must never reach the grid ---------------------------------
    fs = window("warn-ignored")
    r.check("a warn changes nothing -- the modal is still up",
            all(set(f.colours()) == {45} for f in fs) if fs else True,
            "a warn repainted the surface")

    # ---- alert outranks the modal, then gives it back ---------------------
    # The alert TTL is 2 s and this window is longer, so the LAST frame in it has
    # already expired back to the modal. Assert on the FIRST frame after the mark.
    fs = window("alert-red")
    if r.check("alert-red: the grid repainted", fs, "no frame in the window"):
        r.check("alert-red: all %d specs are red (%d)" % (NSPEC, ALERT_RED),
                set(fs[0].colours()) == {ALERT_RED},
                "colours present: %s" % sorted(set(fs[0].colours()))[:6])
        r.check("alert-red: the alert expires inside its own window",
                set(fs[-1].colours()) != {ALERT_RED},
                "still red at the end of the window -- the TTL never fired")
    fs = window("alert-expired")
    if r.check("alert-expired: the grid repainted", fs,
               "NO FRAME AFTER THE ALERT TTL -- the grid would stay red forever"):
        r.check("alert-expired: the surface returns to the MODAL underneath",
                set(fs[-1].colours()) == {45},
                "expected 45 everywhere, got %s"
                % sorted(set(fs[-1].colours()))[:6])

    # ---- the beat row, which is where the one-based bug lived -------------
    fs = window("beat-row")
    if r.check("beat-row: the grid repainted", fs,
               "no frames -- is DSP on? the beat row hangs off threshold~"):
        seen, strays = set(), []
        for f in fs:
            problem, _lamp, beat = home_shape(f)
            if problem:
                strays.append(problem)
            if beat is not None:
                seen.add(beat)
        r.check("beat-row: the lit cell never leaves index %d..%d"
                % (BEAT_LO, BEAT_HI), not strays, strays[0] if strays else "")
        r.check("beat-row: the beat walks -- at least 4 of the 8 cells were lit",
                len(seen) >= 4, "only saw %s" % sorted(seen))

    # ---- panic hands the surface back -------------------------------------
    fs = window("after-panic")
    r.check("after a panic the grid paints nothing at all", not fs,
            "%d frames after ownership was dropped" % len(fs))

    # ---- m_launchpad's own SysEx ------------------------------------------
    prog = [f for f in mode if f.data[7:8] == [1]]
    live = [f for f in mode if f.data[7:8] == [0]]
    r.check("m_launchpad enters Programmer Mode at boot", prog,
            "no F0 .. 0E 01 F7 was ever sent")
    r.check("m_launchpad returns to Live Mode on panic", live,
            "NO F0 .. 0E 00 F7 -- this is the one that costs a power cycle")

    return r.dump()


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
