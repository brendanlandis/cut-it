#!/usr/bin/env python3
"""Where a bench's console lines come from, and how GO is sent.

Imported by run.py. One interface, three implementations -- a replay file today,
a Pd process on the Mac and one over ssh in Phase B -- so the step loop is written
once and never learns which it is talking to.

⛔ REPLAY IS NOT A TOY, IT IS THE ONLY THING THAT EVER EXERCISES THE FAILURE
PATHS. A successful hardware run never stalls, never desyncs and is never
interrupted, so on hardware alone the code handling those three could be dead
and every run would look exactly the same. Reading the stream from a file lets a
gate drive a truncated transcript, an out-of-order one and an empty one in under
a second, on a Mac, with no device.
"""
import collections
import socket
import sys
import time

# How many of the last console lines a stall report shows. Enough to see which
# step the patch thought it was on, short enough to read.
TAIL = 6


class Stalled(Exception):
    """No line arrived in time. ⚠️ Two shapes, and they must be told apart --
    see run.py, where "the bench never loaded" and "stalled mid-run" get
    different advice because they have different causes."""


class Source(object):
    """The interface. `readline` returns a line without its newline, or None
    when nothing arrived before the deadline."""

    # ⛔ HOW LONG THE INSTRUMENT TAKES TO FINISH BOOTING, BEFORE THE FIRST GO.
    # u_init wires MIDI, restores saved state at about 3.5 s and hands the OLED
    # footer over at about four seconds -- and the bench announces step 1 half a
    # second after load. A person takes long enough to read a PASS IF that this
    # never arises; a runner does not, and the first three steps then get judged
    # against a screen still saying `booting` and `wiring`. Measured that way:
    # display 3's OLED predicate reported the boot frames as its evidence.
    boot_settle = 0.0

    # ⛔ IS THERE REAL TIME ON THE OTHER END? A live Pd makes the runner WAIT for
    # a screen to redraw or a ten-second counter to latch. A recording has
    # already happened: every line is available at once, so a wall-clock drain
    # against it does not wait -- it swallows the whole rest of the transcript
    # and every later step reports "not run". Measured exactly that way.
    realtime = True

    # ⛔ WHAT A STALL REPORT IS MADE OF, and none of it existed until a real one
    # said nothing. The only bench verdict this project has ever recorded is a
    # launchpad step-1 `interrupted` reading "stalled mid-run: GO sent, no fired
    # line" -- which names the symptom and not one thing about the cause. A
    # stall has three plausible causes and they are told apart by three
    # different facts: GO never left (the sender), the patch is not there (an
    # empty tail), or the runner is reading faster than the patch is printing (a
    # backlog). Report all three and the next one diagnoses itself.
    gos = 0

    def _note(self, line):
        """Remember the last few lines, for a stall report."""
        if getattr(self, "seen", None) is None:
            self.seen = collections.deque(maxlen=TAIL)
        self.seen.append(line)

    def pending(self):
        """How far behind the reader is, or None where that has no meaning."""
        return None

    def diagnose(self):
        """Everything known about why nothing arrived. -> a block of lines."""
        out = ["    GO sent %d time(s) this run" % self.gos]
        n = self.pending()
        if n is not None:
            out.append("    %d line(s) waiting unread -- %s"
                       % (n, "the runner is ahead of the patch" if n else
                          "nothing is queued, so nothing was sent"))
        seen = getattr(self, "seen", None)
        if seen:
            out.append("    the last %d line(s) seen:" % len(seen))
            out.extend("      %s" % ln.strip() for ln in seen)
        else:
            # ⛔ AN EMPTY TAIL IS THE MOST DIAGNOSTIC CASE OF ALL. Nothing has
            # been read at any point, so this is not a stall in a running bench
            # -- it is a bench that is not on the other end.
            out.append("    NOTHING has been read on this stream at all")
        return "\n".join(out)

    def readline(self, timeout):
        raise NotImplementedError

    def go(self):
        raise NotImplementedError

    def rerun(self):
        """Fire the current step again without advancing. -> did it happen?

        ⚠️ FALSE FROM A REPLAY, and honestly so: a recorded console cannot be
        asked to do anything twice. The caller says so rather than pretending
        the step ran again.
        """
        return False

    def hold(self, on):
        """Keep the current step's result on screen while a verdict is open.

        ⚠️ A NO-OP WHERE THERE IS NOTHING TO RE-FIRE -- a replay, and paper mode.
        Overridden by targets.Process, which is the only Source with a patch on
        the other end.
        """

    def close(self, quiet=False):
        """⚠️ `quiet` is honoured by targets.Process -- see there."""

    # -- shared -------------------------------------------------------------
    def wait_for(self, pattern, timeout, collect=None):
        """Read until `pattern` matches. -> (match, line).

        Every line seen on the way is appended to `collect` if given -- that
        list is the predicate window, so nothing between two markers is thrown
        away before a predicate has had the chance to look at it.
        """
        end = time.time() + timeout
        while True:
            line = self.readline(max(0.0, end - time.time()))
            if line is None:
                raise Stalled()
            if collect is not None:
                collect.append(line)
            m = pattern.search(line)
            if m:
                return m, line
            if time.time() >= end:
                raise Stalled()


class Replay(Source):
    """A recorded console, read as if it were live.

    ⚠️ END OF FILE IS A STALL, NOT A CLEAN FINISH, and that is the whole point of
    the truncated fixture: a transcript that stops at step 7 must make the runner
    say STALL rather than quietly report a pass on the seven it did see.
    """

    realtime = False

    def __init__(self, path):
        with open(path, encoding="utf-8", errors="replace") as fh:
            self.lines = fh.read().splitlines()
        self.i = 0
        self.gos = 0

    def readline(self, timeout):
        if self.i >= len(self.lines):
            return None
        self.i += 1
        self._note(self.lines[self.i - 1])
        return self.lines[self.i - 1]

    def pending(self):
        return len(self.lines) - self.i

    def go(self):
        self.gos += 1


class Go(object):
    """The GO sender, and there is one implementation of it.

    A bench binds [netreceive 9998 1] unconditionally -- on the Mac exactly as on
    the device -- so one UDP datagram drives every target and the host is the
    only thing that changes.

    ⛔ THE TRAILING NEWLINE IS REQUIRED. `b'live ;'` with a space and no newline
    is accepted by the socket and DROPPED by netreceive, which looks precisely
    like a dead bench (item 250).

    ⚠️ AND IT IS NOT netcat. BSD nc with -w0 exits before the datagram is
    flushed, and -w1 was measured to fail here too, while the port IS bound and
    the bench IS fine. The device cannot send to itself either: its busybox has
    no nc at all. A socket send is deterministic.
    """

    def __init__(self, host, port=9998):
        self.host, self.port = host, port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send(self, word="go"):
        """`go` advances the bench. `rerun` fires the CURRENT step again.

        ⚠️ Both go to the same [netreceive], and the bench routes them apart --
        so a repeat travels the path a GO already proved works, rather than a
        second mechanism that only ever runs when somebody presses r.
        """
        self.sock.sendto(("%s;\n" % word).encode(), (self.host, self.port))

    def close(self):
        self.sock.close()


def keystrokes(path):
    """--keys: the verdicts, scripted, for the self-test.

    ⛔ IT RUNS OUT RATHER THAN REPEATING. A provider that returned its last key
    forever would let a fixture pass by accident once the runner asked one more
    question than the fixture answered -- so exhaustion raises EOF, which the
    prompt already treats as quit.
    """
    with open(path, encoding="utf-8") as fh:
        pending = fh.read().splitlines()

    def provider(_prompt=""):
        if not pending:
            raise EOFError
        return pending.pop(0)
    return provider


def console(prompt=""):
    """The real thing: a person at a keyboard."""
    return input(prompt)


ask_line = console


def use(provider):
    """⛔ EVERY VERDICT COMES THROUGH HERE, so the self-test drives exactly the
    code a person drives. A separate scripted path would be a second
    implementation, and the one that never runs is the one that rots."""
    global ask_line
    ask_line = provider


def prompt(text):
    """⚠️ THE PROMPT IS WRITTEN AND FLUSHED BEFORE THE READ BLOCKS.

    input(text) writes its argument without a newline, and a partial line can
    sit in the buffer until something else flushes it -- so the runner appears
    to hang silently at a step it has in fact already described and is waiting
    on. Harmless at a terminal, wrong down a pipe, and it made the interrupt
    fixture wait out its whole deadline for a prompt that had been issued.
    """
    sys.stdout.write(text)
    sys.stdout.flush()
    try:
        return ask_line("")
    except EOFError:
        print()
        raise


def say(*a):
    print(*a)
    sys.stdout.flush()
