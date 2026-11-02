#!/usr/bin/env python3
"""Generates every acceptance bench from test/bench/bench_steps.py.

    python3 test/bench/bench-gen.py

A bench is stepped by hand, so the PASS IF is on screen and still before
anything moves:

    press GO   ->  the described step runs
    press GO   ->  the next step is described, and nothing moves

GO is the bng at the top of the patch or the encoder click, both Mac only, or
./test/run.sh --bench <name>, the only one that works on the device. Turning the
encoder, or the runner's [r]epeat, re-runs the current step without advancing.

The encoder cannot drive a bench on the Organelle: mother forwards encbut only
after a patch bangs enableSubMenu, which Cut It never does, and asking is an
override that takes the click that leaves the patch too (items 313 and 314,
ref/device/organelle.md). u_mother-stub sends encbut unconditionally, which
hides this on the Mac.

A timed count starts at RUN, not at the next press, so it covers exactly
bench_steps.WINDOW_MS however long the step takes to judge.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# The tap labels are lib_drive.TAP_LABELS, the ones lib_assert's parser reads.
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "gate"))
import bench_steps as S  # noqa: E402
import lib_drive as D  # noqa: E402

CW, LH = 7.0, 18.0          # must match test/gate/pd-layout-check.py


class Patch(object):
    def __init__(self):
        self.B, self.C = [], []

    def _add(self, s):
        self.B.append(s)
        return len(self.B) - 1

    def obj(self, x, y, s):
        return self._add("#X obj %d %d %s;" % (x, y, s))

    def msg(self, x, y, s):
        return self._add("#X msg %d %d %s;" % (x, y, s))

    def txt(self, x, y, s, f=90):
        return self._add("#X text %d %d %s, f %d;" % (x, y, s, f))

    def bng(self, x, y, size=15):
        return self.obj(x, y, "bng %d 250 50 0 empty empty empty 17 7 0 10 "
                              "-262144 -1 -1" % size)

    def con(self, a, ao, b, bi):
        self.C.append("#X connect %d %d %d %d;" % (a, ao, b, bi))

    def write(self, path, w, h, declare=None):
        head = "#N canvas 20 20 %d %d 12;\n" % (w, h)
        if declare:
            head += "#X declare %s;\n" % declare
        open(path, "w").write(head + "\n".join(self.B + self.C) + "\n")


def esc(s):
    """Escape for a .pd record. Commas and semicolons are MESSAGE SEPARATORS
    whatever the escaping, so callers must not put them in prose -- see check()."""
    return s.replace("$", "\\$").replace(",", "\\,").replace(";", "\\;")


def width(text):
    return len(text) * CW + 10


def check(steps, name):
    """A comma or a semicolon in a printed line splits it into fragments at
    runtime, and a full stop straight after a digit vanishes: Pd reads `43.` as
    a float (item 122). Asserting both is why these files are generated."""
    lint_selfcontained(steps, name)
    lint_modal(steps, name)
    for i, step in enumerate(steps, 1):
        title, passif, actions, meta = S.norm(step)
        lint_meta(meta, actions, "%s step %d" % (name, i))
        lint_agreement(meta, passif, "%s step %d" % (name, i))
        lint_printed(meta, passif, "%s step %d" % (name, i))
        lint_resume(meta, i, "%s step %d" % (name, i))
        for label, s in (("title", title), ("pass_if", passif)):
            for ch in (",", ";"):
                assert ch not in s, (
                    "%s step %d %s contains %r -- a message box would split "
                    "there and print fragments: %s" % (name, i, label, ch, s))
            for m in re.finditer(r'(?<![\w-])(\d+\.)(?=\s|$)', s):
                raise AssertionError(
                    "%s step %d %s ends a sentence on %r -- Pd parses that as a "
                    "float and the full stop will not print at all: %s"
                    % (name, i, label, m.group(1), s))
            assert "$" not in s, (
                "%s step %d %s contains a dollar sign" % (name, i, label))
        assert title, "%s step %d has no title" % (name, i)
        assert passif.startswith("PASS IF"), (
            "%s step %d pass_if does not start with PASS IF" % (name, i))
        lint_caps(title, passif, meta, "%s step %d" % (name, i))
        for _m, bus in actions:
            assert bus, "%s step %d has an action with no bus" % (name, i)


# --------------------------------------------------------------------------
# The vacuity lint: a predicate that cannot fail is never generated
# --------------------------------------------------------------------------
KINDS = ("print", "ratio", "bus", "bus-count", "bus-not", "oled",
         "osc", "osc-rate", "file", "all")
META_KEYS = ("need", "do", "check", "wait", "targets", "reload",
             "hold")
TARGETS = ("device", "mac", "paper")
BUS_KINDS = ("bus", "bus-count", "bus-not")
# The label bench-tap.pd prints for each bus, so a predicate can be checked
# against the traffic its own step generates.
LABEL_OF = {b: l for b, l in D.TAP_LABELS.items()}


def _positive(spec):
    """Does this predicate assert that something IS there?

    A purely negative one passes on an empty stream -- an OLED that said
    nothing, a patch that failed to load, a window in the wrong place -- so it
    needs a witness that the stream was live.
    """
    k = spec.get("kind")
    if k == "all":
        return any(_positive(s) for s in spec.get("of", []))
    if k == "bus-not":
        return False
    if k == "oled":
        return bool(spec.get("has") or spec.get("has_row"))
    if k == "osc":
        # As for oled. `has` present but empty still counts: it asserts the
        # address carried traffic at all, the witness a has_not needs beside it
        # (phone 8 uses the heartbeat).
        return "has" in spec
    return True


def lint_check(spec, actions, where):
    """Every rule that can be enforced by reading, before Pd is involved."""
    kind = spec.get("kind")
    assert kind in KINDS, "%s: unknown predicate kind %r" % (where, kind)

    if kind == "all":
        assert spec.get("of"), "%s: an `all` with nothing in it asserts nothing" % where
        for s in spec["of"]:
            lint_check(s, actions, where)
        return

    if kind == "bus-count":
        # Exactly n: these steps exist because a second event must not happen,
        # and a range cannot catch a count that has drifted.
        assert "n" in spec, "%s: bus-count needs an exact n" % where
        assert "min" not in spec and "max" not in spec, (
            "%s: bus-count asserts EXACTLY n, never a range. A count that has "
            "drifted is the failure this catches, and a range cannot." % where)

    if kind in BUS_KINDS:
        # A tap on a bus the step itself writes reads the bench's own traffic
        # and proves only that Pd delivers messages.
        written = {LABEL_OF.get(b.lstrip("\\$"), b) for _m, b in actions}
        assert spec["bus"] not in written, (
            "%s: the predicate reads %s but this step WRITES to it, so it would "
            "be reading the bench's own traffic rather than the patch's response"
            % (where, spec["bus"]))


def _claims(spec):
    """The things a predicate says are true, as text a person could read."""
    k = spec.get("kind")
    if k == "all":
        out = []
        for s in spec["of"]:
            out.extend(_claims(s))
        return out
    if k == "print":
        return [spec["name"]]
    if k == "ratio":
        return [spec["a"], spec["b"]]
    if k == "bus":
        return list(spec["has"])
    if k == "bus-count":
        return [spec["match"]]
    if k == "bus-not":
        return list(spec["absent"])
    if k == "oled":
        return list(spec.get("has", [])) + list(spec.get("has_row", []))
    if k == "osc":
        return list(spec.get("has", []))
    if k in ("osc-rate", "file"):
        # A rate and a file path are not things the prose restates in words.
        return []
    return []


def lint_agreement(meta, pass_if, where):
    """The predicate and the prose must agree.

    A step has two oracles, a person reading the PASS IF and a program reading
    the bus; changed apart, the step still looks covered while one of them is
    false. Word by word rather than whole string, because the prose is English:
    the bus carries `warn m_nano` and the sentence says "reads warn and then
    m_nano".
    """
    spec = meta.get("check")
    if not spec:
        return
    prose = pass_if.lower()
    for claim in _claims(spec):
        for word in str(claim).split():
            assert word.lower() in prose, (
                "%s: the predicate asserts %r but %r appears nowhere in the "
                "PASS IF. Either the prose is now wrong, or the "
                "predicate is -- say which in the step rather than letting a "
                "person and a program answer different questions."
                % (where, claim, word))


# A number only the runner sees must say so. `print` and `ratio` read counters
# the bench prints to Pd's console, which the person never sees, so a PASS IF
# written as a claim about the instrument sends somebody hunting the OLED. The
# check is the word `print` in the prose, deliberately: anything cleverer would
# be a guess at English.
PRINTED_KINDS = ("print", "ratio")


def _kinds(spec, out=None):
    out = set() if out is None else out
    if not spec:
        return out
    if spec.get("kind") == "all":
        for sub in spec.get("of", ()):
            _kinds(sub, out)
    else:
        out.add(spec.get("kind"))
    return out


def lint_printed(meta, pass_if, where):
    spec = meta.get("check")
    if not spec or not (_kinds(spec) & set(PRINTED_KINDS)):
        return
    prose = pass_if.lower()
    assert "print" in prose, (
        "%s is judged on a counter the BENCH keeps and the runner prints -- it "
        "is on no screen the person is looking at. The PASS IF must say so; the "
        "word `printed` is what this looks for. Without it the sentence reads as "
        "a claim about the instrument and somebody goes hunting the OLED for a "
        "number that was never there." % where)


# Capitals mean literally on a screen or a label, nothing else: the literal set.
CAPS_OK = {
    "PASS", "IF",                      # the protocol marker itself
    # OSC is PdParty's own name for the settings section the buttons need; ALSA
    # is the layer wire.sh works on.
    "OLED", "LED", "BPM", "DSP", "USB", "CC", "TTL", "MIDI", "NN", "SD", "OSC",
    "ALSA",
    "SP-404", "EXT", "NO-LINK", "SETUP", "GO",
    # Molded on the nanoKONTROL's transport row, left to right.
    "REW", "PLAY", "LOOP", "STOP", "REC",
    "BEATS", "M-BEATS", "C1-BEATS", "C2-BEATS",
    "C1-BEATS-ratio-1", "C2-BEATS-ratio-1.5",
    # The debug patch's screen titles, each row drawn as one symbol, exactly so.
    "1-MIDI-IN", "2-TEST-OUT", "3-ERR-LOG", "4-NETWORK", "5-RE-WIRE", "6-HELP",
}
# Whole whitespace tokens, never a regex: word boundaries split
# `C1-BEATS-ratio-1` at the hyphen. A token with any lower case is an
# identifier, not shouting.
CAPS_STRIP = ".,:;%()[]"


def _shouted(text):
    for tok in text.split():
        tok = tok.strip(CAPS_STRIP)
        if len(tok) < 3 or tok in CAPS_OK:
            continue
        if any(c.islower() for c in tok) or not any(c.isupper() for c in tok):
            continue
        yield tok


def lint_caps(title, passif, meta, where):
    """One meaning for capitals, across every bench. `CAPS_OK` is the literal
    set -- screen text, printed counter names, molded labels, acronyms -- and
    anything else in capitals is emphasis, which this refuses.
    """
    fields = [("title", title), ("pass_if", passif)]
    fields += [("do", str(meta.get("do", "")))]
    fields += [("need", line) for line in meta.get("need", [])]
    for label, text in fields:
        for word in _shouted(text):
            assert False, (
                "%s %s shouts %r. Capitals are reserved for what is literally "
                "printed on a screen or molded on a device -- add it to "
                "CAPS_OK if it is one of those, otherwise write it as a "
                "sentence: %s" % (where, label, word, text))


# Every step sets up its own preconditions: a parameter row ages out in about
# 1.3 s and a modal in 30 s, so a step judging what the step before put up is
# judging an empty screen, and passes.
# Names only, and only where the step sends something: a hands step names what
# you are about to move, and `warn` and `fail` are what the patch emits.
NOT_A_NAME = {"modal", "grid", "bang", "compose", "perform", "stop", "start",
              "panic", "led", "status", "warn", "fail", "info"}


def _sends(actions):
    """The names a step puts on a bus itself."""
    out = set()
    for msg, _bus in actions:
        tok = msg.split()
        if not tok:
            continue
        out.add(tok[0])
        if tok[0] in ("modal", "grid") and len(tok) > 1:
            out.add(tok[1])
    return out


def lint_selfcontained(steps, name):
    """A step that leans on the one before it cannot fail. Checked per bench:
    anything any of its steps sends is a name a later step could lean on.
    """
    vocab = set()
    for step in steps:
        vocab |= _sends(S.norm(step)[2])
    vocab -= NOT_A_NAME
    for i, step in enumerate(steps, 1):
        _t, passif, actions, _m = S.norm(step)
        if not actions:
            continue                     # a person supplies it -- see above
        words = {w.strip(".,:%()") for w in passif.split()}
        leans = sorted((vocab & words) - _sends(actions))
        assert not leans, (
            "%s step %d judges %s but never sends it. Whatever the step before "
            "put on screen has aged out by the time anyone presses ENTER, so "
            "this passes against a blank screen. Send it here too."
            % (name, i, " and ".join(leans)))


def lint_modal(steps, name):
    """A modal covers the whole surface and outlives the step that raised it.

    `grid modal N` paints every pad, ring button and mode lamp, and only `grid
    modal-off` or the 30 s safety timeout takes it down. Walked in order a
    person sits the timeout out; a `--from` walk fires the earlier steps back to
    back, so the next step is judged through it.

    Re-raising counts as handling it (launchpad 8 to 10 keep it up on purpose).
    A next step that sends nothing is exempt, since it judges the picture it
    inherited (display 18 judges the modal clearing itself). Nothing cleverer:
    reading the prose for intent would be a guess at English.
    """
    for i, step in enumerate(steps, 1):
        sends = _sends(S.norm(step)[2])
        if not any(s.startswith("modal") and s != "modal-off" for s in sends):
            continue
        if "modal-off" in sends or i == len(steps):
            continue
        nxt_actions = S.norm(steps[i])[2]
        if not nxt_actions:
            continue                     # it is judging what it inherited
        nxt = _sends(nxt_actions)
        assert any(s.startswith("modal") for s in nxt), (
            "%s step %d raises a modal and never clears it, and step %d does "
            "not clear or re-raise one either. The whole surface stays that "
            "color for thirty seconds -- run in order a person waits the "
            "timeout out, but a --from walk fires these back to back and step "
            "%d is judged through it. Send `grid modal-off` from step %d."
            % (name, i, i + 1, i + 1, i + 1))


RESUME_RE = re.compile(r"--from\s+(\d+)")


def lint_resume(meta, n, where):
    """A step number written into step text goes wrong silently: a `--from N`
    in a `do` or `need` is the step's own index, and inserting a step above it
    makes it wrong without changing a word. It is the one number a step can know
    about itself, so it is the one checked.
    """
    for field in ("do",):
        for m in RESUME_RE.finditer(str(meta.get(field, ""))):
            assert int(m.group(1)) == n, (
                "%s: its `%s` says --from %s but it is step %d. That number is "
                "the step's own index, so inserting a step above this one made "
                "it wrong without changing a word of the text"
                % (where, field, m.group(1), n))
    for line in meta.get("need", []):
        for m in RESUME_RE.finditer(line):
            assert int(m.group(1)) == n, (
                "%s: a `need` line says --from %s but it is step %d. That number "
                "is the step's own index, so inserting a step above this one "
                "made it wrong without changing a word of the text"
                % (where, m.group(1), n))


def lint_meta(meta, actions, where):
    if not meta:
        return
    for k in meta:
        assert k in META_KEYS, "%s: unknown meta key %r -- known keys are %s" % (
            where, k, ", ".join(META_KEYS))
    for t in meta.get("targets", ()):
        assert t in TARGETS, "%s: unknown target %r" % (where, t)
    spec = meta.get("check")
    if not spec:
        return
    lint_check(spec, actions, where)
    # `oled` is not a bus kind, so the self-write rule leaves it alone: display
    # step 3 writes disp and asserts what g_oled drew, downstream of the patch.
    assert _positive(spec), (
        "%s: this predicate only says what must NOT be there, so an empty "
        "window satisfies it -- a patch that failed to load would pass. Put it "
        "in an `all` beside something that asserts the stream was live."
        % where)


# --------------------------------------------------------------------------
# the counter block -- one per clock source a bench wants to count
# --------------------------------------------------------------------------
def counters(p, specs, x0, y0):
    """specs is [(print_name, source)] where source is 'r clock' or 'c_clock A B'.

    Each block counts beats freely; a bang on $0-zero resets it and arms a
    bench_steps.WINDOW_MS timer that latches and prints the count, and $0-read
    reprints the latch. The window is bench_steps', which test/runner/ and the
    header prose read too.
    """
    if not specs:
        return y0
    secs = S.WINDOW_MS // 1000
    p.txt(x0, y0 - 200,
          ("BEAT COUNTERS. \\$0-zero resets one and starts a %d SECOND window \\; the "
           "count is latched and printed when that window closes \\, and \\$0-read "
           "reprints the latched value. THE WINDOW IS MACHINE-TIMED ON PURPOSE -- "
           "under manual stepping the gap between two steps is however long you take "
           "to judge one \\, so a count taken between steps would mean nothing. On the "
           "Mac with DSP OFF every count reads 0 \\, which looks exactly like a dead "
           "clock rather than a setting.") % secs, 120)
    for n, (name, source) in enumerate(specs):
        x = x0 + n * 1300
        src = p.obj(x, y0, source)
        tb = p.obj(x, y0 + 70, "t b")
        # c_clock outlet 1 is the beat bang. Outlet 0 is a SIGNAL, and Pd answers a
        # signal-to-control connection with "signal outlet connect to nonsignal
        # inlet (ignored)" -- measured, and the count would sit at 0 forever.
        p.con(src, 1 if source.startswith("c_clock") else 0, tb, 0)

        count = p.obj(x, y0 + 140, "f")
        inc = p.obj(x + 160, y0 + 200, "+ 1")
        fan = p.obj(x + 160, y0 + 260, "t f f")
        mirror = p.obj(x + 400, y0 + 320, "f")
        p.con(tb, 0, count, 0)
        p.con(count, 0, inc, 0)
        p.con(inc, 0, fan, 0)
        p.con(fan, 1, count, 1)
        p.con(fan, 0, mirror, 1)

        rz = p.obj(x + 700, y0, "r \\$0-zero")
        rzt = p.obj(x + 700, y0 + 70, "t b b")
        zero = p.msg(x + 880, y0 + 140, "0")
        dl = p.obj(x + 700, y0 + 200, "del %d" % S.WINDOW_MS)
        p.con(rz, 0, rzt, 0)
        p.con(rzt, 1, zero, 0)
        p.con(zero, 0, count, 1)
        p.con(rzt, 0, dl, 0)

        close = p.obj(x + 400, y0 + 380, "t f f")
        latch = p.obj(x + 700, y0 + 440, "f -1")
        pr = p.obj(x, y0 + 520, "print %s" % name)
        p.con(dl, 0, mirror, 0)
        p.con(mirror, 0, close, 0)
        p.con(close, 1, latch, 1)
        p.con(close, 0, pr, 0)

        rr = p.obj(x + 950, y0 + 380, "r \\$0-read")
        p.con(rr, 0, latch, 0)
        p.con(latch, 0, pr, 0)
        p.txt(x, y0 + 580,
              "latch starts at -1 \\, so a count read before its %d seconds are up "
              "says so rather than lying." % secs, 46)
    return y0 + 660


# --------------------------------------------------------------------------
def build(name, cfg):
    steps = cfg["steps"]
    check(steps, name)
    n = len(steps)
    p = Patch()

    p.txt(20, 20,
          "%s-bench -- %s STEPPED BY HAND: press GO to run the step that has "
          "just been described \\, press GO again to describe the next one. Nothing "
          "moves until you ask it to \\, so the PASS IF is on screen and STILL while "
          "you read it. The prompt line always says what the next press will do."
          % (name, cfg["blurb"]), 120)
    p.txt(20, 150,
          "GO ON THE MAC: the bng below \\, or the dev panel's ENCODER CLICK -- u_mother-stub "
          "sends encbut unconditionally and nothing in Cut It consumes it. TURNING the encoder "
          "repeats the current step without advancing \\, which is what to do when you looked "
          "away.", 120)
    p.txt(2400, 200,
          "⚠️ GO ON THE DEVICE IS NOT THE ENCODER -- IT IS netcat \\, AND THE DIFFERENCE IS NOT "
          "OPTIONAL. mother only forwards encbut once a patch has banged enableSubMenu \\, "
          "and NOTHING IN Cut It EVER ASKS -- m_organelle leaves the encoder out on purpose. So "
          "the click that drives this bench on the Mac is silently dead on the Organelle. Send "
          "instead with ./test/run.sh --bench <name> from the Mac. ⚠️ NOT netcat: the line this file "
          "used to print does nothing on macOS -- BSD nc exits before the datagram is flushed at "
          "-w0 \\, and -w1 was measured to fail too \\, while the port IS bound and the bench is "
          "fine. It looks exactly like a dead bench. The device cannot send to itself either: "
          "busybox here has no nc at all. Asking mother to enable the encoder is NOT the fix "
          "either: it is an OVERRIDE that takes the turn AND the click \\, so the bench would eat "
          "the press that leaves the patch. Items 313 and 314 \\, ref/device/organelle.md.", 120)
    p.txt(20, 280,
          "Load it as a THIRD patch after mother.pd and main.pd. It touches nothing "
          "in the deployed patch -- it only pushes onto the same buses a controller "
          "would. A PASS IF is printed for EVERY step including the ones whose "
          "correct result is that nothing happens \\, which are otherwise impossible "
          "to mark off.", 120)
    p.txt(2400, 20,
          "ON THE MAC EVERY ERROR STEP ALSO PRINTS /sdcard/cut-it-err.cur: write "
          "failed \\, AND THAT IS NOT A FAILED STEP. u_err keeps its durable log on "
          "the Organelle's SD card \\, which no Mac has -- so the write is attempted "
          "and refused every time. It is in fact the only proof off-device that the "
          "logging path ran at all. On the device that line must NOT appear \\, and "
          "if it does the card is unwritable and the log is being lost silently.",
          120)

    # ---------------------------------------------------------------- say
    say_r = p.obj(6000, 40, "r \\$0-say")
    say_p = p.obj(6000, 100, "print")
    p.con(say_r, 0, say_p, 0)

    # ---------------------------------------------------------------- GO
    Y = 420
    p.txt(20, Y - 60, "GO -- click here \\, or the dev panel's encoder button. "
                      "MAC ONLY -- on the device use netcat \\, top right.", 60)
    go_b = p.bng(20, Y, 40)
    go_s = p.obj(20, Y + 80, "s \\$0-go")
    p.con(go_b, 0, go_s, 0)

    enc_r = p.obj(300, Y, "r encbut")
    enc_sel = p.obj(300, Y + 60, "select 1")
    enc_t = p.obj(300, Y + 120, "t b")
    enc_s = p.obj(300, Y + 180, "s \\$0-go")
    p.con(enc_r, 0, enc_sel, 0)
    p.con(enc_sel, 0, enc_t, 0)
    p.con(enc_t, 0, enc_s, 0)
    p.txt(560, Y + 60,
          "encbut sends 1 THEN 0 \\, so select 1 is what stops one press counting "
          "twice.", 46)

    net_r = p.obj(300, Y + 260, "netreceive 9998 1")
    net_rt = p.obj(300, Y + 320, "route go rerun where show")
    net_t = p.obj(300, Y + 380, "t b")
    net_s = p.obj(300, Y + 440, "s \\$0-go")
    p.con(net_r, 0, net_rt, 0)
    p.con(net_rt, 0, net_t, 0)
    p.con(net_t, 0, net_s, 0)

    # rerun fires the current step again and advances nothing, because g_oled
    # ages a parameter row out after about 1.3 s. It bangs the store the first
    # fire did, so a repeat is the step itself. [t b] because a route reject
    # carries data (C-8) and run_store needs a bang.
    rr_t = p.obj(620, Y + 380, "t b")
    rr_s = p.obj(620, Y + 440, "s \\$0-rerun")
    p.con(net_rt, 1, rr_t, 0)
    p.con(rr_t, 0, rr_s, 0)
    p.txt(860, Y + 380,
          "rerun fires the CURRENT step again without advancing \\, so a visual "
          "step can be looked at more than once. [r]epeat in test/run.sh sends "
          "it.", 46)

    # where and show move nothing. GO is one UDP datagram, so a lost GO looks
    # exactly like a dead patch, and a second GO sent on that guess advances a
    # bench that heard the first. `where` prints step and phase, which says
    # whether the last GO landed; `show` re-describes the current step.
    wh_t = p.obj(1500, Y + 380, "t b b")
    p.con(net_rt, 2, wh_t, 0)
    wh_phase = p.obj(1680, Y + 440, "f")
    wh_step = p.obj(1500, Y + 440, "f")
    p.con(wh_t, 1, wh_phase, 0)
    p.con(wh_t, 0, wh_step, 0)
    wh_pk = p.obj(1500, Y + 500, "pack f f")
    p.con(wh_step, 0, wh_pk, 0)
    p.con(wh_phase, 0, wh_pk, 1)
    wh_pr = p.obj(1500, Y + 560, "print %s" % S.SAY_WHERE)
    p.con(wh_pk, 0, wh_pr, 0)
    # Fed by name from the sends the state machine writes, so it cannot report a
    # position the bench is not in.
    wh_sr = p.obj(1500, Y + 320, "r \\$0-set-step")
    wh_pr2 = p.obj(1680, Y + 320, "r \\$0-set-phase")
    p.con(wh_sr, 0, wh_step, 1)
    p.con(wh_pr2, 0, wh_phase, 1)

    sh_t = p.obj(2000, Y + 380, "t b")
    sh_s = p.obj(2000, Y + 440, "s \\$0-repeat")
    p.con(net_rt, 3, sh_t, 0)
    p.con(sh_t, 0, sh_s, 0)
    p.txt(2200, Y + 380,
          "show goes through $0-repeat \\, which is the encoder's path too -- one "
          "way to re-describe a step \\, not two.", 46)

    rep_r = p.obj(1400, Y, "r enc")
    rep_t = p.obj(1400, Y + 60, "t b")
    rep_s = p.obj(1400, Y + 120, "s \\$0-repeat")
    p.con(rep_r, 0, rep_t, 0)
    p.con(rep_t, 0, rep_s, 0)
    p.txt(1660, Y + 60,
          "enc is 1 for up and 0 for down -- not plus or minus one -- so either "
          "direction repeats.", 46)

    # ---------------------------------------------------------------- state
    Y += 560
    p.txt(20, Y - 60,
          "THE STATE MACHINE. phase 0 means the step has been described and not yet "
          "run \\; phase 1 means it has run. SETTING THE STEP NUMBER IS WHAT DESCRIBES "
          "IT \\, so advancing is just an increment -- there is no second path to keep "
          "in step.", 120)

    go_r = p.obj(20, Y, "r \\$0-go")
    phase_f = p.obj(20, Y + 60, "f")
    phase_sel = p.obj(20, Y + 120, "select 0 1")
    p.con(go_r, 0, phase_f, 0)
    p.con(phase_f, 0, phase_sel, 0)
    # the phase is set BY NAME rather than by a cord: the advance branch lives far
    # to the right and a cord back would be drawn straight through the run branch
    phase_set = p.obj(300, Y + 60, "r \\$0-set-phase")
    p.con(phase_set, 0, phase_f, 1)

    run_t = p.obj(20, Y + 190, "t b b")
    p.con(phase_sel, 0, run_t, 0)
    ph1 = p.msg(300, Y + 250, "1")
    ph1s = p.obj(300, Y + 310, "s \\$0-set-phase")
    p.con(run_t, 1, ph1, 0)
    p.con(ph1, 0, ph1s, 0)
    run_store = p.obj(20, Y + 310, "f")
    p.con(run_t, 0, run_store, 0)
    run_go = p.obj(20, Y + 370, "s \\$0-do-run")
    p.con(run_store, 0, run_go, 0)
    # A repeat lands on the same store and touches neither phase nor step.
    rerun_r = p.obj(20, Y + 250, "r \\$0-rerun")
    p.con(rerun_r, 0, run_store, 0)

    adv_t = p.obj(900, Y + 190, "t b b")
    p.con(phase_sel, 1, adv_t, 0)
    ph0 = p.msg(1180, Y + 250, "0")
    ph0s = p.obj(1180, Y + 310, "s \\$0-set-phase")
    p.con(adv_t, 1, ph0, 0)
    p.con(ph0, 0, ph0s, 0)
    inc_store = p.obj(900, Y + 370, "f")
    inc_add = p.obj(900, Y + 430, "+ 1")
    set_s = p.obj(900, Y + 490, "s \\$0-set-step")
    p.con(adv_t, 0, inc_store, 0)
    p.con(inc_store, 0, inc_add, 0)
    p.con(inc_add, 0, set_s, 0)

    # setting the step number stores it in both places and describes it
    set_r = p.obj(1700, Y, "r \\$0-set-step")
    set_t = p.obj(1700, Y + 60, "t f f f")
    p.con(set_r, 0, set_t, 0)
    # Written by name, as the phase is: a cord back 1700px would cross the
    # branch between. One trigger writes both, so they cannot drift.
    set_inc = p.obj(1700, Y + 130, "s \\$0-set-inc")
    set_run = p.obj(1980, Y + 130, "s \\$0-set-run")
    p.con(set_t, 2, set_inc, 0)
    p.con(set_t, 1, set_run, 0)
    r_inc = p.obj(1180, Y + 370, "r \\$0-set-inc")
    r_run = p.obj(300, Y + 430, "r \\$0-set-run")
    p.con(r_inc, 0, inc_store, 1)
    p.con(r_run, 0, run_store, 1)
    show_s = p.obj(2260, Y + 130, "s \\$0-do-show")
    p.con(set_t, 0, show_s, 0)

    # $0-do-show carries the step number, not a bang: the describe chain is one
    # [select N] per step and a bang matches none (runner-assert checks it).
    # The store reads $0-set-run, which the same trigger writes first, so a
    # repeat never describes a step the bench has left.
    rep_rr = p.obj(2600, Y, "r \\$0-repeat")
    rep_f = p.obj(2600, Y + 60, "f")
    rep_fr = p.obj(2780, Y, "r \\$0-set-run")
    rep_ss = p.obj(2600, Y + 120, "s \\$0-do-show")
    p.con(rep_rr, 0, rep_f, 0)
    p.con(rep_fr, 0, rep_f, 1)
    p.con(rep_f, 0, rep_ss, 0)

    lb = p.obj(3100, Y, "loadbang")
    lbd = p.obj(3100, Y + 60, "del 500")
    lb1 = p.msg(3100, Y + 120, "1")
    lbs = p.obj(3100, Y + 180, "s \\$0-set-step")
    p.con(lb, 0, lbd, 0)
    p.con(lbd, 0, lb1, 0)
    p.con(lb1, 0, lbs, 0)

    # ---------------------------------------------------------------- counters
    Y += 620
    Y = counters(p, cfg["counters"], 20, Y + 260)

    # ---------------------------------------------------------------- describe
    Y += 120
    p.txt(20, Y - 60,
          "DESCRIBING A STEP. One select per step rather than one wide fan \\, so every "
          "cord stays short and local -- the same reason u_map chains its routes.", 120)
    Y += 40
    show_r = p.obj(20, Y, "r \\$0-do-show")
    prev = show_r
    prev_out = 0
    TX = 700
    for i, step in enumerate(steps, 1):
        title, passif, _a, _meta = S.norm(step)
        y = Y + 60 + (i - 1) * 260
        sel = p.obj(20, y, "select %d" % i)
        p.con(prev, prev_out, sel, 0)
        prev, prev_out = sel, 1

        t3 = p.obj(240, y, "t b b b")
        p.con(sel, 0, t3, 0)

        # No title says HANDS any more, so this never adds the note; the runner's
        # own [HANDS] tag comes from a step's `do` (test/runner/steps.py).
        hands = "HANDS" in title.upper()
        measure = any(b.endswith(S.MEASURE_SUFFIX) for _m, b in _a)
        prompt = S.SAY_PROMPT % (i, len(steps))
        if hands:
            prompt += " -- THIS ONE NEEDS YOUR HANDS ON THE HARDWARE"
        if measure:
            prompt += " -- then WAIT for the printed count before pressing GO again"

        m1 = p.msg(TX, y, esc(S.SAY_STEP % (i, len(steps), title)))
        m2 = p.msg(TX, y + 50, esc(passif))
        m3 = p.msg(TX, y + 100, esc(prompt))
        s1 = p.obj(240, y + 170, "s \\$0-say")
        p.con(t3, 2, m1, 0)
        p.con(t3, 1, m2, 0)
        p.con(t3, 0, m3, 0)
        p.con(m1, 0, s1, 0)
        p.con(m2, 0, s1, 0)
        p.con(m3, 0, s1, 0)
        showmax = max(width(passif), width(title) + 100)

    done_t = p.obj(20, Y + 60 + len(steps) * 260, "t b")
    p.con(prev, prev_out, done_t, 0)
    done_m = p.msg(240, Y + 60 + len(steps) * 260, esc(S.SAY_COMPLETE))
    done_s = p.obj(240, Y + 120 + len(steps) * 260, "s \\$0-say")
    p.con(done_t, 0, done_m, 0)
    p.con(done_m, 0, done_s, 0)

    # ---------------------------------------------------------------- run
    Y = Y + 260 + len(steps) * 260
    p.txt(20, Y - 60,
          "RUNNING A STEP. The actions fire in the order they are listed -- rightmost "
          "trigger outlet first -- and the line saying the step has fired goes out "
          "LAST \\, off outlet 0 \\, so it cannot arrive before the thing it describes.",
          120)
    Y += 40
    run_r = p.obj(20, Y, "r \\$0-do-run")
    prev, prev_out = run_r, 0
    runmax = 0
    yy = Y + 60
    for i, step in enumerate(steps, 1):
        title, _p, actions, _meta = S.norm(step)
        na = len(actions)
        sel = p.obj(20, yy, "select %d" % i)
        p.con(prev, prev_out, sel, 0)
        prev, prev_out = sel, 1

        tr = p.obj(240, yy, "t " + " ".join(["b"] * (na + 1)))
        p.con(sel, 0, tr, 0)

        # actions go in ONE column, well right of the trigger and stepping down.
        # A cord from the trigger only reaches x=480 at its endpoint, so it can
        # never be drawn through the action above it.
        for j, (m, bus) in enumerate(actions):
            ay = yy + j * 110
            am = p.msg(480, ay, esc(m))
            b = bus if bus.startswith("\\$") else bus.replace("$", "\\$")
            asnd = p.obj(480, ay + 45, "s %s" % b)
            p.con(tr, na - j, am, 0)
            p.con(am, 0, asnd, 0)
            runmax = max(runmax, 480 + width(m))

        tail = (S.SAY_FIRED % (i, i + 1)) if i < len(steps) else (
                S.SAY_FIRED_LAST % i)
        fm = p.msg(480, yy + na * 110 + 70, esc(tail))
        fs = p.obj(240, yy + na * 110 + 130, "s \\$0-say")
        p.con(tr, 0, fm, 0)
        p.con(fm, 0, fs, 0)
        runmax = max(runmax, 480 + width(tail))
        yy += na * 110 + 250

    W = int(max(7000, runmax + 200,
                max(width(esc(s[1])) for s in steps) + TX + 200))
    H = int(yy + 300)
    p.write("test/bench/%s-bench.pd" % name, W, H, cfg.get("declare"))
    return n, len(p.B), len(p.C)


# The key is the output filename and the only list of benches; bench-verify.py
# derives its own from it (the gate skill, Benches).
BENCHES = {
    "display": dict(steps=S.STEPS_DISPLAY, counters=[],
                    blurb="the display acceptance run: the display arbiter and "
                    "the error bus."),
    "nanokontrol": dict(steps=S.STEPS_NANOKONTROL, counters=[],
                        blurb="the nanoKONTROL acceptance run: every fader \\, knob "
                        "and transport key \\, and the multi-parameter display."),
    "tempo": dict(steps=S.STEPS_TEMPO, counters=[],
                  blurb="the tempo acceptance run: the transport \\, the map \\, "
                  "the 404 link and the aux LED."),
    "launchpad": dict(steps=S.STEPS_LAUNCHPAD,
                      blurb="the Launchpad acceptance run: the grid \\, the grid "
                      "arbiter \\, the mode bus and the first c_clock instance.",
                      counters=[("BEATS", "r clock")]),
    "phone": dict(steps=S.STEPS_PHONE, counters=[],
                  blurb="the phone acceptance run: the status link. EVERY PASS IF "
                  "DESCRIBES THE PHONE \\, not the Organelle -- so PdParty has to be "
                  "open on the CutItRemote scene before step 1."),
    "state": dict(steps=S.STEPS_STATE, counters=[],
                  blurb="the data store acceptance run. MOST OF THE DATA STORE IS "
                  "DELIBERATELY INVISIBLE -- state is FILES \\, and "
                  "test/gate/state-assert.sh proves the logic headlessly in twelve "
                  "seconds. What is left here is only what hardware can show: the "
                  "front-panel Save \\, a REAL power cycle \\, and the mode lamp. Six "
                  "steps rather than a padded twenty \\, because a bench proves the "
                  "cases it contains and nothing else."),
    # Paper -- see STEPS_RECOVER.
    "recover": dict(steps=S.STEPS_RECOVER, counters=[],
                    blurb="panic's second tier. MOST OF IT IS PROVEN HEADLESSLY "
                    "-- test/gate/recover-assert.sh lints the two-step OSC by "
                    "reading it \\, and drives both tiers against a stubbed "
                    "shell. WHAT IT CANNOT DO is load a patch \\, so the reload "
                    "itself is here and only here \\, along with the one case "
                    "that matters most: a reload that CANNOT land."),
    # Paper, and the only bench with no predicate -- see STEPS_DEBUG.
    "debug": dict(steps=S.STEPS_DEBUG, counters=[],
                  blurb="the debug patch acceptance run. IT STOPS THE INSTRUMENT "
                  "-- selecting any patch restarts Pd \\, which is exactly why this "
                  "tool exists and exactly why it is not for mid-set. MOST OF IT IS "
                  "PROVEN HEADLESSLY: test/gate/debug-assert.sh asserts all five "
                  "screen rows \\, the channel-block decode and both probes in about "
                  "thirteen seconds. What is left here is what only hardware can "
                  "show -- that the patch WIRED ITSELF \\, which is step 3 and the "
                  "one everything else rests on."),
    "midi": dict(steps=S.STEPS_MIDI, counters=[],
                 blurb="the MIDI acceptance run: the mode-dependent map \\, both "
                 "output devices and the SP-404 in both directions. MOST OF THIS IS "
                 "PROVEN HEADLESSLY -- test/gate/sp404-assert.sh asserts all sixteen "
                 "pads \\, the rate limiter and the allowlist guard in about eight "
                 "seconds \\, and test/gate/map-assert.sh asserts the lookup. What is "
                 "left here is only what HARDWARE can show: a real pad under a real "
                 "finger \\, and a Volca you can hear."),
}


# --------------------------------------------------------------------------
def build_tap():
    """bench-tap.pd -- a fourth patch the runner loads beside a bench.

    It listens and sends nothing, so loading it cannot change what the bench
    under it does: C-5's ownership governs writing, and Pd delivers a message
    to every receiver of a name. Do not route its output anywhere.

    Its labels are lib_drive.TAP_LABELS, which lib_assert.parse() matches, so
    the runner reuses the gates' parser. `clock` is not tapped: a beat twice a
    second forever would bury every window.
    """
    p = Patch()
    p.txt(20, 20,
          "bench-tap -- loaded BESIDE a bench so a step can assert on what "
          "actually reached a bus. IT LISTENS AND SENDS NOTHING \\, which is "
          "what makes it safe: g_oled owns oscOut and g_grid owns the grid \\, "
          "but that governs WRITING -- Pd delivers a message to EVERY receiver "
          "of a name \\, so adding one here cannot change what any other "
          "subscriber sees. ⛔ DO NOT ROUTE ITS OUTPUT ANYWHERE. clock is "
          "deliberately absent: two beats a second forever \\, which no "
          "assertion wants and which would bury every window it appeared in.",
          120)
    p.txt(20, 150,
          "⛔ THIS FILE IS AN OUTPUT. Edit build_tap in test/bench/bench-gen.py "
          "and regenerate \\; never this. The print labels are "
          "lib_drive.TAP_LABELS \\, which is the same map "
          "test/gate/lib_assert.py's parser matches -- so the runner reuses the "
          "gates' parser rather than growing a second one.", 120)
    taps = sorted(D.TAP_LABELS.items())
    for k, (bus, label) in enumerate(taps):
        r = p.obj(20 + k * 220, 320, "r %s" % bus)
        pr = p.obj(20 + k * 220, 380, "print %s" % label)
        p.con(r, 0, pr, 0)
    p.write("test/bench/bench-tap.pd", 220 * len(taps) + 200, 520)
    return len(taps), len(p.B), len(p.C)


if __name__ == "__main__":
    for name in sorted(BENCHES):
        n, b, c = build(name, BENCHES[name])
        print("%s-bench.pd  %2d steps  %3d boxes  %3d connects" % (name, n, b, c))
    n, b, c = build_tap()
    print("bench-tap.pd    %2d taps   %3d boxes  %3d connects" % (n, b, c))
