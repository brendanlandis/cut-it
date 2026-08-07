#!/usr/bin/env python3
"""Reassembles Launchpad SysEx out of a capture. Imported, never run.

Both gates that read the Launchpad's wire need this: display-assert cares about
the LIGHTING frames and launchpad-assert about the MODE frames, and they arrive
interleaved in one byte stream.

⛔ REALTIME BYTES ARE SKIPPED, NOT STORED. Bytes >= 248 are legal INSIDE a SysEx
stream and u_tempo emits 96 of them a second, so a reassembler that appended
everything between F0 and F7 would corrupt every frame it built and the failure
would look like a broken grid.

FRAME SHAPE: 332 bytes = 7 header + 108 * 3 + terminator. Spec k holds type at
7+3k, LED index at 8+3k and colour at 9+3k, so the colour at LED index i is byte
9 + 3*(i-1). Indices run 1..108.

THAT SPAN WIDENED FROM 10..108 AND THE OLD REASON WAS MEASURED FALSE. It stopped
at 10 on the belief that ~106 specs approached a documented cliff and that 120
was REJECTED OUTRIGHT -- a whole message dropped, which on a frame clock reads as
a frozen grid. Three broken probes produced that; a clean 120-spec message paints
the whole surface (items 105, 109). The reason to cover the span is that an index
OUTSIDE it can never be cleared: LED state survives the Programmer Mode switch,
so whatever Live Mode drew on CC 1-8 persisted into every session.

Index 0 -- Setup -- stays out, and that one IS measured: a valid one-spec frame
addressing it lights nothing and the button transmits nothing (item 110).
"""
import re

HEADER = [240, 0, 32, 41, 2, 14, 3]              # 03 command: batch LED colour
MODE_SYSEX = [240, 0, 32, 41, 2, 14, 14]         # 0E command: Programmer / Live
TERM = 247
NSPEC = 108
FIRST_INDEX = 1
FRAME_LEN = len(HEADER) + NSPEC * 3 + 1          # 332

# read out of g_grid.pd rather than guessed
LAMP_LO, LAMP_HI = 91, 96
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

    def colour(self, index):
        return self.data[9 + 3 * (index - FIRST_INDEX)]

    def colours(self):
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
    returns -- and it is how the one-based beat bug would have been caught in a
    single run. That bug lit index 19, a right-column ring button, and blanked
    the beat row once a bar: SEVEN BEATS OUT OF EIGHT LOOKED PERFECT.
    """
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
