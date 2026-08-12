#!/usr/bin/env python3
"""Generates the timed driver for the device-presence gate, into the scratch path.

⛔ THE WHOLE POINT IS WHAT IT DOES **NOT** SEND. This gate drives no device
inquiry reply at all -- [sysexin] has been rewritten to [t_sysexin] in the
scratch copy and nothing is ever pushed at it -- so the patch is running against
a Launchpad that was ABSENT AT LOAD and never answers. That is item 235's exact
condition, and it is the one case the watchdog was built unable to handle.

⚠️ SO THE SILENCE IS THE STIMULUS, WHICH MEANS IT NEEDS A LIVENESS WITNESS. A run
where the scratch copy failed to load at all also produces no replies, and every
"nothing happened yet" assertion below would pass on it. Two things stop that:
u_init's own boot wire.sh must appear in the BOOT window, and the grid must still
be painting at the end.

⛔ AND THE ROSTER IS THREE, NOT ONE. m_launchpad, m_nano and m_404 each hold a
c_presence, so all three go lost together on the same tick and every count below
is a claim about the SHARED bound. m_organelle registers passive and m_volca
registers none, so neither ages and neither can ever contribute a loss -- which
the roster print asserts by counting five registrations against three losses.

THE SCHEDULE IS u_present's OWN ARITHMETIC, and none of it is free:

    4000 ms   u_present's settle expires -- [metro 2000] starts and fires
              immediately, so the ticks are 4000, 6000, 8000, ...
    8000 ms   c_presence's third missed tick. All three active sources are
              declared lost, and u_present's recovery counter starts in the SAME
              tick, because the tick is broadcast before the recovery step reads
              the gate
   14000 ms   counter 4 -- mod 4 hits 0 and wire.sh is forked FOR THE FIRST TIME
   17000 ms   a KORG reply. m_nano is seen, armed, and publishes back
   22000 ms   counter 8 -- the second fork. m_nano has now missed three ticks
              since its own reply, so it goes lost AGAIN, and this time the warn
              is armed and reaches err
   24000 ms   a Novation reply. m_launchpad is seen and armed
   30000 ms   counter 12 -- the third fork, because m_404 never answered and the
              count never reached zero. m_launchpad goes lost again, armed, and
              THIS time ownership drops
   72000 ms   counter 33, the give-up

⛔ THE WINDOWS STRADDLE 8000 AND 14000 RATHER THAN SITTING AFTER THEM. A gate that
only looked at the end could not tell "fires on the fourth tick" from "fires on
every tick", and the interval is half of what the bound is made of. AFTER-LOSS
exists purely to be EMPTY.

⚠️ THE BOUND ITSELF IS NOT ASSERTED HERE and this file must not grow to 72 seconds
to do it. u_present takes the settle, the tick and the give-up as creation
arguments, so a scratch copy can scale the two TIMES and reach the give-up in a
few seconds with the COUNTS exactly as shipped. That belongs with the multi-device
windows, not here.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_drive as D                                          # noqa: E402

GAP = 40

SEQ = [
    # u_init forks all four .sh scripts inside this window -- wire.sh at 1500 ms.
    # ⛔ IT IS THE LIVENESS WITNESS, not decoration: every other shell assertion
    # here is of the form "nothing forked", which an empty capture answers just
    # as well as a working patch does.
    (300, "BOOT", [], GAP),

    # Before the third missed poll. Nothing has been declared lost yet.
    (6000, "BEFORE-LOSS", [], GAP),

    # ⛔ AFTER THE LOSS AND BEFORE THE FOURTH TICK, AND IT EXISTS TO BE EMPTY.
    # Ticks 1 and 2 of the recovery counter land in here. A re-wire in this
    # window means the interval has gone and the bound is meaningless -- eight
    # attempts over 70 s becomes thirty-four over the same 70 s.
    (9000, "AFTER-LOSS", [], GAP),

    # The fourth recovery tick lands at 14000, inside this window.
    (13000, "WAITING", [], GAP),

    # ⛔ AND THE INVARIANT THE ARMING GATE EXISTS FOR. A mode change dirties
    # g_grid, which paints only while it owns the surface -- so a frame arriving
    # here proves ownership was NOT dropped by a detector that has never once
    # seen a reply. Without that half, "arm the recovery at load" would look
    # identical to "delete the arming gate", which cost 7 of 24 checks once.
    (15000, "AFTER-REWIRE", ["\\; mode compose mode-3"], GAP),

    # ⛔ THE CROSS-TALK CASE, AND IT IS THE MOST VALUABLE WINDOW HERE. This is a
    # KORG reply -- manufacturer byte 66, the nanoKONTROL's, measured as item 249
    # -- arriving on the one [sysexin] the whole patch shares. m_launchpad used to
    # count ANY SysEx as proof of its own presence, which was true only while
    # nothing else in the rig transmitted any. Poll all three and that shortcut
    # reports the Launchpad present whenever the NANO answers: item 235 silently
    # un-fixed, in the worst direction, with the watchdog believing a device that
    # is gone.
    (17000, "FOREIGN",
     ["\\; t-sysexin 2 240 126 0 6 2 66 4 1 0 0 35 0 0 0 247"], GAP),

    # The second re-wire is due at 22000. It must still happen -- the foreign
    # reply changed nothing.
    (21000, "STILL-LOST", [], GAP),

    # ⛔ THE POSITIVE CONTROL, AND IT IS NOT OPTIONAL. Everything above is
    # satisfied by a c_devid that matches NOTHING AT ALL -- a dead matcher
    # ignores the nano's reply for entirely the wrong reason and looks identical.
    # This is the Launchpad's own reply, manufacturer byte 0, item 98. Prove the
    # probe before believing the silence.
    (24000, "OWN-REPLY",
     ["\\; t-sysexin 1 240 126 0 6 2 0 32 41 35 1 0 0 0 4 6 5 247"], GAP),

    # ⛔ THE COALESCING WINDOW, AND IT READS AS A SURPRISE UNTIL YOU COUNT THE
    # ROSTER. The Launchpad answered at 24000 so IT is back -- but m_404 never
    # answered at all and m_nano went quiet again three ticks after its own
    # reply, so the lost count never reaches zero and the shared counter is
    # never reset. The third re-wire therefore lands at 30000, in here. That is
    # the design working: ONE bound serves the whole rig. If the recovery still
    # lived inside each m_ the way it did before Phase 4, three lost sources
    # would fork three times per interval and this run would show NINE.
    (28000, "RECOVERED", [], GAP),

    # ⛔ THE OTHER HALF OF THE ARMING GATE, AND NOTHING HAS EVER TESTED IT. Every
    # ownership check before this one asserts the gate stays SHUT -- a device
    # that never answered must not be allowed to blank the grid. This asserts it
    # OPENS: the Launchpad answered at 24000, so it is armed, and it then missed
    # three ticks and was declared lost again at 30000. Ownership must drop this
    # time. A mode change dirties g_grid, and the frame that would have followed
    # must NOT arrive. ⚠️ A gate that only ever proves a thing stays shut passes
    # just as well when it is welded shut.
    (31000, "DROPPED", ["\\; mode compose mode-1"], GAP),

    # ⛔ EVERY DEVICE ANSWERS AT ONCE, WHICH IS THE ONLY WAY TO REACH A LOST COUNT
    # OF ZERO IN THIS RUN -- m_404 is deliberately never answered anywhere above.
    # Hitting zero is what fires the TRAILING fork: u_present runs one last
    # wire.sh on the transition to nothing-lost, because the recovery used to
    # stop the instant the last DETECTABLE device answered and that is not the
    # same as the rig being whole. It stranded the Volca on the bench, item 275.
    #
    # ⚠️ THE REGULAR SCHEDULE IS QUIET HERE ON PURPOSE. Counter 12 fired at 30000
    # and counter 16 is not due until 38000, so any fork inside this window is
    # unambiguously the trailing one rather than the interval coming round.
    #
    # It doubles as the only place all three matchers are proved to work at the
    # same time, on one [sysexin], with three frames back to back.
    (33000, "ALL-BACK",
     ["\\; t-sysexin 1 240 126 0 6 2 0 32 41 35 1 0 0 0 4 6 5 247",
      "\\; t-sysexin 2 240 126 0 6 2 66 4 1 0 0 35 0 0 0 247",
      "\\; t-sysexin 3 240 126 16 6 2 65 8 4 0 0 0 3 0 0 247"], GAP),

    # ⛔ AND IT FIRES ONCE, NOT REPEATEDLY. The counter is reset by the same
    # transition, so nothing further is due. A fork in here means the trailing
    # path re-arms itself, which would turn one extra fork per episode into an
    # unbounded stream -- the exact thing Phase 4's rule exists to prevent.
    # ⛔ THE PHONE'S BUTTON, AND THIS WINDOW IS THE ONLY PLACE IT CAN BE
    # ATTRIBUTED. Every device answered at 33000, so the lost count is zero, the
    # recovery counter has been reset and the spigot is shut -- nothing on the
    # schedule is due. A wire.sh fork in here came from the presence bus or from
    # nowhere.
    #
    # ⚠️ IT SITS BETWEEN ALL-BACK AND SETTLED RATHER THAN AT THE END, and both
    # sides of that are load-bearing. SETTLED's whole claim is that the trailing
    # fork does not re-arm, so it asserts ZERO forks and a deliberate one inside
    # it would make that check untestable. And a window after SETTLED would run
    # past 38000, where the three devices that answered at 33000 miss their third
    # poll and are declared lost all over again -- which lands `device-lost` in a
    # window three other checks require to be quiet. Measured, not reasoned: put
    # here first at 38000 and four checks went red for exactly that reason.
    (34500, "PHONE-REWIRE", ["\\; presence re-wire"], GAP),

    (36000, "SETTLED", [], GAP),
]
QUIT_MS = 38000

BLURB = ("presence-assert-drive -- GENERATED by presence-assert-drive-gen.py. Do not "
         "edit this file. It withholds the device inquiry reply from every device \\, "
         "which is the absent-at-load case of item 235 \\, and then hands exactly two "
         "of them back. What it asserts is that the bounded re-wire fires anyway -- on "
         "the fourth tick and not the first -- that ONE bound serves three lost "
         "sources rather than three \\, and that the grid is owned right up to the "
         "moment a device that has actually been seen goes away.")

NOTES = [
    "⚠️ RUN IT THROUGH test/gate/presence-assert.sh \\, never by hand. The gate copies "
    "t_shell.pd over shell.pd inside a scratch copy so every wire.sh fork PRINTS \\, "
    "and rewrites [sysexin] to [t_sysexin] so the reply can be withheld deliberately "
    "rather than merely being absent. Run against the real Cut It nothing prints and "
    "every count below is answered by an empty list.",

    "⛔ ITEM 235 IN ONE LINE: the recovery used to sit behind a spigot armed by the "
    "device's own reply \\, so a device that was never there never armed it \\, never "
    "got re-wired \\, and could not even report that it had given up. The give-up path "
    "was downstream of the same shut spigot \\, which is why the error log was empty.",
]

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: presence-assert-drive-gen.py OUT.pd  "
                 "(run it through test/gate/presence-assert.sh, which passes a scratch path)")
    w, b, c = D.build(sys.argv[1], SEQ, tag="PRES", taps=["err", "presence"],
                      quit_ms=QUIT_MS, blurb=BLURB, notes=NOTES)
    print("%s  %d windows  %d boxes  %d connects" % (sys.argv[1], w, b, c))
