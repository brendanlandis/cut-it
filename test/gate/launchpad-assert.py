#!/usr/bin/env python3
"""The Launchpad's analyser -- ref/device/launchpad.md. Reads a capture on stdin.

Two SysEx messages and the order between them:

  Programmer Mode at boot   LED writes sent in Live Mode do not appear, so
                            getting this wrong is a grid that comes up dark
  Live Mode on quit         ⛔ a Launchpad left in Programmer Mode is stranded,
                            and nothing on the Organelle can put it back

And the heartbeat that re-enters Programmer Mode every presence tick waits
while a pad is held: re-entering it makes the device let go of every held pad
(Brendan, 2026-11-04: the repeat pads gave up after a second or so).

Panic must not hand the surface back: that kills the grid until a reload, and
in Live Mode the device floods Pd's Midi-In 1 with clock (item 250). What g_grid
does with the surface is display-assert's.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_assert as A                                         # noqa: E402
import lib_grid as G                                           # noqa: E402

PROGRAMMER, LIVE = 1, 0


MARKS = ("SETTLED", "PANIC", "HELD", "SWAP", "LET-GO", "QUIT")


def main():
    # Read once: G.parse and A.windows both need the text, and a second read of
    # stdin would get nothing.
    cap = A.require_capture(sys.stdin.read())
    frames = G.parse(cap.splitlines(), "LP")
    mode = [f for f in frames if f.is_mode]
    lighting = [f for f in frames if f.is_lighting]

    # A Pd that died after SETTLED would leave PANIC and QUIT empty, and the
    # exact counts below would be answered by an empty list.
    A.windows(cap, "LP", len(MARKS))

    # Nothing below can tell an unrewritten scratch copy from a device that was
    # never told anything.
    if not A.check("the run produced SysEx at all", bool(frames),
                   "nothing reached [midiout] -- is the scratch copy rewritten?"):
        return A.report()

    prog = [f for f in mode if f.data[7:8] == [PROGRAMMER]]
    live = [f for f in mode if f.data[7:8] == [LIVE]]

    A.check("m_launchpad enters Programmer Mode at boot", bool(prog),
            "no F0 .. 0E 01 F7 was ever sent")
    A.check("⛔ m_launchpad returns to Live Mode on QUIT", bool(live),
            "NO F0 .. 0E 00 F7 -- a Launchpad left in Programmer Mode is STRANDED")

    # Exact: the driver fires panic and then quitting, so a panic that still
    # handed back makes two. The check above is this one's liveness witness.
    A.check("⛔ panic does NOT hand the surface back -- exactly ONE Live Mode frame",
            len(live) == 1,
            "saw %d Live Mode frames. Two means panic is still surrendering the "
            "surface, which kills the grid until the patch is reloaded and leaves "
            "the device flooding Pd's Midi-In 1 with clock (item 250)" % len(live))

    # The count alone cannot tell the failures apart: a panic that hands back
    # and a quit that does not also make exactly one frame, and that is worse.
    A.check("⛔ the ONE Live Mode frame arrives in the QUIT window",
            [f.mark for f in live] == ["QUIT"],
            "Live Mode was sent in window(s) %s. Sent at PANIC instead of QUIT "
            "means the grid dies mid-set and the device is STILL stranded on exit"
            % ([f.mark for f in live] or "none"))

    # A patch that painted and then switched mode would send both and still come
    # up dark.
    if prog and lighting:
        A.check("⛔ Programmer Mode is entered BEFORE the first frame is painted",
                frames.index(prog[0]) < frames.index(lighting[0]),
                "the grid was painted into Live Mode and would not have appeared")
    else:
        A.check("⛔ Programmer Mode is entered BEFORE the first frame is painted",
                False, "saw %d mode-switch and %d lighting frame(s) -- cannot "
                       "establish the order" % (len(prog), len(lighting)))

    # And on the way out: a handback before the last paint leaves it lit in Live
    # Mode. The else arm keeps the check from vanishing when there is no handback
    # at all, the stranded case it exists for.
    if live:
        after = [f for f in lighting if frames.index(f) > frames.index(live[0])]
        A.check("nothing is painted AFTER the device has been handed back",
                not after, "%d frame(s) sent to a Launchpad in Live Mode" % len(after))
    else:
        A.check("nothing is painted AFTER the device has been handed back",
                False, "NO Live Mode frame was ever sent, so there is no handback "
                       "to paint after -- the device is STRANDED in Programmer Mode "
                       "and this check cannot be answered")

    # The heartbeat: none while pad 45 is down, then ring button 91, a tick each,
    # and back once both are let go, which is also the witness that it runs at all.
    beats = {m: len([f for f in prog if f.mark == m]) for m in ("HELD", "SWAP", "LET-GO")}
    A.check("⛔ a held pad holds the Programmer Mode heartbeat off -- none while it is down",
            beats["HELD"] == 0,
            "%d heartbeat(s) while pad 45 was held: each one makes the device let go of "
            "the pad, and a held repeat pad stops repeating" % beats["HELD"])
    A.check("... nor while a ring button is held", beats["SWAP"] == 0,
            "%d heartbeat(s) while button 91 was held" % beats["SWAP"])
    A.check("... and let go, the heartbeat comes back", beats["LET-GO"] >= 1,
            "no heartbeat in the 4 s after the pad was let go -- a replugged Launchpad on "
            "the Mac would stay in Live Mode")

    A.note("%d mode switch(es) in the run: %s"
           % (len(mode), " ".join("programmer" if f.data[7:8] == [PROGRAMMER] else "live"
                                  for f in mode)))
    return A.report()


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
