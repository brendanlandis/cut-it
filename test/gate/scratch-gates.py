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
        s.run(cap, dog, *FLAGS, "-path", s.patch, *files)
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
def volca(g):
    S.require("Cut It/m_volca.pd", "Cut It/cut-it-map.txt")
    s = g.copy()
    s.state_dir()
    s.map_rows(["mode-1 gk-cc volca-cc 41",
                "mode-1 gk-note volca-note 48",
                "mode-1 gk-prog volca-prog 5",
                "mode-1 gk-key volca-key 60"])
    g.rewrite(s)
    s.drive(GEN % "volca-assert", s.path("drive.pd"))
    cap = g.pd(s, 40, main_dev(s), s.path("drive.pd"))
    return g.analyze("test/gate/volca-assert.py", *g.args, stdin=cap)


RECIPES = {
    "volca": volca,
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
