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
import socket
import sys
import time


class Stalled(Exception):
    """No line arrived in time. ⚠️ Two shapes, and they must be told apart --
    see run.py, where "the bench never loaded" and "stalled mid-run" get
    different advice because they have different causes."""


class Source(object):
    """The interface. `readline` returns a line without its newline, or None
    when nothing arrived before the deadline."""

    def readline(self, timeout):
        raise NotImplementedError

    def go(self):
        raise NotImplementedError

    def close(self):
        pass

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

    def __init__(self, path):
        with open(path, encoding="utf-8", errors="replace") as fh:
            self.lines = fh.read().splitlines()
        self.i = 0
        self.gos = 0

    def readline(self, timeout):
        if self.i >= len(self.lines):
            return None
        self.i += 1
        return self.lines[self.i - 1]

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

    def send(self):
        self.sock.sendto(b"go;\n", (self.host, self.port))

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
    try:
        return ask_line(text)
    except EOFError:
        print()
        raise


def say(*a):
    print(*a)
    sys.stdout.flush()
