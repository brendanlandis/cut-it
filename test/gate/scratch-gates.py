#!/usr/bin/env python3
"""What each gate that runs a scratch copy of the patch copies, rewrites, drives
and reads -- one recipe per gate, on test/gate/lib_scratch.py.

    python3 test/gate/scratch-gates.py <gate> [-v] [--keep]

⚠️ RUN IT THROUGH test/gate/<gate>-assert.sh. That is the path test/runner/gates.py
and every ref/ page names; the shell file keeps the gate's header and hands over
to the recipe here. -v reaches the analyzer and shows the detail behind every
check; --keep leaves the scratch directories, the drivers and the captures.

WHY ONE FILE. The seventeen shell wrappers this replaced repeated the same 30-60
lines and differed only in required files, extra map rows, a port and the
watchdog -- so three of them dropped -v without anyone noticing, and the t_shell
install was pasted five times. What a gate does differently is all a recipe
says; everything they share is lib_scratch's.
"""
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_scratch as S                                          # noqa: E402

GEN = "test/gate/%s-drive-gen.py"
FLAGS = ("-nogui", "-noaudio", "-nomidi")


class Gate:
    """One run of one gate: its arguments, its copies, and their cleanup."""

    def __init__(self, name, argv):
        self.name = name
        self.keep = "--keep" in argv
        self.args = [a for a in argv if a != "--keep"]
        self.dirs = []

    def copy(self, name=None, src="Cut It"):
        """A fresh scratch copy of src, made, under TMPDIR/cutit-<name>-<pid>."""
        s = S.Scratch(S.work_dir(name or self.name), src)
        self.dirs.append(s.work)
        return s.make()

    def rewrite(self, s, spec=None, out=None):
        """midi_rewrite, and a count that does not match stops the gate."""
        if not s.midi_rewrite(spec, out):
            if out:
                print("\n".join(out))
            sys.exit(2)

    def pd(self, s, dog, *files):
        """Pd on files with this copy on its path; -> the capture's path."""
        cap = s.path("capture.txt")
        S.run(cap, dog, *FLAGS, "-path", s.patch, *files)
        return cap

    def analyze(self, script, *args, stdin=None):
        """The analyzer, as its own process: it keeps its own tally."""
        sys.stdout.flush()
        with open(stdin, "rb") if stdin else open(os.devnull, "rb") as fh:
            return subprocess.call([sys.executable, script] + list(args),
                                   stdin=fh, cwd=S.ROOT)

    def close(self):
        S.close()
        if self.keep:
            if self.dirs:
                print("kept " + " ".join(self.dirs))
        else:
            for d in self.dirs:
                shutil.rmtree(d, ignore_errors=True)


def main_dev(s):
    return os.path.join(s.patch, "main-dev.pd")


# ---------------------------------------------------------------------------
def _instrument(g, dog, rows=(), say=None):
    """The shape most gates share: main-dev.pd in a copy that owns its state and
    port, every MIDI class rewritten, the gate's driver beside it. -> capture."""
    s = g.copy()
    s.state_dir()
    if rows:
        s.map_rows(rows)
    g.rewrite(s)
    S.drive(GEN % (g.name + "-assert"), s.path("drive.pd"))
    if say:
        print(say)
    return g.pd(s, dog, main_dev(s), s.path("drive.pd"))


def _stdin_gate(g, dog, blank=False, **kw):
    cap = _instrument(g, dog, **kw)
    if blank:
        print()
    return g.analyze("test/gate/%s-assert.py" % g.name, *g.args, stdin=cap)


# ⚠️ THE REWRITE IS NOT FOR THESE GATES' BENEFIT -- u_err, g_oled, g_led and
# m_organelle emit no MIDI. It runs because every scratch-copy gate enforces the
# whole inventory, so a new emitter cannot be added anywhere without some gate
# going red.
#
# ⛔ err AND oled ARE THE TWO THAT READ WHAT A DEAD u_net SOCKET RAISES. A
# `warn u_net net-link-down` takes the OLED footer and lands in the error log,
# failing either gate on whichever window it hits, for a reason that has nothing
# to do with what it tests. state_dir's sink is what keeps it out of every
# gate: each of these two once bound a sink of its own on 9992 and 9993 on top
# of it, and that second one was redundant from the day state_dir got its own.
def err(g):
    S.require("Cut It/u_err.pd")
    return _stdin_gate(g, 30)


def oled(g):
    S.require("Cut It/g_oled.pd")
    return _stdin_gate(g, 55)


def led(g):
    S.require("Cut It/g_led.pd")
    return _stdin_gate(g, 30)


def organelle(g):
    S.require("Cut It/m_organelle.pd")
    return _stdin_gate(g, 30)


def nano(g):
    # ⛔ m_404 AND m_launchpad ARE REQUIRED HERE TOO, and not by accident: the
    # last two windows drive their channel blocks through the same t-ctlin, which
    # is what gives "the nano's channel produces nothing of theirs" a liveness
    # witness.
    S.require("Cut It/m_nano.pd", "Cut It/m_404.pd", "Cut It/m_launchpad.pd",
              "test/stubs/t_ctlin.pd")
    return _stdin_gate(g, 40)


def sp404(g):
    S.require("Cut It/m_404.pd", "Cut It/cut-it-map.txt")
    # All sixteen pads of bank A, plus one in bank C -- the bank is what chooses
    # the channel, and a gate that only ever drove bank A could not see that.
    rows = ["mode-1 gk-p%d 404-pad %d" % (n, n) for n in range(1, 17)]
    rows.append("mode-1 gk-pc1 404-pad 33")
    return _stdin_gate(g, 40, rows=rows)


def volca(g):
    S.require("Cut It/m_volca.pd", "Cut It/cut-it-map.txt")
    return _stdin_gate(g, 40, rows=["mode-1 gk-cc volca-cc 41",
                                    "mode-1 gk-note volca-note 48",
                                    "mode-1 gk-prog volca-prog 5",
                                    "mode-1 gk-key volca-key 60"])


def display(g):
    S.require("Cut It/g_grid.pd", "Cut It/g_oled.pd", "Cut It/main-dev.pd")
    return _stdin_gate(g, 90, blank=True, say="   running (about 46 s -- DSP is "
                       "on, the beat row needs it) ...")


def launchpad(g):
    S.require("Cut It/m_launchpad.pd", "Cut It/main-dev.pd")
    return _stdin_gate(g, 40, blank=True)


def tempo(g):
    S.require("Cut It/u_tempo.pd", "Cut It/main-dev.pd")
    return _stdin_gate(g, 60, blank=True, say="   running (about 16 s -- DSP is "
                       "on, the clock is a phasor~) ...")


def init(g):
    S.require("Cut It/u_init.pd", "Cut It/wire.sh", "test/stubs/t_shell.pd")
    s = g.copy()
    s.state_dir()
    s.shell_stub()
    # ⛔ SEED BOTH STATE FILES. The restore is u_init's last outlet, and against
    # empty files it publishes nothing at all -- so "the restore fired" would be
    # answered by silence, which is also what a restore that never fired looks
    # like. ⚠️ manual FIRST in the analyzer's expectation, because u_state
    # replays the manual store before the auto one: the trigger's right outlet
    # fires first.
    with open(os.path.join(s.state, "cut-it-manual.txt"), "w") as fh:
        fh.write("init-mprobe 7\n")
    with open(os.path.join(s.state, "cut-it-auto.txt"), "w") as fh:
        fh.write("init-probe 42\n")
    g.rewrite(s)
    S.drive(GEN % "init-assert", s.path("drive.pd"))
    # ⛔ THE DRIVER LOADS FIRST HERE, AND IT IS THE ONLY GATE THAT DOES. Pd opens
    # these in order, so a driver named second has its [r disp] taps created
    # AFTER main-dev.pd's loadbang has already fired -- and u_init's FIRST stage
    # is at loadbang. Named second, this gate saw four stages instead of five and
    # one midiInGate instead of two, and every one of those absences looked
    # exactly like the patch not doing it. Every other gate gets away with the
    # usual order because its first window opens at 300 ms and it drives what it
    # asserts.
    cap = g.pd(s, 40, s.path("drive.pd"), main_dev(s))
    return g.analyze("test/gate/init-assert.py", *g.args, stdin=cap)


def _harness_gate(g, dog, *gen_args, why):
    """A gate that loads a generated harness rather than main-dev.pd.

    ⚠️ NO state_dir AND NO midi_rewrite, and both omissions are deliberate
    rather than forgotten: there is no `u_root 17 1 /tmp` line to rewrite -- the
    harness is GENERATED -- and nothing in the run reads or asserts a MIDI byte.
    The inventory is enforced by every other copy.

    ⛔ drive() IS TOLD ABOUT THE HARNESS TOO. The generator writes two files,
    and a missing harness is the worst kind of failure: Pd loads a driver that
    talks to nothing and the gate reports a dead subject with total confidence.
    """
    s = g.copy()
    harness = s.path("harness.pd")
    S.drive(GEN % (g.name + "-assert"), s.path("drive.pd"), harness,
            *[a(s) if callable(a) else a for a in gen_args], also=[(harness, why)])
    return s, g.pd(s, dog, harness, s.path("drive.pd"))


def audio(g):
    # ⛔ IT LOADS A HARNESS HOLDING u_root ALONE, NOT main-dev.pd. catch~ must be
    # uniquely defined and u_mother-stub already holds catch~ outL and catch~
    # outR, so a second pair beside it would fail to create and the recording
    # would be silent -- which is also what a broken audio path sounds like.
    # The private state directory is handed to u_root as a creation argument.
    S.require("Cut It/u_root.pd", "Cut It/u_level.pd")
    s, cap = _harness_gate(
        g, 45, lambda s: s.state, lambda s: s.path("out.wav"),
        why=["      Without it nothing instantiates u_root, nothing records, and",
             "      the gate would report a silent audio path rather than a",
             "      broken test."])
    # ⛔ THE ANALYZER READS THE WAV, NOT stdin. It is the only one here that does,
    # because it is the only one whose subject is samples rather than messages.
    # The capture goes with it so u_level's disp reports -- the other file on the
    # page -- can be asserted in the same run.
    return g.analyze("test/gate/audio-assert.py", s.path("out.wav"), cap, *g.args)


def clock(g):
    # ⛔ A HARNESS AND NOT main-dev.pd, and that is the whole shape of it: c_clock
    # publishes on no bus -- its output is four outlets -- so only a [print]
    # wired to an outlet can see it. Three instances, nothing else running.
    S.require("Cut It/c_clock.pd")
    s, cap = _harness_gate(
        g, 40,
        why=["      Without it the driver drives nothing, every count is 0, and",
             "      the gate would report a dead clock rather than a broken test."])
    return g.analyze("test/gate/clock-assert.py", *g.args, stdin=cap)


def debug(g):
    S.require("Cut It Debug/main.pd", "Cut It Debug/wire.sh",
              "Cut It Debug/err-tail.sh", "Cut It Debug/net-probe.sh",
              "Cut It/wire.sh")
    rc = 0
    # ⛔ THE COPY IS CHECKED BEFORE ANY Pd RUNS, and this is the cheapest real
    # check in the file. The debug patch carries its own wire.sh because at a
    # venue the instrument's folder may have been moved or deleted -- that is
    # literally step 5 of the recover bench -- and the two menu directories are
    # separate. But a second INDEPENDENT copy of nine aconnect lines is precisely
    # the drift this project keeps removing, so the copy is allowed and the
    # divergence is not.
    print("=== wire.sh is a copy, not a second implementation ===")
    with open("Cut It/wire.sh", "rb") as a, open("Cut It Debug/wire.sh", "rb") as b:
        same = a.read() == b.read()
    if same:
        print("   identical to Cut It/wire.sh")
    else:
        for ln in ("FAIL: Cut It Debug/wire.sh has diverged from Cut It/wire.sh.",
                   "      The debug patch wires the rig with a COPY so it does not depend",
                   "      on the instrument's folder still existing. Two copies that differ",
                   "      is worse than either: the tool would report a rig wired one way",
                   "      while the instrument wires it another. Copy it across again:",
                   '          cp "Cut It/wire.sh" "Cut It Debug/wire.sh"'):
            print(ln, file=sys.stderr)
        sys.stdout.flush()
        subprocess.call(["diff", "Cut It/wire.sh", "Cut It Debug/wire.sh"],
                        stdout=sys.stderr)
        rc = 2
    s = g.copy(src="Cut It Debug")
    # ⛔ THE DEBUG PATCH'S OWN THREE, NOT THE INSTRUMENT'S TWENTY-ONE. MIDI_EXPECT
    # here would fail on every class the debug patch legitimately does not have,
    # and dropping the count entirely would give back the "not zero" check that
    # let the old phase 6 gate drift from five boxes to six in silence.
    g.rewrite(s, S.MIDI_DEBUG_EXPECT)
    # ⛔ t_shell IS COPIED OVER shell.pd, NOT BESIDE IT, or mac-stubs/shell.pd
    # swallows the fork and the single most important assertion in the file --
    # that the patch wires itself -- is answered by silence.
    s.shell_stub()
    S.drive(GEN % "debug-assert", s.path("drive.pd"))
    cap = g.pd(s, 40, os.path.join(s.patch, "main.pd"), s.path("drive.pd"))
    print()
    if g.analyze("test/gate/debug-assert.py", *g.args, stdin=cap) != 0:
        rc = 1
    return rc


def map_(g):
    S.require("Cut It/u_map.pd", "Cut It/cut-it-map.txt")
    # The gate's own rows, APPENDED so the shipped rows stay under test too. The
    # static lint checks the SHIPPED file; these give the run a destination that
    # exists and one that does not.
    #
    # ⛔ og-knob-2 AND og-knob-3 ARE HERE FOR PICKUP, and they must be DISTINCT
    # CC numbers. Both windows send two values to a knob and count what comes
    # out -- one expects exactly one event and the other expects two -- so a leak
    # between them has to be visible as a different controller, not as a
    # duplicate.
    #
    # ⚠️ gk-note, gk-pad AND gk-prog EXIST ONLY FOR THE SCREEN. Every value
    # destination draws its own row on disp through a c_mapped instance, and the
    # shipped map reaches only tempo and volca-cc -- so without these three rows
    # the note, pad and program rows would never be exercised by anything.
    #
    # ⚠️ pad-13-at is PRESSURE, MAPPED, so the exemption is proven to be about
    # the RAW row only: a pressure name the mode maps must still draw its
    # destination's.
    rows = ["mode-1 gk-cc volca-cc 41",
            "mode-1 gk-bad no-such-destination 0",
            "mode-1 og-knob-2 volca-cc 42",
            "mode-1 og-knob-3 volca-cc 43",
            "mode-1 og-knob-4 volca-cc 44",
            "mode-1 gk-note volca-note 60",
            "mode-1 gk-pad 404-pad 5",
            "mode-1 gk-prog volca-prog 20",
            "mode-1 pad-13-at volca-cc 45"]

    # ⛔ THE GATE RUNS TWICE, AND THE ONLY DIFFERENCE IS ONE FILE. Pickup arms a
    # knob because mother replayed a SAVED position; it must NOT arm when mother
    # pushed the knob's LIVE position, which is what happens when no Save has
    # ever run. u_map tells the two apart by reading knobs.txt at load, so the
    # branch is selected here by creating that file or not -- the real path
    # either way, on both machines, with no stub answering for it. Item 239.
    #
    # ⚠️ TWO COPIES, NOT ONE REUSED. u_state restores at about 3.5 s from the
    # state directory the run before it wrote, and that is item 232 -- a mode
    # left behind changes what the map does mid-run and half the windows go quiet.
    caps, inventory = [], []
    for which in ("save", "nosave"):
        s = g.copy("map-" + which)
        s.state_dir()
        s.map_rows(rows)
        out = []
        g.rewrite(s, out=out)
        inventory = inventory or out
        if which == "save":
            with open(os.path.join(s.patch, "knobs.txt"), "w") as fh:
                fh.write("0.0957967 0.5 0.5 0.5;\n")
        S.drive(GEN % "map-assert", s.path("drive.pd"))
        caps.append(g.pd(s, 40, main_dev(s), s.path("drive.pd")))
        if which == "save":
            print("\n".join(inventory))
    return g.analyze("test/gate/map-assert.py", *g.args, "--nosave", caps[1],
                     stdin=caps[0])


def recover(g):
    S.require("Cut It/u_map.pd", "Cut It/u_init.pd", "Cut It/recover.sh",
              "test/stubs/t_shell.pd")
    # ⛔ TWO RUNS, TWO COPIES, AND THE ONLY DIFFERENCE IS WHAT IS ON DISK. Run A
    # boots clean and drives the button. Run B boots with a breadcrumb already
    # there -- the state the next boot after a real recover is in. ⚠️ Never one
    # copy reused: u_state restores at about 3.5 s from the state directory the
    # previous run wrote, and a leftover mode changes what the map does mid-run.
    # Item 232.
    copies = {}
    for which in ("a", "b"):
        s = copies[which] = g.copy("recover-" + which)
        s.state_dir()
        s.shell_stub()
        crumb = os.path.join(s.state, "cut-it-recover.txt")
        if which == "b":
            # ⛔ THE ONLY DIFFERENCE BETWEEN THE RUNS. An armed breadcrumb, and a
            # knobs.txt beside it so that pickup has something to arm -- without
            # the second file nothing would be held even without a breadcrumb,
            # and the override would be proved by a knob that was never captured.
            with open(crumb, "w") as fh:
                fh.write("recover 8123.4\n")
            with open(os.path.join(s.patch, "knobs.txt"), "w") as fh:
                fh.write("0.0957967 0.5 0.5 0.5;\n")
        else:
            open(crumb, "w").close()
        out = []
        g.rewrite(s, out=out)
        S.drive(GEN % "recover-assert", s.path("drive.pd"), which)
        g.pd(s, 40, main_dev(s), s.path("drive.pd"))
        if which == "a":
            print("\n".join(out))
    a, b = copies["a"], copies["b"]
    return g.analyze("test/gate/recover-assert.py", *g.args,
                     "--runb", b.path("capture.txt"),
                     "--crumb", os.path.join(b.state, "cut-it-recover.txt"),
                     "--crumb-a", os.path.join(a.state, "cut-it-recover.txt"),
                     stdin=a.path("capture.txt"))


def presence(g):
    # g_grid is required and not by accident: it is the only readable evidence
    # of surface OWNERSHIP. m_launchpad keeps that in a $0- send, so the one way
    # to see it from outside is that the grid does or does not paint.
    S.require("Cut It/m_launchpad.pd", "Cut It/g_grid.pd", "Cut It/wire.sh",
              "test/stubs/t_shell.pd", "test/stubs/t_sysexin.pd")
    s = g.copy()
    s.state_dir()
    # ⛔ THE HEARTBEAT FIRES EVERY TICK IN THIS COPY, so "it runs while nothing is
    # lost" is observable in every window rather than wherever 16 s happens to
    # land in a 40 s run. The SHIPPED interval is asserted statically.
    s.watch_fast()
    # The re-wires are the entire subject, so the counting shell stub.
    s.shell_stub()
    g.rewrite(s)
    S.drive(GEN % "presence-assert", s.path("drive.pd"))
    print("   running the schedule (about 38 s -- the three re-wires are at "
          "14 s, 22 s and 30 s) ...")
    cap = g.pd(s, 60, main_dev(s), s.path("drive.pd"))

    # ⛔ THE SECOND RUN, AND IT IS THE ONLY ONE THAT REACHES THE BOUND. The run
    # above proves the INTERVAL and the COALESCING inside 38 s; it never sees
    # tick 33, because at the shipped tick the give-up is 72 seconds away.
    #
    # ⛔ A SECOND COPY, NOT THE FIRST ONE REWRITTEN. Scaling u_root.pd would change
    # the patch the run above is being judged against; and the run above sets a
    # mode, u_state flushes it, and u_init would restore it into this run at what
    # is now the middle of the recovery -- item 232.
    #
    # ⚠️ THE FULL REWRITE, EVEN THOUGH THIS RUN DRIVES NO MIDI AT ALL, so the
    # second copy enforces MIDI_EXPECT exactly like the first and a new emitter
    # cannot slip in behind a gate that happens to make two copies.
    s2 = g.copy("presence-bound")
    s2.state_dir()
    s2.scale_present()
    s2.shell_stub()
    g.rewrite(s2)
    S.drive("test/gate/presence-bound-drive-gen.py", s2.path("drive.pd"))
    print("   running the bound (about 9 s -- the eighth fork is at 7 s and the "
          "give-up at 7.2) ...")
    cap2 = g.pd(s2, 30, main_dev(s2), s2.path("drive.pd"))
    print()
    return g.analyze("test/gate/presence-assert.py", *g.args, "--bound", cap2,
                     stdin=cap)


RECIPES = {
    "init": init, "presence": presence, "audio": audio, "err": err,
    "display": display, "oled": oled, "led": led, "tempo": tempo,
    "clock": clock, "map": map_, "recover": recover, "launchpad": launchpad,
    "nano": nano, "organelle": organelle, "sp404": sp404, "volca": volca,
    "debug": debug,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in RECIPES:
        S.fail("usage: scratch-gates.py <%s> [-v] [--keep]" % "|".join(RECIPES))
    sys.stdout.reconfigure(line_buffering=True)
    os.chdir(S.ROOT)
    g = Gate(sys.argv[1], sys.argv[2:])
    S.require_pd()
    rc = 2
    try:
        rc = RECIPES[g.name](g)
    finally:
        g.close()
    sys.exit(rc)


if __name__ == "__main__":
    main()
