#!/usr/bin/env python3
"""THE GATE HALF -- every headless check this project has, as data.

Imported by run.py, never run on its own.

WHY IT EXISTS, and it is a process fix rather than a new test. Phase 8 edited
u_map, u_init and u_root -- files that Phases 5, 6 and 7 all rest on -- and came
within one step of shipping without ever re-running THEIR gates. Nothing prompted
it. The gates were all there, all passing, and all unused.

⚠️ A GATE YOU HAVE TO REMEMBER TO RUN IS A GATE THAT EVENTUALLY DOES NOT RUN.
That is the same lesson as `wire.sh` being run by u_init rather than by hand, and
as tools/deploy.sh doing the syntax check rather than trusting anyone to.

⛔ EVERYTHING HERE IS MAC-SIDE AND TOUCHES NOTHING ON THE ORGANELLE: no ssh, no
deploy, no device. Safe to run at any time, including with the device off. That
guarantee is the whole reason a bare `./test/run.sh` is worth typing before every
commit, and it is why the bench half lives behind a flag and is never reached
from here. ⚠️ A CHECK THAT COSTS TWENTY MINUTES STOPS BEING RUN, which is the
failure this file was built to fix.

⛔ THE COMMANDS ARE LITERAL SHELL STRINGS, AND THAT IS DELIBERATE. This table was
109 lines of sh until the runner absorbed it, and a port is exactly where a gate
quietly disappears -- so each command is carried across verbatim rather than
rebuilt out of argument lists. `"Cut It"/*.pd` expands in the shell here exactly
as it did there; rebuilding it as a Python glob would introduce an ordering
question that did not previously exist.
"""
import concurrent.futures
import os
import shutil
import subprocess
import sys
import tempfile

# ---------------------------------------------------------------------------
# ⛔ THE INVENTORY, AND ITS LENGTH IS ASSERTED. run.py prints "N gates" on every
# run and EXPECT is what a dropped one collides with. A gate that vanishes in an
# edit is otherwise completely silent: the run gets faster, everything says ok,
# and the tally is the only witness. Watch it go UP.
#
# ⚠️ UPDATE THIS DELIBERATELY, NEVER TO MAKE A RED RUN GREEN -- the same rule as
# MIDI_EXPECT in test/gate/lib_scratch.py, and for the same reason.
EXPECT = 25

# ⛔ THE GATES RUN SIDE BY SIDE, IN TWO BLOCKS, AND PRINT IN TABLE ORDER. Most
# of a gate's time is a Pd instance ticking in real time, so one after another
# the suite took ~5 minutes for about one minute of CPU. Each gate's output is
# buffered and printed whole, in the order below, so the log reads exactly as a
# serial run's did and there is still one RESULT: line.
#
# ⚠️ STRUCTURE FINISHES BEFORE ANY MODULE GATE STARTS. That was for docs-check,
# which reads every .pd, .py and .sh in the repo, while state-assert and
# phone-assert rewrote their drivers inside test/gate/: a half-written driver
# read mid-write was a false failure that came and went. Since 2026-11-02 every
# driver is generated into a scratch directory and no gate writes inside the
# repo, so the order no longer protects anything. It costs the run the
# structure block's ~5 s, most of it runner-assert.
#
# ⛔ THE INVENTORY RUNS FIRST because every gate below it rewrites the same MIDI
# object boxes, so a count that has drifted explains all of them at once. Then
# the instrument-wide concerns, then one gate per physical device -- the same
# axis ref/ uses, because a page that names a gate should be able to name one
# whose whole subject is that page.
STRUCTURE = [
    # --- 1. structure ------------------------------------------------------
    # pd-layout-check separates PROBLEM (structural -- a cord onto a comment
    # means indices are off by one, which is how every one of the five silent
    # rewirings in this project was caught) from note (cosmetic -- crossed
    # cords). Only PROBLEMs exit non-zero, so the status is trustworthy alone.
    # ⛔ BOTH DEPLOYABLES. "Cut It Debug" is a second patch folder, and a cord
    # naming a box that does not exist is exactly as silent there as it is in the
    # instrument -- Pd drops it and loads anyway.
    ("layout and graph structure",
     'python3 test/gate/pd-layout-check.py "Cut It"/*.pd "Cut It Debug"/*.pd'),

    # --- 1b. the documentation ---------------------------------------------
    # The docs restate the same fact in up to ten files and nothing connected
    # the copies, so a correction landed in one and the rest went stale.
    # docs-check ties them together mechanically: an anchored markdown table
    # must equal the array the patch actually plays from, and every pointer to a
    # document must resolve. Reintroduce `47 + n` and it goes red AT PAD 5 --
    # before deploy, before the device, in ~200 ms.
    ("documentation matches the patch",
     "python3 test/gate/docs-check.py"),

    # --- 2. the deploy gate ------------------------------------------------
    # Pd exits 0 even when objects fail to create, so the gate is OUTPUT, not
    # status. Handled in code below rather than as a command, because it needs
    # to read what Pd wrote.
    ("both entry points load in silence (tools/deploy.sh's own gate)", None),

    # --- 3. the benches are generated, not hand-written --------------------
    ("bench step text survived generation",
     "python3 test/bench/bench-verify.py"),

    # --- 3b. the runner itself ---------------------------------------------
    # ⛔ THE ONLY THING THAT EVER EXERCISES THE RUNNER'S FAILURE PATHS. A
    # hardware run that goes well never stalls, never desyncs, is never
    # interrupted and never meets an empty console, so without this every one of
    # those branches could be dead code and every run would look identical and
    # green. Replay fixtures: Mac-only, headless, under a second, so it costs
    # the bare run nothing and takes nothing away from its guarantee.
    ("the runner's own failure paths", "./test/gate/runner-assert.sh"),

    ("the MIDI inventory", "./test/gate/midi-emitters-assert.sh"),
]

MODULES = [
    # --- 4. one gate per module --------------------------------------------
    ("the boot sequence", "./test/gate/init-assert.sh"),
    # ⛔ THE ONLY GATE WHOSE STIMULUS IS A SILENCE. It withholds the device
    # inquiry reply rather than sending one, which is the absent-at-load case of
    # item 235 -- the case the Launchpad watchdog was built unable to handle,
    # because "lost" was a transition from present to absent and never-present is
    # not a transition.
    ("device presence and the bounded re-wire", "./test/gate/presence-assert.sh"),
    # ⛔ THE ONLY GATE HERE THAT READS A SIGNAL BACK. Everything else asserts on
    # messages, which is exactly why the audio path -- four connect lines and no
    # gain -- was the last page in ref/ still declaring `Gate: none`.
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
    ("the Launchpad", "./test/gate/launchpad-assert.sh"),
    ("the nanoKONTROL", "./test/gate/nano-assert.sh"),
    ("the Organelle's own front panel", "./test/gate/organelle-assert.sh"),
    ("the phone link", "./test/gate/phone-assert.sh"),
    ("the SP-404, both directions", "./test/gate/sp404-assert.sh"),
    ("the Volca", "./test/gate/volca-assert.sh"),
    # ⛔ THE SECOND DEPLOYABLE, and the only gate here whose subject is a SCREEN.
    # The debug patch has no bus at all -- no disp, no g_oled, no u_map -- so the
    # five rows it writes to mother are the whole product, and the rows are what
    # it asserts.
    ("the debug patch", "./test/gate/debug-assert.sh"),
]

GATES = STRUCTURE + MODULES

# ⛔ EACH GATE GETS ITS OWN INBOUND UDP PORT, base + its place in the table.
# Every scratch copy of main-dev.pd runs u_net, which listens on one port, and
# only one process can hold it: two gates side by side on 9002 would print
# `bind: Address already in use`. state_dir in test/gate/lib_scratch.py writes
# CUTIT_INPORT into the copy, and a gate run by hand keeps 9002.
# ⚠️ CLEAR OF 9001/9002 (the device and main-dev.pd) and of 9992-9998, which the
# OSC mirrors, phone-assert and the bench stream bind.
INPORT_BASE = 9100

# How many gates run at once. CUTIT_JOBS=1 runs them one at a time again.
JOBS = int(os.environ.get("CUTIT_JOBS") or 0) or len(MODULES)

# ⛔ AND NO GATE'S Pd READS THE MAC'S Pd PREFERENCES. Pd 0.49 sets a `loading`
# flag in them while it starts, and one that starts while another is still
# starting prints "Pd seems to have crashed on startup" and skips them -- which
# failed state-assert's silence check the first time the gates ran side by
# side. -noprefs does not stop it: measured, 6 of 40 startups eight at a time
# printed it with -noprefs and 5 of 40 without. Pd only reads the flag when
# $HOME holds org.puredata.pd.plist, so every gate runs with HOME pointed at an
# empty directory: 0 of 40. Nothing is lost, because every gate already passes
# -noaudio, -nomidi and its own -path.


def _syntax(env):
    """tools/deploy.sh's own gate: both entry points must load in SILENCE.

    ⛔ THE ORACLE IS OUTPUT, NOT EXIT STATUS. Pd returns 0 even when half the
    objects in a patch failed to create, so a status check here would pass a
    patch that does nothing at all.
    """
    pd = os.environ["PD"]
    rc, out_lines = 0, []
    # ⛔ THREE ENTRY POINTS, NOT TWO. "Cut It Debug/main.pd" is menu-launched on
    # the same device with the same -nogui and the same absent console, so a
    # load-time error there is exactly as silent as one in the instrument -- and
    # it is the patch you reach for WHEN the instrument is already broken.
    for f in ("Cut It/main.pd", "Cut It/main-dev.pd", "Cut It Debug/main.pd"):
        p = subprocess.run([pd, "-nogui", "-noaudio", "-nomidi",
                            "-path", "mac-stubs", "-send", "pd quit", f],
                           env=env,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        # $(...) strips every trailing newline and `echo` puts exactly one back
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

    ⚠️ stderr IS FOLDED INTO stdout so a gate's FAIL lines stay where it printed
    them, and PYTHONUNBUFFERED keeps a Python gate's print() from being reordered
    against them in the pipe.
    """
    if command is None:
        rc, out = _syntax(env)
        return rc == 0, out
    env = dict(env, CUTIT_INPORT=str(INPORT_BASE + index))
    p = subprocess.run(command, shell=True, env=env,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return p.returncode == 0, p.stdout


def report_one(label, ok, out):
    """The banner, the gate's own output, the verdict -- what a serial run
    printed, byte for byte."""
    print("\n=== %s" % label)
    sys.stdout.flush()
    sys.stdout.buffer.write(out)
    sys.stdout.buffer.flush()
    print("--- %s: %s" % ("ok" if ok else "FAILED", label))
    sys.stdout.flush()


def run_all():
    """Every gate, STRUCTURE then MODULES, each block side by side.
    -> list of the labels that failed."""
    if len(GATES) != EXPECT:
        # Not a check that can be deferred to the summary: if the table is the
        # wrong length the run about to happen is not the run anyone asked for.
        sys.exit("gates.py: EXPECT is %d but the table holds %d. Update it "
                 "deliberately -- a gate that vanishes is otherwise silent."
                 % (EXPECT, len(GATES)))
    failed = []
    home = tempfile.mkdtemp(prefix="cutit-home-")
    env = dict(os.environ, HOME=home, PYTHONUNBUFFERED="1")
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=JOBS)
    try:
        start = 0
        for block in (STRUCTURE, MODULES):
            futures = [pool.submit(run_one, start + i, label, cmd, env)
                       for i, (label, cmd) in enumerate(block)]
            # In table order: a gate that finishes early waits its turn to print.
            for (label, _), fut in zip(block, futures):
                ok, out = fut.result()
                report_one(label, ok, out)
                if not ok:
                    failed.append(label)
            start += len(block)
    finally:
        # ⚠️ A Ctrl-C must not leave queued gates to start after it.
        pool.shutdown(wait=True, cancel_futures=True)
        shutil.rmtree(home, ignore_errors=True)
    return failed
