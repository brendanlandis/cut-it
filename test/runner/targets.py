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
import socket
import subprocess
import sys
import threading
import time

import stream

# ⛔ ONE OSC DECODER, shared with test/gate/phone-assert.py.
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "gate"))
import lib_osc                                                  # noqa: E402

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

    # The real instrument boots; a recording does not. See Source.boot_settle.
    boot_settle = 5.0

    def __init__(self, argv, go, teardown=None, label="", osc_port=None):
        self.q = queue.Queue()
        # ⛔ THE SOCKET IS BOUND BEFORE Pd STARTS. Measured: a UDP connect to a
        # port with nothing listening survives exactly ONE datagram -- the ICMP
        # port-unreachable that comes back tears the socket down and every later
        # send is discarded in silence (item 114). Bind after launching and you
        # get one packet and then nothing, which looks exactly like a broken
        # rate limiter. phone-assert.py owns its lifecycle for the same reason.
        self.osc = None
        if osc_port is not None:
            self.osc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.osc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.osc.bind(("127.0.0.1", osc_port))
            self.osc.settimeout(0.25)
        self.teardown_fn = teardown
        self.label = label
        self.log = []
        # ⛔ stdin=DEVNULL, AND IT IS THE WHOLE REASON A DEVICE BENCH COULD NOT
        # BE STEPPED BY A PERSON. Popen INHERITS stdin by default, and `ssh`
        # reads stdin greedily to forward it to the remote command -- so the
        # child and the runner's own prompt were both reading the same terminal
        # and racing for every keystroke. Down a pipe ssh swallows the lot and
        # the first prompt gets EOF; at a tty the Enter meant for the prompt
        # goes to a Pd that has no use for it, and the step never fires. It
        # presents as "GO was sent and nothing fired", which is a lie: the
        # prompt never returned, so no GO was sent at all. Neither Pd reads
        # stdin for anything, so closing it costs nothing.
        self.proc = subprocess.Popen(
            argv, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            bufsize=1, universal_newlines=True)
        self.gosender = go
        self.reader = threading.Thread(target=self._pump, daemon=True)
        self.reader.start()
        if self.osc:
            # ⚠️ THE DATAGRAMS JOIN THE SAME QUEUE as the console lines, decoded
            # into the same "LABEL: rest" shape bench-tap.pd prints. One window
            # format rather than a second one only OSC uses -- so a predicate,
            # a stall and the step loop all read one stream.
            threading.Thread(target=self._pump_osc, daemon=True).start()

    def _pump(self):
        for line in self.proc.stdout:
            self.q.put(line.rstrip("\n"))
        self.q.put(None)                    # the process ended

    def _pump_osc(self):
        while True:
            try:
                data, _ = self.osc.recvfrom(4096)
            except socket.timeout:
                continue
            except OSError:
                return
            m = lib_osc.decode(data)
            if m:
                self.q.put(lib_osc.as_text(*m))

    def readline(self, timeout):
        try:
            line = self.q.get(timeout=max(0.05, timeout))
        except queue.Empty:
            return None
        if line is None:
            return None
        self.log.append(line)
        self._note(line)
        return line

    def pending(self):
        """⚠️ THE QUEUE, NOT THE LOG. A backlog here means the reader is behind
        the patch, which is the one stall cause that is not a fault at all --
        the lines are coming, just later than STEP_TIMEOUT allows."""
        return self.q.qsize()

    def go(self):
        self.gos += 1
        self.gosender.send()

    def rerun(self):
        # ⚠️ NOT COUNTED AS A GO. `gos` is what the stall diagnosis reports, and
        # a repeat advances nothing -- counting it would make the diagnostic
        # claim the runner had driven the bench further than it has.
        self.gosender.send("rerun")
        return True

    def close(self):
        try:
            self.proc.terminate()
            self.proc.wait(timeout=5)
        except Exception:
            try:
                self.proc.kill()
            except Exception:
                pass
        if self.osc:
            self.osc.close()
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


def _tap():
    """bench-tap.pd, loaded beside every bench so a predicate has something to
    read. ⛔ It listens and sends nothing -- see build_tap in bench-gen.py."""
    p = os.path.abspath("test/bench/bench-tap.pd")
    if not os.path.exists(p):
        sys.exit("targets: %s does not exist -- run bench-gen.py. Without it "
                 "every bus predicate would be answered by an empty window "
                 "rather than by a fact." % p)
    return p


PHONE_PORT = 9995


def mac(bench_name, auto_only, work):
    """main-dev.pd plus the bench, in a scratch copy, on this machine."""
    _scratch(work)
    # ⚠️ THE PHONE BENCH ON THIS MACHINE IS A MIRROR, AND IT ANSWERS A DIFFERENT
    # QUESTION FROM A DEVICE RUN. Repointed at localhost, u_net's real datagrams
    # are readable here -- so what it FILTERS can be judged with no phone in the
    # room. What it cannot judge is anything about the phone itself, which is
    # why the device run keeps its human verdict rather than being replaced.
    osc_port = None
    if bench_name == "phone":
        subprocess.run(
            ["sh", "-c",
             '. test/gate/lib-scratch.sh; scratch_phone_mirror "$1" "$2"',
             "_", work, str(PHONE_PORT)], check=True)
        osc_port = PHONE_PORT
        stream.say("  u_net repointed at 127.0.0.1:%d -- no phone involved"
                   % PHONE_PORT)
    bench_pd = os.path.abspath("test/bench/%s-bench.pd" % bench_name)
    if not os.path.exists(bench_pd):
        sys.exit("targets: %s does not exist -- run bench-gen.py" % bench_pd)

    # ⚠️ -stderr IS WHAT MAKES A GUI RUN READABLE. With a GUI and without it,
    # every [print] goes to Pd's own console window and the runner is blind --
    # it would see nothing, call it a stall, and be wrong about a bench that is
    # working. Under --auto-only there is nobody to look at a window, so -nogui
    # is both cheaper and free of that dependency.
    mode = ["-nogui"] if auto_only else ["-stderr"]

    # ⛔ DSP ON, AND IT IS NOT OPTIONAL. Every beat counter hangs off threshold~
    # reading a phasor~, so with DSP off EVERY COUNT READS 0 -- which looks
    # exactly like a dead clock rather than a setting, and would make the tempo
    # predicates fail for a reason that has nothing to do with the patch. On the
    # device mother turns DSP on 200 ms after load and this never arises; on the
    # Mac it is the panel toggle a person is told to tick, and nobody is here to
    # tick it. -send runs after the patches are loaded.
    argv = [PD] + mode + ["-send", "pd dsp 1",
                          "-path", os.path.join(work, "patch"),
                          os.path.join(work, "patch", "main-dev.pd"),
                          bench_pd, _tap()]

    def teardown():
        shutil.rmtree(work, ignore_errors=True)

    stream.say("  launching Pd%s ..." % ("" if auto_only else " with the GUI"))
    return Process(argv, stream.Go("127.0.0.1"), teardown, label="mac",
                   osc_port=osc_port)


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
    remote_tap = "%s/bench-tap.pd" % REMOTE_DIR
    stream.say("  copying %s and bench-tap.pd to %s ..." % (bench_pd, HOST))
    subprocess.run(["scp", "-q", bench_pd, _tap(),
                    "%s:%s/" % (HOST, REMOTE_DIR)], check=True)

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
              "-path '%s' /root/fw_dir/mother.pd main.pd %s %s 2>&1"
              % (PATCH_DIR, PATCH_DIR, remote_pd, remote_tap))

    def teardown():
        subprocess.run(["ssh", HOST, "killall pd 2>/dev/null; true"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        stream.say(
            "\n  ⚠️  The Launchpad is stranded in Programmer Mode -- killall pd\n"
            "      skips m_launchpad's safe exit, and the device's own Settings\n"
            "      menu is locked out in that state. Restore it with:\n"
            "          ./tools/lp-live.sh        (needs no Pd)\n"
            "          ./tools/deploy.sh               (reloads the instrument too)")

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
