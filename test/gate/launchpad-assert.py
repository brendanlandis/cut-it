#!/usr/bin/env python3
"""The Launchpad's analyser -- ref/device/launchpad.md. Reads a capture on stdin.

Two SysEx messages and the order between them. That is the entire contract
between this instrument and this device, and both halves of it have a cost when
they are wrong:

  Programmer Mode at boot   LED writes sent in Live Mode do not appear, so
                            getting this wrong is a grid that comes up dark
  Live Mode on QUIT         ⛔ a Launchpad left in Programmer Mode is STRANDED --
                            it stops behaving like a Launchpad for everything
                            else on the machine, and nothing on the Organelle can
                            put it back. This is the one that costs a power cycle.

⛔ PANIC MUST *NOT* HAND THE SURFACE BACK, and that is the newer half of the
contract. It used to, which killed the grid until the patch was reloaded -- and
in Live Mode the device floods MIDI port 1 with clock straight into Pd's Midi-In
1 (item 250), so a panic made the instrument worse in two ways at the moment it
was most needed. Silencing notes has nothing to do with surrendering the surface.

⚠️ Driving `quitting` is therefore not optional. Panic used to be the only thing
that produced a Live Mode frame, which made the PANIC window the sole coverage of
the safe exit BY ACCIDENT. Removing the handback without driving quitting would
have deleted that coverage silently, with the gate still green.

⚠️ IT ASSERTS ON THE DEVICE, NOT ON THE ARBITER. Whether g_grid stops painting
when it loses the surface is display-assert's check, next door; this one is only
about what the hardware is TOLD.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_assert as A                                         # noqa: E402
import lib_grid as G                                           # noqa: E402

PROGRAMMER, LIVE = 1, 0


MARKS = ("SETTLED", "PANIC", "QUIT")


def main():
    # ⛔ READ THE CAPTURE ONCE, because it is needed twice: G.parse reassembles
    # SysEx out of it and A.windows does the bookkeeping over the same MARK lines.
    # Handing sys.stdin to both would give the second one an exhausted stream and
    # a silent "0 of 3 marks".
    cap = A.require_capture(sys.stdin.read())
    frames = G.parse(cap.splitlines(), "LP")
    mode = [f for f in frames if f.is_mode]
    lighting = [f for f in frames if f.is_lighting]

    # ⛔ THE DRIVER GOT ALL THE WAY THROUGH. Without this, a Pd that died after
    # SETTLED leaves the PANIC and QUIT windows empty, and every assertion below
    # of the form "exactly one frame like this" is answered by an empty list
    # rather than by a fact. This gate went without it for its whole life because
    # it taps no bus -- but it does emit marks, so the check was always available.
    A.windows(cap, "LP", len(MARKS))

    # ⛔ AND WITHOUT THIS THE WHOLE GATE CAN PASS ON A CAPTURE THAT REACHED EVERY
    # MARK AND STILL SAID NOTHING. Every check below is of the form "a frame like
    # this exists", and none of them can tell a scratch copy that was never
    # rewritten from a device that was never told anything.
    if not A.check("the run produced SysEx at all", bool(frames),
                   "nothing reached [midiout] -- is the scratch copy rewritten?"):
        return A.report()

    prog = [f for f in mode if f.data[7:8] == [PROGRAMMER]]
    live = [f for f in mode if f.data[7:8] == [LIVE]]

    A.check("m_launchpad enters Programmer Mode at boot", bool(prog),
            "no F0 .. 0E 01 F7 was ever sent")
    A.check("⛔ m_launchpad returns to Live Mode on QUIT", bool(live),
            "NO F0 .. 0E 00 F7 -- a Launchpad left in Programmer Mode is STRANDED")

    # ⛔ THE NEW HALF, AS AN EXACT COUNT rather than a window test. The driver
    # fires panic and THEN quitting, and Live Mode is sent nowhere else -- so the
    # old behaviour produced TWO of these frames and the correct one produces
    # exactly ONE. The check above is this one's liveness witness: together they
    # say "a handback happened, and only the right one did".
    A.check("⛔ panic does NOT hand the surface back -- exactly ONE Live Mode frame",
            len(live) == 1,
            "saw %d Live Mode frames. Two means panic is still surrendering the "
            "surface, which kills the grid until the patch is reloaded and leaves "
            "the device flooding Pd's Midi-In 1 with clock (item 250)" % len(live))

    # ⛔ AND IT IS THE QUIT WINDOW'S, NOT PANIC'S. The count alone cannot tell the
    # two failures apart: "panic hands back and quitting does not" also produces
    # exactly one frame, and it is the WORSE of the two -- the grid dies mid-set
    # AND the device is left stranded on exit. The mark says which window it
    # arrived in, so say so.
    A.check("⛔ the ONE Live Mode frame arrives in the QUIT window",
            [f.mark for f in live] == ["QUIT"],
            "Live Mode was sent in window(s) %s. Sent at PANIC instead of QUIT "
            "means the grid dies mid-set and the device is STILL stranded on exit"
            % ([f.mark for f in live] or "none"))

    # ⛔ THE ORDER, WHICH IS NOT IMPLIED BY EITHER MESSAGE EXISTING. A patch that
    # painted the grid and then switched mode would send both of these and still
    # come up dark, because LED writes in Live Mode do not appear.
    if prog and lighting:
        A.check("⛔ Programmer Mode is entered BEFORE the first frame is painted",
                frames.index(prog[0]) < frames.index(lighting[0]),
                "the grid was painted into Live Mode and would not have appeared")
    else:
        A.check("⛔ Programmer Mode is entered BEFORE the first frame is painted",
                False, "saw %d mode-switch and %d lighting frame(s) -- cannot "
                       "establish the order" % (len(prog), len(lighting)))

    # ...and the same argument on the way out: handing the device back before the
    # last paint would leave whatever was lit on screen in Live Mode.
    #
    # ⛔ THE else ARM IS NOT DECORATION. This check used to live inside a bare
    # `if live:` with nothing after it, so the case it exists for -- the device
    # never handed back at all, which is the ⛔ STRANDED failure at the top of
    # this file -- made it SILENTLY NOT RUN. The tally dropped 5 to 4 and the only
    # witness was a count in test/README.md that nothing compares against. A check
    # that disappears in exactly the situation it was written for is worse than no
    # check, because the run still says ok.
    if live:
        after = [f for f in lighting if frames.index(f) > frames.index(live[0])]
        A.check("nothing is painted AFTER the device has been handed back",
                not after, "%d frame(s) sent to a Launchpad in Live Mode" % len(after))
    else:
        A.check("nothing is painted AFTER the device has been handed back",
                False, "NO Live Mode frame was ever sent, so there is no handback "
                       "to paint after -- the device is STRANDED in Programmer Mode "
                       "and this check cannot be answered")

    A.note("%d mode switch(es) in the run: %s"
           % (len(mode), " ".join("programmer" if f.data[7:8] == [PROGRAMMER] else "live"
                                  for f in mode)))
    return A.report()


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
