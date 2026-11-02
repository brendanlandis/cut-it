#!/usr/bin/env python3
"""Reassembles Launchpad SysEx out of a capture. Imported, never run.

display-assert reads the lighting frames and launchpad-assert the mode frames,
interleaved in one byte stream.

⛔ Realtime bytes (>= 248) are skipped, not stored: they are legal inside a
SysEx stream and u_tempo sends 96 a second, so keeping them corrupts every frame.

Frame shape: 332 bytes = 7 header + 108 * 3 + terminator. Spec k holds type at
7+3k, LED index at 8+3k and color at 9+3k, so the color at LED index i is byte
9 + 3*(i-1). Indices run 1..108, the whole span the Launchpad can paint; index
0 (Setup) is outside it (the Launchpad's Reference page,
The Programmer Mode index map).
"""
import re

HEADER = [240, 0, 32, 41, 2, 14, 3]              # 03 command: batch LED color
MODE_SYSEX = [240, 0, 32, 41, 2, 14, 14]         # 0E command: Programmer / Live
TERM = 247
NSPEC = 108
FIRST_INDEX = 1
FRAME_LEN = len(HEADER) + NSPEC * 3 + 1          # 332

# read out of g_grid.pd rather than guessed. The mode lamps are the top six of
# the left column, mode 1 at the top: LAMPS[m - 1] is mode m's.
LAMPS = (80, 70, 60, 50, 40, 30)
BEAT_LO, BEAT_HI = 11, 18
DIM, LAMP_ON, BEAT_ON, ALERT_RED = 1, 21, 3, 5

MIDI_RE = re.compile(r"^MIDIOUT:\s+(-?\d+)\s+(-?\d+)\s*$")


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

    def color(self, index):
        return self.data[9 + 3 * (index - FIRST_INDEX)]

    def colors(self):
        return [self.data[9 + 3 * k] for k in range(NSPEC)]

    def indices(self):
        return [self.data[8 + 3 * k] for k in range(NSPEC)]

    def types(self):
        return [self.data[7 + 3 * k] for k in range(NSPEC)]


def parse(stream, tag):
    """-> [Frame], each tagged with the MARK that was current when it arrived.

    `tag` is the driver's print label -- MARK lines read "<tag>: MARK NAME", the
    same shape lib_assert.parse reads, so one driver builder serves every gate.
    """
    mark_re = re.compile(r"^%s:\s+MARK\s+(\S+)\s*$" % re.escape(tag))
    frames, mark, buf, collecting = [], "(none)", [], False
    for line in stream:
        m = mark_re.match(line.strip())
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


def home_shape(frame):
    """-> (problem_or_None, lit_lamp_index, lit_beat_index) for a HOME frame.

    Home is: everything dark, the six mode lamps dim with one lit, the eight beat
    cells dim with one lit. Anything else lit anywhere is the problem this
    returns, so an off-by-one that lights a ring button once a bar is caught
    though seven beats of eight look right.
    """
    lamp, beat, stray = None, None, []
    for k, color in enumerate(frame.colors()):
        idx = FIRST_INDEX + k
        if idx in LAMPS:
            if color == LAMP_ON:
                if lamp is not None:
                    return ("two mode lamps lit: %d and %d" % (lamp, idx)), lamp, beat
                lamp = idx
            elif color != DIM:
                return ("mode lamp %d is color %d" % (idx, color)), lamp, beat
        elif BEAT_LO <= idx <= BEAT_HI:
            if color == BEAT_ON:
                if beat is not None:
                    return ("two beat cells lit: %d and %d" % (beat, idx)), lamp, beat
                beat = idx
            elif color != DIM:
                return ("beat cell %d is color %d" % (idx, color)), lamp, beat
        elif color != 0:
            stray.append((idx, color))
    if stray:
        return ("lit outside every region: %s" % stray[:6]), lamp, beat
    return None, lamp, beat


# ---------------------------------------------------------------------------
# The drum page, mode 1. Which cell is which comes from the layout table that
# g_grid and u_map both read, never typed here; the colors are g_grid's.
DRUM_PAGE = "Cut It/cut-it-drum-page.txt"
PICKED = 9                      # the selected velocity button and pad
PLAYHEAD = 3                    # white, over whatever the step holds
STEP_RAMP = (11, 10, 9, 8)      # one hue, dark to bright, by velocity quarter


def drum_layout(path=DRUM_PAGE):
    """-> {grid index: (role, n)} from the layout table."""
    lay = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            f = line.split()
            if f:
                lay[int(f[0])] = (f[1], int(f[2]))
    return lay


def step_color(velocity):
    """The color a step at this velocity paints, off the playhead."""
    if velocity <= 0:
        return DIM
    return STEP_RAMP[(int(velocity) - 1) // 32]


def drum_page(frame, lay):
    """-> (problem_or_None, lit_lamp_index, page) for a mode-1 HOME frame.

    page is {"step": {n: color}, "vel": {n: color}, "pad": {n: color}}. The
    page is: the six mode lamps as home has them, every layout cell in a color
    its role can take, and everything else dark -- the beat row included, since
    it gives way here, and the bottom-right 4x4, which no row names.
    """
    allowed = {"step": {DIM, PLAYHEAD} | set(STEP_RAMP), "vel": {DIM, PICKED},
               "pad": {DIM, PICKED}}
    lamp, page, stray = None, {"step": {}, "vel": {}, "pad": {}}, []
    for k, color in enumerate(frame.colors()):
        idx = FIRST_INDEX + k
        if idx in LAMPS:
            if color == LAMP_ON:
                if lamp is not None:
                    return ("two mode lamps lit: %d and %d" % (lamp, idx)), lamp, page
                lamp = idx
            elif color != DIM:
                return ("mode lamp %d is color %d" % (idx, color)), lamp, page
        elif idx in lay:
            role, n = lay[idx]
            if color not in allowed[role]:
                return ("%s %d (index %d) is color %d" % (role, n, idx, color)), lamp, page
            page[role][n] = color
        elif color != 0:
            stray.append((idx, color))
    if stray:
        return ("lit outside the lamps and the page: %s" % stray[:6]), lamp, page
    for role, many in (("vel", "velocity buttons"), ("pad", "pads")):
        lit = [n for n, c in page[role].items() if c == PICKED]
        if len(lit) > 1:
            return ("%d %s lit: %s" % (len(lit), many, sorted(lit))), lamp, page
    heads = [n for n, c in page["step"].items() if c == PLAYHEAD]
    if len(heads) > 1:
        return ("%d playheads: steps %s" % (len(heads), sorted(heads))), lamp, page
    return None, lamp, page
