#!/usr/bin/env python3
"""Every headless check, as data. Imported by run.py.

Mac-side only: no ssh, no deploy, no device, so ./test/run.sh is safe with the
device off. The hands-on checks are test/checklists/ (test/README.md).

The commands are shell strings so `"Cut It"/*.pd` expands in the shell, in the
order it always has.
"""
import concurrent.futures
import os
import shutil
import subprocess
import sys
import tempfile

# lib_scratch says where pdlua and ELSE are, for the deploy gate's Pd as for
# every other gate's.
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "gate"))
import lib_scratch                                              # noqa: E402

# ---------------------------------------------------------------------------
# The table's length is asserted, since a gate dropped in an edit is otherwise
# silent. Update it deliberately, never to make a red run green (as MIDI_EXPECT).
EXPECT = 28

# The gates all run side by side and print whole in table order, so the log
# reads as a serial run's and has one RESULT: line. None waits for another: no
# gate writes inside the repo, so none can read another's half-written file.
# The MIDI inventory prints before the module gates because every one of them
# rewrites the same MIDI boxes, so a drifted count explains them all at once.
GATES = [
    # --- 1. structure ------------------------------------------------------
    ("layout and graph structure",
     'python3 test/gate/pd-layout-check.py "Cut It"/*.pd "Cut It Debug"/*.pd'),

    # --- 1b. the documentation ---------------------------------------------
    ("documentation matches the patch",
     "python3 test/gate/docs-check.py"),

    # --- 2. the deploy gate, _syntax below ---------------------------------
    ("both entry points load in silence (tools/deploy.sh's own gate)", None),

    # --- 3. the MIDI inventory ---------------------------------------------
    ("the MIDI inventory", "./test/gate/midi-emitters-assert.sh"),

    # --- 4. one gate per module --------------------------------------------
    ("the boot sequence", "./test/gate/init-assert.sh"),
    ("device presence and the bounded re-wire", "./test/gate/presence-assert.sh"),
    ("the audio path, as a SIGNAL", "./test/gate/audio-assert.sh"),
    ("the error bus", "./test/gate/err-assert.sh"),
    ("the display arbiter", "./test/gate/display-assert.sh"),
    ("the OLED's four layers", "./test/gate/oled-assert.sh"),
    ("the aux LED", "./test/gate/led-assert.sh"),
    ("the tempo reference", "./test/gate/tempo-assert.sh"),
    ("one clock, and its two arguments", "./test/gate/clock-assert.sh"),
    ("the map", "./test/gate/map-assert.sh"),
    ("panic's second tier", "./test/gate/recover-assert.sh"),
    ("the data store", "./test/gate/state-assert.sh"),
    ("the song store: sections, save and revert", "./test/gate/song-assert.sh"),
    ("the Launchpad", "./test/gate/launchpad-assert.sh"),
    ("the nanoKONTROL", "./test/gate/nano-assert.sh"),
    ("the Organelle's own front panel", "./test/gate/organelle-assert.sh"),
    ("the phone link", "./test/gate/phone-assert.sh"),
    ("the checklists' Send lines", "./test/gate/inject-assert.sh"),
    ("the phone's TouchOSC layout", "./test/gate/touchosc-assert.sh"),
    ("the Volca", "./test/gate/volca-assert.sh"),
    ("the sequencer and its drum page", "./test/gate/sequencer-assert.sh"),
    ("the drum kit, as a SIGNAL", "./test/gate/kit-assert.sh"),
    ("the synths: the nanoKEY, the choice and the Streichfett", "./test/gate/synths-assert.sh"),
    ("the debug patch", "./test/gate/debug-assert.sh"),
]

# Each gate's main-dev.pd copy runs u_net on its own inbound port, base + its
# place in the table (lib_scratch's state_dir writes CUTIT_INPORT); a gate run
# by hand keeps 9002. Clear of 9001/9002 (the device, main-dev.pd) and of
# 9994/9995, which phone-assert binds.
INPORT_BASE = 9100

# CUTIT_JOBS=1 runs them one at a time.
JOBS = int(os.environ.get("CUTIT_JOBS") or 0) or len(GATES)

# Every gate's Pd runs with HOME pointed at an empty directory, so it never reads
# the Mac's Pd preferences, which Pds starting side by side trip over (Reference,
# pure-data, Preferences). Every gate already passes -noaudio, -nomidi and its
# own -path, and lib_scratch adds the device's rate, -r 44100, and the -path of
# the libs folder, which an empty HOME would hide.


def _syntax(env):
    """tools/deploy.sh's own gate: every entry point loads in silence.

    The oracle is output, not status: Pd exits 0 even when objects fail to
    create.
    """
    pd = os.environ["PD"]
    rc, out_lines = 0, []
    # The debug patch too: menu-launched on the device, with no console.
    for f in ("Cut It/main.pd", "Cut It/main-dev.pd", "Cut It Debug/main.pd"):
        p = subprocess.run([pd, "-nogui", "-noaudio", "-nomidi", "-r", "44100",
                            "-path", "mac-stubs", *lib_scratch.LIBS_PATH,
                            "-send", "pd quit", f],
                           env=env,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        out = p.stdout.decode("utf-8", "replace").rstrip("\n")
        if out:
            out_lines.append("  %s produced output:" % f)
            out_lines.append(out)
            rc = 1
        else:
            out_lines.append("  silent: %s" % f)
    return rc, ("\n".join(out_lines) + "\n").encode("utf-8")


def run_one(index, label, command, env):
    """One gate, its output held back. -> (ok, output as bytes).

    stderr is folded into stdout so a gate's FAIL lines stay where it printed
    them, and PYTHONUNBUFFERED keeps a Python gate's print() in order with them.
    """
    if command is None:
        rc, out = _syntax(env)
        return rc == 0, out
    env = dict(env, CUTIT_INPORT=str(INPORT_BASE + index))
    p = subprocess.run(command, shell=True, env=env,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return p.returncode == 0, p.stdout


def report_one(label, ok, out):
    """The banner, the gate's own output, the verdict."""
    print("\n=== %s" % label)
    sys.stdout.flush()
    sys.stdout.buffer.write(out)
    sys.stdout.buffer.flush()
    print("--- %s: %s" % ("ok" if ok else "FAILED", label))
    sys.stdout.flush()


def run_all():
    """Every gate, side by side. -> list of the labels that failed."""
    if len(GATES) != EXPECT:
        # Before anything runs: the wrong table is not the run anyone asked for.
        sys.exit("gates.py: EXPECT is %d but the table holds %d. Update it "
                 "deliberately -- a gate that vanishes is otherwise silent."
                 % (EXPECT, len(GATES)))
    failed = []
    home = tempfile.mkdtemp(prefix="cutit-home-")
    env = dict(os.environ, HOME=home, PYTHONUNBUFFERED="1")
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=JOBS)
    try:
        futures = [pool.submit(run_one, i, label, cmd, env)
                   for i, (label, cmd) in enumerate(GATES)]
        # In table order: a gate that finishes early waits its turn to print.
        for (label, _), fut in zip(GATES, futures):
            ok, out = fut.result()
            report_one(label, ok, out)
            if not ok:
                failed.append(label)
    finally:
        # A Ctrl-C must not leave queued gates to start after it.
        pool.shutdown(wait=True, cancel_futures=True)
        shutil.rmtree(home, ignore_errors=True)
    return failed
