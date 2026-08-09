#!/usr/bin/env python3
"""Generates all four acceptance benches from test/bench/bench_steps.py.

    python3 test/bench/bench-gen.py

Replaces launchpad-bench-gen.py, which generated one bench. Four near-identical
files of fifteen-odd near-identical steps is exactly where hand-authored box
indices drift, and it did -- see C-10, and the git history.

THE INTERACTION, and why it changed. Every bench up to now drove itself on a
ten-second timer, so the console text and the physical device moved at the same
moment -- you cannot read one while watching the other. These are stepped BY HAND:

    press GO   ->  the described step runs
    press GO   ->  the next step is described, and nothing moves
    press GO   ->  that step runs

so the PASS IF is always on screen and still, before anything happens. The prompt
line states what the next press will do, so one control is enough -- which matters
on the Organelle, where the encoder click is the only free control there is.

GO is:
  * the bng at the top of the patch                     (Mac)
  * the encoder click, via [r encbut]                   (MAC ONLY -- see below)
  * ./tools/go.sh                                       (THE ONLY ONE THAT WORKS
                                                         ON THE DEVICE)
Turning the encoder REPEATS the current step without advancing (Mac only).

!! THE ENCODER DOES NOT DRIVE THIS BENCH ON THE ORGANELLE, and the plan that
chose a single alternating control assumed it did. mother forwards encbut only
after a patch sends /enableEncoder, and nothing in Cut It ever does -- m_organelle
leaves the encoder out deliberately. On the Mac u_mother-stub sends encbut
unconditionally, which is what hid this. Use netcat on the device. Making the
bench ask mother to enable the encoder is NOT the fix: that means writing to
oscOut, and C-5 gives g_oled sole ownership of it.

TIMED ASSERTIONS still mean something because the window starts at RUN rather than
at the press that follows it: a step that zeroes a beat counter arms a 10 s timer
which latches and prints the count. However long you take to judge the step, the
number covers exactly ten seconds.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# ⛔ THE TAP LABELS ARE THE GATES', NOT A SECOND SET. lib_drive.TAP_LABELS
# is what lib_assert's parser matches, so bench-tap.pd emits exactly the
# labels every headless gate already reads.
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
    runtime. This assertion is the whole reason these files are generated.

    The digit-then-full-stop check below is a WARNING and not an assertion, on
    purpose. `43.` is a valid Pd float literal, so the atom is parsed as the
    number and the stop disappears from the printed line -- but it is cosmetic
    rather than structural, and it is already present in the tempo and Launchpad benches,
    which are verified on the Organelle and must not be reworded. Asserting
    would refuse to generate four working benches over a missing full stop.
    item 122."""
    for i, step in enumerate(steps, 1):
        title, passif, actions, meta = S.norm(step)
        lint_meta(meta, actions, "%s step %d" % (name, i))
        lint_agreement(meta, passif, "%s step %d" % (name, i))
        for label, s in (("title", title), ("pass_if", passif)):
            for ch in (",", ";"):
                assert ch not in s, (
                    "%s step %d %s contains %r -- a message box would split "
                    "there and print fragments: %s" % (name, i, label, ch, s))
            for m in re.finditer(r'(?<![\w-])(\d+\.)(?=\s|$)', s):
                print("  note: %s step %d %s has %r -- Pd reads that as a "
                      "float and the full stop will not print"
                      % (name, i, label, m.group(1)))
            assert "$" not in s, (
                "%s step %d %s contains a dollar sign" % (name, i, label))
        assert title, "%s step %d has no title" % (name, i)
        assert passif.startswith("PASS IF"), (
            "%s step %d pass_if does not start with PASS IF" % (name, i))
        for _m, bus in actions:
            assert bus, "%s step %d has an action with no bus" % (name, i)


# --------------------------------------------------------------------------
# ⛔ THE VACUITY LINT -- a predicate that cannot fail must never be generated
# --------------------------------------------------------------------------
KINDS = ("print", "ratio", "bus", "bus-count", "bus-not", "oled", "all")
META_KEYS = ("need", "do", "watch", "check", "wait", "targets")
TARGETS = ("device", "mac", "paper")
BUS_KINDS = ("bus", "bus-count", "bus-not")
# The label bench-tap.pd prints for each bus, so a predicate can be checked
# against the traffic its own step generates.
LABEL_OF = {b: l for b, l in D.TAP_LABELS.items()}


def _positive(spec):
    """Does this predicate assert that something IS there?

    ⛔ A PURELY NEGATIVE PREDICATE PASSES ON AN EMPTY STREAM. "the OLED must not
    say %" is satisfied by an OLED that said nothing, by a patch that failed to
    load, and by a window the runner opened in the wrong place. It needs an
    independent witness that the stream was live at all.
    """
    k = spec.get("kind")
    if k == "all":
        return any(_positive(s) for s in spec.get("of", []))
    if k == "bus-not":
        return False
    if k == "oled":
        return bool(spec.get("has") or spec.get("has_row"))
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
        # ⛔ EXACTLY n. "at least" cannot catch a count that has drifted, which
        # is the failure this project keeps finding -- and the steps that use
        # this kind exist precisely because a SECOND event must not happen.
        assert "n" in spec, "%s: bus-count needs an exact n" % where
        assert "min" not in spec and "max" not in spec, (
            "%s: bus-count asserts EXACTLY n, never a range. A count that has "
            "drifted is the failure this catches, and a range cannot." % where)

    if kind in BUS_KINDS:
        # ⛔ A TAP ON A BUS THE STEP ITSELF WRITES IS VACUOUS. The bench sent the
        # traffic, bench-tap read it back, and the patch under test was never
        # involved -- the predicate proves only that Pd delivers messages.
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
    return []


def lint_agreement(meta, pass_if, where):
    """⛔ THE PREDICATE AND THE PROSE MUST AGREE.

    A step has two oracles now -- a person reading the PASS IF, and a program
    reading the bus -- and nothing stops them drifting apart. Change the
    predicate without the prose and the run goes green while the sentence
    describing it is false; change the prose without the predicate and a person
    marks off something the machine never checked. Either way the step still
    LOOKS covered, which is worse than not being covered at all.

    ⚠️ WORD BY WORD RATHER THAN WHOLE-STRING, and that is not laziness. A
    predicate reads the wire and prose reads as English: the bus carries
    `sp-pad 5` and the sentence says "sp-pad reads 5". Demanding the exact
    string would force the prose to be rewritten into wire format -- and these
    sentences are hardware-verified and are not to be reworded.
    """
    spec = meta.get("check")
    if not spec:
        return
    prose = (pass_if + " " + meta.get("watch", "")).lower()
    for claim in _claims(spec):
        for word in str(claim).split():
            assert word.lower() in prose, (
                "%s: the predicate asserts %r but %r appears nowhere in the "
                "PASS IF or in `watch`. Either the prose is now wrong, or the "
                "predicate is -- say which in the step rather than letting a "
                "person and a program answer different questions."
                % (where, claim, word))


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
    # ⚠️ `oled` IS EXEMPT FROM THE SELF-WRITE RULE ABOVE and must be: display
    # step 3 writes to disp and then asserts on what g_oled DREW, which is
    # downstream of the patch rather than an echo of the bench. Refusing that
    # would refuse every screen assertion there is.
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

    Each block counts beats freely, and a bang on $0-zero resets it AND arms a
    timer of bench_steps.WINDOW_MS that latches the count and prints it. $0-read
    reprints the latched value, so the number always covers exactly that window
    no matter when the step that reads it is reached.

    ⛔ THE WINDOW IS NOT WRITTEN DOWN HERE. It is bench_steps.WINDOW_MS, because
    test/runner/ has to open its predicate window over the same span -- and the
    prose below is derived from it too, so a bench header cannot come to say TEN
    while the [del] says something else.
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
          "OPTIONAL. mother only forwards encbut once a patch has asked with /enableEncoder \\, "
          "and NOTHING IN Cut It EVER ASKS -- m_organelle leaves the encoder out on purpose. So "
          "the click that drives this bench on the Mac is silently dead on the Organelle. Send "
          "instead with ./tools/go.sh from the Mac. ⚠️ NOT netcat: the one-liner this file used "
          "to print here does nothing on macOS -- BSD nc exits before the datagram is flushed at "
          "-w0 \\, and -w1 was measured to fail too \\, while the port IS bound and the bench is "
          "fine. It looks exactly like a dead bench. The device cannot send to itself either: "
          "busybox here has no nc at all. Asking mother to enable the encoder is NOT the fix "
          "either: that means writing to oscOut \\, and g_oled is its sole owner.", 120)
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
    net_rt = p.obj(300, Y + 320, "route go")
    net_t = p.obj(300, Y + 380, "t b")
    net_s = p.obj(300, Y + 440, "s \\$0-go")
    p.con(net_r, 0, net_rt, 0)
    p.con(net_rt, 0, net_t, 0)
    p.con(net_t, 0, net_s, 0)

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
    # both stores are written by name for the same reason as the phase above: a
    # cord back to boxes 1700px to the left would be drawn through the branch
    # between them. They cannot drift, because one trigger writes both.
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

    rep_rr = p.obj(2100, Y, "r \\$0-repeat")
    rep_ss = p.obj(2100, Y + 60, "s \\$0-do-show")
    p.con(rep_rr, 0, rep_ss, 0)

    lb = p.obj(2500, Y, "loadbang")
    lbd = p.obj(2500, Y + 60, "del 500")
    lb1 = p.msg(2500, Y + 120, "1")
    lbs = p.obj(2500, Y + 180, "s \\$0-set-step")
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

        # ⚠️ THE SUBSTRING TEST IS KNOWN TO BE WRONG and is kept only until the
        # runner's meta carries the flag: measured, it misses NINE hands-on steps
        # -- all three `THE NANO --`, both tempo `BY HAND`, and four of the six
        # state steps. A flag has to be a field, not a guess at prose.
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


# ⛔ THE KEY IS THE OUTPUT FILENAME, and it is the only list of benches there is.
# bench-verify.py derives its own list from these keys rather than repeating them,
# because it used to carry a hand-typed tuple (3, 4, 5, 6, 7, 8, 9) -- a third
# copy of the same list, alongside this table and the STEPS_ names -- and missing
# it meant a bench was generated but NEVER FIDELITY-CHECKED. That trap is gone
# rather than documented.
#
# ⚠️ These are named for MODULES now, not phases. What a bench asks a person to do
# has not changed by one word; only which page can honestly point at it.
BENCHES = {
    "display": dict(steps=S.STEPS_DISPLAY, counters=[],
                    blurb="the display acceptance run: the display arbiter and "
                    "the error bus."),
    "nanokontrol": dict(steps=S.STEPS_NANOKONTROL, counters=[],
                        blurb="the nanoKONTROL acceptance run: every fader \\, knob "
                        "and transport key \\, and the multi-parameter display."),
    "tempo": dict(steps=S.STEPS_TEMPO,
                  blurb="the tempo acceptance run: the clock \\, the transport \\, "
                  "the map and the aux LED.",
                  counters=[("M-BEATS", "r clock"),
                            ("C1-BEATS-ratio-1", "c_clock 1 4"),
                            ("C2-BEATS-ratio-1.5", "c_clock 1.5 4")],
                  declare="-path ../../Cut\\ It"),
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

    ⛔ IT LISTENS AND SENDS NOTHING. Not one message box, not one [s], nothing.
    C-5 gives g_oled sole ownership of oscOut and g_grid its own surface, but
    that rule governs WRITING: adding a [receive] cannot change what any other
    subscriber gets, because Pd delivers a message to every receiver of a name.
    ⚠️ SO DO NOT "FIX" THIS FILE BY ROUTING ITS OUTPUT ANYWHERE. Its whole value
    is that loading it cannot change what the bench under it does.

    ⛔ THE LABELS COME FROM lib_drive.TAP_LABELS, which is also what
    lib_assert.parse() matches -- so the runner reuses the gates' parser instead
    of growing a second one. Two parsers is how a fix reaches one and not the
    other, which is the failure the whole test refactor existed to remove.

    ⛔ `clock` IS NOT TAPPED. It carries a beat twice a second forever and would
    bury every window in noise no predicate wants.
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
    # ⛔ AND THE SCREEN ITSELF. oscOut is how g_oled draws, so this is the only
    # way to assert what the OLED was TOLD to show -- Pd cannot ask a screen what
    # it is displaying, but the bytes sent to it are completely knowable, which
    # is the right level to test our own code at.
    # ⚠️ C-5 MAKES g_oled THE SOLE OWNER OF oscOut AND THIS DOES NOT BREAK IT:
    # ownership governs WRITING. Nothing here writes.
    taps.append(("oscOut", "OLED"))
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
