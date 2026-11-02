"""The machinery every headless gate that copies the patch shares. Imported:

    import lib_scratch as S
    S.require("Cut It/u_map.pd")
    s = S.Scratch("/tmp/cutit-map-123")
    s.make(); s.state_dir(); s.midi_rewrite()
    s.drive("test/gate/map-assert-drive-gen.py", s.path("drive.pd"))
    s.run(s.path("capture.txt"), 40, "-nogui", ...)

WHY IT EXISTS. Every gate needs the same five things -- a scratch copy of the
patch, MIDI object boxes rewritten to printing stubs, a private state directory,
a generated driver, and a watchdogged Pd run -- and two of them once had two
different, drifted implementations: the old phase 6 gate rewrote [midiout] with
an anchored regex and a non-zero count, the split gates rewrote four other
classes with an argument-tolerant regex and an exact count. ⛔ THE WEAKER ONE IS
NOT A STYLE DIFFERENCE. It is three of the four ways a gate passes vacuously,
shipped and green. There is one implementation, and it is the strict one.

⛔ IT READS AND REWRITES RECORDS, NOT LINES, AND FORKS NOTHING TO DO IT. It was
lib-scratch.sh until 2026-11-02, and counting and rewriting the MIDI boxes there
forked hundreds of grep and sed per scratch copy: a gate whose Pd ran 8 s took
about 48 s with nineteen copies side by side. Records come from lib_pd, so a box
Pd 0.49 wrapped across two lines when it saved is counted like any other -- a
line-anchored grep never saw it at all.

⚠️ "Cut It/" IS NEVER TOUCHED. Everything happens in a scratch copy that is
thrown away, because a built-in Pd class has no side channel -- Pd resolves the
class table before it looks for a file, so a midiout.pd on the search path is
simply ignored. Measured both ways.

test/gate/scratch-gates.py holds what each gate does with this; the phone and
state gates drive it from their own analyzers; test/runner/targets.py makes a
bench's copy with it.
"""
import os
import re
import shutil
import socket
import subprocess
import sys

import lib_pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PD = os.environ.get("PD", "/Applications/Pd-0.49-1.app/Contents/Resources/bin/pd")

# ---------------------------------------------------------------------------
# ⛔ THE EMITTER INVENTORY, AND IT LIVES IN EXACTLY ONE PLACE.
#
# An EXACT count per class, never "not zero". A LOWER count means boxes have
# disappeared and the assertions about them have gone vacuous; a HIGHER one means
# a new MIDI emitter no gate knows about. Both are failures and both are silent
# without this.
#
# The drift this replaces: the old phase 6 gate's comment claimed five [midiout]
# where the patch has six, and nothing noticed, because it only ever asserted the
# count was not zero.
#
# ⚠️ UPDATE THIS DELIBERATELY, NEVER TO MAKE A RED RUN GREEN. A gate going red
# here is the invariant working.
#
# ⚠️ IT IS "EVERY CLASS THAT GETS REWRITTEN", not "every emitter" -- notein and
# ctlin are INPUTS and they are here because test/stubs/ has a source stub for
# each. The name is older than the notein stub and is kept because every gate,
# every error message and the gate skill all cite it.
# midiout went 6 -> 8 when m_nano and m_404 gained device presence: an inquiry
# has to leave through the m_'s OWN port, and midiout is the one MIDI object that
# takes the port as a number rather than encoding it in the channel.
MIDI_EXPECT = {"midiout": 9, "noteout": 2, "ctlout": 3, "pgmout": 1,
               "notein": 2, "ctlin": 3, "sysexin": 1}

# The MIDI objects with no stub. Counted so the inventory is complete and a new
# one cannot appear unannounced -- never rewritten, because there is nothing to
# rewrite them to.
#
# [sysexin] used to be the only entry and it moved UP into MIDI_EXPECT when
# t_sysexin landed: the hot-swap work needed to DRIVE a device-inquiry reply,
# because a reply is the only evidence of presence there is and it arrives on a
# MIDI input, where there is no bus to fake.
#
# ⛔ [polytouchin] WAS NEVER IN EITHER LIST, AND NOTHING NOTICED. It is
# m_launchpad's polyphonic aftertouch decode -- "the most expressive control on
# the rig" by its own page -- and the inventory claimed "these are all the MIDI
# objects in the patch" the whole time it was missing. Found by scan_unknown on
# its first run, which is the check that asks the question in the direction that
# can actually answer it. ⬜ It is COUNTED and not covered: a t_polytouchin would
# be the same shape as t_ctlin, and the pressure path it would unlock is nobody's
# yet. See ref/device/launchpad.md.
MIDI_INVENTORY = {"polytouchin": 1}

# ⛔ THE DEBUG PATCH IS A SECOND DEPLOYABLE AND IT NEEDS ITS OWN INVENTORY. Every
# count above is scoped to "Cut It", so a [notein] in "Cut It Debug" is not
# "uncounted" -- it is INVISIBLE, and the one gate whose entire claim is "these
# are all the MIDI objects in the patch" would keep saying so while a second
# patch grew ways to talk to the rig that nothing watched. That is the exact
# failure midi-emitters-assert exists to prevent, arrived at by adding a
# directory rather than an object.
#
# ⚠️ THREE OBJECTS AND NO MORE, and the smallness is the point: the debug patch
# reads what arrives and fires two settled probes. notein and ctlin are OMNI, so
# one of each covers all four ports; noteout's channel encodes the port, so one
# of it reaches both the Volca on 49 and the SP-404 on 33.
MIDI_DEBUG_EXPECT = {"notein": 1, "ctlin": 1, "noteout": 1}

# ⛔ EVERY MIDI CLASS Pd HAS, so "these are all the MIDI objects in the patch" can
# be checked as a CLOSED question rather than by listing what we expect and
# hoping the list is complete. The old inventory could only ever find a drift in
# a class someone had already thought of.
MIDI_ALL_CLASSES = ("notein ctlin pgmin bendin touchin polytouchin midiin sysexin "
                    "midirealtimein midiclkin noteout ctlout pgmout bendout touchout "
                    "polytouchout midiout").split()

# An object box and its class. ⚠️ THE ARGUMENTS ARE NOT OPTIONAL IN THIS
# PATTERN'S CARE: phase 6's regex was anchored so the class name had to end the
# line, which silently skipped every box with creation arguments -- and the
# patch has one, [ctlout 123] in m_404. An anchored regex there would have made
# its panic assertion vacuous. So the class ends at a space, at the `;`, or at
# the `,` Pd writes before a box width (`midiout, f 12;`), and negative
# coordinates count: a box dragged above or left of the canvas is still a box.
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

    ⛔ THE LIST IS AN ARGUMENT, NEVER A GLOBAL SOMEBODY OVERRIDES. In the shell
    version `MIDI_EXPECT=... midi_scan_unknown` looked like a scoped override and
    was not: in dash and busybox ash a variable assignment prefixed to a FUNCTION
    call persists, so the debug patch's three-class list silently became the
    instrument's for everything after it, and the closing summary printed the
    wrong inventory while exiting 0.

    ⛔ THIS IS THE HALF THAT CANNOT GO VACUOUS. check_counts walks a list we wrote
    and asks the patch about each entry, so a class nobody thought of is invisible
    to it -- and once MIDI_INVENTORY emptied, the "counted only" arm of
    midi-emitters-assert became a loop over nothing that returned 0. This walks
    the CLASSES and asks the list, which is the closed question the gate has
    always claimed to answer.
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
        new, n = re.subn(pattern, repl, rec)
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
    sink its u_net talks to stays open until close()."""

    def __init__(self, work, src="Cut It"):
        # ⛔ NO WHITESPACE IN THE WORK DIR. Its state path goes into a Pd box as a
        # creation argument, and a space there would split it into two atoms.
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
        shutil.copytree(os.path.join(ROOT, self.src), self.patch)

        # ⛔ COPY THE STUBS WITH A HARD CHECK. A missing stub used to sail past an
        # unchecked cp and surface six windows later as confusing assertion
        # failures -- the right verdict reached by the wrong route, which costs the
        # time of a real debugging session. One clear line instead.
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
        """⛔ OWN YOUR STATE DIRECTORY, AND ASSERT THE REPOINT WORKED. main-dev.pd
        passes /tmp, which every run on the machine shares, and u_init restores
        saved state at about 3.5 s. A previous test that changed mode leaves it in
        that file, the restore republishes it mid-run, and every row keyed to
        another mode stops matching from that instant. It cost a wrong diagnosis
        once already: item 232.

        ⛔ AND OWN YOUR INBOUND PORT, in the same box. u_net listens on
        main-dev.pd's last argument, 9002, and only one process can hold a UDP
        port, so gates run side by side would print `bind: Address already in
        use`. test/runner/gates.py hands each gate its own in CUTIT_INPORT; a gate
        run by hand keeps 9002.
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

        # ⛔ AND KEEP u_net OFF THE HOUSE NETWORK. u_root.pd sends to the phone at
        # 192.168.1.5:8000, so a copy left alone sends its OSC there for the whole
        # run, and draws on the phone if PdParty is up. It goes to a sink on this
        # machine instead, 1000 above the inbound port so gates side by side each
        # have their own. ⚠️ THE SINK IS NOT OPTIONAL: with nothing bound, loopback
        # answers with ICMP and u_net raises `warn u_net net-link-down` in every
        # gate (sink() below). phone_mirror repoints it again for a bench that
        # reads what u_net sends.
        sink = port + 1000
        _records_replace(
            os.path.join(self.patch, "u_root.pd"),
            re.escape("u_net 192.168.1.5 8000 "),
            "u_net 127.0.0.1 %d " % sink,
            ["      Could not point u_net away from the phone."])
        self.sink(sink)
        return self

    def watch_fast(self):
        """⛔ MAKE THE HEARTBEAT OBSERVABLE WITHOUT CHANGING WHAT IT IS. The
        re-wire watch fires every 8 ticks, so 16 s at the shipped tick -- and the
        main presence run is about 40 s wide, which is two fires landing wherever
        the arithmetic puts them. The claim being tested is NOT the interval; it
        is that the watch runs off the RAW tick rather than through the
        recovery's spigot, so it fires while nothing is lost. Firing every tick
        makes that observable in every window.

        ⛔ THE SHIPPED INTERVAL IS ASSERTED SEPARATELY AND STATICALLY, by reading
        u_root.pd in presence-assert.py. Scaling a number in a scratch copy without
        checking the real one somewhere is how a gate comes to test a patch that
        does not ship.
        """
        _records_replace(
            os.path.join(self.patch, "u_root.pd"),
            re.escape("u_present 4000 2000 33 8") + r"(?=[\s;,])",
            "u_present 4000 2000 33 1",
            ["      watch_fast: the rewrite did not land in the scratch u_root.pd."])

    def scale_present(self):
        """⛔ SCALE THE TWO TIMES AND LEAVE THE COUNTS ALONE.

        WHY IT IS NEEDED AT ALL. u_present's bound -- eight wire.sh attempts and
        then a give-up -- is 72 seconds wide at the shipped tick, and no gate in
        this suite runs that long. So the only claim presence-assert could make
        about it was arithmetic read off [moses 33], which is not a claim about a
        run at all. u_present takes the settle, the tick and the give-up as
        creation arguments PRECISELY so a scratch copy can divide the two TIMES by
        ten and reach counter 33 in about seven seconds.

        ⛔ ONLY THE SETTLE AND THE TICK MOVE. 3 (c_presence's missed-tick
        threshold) and 33 (the give-up) are the SHIPPED counts, and a gate that
        scaled those would be asserting a different patch than the one that ships
        -- which is the most expensive kind of green there is.

        ⚠️ IT DELIBERATELY BREAKS THE SETTLE'S COUPLING TO u_init, and that is safe
        HERE and nowhere else. The 4000 ms settle exists so the first re-wire lands
        past u_init's last stage; at 400 ms it does not, so u_init's own boot fork
        at 1500 ms lands BETWEEN recovery forks 1 and 2. The bound driver's windows
        are drawn knowing that. ⛔ Do not reuse this in a gate that counts forks
        per window without accounting for it.
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

    def phone_mirror(self, port):
        """⛔ POINT u_net AT THIS MACHINE, AND ASSERT THE REPOINT WORKED.

        WHY IT IS NEEDED AT ALL. u_net sends to the phone, so on a live run the
        Mac cannot see those datagrams -- a tap on the device would prove what
        u_net was OFFERED, not what it FILTERED, and the filtering is the whole
        subject. Repointing it at localhost in a throwaway copy gives real OSC
        verdicts with no phone in the room. ⚠️ It answers a DIFFERENT question
        from a device run with a real phone, and neither replaces the other.

        ⛔ A SILENT MISS HERE IS THE WORST OUTCOME: every datagram would go to a
        real address on the network and the predicate would read an empty socket,
        which looks exactly like u_net being broken.
        """
        _records_replace(
            os.path.join(self.patch, "u_root.pd"),
            r"u_net [0-9.]+ [0-9]+ ",
            "u_net 127.0.0.1 %d " % port,
            ["      Could not repoint u_net at localhost.",
             "      Without that every datagram goes to a real address and the",
             "      predicate reads an empty socket -- which looks exactly like",
             "      u_net being broken."])

    def sink(self, port):
        return sink(port)

    def map_rows(self, rows):
        """Rows APPENDED to the scratch map rather than replacing it, so the
        shipped rows stay under test too."""
        p = os.path.join(self.patch, "cut-it-map.txt")
        with open(p, encoding="utf-8") as fh:
            body = fh.read()
        if body and not body.endswith("\n"):
            body += "\n"            # or the first row joins the shipped last one
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(body + "".join(r + "\n" for r in rows))

    def shell_stub(self):
        """⛔ THE COUNTING SHELL STUB, COPIED UNDER THE NAME PD WILL LOOK FOR.
        [shell] is an EXTERNAL, not a built-in, so unlike ctlin and midiout it
        resolves from the search path and a file of that name simply wins -- no
        box rewriting needed. make() has already put mac-stubs/shell.pd here,
        which deliberately SWALLOWS the command so a syntax check stays silent;
        this one reports it so a gate can count it. Without it every fork
        assertion is answered by silence, which is also what the bug looks like.

        ⚠️ THE RENAME HAPPENS HERE AND NOWHERE ELSE. The repo copy stays
        t_shell.pd because a file named shell.pd anywhere is a live hazard:
        reaching the patch folder on the device it would shadow the real external
        and every aconnect in wire.sh would silently stop happening.
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

        ⚠️ IT REWRITES THEM ALL, even for a gate that reads only one. That is
        deliberate: it costs nothing -- a stub only prints -- and it means every
        gate that makes a scratch copy enforces the whole inventory, so a new
        emitter cannot be added without some gate going red.

        ⚠️ THE SPEC IS AN ARGUMENT ONLY BECAUSE THERE ARE TWO DEPLOYABLES. The
        debug patch has three MIDI objects and the instrument has twenty-one, so
        one shared count would be wrong for both -- see MIDI_DEBUG_EXPECT.

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

    def drive(self, gen, out, *args, also=()):
        """Run a driver generator and prove it wrote what the run will load.

        ⛔ CHECK THE GENERATOR SUCCEEDED. Unchecked, the failure mode is the worst
        kind: the driver is never written, Pd loads a file that does not exist,
        the "; pd quit" that lives in that file never fires, and the gate HANGS
        FOREVER instead of failing. A gate that hangs is worse than one that
        fails.

        `also` is (path, why) for each further file the generator must write --
        a harness beside the driver, whose absence is the worst failure of all:
        Pd loads a driver that talks to nothing and every count comes back 0.
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

    def run(self, cap, dog, *argv):
        """Pd with argv, its console into cap, killed at `dog` seconds.

        ...and a watchdog on every headless run, so that no future variant of the
        generator mistake above can hang instead of failing. A run the watchdog
        had to end is said out loud: its capture stops wherever Pd was, and the
        analyzer's window count is what fails it.
        """
        with open(cap, "wb") as fh:
            p = subprocess.Popen([PD] + list(argv), stdout=fh,
                                 stderr=subprocess.STDOUT, cwd=ROOT)
            try:
                p.wait(timeout=dog)
            except subprocess.TimeoutExpired:
                p.kill()
                p.wait()
                print("watchdog: Pd was still running after %d s and was killed "
                      "-- its driver never reached `pd quit`." % dog, file=sys.stderr)
        return p.returncode

    def close(self):
        close()


def sink(port):
    """Bind a UDP socket on 127.0.0.1:port, held until close() -- ONE PER PORT
    PER PROCESS, so a gate that makes two copies one after the other (map,
    presence, recover) hands both the same socket rather than failing to bind
    the second.

    ⛔ IT EXISTS BECAUSE THREE GATES SILENTLY DEPENDED ON THE MAC'S LAN. u_net
    pointed at a literal phone address, and a datagram to an address that
    answers with ICMP port-unreachable TEARS THE SOCKET DOWN -- item 114 --
    which raises `warn u_net net-link-down`. That alert takes the OLED footer
    and lands in the error log, so oled-assert and err-assert failed on
    whichever window it happened to hit, with a message about u_net that had
    nothing to do with what either gate tests.

    ⚠️ IT PASSED FOR MONTHS BY LUCK. Nothing on the network answered, the ICMP
    never came back, and the socket stayed up. The day something did answer,
    two gates went red and pointed at the wrong module.

    ⚠️ REPOINTING ALONE IS NOT ENOUGH, which is the trap here. Sending to
    127.0.0.1 with nothing bound is the WORST case -- the local stack answers
    with ICMP immediately and reliably. The socket has to actually exist
    before Pd starts. phone-assert.py binds first for exactly this reason.

    ⚠️ IT IS A SOCKET IN THIS PROCESS, NOT A BACKGROUND ONE. The shell version
    forked a python sleeper that outlived the gate by up to two minutes and
    died unseen behind a /dev/null redirect if its bind failed. Here a failed
    bind stops the gate with a reason, and the socket goes when the gate does.
    ⚠️ The sleeper set SO_REUSEADDR "so a lingering sink cannot stop the next
    one binding". On macOS it does not do that for UDP -- measured 2026-11-02, a
    second bind on a held port still raises EADDRINUSE -- so the bind is checked
    instead of trusted.
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
             "      With nothing listening there, loopback answers with ICMP and",
             "      u_net raises net-link-down in the middle of the run.")
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
