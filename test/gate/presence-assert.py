#!/usr/bin/env python3
"""The device-presence analyser -- ref/module/presence.md. Reads a capture on stdin.

⛔ THE CLAIM: A DEVICE THAT WAS NEVER THERE STILL GETS RECOVERED. The run it reads
never delivers a device-inquiry reply, so the Launchpad it describes is one that
was absent when the patch loaded. Item 235 is that this case was unreachable --
the bounded wire.sh recovery sat behind a [spigot] armed only by a reply, and so
did the give-up, which is why the error log was empty when it happened.

FOUR THINGS, AND THEY FAIL DIFFERENTLY:

  the re-wire happens at all      item 235. Nothing forked before the fix
  it waits for the fourth tick    the interval, which is half of what the bound
                                  is made of -- fire every tick and eight
                                  attempts over 70 s becomes thirty-four
  it does not fire early          a re-wire before the threshold means the loss
                                  test has gone, not that recovery is eager
  ownership is NOT dropped        ⛔ the invariant the arming gate protects. The
                                  fix splits that gate rather than removing it,
                                  and removing it is the plausible wrong answer

⚠️ EVERY SHELL ASSERTION HERE IS A COUNT WITHIN A WINDOW, never a total. u_init
forks wire.sh once at boot as well, so a total of "at least one" is satisfied by
the boot fork alone and says nothing whatever about recovery.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_assert as A                                         # noqa: E402
import lib_grid as G                                           # noqa: E402

MARKS = ("BOOT", "BEFORE-LOSS", "AFTER-LOSS", "WAITING", "AFTER-REWIRE",
         "FOREIGN", "STILL-LOST", "OWN-REPLY", "RECOVERED", "DROPPED",
         "ALL-BACK", "SETTLED")

# ⛔ EVERY m_ LAYER REGISTERS, INCLUDING THE TWO THAT CANNOT BE POLLED. Three are
# active and hold a c_presence; m_organelle is passive and m_volca is none, and
# both of those register and then age never. Asserting the TOTAL is what stops
# this gate going quietly vacuous: a device layer that stopped registering would
# simply stop being watched, and every "nothing was lost" check here would pass
# for the worst possible reason. Same failure docs-check had when it stopped
# seeing seven of nine pages and still said ok.
ROSTER = 5
ACTIVE = 3

MARK_RE = re.compile(r"^PRES:\s+MARK\s+(\S+)\s*$")
ROSTER_RE = re.compile(r"^u_present-sources:\s+(\d+)\s*$")
ERR_RE = re.compile(r"^err:\s+(.*\S)\s*$")
# ⚠️ THE BUS IS TAPPED AS WELL AS err, and `tick` rides it every 2 s -- 17 of
# them in this run. That is noise worth paying for: `back <src>` is the only
# direct evidence that a matcher accepted its OWN reply, and without it the
# trailing-fork check has no positive control except itself.
# ⛔ UPPERCASE, AND THE err ONE ABOVE IS NOT. `err:` lines come from u_err's own
# internal [print err], which is unconditional and is the reason the log sees
# everything the screen is filtered out of. `PRESENCE:` lines come from the
# DRIVER's tap, and lib_drive labels those from TAP_LABELS in upper case. Two
# different mechanisms that happen to look alike in a capture.
BUS_RE = re.compile(r"^PRESENCE:\s+(.*\S)\s*$")
# ⚠️ THE TRAILING ARGUMENTS ARE NOT OPTIONAL IN THIS REGEX -- two of the four
# scripts carry one. u_state forks `sh state-dir.sh <dir>` and u_net forks
# `sh phone-ip.sh <fallback>`, so an end-anchored pattern matches logroll.sh and
# wire.sh only and silently reports the other two as never having run. Same
# shape as the anchored [midiout] regex that made phase 6's gate blind to
# [ctlout 123], and found the same way -- by the count being wrong.
SHELL_RE = re.compile(r"^SHELL:\s+sh\s+(\S+)")


def by_window(cap, rx):
    """-> {mark: [group(1), ...]} for every line matching rx, keyed by window."""
    by, cur = {"PRE": []}, "PRE"
    for line in cap.splitlines():
        line = line.strip()
        m = MARK_RE.match(line)
        if m:
            cur = m.group(1)
            by.setdefault(cur, [])
            continue
        m = rx.match(line)
        if m:
            by.setdefault(cur, []).append(m.group(1))
    return by


def wire_in(by, *marks):
    return sum(by.get(m, []).count("wire.sh") for m in marks)


def lost_in(errs, src, *marks):
    """Windows in which `warn <src> device-lost` was raised."""
    want = "warn %s device-lost" % src
    return [m for m in marks if want in errs.get(m, [])]


def main():
    cap = A.require_capture(sys.stdin.read())
    frames = G.parse(cap.splitlines(), "PRES")
    by = by_window(cap, SHELL_RE)
    errs = by_window(cap, ERR_RE)
    bus = by_window(cap, BUS_RE)

    A.windows(cap, "PRES", len(MARKS))

    # ⛔ THE LIVENESS WITNESS, AND EVERY "NOTHING FORKED" CHECK BELOW DEPENDS ON
    # IT. A scratch copy whose shell stub never got installed reports no forks at
    # all, which satisfies three of the four assertions here for entirely the
    # wrong reason.
    #
    # ⚠️ THE OTHER THREE SCRIPTS FIRE AT loadbang, WHICH IS BEFORE THE FIRST MARK.
    # u_state, u_err and u_net each fork one at load, so they land in the capture
    # ahead of the BOOT mark and belong to no window -- only wire.sh, at u_init's
    # 1500 ms wiring stage, arrives late enough to be inside one. That is why
    # this is two checks: the three prove the STUB, and wire.sh proves the
    # WINDOWING as well.
    quiet = sorted(s for v in by.values() for s in v if s != "wire.sh")
    if not A.check("⛔ the shell stub is installed -- the three loadbang scripts fired",
                   quiet == ["logroll.sh", "phone-ip.sh", "state-dir.sh"],
                   "saw %s, wanted one each of logroll.sh, phone-ip.sh and "
                   "state-dir.sh. Without a working [shell] stub every count "
                   "below is answered by silence rather than by a fact" % (quiet,)):
        return A.report()

    if not A.check("⛔ u_init's own boot wire.sh lands in the BOOT window",
                   wire_in(by, "BOOT") == 1,
                   "%d in BOOT, wanted 1. The marks and the capture have come out "
                   "of step, so every window count below is reading the wrong "
                   "stretch of the run" % wire_in(by, "BOOT")):
        return A.report()

    # ⛔ AND THE OTHER HALF OF LIVENESS: the patch is actually talking to the
    # device. Without SysEx at all, "the grid is still painted" is unanswerable.
    if not A.check("the run produced SysEx at all", bool(frames),
                   "nothing reached [midiout] -- is the scratch copy rewritten?"):
        return A.report()

    # ⛔ THE ROSTER, AND IT IS THE THIRD LIVENESS WITNESS. u_present prints how
    # many layers registered, once, at settle. Every negative assertion below --
    # nothing forked, nothing was lost, nothing was reported -- is also what a
    # patch with an EMPTY roster produces, and an empty roster is exactly what a
    # renamed bus or a dropped loadbang would give. Asserting the count is what
    # separates "the instrument watched five devices and none misbehaved" from
    # "the instrument watched nothing".
    seen_roster = [int(n) for v in by_window(cap, ROSTER_RE).values() for n in v]
    if not A.check("⛔ every m_ layer registered on the presence bus -- %d of them"
                   % ROSTER,
                   seen_roster == [ROSTER],
                   "u_present-sources printed %s, wanted exactly one line saying "
                   "%d. Fewer means a device layer stopped registering and is now "
                   "silently unwatched, which makes every check below vacuous; "
                   "more than one line means the settle fired twice"
                   % (seen_roster, ROSTER)):
        return A.report()

    # --- the recovery is not eager ------------------------------------------
    A.check("no re-wire before the loss is declared",
            wire_in(by, "BEFORE-LOSS") == 0,
            "%d wire.sh fork(s) in BEFORE-LOSS. The three-missed-poll test has "
            "gone -- a single dropped reply now forks Pd"
            % wire_in(by, "BEFORE-LOSS"))

    # ⛔ THE INTERVAL. Ticks 1 and 2 of the recovery counter land in this window
    # and mod 4 must swallow both.
    A.check("⛔ no re-wire on the first ticks after the loss -- it waits for the fourth",
            wire_in(by, "AFTER-LOSS") == 0,
            "%d wire.sh fork(s) in AFTER-LOSS. Firing every tick turns eight "
            "attempts over 70 s into thirty-four, and the bound is what makes "
            "forking permissible at all" % wire_in(by, "AFTER-LOSS"))

    # --- ⛔ ITEM 235 ---------------------------------------------------------
    A.check("⛔ a device that NEVER answered still gets re-wired -- exactly once, "
            "on the fourth tick",
            wire_in(by, "WAITING") == 1,
            "%d wire.sh fork(s) in WAITING, wanted exactly 1. Zero is item 235 "
            "itself: the recovery armed only on a device-inquiry REPLY, so a "
            "device absent at load never armed it and only a reload brought the "
            "surface back" % wire_in(by, "WAITING"))

    # --- ⛔ THE INVARIANT THE ARMING GATE PROTECTS ---------------------------
    # g_grid paints only while it owns the surface, so a lighting frame after the
    # loss was declared is proof that ownership survived a detector which has
    # never once seen a reply.
    late = [f for f in frames
            if f.is_lighting and f.mark in ("AFTER-REWIRE", "FOREIGN")]
    A.check("⛔ ownership is NOT dropped by a detector that never saw a reply",
            bool(late),
            "no lighting frame after the re-wire. The arming gate has been "
            "REMOVED rather than split: the grid now blanks six seconds into "
            "every run on any platform without a Launchpad, which is how this "
            "was found the first time -- 7 of 24 checks")

    # --- ⛔ CROSS-TALK: ANOTHER DEVICE'S REPLY IS NOT THIS DEVICE'S ----------
    # A KORG reply landed in FOREIGN. If m_launchpad counted it, the miss counter
    # zeroed, moses went left, the recovery counter was reset -- and the re-wire
    # due at 21000 never comes.
    A.check("⛔ a nanoKONTROL reply does NOT mark the Launchpad present",
            wire_in(by, "STILL-LOST") == 1,
            "%d wire.sh fork(s) in STILL-LOST, wanted exactly 1. A KORG reply "
            "(manufacturer byte 66) was accepted as this device's. That is item "
            "235 un-fixed in the worst direction -- the watchdog believing a "
            "device that is gone -- and it is what 'ANY SysEx counts as "
            "presence' becomes the moment more than one device answers"
            % wire_in(by, "STILL-LOST"))

    # ⛔ THE POSITIVE CONTROL FOR THE CHECK ABOVE, AND WITHOUT IT THAT CHECK IS
    # WORTHLESS: a c_devid that matches NOTHING AT ALL ignores the nano's reply
    # for entirely the wrong reason and passes every assertion so far.
    #
    # ⚠️ IT CANNOT BE READ OFF THE FORKS ANY MORE, and that change is the whole of
    # Phase 4. The re-wire is now SHARED, so it keeps running while m_404 is
    # missing no matter what the Launchpad does -- "did this device's reply get
    # through" and "is anything still lost" stopped being the same question.
    #
    # The armed warn answers it instead, and answers it per device. c_presence
    # publishes `lost` unconditionally but reports it only once the device has
    # been seen at least once, because a device that has NEVER answered is
    # ABSENT rather than lost and absent is the normal state of everything on a
    # Mac. So a `warn <src> device-lost` on the bus is proof of three things at
    # once: that source's matcher fired, it fired for a reply that really was
    # its own, and the arming latch it set is still holding.
    nano_lost = lost_in(errs, "m_nano", *MARKS)
    A.check("⛔ ...and the KORG reply IS taken -- by m_nano, and only after it lands",
            nano_lost == ["STILL-LOST"],
            "warn m_nano device-lost appeared in %s, wanted exactly STILL-LOST. "
            "Nowhere at all means [c_devid 66] matched nothing, which makes the "
            "cross-talk check above vacuous -- a dead matcher rejects the "
            "Launchpad's traffic too. Earlier than STILL-LOST means the warn is "
            "not armed by a reply and fires for a device that was merely absent"
            % (nano_lost,))

    lp_lost = lost_in(errs, "m_launchpad", *MARKS)
    A.check("⛔ ...and so is the Novation reply -- by m_launchpad, and only after ITS own",
            lp_lost == ["RECOVERED"],
            "warn m_launchpad device-lost appeared in %s, wanted exactly "
            "RECOVERED. This is the second positive control and it is aimed at "
            "the other matcher: [c_devid 0] must accept byte 0 and must have "
            "rejected the KORG byte 66 that arrived seven seconds earlier"
            % (lp_lost,))

    # ⛔ AND THE THIRD DEVICE IS THE NEGATIVE CONTROL. m_404 is polled, is never
    # answered, and holds manufacturer byte 65. Two foreign replies crossed the
    # one [sysexin] it is reading and neither was its own, so it must never have
    # been armed -- and an unarmed source must stay silent however long it is
    # missing. This is the check that would go red if c_devid ignored its
    # creation argument, and it is the one the whole rig depends on: three
    # matchers on one wire.
    p404_lost = lost_in(errs, "m_404", *MARKS)
    A.check("⛔ a device that answered NEITHER reply never reports -- m_404 stays quiet",
            p404_lost == [],
            "warn m_404 device-lost appeared in %s. Nothing ever matched byte "
            "65, so the arming latch was never set and this warn is unreachable "
            "-- unless c_devid is matching on something other than its argument, "
            "in which case all three matchers are the same matcher"
            % (p404_lost,))

    # --- ⛔ THE ARMING GATE OPENS, WHICH IS THE HALF NOTHING TESTED -----------
    # Every ownership assertion until now says the gate stays SHUT. That passes
    # just as well when it is welded shut -- and welded shut is a real failure,
    # because then a Launchpad that genuinely went away keeps being painted and
    # the grid lies about what it is showing. The Launchpad answered at 24 s, so
    # it is armed; it then missed three ticks and was declared lost at 30 s. A
    # mode change dirties g_grid inside DROPPED and the frame must NOT come.
    dropped = [f for f in frames if f.is_lighting and f.mark == "DROPPED"]
    A.check("⛔ ownership IS dropped once the device has been seen and then lost",
            not dropped,
            "%d lighting frame(s) in DROPPED. The grid repainted for a device "
            "that answered and then went away, so the arming gate never opens "
            "and a dark Launchpad would keep being addressed as though it were "
            "there" % len(dropped))

    # ⛔ AND THE LIVENESS WITNESS FOR *THAT* ONE, because "no lighting frame" is
    # also what a Pd that died at 31 s produces. The Programmer Mode heartbeat
    # rides $0-want, which ownership does not touch, so a mode frame in the last
    # window proves the run was still alive and still talking to the port.
    alive = [f for f in frames if f.is_mode and f.mark == "DROPPED"]
    A.check("the run is still alive in the last window",
            bool(alive),
            "no heartbeat frame in DROPPED -- Pd died before the ownership drop "
            "was due, so 'the grid went quiet' is unproven. ⚠️ The heartbeat rides "
            "$0-want and NOT $0-own precisely so that this stays answerable")

    # --- ⛔ THE TRAILING FORK -------------------------------------------------
    # Added after the hardware session and covered by nothing until this window
    # existed: every other window here leaves m_404 missing, so the lost count
    # never reaches zero and the transition that fires this never happens.
    A.check("⛔ the last device returning fires ONE trailing re-wire",
            wire_in(by, "ALL-BACK") == 1,
            "%d wire.sh fork(s) in ALL-BACK, wanted exactly 1. Zero means the "
            "recovery still stops the instant the last DETECTABLE device answers "
            "-- which is not the same as the rig being whole, and is what left a "
            "replugged Volca disconnected on the bench (item 275). The regular "
            "schedule is quiet in this window, so this fork can only be the "
            "trailing one" % wire_in(by, "ALL-BACK"))

    A.check("⛔ ...and exactly once -- the transition does not re-arm",
            wire_in(by, "SETTLED") == 0,
            "%d wire.sh fork(s) in SETTLED. The trailing fork is bounded at one "
            "per episode by the same reset that triggers it; more than one turns "
            "a deliberate exception to Phase 4's one-fork-per-load rule into the "
            "unbounded stream that rule exists to prevent"
            % wire_in(by, "SETTLED"))

    # ⛔ AND ITS POSITIVE CONTROL: all three matchers, on one [sysexin], in one
    # logical instant. If any of the three replies had been rejected the count
    # would not have reached zero and the check above would be answered by a
    # silence that has nothing to do with the trailing fork.
    for src in ("m_launchpad", "m_nano", "m_404"):
        A.check("...because %s accepted its own reply in ALL-BACK" % src,
                ("back %s" % src) in bus.get("ALL-BACK", []),
                "no `back %s` on the presence bus in ALL-BACK -- saw %s. Three "
                "frames went into one [sysexin] back to back and this one's "
                "matcher did not take its own, so the lost count reaching zero "
                "cannot be what fired the trailing re-wire"
                % (src, bus.get("ALL-BACK", [])))

    # --- ⛔ ONE BOUND, NOT ONE PER DEVICE ------------------------------------
    total = sum(v.count("wire.sh") for v in by.values())
    A.check("⛔ %d sources lost together produce ONE re-wire per interval" % ACTIVE,
            total == 5,
            "saw %d wire.sh fork(s), wanted u_init's boot fork plus three "
            "recoveries plus one trailing. %d would be one per lost source per "
            "interval, which is "
            "what the recovery did before Phase 4 moved it out of m_launchpad "
            "and into u_present -- three copies of a bound is not a bound. Fewer "
            "than 5 means the interval, the loss test or the trailing fork has gone"
            % (total, 1 + 3 * ACTIVE))

    A.note("wire.sh by window: %s"
           % " ".join("%s=%d" % (m, wire_in(by, m)) for m in MARKS))
    A.note("device-lost warnings: %s"
           % " ".join("%s=%s" % (s, lost_in(errs, s, *MARKS) or "never")
                      for s in ("m_launchpad", "m_nano", "m_404")))
    A.note("%d lighting frame(s), %d mode frame(s)"
           % (len([f for f in frames if f.is_lighting]),
              len([f for f in frames if f.is_mode])))
    return A.report()


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
