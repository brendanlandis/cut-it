"""Reading a .pd file the way Pd does: by record, not by line.

A record ends at an unescaped `;`. Pd 0.49 wraps a long record across lines when
it saves, at about 65 columns (0.57 keeps each on one line), so a lint that reads
one line at a time cuts a long box short or misses it outright the first time a
patch is saved from 0.49 rather than written by a script. u_map's destination
`route` is about 120 characters.
"""


def records(src):
    """The records in .pd source text, in file order.

    Each keeps its closing `;`, the newlines Pd wrapped it with become the
    spaces they replaced, and the space Pd leaves before a wrapped `;` goes, so
    a pattern written for a one-line record still matches. Escaped pairs
    (`\\;`, `\\,`, `\\$`) stay as they are: a `\\;` inside a `#A set` record is
    data, not the end of it.
    """
    out, buf, i = [], [], 0
    while i < len(src):
        ch = src[i]
        if ch == "\\" and i + 1 < len(src):
            buf.append(src[i:i + 2])
            i += 2
            continue
        buf.append(ch)
        i += 1
        if ch == ";":
            rec = _one_line("".join(buf)[:-1]) + ";"
            if rec != ";":
                out.append(rec)
            buf = []
    tail = _one_line("".join(buf))
    if tail:
        out.append(tail)
    return out


def _one_line(text):
    """A wrapped record's text on one line. Pd wraps at a space, and when it
    wraps just before the `;` it leaves that space in front of it, so the text
    is stripped before the `;` goes back on."""
    return text.replace("\r", " ").replace("\n", " ").strip()


def read(path):
    """records() of the file at path."""
    with open(path, encoding="utf-8") as fh:
        return records(fh.read())
