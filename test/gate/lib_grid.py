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

# The voices' lamps, read out of g_grid.lua: a row's left button and its right, row 1 at the top.
# LEFT[r - 1] and RIGHT[r - 1] are row r's. Each is its voice's color, full where the page is, dim
# elsewhere, and dark with no voice (g_grid.pd's RGB entries 28 to 43).
LEFT = (80, 70, 60, 50, 40, 30, 20, 10)
RIGHT = (89, 79, 69, 59, 49, 39, 29, 19)
VOICE_FULL = ((127, 20, 72), (0, 96, 127), (127, 56, 0), (0, 127, 32),
              (64, 20, 127), (127, 110, 0), (127, 24, 8), (90, 90, 90))
VOICE_DIM = ((31, 5, 18), (0, 24, 31), (31, 14, 0), (0, 31, 8),
             (16, 5, 31), (31, 27, 0), (31, 6, 2), (22, 22, 22))
DIM, ALERT_RED = 1, 5

MIDI_RE = re.compile(r"^MIDIOUT:\s+(-?\d+)\s+(-?\d+)\s*$")

# The edges, on every page (ref/module/songs.md): the top row's eight, CC 91 to 98 -- the two
# arrows, then the six section buttons -- from u_song's top <8 lamps>, save and revert, CC
# 108 and 8, from its unsaved. Read out of g_grid.pd's RGB table (entries 20, 21, 22 and 23) and
# its palette: an arrow is palette 1, dim; a section dim green, the one playing full green, the
# one queued full and dark by turns; save red and revert gray while anything is unsaved.
TOP = tuple(range(91, 99))
SAVE, REVERT = 108, 8
SECTION_DIM, SECTION_ON = (0, 32, 8), (0, 127, 32)
SAVE_ON, REVERT_ON = (127, 0, 0), (40, 40, 40)
# The next arrow, the top row's second: blue when it is the setlist's next song (RGB entry 17, the
# drum page's blue), blinking while that song is queued.
NEXT = TOP[1]
NEXT_SONG = (16, 40, 127)
EDGES = TOP + (SAVE, REVERT)


def edge_problem(idx, color):
    """None if an edge cell is a color its lamp can take, else what is wrong."""
    ok = {0}
    if idx == NEXT:
        ok |= {1, NEXT_SONG}
    elif idx in TOP[:2]:
        ok |= {1}
    elif idx in TOP:
        ok |= {SECTION_DIM, SECTION_ON}
    elif idx == SAVE:
        ok |= {SAVE_ON}
    elif idx == REVERT:
        ok |= {REVERT_ON}
    return None if color in ok else "edge %d is color %s" % (idx, color)


def edges(frame):
    """-> {index: color} for the edge cells of a frame."""
    return {i: frame.color(i) for i in EDGES}


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


def lamp_problem(idx, color):
    """None if a cell of the two columns is a color its row's lamp can take, else what is wrong."""
    row = (LEFT + RIGHT).index(idx) % 8
    if color in (0, VOICE_FULL[row], VOICE_DIM[row]):
        return None
    return "row %d's lamp at %d is color %s" % (row + 1, idx, color)


def page_shape(frame, lit=(), save_lamps=True):
    """-> (problem_or_None, lit_lamp_index) for a frame: the lamps as voices have them, the edges a
    color each can take, the cells in `lit` free, and everything else dark. An off-by-one that
    lights a stray cell is the problem this returns. The lamp is the one lit at full, which is
    where the page is, or None. save_lamps False: the performance page, whose bottom rows are the
    nanoKONTROL's buttons, so save's and revert's cells are free too."""
    lamp, stray = None, []
    for k, color in enumerate(frame.colors()):
        idx = FIRST_INDEX + k
        if idx in lit:
            continue
        if idx in LEFT or idx in RIGHT:
            problem = lamp_problem(idx, color)
            if problem:
                return problem, lamp
            if color and color in VOICE_FULL:
                if lamp is not None:
                    return "two lamps lit: %d and %d" % (lamp, idx), lamp
                lamp = idx
        elif idx in EDGES and (save_lamps or idx in TOP):
            if edge_problem(idx, color):
                return edge_problem(idx, color), lamp
        elif idx in (SAVE, REVERT) and not save_lamps:
            continue
        elif color != 0:
            stray.append((idx, color))
    if stray:
        return "lit outside the page, the lamps and the edges: %s" % stray[:6], lamp
    return None, lamp


# ---------------------------------------------------------------------------
# The drum page. Which cell is which comes from the layout table that g_grid and
# u_map both read, never typed here; the colors are g_grid's.
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
# A pad whose track won't play, muted or left out of a solo (Brendan, 2026-11-05): each of those
# at a quarter, g_grid's RGB entries 24 and 25.
PAD_QUIET, PAD_ON_QUIET = (32, 5, 18), (32, 0, 0)
PADS = (PAD_DIM, PAD_ON, PAD_QUIET, PAD_ON_QUIET)
BAR_START = (16, 40, 127)       # every Nth step, off, N the top number: blue
# The step cells are four rows of eight, numbered 1 to 32 along them by the layout table, and the
# time signature's top number says how many of a row's eight hold steps (c_steps.lua's R.row):
# row r and column c, from 0, show step r x row + c + 1, and a cell past the row is dark.
ROW = 8
# A repeat pad and the 500 BPM repeat, pad-35: the brightest purple there is, and whiter, never
# dimmer, while held (Brendan, 2026-11-05). REP_DIM keeps its name for what a pad not held is.
REP_DIM, REP_HELD = (127, 0, 127), (127, 80, 127)
# The saved tempo, pad-38: dim blue, and bright while held. g_grid's RGB entries 26 and 27.
RECALL_DIM, RECALL_HELD = (8, 20, 64), (40, 100, 127)


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


def step_color(velocity, step=1, last=16, every=4):
    """The color a step at this velocity paints, off the playhead, a blue step every
    this many from step 1, the time signature's top number."""
    if step > last:
        return OUT
    if velocity < 1:
        return BAR_START if (step - 1) % every == 0 else DIM
    return LEVEL_RGB[level_of(velocity) - 1]


def cell_step(n, row=ROW):
    """The step the step cell n, 1 to 32, shows in rows of this many steps, or None past
    the row: c_steps.lua's R.cell_step, a copy, so a change to that rule turns the
    sequencer gate red until this follows it."""
    r, c = (n - 1) // ROW, (n - 1) % ROW
    return None if c >= row else r * row + c + 1


def drum_page(frame, lay, row=ROW):
    """-> (problem_or_None, lit_lamp_index, page) for a frame of the drum page, its rows of steps
    this long.

    page is {"step": {step: color}, "vel": {n: color}, "pad": {n: color}, "rep": {n:
    color}, "fast": {1: color}, "recall": {1: color}}, a step cell keyed by the step
    it shows (cell_step). The page is: the voices' lamps, every layout cell in a color
    its role can take, a step cell past its row dark, and everything else dark -- the
    two cells between pad-35 and pad-38 among them, which no row names.
    """
    allowed = {"step": {DIM, OUT, PLAYHEAD, BAR_START} | set(LEVEL_RGB),
               "vel": set(LEVEL_RGB) | set(LEVEL_DIM), "pad": set(PADS),
               "rep": {REP_DIM, REP_HELD}, "fast": {REP_DIM, REP_HELD},
               "recall": {RECALL_DIM, RECALL_HELD}}
    lamp, page, stray = None, {"step": {}, "vel": {}, "pad": {}, "rep": {}, "fast": {},
                               "recall": {}}, []
    for k, color in enumerate(frame.colors()):
        idx = FIRST_INDEX + k
        if idx in LEFT or idx in RIGHT:
            problem = lamp_problem(idx, color)
            if problem:
                return problem, lamp, page
            if color and color in VOICE_FULL:
                if lamp is not None:
                    return ("two lamps lit: %d and %d" % (lamp, idx)), lamp, page
                lamp = idx
        elif idx in lay:
            role, n = lay[idx]
            if color not in allowed[role]:
                return ("%s %d (index %d) is color %s" % (role, n, idx, color)), lamp, page
            if role == "step":
                step = cell_step(n, row)
                if step is None:
                    if color != OUT:
                        return ("step cell %d (index %d), past a row of %d, is color %s"
                                % (n, idx, row, color)), lamp, page
                    continue
                n = step
            page[role][n] = color
        elif idx in EDGES:
            if edge_problem(idx, color):
                return edge_problem(idx, color), lamp, page
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
    lit = [n for n, c in page["pad"].items() if c in (PAD_ON, PAD_ON_QUIET)]
    if len(lit) > 1:
        return ("%d pads lit: %s" % (len(lit), sorted(lit))), lamp, page
    held = [n for n, c in page["rep"].items() if c == REP_HELD]
    if len(held) > 1:
        return ("%d repeat pads held: %s" % (len(held), sorted(held))), lamp, page
    heads = [n for n, c in page["step"].items() if c == PLAYHEAD]
    if len(heads) > 1:
        return ("%d playheads: steps %s" % (len(heads), sorted(heads))), lamp, page
    return None, lamp, page
