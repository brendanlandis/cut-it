#!/usr/bin/env python3
"""Where a bench's console lines come from, and how GO is sent. Imported by
run.py.

One interface and three sources: a replay file, a Pd on the Mac, a Pd over ssh.
The replay is what lets runner-assert drive the truncated, out-of-order and
empty transcripts that a good hardware run never produces.
"""
import collections
import socket
import sys
import time

# How many of the last console lines a stall report shows.
TAIL = 6

# How many lines a patch may say without answering before wait_for gives up.
# Only lines after the question count: run.py flushes the queue before every GO.
LINE_CAP = 2000


class Stalled(Exception):
    """Nothing answered, and why. `silence` is a dead console: the patch is
    gone. `cap` is a console still talking that has not answered: a wedged
    bench, or the wrong question. They want opposite responses."""

    def __init__(self, why="silence"):
        Exception.__init__(self, why)
        self.why = why


class Source(object):
    """The interface. `readline` returns a line without its newline, or None
    when nothing arrived before the deadline."""

    # How long the instrument takes to finish booting before the first GO:
    # u_init restores state at ~3.5 s and hands over the OLED footer at ~4 s,
    # while a bench announces step 1 half a second after load. Without it the
    # first steps are judged against a screen still saying `booting`.
    boot_settle = 0.0

    # Is there real time on the other end? A recording has every line at once,
    # so a wall-clock drain against it would swallow the rest of the transcript.
    realtime = True

    # A stall report tells three causes apart: GO never left (gos), the patch
    # is not there (an empty tail), the runner is ahead of the patch (a backlog).
    gos = 0

    # A console quiet for five seconds is gone; one printing every 40 ms has
    # simply not answered yet.
    last_at = None

    def _note(self, line):
        """Remember the last few lines, for a stall report."""
        if getattr(self, "seen", None) is None:
            self.seen = collections.deque(maxlen=TAIL)
        self.seen.append(line)
        self.last_at = time.time()

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
        if self.last_at is not None and self.realtime:
            gap = time.time() - self.last_at
            out.append("    the last line arrived %.1f s ago -- %s"
                       % (gap, "the console has gone quiet" if gap > 1.0 else
                          "the console is still alive, it just has not answered"))
        seen = getattr(self, "seen", None)
        if seen:
            out.append("    the last %d line(s) seen:" % len(seen))
            out.extend("      %s" % ln.strip() for ln in seen)
        else:
            # Not a stall in a running bench: a bench that is not there.
            out.append("    NOTHING has been read on this stream at all")
        return "\n".join(out)

    def readline(self, timeout):
        raise NotImplementedError

    def go(self):
        raise NotImplementedError

    def rerun(self):
        """Fire the current step again without advancing. -> did it happen?
        False from a replay: a recording cannot do anything twice."""
        return False

    def hold(self, on):
        """Keep the current step's result on screen while a verdict is open.
        Nothing to re-fire here; targets.Process overrides it."""

    def where(self):
        """Ask the bench which step it is on. -> did it happen? False from a
        replay, as `rerun` is."""
        return False

    def show(self):
        """Ask the bench to describe its current step again. -> did it happen?"""
        return False

    def flush(self):
        """Throw away everything already queued. -> how many lines went.

        What is queued belongs to what came before, on a hands step the
        person's own traffic: three console lines per CC at ~98 lines a second
        on the device, 4141 lines after two hands-on steps. Carried over it
        spends the next wait's line cap and lands in that step's predicate
        window. A recording has nothing to discard: its queue is the rest of
        the run.
        """
        return 0

    def close(self, quiet=False):
        """`quiet` is honored by targets.Process."""

    # -- shared -------------------------------------------------------------
    def wait_for(self, pattern, timeout, collect=None):
        """Read until `pattern` matches. -> (match, line).

        Every line seen on the way goes into `collect` if given: that list is
        the predicate window.

        A stall is silence, not slowness: `timeout` is per line, how long the
        patch may stay silent, since a person's own sweep can put seconds of
        traffic ahead of the answer. The cap on a patch that talks forever
        counts lines rather than seconds, so a replay, which hands over its
        whole transcript at once, can test it.
        """
        seen = 0
        while True:
            line = self.readline(timeout)
            if line is None:
                raise Stalled("silence")
            if collect is not None:
                collect.append(line)
            m = pattern.search(line)
            if m:
                return m, line
            seen += 1
            if seen >= LINE_CAP:
                raise Stalled("cap")


class Replay(Source):
    """A recorded console, read as if it were live. End of file is a stall,
    not a clean finish: a transcript that stops at step 7 must not pass the
    seven it saw."""

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
    """The GO sender. Every bench binds [netreceive 9998 1], on the Mac as on
    the device, so one UDP datagram drives every target.

    A socket send with a trailing newline, never netcat: the Organelle's
    Reference page, Sending the device a UDP datagram (item 250).
    """

    def __init__(self, host, port=9998):
        self.host, self.port = host, port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send(self, word="go"):
        """`go` advances the bench, `rerun` fires the current step again. One
        [netreceive] takes both, so a repeat travels the path GO proved."""
        self.sock.sendto(("%s;\n" % word).encode(), (self.host, self.port))

    def close(self):
        self.sock.close()


def keystrokes(path):
    """--keys: the verdicts, scripted, for the self-test. It runs out rather
    than repeating, raising EOF, so a fixture cannot pass by answering one
    more question than it scripted."""
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
    """Every verdict comes through here, so the self-test drives the code a
    person drives."""
    global ask_line
    ask_line = provider


def prompt(text):
    """Write and flush the prompt before the read blocks: input() can leave a
    partial line in the buffer, and down a pipe the runner then looks hung at a
    step it has already described.
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
