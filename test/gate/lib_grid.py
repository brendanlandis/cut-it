#!/usr/bin/env python3
"""Reassembles Launchpad SysEx out of a capture. Imported, never run.

display-assert reads the lighting frames and launchpad-assert the mode frames,
interleaved in one byte stream.

⛔ Realtime bytes (>= 248) are skipped, not stored: they are legal inside a
SysEx stream and u_tempo sends 96 a second, so keeping them corrupts every frame.

Frame shape: 7 header bytes, 108 specs, then the terminator. A spec is type 0,
the LED index and a palette color (3 bytes), or type 3, the index and red, green
and blue (5 bytes), so an all-palette frame is 332 bytes and each RGB cell adds
two. A palette color reads as an int and an RGB one as an (r, g, b) tuple.
Indices run 1..108, the whole span the Launchpad can paint; index 0 (Setup) is
outside it (the Launchpad's Reference page, The Programmer Mode index map).
"""
import re

HEADER = [240, 0, 32, 41, 2, 14, 3]              # 03 command: batch LED color
MODE_SYSEX = [240, 0, 32, 41, 2, 14, 14]         # 0E command: Programmer / Live
TERM = 247
NSPEC = 108
FIRST_INDEX = 1
FRAME_LEN = len(HEADER) + NSPEC * 3 + 1          # 332, every cell a palette color
SPEC_LEN = {0: 3, 1: 4, 2: 3, 3: 5}              # by type: static, flash, pulse, RGB

# read out of g_grid.pd rather than guessed. The mode lamps are the left
# column's eight, page 1 at the top: LAMPS[m - 1] is page m's.
LAMPS = (80, 70, 60, 50, 40, 30, 20, 10)
BEAT_LO, BEAT_HI = 11, 18
DIM, LAMP_ON, BEAT_ON, ALERT_RED = 1, 21, 3, 5

MIDI_RE = re.compile(r"^MIDIOUT:\s+(-?\d+)\s+(-?\d+)\s*$")


class Frame(object):
    def __init__(self, data, mark):
        self.data = data
        self.mark = mark
        self.specs = self._specs() if self.is_lighting else None

    @property
    def is_lighting(self):
        return self.data[:7] == HEADER

    @property
    def is_mode(self):
        return self.data[:7] == MODE_SYSEX

    def _specs(self):
        """-> [(type, index, color)] read spec by spec to the terminator, or None
        when a type is unknown or a spec runs into it."""
        out, k, end = [], len(HEADER), len(self.data) - 1
        while k < end:
            n = SPEC_LEN.get(self.data[k])
            if n is None or k + n > end:
                return None
            body = self.data[k + 2:k + n]
            out.append((self.data[k], self.data[k + 1],
                        body[0] if len(body) == 1 else tuple(body)))
            k += n
        return out

    @property
    def whole(self):
        """Every spec read cleanly and there are 108 of them."""
        return self.specs is not None and len(self.specs) == NSPEC

    def color(self, index):
        return {i: c for _t, i, c in self.specs or []}.get(index)

    def colors(self):
        return [c for _t, _i, c in self.specs or []]

    def indices(self):
        return [i for _t, i, _c in self.specs or []]

    def types(self):
        return [t for t, _i, _c in self.specs or []]


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

    Home is: everything dark, the eight mode lamps dim with one lit, the eight beat
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
                return ("mode lamp %d is color %s" % (idx, color)), lamp, beat
        elif BEAT_LO <= idx <= BEAT_HI:
            if color == BEAT_ON:
                if beat is not None:
                    return ("two beat cells lit: %d and %d" % (beat, idx)), lamp, beat
                beat = idx
            elif color != DIM:
                return ("beat cell %d is color %s" % (idx, color)), lamp, beat
        elif color != 0:
            stray.append((idx, color))
    if stray:
        return ("lit outside every region: %s" % stray[:6]), lamp, beat
    return None, lamp, beat


# ---------------------------------------------------------------------------
# The drum page, page 2. Which cell is which comes from the layout table that
# g_grid and u_map both read, never typed here; the colors are g_grid's.
DRUM_PAGE = "Cut It/cut-it-drum-page.txt"
PLAYHEAD = 21                   # green, over whatever the step holds
OUT = 0                         # a step past the last step, lit or not: dark
# g_grid's RGB table: velocity level n's color at full brightness, white for
# level 1 falling evenly to red for level 8, and the same at a quarter, for the
# velocity buttons not selected.
LEVEL_RGB = ((127, 127, 127), (127, 109, 109), (127, 91, 91), (127, 73, 73),
             (127, 54, 54), (127, 36, 36), (127, 18, 18), (127, 0, 0))
LEVEL_DIM = ((32, 32, 32), (32, 27, 27), (32, 23, 23), (32, 18, 18),
             (32, 14, 14), (32, 9, 9), (32, 4, 4), (32, 0, 0))
# The drum pads: bright pink, and the selected one red (Brendan, 2026-11-05: near black they read
# too indistinct). The selected pad no longer takes the velocity's color. PAD_DIM keeps its name
# for what every pad but one is.
PAD_DIM, PAD_ON = (127, 20, 72), (127, 0, 0)
BAR_START = (16, 40, 127)       # a bar's first step, off: blue
REP_DIM, REP_HELD = (20, 8, 32), (80, 24, 127)   # a repeat pad, and the one held: purple


def drum_layout(path=DRUM_PAGE):
    """-> {grid index: (role, n)} from the layout table."""
    lay = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            f = line.split()
            if f:
                lay[int(f[0])] = (f[1], int(f[2]))
    return lay


def level_of(velocity):
    """The velocity level, 1..8, whose color a step at this velocity takes: c_steps.lua's
    R.level, which c_steps sends the page. A copy, so a change to that rule turns the
    sequencer gate red until this follows it."""
    return (int(velocity) - 1) // 16 + 1


def step_color(velocity, step=1, last=16, bar=16):
    """The color a step at this velocity paints, off the playhead, in bars of
    this many steps."""
    if step > last:
        return OUT
    if velocity < 1:
        return BAR_START if (step - 1) % bar == 0 else DIM
    return LEVEL_RGB[level_of(velocity) - 1]


def drum_page(frame, lay):
    """-> (problem_or_None, lit_lamp_index, page) for a page-2 HOME frame.

    page is {"step": {n: color}, "vel": {n: color}, "pad": {n: color}, "rep": {n:
    color}}. The
    page is: the eight mode lamps as home has them, every layout cell in a color
    its role can take, and everything else dark -- the beat row included, since
    it gives way here, and the bottom-right 4x4, which no row names.
    """
    allowed = {"step": {DIM, OUT, PLAYHEAD, BAR_START} | set(LEVEL_RGB),
               "vel": set(LEVEL_RGB) | set(LEVEL_DIM), "pad": {PAD_DIM, PAD_ON},
               "rep": {REP_DIM, REP_HELD}}
    lamp, page, stray = None, {"step": {}, "vel": {}, "pad": {}, "rep": {}}, []
    for k, color in enumerate(frame.colors()):
        idx = FIRST_INDEX + k
        if idx in LAMPS:
            if color == LAMP_ON:
                if lamp is not None:
                    return ("two mode lamps lit: %d and %d" % (lamp, idx)), lamp, page
                lamp = idx
            elif color != DIM:
                return ("mode lamp %d is color %s" % (idx, color)), lamp, page
        elif idx in lay:
            role, n = lay[idx]
            if color not in allowed[role]:
                return ("%s %d (index %d) is color %s" % (role, n, idx, color)), lamp, page
            page[role][n] = color
        elif color != 0:
            stray.append((idx, color))
    if stray:
        return ("lit outside the lamps and the page: %s" % stray[:6]), lamp, page
    full = [n for n, c in page["vel"].items() if c == LEVEL_RGB[n - 1]]
    wrong = [n for n, c in page["vel"].items() if c not in (LEVEL_RGB[n - 1], LEVEL_DIM[n - 1])]
    if wrong:
        return ("velocity buttons %s are not their own level's color" % wrong), lamp, page
    if len(full) > 1:
        return ("%d velocity buttons selected: %s" % (len(full), sorted(full))), lamp, page
    lit = [n for n, c in page["pad"].items() if c != PAD_DIM]
    if len(lit) > 1:
        return ("%d pads lit: %s" % (len(lit), sorted(lit))), lamp, page
    held = [n for n, c in page["rep"].items() if c == REP_HELD]
    if len(held) > 1:
        return ("%d repeat pads held: %s" % (len(held), sorted(held))), lamp, page
    heads = [n for n, c in page["step"].items() if c == PLAYHEAD]
    if len(heads) > 1:
        return ("%d playheads: steps %s" % (len(heads), sorted(heads))), lamp, page
    return None, lamp, page


# ---------------------------------------------------------------------------
# The synth pads, page 3. Which cell is which synth comes from the layout table
# g_grid and u_map both read, never typed here; the colors are g_grid's RGB
# entries 20 to 23: each synth's, full when it is chosen and a quarter when not.
SYNTH_PAGE = "Cut It/cut-it-synth-page.txt"
SYNTH_RGB = {"fm": ((127, 56, 0), (32, 14, 0)),            # amber
             "strings": ((0, 96, 127), (0, 24, 32))}       # cyan


def synth_layout(path=SYNTH_PAGE):
    """-> {grid index: synth} from the layout table."""
    lay = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            f = line.split()
            if f:
                lay[int(f[0])] = f[1]
    return lay


def synth_page(frame, lay, chosen):
    """-> (problem_or_None, lit_lamp_index, lit_beat_index) for a page-3 HOME frame.

    Page 3 is home, the mode lamps and the beat row, with the synth pads above the
    beat row: every layout cell its synth's color, full for the synth chosen and a
    quarter for the other, and everything else dark.
    """
    lamp, beat, stray = None, None, []
    for k, color in enumerate(frame.colors()):
        idx = FIRST_INDEX + k
        if idx in lay:
            full, quarter = SYNTH_RGB[lay[idx]]
            want = full if lay[idx] == chosen else quarter
            if color != want:
                return ("synth pad %d, %s, is %s, wanted %s with %s chosen"
                        % (idx, lay[idx], color, want, chosen)), lamp, beat
        elif idx in LAMPS:
            if color == LAMP_ON:
                if lamp is not None:
                    return ("two mode lamps lit: %d and %d" % (lamp, idx)), lamp, beat
                lamp = idx
            elif color != DIM:
                return ("mode lamp %d is color %s" % (idx, color)), lamp, beat
        elif BEAT_LO <= idx <= BEAT_HI:
            if color == BEAT_ON:
                beat = idx
            elif color != DIM:
                return ("beat cell %d is color %s" % (idx, color)), lamp, beat
        elif color != 0:
            stray.append((idx, color))
    if stray:
        return ("lit outside the lamps, the beat row and the synth pads: %s"
                % stray[:6]), lamp, beat
    return None, lamp, beat


# ---------------------------------------------------------------------------
# The tap pad, page 1. Which cell is which role comes from the layout table
# g_grid and u_map both read, never typed here; the colors are g_grid's RGB
# entries 24 and 25: a tap cell yellow at a quarter, and full while it flashes.
ARRANGE_PAGE = "Cut It/cut-it-arrangement-page.txt"
ROLE_RGB = {"tap": ((32, 24, 0), (127, 96, 0))}            # dim, flashing


def arrange_layout(path=ARRANGE_PAGE):
    """-> {grid index: role} from the layout table."""
    lay = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            f = line.split()
            if f:
                lay[int(f[0])] = f[1]
    return lay


def arrange_page(frame, lay, flashing=False):
    """-> (problem_or_None, lit_lamp_index, lit_beat_index) for a page-1 HOME frame.

    Page 1 is home, the mode lamps and the beat row, with the arrangement page's
    pads beside them: every layout cell its role's color, dim, or full while it
    flashes, and everything else dark.
    """
    lamp, beat, stray = None, None, []
    for k, color in enumerate(frame.colors()):
        idx = FIRST_INDEX + k
        if idx in lay:
            dim, full = ROLE_RGB[lay[idx]]
            want = full if flashing else dim
            if color != want:
                return ("pad %d, %s, is %s, wanted %s%s"
                        % (idx, lay[idx], color, want, " flashing" if flashing else "")), lamp, beat
        elif idx in LAMPS:
            if color == LAMP_ON:
                if lamp is not None:
                    return ("two mode lamps lit: %d and %d" % (lamp, idx)), lamp, beat
                lamp = idx
            elif color != DIM:
                return ("mode lamp %d is color %s" % (idx, color)), lamp, beat
        elif BEAT_LO <= idx <= BEAT_HI:
            if color == BEAT_ON:
                beat = idx
            elif color != DIM:
                return ("beat cell %d is color %s" % (idx, color)), lamp, beat
        elif color != 0:
            stray.append((idx, color))
    if stray:
        return ("lit outside the lamps, the beat row and page 1's pads: %s"
                % stray[:6]), lamp, beat
    return None, lamp, beat
