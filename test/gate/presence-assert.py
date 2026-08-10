#!/usr/bin/env python3
"""The device-presence analyser -- ref/module/presence.md.

    presence-assert.py [-v] --bound BOUND-CAPTURE < MAIN-CAPTURE

⛔ IT READS TWO CAPTURES, FROM TWO Pd RUNS, AND KEEPS ONE TALLY. The first run is
the schedule at the shipped tick; the second scales the settle and the tick by ten
and leaves the counts alone, which is the only way anything here ever reaches the
give-up. Two analysers would print two `N checks` lines, and the count is this
suite's whole defence against an assertion quietly going missing -- test/README.md
adds them up. So there is one report(), at the bottom, covering both.

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

# The second run's windows -- see presence-bound-drive-gen.py for the schedule
# each one straddles.
BOUND_MARKS = ("EARLY", "LATE", "AFTER")

# ⛔ SIX IN EARLY, NOT FIVE. u_init forks wire.sh once at 1500 ms, and the scaled
# settle deliberately puts the first recovery fork at 1400 -- so u_init's own lands
# BETWEEN recovery forks 1 and 2 and inside this window. Every other count in the
# bound run is of recovery forks alone.
BOUND_EARLY = 6
# Eight recovery forks at counter 4, 8 ... 32, plus u_init's one at boot.
BOUND_TOTAL = 9
GAVEUP = "fail u_present rewire-gaveup"
# ⛔ THE TWO FORKS NAME THEMSELVES SEPARATELY, and that separation is the point.
# Both converge on the same `sh wire.sh` message box, so one report tapped below
# the junction would call every scheduled attempt a trailing one -- which is
# precisely the distinction that could not be drawn on the hardware.
REWIRE_TRY = "info u_present rewire-try"
REWIRE_LAST = "info u_present rewire-last"

# ⛔ EVERY m_ LAYER REGISTERS, INCLUDING THE TWO THAT CANNOT BE POLLED. Three are
# active and hold a c_presence; m_organelle is passive and m_volca is none, and
# both of those register and then age never. Asserting the TOTAL is what stops
# this gate going quietly vacuous: a device layer that stopped registering would
# simply stop being watched, and every "nothing was lost" check here would pass
# for the worst possible reason. Same failure docs-check had when it stopped
# seeing seven of nine pages and still said ok.
ROSTER = 5
ACTIVE = 3

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


def by_window(cap, rx, tag="PRES"):
    """-> {mark: [group(1), ...]} for every line matching rx, keyed by window.

    ⚠️ THE TAG IS A PARAMETER BECAUSE THERE ARE TWO RUNS. The first driver prints
    `PRES: MARK ...` and the second `BOUND: MARK ...`, and a hardcoded prefix
    here would silently put the whole of the second capture into the PRE window
    -- where every per-window count reads zero and every "nothing happened in
    this window" assertion passes for the worst possible reason.
    """
    mark_re = re.compile(r"^%s:\s+MARK\s+(\S+)\s*$" % re.escape(tag))
    by, cur = {"PRE": []}, "PRE"
    for line in cap.splitlines():
        line = line.strip()
        m = mark_re.match(line)
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


def raised_in(errs, want, *marks):
    """Windows in which an exact err line appeared, once per appearance.

    ⚠️ IT COUNTS RATHER THAN TESTING MEMBERSHIP, which lost_in above does not.
    The give-up's whole claim is that it happens ONCE -- a window naming it twice
    has to be distinguishable from a window naming it once, and `in` cannot do
    that.
    """
    return [m for m in marks for _ in range(errs.get(m, []).count(want))]


def main_run(cap):
    """The first run: the schedule at the shipped tick. -> keep going?"""
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
    # ⚠️ wire-watch.sh IS EXCLUDED HERE AND ASSERTED SEPARATELY BELOW. It is
    # a HEARTBEAT, not a one-shot -- it fires for the whole life of the
    # patch -- so folding it into a list of scripts that run once at load
    # would make this check depend on how long the run happened to be.
    quiet = sorted(s for v in by.values() for s in v
                   if s not in ("wire.sh", "wire-watch.sh"))
    if not A.check("⛔ the shell stub is installed -- the three loadbang scripts fired",
                   quiet == ["logroll.sh", "phone-ip.sh", "state-dir.sh"],
                   "saw %s, wanted one each of logroll.sh, phone-ip.sh and "
                   "state-dir.sh. Without a working [shell] stub every count "
                   "below is answered by silence rather than by a fact" % (quiet,)):
        return False

    if not A.check("⛔ u_init's own boot wire.sh lands in the BOOT window",
                   wire_in(by, "BOOT") == 1,
                   "%d in BOOT, wanted 1. The marks and the capture have come out "
                   "of step, so every window count below is reading the wrong "
                   "stretch of the run" % wire_in(by, "BOOT")):
        return False

    # ⛔ AND THE OTHER HALF OF LIVENESS: the patch is actually talking to the
    # device. Without SysEx at all, "the grid is still painted" is unanswerable.
    if not A.check("the run produced SysEx at all", bool(frames),
                   "nothing reached [midiout] -- is the scratch copy rewritten?"):
        return False

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
        return False

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

    # --- ⛔ THE HEARTBEAT, WHICH FIRES WHEN NOTHING IS LOST -------------------
    # ⛔ ITEM 285: A DEVICE NOTHING EVER LOST IS NEVER RECOVERED. Every fork
    # above is gated on something being lost, and a `none` device -- the Volca,
    # which transmits nothing and can never be polled -- has no clock, so it can
    # never be lost. Plug its interface into a running instrument and it
    # enumerates in a second and sits unsubscribed forever. Seen on the rig
    # 2026-08-10 after 1 day 21 hours up.
    #
    # ⛔ SETTLED IS THE WINDOW THAT DECIDES IT, and it was chosen by measuring
    # rather than by reasoning. Every device has answered by then, so nothing is
    # lost -- which is why the check directly above asserts ZERO wire.sh forks
    # here. A heartbeat in the same window is therefore the only positive
    # evidence in this file that the watch does NOT share the recovery's gate.
    #
    # ⚠️ THE OBVIOUS CHOICE WAS WRONG AND THE MUTATION CAUGHT IT. This first read
    # "BEFORE-LOSS or SETTLED", and BEFORE-LOSS is not quiet at all: no MIDI
    # device ever answers on a Mac, so layers are already lost by then. Gating
    # the watch behind the recovery spigot -- the exact regression this guards --
    # left it firing in BEFORE-LOSS and the check passed. Measured both builds:
    # correct fires in BOOT, FOREIGN and SETTLED; gated fires in BEFORE-LOSS and
    # OWN-REPLY and never in SETTLED.
    # ⛔ WHAT ACTUALLY SHIPS, READ OFF u_root.pd, because the copy this run
    # judges has had its watch interval scaled to every tick so the property
    # below is observable at all. Scaling a number in a scratch copy without
    # asserting the real one somewhere is how a gate comes to test a patch that
    # does not ship -- and the scaled value would satisfy every check here.
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "..", "Cut It", "u_root.pd")
    inst = re.search(r"u_present\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)",
                     open(root, encoding="utf-8").read())
    A.check("⛔ u_root ships the four presence arguments, watch included",
            bool(inst),
            "no `u_present <settle> <tick> <give-up> <watch>` in u_root.pd -- a "
            "three-argument instantiation leaves the watch interval at 0 and Pd "
            "0.49 does not warn about a missing creation argument")
    if inst:
        A.check("⛔ ...and the shipped watch interval is 8 ticks, not the scaled 1",
                inst.group(4) == "8",
                "u_root instantiates a watch interval of %s. The gate scales it "
                "to 1 in its own copy; if the SHIPPED patch is 1 the instrument "
                "forks a probe every 2 s forever" % inst.group(4))

    watch = sum(by.get(m, []).count("wire-watch.sh") for m in MARKS)
    A.check("⛔ the re-wire heartbeat fires at all -- item 285's whole subject",
            watch > 0,
            "no wire-watch.sh fork anywhere in the run. A device that was never "
            "lost is then never wired, which is the gap this closes")
    A.check("⛔ ...and in SETTLED, where nothing is lost and no other fork can be",
            by.get("SETTLED", []).count("wire-watch.sh") > 0,
            "the heartbeat fired %d time(s) overall but NONE in SETTLED, the one "
            "window where every device has come back. If it only fires while "
            "something is missing then it is sharing the recovery's gate, and a "
            "device nothing ever lost is still never wired -- item 285 open, with "
            "a green gate over it" % watch)

    # --- ⛔ AND IT SAYS SO ON err, WHICH IS WHAT MAKES IT ATTRIBUTABLE --------
    # ⛔ A FORK THE LOG CANNOT NAME IS THE DEFECT THIS CLOSES. The attempts had a
    # [print rewire] and nothing else, and a menu-launched patch sends stdout to
    # tty1 -- so on the instrument they were invisible. Measured 2026-08-10: the
    # Volca's interface went from unsubscribed to wired on a LIVE instrument with
    # no BOOT, no device-lost and no give-up anywhere in cut-it-err.log. Something
    # ran wire.sh and nothing recorded it.
    last = raised_in(errs, REWIRE_LAST, *MARKS)
    A.check("⛔ the trailing fork names ITSELF on err, once",
            last == ["ALL-BACK"],
            "`%s` reached err in %s, wanted exactly ALL-BACK. This is the line "
            "that lets a trailing fork be told from a scheduled one after the "
            "fact, which is the question item 275 turned on and which the "
            "hardware could not answer" % (REWIRE_LAST, last))

    # ⚠️ THE NEGATIVE HALF, and it is the one that catches a mis-wire. Both forks
    # converge on the same `sh wire.sh` message box, so a report tapped one box
    # too low would fire for BOTH kinds and the check above would still pass --
    # the trailing fork would be named correctly and every scheduled one would be
    # named as trailing too.
    stray = raised_in(errs, REWIRE_LAST, "WAITING", "STILL-LOST", "SETTLED")
    A.check("⛔ ...and a SCHEDULED fork is never reported as the trailing one",
            not stray,
            "`%s` also appeared in %s. Those windows hold regular attempts, so "
            "the report is tapped below the point where the two paths meet and "
            "the distinction it exists to draw is gone" % (REWIRE_LAST, stray))

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
    return True


def bound_run(cap):
    """The second run: the bound, REACHED.

    ⛔ WHAT THE FIRST RUN CANNOT SAY. It proves the re-wire waits for the fourth
    tick and that one counter serves three lost sources -- the INTERVAL and the
    COALESCING. Where the counting STOPS was arithmetic: [moses 33] read off the
    page, 72 seconds away, and no gate in this suite runs that long. This run
    scales u_present's settle and tick by ten and leaves the counts exactly as
    shipped, so counter 33 arrives at 7.2 s and the claim becomes a measurement.

    THREE THINGS, AND THEY FAIL DIFFERENTLY:

      the give-up REPORTS         item 235's other half. It sat behind the same
                                  shut spigot as the recovery, which is why the
                                  error log was empty when this happened for real
      there are exactly EIGHT     the bound. Nine forks in the capture: u_init's
                                  one at boot plus attempts at counter 4 ... 32
      and then NOTHING            moses stops it dead rather than slowing it down.
                                  The counter keeps counting out an unconnected
                                  outlet, which is not the same as the counter
                                  stopping, and only an empty window says so
    """
    by = by_window(cap, SHELL_RE, tag="BOUND")
    errs = by_window(cap, ERR_RE, tag="BOUND")

    A.windows(cap, "BOUND", len(BOUND_MARKS))

    # ⛔ THE SAME LIVENESS WITNESS AS THE FIRST RUN, AND IT IS NOT REDUNDANT.
    # This is a SECOND scratch copy with its own shell stub, and the two headline
    # assertions below -- the give-up arrived, nothing forked afterwards -- are
    # both answered just as well by a copy that never loaded at all.
    # ⚠️ wire-watch.sh IS EXCLUDED HERE AND ASSERTED SEPARATELY BELOW. It is
    # a HEARTBEAT, not a one-shot -- it fires for the whole life of the
    # patch -- so folding it into a list of scripts that run once at load
    # would make this check depend on how long the run happened to be.
    quiet = sorted(s for v in by.values() for s in v
                   if s not in ("wire.sh", "wire-watch.sh"))
    if not A.check("⛔ the shell stub is installed in the scaled copy too",
                   quiet == ["logroll.sh", "phone-ip.sh", "state-dir.sh"],
                   "saw %s, wanted one each of logroll.sh, phone-ip.sh and "
                   "state-dir.sh. This is a SECOND scratch copy and it gets its "
                   "own stub; without it every fork count below is answered by "
                   "silence" % (quiet,)):
        return False

    # ⛔ AND THE ROSTER, because a run where no m_ registered loses nothing, forks
    # nothing and gives up on nothing -- which passes "the bound stopped it dead"
    # for the one reason that has nothing to do with the bound.
    seen_roster = [int(n) for v in by_window(cap, ROSTER_RE, tag="BOUND").values()
                   for n in v]
    if not A.check("⛔ every m_ layer registered in the scaled run -- %d of them" % ROSTER,
                   seen_roster == [ROSTER],
                   "u_present-sources printed %s, wanted exactly one line saying "
                   "%d. An empty roster means nothing was ever lost, so the "
                   "recovery counter never started and every count below is a "
                   "claim about a run that did nothing"
                   % (seen_roster, ROSTER)):
        return False

    # --- ⛔ THE BOUND IS REACHED ---------------------------------------------
    gaveup = raised_in(errs, GAVEUP, "PRE", *BOUND_MARKS)
    A.check("⛔ the bound is REACHED -- the give-up reports, exactly once",
            len(gaveup) == 1,
            "`%s` reached err %d time(s), in %s -- wanted exactly one. Zero is "
            "item 235's other half: the give-up sat downstream of the same "
            "[spigot] the recovery did, so a device absent at load could not "
            "even report that it had stopped trying. More than one means the "
            "counter is being reset and re-run" % (GAVEUP, len(gaveup), gaveup))

    A.check("⛔ ...and only once the eight attempts are spent -- not before",
            gaveup == ["LATE"],
            "the give-up landed in %s, wanted exactly LATE. EARLY means the "
            "give-up count is smaller than the 33 that ships -- the rig would "
            "get its handful of attempts and stop while somebody was still "
            "reaching for the cable, which is the 12-second version that was "
            "measured useless in a room" % (gaveup,))

    # --- ⛔ EIGHT ATTEMPTS, AND THE COUNTS ARE THE SHIPPED ONES --------------
    total = sum(v.count("wire.sh") for v in by.values())
    A.check("⛔ exactly 8 recovery forks, on top of u_init's boot one",
            total == BOUND_TOTAL,
            "saw %d wire.sh fork(s), wanted %d -- u_init's one at 1500 ms plus "
            "attempts at counter 4, 8 ... 32. Fewer means the give-up count is "
            "smaller than it ships; more means [moses] is not stopping them"
            % (total, BOUND_TOTAL))

    # ⛔ EVERY ONE OF THEM REACHES err, AND THE COUNT IS EXACT. u_init's boot fork
    # is not u_present's and must NOT be reported here, so this is one fewer than
    # the fork total above -- which is also what makes the pair of counts able to
    # disagree. A report wired to the wrong side of the schedule would match the
    # forks and miss that distinction.
    tries = raised_in(errs, REWIRE_TRY, "PRE", *BOUND_MARKS)
    A.check("⛔ every scheduled attempt names itself on err -- all %d"
            % (BOUND_TOTAL - 1), len(tries) == BOUND_TOTAL - 1,
            "`%s` reached err %d time(s), in %s -- wanted %d, one per recovery "
            "fork and NOT one for u_init's boot fork. Zero means the attempts are "
            "still invisible to the log, which is how a re-wire on a live "
            "instrument came to be unattributable"
            % (REWIRE_TRY, len(tries), tries, BOUND_TOTAL - 1))

    A.check("...and they are spread on the interval rather than bunched",
            wire_in(by, "EARLY") == BOUND_EARLY,
            "%d wire.sh fork(s) in EARLY, wanted %d -- u_init's boot fork plus "
            "recovery forks 1 through 5. ⚠️ SIX AND NOT FIVE: the scaled settle "
            "puts the first recovery fork at 1400 ms and u_init's own lands at "
            "1500, inside this window. A different number here means mod 4 is "
            "not what is spacing them" % (wire_in(by, "EARLY"), BOUND_EARLY))

    # --- ⛔ AND IT STOPS DEAD, WHICH IS NOT THE SAME AS SLOWING DOWN ---------
    # moses sends 33 and everything above it out a right outlet connected to
    # nothing, so the counter goes on counting for the rest of the run. Counters
    # 36 and 40 fall inside this window, which is exactly where mod 4 would fire
    # if the bound had been widened rather than reached.
    A.check("⛔ nothing forks after the give-up -- the bound stops it DEAD",
            wire_in(by, "AFTER") == 0,
            "%d wire.sh fork(s) in AFTER. The counter is still counting -- that "
            "is correct and unavoidable -- but nothing may act on it again. A "
            "fork here means the bound slowed the retries down instead of "
            "ending them, and Phase 4's one-fork-per-load rule was bent for a "
            "recovery that ENDS" % wire_in(by, "AFTER"))

    A.note("bound run, wire.sh by window: %s"
           % " ".join("%s=%d" % (m, wire_in(by, m)) for m in BOUND_MARKS))
    return True


def _bound_capture():
    """The second capture, named by --bound. ⛔ Its absence is a FAILURE.

    A gate handed no second capture must fail rather than quietly report on one
    run and exit 0 -- the same rule as lib_assert.require_capture, and the same
    reason: a check that did not happen is indistinguishable from one that passed
    once the tally is the only thing anyone reads.
    """
    if "--bound" not in sys.argv or sys.argv[-1] == "--bound":
        A.check("a second capture was supplied", False,
                "no --bound PATH argument. The bound half of this gate reads a "
                "SECOND Pd run, and without it the give-up is untested while "
                "the gate still exits 0")
        return None
    path = sys.argv[sys.argv.index("--bound") + 1]
    try:
        cap = open(path, encoding="utf-8", errors="replace").read()
    except OSError as e:
        A.check("the second capture is readable", False, "%s: %s" % (path, e))
        return None
    if not cap.strip():
        A.check("the second capture is not empty", False,
                "%s held nothing -- Pd wrote no output at all" % path)
        return None
    return cap


def main():
    ok = main_run(A.require_capture(sys.stdin.read()))
    if not ok:
        A.note("the first run's liveness failed -- its remaining checks were skipped")
    # ⛔ THE SECOND RUN GOES AHEAD EITHER WAY. It is a separate Pd process on a
    # separate scratch copy, so a first run that failed to load says nothing
    # about it -- and skipping it here would silently shrink the tally, which is
    # the one number that proves no assertion went missing.
    cap = _bound_capture()
    if cap is not None:
        bound_run(cap)
    return A.report()


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
