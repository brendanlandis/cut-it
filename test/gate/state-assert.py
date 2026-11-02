#!/usr/bin/env python3
"""The data store's headless gate -- ref/module/state.md. No eyes, no hardware, no socket, ~12 s.

    python3 test/gate/state-assert.py [-v] [--keep]     (run it as state-assert.sh)

It asserts on the files u_state leaves on disk, plus the console: what a
performer loses is a file, not a message. Every check names the property it
protects, not a proxy for it.
"""
import atexit
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_assert as A                                          # noqa: E402
import lib_scratch as S                                         # noqa: E402

# The driver and the state files live in the gate's own scratch directory, never a
# path another run shares; --keep leaves them.
KEEP = "--keep" in sys.argv
WORK = S.work_dir("state")
DIR = os.path.join(WORK, "state")
DRIVE = os.path.join(WORK, "drive.pd")
AUTO = os.path.join(DIR, "cut-it-auto.txt")
MANUAL = os.path.join(DIR, "cut-it-manual.txt")
PD_ARGS = ("-nogui", "-noaudio", "-nomidi", "-path", "mac-stubs")


def fresh_dir():
    if os.path.isdir(DIR):
        shutil.rmtree(DIR)
    os.makedirs(DIR)


def run_driver(name):
    """Run the driver to completion. It quits itself: -send 'pd quit' would
    return before any [del] fired."""
    cap = os.path.join(WORK, "capture-%s.txt" % name)
    S.run(cap, 60, *PD_ARGS, "-path", "Cut It", DRIVE)
    return open(cap, encoding="utf-8", errors="replace").read()


def read(path):
    try:
        with open(path) as fh:
            return [l.rstrip("\n") for l in fh if l.strip()]
    except IOError:
        return None


def cleanup():
    """--keep leaves the driver, the state files and every capture; otherwise the
    directory goes, however the run ends."""
    if KEEP:
        print("kept " + WORK)
    else:
        shutil.rmtree(WORK, ignore_errors=True)


sys.stdout.reconfigure(line_buffering=True)
os.chdir(S.ROOT)
S.require_pd()
S.require("Cut It/u_state.pd", "Cut It/u_store.pd")
os.makedirs(WORK)
atexit.register(cleanup)
S.drive("test/gate/state-assert-drive-gen.py", DRIVE, DIR)

print("=== A. the tools/deploy.sh gate: both entry points load in SILENCE ===")
# tools/deploy.sh's own command. u_state reads two files at boot, and a missing
# one prints three lines (item 143), which would fail every deploy.
for entry in ("main.pd", "main-dev.pd"):
    cap = os.path.join(WORK, "load-%s.txt" % entry)
    S.run(cap, 60, *PD_ARGS, "-send", "pd quit", os.path.join("Cut It", entry))
    out = open(cap, encoding="utf-8", errors="replace").read()
    A.check("%s loads with no output" % entry, out.strip() == "", out.strip())

print("=== B. a fresh install: auto and manual are separate stores ===")
fresh_dir()
run_driver("b")
auto = read(AUTO)
manual = read(MANUAL)

A.check("auto.txt was written", auto is not None, DIR)
A.check("manual.txt was written", manual is not None, DIR)

auto = auto or []
manual = manual or []

A.check("an auto put reaches auto.txt",
        any(l.startswith("mode ") for l in auto), auto)
A.check("an auto put does NOT leak into manual.txt",
        not any(l.startswith("mode ") for l in manual), manual)
A.check("a save broadcast is answered and written to manual.txt",
        any(l.startswith("take-1 ") for l in manual), manual)
A.check("a manual answer does NOT leak into auto.txt",
        not any(l.startswith("take-1 ") for l in auto), auto)

# The synchronous contract itself.
A.check("a contributor answering behind a [del] is ABSENT from the file",
        not any("late-key" in l for l in manual + auto),
        "manual=%s auto=%s" % (manual, auto))

# A store that appended would pass everything above.
mode_lines = [l for l in auto if l.startswith("mode ")]
A.check("re-putting a key REPLACES its line rather than appending",
        len(mode_lines) == 1, mode_lines)
A.check("the surviving line is the LAST value put",
        mode_lines == ["mode perform mode-4"], mode_lines)

print("=== C. restore: order, and a key present in both files ===")
fresh_dir()
with open(AUTO, "w") as fh:
    fh.write("mode perform mode-6\ndupe from-auto\n")
with open(MANUAL, "w") as fh:
    fh.write("take-1 kick 36 snare 38\ndupe from-manual\n")
out2 = run_driver("c")

restores = [l.split(":", 1)[1].strip()
            for l in out2.split("\n") if l.startswith("RESTORE:")]
A.check("every line of both files is replayed", len(restores) >= 4, restores)

# Manual first, auto second, so where a key is in both the running value wins.
i_manual = next((i for i, r in enumerate(restores) if "from-manual" in r), None)
i_auto = next((i for i, r in enumerate(restores) if "from-auto" in r), None)
A.check("manual is replayed BEFORE auto, so auto wins a duplicate key",
        i_manual is not None and i_auto is not None and i_manual < i_auto,
        restores)

A.check("a manual line survives a restart and is replayed intact",
        any("take-1 kick 36 snare 38" in r for r in restores), restores)

# The restore replays what was on disk at boot. A flush armed by a loadbang
# writes the running values over the file first, and mode-6 never appears.
A.check("a boot does NOT overwrite saved state before reading it",
        any("mode perform mode-6" in r for r in restores), restores)

sys.exit(1 if A.report() else 0)
