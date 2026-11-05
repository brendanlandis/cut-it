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
    S.require("Cut It/g_grid.pd", "Cut It/g_grid.lua", "Cut It/g_grid-lua.pd_lua",
              "Cut It/cut-it-drum-page.txt", "Cut It/g_oled.pd", "Cut It/main-dev.pd",
              "test/gate/lua/g_grid_test.lua")
    # The drum page's painter first, in Lua and without Pd: what each cell shows. Then the Pd
    # half: the arbiter and every page, the drum page's frames included, through the running
    # instrument.
    print("   the drum page's painter, in Lua ...")
    rc_lua = S.lua("test/gate/lua/g_grid_test.lua", *g.args)
    print("\n   the patch, in Pd ...")
    rc = _stdin_gate(g, 90, blank=True, say="   running (about 46 s -- DSP is "
                     "on, the beat row needs it) ...")
    return rc or rc_lua


def launchpad(g):
    S.require("Cut It/m_launchpad.pd", "Cut It/main-dev.pd")
    return _stdin_gate(g, 40, blank=True)


def tempo(g):
    S.require("Cut It/u_tempo.pd", "Cut It/u_tempo.lua", "Cut It/u_tempo-lua.pd_lua",
              "Cut It/cut-it-arrangement-page.txt", "Cut It/main-dev.pd",
              "test/gate/lua/u_tempo_test.lua")
    # Tap tempo's rules first, in Lua and without Pd: the intervals, the gap, the clamp. Then
    # the Pd half: the clock, the clamp and the transport, the tap pad and the phone's tempo
    # through the running instrument.
    print("   tap tempo's rules, in Lua ...")
    rc_lua = S.lua("test/gate/lua/u_tempo_test.lua", *g.args)
    print("\n   the patch, in Pd ...")
    rc = _stdin_gate(g, 60, blank=True, say="   running (about 24 s -- DSP is "
                     "on, the clock is a phasor~) ...")
    return rc or rc_lua


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
    S.require("Cut It/u_root.pd", "Cut It/c_kit.pd",
              "Cut It/cut-it-drum-page.txt")
    # Its u_root holds u_net, so its OSC goes to a sink here, not to the phone. The
    # generator writes pad 1's sample into the copy's samples/drums, as kit's does.
    s, cap = _harness_gate(
        g, 45, lambda s: s.state, lambda s: s.path("out.wav"), lambda s: s.patch,
        prep=lambda s: s.net_off(),
        why=["      Without it nothing instantiates u_root, nothing records, and",
             "      the gate would report a silent audio path rather than a",
             "      broken test."])
    # The analyzer reads the wav, and the capture's disp tap: no level is reported.
    return g.analyze("test/gate/audio-assert.py", s.path("out.wav"), cap, *g.args)


def kit(g):
    # A harness holding c_kit alone, with three samples the generator writes into
    # the copy's samples/drums: lib_scratch leaves the Mac's own out, so the run
    # hears these and nothing else.
    S.require("Cut It/c_kit.pd", "Cut It/c_voice.pd", "Cut It/u_root.pd")
    s, cap = _harness_gate(
        g, 40, lambda s: s.patch, lambda s: s.path("out.wav"),
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
SEQ_VOL = {16: -12}
SEQ_PITCH = {3: 5}
SEQ_SIG = (7, 8)
# Effects off their starting points, so the seed is the 711-number line and the restore tells
# c_kit them (c_steps.lua's R.FX, its first R.FX_BLOCK, those the 711 holds, in its order, each
# with its starting point; every track soft, as a line saved before the characters): track 2's
# distortion mixed in at 40, track 5's delay a dotted quarter at 30, track 9's send at 60, and
# the reverb's size 70.
SEQ_FX = [("drive", 50, {}), ("tone", 100, {}), ("dist", 0, {2: 40}), ("note", 3, {5: 2}),
          ("feel", 1, {5: 3}), ("feedback", 40, {}), ("delay", 0, {5: 30}), ("send", 0, {9: 60})]
SEQ_VERB = [("size", 50, 70), ("damping", 50, 50)]


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
    # A saved song whose one section holds a pattern, so the restore at ~3.5 s is under test
    # as well as the edits after it, and its last cells, track 16's own last step and volume,
    # track 3's pitch, a time signature of 7/8, the swing at 50% and the global last step at
    # 16, and its effects, prove the whole 711-atom line came back. No randomness and sober, so
    # every note is where the pattern says. The knobs start held where the seed has them.
    pat = [0] * 581
    for (track, step), v in SEQ_SEED.items():
        pat[(track - 1) * 32 + step - 1] = v
    for track, n in SEQ_OWN.items():
        pat[512 + track - 1] = n
    for track, db in SEQ_VOL.items():
        pat[544 + track - 1] = db
    for track, st in SEQ_PITCH.items():
        pat[560 + track - 1] = st
    pat[576], pat[577] = SEQ_SIG
    pat[579], pat[580] = 50, 16
    for _name, start, moved in SEQ_FX:
        pat += [moved.get(t, start) for t in range(1, 17)]
    pat += [v for _name, _start, v in SEQ_VERB]
    drums = "drums %s\n" % " ".join(map(str, pat))
    # Page 2, the drum page, restored at about 3.5 s by u_state, and the song by u_song after
    # it, before the first press.
    with open(os.path.join(s.state, "cut-it-auto.txt"), "w") as fh:
        fh.write("mode mode-2\n")
    song = "song song 1\nsection 1 0 section 1\n" + drums
    for name in ("cut-it-song.txt", "cut-it-song-draft.txt"):
        with open(os.path.join(s.state, name), "w") as fh:
            fh.write(song)
    with open(s.path("seed.txt"), "w") as fh:
        fh.write(drums)
    g.rewrite(s)
    # The drums go to c_kit, a signal no message tap sees: t_kit in its place
    # prints each pad and velocity c_steps sends, and each track's volume and
    # pitch (test/stubs/t_kit.pd).
    root = os.path.join(s.patch, "u_root.pd")
    with open(root) as fh:
        text = fh.read()
    if text.count(" c_kit;") != 1:
        S.fail("FAIL: u_root.pd holds %d c_kit boxes, wanted 1 to swap for t_kit."
               % text.count(" c_kit;"))
    with open(root, "w") as fh:
        fh.write(text.replace(" c_kit;", " t_kit;"))
    S.drive(GEN % "sequencer-assert", s.path("drive.pd"))
    print("   running (about 37 s -- DSP is on, the steps are cut from a phasor~) ...")
    cap = g.pd(s, 47, main_dev(s), s.path("drive.pd"))
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
    # Page 3, and a song whose one section holds strings and the velocity switch off,
    # restored at about 3.5 s: fm and on are the boot defaults, so a restore that never landed
    # plays the Volca at the key's own velocity in the first window.
    with open(os.path.join(s.state, "cut-it-auto.txt"), "w") as fh:
        fh.write("mode mode-3\n")
    for name in ("cut-it-song.txt", "cut-it-song-draft.txt"):
        with open(os.path.join(s.state, name), "w") as fh:
            fh.write("song song 1\nsection 1 0 section 1\nsynth strings\nvelocity off\n")
    g.rewrite(s)
    S.drive(GEN % "synths-assert", s.path("drive.pd"))
    cap = g.pd(s, 30, main_dev(s), s.path("drive.pd"))
    print()
    rc = g.analyze("test/gate/synths-assert.py", *g.args, "--state", s.state, stdin=cap)
    return rc or rc_lua


def _drums(last, hits, own=None, sig=(4, 4), drunk=0, sectionless=False):
    """A drum pattern as c_steps saves it: 512 velocities, the tracks' own last steps, their
    randomness, volumes and pitches, the time signature and the drunkenness, then the swing and
    the global last step, 581 numbers; or, sectionless, the 579 it saved before sections."""
    pat = [0] * 581
    for (track, step), v in hits.items():
        pat[(track - 1) * 32 + step - 1] = v
    for track, n in (own or {}).items():
        pat[512 + track - 1] = n
    pat[576], pat[577], pat[578] = sig[0], sig[1], drunk
    pat[579], pat[580] = 50, last
    return pat[:579] if sectionless else pat


# The song the first run's state directory holds, saved and as the draft: intro, verse and
# chorus, each every part a section has (ref/module/songs.md). Verse plays two loops of eight
# steps and hands over; chorus's loop is 32 steps, long enough to watch a queued section blink.
SONG_SEED = [
    ("intro", 0, {"drums": _drums(8, {(1, 1): 95}), "programs": ["none", "none"],
                  "synth": ["fm"], "tempo": [200], "velocity": ["on"]}),
    ("verse", 2, {"drums": _drums(8, {(1, 1): 127, (2, 5): 79}), "programs": [20, 5],
                  "synth": ["strings"], "tempo": [240], "velocity": ["off"]}),
    ("chorus", 0, {"drums": _drums(32, {(1, 1): 111, (1, 17): 111}), "programs": [7, "none"],
                   "synth": ["fm"], "tempo": [180], "velocity": ["on"]}),
]


# The fourth run's songs, by id: each its name, its tempo and its drums' global last step, one
# section; and its setlist, gig, each entry a song and how it starts. Night drive is loaded.
SONGS = {1: ("night drive", 200, 8), 2: ("lantern", 240, 32), 3: ("hollow bell", 220, 32)}
SONGS_INDEX = ("next 4\ncurrent 1\nchosen 1\nsong 1\nsong 2\nsong 3\nset gig\n"
               "entry 2 silence\nentry 3 next-bar\nentry 1 go\n")


def _song_text(sections, name="song 1"):
    out = ["song " + name]
    for i, (name, length, parts) in enumerate(sections, 1):
        out.append("section %d %d %s" % (i, length, name))
        out += ["%s %s" % (k, " ".join(str(a) for a in parts[k])) for k in sorted(parts)]
    return "\n".join(out) + "\n"


def song(g):
    S.require("Cut It/u_song.pd", "Cut It/u_song.lua", "Cut It/u_song-lua.pd_lua",
              "test/gate/lua/u_song_test.lua")
    # The rules first, in Lua and without Pd: the sections, the top row, the bars, the draft
    # against the saved song, the files. Then the Pd half: the store in the running instrument.
    print("   the rules, in Lua ...")
    rc_lua = S.lua("test/gate/lua/u_song_test.lua", *g.args)
    print("\n   the patch, in Pd ...")
    s = g.copy()
    s.state_dir()
    # Page 2, so the frames show the drum page's playhead, and a song saved.
    with open(os.path.join(s.state, "cut-it-auto.txt"), "w") as fh:
        fh.write("mode mode-2\n")
    text = _song_text(SONG_SEED)
    for path in (os.path.join(s.state, "cut-it-song.txt"),
                 os.path.join(s.state, "cut-it-song-draft.txt"), s.path("seed-song.txt")):
        with open(path, "w") as fh:
            fh.write(text)
    g.rewrite(s)
    for run in ("play", "reload"):
        S.drive(GEN % "song-assert", s.path("drive-%s.pd" % run), run)
    print("   running the song (about 15 s), then a reload of it (about 6) ...")
    cap = s.path("capture-play.txt")
    S.run(cap, 40, *FLAGS, "-path", s.patch, main_dev(s), s.path("drive-play.pd"))
    after = s.path("after-play")
    os.makedirs(after)
    for name in ("cut-it-song.txt", "cut-it-song-draft.txt"):
        if os.path.exists(os.path.join(s.state, name)):
            shutil.copy(os.path.join(s.state, name), after)
    cap2 = s.path("capture-reload.txt")
    S.run(cap2, 30, *FLAGS, "-path", s.patch, main_dev(s), s.path("drive-reload.pd"))
    # A state directory from before sections: the drum pattern and the synth choice in the auto
    # file, as Cut It wrote them, and no song. Its own copy, booted once.
    s3 = g.copy("song-legacy")
    s3.state_dir()
    old = _drums(16, {(1, 1): 111, (3, 9): 64}, own={16: 24}, sig=(3, 4), drunk=10,
                 sectionless=True)
    line = "section-1-drums %s" % " ".join(map(str, old))
    with open(os.path.join(s3.state, "cut-it-auto.txt"), "w") as fh:
        fh.write("mode mode-4\n%s\nsynth strings\nvelocity off\n" % line)
    with open(s3.path("legacy-seed.txt"), "w") as fh:
        fh.write(line + "\n")
    g.rewrite(s3, out=[])
    S.drive(GEN % "song-assert", s3.path("drive.pd"), "legacy")
    print("   and a first load from a state directory before sections (about 6 s) ...")
    S.run(s3.path("capture.txt"), 30, *FLAGS, "-path", s3.patch, main_dev(s3), s3.path("drive.pd"))
    # Three songs and a setlist saved, on page 8, the songs: the keys and go, stopped and playing.
    s4 = g.copy("song-songs")
    s4.state_dir()
    with open(os.path.join(s4.state, "cut-it-auto.txt"), "w") as fh:
        fh.write("mode mode-8\n")
    with open(os.path.join(s4.state, "cut-it-songs.txt"), "w") as fh:
        fh.write(SONGS_INDEX)
    for sid, (name, tempo, last) in SONGS.items():
        text = _song_text([("section 1", 0, {"drums": _drums(last, {(1, 1): 100}),
                                             "programs": ["none", "none"], "synth": ["fm"],
                                             "tempo": [tempo], "velocity": ["on"]})], name)
        names = ("cut-it-song.txt", "cut-it-song-draft.txt") if sid == 1 else (
            "cut-it-song-%d.txt" % sid, "cut-it-song-%d-draft.txt" % sid)
        for n in names:
            with open(os.path.join(s4.state, n), "w") as fh:
                fh.write(text)
    g.rewrite(s4, out=[])
    S.drive(GEN % "song-assert", s4.path("drive.pd"), "songs")
    print("   and three songs, played from the Organelle's keys and go (about 14 s) ...")
    cap4 = s4.path("capture.txt")
    S.run(cap4, 40, *FLAGS, "-path", s4.patch, main_dev(s4), s4.path("drive.pd"))
    print()
    rc = g.analyze("test/gate/song-assert.py", *g.args, "--seed", s.path("seed-song.txt"),
                   "--state", s.state, "--after", after, "--reload", cap2,
                   "--legacy", s3.state, "--legacy-seed", s3.path("legacy-seed.txt"),
                   "--songs", cap4, "--songs-state", s4.state, stdin=cap)
    return rc or rc_lua


RECIPES = {
    "init": init, "presence": presence, "audio": audio, "err": err,
    "display": display, "oled": oled, "led": led, "tempo": tempo,
    "clock": clock, "map": map_, "recover": recover, "launchpad": launchpad,
    "nano": nano, "organelle": organelle, "volca": volca,
    "debug": debug, "sequencer": sequencer, "kit": kit, "synths": synths, "song": song,
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
