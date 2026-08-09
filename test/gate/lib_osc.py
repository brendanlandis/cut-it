#!/usr/bin/env python3
"""OSC decoding, shared by the phone gate and the test runner. Imported, never run.

⚠️ THE MODULE NAME HAS AN UNDERSCORE and its neighbours have hyphens. A hyphen is
not a legal Python identifier, so a module that is IMPORTED cannot have one,
while a script that is only ever RUN can.

WHY IT EXISTS. This was inside phone-assert.py, and test/runner/ needs exactly
the same decode to judge a phone step from the datagrams u_net actually emits.
Copying it would make two decoders, which is how a fix reaches one and not the
other -- the same failure the whole test refactor existed to remove, and the
reason lib_assert.py and lib_grid.py exist at all.

⛔ IT DECODES ONLY. No sockets, no lifecycle, no opinions about what an address
means -- both callers have different and legitimate views on that.
"""
import struct


def _pad(n):
    return (n + 3) & ~3


def _string(buf, i):
    end = buf.index(b"\0", i)
    return buf[i:end].decode("ascii", "replace"), i + _pad(end - i + 1)


def decode(buf):
    """Return (address, [args]) or None if this is not an OSC message."""
    try:
        addr, i = _string(buf, 0)
        if not addr.startswith("/"):
            return None
        tags, i = _string(buf, i)
        if not tags.startswith(","):
            return None
        args = []
        for t in tags[1:]:
            if t == "f":
                args.append(struct.unpack_from(">f", buf, i)[0])
                i += 4
            elif t == "i":
                args.append(struct.unpack_from(">i", buf, i)[0])
                i += 4
            elif t == "s":
                s, i = _string(buf, i)
                args.append(s)
            elif t == "b":
                n = struct.unpack_from(">i", buf, i)[0]
                args.append(buf[i + 4:i + 4 + n])
                i += 4 + _pad(n)
            else:
                return None
        return addr, args
    except Exception:
        return None


def as_text(addr, args):
    """One decoded datagram as a line a predicate can read, in the same shape
    as bench-tap.pd's bus lines -- so the runner has one window format rather
    than a second one that only OSC uses."""
    return "OSC: %s %s" % (addr, " ".join(_atom(a) for a in args))


def _atom(a):
    if isinstance(a, float) and a == int(a):
        return "%g" % a
    return str(a)
