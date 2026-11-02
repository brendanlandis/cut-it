#!/usr/bin/env python3
"""Where a bench runs: a Pd on this Mac, or one on the Organelle.

Imported by run.py. Each target hands back a stream.Source, so the step loop
never learns which it is talking to.

The target says where the patch runs, not whether a person is watching: that is
--auto-only, kept separate so an unattended run on the rig stays possible.
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

# The OSC decoder phone-assert uses, and the scratch copy every gate makes.
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "gate"))
import lib_osc                                                  # noqa: E402
import lib_scratch                                              # noqa: E402

PD = os.environ.get(
    "PD", "/Applications/Pd-0.49-1.app/Contents/Resources/bin/pd")

HOST = os.environ.get("ORGANELLE", "root@organelle.local")
# /sdcard, never /tmp: /tmp empties on reboot, and a launch with no bench looks
# exactly like a bench frozen on step 1 (item 134).
REMOTE_DIR = "/sdcard"
PATCH_DIR = "/sdcard/Patches/!/Cut It"


class Process(stream.Source):
    """A Pd whose console we read line by line, on a thread: there is no
    portable timed readline, and a bare readline() turns every stall into a
    hang.
    """

    # The real instrument boots; a recording does not. See Source.boot_settle.
    boot_settle = 5.0

    def __init__(self, argv, go, teardown=None, label="", osc_port=None):
        self.q = queue.Queue()
        # Bound before Pd starts: a UDP socket dies on the first datagram
        # nobody hears, and every later send vanishes (item 114).
        self.osc = None
        if osc_port is not None:
            self.osc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.osc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.osc.bind(("127.0.0.1", osc_port))
            self.osc.settimeout(0.25)
        self.teardown_fn = teardown
        self._holding = False
        self.label = label
        self.log = []
        # ⛔ stdin=DEVNULL: ssh reads stdin greedily to forward it, so an
        # inherited one races the runner's own prompt for every keystroke and
        # the step never fires. runner-assert checks for it.
        self.proc = subprocess.Popen(
            argv, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            bufsize=1, universal_newlines=True)
        self.gosender = go
        self.reader = threading.Thread(target=self._pump, daemon=True)
        self.reader.start()
        if self.osc:
            # Decoded into the "LABEL: rest" shape bench-tap.pd prints, on the
            # same queue, so predicates and the step loop read one stream.
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

    def flush(self):
        """Discard the backlog. -> how many lines went. See Source.flush."""
        n = 0
        while True:
            try:
                line = self.q.get_nowait()
            except queue.Empty:
                return n
            if line is None:                # the process ended -- put it back
                self.q.put(None)
                return n
            self.log.append(line)
            n += 1

    def pending(self):
        """The queue, not the log: a backlog means the reader is behind the
        patch, the one stall cause that is no fault."""
        return self.q.qsize()

    def go(self):
        self.gos += 1
        self.gosender.send()

    def rerun(self):
        # Not counted as a GO: `gos` is what a stall report cites, and a
        # repeat advances nothing.
        self.gosender.send("rerun")
        return True

    def where(self):
        # Nor this: a question asked because of a stall must not add to the
        # evidence about it.
        self.gosender.send("where")
        return True

    def show(self):
        self.gosender.send("show")
        return True

    def hold(self, on):
        """Keep re-firing the current step while a verdict is open.

        A thread, because the prompt blocks: the question appears at once and
        the screen stays alive under it. It ends when told to or after
        HOLD_MAX; one that outlived its step would re-fire into the next and be
        read as that step's console.
        """
        if not on:
            self._holding = False
            return
        self._holding = True
        # One now, then the loop: the hold starts about a second into the
        # row's ~1.3 s life, so waiting a full interval let it expire first.
        self.gosender.send("rerun")

        def loop():
            for _ in range(HOLD_MAX):
                time.sleep(HOLD_EVERY)
                if not self._holding:
                    return
                self.gosender.send("rerun")
        threading.Thread(target=loop, daemon=True).start()

    def close(self, quiet=False):
        """`quiet` is for a reload: the stranded-Launchpad notice is true at
        the end of a session and noise in the middle of one."""
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
        if self.teardown_fn and not quiet:
            self.teardown_fn()


# ---------------------------------------------------------------------------
def _scratch(work):
    """A throwaway copy of the patch, through the harness every gate uses.

    state_dir is required: main-dev.pd's /tmp is shared, and u_init restores
    saved state mid-run (item 232, the gate skill). midi_rewrite is not called:
    a bench wants the real Volca and 404, not printing stubs. state_dir's u_net
    sink is a socket in this process, so it lasts as long as the bench does.
    """
    s = lib_scratch.Scratch(work).make()
    s.state_dir()
    return s


def _tap():
    """bench-tap.pd, loaded beside every bench so a predicate has something to
    read. It listens and sends nothing: build_tap in bench-gen.py."""
    p = os.path.abspath("test/bench/bench-tap.pd")
    if not os.path.exists(p):
        sys.exit("targets: %s does not exist -- run bench-gen.py. Without it "
                 "every bus predicate would be answered by an empty window "
                 "rather than by a fact." % p)
    return p


# A row lives ~1.3 s on the OLED, so the hold re-sends well inside that; 0.8 s
# leaves room for the datagram and g_oled's 10 Hz repaint. HOLD_MAX caps a
# walk-away at four minutes.
HOLD_EVERY = 0.8
HOLD_MAX = 300

PHONE_PORT = 9995


def mac(bench_name, auto_only, work):
    """main-dev.pd plus the bench, in a scratch copy, on this machine."""
    copy = _scratch(work)
    # Here the phone bench is a mirror, u_net repointed at localhost: what it
    # filters can be judged with no phone, nothing about the phone itself.
    osc_port = None
    if bench_name == "phone":
        copy.phone_mirror(PHONE_PORT)
        osc_port = PHONE_PORT
        stream.say("  u_net repointed at 127.0.0.1:%d -- no phone involved"
                   % PHONE_PORT)
    bench_pd = os.path.abspath("test/bench/%s-bench.pd" % bench_name)
    if not os.path.exists(bench_pd):
        sys.exit("targets: %s does not exist -- run bench-gen.py" % bench_pd)

    # With a GUI, [print] goes to Pd's own window unless -stderr, and the runner
    # would see nothing. --auto-only has nobody to look at a window: -nogui.
    mode = ["-nogui"] if auto_only else ["-stderr"]

    # DSP on: every beat counter is threshold~ on a phasor~, so with it off
    # every count reads 0. On the device mother turns it on; here it is a panel
    # toggle nobody is present to tick. -send runs after the patches load.
    argv = [PD] + mode + ["-send", "pd dsp 1",
                          "-path", os.path.join(work, "patch"),
                          os.path.join(work, "patch", "main-dev.pd"),
                          bench_pd, _tap()]

    def teardown():
        lib_scratch.close()
        shutil.rmtree(work, ignore_errors=True)

    stream.say("  launching Pd%s ..." % ("" if auto_only else " with the GUI"))
    return Process(argv, stream.Go("127.0.0.1"), teardown, label="mac",
                   osc_port=osc_port)


def device(bench_name, auto_only, work):
    """The real rig: mother.pd, main.pd and the bench, as a third patch.

    It kills the running instrument, and `killall pd` strands the Launchpad in
    Programmer Mode with its own Settings menu locked out, so the teardown says
    how to restore it every time.
    """
    bench_pd = "test/bench/%s-bench.pd" % bench_name
    remote_pd = "%s/%s-bench.pd" % (REMOTE_DIR, bench_name)
    remote_tap = "%s/bench-tap.pd" % REMOTE_DIR
    stream.say("  copying %s and bench-tap.pd to %s ..." % (bench_pd, HOST))
    subprocess.run(["scp", "-q", bench_pd, _tap(),
                    "%s:%s/" % (HOST, REMOTE_DIR)], check=True)

    # The patch path in single quotes: the folder is /sdcard/Patches/!/..., and
    # `!` inside double quotes is a history event in an interactive zsh.
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
