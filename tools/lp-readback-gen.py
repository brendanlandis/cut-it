# One-off generator for tools/lp-readback.pd -- Part 0 of the test-suite work.
# Generated rather than hand-authored because #X connect indices are positional
# and every hand edit in this repo that inserted a box shifted them silently.
#
# LAYOUT RULE, from Brendan's feedback on lp-step0.pd ("lots of elements
# overlapping each other"): every clickable control is a VERTICAL chain in one
# left-hand column, in procedure order, with its note text well clear to the
# right. Nothing a cord could pass through sits between a button and its message.
B = []
C = []


def obj(x, y, s):
    B.append("#X obj %d %d %s;" % (x, y, s))
    return len(B) - 1


def msg(x, y, s):
    B.append("#X msg %d %d %s;" % (x, y, s))
    return len(B) - 1


def txt(x, y, s, f=80):
    B.append("#X text %d %d %s, f %d;" % (x, y, s, f))
    return len(B) - 1


def bng(x, y):
    return obj(x, y, "bng 25 250 50 0 empty empty empty 17 7 0 10 -262144 -1 -1")


def con(a, ao, b, bi):
    C.append("#X connect %d %d %d %d;" % (a, ao, b, bi))


# ---------------------------------------------------------------- headers
txt(20, 20,
    "lp-readback -- WHAT CAN THE LAUNCHPAD TELL Pd? Nothing here touches Cut It. It was "
    "written to settle a claim ref-midi.md stated as fact and had never measured: that "
    "nothing in the rig transmits SysEx TO Pd. ✅ THAT CLAIM IS FALSE. [sysexin] fires \\, "
    "and the Launchpad answers a universal device inquiry with its manufacturer ID and "
    "firmware version -- which is what makes detecting a replug possible at all. Kept as "
    "the re-check if a Launchpad is ever swapped.", 96)
txt(20, 150,
    "SETUP: Media -> MIDI Settings. Launchpad as input device 1 AND output device 1. "
    "Run this in the FOREGROUND so the Pd window shows the prints. Work down the left "
    "column in order -- every step is labelled with the item number it answers.", 96)
txt(20, 250,
    "BUTTONS 1 TO 5 DO THE WHOLE TEST THEMSELVES -- press one \\, then read the console and "
    "look at the device. Do not touch the Launchpad for those. STEPS 6 AND 7 ARE THE "
    "OPPOSITE: they have NO BUTTON at all and the test IS what you do with your hands. "
    "Nothing in between \\, so there is never a step where you have to guess.", 96)
txt(20, 360,
    "WHAT TO WATCH: the two print objects top right. SYSEX-IN fires only for System "
    "Exclusive. RAW-IN fires for every incoming byte of any kind \\, so it is the wider "
    "net -- if the device answers with anything at all \\, RAW-IN sees it even when "
    "SYSEX-IN does not. A COMPLETELY SILENT CONSOLE IS A RESULT \\, not a failure to run "
    "the test.", 96)

# ---------------------------------------------------------------- output plumbing
o_r = obj(1900, 120, "r \\$0-out")
o_m = obj(1900, 190, "midiout")
o_lb = obj(2120, 60, "loadbang")
o_p = obj(2120, 120, "f 1")
con(o_r, 0, o_m, 0)
con(o_lb, 0, o_p, 0)
con(o_p, 0, o_m, 1)
txt(1900, 250,
    "Every button sends its bytes here. The port goes into the cold inlet at load -- "
    "u_init's proven pattern \\, not a creation argument.", 52)

# ---------------------------------------------------------------- input side
i_s = obj(1900, 380, "sysexin")
i_sp = obj(1900, 440, "print SYSEX-IN")
con(i_s, 0, i_sp, 0)
i_m = obj(2300, 380, "midiin")
i_mp = obj(2300, 440, "print RAW-IN")
con(i_m, 0, i_mp, 0)
txt(1900, 510,
    "ITEM 98 IS ANSWERED THE MOMENT THIS PATCH LOADS WITHOUT AN ERROR: [sysexin] "
    "instantiates in Pd 0.49. Whether it ever FIRES is items 99 to 101.", 52)

# ---------------------------------------------------------------- controls
COL = 20        # the one column every control lives in
NOTE = 640      # notes start here, well clear of the vertical cords
Y = 530
STEP = 250


def control(label, note, button=True):
    """label + bng in one column; returns the bng index and the row's y.

    button=False for a step that happens entirely on the hardware. An earlier
    version drew a bng for those too and wired it to nothing, which is a control
    that lies about being a control -- Brendan reasonably asked what it did."""
    global Y
    txt(COL, Y, label, 44)
    b = bng(COL, Y + 55) if button else None
    txt(NOTE, Y + 55, note, 60)
    y = Y
    Y += STEP
    return b, y


def bytes_control(label, note, byte_msg):
    b, y = control(label, note)
    m = msg(COL, y + 110, byte_msg)
    s = obj(COL, y + 170, "s \\$0-out")
    con(b, 0, m, 0)
    con(m, 0, s, 0)


bytes_control(
    "1 -- ITEM 99: universal device inquiry",
    "The most widely implemented query there is. If anything comes back at all \\, "
    "Pd can poll the device for presence -- which is what would make the replug hazard "
    "fixable.",
    "240 \\, 126 \\, 127 \\, 6 \\, 1 \\, 247")

bytes_control(
    "2 -- enter Programmer Mode",
    "Needed before the paint buttons mean anything. Note that the grid keeps whatever it "
    "was already showing -- LED state survives the switch \\, which is measured.",
    "240 \\, 0 \\, 32 \\, 41 \\, 2 \\, 14 \\, 14 \\, 1 \\, 247")

b3, y3 = control(
    "3 -- ITEM 101a: paint 99 specs from index 10 -- KNOWN GOOD",
    "The surface MUST go green from the top row down to the bottom row of the ring \\, "
    "leaving the SECOND bottom row -- CC 1 to 8 -- dark. That is exactly the span g_grid "
    "paints every repaint \\, and every index in it is inside MIDI's 7-bit data range.")
m3 = msg(COL, y3 + 110, "10 99 21")
s3 = obj(COL, y3 + 170, "s \\$0-paint")
con(b3, 0, m3, 0)
con(m3, 0, s3, 0)

b4, y4 = control(
    "4 -- ITEM 105: paint 120 specs from index 1 -- IS THERE A CEILING AT ALL?",
    "⚠️ EVERY EARLIER ANSWER TO THIS WAS FROM A BROKEN TEST \\, twice over. The first probe "
    "counted from index 10 \\, so it addressed index 128 -- which is 0x80 \\, a STATUS byte -- "
    "and cut its own SysEx short. The second sent a bare 120 instead of a start and a "
    "count \\, so the engine painted ZERO specs and the empty message looked like a "
    "rejection. Watch the PAINT line in the console: it says exactly what went out.")
m4 = msg(COL, y4 + 110, "1 120 5")
s4 = obj(COL, y4 + 170, "s \\$0-paint")
con(b4, 0, m4, 0)
con(m4, 0, s4, 0)

b4b, y4b = control(
    "4b -- ITEM 108: paint 106 specs from index 1 -- Novation's documented maximum",
    "99 works \\, so the ceiling is above that. This is the number the programmer's "
    "reference gives. If the surface changes \\, the documented limit is real on this unit.")
m4b = msg(COL, y4b + 110, "1 106 45")
s4b = obj(COL, y4b + 170, "s \\$0-paint")
con(b4b, 0, m4b, 0)
con(m4b, 0, s4b, 0)

b4c, y4c = control(
    "4c -- ITEM 109: paint 108 specs from index 1 -- THE WHOLE SURFACE IN ONE MESSAGE",
    "⚠️ THE ONLY ONE OF THESE WITH A DESIGN CONSEQUENCE. Index 1 to 108 is every button the "
    "Launchpad has \\, including the undocumented second bottom row at CC 1 to 8 that g_grid "
    "currently leaves dark. If this paints \\, lighting the whole surface costs one SysEx and "
    "the span could be widened later. If it does not \\, it would cost two -- which is worth "
    "knowing before anyone designs something that wants those eight buttons.")
m4c = msg(COL, y4c + 110, "1 108 13")
s4c = obj(COL, y4c + 170, "s \\$0-paint")
con(b4c, 0, m4c, 0)
con(m4c, 0, s4c, 0)

b4d, y4d = control(
    "4d -- ITEM 110: light INDEX 0 alone -- the Setup button -- DOES IT EVEN TAKE A COLOUR?",
    "⚠️ NEVER ONCE TRIED. Every paint above starts at index 1 or 10 \\, so nothing has ever "
    "addressed index 0 and \"Setup never lights\" is what you would see either way. What IS "
    "measured is only that Programmer Mode locks out the Setup MENU -- that is the button not "
    "opening the device's own settings \\, and it says nothing about the LED or whether the "
    "button transmits. TWO QUESTIONS \\, BOTH ANSWERED HERE: does the bottom-left button go "
    "GREEN when you click this \\, and then does PRESSING it put anything on RAW-IN? If both \\, "
    "g_grid's span should be 0 to 108 -- 109 specs \\, exactly the size \\$0-surface already "
    "is -- and Cut It gains a button. If neither \\, the span stops at 1 and Setup is genuinely "
    "not ours. Press button 2 first if you are not already in Programmer Mode.")
m4d = msg(COL, y4d + 110, "0 1 21")
s4d = obj(COL, y4d + 170, "s \\$0-paint")
con(b4d, 0, m4d, 0)
con(m4d, 0, s4d, 0)
Y += 150        # this note runs past STEP -- pd-layout-check catches it if not

bytes_control(
    "5 -- return to Live Mode",
    "⚠️ DO THIS BEFORE STEP 6. Programmer Mode LOCKS OUT the device's own Setup menu -- "
    "so a mode change by hand is impossible until you are back in Live Mode. The first "
    "version of this patch asked for it the other way round \\, which could not work.",
    "240 \\, 0 \\, 32 \\, 41 \\, 2 \\, 14 \\, 14 \\, 0 \\, 247")

control(
    "6 -- ITEM 100: now change mode BY HAND -- no button here",
    "NOTHING TO CLICK: this step is entirely on the hardware \\, and there is deliberately "
    "no bng beside it. You are in Live Mode now \\, so the device's own mode buttons work. "
    "Press Session \\, Note \\, Chord. DOES ANYTHING REACH THE CONSOLE? If the device "
    "announces its own mode changes \\, Pd can notice a replug the moment it happens "
    "instead of polling for it.",
    button=False)

control(
    "7 -- ITEM 99b: unplug the Launchpad \\, then plug it back in -- no button here",
    "ALSO ENTIRELY ON THE HARDWARE. Wait a few seconds \\, plug it back in \\, then press "
    "button 1 again. If the inquiry still answers \\, Pd can detect a return by polling. "
    "If Pd has dropped the device instead \\, say so -- that is the answer for the Mac and "
    "the device may differ \\, since the Organelle rewires ALSA by name at boot.",
    button=False)

# ---------------------------------------------------------------- paint engine
E = Y + 200
txt(COL, E - 160,
    "THE PAINT ENGINE -- header \\, then N times a type byte an index and a colour \\, then "
    "247. The same frame shape g_grid builds. BYTE ORDER INSIDE A SPEC COMES FROM ONE "
    "TRIGGER firing right to left \\, which is what makes it impossible to send a spec with "
    "its bytes swapped.", 96)

e_r = obj(COL, E, "r \\$0-paint")
# THE ENGINE SAYS WHAT IT WAS ASKED FOR AND WHAT IT SENT. A caller that passed a
# bare count instead of "start count" once left the engine painting ZERO specs,
# and an empty SysEx on the wire is indistinguishable from a message the device
# rejected -- so a real bug read as a clean measurement. Two prints make that
# impossible: PAINT-ASKED echoes the request, PAINT-SENT counts the bytes.
e_pr = obj(COL + 620, E, "print PAINT-ASKED")
con(e_r, 0, e_pr, 0)
e_up = obj(COL, E + 60, "unpack f f f")
e_cnt = obj(COL + 300, E + 120, "f")
e_t = obj(COL, E + 180, "t b b f b b")
con(e_r, 0, e_up, 0)
con(e_up, 1, e_cnt, 1)
con(e_up, 0, e_t, 0)

# byte counter: reset when the header goes out, printed when the terminator does
BC = COL + 1400
e_bcr = obj(BC, E, "r \\$0-out")
e_bct = obj(BC, E + 60, "t b")
e_bcf = obj(BC, E + 120, "f")
e_bci = obj(BC + 200, E + 180, "+ 1")
e_bcfan = obj(BC + 200, E + 240, "t f f")
e_bcmir = obj(BC + 460, E + 300, "f")
e_bcz = obj(BC + 700, E + 120, "r \\$0-bytes-zero")
e_bcrd = obj(BC + 460, E + 240, "r \\$0-bytes-read")
e_bcp = obj(BC + 460, E + 380, "print PAINT-SENT-BYTES")
con(e_bcr, 0, e_bct, 0)
con(e_bct, 0, e_bcf, 0)
con(e_bcf, 0, e_bci, 0)
con(e_bci, 0, e_bcfan, 0)
con(e_bcfan, 1, e_bcf, 1)
con(e_bcfan, 0, e_bcmir, 1)
con(e_bcz, 0, e_bcf, 1)
# only the READ prints. Wiring the increment straight to the print put one line
# on the console per byte -- 368 of them for a single press.
con(e_bcrd, 0, e_bcmir, 0)
con(e_bcmir, 0, e_bcp, 0)
txt(BC, E + 480,
    "368 bytes is 120 specs \\, 305 is 99 \\, and 8 means the engine sent a header and a "
    "terminator with NOTHING in between -- which looks exactly like the device rejecting a "
    "message. That ambiguity cost a wrong conclusion \\, twice.", 60)

# outlet 0 -- the terminator, fires LAST. Leftmost column.
e_endt = obj(COL, E + 260, "t b b")
e_end = msg(COL, E + 320, "247")
e_es = obj(COL, E + 380, "s \\$0-out")
e_rd = obj(COL + 160, E + 320, "s \\$0-bytes-read")
con(e_t, 0, e_endt, 0)
con(e_endt, 1, e_end, 0)
con(e_end, 0, e_es, 0)
con(e_endt, 0, e_rd, 0)

# outlet 1 -- the loop.
LOOP = COL + 300
e_u = obj(LOOP, E + 260, "until")
e_f = obj(LOOP, E + 320, "f")
e_ff = obj(LOOP, E + 380, "t f f")
e_inc = obj(LOOP + 220, E + 440, "+ 1")
con(e_t, 1, e_cnt, 0)
con(e_cnt, 0, e_u, 0)
con(e_u, 0, e_f, 0)
con(e_f, 0, e_ff, 0)
con(e_ff, 1, e_inc, 0)
con(e_inc, 0, e_f, 1)

# outlet 2 -- the header.
HDR = COL + 620
e_hdr = msg(HDR, E + 260, "240 \\, 0 \\, 32 \\, 41 \\, 2 \\, 14 \\, 3")
e_hs = obj(HDR, E + 320, "s \\$0-out")
con(e_t, 3, e_hdr, 0)
con(e_hdr, 0, e_hs, 0)

# outlet 3 -- reset the counter, fires FIRST. Rightmost column, and it reaches the
# counter by name rather than by a long cord back across the loop.
RST = COL + 1000
e_zero = msg(RST, E + 260, "0")
e_zs = obj(RST, E + 320, "s \\$0-reset")
e_bz = obj(RST + 300, E + 400, "s \\$0-bytes-zero")
con(e_t, 4, e_zero, 0)
con(e_zero, 0, e_zs, 0)
con(e_zero, 0, e_bz, 0)
e_rr = obj(LOOP + 220, E + 260, "r \\$0-reset")
con(e_rr, 0, e_f, 1)

# the three bytes of one spec, in firing order right to left
SPEC = E + 560
e_spec = obj(LOOP, SPEC, "t b f b")
con(e_ff, 0, e_spec, 0)

# THE COLOUR IS A PARAMETER TOO. Every button used to paint the same green, so
# once one of them had covered the surface the next was invisible -- and "no
# change" read as "the device refused it". Distinct colours make each press say
# something on its own.
e_col = obj(LOOP, SPEC + 60, "f 21")
e_cs = obj(LOOP, SPEC + 120, "s \\$0-out")
con(e_spec, 0, e_col, 0)
con(e_col, 0, e_cs, 0)
e_cols = obj(COL + 320, E + 60, "s \\$0-colour")
con(e_up, 2, e_cols, 0)
e_colr = obj(LOOP - 260, SPEC + 60, "r \\$0-colour")
con(e_colr, 0, e_col, 1)

# THE START INDEX IS A PARAMETER, and that is not cosmetic. The first version of
# this patch hardcoded + 10, so a 120-spec test addressed indices 10..129 -- and
# 128 is 0x80, a Note Off STATUS byte. MIDI data bytes are 7-bit, so that message
# was malformed rather than merely long: it cut its own SysEx short and the tail
# was parsed as channel-voice messages on channel 2, the Launchpad's FLASHING
# channel, addressing note 21 -- which is the colour byte in every spec. So the
# pad that misbehaved was named by a byte meant to be a colour.
e_idx = obj(LOOP + 260, SPEC + 60, "+ 10")
e_is = obj(LOOP + 260, SPEC + 120, "s \\$0-out")
con(e_spec, 1, e_idx, 0)
con(e_idx, 0, e_is, 0)
e_ss = obj(COL + 620, E + 180, "s \\$0-start")
con(e_t, 2, e_ss, 0)
e_sr = obj(LOOP + 500, SPEC, "r \\$0-start")
con(e_sr, 0, e_idx, 1)

e_typ = msg(LOOP + 520, SPEC + 60, "0")
e_ts = obj(LOOP + 520, SPEC + 120, "s \\$0-out")
con(e_spec, 2, e_typ, 0)
con(e_typ, 0, e_ts, 0)

txt(LOOP + 760, SPEC + 60,
    "colour \\, then index \\, then type -- laid out left to right but FIRED right to left \\, "
    "so the bytes leave in the order type index colour.", 52)

W, H = 2900, SPEC + 320
open("tools/lp-readback.pd", "w").write(
    "#N canvas 20 20 %d %d 12;\n" % (W, H) + "\n".join(B + C) + "\n")
print("boxes", len(B), "connects", len(C))
