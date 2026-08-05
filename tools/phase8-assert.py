#!/usr/bin/env python3
"""Phase 8's headless gate -- no eyes, no hardware, no socket, ~12 s.

It asserts on the FILES u_state leaves on disk, plus the console output, which
is the right level to test our own code at: what a performer eventually loses is
a file, not a message.

⚠️ THE CHECKS ASSERT PROPERTIES, NOT PROXIES. Phase 7's gate had seven checks
that asserted "zero packets in an idle window" as a stand-in for a property they
never named, and they all broke the moment a legitimate feature added traffic.
They were rewritten to assert the real property and the gate came out stronger.
So every check below names the thing it is actually protecting.
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PD = os.environ.get("PD", "/Applications/Pd-0.49-1.app/Contents/Resources/bin/pd")
DIR = "/tmp/cut-it-phase8-gate"
DRIVE = os.path.join(HERE, "phase8-assert-drive.pd")
AUTO = os.path.join(DIR, "cut-it-auto.txt")
MANUAL = os.path.join(DIR, "cut-it-manual.txt")
VERBOSE = "-v" in sys.argv

RESULTS = []


def check(ok, name, detail=""):
    RESULTS.append((bool(ok), name, detail))
    print("  %s  %s" % ("PASS" if ok else "FAIL", name))
    if detail and (VERBOSE or not ok):
        for line in str(detail).rstrip().split("\n"):
            print("        %s" % line)


def fresh_dir():
    if os.path.isdir(DIR):
        shutil.rmtree(DIR)
    os.makedirs(DIR)


def run_driver():
    """Run the driver to completion. It quits itself -- -send 'pd quit' would
    return before any [del] fired, which is the same fact that lets deploy.sh
    ignore a [print] behind [del 2000]."""
    p = subprocess.run(
        [PD, "-nogui", "-noaudio", "-nomidi",
         "-path", os.path.join(ROOT, "mac-stubs"),
         "-path", os.path.join(ROOT, "Cut It"), DRIVE],
        capture_output=True, text=True, timeout=60)
    return (p.stdout or "") + (p.stderr or "")


def read(path):
    try:
        with open(path) as fh:
            return [l.rstrip("\n") for l in fh if l.strip()]
    except IOError:
        return None


# ---------------------------------------------------------------------------
print("=== A. the deploy.sh gate: both entry points load in SILENCE ===")
# This is deploy.sh's own command, not an approximation of it. u_state reads two
# files at boot and a missing file PRINTS three lines (item 143) -- so this is
# the check that would catch the state store breaking every deploy.
for entry in ("main.pd", "main-dev.pd"):
    p = subprocess.run(
        [PD, "-nogui", "-noaudio", "-nomidi",
         "-path", os.path.join(ROOT, "mac-stubs"),
         "-send", "pd quit", os.path.join(ROOT, "Cut It", entry)],
        capture_output=True, text=True, timeout=60)
    out = (p.stdout or "") + (p.stderr or "")
    check(out.strip() == "", "%s loads with no output" % entry, out)

# ---------------------------------------------------------------------------
print("=== B. a fresh install: auto and manual are separate stores ===")
fresh_dir()
out1 = run_driver()
auto = read(AUTO)
manual = read(MANUAL)

check(auto is not None, "auto.txt was written", DIR)
check(manual is not None, "manual.txt was written", DIR)

auto = auto or []
manual = manual or []

check(any(l.startswith("mode ") for l in auto),
      "an auto put reaches auto.txt", auto)
check(not any(l.startswith("mode ") for l in manual),
      "an auto put does NOT leak into manual.txt", manual)
check(any(l.startswith("take-1 ") for l in manual),
      "a save broadcast is answered and written to manual.txt", manual)
check(not any(l.startswith("take-1 ") for l in auto),
      "a manual answer does NOT leak into auto.txt", auto)

# THE CONTRACT. Not a proxy: this is the rule itself.
check(not any("late-key" in l for l in manual + auto),
      "a contributor answering behind a [del] is ABSENT from the file",
      "manual=%s auto=%s" % (manual, auto))

# THE REPLACE CASE. A store that appended would pass everything above.
mode_lines = [l for l in auto if l.startswith("mode ")]
check(len(mode_lines) == 1,
      "re-putting a key REPLACES its line rather than appending", mode_lines)
check(mode_lines == ["mode perform mode-4"],
      "the surviving line is the LAST value put", mode_lines)

# ---------------------------------------------------------------------------
print("=== C. restore: order, and a key present in both files ===")
fresh_dir()
with open(AUTO, "w") as fh:
    fh.write("mode perform mode-6\ndupe from-auto\n")
with open(MANUAL, "w") as fh:
    fh.write("take-1 kick 36 snare 38\ndupe from-manual\n")
out2 = run_driver()

restores = [l.split(":", 1)[1].strip()
            for l in out2.split("\n") if l.startswith("RESTORE:")]
check(len(restores) >= 4, "every line of both files is replayed", restores)

# manual FIRST, auto SECOND -- so that where a key appears in both, the running
# value is the one left standing.
try:
    i_manual = next(i for i, r in enumerate(restores) if "from-manual" in r)
    i_auto = next(i for i, r in enumerate(restores) if "from-auto" in r)
    check(i_manual < i_auto,
          "manual is replayed BEFORE auto, so auto wins a duplicate key",
          restores)
except StopIteration:
    check(False, "manual is replayed BEFORE auto, so auto wins a duplicate key",
          restores)

check(any("take-1 kick 36 snare 38" in r for r in restores),
      "a manual line survives a restart and is replayed intact", restores)

# ⚠️ THE BUG THIS EXISTS TO CATCH, and it shipped once already: the flush used to
# be armed by a loadbang, so the boot default was written over the saved file
# BEFORE the restore ever read it. Saved state could never survive a boot, and
# the file looked entirely plausible throughout.
# The property: the restore replayed what was ON DISK AT BOOT. With the bug,
# the flush fires first and overwrites the file with the running values, so the
# restore replays those instead and `mode perform mode-6` never appears.
check(any("mode perform mode-6" in r for r in restores),
      "a boot does NOT overwrite saved state before reading it", restores)

# ---------------------------------------------------------------------------
print()
failed = [r for r in RESULTS if not r[0]]
print("%d checks, %d passed, %d failed"
      % (len(RESULTS), len(RESULTS) - len(failed), len(failed)))
if failed:
    print()
    print("FAILED:")
    for _ok, name, _d in failed:
        print("  - %s" % name)
sys.exit(1 if failed else 0)
