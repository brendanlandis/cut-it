#!/usr/bin/env python3
"""Where a bench actually runs: a Pd on this Mac, or one on the Organelle.

Imported by run.py. Each target hands back a stream.Source, so the step loop
never learns which it is talking to -- the same loop the replay fixtures drive.

⛔ THE TARGET SAYS WHERE THE PATCH RUNS. IT DOES NOT SAY WHETHER A PERSON IS
WATCHING -- that is --auto-only, and the two are separate on purpose. Welded
together they make an unattended run on the real rig unreachable, which is a
thing worth having: the predicates can be collected on hardware with nobody in
the room, and the steps only eyes can judge say so instead of being invented.
"""
import os
import queue
import shutil
import subprocess
import sys
import threading
import time

import stream

PD = os.environ.get(
    "PD", "/Applications/Pd-0.49-1.app/Contents/Resources/bin/pd")

HOST = os.environ.get("ORGANELLE", "root@organelle.local")
# ⚠️ /sdcard, NEVER /tmp. /tmp is wiped on reboot, and a bench copied there
# vanishes with a restart -- the by-hand launch then runs mother.pd + main.pd
# with NO BENCH, the GO port is never bound, and it looks exactly like a bench
# frozen on step 1. Item 134.
REMOTE_DIR = "/sdcard"
PATCH_DIR = "/sdcard/Patches/!/Cut It"


class Process(stream.Source):
    """A Pd whose console we read line by line.

    ⚠️ THE READER IS A THREAD BECAUSE THERE IS NO PORTABLE TIMED readline. The
    loop needs "a line, or nothing within N seconds" -- a bare readline() blocks
    forever, which turns every stall into a hang, and a gate that hangs is worse
    than one that fails.
    """

    def __init__(self, argv, go, teardown=None, label=""):
        self.q = queue.Queue()
        self.teardown_fn = teardown
        self.label = label
        self.log = []
        self.proc = subprocess.Popen(
            argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            bufsize=1, universal_newlines=True)
        self.gosender = go
        self.reader = threading.Thread(target=self._pump, daemon=True)
        self.reader.start()

    def _pump(self):
        for line in self.proc.stdout:
            self.q.put(line.rstrip("\n"))
        self.q.put(None)                    # the process ended

    def readline(self, timeout):
        try:
            line = self.q.get(timeout=max(0.05, timeout))
        except queue.Empty:
            return None
        if line is None:
            return None
        self.log.append(line)
        return line

    def go(self):
        self.gosender.send()

    def close(self):
        try:
            self.proc.terminate()
            self.proc.wait(timeout=5)
        except Exception:
            try:
                self.proc.kill()
            except Exception:
                pass
        if self.gosender:
            self.gosender.close()
        if self.teardown_fn:
            self.teardown_fn()


# ---------------------------------------------------------------------------
def _scratch(work):
    """A throwaway copy of the patch, through the SAME shell functions every
    gate uses.

    ⛔ scratch_state_dir IS NOT OPTIONAL. main-dev.pd passes /tmp, which every
    run on this machine shares, and u_init restores saved state at about 3.5 s
    -- so a previous run that changed mode silently rewrites the starting
    conditions of this one, mid-bench. It cost a wrong diagnosis once: item 232.

    ⛔ AND midi_rewrite IS NOT CALLED. Every headless gate swaps the MIDI objects
    for printing stubs; a BENCH wants the opposite. Its whole point is a real
    Volca you can hear and a real 404 under a real finger, and a bench run
    against stubs would be a very thorough test of nothing.
    """
    subprocess.run(
        ["sh", "-c",
         '. test/gate/lib-scratch.sh; scratch_make "$1"; scratch_state_dir "$1"',
         "_", work],
        check=True)


def mac(bench_name, auto_only, work):
    """main-dev.pd plus the bench, in a scratch copy, on this machine."""
    _scratch(work)
    bench_pd = os.path.abspath("test/bench/%s-bench.pd" % bench_name)
    if not os.path.exists(bench_pd):
        sys.exit("targets: %s does not exist -- run bench-gen.py" % bench_pd)

    # ⚠️ -stderr IS WHAT MAKES A GUI RUN READABLE. With a GUI and without it,
    # every [print] goes to Pd's own console window and the runner is blind --
    # it would see nothing, call it a stall, and be wrong about a bench that is
    # working. Under --auto-only there is nobody to look at a window, so -nogui
    # is both cheaper and free of that dependency.
    mode = ["-nogui"] if auto_only else ["-stderr"]
    argv = [PD] + mode + ["-path", os.path.join(work, "patch"),
                          os.path.join(work, "patch", "main-dev.pd"), bench_pd]

    def teardown():
        shutil.rmtree(work, ignore_errors=True)

    stream.say("  launching Pd%s ..." % ("" if auto_only else " with the GUI"))
    return Process(argv, stream.Go("127.0.0.1"), teardown, label="mac")


def device(bench_name, auto_only, work):
    """The real rig: mother.pd, main.pd and the bench, as a third patch.

    ⚠️ IT KILLS THE RUNNING INSTRUMENT. That is what loading a bench has always
    meant here, and `killall pd` STRANDS THE LAUNCHPAD IN PROGRAMMER MODE -- its
    own Settings menu is locked out in that state, so the front panel cannot
    recover it. The teardown says so every time rather than trusting anyone to
    remember.
    """
    bench_pd = "test/bench/%s-bench.pd" % bench_name
    remote_pd = "%s/%s-bench.pd" % (REMOTE_DIR, bench_name)
    stream.say("  copying %s to %s ..." % (bench_pd, HOST))
    subprocess.run(["scp", "-q", bench_pd, "%s:%s" % (HOST, remote_pd)],
                   check=True)

    # ⚠️ THE SECOND -path IS NOT OPTIONAL. tempo-bench's own declare is
    # `../../Cut It`, which resolves from test/bench/ on the Mac and from
    # nowhere useful on the device -- without this c_clock fails to create and
    # both its counts read 0, which looks exactly like a dead clock rather than
    # a missing search path.
    #
    # ⚠️ SINGLE QUOTES AROUND THE PATCH PATH. The folder is /sdcard/Patches/!/…
    # and `!` inside double quotes is a history event in an interactive zsh --
    # you get `zsh: event not found` before anything reaches the device.
    remote = ("killall pd 2>/dev/null; sleep 1; cd '%s' && "
              "exec pd -nogui -rt -audiobuf 6 -path /root/Pd/externals "
              "-path '%s' /root/fw_dir/mother.pd main.pd %s 2>&1"
              % (PATCH_DIR, PATCH_DIR, remote_pd))

    def teardown():
        subprocess.run(["ssh", HOST, "killall pd 2>/dev/null; true"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        stream.say(
            "\n  ⚠️  The Launchpad is stranded in Programmer Mode -- killall pd\n"
            "      skips m_launchpad's safe exit, and the device's own Settings\n"
            "      menu is locked out in that state. Restore it with:\n"
            "          ./tools/lp-live.sh        (needs no Pd)\n"
            "          ./deploy.sh               (reloads the instrument too)")

    stream.say("  launching on %s -- ⚠️ this stops the running instrument" % HOST)
    return Process(["ssh", HOST, remote], stream.Go(_host_only(HOST)),
                   teardown, label="device")


def _host_only(spec):
    return spec.split("@", 1)[-1]


def open_target(name, bench_name, auto_only):
    work = os.path.join(os.environ.get("TMPDIR", "/tmp"),
                        "cutit-bench-%d" % os.getpid())
    if name == "mac":
        return mac(bench_name, auto_only, work)
    if name == "device":
        return device(bench_name, auto_only, work)
    raise ValueError("no such target: %s" % name)
