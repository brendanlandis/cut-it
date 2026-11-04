"""The machinery every headless gate that copies the patch shares. Imported:

    import lib_scratch as S
    S.require("Cut It/u_map.pd")
    s = S.Scratch("/tmp/cutit-map-123")
    s.make(); s.state_dir(); s.midi_rewrite()
    S.drive("test/gate/map-assert-drive-gen.py", s.path("drive.pd"))
    S.run(s.path("capture.txt"), 40, "-nogui", ...)
    S.close()

It reads and rewrites records, not lines (lib_pd), so a box Pd wrapped across
two lines when it saved is counted like any other. "Cut It/" is never touched:
a built-in class has no side channel, so the only way to read what a patch
emitted is to swap the box out in a copy (the gate skill).

test/gate/scratch-gates.py holds what each gate does with this; the phone and
state gates drive it from their own analyzers.
"""
import os
import pwd
import re
import shutil
import socket
import subprocess
import sys

import lib_pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# The Mac's Pd is 0.57, the version the Organelle runs (ref/workflow.md); PD=
# points a run at another.
PD = os.environ.get("PD", os.path.expanduser(
    "~/Applications/Pd-0.57-0.app/Contents/Resources/bin/pd"))

# Every Pd a gate starts runs at the device's rate, the 44100 its .pdsettings
# sets. Pd 0.56 made 48000 the default, and a gate's Pd reads no preferences.
RATE = ("-r", "44100")

# The externals beyond vanilla, pdlua and ELSE, built for the Mac and kept in
# Pd's own user folder, ~/Library/Pd, as the device keeps them in
# /sdcard/PdExtraLibs (device/README.md, Lua and ELSE). Every Pd the suite
# starts gets the folder on its -path: the suite empties HOME, so Pd would not
# find it there, and this reads the account's home, not $HOME, for the same
# reason. CUTIT_PD_LIBS= points a run at another folder.
HOME = pwd.getpwuid(os.getuid()).pw_dir
LIBS = os.environ.get("CUTIT_PD_LIBS") or os.path.join(HOME, "Library", "Pd")
LIBS_PATH = ("-path", LIBS)

# lua.org's Lua 5.4, which runs the Lua halves of the gates (test/gate/lua/);
# LUA= points a run at another.
LUA = (os.environ.get("LUA") or shutil.which("lua5.4") or shutil.which("lua")
       or os.path.join(HOME, ".local", "bin", "lua"))

# ---------------------------------------------------------------------------
# The one MIDI inventory: an exact count per class, never "not zero", updated
# deliberately and never to make a red run green (the gate skill). It is every
# class that gets rewritten, inputs included: notein and ctlin have source stubs.
# Two [sysexin]: c_devid's, every device's inquiry reply, and m_launchpad's, the
# announcement a tap on Setup makes (launchpad-assert drives it).
MIDI_EXPECT = {"midiout": 8, "noteout": 2, "ctlout": 3, "pgmout": 1,
               "notein": 2, "ctlin": 3, "sysexin": 2}

# The MIDI objects with no stub: counted, so a new one cannot appear unannounced,
# and never rewritten. polytouchin's pressure path is uncovered
# (ref/device/launchpad.md, Open).
MIDI_INVENTORY = {"polytouchin": 1}

# The debug patch is a second deployable, and the counts above are scoped to
# "Cut It", so it needs its own. Three is all it takes: notein and ctlin are
# omni, and noteout's channel picks the port, so one reaches the Volca and the
# SP-404 both.
MIDI_DEBUG_EXPECT = {"notein": 1, "ctlin": 1, "noteout": 1}

# Every MIDI class Pd has, so scan_unknown can ask a closed question.
MIDI_ALL_CLASSES = ("notein ctlin pgmin bendin touchin polytouchin midiin sysexin "
                    "midirealtimein midiclkin noteout ctlout pgmout bendout touchout "
                    "polytouchout midiout").split()

# An object box and its class. The class ends at a space, the `;`, or the `,`
# before a box width (`midiout, f 12;`), so a box with arguments ([ctlout 123] in
# m_404) is not skipped; and negative coordinates count.
_OBJ = re.compile(r"^(#X obj -?\d+ -?\d+ )([^\s;,]+)(?=[\s;,])")


def spec_text(spec):
    """{"midiout": 9, ...} as the `midiout:9 ...` every message prints."""
    return " ".join("%s:%d" % kv for kv in spec.items())


def fail(*lines):
    """A broken harness, as opposed to a failed check: say why and exit 2."""
    for ln in lines:
        print(ln, file=sys.stderr)
    sys.exit(2)


def require(*paths):
    """Every file the gate needs, before it does anything else.

    A gate is meant to be built BEFORE the abstraction it tests, so its first run
    fails for a known reason -- that is a real failure, not a skip."""
    for p in paths:
        if not os.path.exists(os.path.join(ROOT, p)):
            fail("%s does not exist yet." % p,
                 "That is a real failure, not a skip: the gate is meant to be built",
                 "BEFORE the abstraction, so its first run fails for a known reason.")


def require_pd():
    if not os.access(PD, os.X_OK):
        fail("no Pd at %s -- set PD=..." % PD)
    if not os.path.isdir(os.path.join(LIBS, "pdlua")):
        fail("no pdlua in %s -- device/README.md, Lua and ELSE, builds it;" % LIBS,
             "set CUTIT_PD_LIBS=... to point at another folder.")


def lua(script, *args):
    """A Lua half of a gate, run from the repo root; -> its exit status."""
    try:
        version = subprocess.run([LUA, "-v"], stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT).stdout.decode()
    except OSError:
        version = ""
    if not version.startswith("Lua 5.4"):
        fail("no Lua 5.4 at %s -- device/README.md, Lua and ELSE, builds one;" % LUA,
             "set LUA=... to point at another.")
    sys.stdout.flush()
    return subprocess.call([LUA, script] + [str(a) for a in args], cwd=ROOT)


# ---------------------------------------------------------------------------
# The MIDI inventory, counted on records.
def _patch_files(d):
    """The .pd files of a patch folder, skipping the stubs themselves."""
    return sorted(os.path.join(d, f) for f in os.listdir(d)
                  if f.endswith(".pd") and not f.startswith("t_"))


def midi_counts(d):
    """{class: object boxes of it} across one patch folder, every class."""
    n = {}
    for f in _patch_files(d):
        for rec in lib_pd.read(f):
            m = _OBJ.match(rec)
            if m:
                n[m.group(2)] = n.get(m.group(2), 0) + 1
    return n


def _count_failed(want, cls, got):
    print("FAIL: expected %d [%s] box(es), found %d." % (want, cls, got), file=sys.stderr)
    print("      A LOWER count means assertions about it have gone vacuous;", file=sys.stderr)
    print("      a HIGHER one means a MIDI object no gate knows about.", file=sys.stderr)
    print("      Update MIDI_EXPECT in test/gate/lib_scratch.py deliberately,", file=sys.stderr)
    print("      never silently.", file=sys.stderr)


def check_counts(d, spec):
    """Counts only. True if every class in spec matches exactly."""
    have, ok = midi_counts(d), True
    for cls, want in spec.items():
        got = have.get(cls, 0)
        if got != want:
            _count_failed(want, cls, got)
            ok = False
        else:
            print("   %d [%s]" % (got, cls))
    return ok


def scan_unknown(d, known=None):
    """True unless a MIDI class present in the folder is named by neither list.

    `known` defaults to MIDI_EXPECT plus MIDI_INVENTORY.

    This is the half that cannot go vacuous: check_counts asks the patch about
    each class on a list, so a class nobody listed is invisible to it; this asks
    the list about every class Pd has.
    """
    known = set(known if known is not None else {**MIDI_EXPECT, **MIDI_INVENTORY})
    have, ok = midi_counts(d), True
    for cls in MIDI_ALL_CLASSES:
        got = have.get(cls, 0)
        if got and cls not in known:
            print("FAIL: %d [%s] box(es) in the patch, and NO gate knows." % (got, cls),
                  file=sys.stderr)
            print("      A MIDI object nobody inventoried is a way to talk to a", file=sys.stderr)
            print("      device that nothing is watching. Add it to MIDI_EXPECT in", file=sys.stderr)
            print("      test/gate/lib_scratch.py, give it a stub, and give it a", file=sys.stderr)
            print("      gate at the same time.", file=sys.stderr)
            ok = False
    if ok:
        print("   no MIDI class outside the inventory")
    return ok


# ---------------------------------------------------------------------------
def _records_replace(path, pattern, repl, why):
    """Rewrite one thing in one file of a scratch copy, by record, and PROVE IT
    LANDED: exactly one record must change. A rewrite that silently matched
    nothing leaves the gate asserting the shipped value and reporting it as the
    rewritten one; one that matched twice is a patch this gate was not written
    for. Either way the run stops here, with `why`."""
    recs = lib_pd.read(path)
    hits = 0
    for i, rec in enumerate(recs):
        # repl is literal text -- a path, a port -- never a template for re
        new, n = re.subn(pattern, lambda m: repl, rec)
        if n:
            recs[i], hits = new, hits + n
    if hits != 1:
        fail("FAIL: expected one match for %r in %s, found %d." % (pattern, path, hits),
             *why)
    _write(path, recs)


def _write(path, recs):
    """Records back to a file, one per line. Pd reads a record to its `;`, so
    where its own save had wrapped one is a matter of looks, not of meaning."""
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(recs) + "\n")


class Scratch:
    """One throwaway copy of a patch folder: work/patch and work/state. The UDP
    sink its u_net talks to stays open until the module's close()."""

    def __init__(self, work, src="Cut It"):
        # The state path becomes a Pd creation argument, where a space splits it.
        if re.search(r"\s", work):
            fail("FAIL: the scratch directory %r holds whitespace, and its path" % work,
                 "      becomes a Pd creation argument. Set TMPDIR to a path without.")
        self.work = work
        self.src = src
        self.patch = os.path.join(work, "patch")
        self.state = os.path.join(work, "state")

    def path(self, *parts):
        return os.path.join(self.work, *parts)

    def make(self):
        """Copy the patch, the stubs and mac-stubs; leave the state dir with its
        two files, empty."""
        os.makedirs(self.state, exist_ok=True)
        # Not the drum samples: a gate hears none, whatever is on this Mac (tools/samples.sh).
        shutil.copytree(os.path.join(ROOT, self.src), self.patch,
                        ignore=shutil.ignore_patterns("samples"))

        stubs = os.path.join(ROOT, "test", "stubs")
        names = sorted(f for f in os.listdir(stubs)
                       if f.startswith("t_") and f.endswith(".pd"))
        if not names:
            fail("FAIL: no stubs in test/stubs/ -- every rewritten box would",
                 "      fail to create and every assertion would be answered",
                 "      by an empty list.")
        for f in names:
            shutil.copy(os.path.join(stubs, f), self.patch)
        macs = os.path.join(ROOT, "mac-stubs")
        for f in sorted(os.listdir(macs)):
            if f.endswith(".pd"):
                shutil.copy(os.path.join(macs, f), self.patch)

        # state-dir.sh runs through [shell], a no-op stub on the Mac, so the two
        # files have to be made here or u_state prints on every run.
        for f in ("cut-it-auto.txt", "cut-it-manual.txt"):
            open(os.path.join(self.state, f), "w").close()
        return self

    def state_dir(self, port=None):
        """A private state directory and inbound port, in main-dev.pd's u_root box.

        main-dev.pd passes /tmp, which every run shares, and u_init restores a
        mode a previous run left there at about 3.5 s (item 232, the gate skill).
        Only one process can hold u_net's UDP port, so test/runner/gates.py hands
        each gate its own in CUTIT_INPORT; a gate run by hand keeps 9002.
        """
        port = int(port or os.environ.get("CUTIT_INPORT") or 9002)
        _records_replace(
            os.path.join(self.patch, "main-dev.pd"),
            re.escape("u_root 17 1 /tmp 33 49 9002;"),
            "u_root 17 1 %s 33 49 %d;" % (self.state, port),
            ["      Could not repoint main-dev.pd's state directory and port.",
             "      Without that, a previous run's saved mode changes what the map",
             "      does at 3.5 s and half the windows go silent -- item 232 --",
             "      and gates run side by side fight over one UDP port."])
        return self.net_off(port)

    def net_off(self, port=None):
        """Keep u_net's OSC off the house network (and the phone): send it to a
        sink here, 1000 above the inbound port. The sink has to be bound (sink()
        below). state_dir does this; a gate that builds its own harness around
        u_root calls it alone.
        """
        port = int(port or os.environ.get("CUTIT_INPORT") or 9002)
        _records_replace(
            os.path.join(self.patch, "u_root.pd"),
            re.escape("u_net 192.168.1.9 8000 "),
            "u_net 127.0.0.1 %d " % (port + 1000),
            ["      Could not point u_net away from the phone."])
        sink(port + 1000)
        return self

    def watch_fast(self):
        """The re-wire watch every tick instead of every 8 (16 s), so that it runs
        off the raw tick while nothing is lost is visible in every window of the
        presence run. The shipped 8 is asserted statically in presence-assert.py.
        """
        _records_replace(
            os.path.join(self.patch, "u_root.pd"),
            re.escape("u_present 4000 2000 33 8") + r"(?=[\s;,])",
            "u_present 4000 2000 33 1",
            ["      watch_fast: the rewrite did not land in the scratch u_root.pd."])

    def scale_present(self):
        """u_present's settle and tick divided by ten, so its 72 s bound (eight
        wire.sh attempts, then the give-up at tick 33) happens in about seven.
        The counts stay as shipped, or the run would judge another patch.

        ⚠️ A 400 ms settle no longer clears u_init's last stage, so u_init's own
        boot fork at 1500 ms lands between recovery forks 1 and 2. The bound
        driver's windows allow for it; a gate counting forks per window must too.
        """
        _records_replace(
            os.path.join(self.patch, "u_root.pd"),
            re.escape("u_present 4000 2000 33 "),
            "u_present 400 200 33 ",
            ["      Could not scale u_present's settle and tick.",
             "      Without that the give-up is 72 s away, the run quits at 9 s,",
             "      and every count below is answered by a recovery that never",
             "      got started -- which looks exactly like a bound that fires",
             "      nothing."])

    def map_rows(self, rows):
        """Rows put BEFORE the scratch map's own rather than replacing it, so the
        shipped rows stay under test too, and a gate's row wins over a shipped
        one for the same mode and control: the first row wins (map.md)."""
        p = os.path.join(self.patch, "cut-it-map.txt")
        with open(p, encoding="utf-8") as fh:
            body = fh.read()
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("".join(r + "\n" for r in rows) + body)

    def shell_stub(self):
        """The counting shell stub, over mac-stubs/shell.pd (which swallows the
        command). [shell] is an external, so a file of that name on the path wins
        and no box needs rewriting.

        ⚠️ The rename to shell.pd happens here only. On the device a shell.pd in
        the patch folder would shadow the real external, and wire.sh would stop
        running without a word.
        """
        src = os.path.join(ROOT, "test", "stubs", "t_shell.pd")
        try:
            shutil.copyfile(src, os.path.join(self.patch, "shell.pd"))
        except OSError as e:
            fail("FAIL: could not install the counting shell stub -- %s." % e,
                 "      Without it mac-stubs/shell.pd swallows the command and every",
                 "      fork assertion is answered by silence.")

    def midi_rewrite(self, spec=None, out=None):
        """Rewrite every class in spec (MIDI_EXPECT by default) to its printing
        stub, asserting the exact count first. True if every count matched.

        It rewrites them all even for a gate that reads one, so every scratch
        copy enforces the whole inventory. `spec` is MIDI_DEBUG_EXPECT for the
        debug patch.

        `out` collects the per-class lines instead of printing them, for a gate
        that makes two copies and shows one inventory.
        """
        spec = MIDI_EXPECT if spec is None else spec
        say = out.append if out is not None else print
        have, ok, swap = midi_counts(self.patch), True, set()
        for cls, want in spec.items():
            got = have.get(cls, 0)
            if got != want:
                _count_failed(want, cls, got)
                ok = False
                continue
            swap.add(cls)
            say("   %d [%s] -> [t_%s]" % (got, cls, cls))
        for f in _patch_files(self.patch):
            recs, hit = lib_pd.read(f), False
            for i, rec in enumerate(recs):
                m = _OBJ.match(rec)
                if m and m.group(2) in swap:
                    recs[i] = m.group(1) + "t_" + rec[len(m.group(1)):]
                    hit = True
            if hit:
                _write(f, recs)
        return ok


def drive(gen, out, *args, also=()):
    """Run a driver generator and prove it wrote what the run will load: with no
    driver, its `; pd quit` never fires and the gate hangs (the gate skill).

    `also` is (path, why) for each further file the generator must write, such
    as a harness, without which the driver talks to nothing.
    """
    rc = subprocess.call([sys.executable, os.path.join(ROOT, gen), out]
                         + [str(a) for a in args],
                         stdout=subprocess.DEVNULL, cwd=ROOT)
    if rc != 0:
        fail("FAIL: %s errored -- see the traceback above." % gen)
    if not os.path.isfile(out):
        fail("FAIL: %s wrote no driver to %s." % (gen, out))
    for p, why in also:
        if not os.path.isfile(p):
            fail("FAIL: the generator wrote no harness to %s." % p, *why)

def run(cap, dog, *argv):
    """Pd with argv at the device's rate and the libs on its path, its console
    into cap, killed at `dog` seconds.

    A run the watchdog ends is said out loud; its capture stops wherever Pd
    was, and the analyzer's window count fails it.
    """
    with open(cap, "wb") as fh:
        p = subprocess.Popen([PD] + list(RATE) + list(LIBS_PATH) + list(argv),
                             stdout=fh, stderr=subprocess.STDOUT, cwd=ROOT)
        try:
            p.wait(timeout=dog)
        except subprocess.TimeoutExpired:
            p.kill()
            p.wait()
            print("watchdog: Pd was still running after %d s and was killed "
                  "-- its driver never reached `pd quit`." % dog, file=sys.stderr)
    return p.returncode


def sink(port):
    """Bind a UDP socket on 127.0.0.1:port, held until close(); one per port per
    process, so a gate that makes two copies (map, presence, recover) hands
    both the same socket.

    Under Pd 0.49, with nothing bound, loopback answered with ICMP, which tore
    u_net's socket down (item 114) and raised its net-link-down warning mid-run.
    0.57 keeps the socket and the warning is gone (2026-11-03); the sink stays,
    so u_net's OSC lands somewhere known (test/README.md, the shared machinery).
    """
    port = int(port)
    if port in _SINKS:
        return _SINKS[port]
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.bind(("127.0.0.1", port))
    except OSError as e:
        s.close()
        fail("FAIL: could not bind u_net's sink on 127.0.0.1:%d -- %s." % (port, e),
             "      Another process holds it: two gates were given one port.")
    _SINKS[port] = s
    return s


_SINKS = {}


def close():
    """Every sink this process holds."""
    for s in _SINKS.values():
        s.close()
    _SINKS.clear()


def work_dir(name):
    """${TMPDIR:-/tmp}/cutit-<name>-<pid>, as every gate has always used."""
    return os.path.join(os.environ.get("TMPDIR") or "/tmp",
                        "cutit-%s-%d" % (name, os.getpid()))
