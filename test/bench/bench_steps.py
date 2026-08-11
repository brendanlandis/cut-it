"""Step tables for the seven benches -- the DATA half of bench-gen.py.

Each step is (title, pass_if, [(message, bus), ...]) and optionally a fourth
element, a dict -- see norm() below.

⛔ A STEP SAYS WHAT TO SEE AND WHAT TO DO. NOTHING ELSE.
No mechanism, no rationale, no history, no "this step exists because". A person
reads this with the rig in front of them and one question -- did that happen or
not. Why it happens is on the module's ref/ page; why it is tested this way is
in git log. Both were in here, and they buried the sentence that mattered.

⛔ CAPITALS MEAN "THIS IS LITERALLY ON THE SCREEN OR THE LABEL", never emphasis.
`EXT` is printed on the 404, `NO-LINK` on the phone, `SETUP` on the Launchpad;
`NOTHING CHANGES` was just loud. With capitals doing both jobs they did neither.
bench-gen.py's `lint_caps` holds the literal set and refuses anything else.

⛔ WHAT A STEP CLAIMS IS FIXED. HOW IT READS IS NOT. Every one of these was
transcribed out of a hand-authored .pd by test/bench/bench-extract.py, and the
benches behind them are verified on the Organelle -- so a change here may never
alter what a step ASSERTS. Wording is a different question, and it was rewritten
in full on 2026-08-10. test/bench/bench-verify.py re-extracts from the
regenerated files and diffs against these tables.

⛔ NO COMMA AND NO SEMICOLON IN A `title` OR A `pass_if`. A message box treats
either as a message SEPARATOR whatever the escaping -- `\\,` satisfies the .pd
parser and still printed one PASS IF as THREE fragments, and the same defect
produced fourteen on the first Phase 6 run. Full stops are safe; a full stop
straight after a digit is not, because Pd reads `12.` as the float 12 and the
stop disappears (item 122). That is why these read as short sentences joined by
` -- ` rather than as ordinary prose, and why bench-gen.py asserts it rather
than trusting review.

⚠️ `need`, `do` and `watch` NEVER REACH A .pd -- see norm() -- so they carry
ordinary commas and are written as plain instructions.
"""
import re

# ---------------------------------------------------------------------------
# ⛔ THE MEASUREMENT WINDOW LIVES HERE AND NOWHERE ELSE. bench-gen.py builds the
# [del] from it and test/runner/ opens its predicate window from it, and until
# this existed the same 10000 was written in the generator and would have been
# written again in the runner -- two copies of one number, which is exactly the
# drift this project keeps eliminating. The generator's own prose is derived from
# it too, so "TEN SECOND" in a bench header cannot go stale either.
WINDOW_MS = 10000

# ⛔ AND WHAT MARKS A MEASURE STEP. A step that sends to a bus ending in this is
# arming a timed count, so the prompt tells the person to WAIT for the printed
# number and the runner holds its window open for WINDOW_MS instead of judging
# immediately. Same reason as above: the generator and the runner must agree, so
# there is one definition rather than two spellings of "-zero".
MEASURE_SUFFIX = "-zero"

# ---------------------------------------------------------------------------
# ⛔ THE CONSOLE PROTOCOL, AND BOTH HALVES OF IT LIVE HERE.
#
# A bench announces itself on Pd's console and test/runner/ reads those lines
# back to know which step is running -- so the generator's format strings and the
# runner's regexes are two halves of ONE agreement. Written apart they drift
# silently and in the worst possible way: the runner stops recognising a step,
# calls it a stall, and the bench is fine. Written together, a change to the
# wording has to pass runner-assert, which checks each regex against the string
# its own format produces.
#
# ⚠️ THE REGEXES ARE UNANCHORED ON PURPOSE. These reach the console through a
# bare [print], so every line arrives with Pd's own "print: " in front of it.
SAY_STEP = "=== STEP-%02d-of-%02d === %s"
SAY_PROMPT = ">>> press GO to run step %d of %d"
SAY_FIRED = ("--- step %d fired --- judge it against the PASS IF above --- "
             "press GO for step %d")
SAY_FIRED_LAST = ("--- step %d fired --- that was the last one --- "
                  "press GO to finish")
SAY_COMPLETE = ("=== BENCH COMPLETE === every step has been run -- reload the "
                "patch to go round again")

RE_STEP = re.compile(r"=== STEP-(\d+)-of-(\d+) === (.*?)\s*$")
RE_FIRED = re.compile(r"--- step (\d+) fired ---")
RE_COMPLETE = re.compile(r"=== BENCH COMPLETE ===")


def norm(step):
    """A step is 3 or 4 long -> (title, pass_if, actions, meta).

    ⛔ THE FOURTH ELEMENT IS RUNNER-SIDE ONLY AND NEVER REACHES A .pd. It carries
    what a person needs (`need`, `do`, `watch`) and what a program needs
    (`check`, `wait`, `targets`) -- and keeping it out of the patch is not
    tidiness. Emitting it would reopen every hardware-verified step text to the
    comma/semicolon fragmentation hazard the generator exists to prevent, which
    produced fourteen fragments on the first Phase 6 run. It buys nothing either:
    with the runner in place the person reads the runner's terminal, not Pd's
    console.

    ⚠️ SO bench-verify.py STILL DIFFS THREE FIELDS. Its round trip proves the
    step TEXT survived generation, and meta is not text that gets generated.
    """
    title, pass_if, actions = step[0], step[1], list(step[2])
    return title, pass_if, actions, dict(step[3]) if len(step) > 3 else {}


STEPS_DISPLAY = [
 ('Resting display',
  'PASS IF: Two bars with a small gate mark under each. A BPM at the bottom. The footer changes from v0.3-ready to the tempo about four seconds in.',
  []),
 ('Parameter with a unit',
  'PASS IF: chop-size on the top line and a big 43 % under it. The bars shrink to a thin strip. About 1.2 s later the meters come back on their own.',
  [('chop-size 43 %', 'disp')]),
 ('Parameter with no unit',
  'PASS IF: grain and then a big 12 with no percent sign left over from the last step.',
  [('grain 12', 'disp')],
  # ⛔ EXACT ROWS, NOT SUBSTRINGS, AND NOT A TIMED WINDOW. g_oled draws a
  # parameter as two rows -- the name, then the value -- and the stale unit shows
  # up as a VALUE ROW reading `12 %` where it must read `12`. Asserting exact
  # rows catches that whatever else is on screen, which matters because g_oled
  # stacks up to five parameters: for about 1.3 s after the previous step the
  # screen correctly shows chop-size 43 % as well, so a screen-wide `no %` test
  # reports a failure that is really the runner outpacing the fade. Tried that
  # first, both ways -- judging at once saw the %, waiting 2.5 s saw grain fade
  # away too. An exact row does not care.
  {'check': {'kind': 'oled', 'has_row': ['grain', '12']}}),
 ('Modal',
  'PASS IF: recording in mid-size text with the bars as a thin strip. It stays and does not fade.',
  [('modal recording', 'disp')]),
 ('Parameter under a modal',
  'PASS IF: Nothing changes. Still recording. chop-size never appears.',
  [('modal recording', 'disp'), ('chop-size 43 %', 'disp')]),
 ('Warning over a modal',
  'PASS IF: A bordered box reads warn then u_root then test-warn. About 2 s later it vanishes and recording is back underneath.',
  [('modal recording', 'disp'), ('warn u_root test-warn', 'err')]),
 ('Switch to perform',
  'PASS IF: Nothing changes. Still recording. Mode is never drawn.',
  [('modal recording', 'disp'), ('perform', 'mode')]),
 ('Warning in perform',
  'PASS IF: Nothing changes. No alert box at all. Still recording.',
  [('modal recording', 'disp'), ('warn u_root hidden-warn', 'err')]),
 ('Failure in perform',
  'PASS IF: An alert does appear reading fail then u_root then shown-fail. recording returns after about 4 s.',
  [('modal recording', 'disp'), ('fail u_root shown-fail', 'err')]),
 ('Switch back to compose',
  'PASS IF: Nothing changes. Still recording.',
  [('modal recording', 'disp'), ('compose', 'mode')]),
 ('Warning in compose',
  'PASS IF: The alert does appear this time reading warn then u_root then back-again.',
  [('modal recording', 'disp'), ('warn u_root back-again', 'err')]),
 ('Clearing the modal',
  'PASS IF: recording disappears. You are back to the two meters and the BPM footer.',
  [('modal recording', 'disp'), ('modal-off', 'disp')]),
 ('Modal safety timeout',
  'PASS IF: stuck appears now. Then wait and watch -- with no further input it clears itself after 30 s. Do not answer until it has.',
  [('modal stuck', 'disp')]),
 ('Modal safety timeout -- the wait',
  'PASS IF: The screen returned to the meters on its own while you waited.',
  []),
]

STEPS_NANOKONTROL = [
 ('Resting display',
  'PASS IF: Two bars with a small gate mark under each. A BPM at the bottom. The footer changes from v0.3-ready to the tempo about four seconds in.',
  []),
 ('One parameter',
  'PASS IF: chop-size small on the top line and a big 43 % under it.',
  [('chop-size 43 %', 'disp')]),
 ('Two parameters',
  'PASS IF: Two stacked pairs -- chop-size over 43 % on top and grain over 12 below. First touched on top. The values are mid-sized.',
  [('chop-size 43 %', 'disp'), ('grain 12', 'disp')]),
 ('Five parameters',
  'PASS IF: Five small lines in the order they were first touched: chop-size then grain then slider-1 then knob-3 then btn-t-2.',
  [('chop-size 43 %', 'disp'), ('grain 12', 'disp'), ('slider-1 64', 'disp'), ('knob-3 100', 'disp'), ('btn-t-2 1', 'disp')]),
 ('Seven parameters -- two too many',
  'PASS IF: Still exactly five lines -- a1 a2 a3 a4 a5. a6 and a7 are refused rather than pushing the rows around. Nothing shifts.',
  [('a1 1', 'disp'), ('a2 2', 'disp'), ('a3 3', 'disp'), ('a4 4', 'disp'), ('a5 5', 'disp'), ('a6 6', 'disp'), ('a7 7', 'disp')]),
 ('A single parameter is drawn big',
  'PASS IF: a1 alone on screen at the big 24px layout. One parameter is drawn big where five are drawn as small lines.',
  [('a1 1', 'disp')]),
 ('Modal over parameters',
  'PASS IF: recording at mid size. The chop-size sent with it never appears.',
  [('modal recording', 'disp'), ('chop-size 43 %', 'disp')]),
 ('Warning over a modal',
  'PASS IF: A bordered alert reads warn then u_root then bench-warn. About 2 s later it vanishes and recording is still there underneath.',
  [('modal recording', 'disp'), ('warn u_root bench-warn', 'err')]),
 ('Switch to perform',
  'PASS IF: Nothing changes. Still recording.',
  [('modal recording', 'disp'), ('perform', 'mode')]),
 ('Warning in perform',
  'PASS IF: Nothing changes. No alert at all.',
  [('modal recording', 'disp'), ('warn u_root hidden-warn', 'err')]),
 ('Failure in perform',
  'PASS IF: An alert does appear. recording returns after about 4 s.',
  [('modal recording', 'disp'), ('fail u_root shown-fail', 'err')]),
 ('Switch back to compose',
  'PASS IF: Nothing changes. Still recording.',
  [('modal recording', 'disp'), ('compose', 'mode')]),
 ('Warning in compose',
  'PASS IF: The alert does appear this time.',
  [('modal recording', 'disp'), ('warn u_root back-again', 'err')]),
 ('Clearing the modal',
  'PASS IF: recording disappears. You are back to the two meters and the BPM footer.',
  [('modal recording', 'disp'), ('modal-off', 'disp')]),
 ('Every slider and knob',
  "PASS IF: Each control names itself -- slider-1 to slider-9 then knob-1 to knob-9. None reports another's name. Watch slider 9 and knob 1 especially.",
  [],
  {'do': 'Sweep every slider and every knob on the nanoKONTROL.',
   'need': ['The nanoKONTROL powered and connected.']}),
 ('Several faders at once',
  'PASS IF: Two stay readable as stacked pairs. Three to five become small lines. Nine shows the five you touched first with the rest refused. Rows must not reshuffle while you move things.',
  [],
  {'do': 'Move two faders at once, then three, then all nine.',
   'need': ['The nanoKONTROL powered and connected.']}),
 ('Every button and transport key',
  'PASS IF: All 18 buttons name themselves on press and nothing on release. The six transport keys report xport-1 to xport-6 on press. No toggle and no footer change.',
  [],
  {'do': 'Press every button on the nanoKONTROL, then all six transport keys.',
   'need': ['The nanoKONTROL powered and connected.']}),

 # ⛔ HOT-SWAP, TWO CASES, AND ITEM 235 IS THE PROOF THEY ARE NOT THE SAME TEST.
 # The transition case needs the device to have ANSWERED at least once, because
 # c_presence's warn is armed by a reply -- a device that was never there is
 # ABSENT rather than lost, and absent raises nothing. The absent-at-load case
 # needs a fresh load and can see what no transition ever shows: that a device
 # missing at boot is recovered at all.
 ('Hot-swap -- unplugged mid-session',
  'PASS IF: A bordered alert on the OLED reads warn and then m_nano.',
  [],
  # ⚠️ wait 12 IS LOAD-BEARING -- the warn is three missed ticks behind the
  # unplug, up to 8 s, and the runner's default drain is 0.4 s.
  {'do': 'Press enter first, then unplug the nanoKONTROL and leave it out. Watch the OLED.',
   'need': ['The nanoKONTROL powered and connected.'],
   'wait': 20,
   'check': {'kind': 'bus', 'bus': 'ERR', 'has': ['warn m_nano']}}),
 ('Hot-swap -- absent at load',
  'PASS IF: Slider 1 moves a value on the OLED.',
  [],
  # ⚠️ 60 SECONDS AND NOT 10 -- the nano needed two of the eight attempts on the
  # bench because the device was still enumerating when the first landed (item
  # 277). ⛔ AND THE SLIDER IS THE ORACLE, not the absence of a warn: the nano is
  # PASSIVE to look at, so the only proof the subscription came back is traffic
  # arriving through it.
  {'do': 'Plug it in, wait 60 seconds, then move slider 1.',
   'reload': True,
   'need': ['The nanoKONTROL still unplugged from the last step.']}),
]

STEPS_TEMPO = [
 ('Resting display at 120 BPM',
  'PASS IF: Two bars with a small gate mark under each and 120-bpm in the footer. The aux button is lit dark blue.',
  [('120', 'tempo'), ('bang', 'stop')]),
 ('Zero the beat counters',
  'PASS IF: Nothing visible changes. The transport is still stopped.',
  [('bang', '\\$0-zero')]),
 ('Beat counts while stopped',
  'PASS IF: M-BEATS reads 20 or 21 beats. C1-BEATS reads the same number. C2-BEATS reads 30 or 31 in the same window. A zero anywhere is a failure -- on the Mac check DSP is on first.',
  [('bang', '\\$0-read')],
  # ⛔ THE RATIO IS THE POINT, and it is why this is not three range checks. A
  # count in a range still depends on the real-time scheduler having kept up;
  # C2/C1 cancels the scheduler entirely, because both counters were driven by
  # the same clock over the same window. tempo-assert.sh makes the same argument
  # about 24 PPQN on the wire.
  {'watch': 'M-BEATS reads 20 or 21, C1-BEATS-ratio-1 the same, C2-BEATS-ratio-1.5 reads 30 or 31, and C2 over C1 is 1.5.',
   'check': {'kind': 'all', 'of': [
      {'kind': 'print', 'name': 'M-BEATS', 'min': 19, 'max': 22},
      {'kind': 'print', 'name': 'C1-BEATS-ratio-1', 'min': 19, 'max': 22},
      {'kind': 'print', 'name': 'C2-BEATS-ratio-1.5', 'min': 29, 'max': 32},
      {'kind': 'ratio', 'a': 'C2-BEATS-ratio-1.5', 'b': 'C1-BEATS-ratio-1',
       'want': 1.5, 'tol': 0.15},
  ]}}),
 ('Start the transport',
  "PASS IF: The aux button turns green and the 404 starts its pattern. Watch EXT on the 404's pattern select screen. The number beside a pad never moves.",
  [('bang', 'start')]),
 ('Knob pickup holds',
  "PASS IF: ⛔ What you see depends on whether A Save has ever happened. With a saved knobs.txt -- the device after any Storage Save -- the footer does not move. With no knobs.txt -- always on the Mac and on the device after tools/deploy.sh --clean -- the footer reads 10-bpm and the 404's EXT slides down.",
  [('og-knob-1 0', 'param')]),
 ('Knob pickup crosses over',
  "PASS IF: The footer reads 500-bpm and the 404's EXT slides up. A slide rather than a snap is correct.",
  [('og-knob-1 1', 'param')]),
 ('Knob tracking after pickup',
  'PASS IF: The footer reads 10-bpm on either machine. If it is held here too then the knob is stuck and that is the failure.',
  [('og-knob-1 0', 'param')]),
 ('Tempo above range',
  'PASS IF: The footer reads 600-bpm and exactly one alert appears -- a bordered box naming u_tempo. The second 5000 is silent.',
  [('5000', 'tempo'), ('5000', 'tempo')],
  # ⛔ EXACTLY ONE, and that is the whole step. The second 5000 must be silent
  # because the VALUE did not change -- "one or more alerts" is satisfied by two
  # and would pass the bug. A person counting bordered boxes on an OLED that
  # redraws is exactly the oracle a machine should replace.
  {'check': {'kind': 'bus-count', 'bus': 'ERR', 'match': 'u_tempo', 'n': 1}}),
 ('Tempo below range',
  'PASS IF: The footer reads 5-bpm and a second alert appears.',
  [('0', 'tempo')]),
 ('Back in range',
  'PASS IF: The footer reads 120-bpm and no alert appears at all.',
  [('120', 'tempo')]),
 ('Stop the transport',
  'PASS IF: The aux button goes dark blue and the 404 stops. But its display must still say EXT. If it falls back to BPM that is the failure.',
  [('bang', '\\$0-zero'), ('bang', 'stop')]),
 ('Beat counts after stopping',
  'PASS IF: M-BEATS reads 20 or 21 again.',
  [('bang', '\\$0-read')],
  # ⛔ A ZERO HERE IS THE BUG THE STEP EXISTS FOR: the transport pauses the
  # subscribers, it does not clear the timer, and a clock that stopped with the
  # transport leaves the 404 stretching every sample to a stale tempo.
  {'check': {'kind': 'print', 'name': 'M-BEATS', 'min': 19, 'max': 22}}),
 ('Panic',
  'PASS IF: The aux button turns red and the footer says panic.',
  [('bang', 'panic')]),
 ('Aux button transport',
  'PASS IF: On the device use the real button. On the Mac use aux-tap and not the aux toggle. First press green and the 404 starts. Second press dark blue and it stops.',
  [],
  {'do': 'Press the aux button twice. On the Mac use aux-tap and not the aux toggle.',
   'need': ['The Organelle powered and in reach.']}),
 ('Knob 1 tempo sweep',
  'PASS IF: The row reads bpm and a number. Never og-knob-1 and never a 0-to-1 decimal. While the knob is still held it reads bpm 57 (120) or similar -- the latched tempo first and the knob position in brackets. Once it crosses it reads bpm alone and tracks between 10 and 500 BPM. The 404 follows the sweep.',
  [],
  {'do': 'Sweep Organelle knob 1 all the way and back. A full sweep always crosses.',
   'need': ['The Organelle powered and in reach.']}),
]

STEPS_LAUNCHPAD = [
 ('Resting grid',
  'PASS IF: The top row shows one bright green lamp at the far left and five dim ones beside it. The bottom row of pads has a single white pad. Dim means faint and not off. The white pad is already walking and that is correct -- a frozen pad is the failure. Everything else on the surface is dark.',
  [('120', 'tempo'), ('bang', 'stop'), ('compose mode-1', 'mode')]),
 ('Mode lamp 4',
  'PASS IF: The bright lamp moves to the fourth position and the other five go dim. Nothing else on the grid changes.',
  [('perform mode-4', 'mode')]),
 ('Mode lamp 2',
  'PASS IF: The bright lamp lands on the second position.',
  [('compose mode-2', 'mode')]),
 ('Mode lamp 5',
  'PASS IF: The bright lamp lands on the fifth position and the other five go dim.',
  [('perform mode-5', 'mode')]),
 ('Mode lamp 6',
  'PASS IF: The bright lamp lands on the sixth and last position.',
  [('perform mode-6', 'mode')]),
 ('Grid vocabulary stays off the OLED',
  'PASS IF: Nothing happens on either surface. In particular no parameter row called grid appears on the OLED.',
  [('grid no-such-thing', 'disp')]),
 ('Modal claims the surface',
  'PASS IF: Every pad and every lamp on the top row turns blue. The mode lamps are covered too. The OLED must not change.',
  [('grid modal 45', 'disp')]),
 ('Mode change under a modal',
  'PASS IF: Nothing happens. The surface stays blue. The mode really does change underneath and you will see it two steps from now.',
  [('grid modal 45', 'disp'), ('perform mode-3', 'mode')]),
 ('Alert over a modal',
  'PASS IF: The surface turns red for about two seconds and then goes back to blue -- not to the mode lamps.',
  [('grid modal 45', 'disp'), ('fail u_bench stacked', 'err')]),
 ('Clearing the modal',
  'PASS IF: The grid returns to mode lamps and the beat row. The bright lamp is now the third one -- the change made while the modal covered it.',
  [('grid modal 45', 'disp'), ('grid modal-off', 'disp')]),
 ('A fail takes the surface',
  'PASS IF: The whole surface turns red and then goes back to the mode lamps by itself after about two seconds. A grid that stays red is the failure.',
  [('fail u_bench boom', 'err')]),
 ('A warn does not',
  'PASS IF: Nothing happens on the grid and the OLED does show the warning.',
  [('compose mode-3', 'mode'), ('warn u_bench quiet', 'err')]),
 ('Modal safety timeout',
  'PASS IF: The surface turns green and then clears itself about thirty seconds later with nothing sent to it. Do not press GO -- sit and watch it.',
  [('grid modal 21', 'disp')]),
 ('Start the transport',
  'PASS IF: The white pad walks along the bottom row twice a second and the aux LED goes green. On the Mac the aux LED is not A button -- it is the numeric readout labelled aux-LED on the bottom row of the dev panel -- with a symbol box beside it spelling the colour. On the Mac tick enable-DSP first or the pad will not move. A BEATS line prints about ten seconds from now.',
  [('bang', 'start'), ('bang', '\\$0-zero')],
  # The eyes still judge the walking pad and the aux LED. What the machine can
  # judge is the number underneath them, which is the same evidence and is not
  # subject to anyone counting flashes.
  # ⚠️ THE EXPECTED COUNT IS STATED IN `watch` BECAUSE THE PASS IF DOES NOT SAY
  # IT -- it only promises a BEATS line "about ten seconds from now". A predicate
  # asserting a number the prose never mentions is a disagreement waiting to
  # happen, and the person reading the terminal deserves to know what it wants.
  {'watch': 'The white pad walks along the bottom row twice a second and the aux LED goes green, then a BEATS line of about 20 prints about ten seconds from now.',
   'check': {'kind': 'print', 'name': 'BEATS', 'min': 19, 'max': 22}}),
 ('Beat row wrapping',
  'PASS IF: The white pad reaches the eighth pad and the next beat is back to the first -- with no gap and no stray light anywhere else. Nothing is sent for this step. Just watch one wrap go by.',
  []),
 ('Beat row at 240 BPM',
  'PASS IF: The white pad moves twice as fast. The BEATS line just printed should read about 20 beats and the next one about 40 beats. Expect A visible swing here and do not fail the step for it -- the row can only move on a 100 ms boundary so at 240 BPM it swings either way by 50 ms.',
  [('bang', '\\$0-read'), ('240', 'tempo'), ('bang', '\\$0-zero')]),
 ('Back to 120 and stopped',
  'PASS IF: The second BEATS line reads about 40 and then the beat row slows to two a second. The pad must keep walking after the stop.',
  [('bang', '\\$0-read'), ('120', 'tempo'), ('bang', 'stop')]),
 ('Pads and releases',
  'PASS IF: Every pad you press reports pad-NN on the OLED with its velocity. Releasing it reports the same name with a velocity of 0 instead. Numbering runs from 11 at the bottom left to 88 at the top right. Pressure on a held pad reports nothing and that is correct.',
  [],
  {'do': 'Press pads on the Launchpad and release them.',
   'need': ['The Launchpad connected and in Programmer Mode.']}),
 ('Ring buttons',
  'PASS IF: The ring buttons report lp-cc-NN. Check the top left corner reads 90 and the bottom row runs from 101 to 108 in order. CC 1 to 8 must be lit like everything else and must go blue under a modal and red under an alert. One button stays dark -- index 0 -- SETUP. It takes no colour and transmits nothing.',
  [],
  {'do': 'Press the Launchpad ring buttons, including the top left corner and the bottom row.',
   'need': ['The Launchpad connected and in Programmer Mode.']}),
 ('Transport keys change mode',
  'PASS IF: Each of the six keys moves the bright lamp to its own position.',
  [],
  {'do': 'Press each of the six nanoKONTROL transport keys.',
   'need': ['The nanoKONTROL powered and connected.', 'The Launchpad connected and in Programmer Mode.']}),
 # ⛔ THESE TWO REPLACED THE REPLUG HAZARD STEP, WHICH DESCRIBED A HAZARD THAT NO
 # LONGER EXISTS. It read "the device returns in Live Mode but m_launchpad still
 # believes it owns the surface -- press a few pads and watch pad-NN names appear
 # on the OLED", and closed "Not built yet. See plan-v04.md". Presence drops
 # ownership on the third missed poll and the bounded re-wire brings the device
 # back with Programmer Mode re-asserted -- item 276, verified on the hardware --
 # so the step asserted the opposite of what the instrument does, and pointed at a
 # plan-v04 section that had already gone.
 #
 # ⛔ TWO CASES, AND ITEM 235 IS THE PROOF THEY ARE NOT THE SAME TEST. "Lost" was
 # built as a transition from present to absent, and never-present is not a
 # transition -- so a device that was missing when the patch loaded could not be
 # recovered at all, however long you waited. Only the second step below can see
 # that, and only from a fresh load.
 ('Hot-swap -- unplugged mid-session',
  'PASS IF: A bordered alert on the OLED reads warn and then m_launchpad. The grid goes dark.',
  [],
  # ⚠️ THE PREDICATE READS err AND THE EYES READ THE GRID, and neither covers the
  # other. c_presence publishes the warn; g_grid going dark is m_launchpad
  # dropping ownership two boxes further on, and no bus carries "the grid stopped
  # painting".
  # ⚠️ wait 12 IS LOAD-BEARING. The warn is three missed ticks behind the unplug
  # -- up to 8 s at the shipped 2000 ms tick -- and the runner's default drain is
  # 0.4 s, which would miss it on entirely correct hardware.
  {'do': 'Press enter first, then unplug the Launchpad USB and leave it out. Watch the OLED and the grid.',
   'need': ['The Launchpad connected and in Programmer Mode, with the grid lit.'],
   'wait': 20,
   'check': {'kind': 'bus', 'bus': 'ERR', 'has': ['warn m_launchpad']}}),
 ('Hot-swap -- absent at load',
  'PASS IF: The grid lights and the top row shows one green lamp.',
  [],
  # ⚠️ 60 SECONDS AND NOT 10. A replug is routinely missed by the FIRST re-wire
  # because the device is still enumerating -- the Launchpad used six of its eight
  # attempts on the bench, item 277 -- and the eight are spread over seventy
  # seconds. Anything under about 50 s fails intermittently on correct code.
  {'do': 'Plug the Launchpad in and wait up to 60 seconds without touching anything else.',
   'reload': True,
   'need': ['The Launchpad still unplugged from the last step.']}),
 ('Panic hands the surface back',
  'PASS IF: The Launchpad visibly leaves Programmer Mode and its own display returns. Button presses stop reaching the OLED. Watch both. It stays handed back until the patch is reloaded -- so every remaining step is downstream of this one and nothing after it can check the grid. If you have any doubt about an earlier step go back and redo it before pressing GO here.',
  [('bang', 'panic')]),
 ('Grid silent after panic',
  'PASS IF: Nothing happens. The Launchpad keeps showing its own display.',
  [('compose mode-1', 'mode')]),
 ('Pads silent after panic',
  'PASS IF: Nothing reaches the OLED. Reload the patch to get the grid back.',
  [],
  {'do': 'Press a pad on the Launchpad now that the panic has run.',
   'need': ['The Launchpad connected and in Programmer Mode.']}),
]



# Phase 7 -- the phone. Every PASS IF here describes what the PHONE shows, which
# makes this the first bench whose subject is not the Organelle. Three steps are
# hands-only and one of them (closing PdParty) is the only way to reach item 114's
# ICMP teardown on real hardware.
#
# THE RATE LIMIT IS NOT TESTED HERE AND CANNOT BE. A step table pushes discrete
# messages; a flood needs a metro. test/gate/phone-assert.sh is what proves the
# coalescer, and step 12 is the closest a person can get -- a real fader, and the
# question of whether the phone SETTLES on the value you stopped at.
STEPS_PHONE = [
 ('The link is up',
  'PASS IF: The bottom line of the phone reads ok rather than NO-LINK. IF it says NO-LINK stop here and check that PdParty is open on the same network. Every step below depends on it.',
  [('compose mode-1', 'mode')]),
 ('One parameter',
  'PASS IF: The top line reads chop-size and the big number reads 43 on its own. The unit is not drawn and that is correct.',
  [('chop-size 43 %', 'disp')],
  # ⚠️ THE MAC RUN IS A MIRROR AND ANSWERS A DIFFERENT QUESTION FROM THE DEVICE.
  # With u_net repointed at localhost the datagrams are readable here, so what
  # u_net FILTERS can be judged with no phone at all. What no Mac can judge is
  # what the PHONE then draws -- so the device run keeps its human verdict.
  {'targets': ('mac',),
   'check': {'kind': 'osc', 'addr': '/cutit/param', 'has': ['chop-size', '43']}}),
 ('A second parameter',
  'PASS IF: The top line changes to grain and the number to 12 with it.',
  [('grain 12', 'disp')]),
 ('The status line',
  'PASS IF: The third line reads 128-bpm and the parameter name and number above it do not change. Expect u_tempo to overwrite it with the real BPM at the next transport event.',
  [('status 128-bpm', 'disp')]),
 ('An alert reaches the phone',
  'PASS IF: The fourth line shows warn on the left and probe-warning on the right.',
  [('warn u_bench probe-warning', 'err')]),
 ('The alert persists',
  'PASS IF: Several seconds later the fourth line still reads warn and probe-warning. On the OLED the same alert has long since timed out. The two surfaces disagree on purpose.',
  []),
 ('A second alert replaces it',
  'PASS IF: The fourth line changes to fail and probe-failure.',
  [('fail u_bench probe-failure', 'err')]),
 ('Meters must not appear',
  'PASS IF: Nothing on the phone changes at all. A line reading in-l or in-r is the failure.',
  [('in-l 42 dB', 'disp'), ('in-r 7 dB', 'disp')],
  # ⛔ THE has HALF IS THE WITNESS, not decoration. "in-l never appears" is
  # satisfied by a u_net that emitted nothing at all -- which is what a broken
  # one looks like -- so the heartbeat proves the link was live while the
  # meters were being dropped. The lint refuses this predicate without it.
  {'targets': ('mac',),
   'check': {'kind': 'all', 'of': [
       {'kind': 'osc', 'addr': '/cutit/hb', 'has': []},
       {'kind': 'osc', 'addr': '/cutit/param', 'has_not': ['in-l', 'in-r']}]}}),
 ('Grid vocabulary must not appear',
  'PASS IF: Nothing on the phone changes. The Launchpad going modal is correct. The next step clears it.',
  [('grid modal 45', 'disp')]),
 ('Clearing the grid',
  'PASS IF: The Launchpad returns to its home layout and the phone does not move.',
  [('grid modal-off', 'disp')]),
 ('The aux LED',
  'PASS IF: The aux button goes green and the phone does not move.',
  [('led running', 'disp')]),
 ('Fast fader sweep',
  'PASS IF: The phone tracks the fader while it moves and then settles on the value you stopped at. A phone left showing a number from the middle of the sweep is the failure. Sweep two faders at once if you have the fingers -- both must settle.',
  [],
  {'do': 'Sweep a nanoKONTROL fader as fast as you can, two at once if you have the fingers.',
   'need': ['The nanoKONTROL powered and connected.', 'PdParty open on the CutItRemote scene.']}),
 ('Link lost',
  'PASS IF: Nothing on the Organelle changes. No audio glitch and no error on the OLED.',
  [],
  {'do': 'Close PdParty on the phone and count to ten.',
   'need': ['PdParty open on the CutItRemote scene.']}),
 ('Link recovers',
  'PASS IF: The phone starts updating again within about five seconds and you touched nothing on the Organelle.',
  [],
  {'do': 'Reopen PdParty on the phone. Touch nothing on the Organelle.',
   'need': ['PdParty open on the CutItRemote scene.']}),
]

STEPS_STATE = [
 ('Restored mode at boot',
  'PASS IF: The Launchpad top row shows exactly one lit mode lamp. Which one is the test -- a fresh install comes up on mode-1 and a restored one comes up wherever you left it. If the grid is dark then nothing below can be read.',
  [],
  {'do': 'Look at the Launchpad top row. Press nothing.',
   'need': ['The Launchpad connected and in Programmer Mode.']}),
 ('Change the mode',
  'PASS IF: The lit lamp moves to the fourth position. Nothing else is visible yet and that is correct.',
  [],
  {'do': 'Press transport key 4 on the nanoKONTROL.',
   'need': ['The nanoKONTROL powered and connected.', 'The Launchpad connected and in Programmer Mode.']}),
 ('The change reached the disk',
  'PASS IF: Cut-it-auto.txt reads mode perform mode-4. Nothing on the instrument shows this -- the file is the only evidence. If it still reads the old mode that is the failure.',
  [],
  # ⛔ THIS STEP USED TO INSTRUCT A PERSON TO RUN A SHELL COMMAND AND READ THE
  # OUTPUT. The file is the only evidence there is -- nothing on the instrument
  # displays what has been saved, deliberately -- so the runner fetches it and
  # compares the string, which is exactly what the person was doing by eye.
  {'do': 'Nothing on the instrument. The runner fetches the file and reads it for you.',
   'need': ['The Organelle reachable over the network.'],
   'targets': ('device', 'paper'),
   'check': {'kind': 'file', 'fetch': 'state',
             'path': 'device-state/cut-it-auto.txt',
             'contains': 'mode perform mode-4'}}),
 ('Front-panel Save',
  'PASS IF: The screen shows Saving briefly and returns. Then cut-it-manual.txt has a new timestamp even though it is still empty. An unchanged timestamp is the failure.',
  [],
  # ⚠️ A TIMESTAMP, NOT CONTENTS, AND IT HAS TO BE. cut-it-manual.txt is still
  # EMPTY -- no shipped contributor uses the manual policy yet -- so there is
  # nothing in it to compare. An UNCHANGED timestamp means saveState never
  # arrived and the commit path is dead, which is the whole assertion.
  {'do': 'On the Organelle press Storage then Save.',
   'need': ['The Organelle powered and in reach.'],
   'targets': ('device', 'paper'),
   'check': {'kind': 'file',
             'path': 'device-state/cut-it-manual.txt',
             'remote': '/sdcard/cut-it-state/cut-it-manual.txt',
             'newer_than': 'step-start'}}),
 ('Survives a power cycle',
  'PASS IF: The same mode lamp is lit as before the power cycle. Do this last in A session -- it resets the wifi fault uptime clock and that fault needs about three hours to reappear.',
  [],
  {'do': 'Power cycle the Organelle and wait for it to come back. Do this last in A session.',
   'need': ['The Organelle powered and in reach.', 'The Launchpad connected and in Programmer Mode.']}),
]


STEPS_MIDI = [
 ('Restored tempo at boot',
  'PASS IF: The footer reads 57 BPM and not 120 BPM. Also note which mode lamp is lit on the Launchpad top row -- a restored session comes up wherever you left it.',
  [],
  # ⚠️ ONLY ON THE DEVICE. 57 comes from knobs.txt, which mother reads at boot
  # and which no Mac has -- on a Mac this legitimately reads 120 and the
  # predicate would be asserting the absence of hardware.
  {'targets': ('device',),
   'check': {'kind': 'oled', 'has': ['57'], 'has_not': ['120']}}),

 ('Get to mode 1',
  'PASS IF: The lit lamp moves to the first position. If it does not move then nothing below will work.',
  [],
  {'do': 'Press transport key 1 on the nanoKONTROL.',
   'need': ['The nanoKONTROL powered and connected.', 'The Launchpad connected and in Programmer Mode.']}),

 ('SP-404 pad 1',
  'PASS IF: The OLED shows sp-bank 1 and sp-pad 1 together. ⚠️ State which bank is selected out loud before every one of these -- the 404 lights only the bank it is on.',
  [],
  {'do': 'Select bank A on the SP-404 and press pad 1.',
   'need': ['The SP-404 powered and connected.']}),

 ('SP-404 pad 5',
  'PASS IF: sp-pad reads 5 on the OLED. Anything else is the failure.',
  [],
  # ⛔ THE PAD THAT CATCHES `47 + n`. Under the old formula pad 5 reads 13, and
  # 13 is a plausible-looking number on an OLED -- which is how that bug lived
  # in this repo's own docs for months. A person reads two digits; this reads
  # the bus.
  {'do': 'Press pad 5 on bank A of the SP-404.',
   'need': ['The SP-404 powered and connected.', 'Bank A selected. Say it out loud.'],
   'check': {'kind': 'bus', 'bus': 'DISP', 'has': ['sp-pad 5']}}),

 ('All sixteen pads',
  'PASS IF: sp-pad counts 1 2 3 up to 16 in step with your finger while sp-bank stays at 1 throughout. A run that counts 1 2 3 4 and then jumps is the failure.',
  [],
  {'do': 'Press pads 1 through 16 in order on bank A.',
   'need': ['The SP-404 powered and connected.']}),

 ('Bank B',
  'PASS IF: sp-pad still reads 1 but sp-bank changes from 1 to 2 as you switch banks.',
  [],
  {'do': 'Select bank B on the SP-404 and press pad 1.',
   'need': ['The SP-404 powered and connected.', 'Bank B selected. Say it out loud.'],
   'check': {'kind': 'bus', 'bus': 'DISP', 'has': ['sp-pad 1', 'sp-bank 2']}}),

 ('A release is not a press',
  'PASS IF: Both rows update on the press and neither updates again on the release. Two updates per hit is the failure.',
  [],
  # ⛔ EXACTLY ONE sp-pad ROW FOR ONE HIT. Two means the velocity test on the
  # disp side has gone and every pad is reporting itself twice -- which on a
  # screen that redraws looks like nothing at all.
  {'do': 'Press and hold any pad on the SP-404 then let go.',
   'need': ['The SP-404 powered and connected.'],
   'watch': 'The sp-pad and sp-bank rows update once on the press and not again when you let go -- exactly one sp-pad row per hit.',
   'check': {'kind': 'bus-count', 'bus': 'DISP', 'match': 'sp-pad', 'n': 1}}),

 ('Fader 1 in mode 1',
  'PASS IF: The Volca tone changes as you move it. ⚠️ The Volca is by ear. It transmits nothing so there is never a readback.',
  [],
  {'do': 'In mode 1 move fader 1 on the nanoKONTROL.',
   'need': ['The nanoKONTROL powered and connected.', 'The Volca audible. It transmits nothing so there is never a readback.']}),

 ('Fader 1 in mode 4',
  'PASS IF: The Volca does not change. Silence is the pass. The OLED still shows the fader moving and that is correct.',
  [],
  {'do': 'Press transport key 4 then move fader 1.',
   'need': ['The nanoKONTROL powered and connected.', 'The Volca audible. It transmits nothing so there is never a readback.']}),

 ('Fader 1 back in mode 1',
  'PASS IF: The Volca responds again. If it stays silent check the lit lamp -- the mode did not change back.',
  [],
  {'do': 'Press transport key 1 then move fader 1 again.',
   'need': ['The nanoKONTROL powered and connected.', 'The Volca audible. It transmits nothing so there is never a readback.']}),

 ('Tempo from knob 1',
  'PASS IF: The footer BPM follows the knob over roughly 10 to 500 BPM. ⛔ But not until the knob passes through the restored value. Turning it does nothing until it crosses. Then it takes over and tracks.',
  [],
  {'do': 'Turn Organelle knob 1. It does nothing until it crosses the restored value.',
   'need': ['The Organelle powered and in reach.']}),

 ('Transport from the aux button',
  'PASS IF: The aux LED changes state on each press and the footer agrees.',
  [],
  {'do': 'Press the Organelle aux button twice.',
   'need': ['The Organelle powered and in reach.']}),

 ('Panic is unbound',
  'PASS IF: There is nothing to do here. Nothing on the device can raise panic and nothing is meant to. Read this and move on.',
  []),

 # ⛔ HOT-SWAP FOR BOTH OUTPUT DEVICES, AND THE TWO ARE NOT ALIKE. The SP-404 is
 # `active` -- it answers a device inquiry, so it has a last-heard clock and can
 # be declared lost. The Volca is `none`: it transmits nothing at all, can never
 # be polled, and its recovery is PARASITIC on a detectable device being missing
 # in the same moment. Step 7 below is what that costs.
 ('Hot-swap -- SP-404 unplugged',
  'PASS IF: A bordered alert on the OLED reads warn and then m_404.',
  [],
  # ⚠️ wait 12 IS LOAD-BEARING -- the warn is three missed ticks behind the
  # unplug, up to 8 s, and the runner's default drain is 0.4 s.
  {'do': 'Press enter first, then unplug the SP-404 and leave it out. Watch the OLED.',
   'need': ['The SP-404 powered and connected.'],
   'wait': 20,
   'check': {'kind': 'bus', 'bus': 'ERR', 'has': ['warn m_404']}}),
 ('Hot-swap -- SP-404 absent at load',
  'PASS IF: The OLED shows an sp-pad row.',
  [],
  # ⚠️ A PAD IS THE ORACLE AND NOT THE ABSENCE OF A WARN. The 404's detection is
  # proven by its silence at boot -- it can only stay quiet by matching byte 65 on
  # port 3 -- but silence cannot tell a working subscription from a dead one. A
  # pad under a finger can.
  {'do': 'Plug it in, wait 60 seconds, then press pad 1.',
   'reload': True,
   'need': ['The SP-404 still unplugged from the last step.',
            'Bank A selected. Say it out loud.']}),

 # ⛔ THE ORACLE IS THE FADER CHANGING THE SOUND \, NEVER THE VOLCA MAKING ONE.
 # Both of these steps used to read "PASS IF the Volca sounds -- BY EAR" \, which
 # is satisfied by a Volca with no MIDI cable in it at all: it is a synth with its
 # own keyboard and it sounds whenever it is powered. Measured on the rig
 # 2026-08-10 -- the interface was enumerated and completely unsubscribed for two
 # minutes and the keys still played. ref/device/volca.md said so before the step
 # was written: its only mapping is a CC that needs the device ALREADY SOUNDING.
 # ⚠️ THE TEXT CAME VERBATIM FROM THE PLAN and was checked against the punctuation
 # rules rather than against what this device can demonstrate.
 ('Hot-swap -- Volca unplugged',
  'PASS IF: Holding a Volca key and sweeping slider 1 changes the sound -- by ear. Sweep it up. Slider 1 is velocity and left at the bottom it silences the Volca.',
  [],
  # ⛔ THE NANOKONTROL COMES OUT TOO AND IT HAS TO. The Volca registers `none`, so
  # pulling it alone loses nothing, forks nothing and recovers nothing -- there is
  # no clock to run out on a device that never speaks. Its recovery rides a
  # DETECTABLE device being missing at the same moment: the trailing fork fires on
  # the transition back to nothing-lost, which is the best-informed instant
  # available because a device answering its inquiry is the signal that
  # enumeration has FINISHED. A step that unplugged only the Volca would fail for
  # a reason that has nothing to do with what it tests. Item 275, and it stranded
  # the Volca on the bench exactly this way.
  # ⚠️ AND IT IS BY EAR AND ALWAYS WILL BE. The Volca transmits nothing, so there
  # is no readback and no predicate is possible -- see ref/device/volca.md.
  {'do': 'Unplug the Volca interface and the nanoKONTROL together, count to fifteen so the loss is recorded, then plug both back in and sweep slider 1 while holding a Volca key.',
   'need': ['The Volca sounding and its USB interface connected.',
            'The nanoKONTROL powered and connected.',
            'Mode 1. Fader 1 is the only control bound to the Volca.']}),
 ('Hot-swap -- Volca absent at load',
  'PASS IF: Holding a Volca key and sweeping slider 1 changes the sound -- by ear. Sweep it up -- slider 1 is velocity.',
  [],
  # ⛔ THE NANOKONTROL COMES OUT HERE TOO, AND THIS STEP USED TO CLAIM OTHERWISE.
  # It read "THIS ONE NEEDS NO SECOND DEVICE" and reasoned that the recovery
  # counter would already be running for the pollable layers that are absent --
  # which is only true if one IS absent. Leave the Launchpad, nano and 404 all
  # plugged in and nothing is ever lost: u_present's spigot stays shut, the
  # counter never starts, and the eight attempts the step is waiting for are never
  # scheduled at all. u_init's boot fork ran before the cable went in.
  #
  # ⛔ MEASURED, 2026-08-10, item 285: the interface was plugged into a clean
  # session and sat ENUMERATED AND COMPLETELY UNSUBSCRIBED for two minutes with an
  # empty error log. The step as written would have failed on correct code, which
  # is the exact defect the plan flagged for the step above it.
  #
  # ⚠️ SO THIS IS THE SAME SHAPE AS THE TRANSITION STEP, and it has to be: a none
  # device cannot be recovered on its own in EITHER direction, and absent-at-load
  # is the likelier one in a room -- you power the rig up and then plug the Volca
  # in. See ref/device/volca.md.
  {'do': 'Plug both back in, wait 60 seconds, then hold a Volca key and sweep slider 1.',
   'reload': True,
   'need': ['The Volca interface and the nanoKONTROL both still unplugged from the last step.',
            'Mode 1. Slider 1 is the only control bound to the Volca.']}),
]
