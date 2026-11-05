#!/usr/bin/env python3
"""What each gate that runs a scratch copy of the patch copies, rewrites, drives
and reads -- one recipe per gate, on test/gate/lib_scratch.py.

    python3 test/gate/scratch-gates.py <gate> [-v] [--keep]

Run it through test/gate/<gate>-assert.sh, the path test/runner/gates.py and
the ref/ pages name. -v reaches the analyzer and shows the detail behind every
check; --keep leaves the scratch directories, the drivers and the captures.
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


# These four emit no MIDI; the rewrite runs anyway, to enforce the inventory.
# err and oled were the two a dead u_net socket failed under Pd 0.49 (its
# net-link-down warning, gone since 2026-11-03); state_dir's sink is kept.
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
    S.require("Cut It/m_organelle.pd", "Cut It/m_organelle.lua",
              "Cut It/m_organelle-lua.pd_lua", "test/gate/lua/m_organelle_test.lua")
    # The keyboard's rules first, in Lua and without Pd: each key's name and the layer it
    # latched. Then the Pd half: mother's names through the running instrument.
    print("   the keyboard's rules, in Lua ...")
    rc_lua = S.lua("test/gate/lua/m_organelle_test.lua", *g.args)
    print("\n   the patch, in Pd ...")
    return _stdin_gate(g, 30) or rc_lua


def nano(g):
    # m_launchpad too: the last two windows drive its channel and Pd's port 3's
    # through the same t-ctlin, the witness that the nano's produces none of theirs.
    S.require("Cut It/m_nano.pd", "Cut It/m_nano.lua", "Cut It/m_nano-lua.pd_lua",
              "Cut It/m_launchpad.pd", "test/stubs/t_ctlin.pd",
              "test/gate/lua/m_nano_test.lua")
    # The decode first, in Lua and without Pd: every CC's name, value and warning. Then the
    # Pd half: the channel gate and the buses, through the running instrument.
    print("   the decode, in Lua ...")
    rc_lua = S.lua("test/gate/lua/m_nano_test.lua", *g.args)
    print("\n   the patch, in Pd ...")
    return _stdin_gate(g, 40) or rc_lua


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
    return _stdin_gate(g, 60, blank=True, say="   running (about 18 s -- DSP is "
                       "on, the clock is a phasor~) ...")


def init(g):
    S.require("Cut It/u_init.pd", "Cut It/wire.sh", "test/stubs/t_shell.pd")
    s = g.copy()
    s.state_dir()
    s.shell_stub()
    # Both state files seeded, or an empty restore and a restore that never
    # fired look the same. u_state replays manual before auto.
    with open(os.path.join(s.state, "cut-it-manual.txt"), "w") as fh:
        fh.write("init-mprobe 7\n")
    with open(os.path.join(s.state, "cut-it-auto.txt"), "w") as fh:
        fh.write("init-probe 42\n")
    g.rewrite(s)
    S.drive(GEN % "init-assert", s.path("drive.pd"))
    # ⛔ The driver loads first here, alone among the gates: u_init's first stage
    # is at loadbang, and a driver opened second creates its taps after it.
    cap = g.pd(s, 40, s.path("drive.pd"), main_dev(s))
    return g.analyze("test/gate/init-assert.py", *g.args, stdin=cap)


def _harness_gate(g, dog, *gen_args, why, prep=None):
    """A gate that loads a generated harness rather than main-dev.pd.

    No state_dir and no midi_rewrite, on purpose: the harness is generated, so
    there is no main-dev.pd line to repoint, and nothing in the run reads MIDI.
    A harness that holds u_root passes prep=net_off, or its u_net would send to
    the phone.
    drive() checks the harness was written as well as the driver.
    """
    s = g.copy()
    if prep:
        prep(s)
    harness = s.path("harness.pd")
    S.drive(GEN % (g.name + "-assert"), s.path("drive.pd"), harness,
            *[a(s) if callable(a) else a for a in gen_args], also=[(harness, why)])
    return s, g.pd(s, dog, harness, s.path("drive.pd"))


def audio(g):
    # A harness holding u_root alone, not main-dev.pd: catch~ must be unique and
    # u_mother-stub already holds catch~ outL and outR, so a second pair would
    # fail to create and record silence. The state directory is u_root's arg.
    S.require("Cut It/u_root.pd", "Cut It/u_level.pd")
    # Its u_root holds u_net, so its OSC goes to a sink here, not to the phone.
    s, cap = _harness_gate(
        g, 45, lambda s: s.state, lambda s: s.path("out.wav"), prep=lambda s: s.net_off(),
        why=["      Without it nothing instantiates u_root, nothing records, and",
             "      the gate would report a silent audio path rather than a",
             "      broken test."])
    # The analyzer reads the wav, and the capture for u_level's disp reports.
    return g.analyze("test/gate/audio-assert.py", s.path("out.wav"), cap, *g.args)


def kit(g):
    # A harness holding c_kit alone, with two samples the generator writes into
    # the copy's samples/drums: lib_scratch leaves the Mac's own out, so the run
    # hears these and nothing else.
    S.require("Cut It/c_kit.pd", "Cut It/c_voice.pd", "Cut It/u_root.pd")
    s, cap = _harness_gate(
        g, 30, lambda s: s.patch, lambda s: s.path("out.wav"),
        why=["      Without it nothing instantiates c_kit, nothing records, and",
             "      the gate would report a silent kit rather than a broken test."])
    return g.analyze("test/gate/kit-assert.py", s.path("out.wav"), *g.args, stdin=cap)


def clock(g):
    # A harness: c_clock publishes on no bus, so only a [print] on an outlet
    # sees it. Three instances, nothing else running.
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
    # The debug patch's wire.sh is a copy, so it works with the instrument's
    # folder gone (AGENTS.md); the copy may not diverge.
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
    g.rewrite(s, S.MIDI_DEBUG_EXPECT)
    s.shell_stub()
    S.drive(GEN % "debug-assert", s.path("drive.pd"))
    cap = g.pd(s, 40, os.path.join(s.patch, "main.pd"), s.path("drive.pd"))
    print()
    if g.analyze("test/gate/debug-assert.py", *g.args, stdin=cap) != 0:
        rc = 1
    return rc


def map_(g):
    S.require("Cut It/u_map.pd", "Cut It/u_map.lua", "Cut It/u_map-lua.pd_lua",
              "Cut It/cut-it-map.txt", "test/gate/lua/u_map_test.lua")
    # The rules first, in Lua and without Pd: the table, the lookup, pickup and the raw row.
    # Then the Pd half: the patch around them, running.
    print("   the rules, in Lua ...")
    rc_lua = S.lua("test/gate/lua/u_map_test.lua", *g.args)
    print("\n   the patch, in Pd ...")
    # Put before the shipped rows, so each wins over a shipped row for the same
    # mode and control. gk-bad names a
    # destination that does not exist. The pickup knobs get distinct CCs, so a
    # leak between their windows shows as the wrong controller rather than a
    # duplicate. gk-note, gk-prog and gk-key exist for what the shipped map
    # never reaches: their disp rows, and a key, since the Organelle's own keys
    # play nothing until they choose songs (Brendan, 2026-11-04).
    # pad-13-at is pressure, mapped: the raw-row exemption must not hide a
    # mapped destination's row.
    rows = ["mode-1 gk-cc volca-cc 41",
            "mode-1 gk-bad no-such-destination 0",
            "mode-1 og-knob-2 volca-cc 42",
            "mode-1 og-knob-3 volca-cc 43",
            "mode-1 og-knob-4 volca-cc 44",
            "mode-1 gk-note volca-note 60",
            "mode-1 gk-prog volca-prog 20",
            "mode-1 gk-key volca-key 60",
            "mode-1 pad-13-at volca-cc 45"]

    # Twice, differing only in knobs.txt: u_map arms pickup for a saved knob
    # position and not for a live one, and tells them apart by that file (item
    # 239). Two copies, never one reused (item 232).
    caps, inventory = [], []
    for which in ("save", "nosave"):
        s = g.copy("map-" + which)
        s.state_dir()
        s.map_rows(rows)
        # A mode the old code saved, <class> <page>: u_map's restore must put the
        # page alone on the bus. Page 1, so the gate's rows, all keyed mode-1,
        # still hold after it lands at about 3.5 s.
        with open(os.path.join(s.state, "cut-it-auto.txt"), "w") as fh:
            fh.write("mode compose mode-1\n")
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
    rc = g.analyze("test/gate/map-assert.py", *g.args, "--nosave", caps[1], stdin=caps[0])
    return rc or rc_lua


def recover(g):
    S.require("Cut It/u_map.pd", "Cut It/u_init.pd", "Cut It/recover.sh",
              "test/stubs/t_shell.pd")
    # Two copies differing only on disk: A boots clean and drives the button, B
    # boots with a breadcrumb, as the boot after a real recover does. Never one
    # copy reused (item 232).
    copies = {}
    for which in ("a", "b"):
        s = copies[which] = g.copy("recover-" + which)
        s.state_dir()
        s.shell_stub()
        crumb = os.path.join(s.state, "cut-it-recover.txt")
        if which == "b":
            # And knobs.txt, or nothing would be held even without a breadcrumb
            # and the override would prove nothing.
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
    # g_grid: whether it paints is the only outside evidence of surface
    # ownership, which m_launchpad keeps in a $0- send.
    S.require("Cut It/m_launchpad.pd", "Cut It/g_grid.pd", "Cut It/wire.sh",
              "test/stubs/t_shell.pd", "test/stubs/t_sysexin.pd")
    s = g.copy()
    s.state_dir()
    s.watch_fast()
    s.shell_stub()
    g.rewrite(s)
    S.drive(GEN % "presence-assert", s.path("drive.pd"))
    print("   running the schedule (about 38 s -- the three re-wires are at "
          "14 s, 22 s and 30 s) ...")
    cap = g.pd(s, 60, main_dev(s), s.path("drive.pd"))

    # The bound, which the run above never reaches (the give-up is 72 s away),
    # in a second copy scaled by scale_present (item 232 again).
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


# The pattern the state directory starts with, as (track, step): velocity, and
# the tracks with a last step of their own. The analyzer reads it back from
# seed.txt rather than holding a second copy.
SEQ_SEED = {(1, 3): 20, (1, 9): 77, (2, 7): 50, (16, 32): 127}
SEQ_OWN = {16: 24}
SEQ_SIG = (7, 8)


def sequencer(g):
    S.require("Cut It/c_steps.pd", "Cut It/c_steps.lua", "Cut It/c_steps-lua.pd_lua",
              "Cut It/cut-it-drum-page.txt", "Cut It/g_grid.pd", "Cut It/u_map.pd",
              "test/gate/lua/c_steps_test.lua")
    # The rules first, in Lua and without Pd: what each press, step and restore
    # answers. Then the Pd half: the patch around them, running.
    print("   the rules, in Lua ...")
    rc_lua = S.lua("test/gate/lua/c_steps_test.lua", *g.args)
    print("\n   the patch, in Pd ...")
    s = g.copy()
    s.state_dir()
    # A saved pattern, so the restore at ~3.5 s is under test as well as the
    # edits after it, and its last cells, track 16's own last step and a time
    # signature of 7/8, prove the whole 564-atom line came back. No chances and
    # sober, so every note is where the pattern says.
    pat = [0] * 563
    for (track, step), v in SEQ_SEED.items():
        pat[(track - 1) * 32 + step - 1] = v
    for track, n in SEQ_OWN.items():
        pat[512 + track - 1] = n
    pat[560], pat[561] = SEQ_SIG
    # Page 2, the drum page, restored at about 3.5 s, before the first press.
    body = "mode mode-2\nsection-1-drums %s\n" % " ".join(map(str, pat))
    for path in (os.path.join(s.state, "cut-it-auto.txt"), s.path("seed.txt")):
        with open(path, "w") as fh:
            fh.write(body)
    g.rewrite(s)
    # The drums go to c_kit, a signal no message tap sees: t_kit in its place
    # prints each pad and velocity c_steps sends (test/stubs/t_kit.pd).
    root = os.path.join(s.patch, "u_root.pd")
    with open(root) as fh:
        text = fh.read()
    if text.count(" c_kit;") != 1:
        S.fail("FAIL: u_root.pd holds %d c_kit boxes, wanted 1 to swap for t_kit."
               % text.count(" c_kit;"))
    with open(root, "w") as fh:
        fh.write(text.replace(" c_kit;", " t_kit;"))
    S.drive(GEN % "sequencer-assert", s.path("drive.pd"))
    print("   running (about 18 s -- DSP is on, the steps are cut from a phasor~) ...")
    cap = g.pd(s, 40, main_dev(s), s.path("drive.pd"))
    print()
    rc = g.analyze("test/gate/sequencer-assert.py", *g.args, "--seed", s.path("seed.txt"),
                   "--state", s.state, stdin=cap)
    return rc or rc_lua


def synths(g):
    S.require("Cut It/c_synth.pd", "Cut It/c_synth.lua", "Cut It/c_synth-lua.pd_lua",
              "Cut It/m_nanokey.pd", "Cut It/m_streich.pd", "Cut It/cut-it-synth-page.txt",
              "Cut It/cut-it-map.txt", "test/gate/lua/c_synth_test.lua")
    # The rules first, in Lua and without Pd: the choice, where each key goes, the restore.
    # Then the Pd half: the nanoKEY, the pads and the phone through the running instrument.
    print("   the rules, in Lua ...")
    rc_lua = S.lua("test/gate/lua/c_synth_test.lua", *g.args)
    print("\n   the patch, in Pd ...")
    s = g.copy()
    s.state_dir()
    # Page 3 and strings saved, restored at about 3.5 s: fm is the boot default, so a
    # restore that never landed plays the Volca in the first window.
    with open(os.path.join(s.state, "cut-it-auto.txt"), "w") as fh:
        fh.write("mode mode-3\nsynth strings\n")
    g.rewrite(s)
    S.drive(GEN % "synths-assert", s.path("drive.pd"))
    cap = g.pd(s, 30, main_dev(s), s.path("drive.pd"))
    print()
    rc = g.analyze("test/gate/synths-assert.py", *g.args, "--state", s.state, stdin=cap)
    return rc or rc_lua


RECIPES = {
    "init": init, "presence": presence, "audio": audio, "err": err,
    "display": display, "oled": oled, "led": led, "tempo": tempo,
    "clock": clock, "map": map_, "recover": recover, "launchpad": launchpad,
    "nano": nano, "organelle": organelle, "volca": volca,
    "debug": debug, "sequencer": sequencer, "kit": kit, "synths": synths,
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
