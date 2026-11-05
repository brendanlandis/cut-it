#!/usr/bin/env python3
"""The device-presence analyzer -- ref/module/presence.md.

    presence-assert.py [-v] --bound BOUND-CAPTURE < MAIN-CAPTURE

Two captures from two Pd runs, and one report() over both, so the gate prints
one `N checks` line (test/README.md). The first run is the shipped schedule; the
second scales the settle and tick by ten, counts untouched, to reach the give-up.

No device answers until late, so the Launchpad is absent at load: item 235, where
the recovery and the give-up both sat behind a [spigot] armed only by a reply.

Every shell assertion is a count within a window, never a total: u_init forks
wire.sh once at boot too, so "at least one" is met by the boot fork alone.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_assert as A                                         # noqa: E402
import lib_grid as G                                           # noqa: E402
import lib_drive as D                                          # noqa: E402

MARKS = ("BOOT", "BEFORE-LOSS", "AFTER-LOSS", "WAITING", "AFTER-REWIRE",
         "WALDORF", "FOREIGN", "STILL-LOST", "OWN-REPLY", "RECOVERED", "DROPPED",
         "ALL-BACK", "PHONE-REWIRE", "SETTLED")

# The second run's windows; presence-bound-drive-gen.py has the schedule.
BOUND_MARKS = ("EARLY", "LATE", "AFTER")

# Six, not five: the scaled settle puts the first recovery fork at 1400 ms, so
# u_init's own at 1500 lands in EARLY. Every other bound count is recovery forks
# alone.
BOUND_EARLY = 6
# Eight recovery forks at counter 4, 8 ... 32, plus u_init's one at boot.
BOUND_TOTAL = 9
GAVEUP = "fail u_present rewire-gaveup"
# The three causes of a fork name themselves separately: all three converge on
# one `sh wire.sh` box, so a report tapped below the junction would name every
# fork as whichever cause it sat under.
REWIRE_TRY = "info u_present rewire-try"
REWIRE_LAST = "info u_present rewire-last"
REWIRE_PHONE = "info u_present rewire-phone"

# Every m_ registers, m_organelle (passive) and m_volca (none) included, though
# neither ages. The total is asserted because a layer that stopped registering
# would stop being watched, and every "nothing was lost" check would still pass;
# exactly, so m_404, gone with the SP-404 (2026-11-04), cannot come back unnoticed.
# Five since m_streich (2026-11-04), the most g_oled's diag layer draws; m_nanokey
# registers nothing, since a sixth row breaks that bound.
ROSTER = 5
ACTIVE = 3
# The universal identity request, which every active layer sends on its own port.
INQUIRY = [240, 126, 127, 6, 1, 247]
STREICH_PORT = 3

ROSTER_RE = re.compile(r"^u_present-sources:\s+(\d+)\s*$")
ERR_RE = re.compile(r"^err:\s+(.*\S)\s*$")
# The presence bus is tapped, `tick` noise and all, because `back <src>` is the
# only direct evidence a matcher took its own reply. Its label is upper case
# (lib_drive's TAP_LABELS) where `err:` is not: that one is u_err's own [print].
BUS_RE = re.compile(r"^%s:\s+(.*\S)\s*$" % re.escape(D.TAP_LABELS["presence"]))
# Not end-anchored: u_state forks `sh state-dir.sh <dir>` and u_net
# `sh phone-ip.sh <fallback>`, and an anchored pattern reports both as never run.
SHELL_RE = re.compile(r"^SHELL:\s+sh\s+(\S+)")
# Forked once each at loadbang, by u_root, u_err, u_net and u_state: the
# liveness witness for every "nothing forked" count.
LOADBANG_SCRIPTS = ["codec-gain.sh", "logroll.sh", "phone-ip.sh", "state-dir.sh"]


def by_window(cap, rx, tag="PRES"):
    """-> {mark: [group(1), ...]} for every line matching rx, keyed by window.

    The two drivers print different tags (PRES, BOUND). The wrong one puts the
    whole capture in PRE, where every "nothing happened" check passes.
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

    It counts, unlike lost_in, because the give-up must happen exactly once.
    """
    return [m for m in marks for _ in range(errs.get(m, []).count(want))]


def main_run(cap):
    """The first run: the schedule at the shipped tick. -> keep going?"""
    frames = G.parse(cap.splitlines(), "PRES")
    by = by_window(cap, SHELL_RE)
    errs = by_window(cap, ERR_RE)
    bus = by_window(cap, BUS_RE)

    A.windows(cap, "PRES", len(MARKS))

    # Liveness: a copy with no shell stub forks nothing, which every "nothing
    # forked" check below also accepts. The four loadbang scripts land before
    # the first mark and prove the stub; wire.sh, at u_init's 1500 ms, lands in
    # BOOT and proves the windowing too. wire-watch.sh is a heartbeat for the
    # whole run, so it is left out here and asserted below.
    quiet = sorted(s for v in by.values() for s in v
                   if s not in ("wire.sh", "wire-watch.sh"))
    if not A.check("⛔ the shell stub is installed -- the four loadbang scripts fired",
                   quiet == LOADBANG_SCRIPTS,
                   "saw %s, wanted one each of codec-gain.sh, logroll.sh, "
                   "phone-ip.sh and state-dir.sh. Without a working [shell] stub every count "
                   "below is answered by silence rather than by a fact" % (quiet,)):
        return False

    if not A.check("⛔ u_init's own boot wire.sh lands in the BOOT window",
                   wire_in(by, "BOOT") == 1,
                   "%d in BOOT, wanted 1. The marks and the capture have come out "
                   "of step, so every window count below is reading the wrong "
                   "stretch of the run" % wire_in(by, "BOOT")):
        return False

    # Without SysEx at all, "the grid is still painted" is unanswerable.
    if not A.check("the run produced SysEx at all", bool(frames),
                   "nothing reached [midiout] -- is the scratch copy rewritten?"):
        return False

    # The third witness: u_present prints the roster once, at settle, and an
    # empty one (a renamed bus, a dropped loadbang) passes every negative below.
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

    # Ticks 1 and 2 of the recovery counter land here, and mod 4 swallows both.
    A.check("⛔ no re-wire on the first ticks after the loss -- it waits for the fourth",
            wire_in(by, "AFTER-LOSS") == 0,
            "%d wire.sh fork(s) in AFTER-LOSS. Firing every tick turns eight "
            "attempts over 70 s into thirty-four, and the bound is what makes "
            "forking permissible at all" % wire_in(by, "AFTER-LOSS"))

    # --- item 235 ---------------------------------------------------------
    A.check("⛔ a device that NEVER answered still gets re-wired -- exactly once, "
            "on the fourth tick",
            wire_in(by, "WAITING") == 1,
            "%d wire.sh fork(s) in WAITING, wanted exactly 1. Zero is item 235 "
            "itself: the recovery armed only on a device-inquiry REPLY, so a "
            "device absent at load never armed it and only a reload brought the "
            "surface back" % wire_in(by, "WAITING"))

    # --- the arming gate stays shut ------------------------------------------
    # g_grid paints only while it owns the surface, so a lighting frame after the
    # loss proves ownership survived a detector that never saw a reply.
    late = [f for f in frames
            if f.is_lighting and f.mark in ("AFTER-REWIRE", "FOREIGN")]
    A.check("⛔ ownership is NOT dropped by a detector that never saw a reply",
            bool(late),
            "no lighting frame after the re-wire. The arming gate has been "
            "REMOVED rather than split: the grid now blanks six seconds into "
            "every run on any platform without a Launchpad, which is how this "
            "was found the first time -- 7 of 24 checks")

    # --- cross-talk: another device's reply is not this device's ------------
    # A KORG reply lands in FOREIGN with both layers lost, and a layer that
    # takes a reply publishes `back` at once (and `seen`, the first time), so
    # the bus answers per device. The fork count can't: m_launchpad, still
    # lost, keeps the shared counter running whatever m_nano takes.
    foreign = bus.get("FOREIGN", [])
    took = [(w, m) for w in ("FOREIGN", "STILL-LOST") for m in bus.get(w, [])
            if m in ("back m_launchpad", "seen m_launchpad")]
    A.check("⛔ a nanoKONTROL reply does NOT mark the Launchpad present",
            "back m_nano" in foreign and not took,
            ("the presence bus held %s after the KORG reply (manufacturer byte "
             "66). m_launchpad took it as its own, so the watchdog believes a "
             "Launchpad that is gone: item 235 un-fixed in the worst direction, "
             "and what 'ANY SysEx counts as presence' becomes the moment more "
             "than one device answers" % (took,)) if took else
            ("no `back m_nano` in FOREIGN, which held %s. Nothing took the KORG "
             "reply at all, so 'the Launchpad did not take it' proves nothing"
             % (foreign,)))

    # The Streichfett's reply, Waldorf's byte 62, alone in WALDORF with the other two
    # lost: m_streich takes it, and nobody else may.
    waldorf = bus.get("WALDORF", [])
    others = [m for m in waldorf if m.split()[:1] in (["back"], ["seen"])
              and m.split()[1:2] != ["m_streich"]]
    A.check("⛔ a Streichfett reply marks m_streich present, and NOBODY else",
            "back m_streich" in waldorf and not others,
            ("%s took the Waldorf reply (manufacturer byte 62), so a lost device reads as "
             "present while the Streichfett answers" % others) if others else
            ("no `back m_streich` in WALDORF, which held %s. [c_devid 62] matched "
             "nothing, so 'nobody else took it' proves nothing" % waldorf))

    # m_nano is back but m_launchpad has not answered, so the fork due at 22000 comes.
    A.check("⛔ one device answering does not reset the shared recovery -- the "
            "second re-wire still comes",
            wire_in(by, "STILL-LOST") == 1,
            "%d wire.sh fork(s) in STILL-LOST, wanted exactly 1. Zero means a "
            "partial return reset the counter, so a rig with one device back "
            "and another still out stops being re-wired; more than one means "
            "the four-tick interval has gone" % wire_in(by, "STILL-LOST"))

    # The positive controls, since a c_devid that matches nothing also ignores
    # the nano's reply. c_presence warns `device-lost` only for a device that
    # has answered (never-answered is absent, the normal state on a Mac), so a
    # warn proves that source's matcher took a reply that was its own.
    nano_lost = lost_in(errs, "m_nano", *MARKS)
    A.check("⛔ ...and the KORG reply IS taken -- by m_nano, and only after it lands",
            nano_lost == ["STILL-LOST"],
            "warn m_nano device-lost appeared in %s, wanted exactly STILL-LOST. "
            "Nowhere at all means [c_devid 66] matched nothing, which makes the "
            "cross-talk check above vacuous -- a dead matcher rejects the "
            "Launchpad's traffic too. Earlier than STILL-LOST means the warn is "
            "not armed by a reply and fires for a device that was merely absent"
            % (nano_lost,))

    st_lost = lost_in(errs, "m_streich", *MARKS)
    A.check("⛔ ...and m_streich, seen at 16000, is lost again with m_nano",
            st_lost == ["STILL-LOST"],
            "warn m_streich device-lost appeared in %s, wanted exactly STILL-LOST: its "
            "warn is armed by its own reply, and three missed polls later it is lost"
            % (st_lost,))

    lp_lost = lost_in(errs, "m_launchpad", *MARKS)
    A.check("⛔ ...and so is the Novation reply -- by m_launchpad, and only after ITS own",
            lp_lost == ["RECOVERED"],
            "warn m_launchpad device-lost appeared in %s, wanted exactly "
            "RECOVERED. The second positive control, aimed at the other "
            "matcher: [c_devid 0] must take its own byte 0 at 24000, which arms "
            "the warn for the loss at 30000. STILL-LOST in the list is "
            "cross-talk: the KORG reply at 17000 armed it and it was lost again "
            "at 22000. No RECOVERED means it never took its own"
            % (lp_lost,))

    # --- the arming gate opens ---------------------------------------------
    # A gate welded shut passes every check above. The Launchpad answered at
    # 24 s and is lost again at 30 s, so the mode change in DROPPED must not paint.
    dropped = [f for f in frames if f.is_lighting and f.mark == "DROPPED"]
    A.check("⛔ ownership IS dropped once the device has been seen and then lost",
            not dropped,
            "%d lighting frame(s) in DROPPED. The grid repainted for a device "
            "that answered and then went away, so the arming gate never opens "
            "and a dark Launchpad would keep being addressed as though it were "
            "there" % len(dropped))

    # "No lighting frame" is also what a Pd that died at 31 s gives. The
    # Programmer Mode heartbeat rides $0-want, which ownership doesn't touch.
    alive = [f for f in frames if f.is_mode and f.mark == "DROPPED"]
    A.check("the run is still alive in the last window",
            bool(alive),
            "no heartbeat frame in DROPPED -- Pd died before the ownership drop "
            "was due, so 'the grid went quiet' is unproven. ⚠️ The heartbeat rides "
            "$0-want and NOT $0-own precisely so that this stays answerable")

    # --- the trailing fork -------------------------------------------------
    # Only here does the lost count reach zero: from 8000 on, one layer or the
    # other is always missing until both answer at once.
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

    # --- the heartbeat, item 285 -------------------------------------------
    # A `none` device (the Volca) can never be lost, so the heartbeat must not
    # share the recovery's gate. SETTLED decides it: nothing is lost there, so a
    # heartbeat in it is the only positive evidence. Not BEFORE-LOSS: nothing
    # answers on a Mac, so layers are lost by then, and a heartbeat gated behind
    # the recovery fires there (measured: gated fires in BEFORE-LOSS and
    # OWN-REPLY and never in SETTLED).
    #
    # This copy's watch is scaled to every tick, so the shipped interval is read
    # off u_root.pd; the scaled value would satisfy every check here.
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

    # --- each fork names itself on err (ref/module/presence.md) ------------
    last = raised_in(errs, REWIRE_LAST, *MARKS)
    A.check("⛔ the trailing fork names ITSELF on err, once",
            last == ["ALL-BACK"],
            "`%s` reached err in %s, wanted exactly ALL-BACK. This is the line "
            "that lets a trailing fork be told from a scheduled one after the "
            "fact, which is the question item 275 turned on and which the "
            "hardware could not answer" % (REWIRE_LAST, last))

    # --- the phone's re-wire ------------------------------------------------
    # Every device answered in ALL-BACK, so nothing on the schedule is due: a
    # fork in this window came from the bus.
    A.check("⛔ re-wire on the presence bus forks wire.sh, exactly once",
            wire_in(by, "PHONE-REWIRE") == 1,
            "%d wire.sh fork(s) in PHONE-REWIRE, wanted exactly 1. Zero means "
            "the phone's button reaches u_present and dies there; more than one "
            "means one press costs several forks, and a fork per event is the "
            "thing Phase 4's rule exists to prevent"
            % wire_in(by, "PHONE-REWIRE"))

    phone = raised_in(errs, REWIRE_PHONE, *MARKS)
    A.check("⛔ ...and names ITSELF on err, once, in that window alone",
            phone == ["PHONE-REWIRE"],
            "`%s` reached err in %s, wanted exactly PHONE-REWIRE. A fork nothing "
            "records is a repair nobody can attribute, and this is the only one "
            "of the three that a person caused" % (REWIRE_PHONE, phone))

    # The negatives catch a report tapped below the shared `sh wire.sh` box,
    # which would name every fork as each kind and still pass the checks above.
    crossed = raised_in(errs, REWIRE_TRY, "PHONE-REWIRE") + \
        raised_in(errs, REWIRE_LAST, "PHONE-REWIRE")
    A.check("⛔ ...and the phone's fork is not ALSO reported as a scheduled one",
            not crossed,
            "a scheduled or trailing name appeared in PHONE-REWIRE: %s. The "
            "three causes share one `sh wire.sh` box, so telling them apart "
            "depends entirely on where each report is tapped" % crossed)

    stray = raised_in(errs, REWIRE_LAST, "WAITING", "STILL-LOST", "SETTLED",
                      "PHONE-REWIRE")
    A.check("⛔ ...and a SCHEDULED fork is never reported as the trailing one",
            not stray,
            "`%s` also appeared in %s. Those windows hold regular attempts, so "
            "the report is tapped below the point where the two paths meet and "
            "the distinction it exists to draw is gone" % (REWIRE_LAST, stray))

    # The trailing fork's positive control: four frames on one [sysexin] in
    # one instant, three taken by their own matchers, or the count never hit zero.
    for src in ("m_launchpad", "m_nano", "m_streich"):
        A.check("...because %s accepted its own reply in ALL-BACK" % src,
                ("back %s" % src) in bus.get("ALL-BACK", []),
                "no `back %s` on the presence bus in ALL-BACK -- saw %s. Four "
                "frames went into one [sysexin] back to back and this one's "
                "matcher did not take its own, so the lost count reaching zero "
                "cannot be what fired the trailing re-wire"
                % (src, bus.get("ALL-BACK", [])))

    # The fourth frame is a Roland reply, byte 65: the SP-404's, which left the
    # rig on 2026-11-04. No layer may take it -- a c_devid matching on anything
    # but its argument would, and so would an m_404 that came back. The negative
    # control the three matchers' own replies cannot give.
    stray = [m for m in bus.get("ALL-BACK", [])
             if m.split()[:1] in (["back"], ["seen"])
             and m.split()[1:2] not in (["m_launchpad"], ["m_nano"], ["m_streich"])]
    A.check("⛔ ...and the Roland reply beside them is taken by NOBODY -- no SP-404 layer",
            not stray,
            "%s on the presence bus in ALL-BACK. Nothing in the rig answers with "
            "manufacturer byte 65 any more, so whatever took it is either a "
            "matcher that ignores its argument or the SP-404's layer back" % stray)

    # --- `seen`, once per active source, ever (item 302) --------------------
    # Exactly one, not at least one: a publish per reply passes any non-zero test.
    allbus = [m for v in bus.values() for m in v]
    for src in ("m_launchpad", "m_nano", "m_streich"):
        n = allbus.count("seen %s" % src)
        A.check("⛔ %s publishes `seen` EXACTLY ONCE across the whole run" % src,
                n == 1,
                "saw %d. Zero means the diag screen can never tell this device "
                "apart from one that has never answered; more than one means it "
                "publishes per reply, which is a message every two seconds "
                "forever" % n)
    # Each layer's first reply lands in a window of its own, so a `seen` in any
    # other window is published on a poll rather than on an answer.
    first = {src: [w for w in MARKS if ("seen %s" % src) in bus.get(w, [])]
             for src in ("m_nano", "m_launchpad", "m_streich")}
    A.check("⛔ ...and a device says it on its FIRST reply, not before",
            first == {"m_nano": ["FOREIGN"], "m_launchpad": ["OWN-REPLY"],
                      "m_streich": ["WALDORF"]},
            "`seen` landed in %s, wanted m_nano's in FOREIGN, m_launchpad's in "
            "OWN-REPLY and m_streich's in WALDORF, where each first answers. Earlier is "
            "a `seen` on a poll, and every device on a Mac would then read as present"
            % first)

    # --- the Streichfett is polled, on its own port ---------------------------
    # The inquiry leaves m_streich's [midiout] on port 3, worked out from its
    # channel block, once a tick: whole inquiries and nothing else, since nothing
    # else in Cut It talks to that port in this run.
    port3, cur = [], None
    for line in cap.splitlines():
        m = G.MIDI_RE.match(line.strip())
        if not m or int(m.group(2)) != STREICH_PORT:
            continue
        b = int(m.group(1))
        if b == 240:
            cur = [b]
        elif cur is not None:
            cur.append(b)
            if b == 247:
                port3.append(cur)
                cur = None
    ticks = sum(v.count("tick") for v in bus.values())
    A.check("⛔ the Streichfett is polled: the identity request leaves on port 3, one a tick",
            port3 and all(f == INQUIRY for f in port3) and ticks - 1 <= len(port3) <= ticks,
            "%d frame(s) on port 3 for %d ticks, %d of them the inquiry. None means "
            "m_streich never asks, and its device would read as never seen while it "
            "answers every request it gets" % (len(port3), ticks,
                                               sum(1 for f in port3 if f == INQUIRY)))

    # --- one bound, not one per device --------------------------------------
    total = sum(v.count("wire.sh") for v in by.values())
    # Six: u_init's boot fork, three scheduled, one trailing and the phone's.
    A.check("⛔ %d sources lost together produce ONE re-wire per interval" % ACTIVE,
            total == 6,
            "saw %d wire.sh fork(s), wanted u_init's boot fork plus three "
            "recoveries plus one trailing plus the phone's one. %d would be one "
            "per lost source per "
            "interval, which is "
            "what the recovery did before Phase 4 moved it out of m_launchpad "
            "and into u_present -- a copy of a bound per device is not a bound. Fewer "
            "than 6 means the interval, the loss test, the trailing fork or the "
            "phone's request has gone"
            % (total, 1 + 3 * ACTIVE))

    A.note("wire.sh by window: %s"
           % " ".join("%s=%d" % (m, wire_in(by, m)) for m in MARKS))
    A.note("device-lost warnings: %s"
           % " ".join("%s=%s" % (s, lost_in(errs, s, *MARKS) or "never")
                      for s in ("m_launchpad", "m_nano", "m_streich")))
    A.note("%d lighting frame(s), %d mode frame(s)"
           % (len([f for f in frames if f.is_lighting]),
              len([f for f in frames if f.is_mode])))
    return True


def bound_run(cap):
    """The second run: the bound, reached. -> keep going?

    At the shipped tick counter 33 is 72 s away; scaled, it is at 7.2 s. So this
    run checks that the give-up reports, that there are exactly eight attempts,
    and that nothing forks after: [moses 33] stops the forks while the counter
    keeps counting, which only an empty window shows.
    """
    by = by_window(cap, SHELL_RE, tag="BOUND")
    errs = by_window(cap, ERR_RE, tag="BOUND")

    A.windows(cap, "BOUND", len(BOUND_MARKS))

    # The first run's liveness witnesses again: this is a second copy with its
    # own stub, and a copy that never loaded also "forks nothing afterwards".
    quiet = sorted(s for v in by.values() for s in v
                   if s not in ("wire.sh", "wire-watch.sh"))
    if not A.check("⛔ the shell stub is installed in the scaled copy too",
                   quiet == LOADBANG_SCRIPTS,
                   "saw %s, wanted one each of codec-gain.sh, logroll.sh, "
                   "phone-ip.sh and state-dir.sh. This is a SECOND scratch copy and it gets its "
                   "own stub; without it every fork count below is answered by "
                   "silence" % (quiet,)):
        return False

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

    # --- the bound is reached -----------------------------------------------
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

    # --- eight attempts, at the shipped counts ------------------------------
    total = sum(v.count("wire.sh") for v in by.values())
    A.check("⛔ exactly 8 recovery forks, on top of u_init's boot one",
            total == BOUND_TOTAL,
            "saw %d wire.sh fork(s), wanted %d -- u_init's one at 1500 ms plus "
            "attempts at counter 4, 8 ... 32. Fewer means the give-up count is "
            "smaller than it ships; more means [moses] is not stopping them"
            % (total, BOUND_TOTAL))

    # One fewer than the forks: u_init's boot fork is not u_present's and must
    # not be reported, so a report tapped on the wrong side would match the forks.
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

    # --- and it stops dead -------------------------------------------------
    # Counters 36 and 40 fall in AFTER, where mod 4 would fire had the bound been
    # widened rather than reached.
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
    """The second capture, named by --bound. Its absence is a failure, as in
    lib_assert.require_capture."""
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
    # The second run is judged either way: it is a separate Pd on a separate
    # copy, and skipping it would shrink the tally.
    cap = _bound_capture()
    if cap is not None:
        bound_run(cap)
    return A.report()


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
