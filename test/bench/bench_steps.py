"""Step tables for the seven benches -- the DATA half of bench-gen.py.

Each step is (title, pass_if, [(message, bus), ...]) and optionally a fourth
element, a dict -- see norm() below.

⛔ WHAT A STEP CLAIMS IS FIXED. HOW IT READS IS NOT. Every one of these was
transcribed out of a hand-authored .pd by test/bench/bench-extract.py, and the
benches behind them are verified on the Organelle -- so a change here may never
alter what a step ASSERTS. Wording is a different question, and it was rewritten
in full on 2026-08-10: sentence case, terminal full stops, run-ons split, no
claim added or dropped. test/bench/bench-verify.py re-extracts from the
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
 ('Baseline -- nothing is sent',
  'PASS IF: Two bars with a small gate mark under each. A BPM at the bottom. Phase 5 hands the footer over from v0.3-ready to the tempo about four seconds in.',
  []),
 ('A parameter with a unit -- sending chop-size 43 %',
  'PASS IF: chop-size on the top line and a big 43 % under it. The bars shrink to a thin strip. About 1.2 s later the meters come back on their own.',
  [('chop-size 43 %', 'disp')]),
 ('A parameter with no unit -- sending grain 12',
  'PASS IF: grain and then a big 12 with NO PERCENT SIGN left over from the last step. This is the one that matters most.',
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
 ('A modal -- sending modal recording',
  'PASS IF: recording in mid-size text with the bars as a thin strip. Unlike a parameter it STAYS and does not fade.',
  [('modal recording', 'disp')]),
 ('A parameter while a modal is up -- sending chop-size 43 %',
  'PASS IF: NOTHING CHANGES. Still recording. chop-size never appears because the modal outranks it.',
  [('modal recording', 'disp'), ('chop-size 43 %', 'disp')]),
 ('A warning over the modal -- sending warn u_root test-warn',
  'PASS IF: A bordered box reads warn then u_root then test-warn. About 2 s later it vanishes and RECORDING IS BACK underneath.',
  [('modal recording', 'disp'), ('warn u_root test-warn', 'err')]),
 ('Mode to perform -- nothing is sent to the screen',
  'PASS IF: NOTHING CHANGES. Still recording. Mode is never drawn. This only sets up the next two steps.',
  [('modal recording', 'disp'), ('perform', 'mode')]),
 ('A warning while in perform -- sending warn u_root hidden-warn',
  'PASS IF: NOTHING CHANGES. No alert box at all. Still recording. Perform mode suppresses warnings.',
  [('modal recording', 'disp'), ('warn u_root hidden-warn', 'err')]),
 ('A failure while in perform -- sending fail u_root shown-fail',
  'PASS IF: An alert DOES appear reading fail then u_root then shown-fail. Failures are never suppressed. Recording returns after about 4 s.',
  [('modal recording', 'disp'), ('fail u_root shown-fail', 'err')]),
 ('Mode back to compose -- nothing is sent to the screen',
  'PASS IF: NOTHING CHANGES. Still recording.',
  [('modal recording', 'disp'), ('compose', 'mode')]),
 ('A warning now we are back in compose -- sending warn u_root back-again',
  'PASS IF: The alert DOES appear this time reading warn then u_root then back-again. The filter has released.',
  [('modal recording', 'disp'), ('warn u_root back-again', 'err')]),
 ('Clearing the modal -- sending modal-off',
  'PASS IF: recording disappears. You are back to the two meters and the BPM footer.',
  [('modal-off', 'disp')]),
 ('The safety timeout -- sending modal stuck and then DELIBERATELY never clearing it',
  'PASS IF: stuck appears now. With NO further input it clears itself after 30 s. The next step is 35 s away.',
  [('modal stuck', 'disp')]),
 ('The 30 second safety timeout -- the deferred half of step 13',
  'PASS IF: The screen returned to the meters on its own during that 35 s wait. That was the safety timeout.',
  []),
]

STEPS_NANOKONTROL = [
 ('Baseline -- nothing is sent',
  'PASS IF: Two bars with a small gate mark under each. A BPM at the bottom. Phase 5 hands the footer over from v0.3-ready to the tempo about four seconds in.',
  []),
 ('One mover -- chop-size 43 %',
  'PASS IF: chop-size small on the top line and a BIG 43 % under it. This is the Phase 3 layout and it must be unchanged.',
  [('chop-size 43 %', 'disp')]),
 ('Two movers -- chop-size and grain together',
  'PASS IF: TWO stacked pairs -- chop-size over 43 % on top and grain over 12 below. FIRST TOUCHED on top. The values are mid-sized.',
  [('chop-size 43 %', 'disp'), ('grain 12', 'disp')]),
 ('Five movers',
  'PASS IF: FIVE small lines in the order they were first touched: chop-size then grain then slider-1 then knob-3 then btn-t-2.',
  [('chop-size 43 %', 'disp'), ('grain 12', 'disp'), ('slider-1 64', 'disp'), ('knob-3 100', 'disp'), ('btn-t-2 1', 'disp')]),
 ('Seven movers -- two more than fit',
  'PASS IF: Still exactly FIVE lines -- a1 a2 a3 a4 a5. a6 and a7 are REFUSED rather than pushing the rows around. Nothing shifts.',
  [('a1 1', 'disp'), ('a2 2', 'disp'), ('a3 3', 'disp'), ('a4 4', 'disp'), ('a5 5', 'disp'), ('a6 6', 'disp'), ('a7 7', 'disp')]),
 ('Ageing -- only a1 is kept alive from here',
  'PASS IF: The other four fade out within about 1.3 s and a1 alone is left. It grows BACK to the big 24px layout.',
  [('a1 1', 'disp')]),
 ('A modal over parameters -- modal recording',
  'PASS IF: recording at mid size. NO parameters at all. The modal outranks them.',
  [('modal recording', 'disp'), ('chop-size 43 %', 'disp')]),
 ('A warning over the modal',
  'PASS IF: A bordered alert reads warn then u_root then bench-warn. About 2 s later it vanishes and RECORDING IS STILL THERE underneath.',
  [('modal recording', 'disp'), ('warn u_root bench-warn', 'err')]),
 ('Perform mode -- nothing is drawn',
  'PASS IF: NOTHING CHANGES. Still recording. This only sets up the next two steps.',
  [('modal recording', 'disp'), ('perform', 'mode')]),
 ('A warning while in perform',
  'PASS IF: NOTHING CHANGES. No alert at all. Perform suppresses warnings.',
  [('modal recording', 'disp'), ('warn u_root hidden-warn', 'err')]),
 ('A failure while in perform',
  'PASS IF: An alert DOES appear because failures are never suppressed. Recording returns after about 4 s.',
  [('modal recording', 'disp'), ('fail u_root shown-fail', 'err')]),
 ('Back to compose',
  'PASS IF: NOTHING CHANGES. Still recording.',
  [('modal recording', 'disp'), ('compose', 'mode')]),
 ('A warning now we are in compose',
  'PASS IF: The alert DOES appear this time. The filter has released.',
  [('modal recording', 'disp'), ('warn u_root back-again', 'err')]),
 ('Clearing the modal',
  'PASS IF: recording disappears. You are back to the two meters and the BPM footer.',
  [('modal-off', 'disp')]),
 ('The nano -- sweep every slider and knob now',
  "PASS IF: Each control names ITSELF -- slider-1 to slider-9 then knob-1 to knob-9. None reports another's name. Watch slider 9 and then knob 1 especially: CC 9 and CC 11 are where an off-by-one shows.",
  [],
  {'do': 'Sweep every slider and every knob on the nanoKONTROL.',
   'need': ['The nanoKONTROL powered and connected.']}),
 ('The nano -- two faders at once then three then all nine',
  'PASS IF: Two stay readable as stacked pairs. Three to five become small lines. Nine shows the FIVE YOU TOUCHED FIRST with the rest refused. Rows must not reshuffle while you move things.',
  [],
  {'do': 'Move two faders at once, then three, then all nine.',
   'need': ['The nanoKONTROL powered and connected.']}),
 ('The nano -- press every button then all six transport keys',
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
 ('Unplug the nanoKONTROL and leave it out',
  'PASS IF: The OLED shows a warn for m_nano within 10 seconds.',
  [],
  # ⚠️ wait 12 IS LOAD-BEARING -- the warn is three missed ticks behind the
  # unplug, up to 8 s, and the runner's default drain is 0.4 s.
  {'do': 'Unplug the nanoKONTROL and leave it out, then press enter straight away -- the runner starts listening from there.',
   'need': ['The nanoKONTROL powered and connected.'],
   'wait': 12,
   'check': {'kind': 'bus', 'bus': 'ERR', 'has': ['warn m_nano']}}),
 ('Absent at load -- reload with it unplugged then plug it in',
  'PASS IF: Slider 1 moves a value on the OLED.',
  [],
  # ⚠️ 60 SECONDS AND NOT 10 -- the nano needed two of the eight attempts on the
  # bench because the device was still enumerating when the first landed (item
  # 277). ⛔ AND THE SLIDER IS THE ORACLE, not the absence of a warn: the nano is
  # PASSIVE to look at, so the only proof the subscription came back is traffic
  # arriving through it.
  {'do': 'Plug it in, wait 60 seconds, then move slider 1.',
   'need': ['The patch freshly loaded with the nanoKONTROL UNPLUGGED. Reload first, then resume this bench with --from 19.']}),
]

STEPS_TEMPO = [
 ('Baseline -- re-asserting 120 BPM and stopped',
  'PASS IF: Two bars with a small gate mark under each and 120-bpm in the footer. The aux button is lit DARK BLUE. This step exists so the run repeats without reopening the patch.',
  [('120', 'tempo'), ('bang', 'stop')]),
 ('Counting -- zeroing the beat counters for 10 s at 120 BPM',
  'PASS IF: NOTHING VISIBLE CHANGES. The transport is still stopped and the clock is running anyway. That is exactly what is being counted.',
  [('bang', '\\$0-zero')]),
 ('Read the counts -- the clock ran for 10 s while STOPPED',
  'PASS IF: M-BEATS reads 20 or 21 beats. C1-BEATS reads the same number. C2-BEATS reads 30 or 31 in the same window. A zero anywhere means the clock does not run until the transport does. On the Mac it can also mean DSP is off which looks exactly the same.',
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
  "PASS IF: The aux button turns GREEN and the 404 starts its pattern. WATCH EXT ON THE 404'S PATTERN SELECT SCREEN. The number beside a pad is that SAMPLE's BPM and never moves.",
  [('bang', 'start')]),
 ('Tempo through the map -- og-knob-1 at 0 -- PICKUP HOLDS IT',
  "PASS IF: ⛔ THIS ONE DIFFERS BY WHETHER A SAVE HAS EVER HAPPENED AND THE DIFFERENCE IS PICKUP WORKING. With a saved knobs.txt -- the device after any Storage Save -- the footer does NOT move. Mother restored knob 1 at boot and 0 is below that stored value so the knob is HELD until it crosses back. With no knobs.txt -- always on the Mac and on the device after tools/deploy.sh --clean -- u_map reads that the file is absent and holds nothing. So this lands and the footer reads 10-bpm with the 404's EXT sliding down.",
  [('og-knob-1 0', 'param')]),
 ('Tempo through the map -- og-knob-1 at 1 -- THE CROSSING',
  "PASS IF: The footer reads 500-bpm and the 404's EXT slides up. With a saved knobs.txt this is the moment the knob crosses the restored value and TAKES OVER -- held one step ago and live now. A slide rather than a snap IS the inference working. It snaps only to a tempo it has already learned.",
  [('og-knob-1 1', 'param')]),
 ('Tempo through the map -- back to 0 -- LIVE ON BOTH MACHINES',
  'PASS IF: The footer reads 10-bpm on EITHER machine. Pickup has handed over so the knob tracks normally from here. If this one is held too then the release never happened and the knob is stuck.',
  [('og-knob-1 0', 'param')]),
 ('Out of range -- 5000 sent TWICE',
  'PASS IF: The footer reads 600-bpm and EXACTLY ONE alert appears -- a bordered box naming u_tempo. The second 5000 must be silent because the VALUE did not change.',
  [('5000', 'tempo'), ('5000', 'tempo')],
  # ⛔ EXACTLY ONE, and that is the whole step. The second 5000 must be silent
  # because the VALUE did not change -- "one or more alerts" is satisfied by two
  # and would pass the bug. A person counting bordered boxes on an OLED that
  # redraws is exactly the oracle a machine should replace.
  {'check': {'kind': 'bus-count', 'bus': 'ERR', 'match': 'u_tempo', 'n': 1}}),
 ('Out of range the other way -- 0',
  'PASS IF: The footer reads 5-bpm and a SECOND alert appears. The verdict did not change but the value did. This is the case that was broken once.',
  [('0', 'tempo')]),
 ('Back to 120',
  'PASS IF: The footer reads 120-bpm and NO alert appears at all.',
  [('120', 'tempo')]),
 ('Stop -- and the clock must NOT stop with it',
  'PASS IF: The aux button goes DARK BLUE and the 404 stops. But its display MUST STILL SAY EXT. If it falls back to BPM then the clock stopped with the transport and that is the bug this step exists for.',
  [('bang', '\\$0-zero'), ('bang', 'stop')]),
 ('Read the counts while stopped',
  'PASS IF: M-BEATS reads 20 or 21 again. Stop the pulse stream and the 404 stretches every sample to a stale tempo. This is the least obvious requirement in the phase.',
  [('bang', '\\$0-read')],
  # ⛔ A ZERO HERE IS THE BUG THE STEP EXISTS FOR: the transport pauses the
  # subscribers, it does not clear the timer, and a clock that stopped with the
  # transport leaves the 404 stretching every sample to a stale tempo.
  {'check': {'kind': 'print', 'name': 'M-BEATS', 'min': 19, 'max': 22}}),
 ('Panic',
  'PASS IF: The aux button turns RED and the footer says panic. The clock is STILL running underneath.',
  [('bang', 'panic')]),
 ('By hand -- press the aux button twice',
  'PASS IF: ON THE DEVICE use the real button. ON THE MAC use aux-tap and NOT the aux toggle. Aux is momentary 1 then 0 and only the 1 is a press. A toggle needs two clicks per press and the uncheck is meant to do nothing. First press GREEN and the 404 starts. Second press DARK BLUE and it stops. If nothing happens at all then mother is eating the press.',
  [],
  {'do': 'Press the aux button twice. ON THE MAC use aux-tap and NOT the aux toggle.',
   'need': ['The Organelle powered and in reach.']}),
 ('By hand -- sweep KNOB 1 all the way and back',
  'PASS IF: The row reads bpm and a NUMBER. Never og-knob-1 and never a 0-to-1 decimal. While the knob is still held it reads bpm 57 (120) or similar: the latched tempo first and the knob position in brackets. Once it crosses it reads bpm alone and tracks between 10 and 500 BPM. The 404 follows the sweep. ⚠️ A FULL SWEEP ALWAYS CROSSES so pickup can never make this step fail. That is why it is a sweep and not a nudge.',
  [],
  {'do': 'Sweep Organelle knob 1 all the way and back. A FULL sweep always crosses.',
   'need': ['The Organelle powered and in reach.']}),
]

STEPS_LAUNCHPAD = [
 ('Baseline -- 120 BPM -- stopped -- compose mode-1',
  'PASS IF: The top row shows ONE bright green lamp at the far left and five dim ones beside it. The BOTTOM row of pads has a single white pad. DIM MEANS FAINT AND NOT OFF: the five idle lamps are colour 1 which is a near-black grey and the current one is colour 21 instead. THE WHITE PAD IS ALREADY WALKING and that is correct. c_clock free-runs and the transport gates what PLAYS rather than what counts. A frozen pad here is the fault and a moving one is not. Everything else on the surface is dark.',
  [('120', 'tempo'), ('bang', 'stop'), ('compose mode-1', 'mode')]),
 ('Mode -- selecting the fourth mode',
  'PASS IF: The bright lamp MOVES to the fourth position and the other five go dim. Nothing else on the grid changes.',
  [('perform mode-4', 'mode')]),
 ('Mode -- the second lamp',
  'PASS IF: The bright lamp lands on the SECOND position. Between this step and the next four the bus drives all six lamps in turn. Until now only two of the six were ever exercised without hands.',
  [('compose mode-2', 'mode')]),
 ('Mode -- the fifth lamp',
  'PASS IF: The bright lamp lands on the FIFTH position and the other five go dim.',
  [('perform mode-5', 'mode')]),
 ('Mode -- the sixth and last lamp',
  'PASS IF: The bright lamp lands on the sixth and last position. ONE MESSAGE PER STEP FOR ANYTHING VISUAL: two sent back to back both land inside the same frame and only the second is ever drawn. That was found by running this bench and watching the painted frames rather than the surface.',
  [('perform mode-6', 'mode')]),
 ('The grid selector must not reach the OLED -- sending grid vocabulary g_grid ignores',
  'PASS IF: NOTHING HAPPENS ON EITHER SURFACE. g_oled treats every selector it does not recognise as a parameter to draw. Without grid in its route this would appear on the OLED as a nonsense parameter row called grid. That one route argument is the whole reason a third display surface was cheap.',
  [('grid no-such-thing', 'disp')]),
 ('A modal -- the whole surface claimed',
  'PASS IF: EVERY pad and every lamp on the top row turns blue. The mode lamps are covered too and that is the point of a modal. THE OLED MUST NOT CHANGE.',
  [('grid modal 45', 'disp')]),
 ('A mode change underneath a modal -- nothing should be visible',
  'PASS IF: NOTHING HAPPENS. The surface stays blue. The mode really does change underneath and you will see it two steps from now. THIS STEP RE-SENDS THE MODAL BEFORE THE MODE CHANGE and so does the next one. That is not decoration: the modal safety TTL is thirty seconds of WALL CLOCK and under manual stepping the gap between two steps is however long you take. Without the re-send this chain silently expires mid-test and the surface is back to mode lamps before the step that needs it runs. Re-asserting a live modal is what a caller would do anyway and it restarts the timer.',
  [('grid modal 45', 'disp'), ('perform mode-3', 'mode')]),
 ('An alert on top of a modal -- two layers deep',
  'PASS IF: The surface turns RED for about two seconds and then goes back to BLUE -- NOT to the mode lamps. The modal is still up underneath and the alert only borrowed the surface. This is the only step that tests the cascade more than one layer deep. The modal is re-sent first for the same reason as the last step.',
  [('grid modal 45', 'disp'), ('fail u_bench stacked', 'err')]),
 ('Modal off',
  'PASS IF: The grid returns to mode lamps and the beat row. The bright lamp is now the THIRD one -- the change made while the modal covered it. THIS STEP RE-SENDS THE MODAL BEFORE CLEARING IT and that is not pointless. The 30 second safety TTL is wall clock and it has expired underneath this step before -- on the first device run -- because a report was being typed between the last step and this one. When that happens the surface has ALREADY returned home by itself and modal-off clears nothing. The step passes while proving nothing at all. Raising it again first means there is always a modal here to clear. You will not SEE the re-raise because both messages land in one frame and only the last is drawn. That is expected and it is why the previous steps carry the visible part of this test.',
  [('grid modal 45', 'disp'), ('grid modal-off', 'disp')]),
 ('An alert -- a fail -- which outranks everything',
  'PASS IF: The whole surface turns RED and then goes back to the mode lamps BY ITSELF after about two seconds. A grid that stays red is the bug this step exists for.',
  [('fail u_bench boom', 'err')]),
 ('An alert -- a warn -- which the grid must ignore but the OLED must show',
  'PASS IF: NOTHING HAPPENS ON THE GRID and the OLED DOES show the warning. Only a fail is worth the whole surface. THE compose SENT FIRST IS LOAD-BEARING and not a mode test. u_err gates warns off the SCREEN in perform mode -- compose sets its verbose spigot to 1 and perform sets it to 0 -- and this bench put itself in perform back at step 8 already. Without the compose the OLED stays blank for a legitimate reason and the step cannot tell that apart from the grid filter working. Fails ignore the spigot which is why the previous step needed no such thing.',
  [('compose mode-3', 'mode'), ('warn u_bench quiet', 'err')]),
 ('The 30 second modal safety TTL -- this step needs you to wait',
  'PASS IF: The surface turns green and then clears ITSELF about thirty seconds later with nothing sent to it. DO NOT PRESS GO -- sit and watch it. A modal is sticky by design so this timer is the only thing between a stuck modal and a grid that never comes back. It has never once been observed.',
  [('grid modal 21', 'disp')]),
 ('Transport -- start -- and the beat counter starts with it',
  'PASS IF: The white pad WALKS along the bottom row twice a second and the aux LED goes green. ON THE MAC THE AUX LED IS NOT A BUTTON: it is the numeric readout labelled aux-LED on the bottom row of the dev panel next to the clock beat bng and the tempo-bus box -- with a symbol box beside it spelling the colour. Only the Organelle has a lamp to look at. On the Mac with DSP off the pad will not move -- tick enable-DSP first. A BEATS line prints about ten seconds from now.',
  [('bang', 'start'), ('bang', '\\$0-zero')],
  # The eyes still judge the walking pad and the aux LED. What the machine can
  # judge is the number underneath them, which is the same evidence and is not
  # subject to anyone counting flashes.
  # ⚠️ THE EXPECTED COUNT IS STATED IN `watch` BECAUSE THE PASS IF DOES NOT SAY
  # IT -- it only promises a BEATS line "about ten seconds from now". A predicate
  # asserting a number the prose never mentions is a disagreement waiting to
  # happen, and the person reading the terminal deserves to know what it wants.
  {'watch': 'The white pad WALKS along the bottom row twice a second and the aux LED goes green, then a BEATS line of about 20 prints about ten seconds from now.',
   'check': {'kind': 'print', 'name': 'BEATS', 'min': 19, 'max': 22}}),
 ('The beat row wrapping -- WATCH ONLY -- this step sends nothing on purpose',
  'PASS IF: The white pad reaches the EIGHTH pad and the next step is back to the FIRST -- with no gap and no stray light anywhere else. NO ACTION IS SENT AND THAT IS DELIBERATE rather than an omission. The wrap happens on the clock schedule and cannot be provoked on demand. The only way to test it is to watch one go by. It gets its own step because folding it into the transport step is how it goes unlooked-at. Nothing here disturbs the ten second BEATS window still running underneath. THE BEAT NUMBER IS ONE-BASED: built against a zero-based assumption beat 8 landed on a right-column ring button and blanked the row once a bar -- and seven beats out of eight looked perfect.',
  []),
 ('Tempo -- 240 BPM -- so the beat row should double',
  'PASS IF: The white pad moves twice as fast. The BEATS line just printed covers ten seconds at 120 and should read about 20 beats. The next one covers ten seconds at 240 and should read about 40 beats. EXPECT A VISIBLE SWING HERE AND DO NOT FAIL THE STEP FOR IT. g_grid repaints on a metro 100 so the row can only move on a 100 ms boundary. At 120 BPM a beat is 500 ms which divides exactly and the walk is dead even. At 240 a beat is 250 ms which does not. So beats land alternately at 200 and 300 ms and the row swings by 50 either way. The CLOCK is not swinging and the BEATS count is unaffected: this is the display quantising. It is the price of the 10 Hz repaint that keeps MIDI writes inside the CPU budget.',
  [('bang', '\\$0-read'), ('240', 'tempo'), ('bang', '\\$0-zero')]),
 ('Back to 120 and stopped',
  'PASS IF: The second BEATS line reads about 40 and then the beat row slows to two a second. THE CLOCK KEEPS RUNNING WHEN THE TRANSPORT STOPS so the pad must keep walking after the stop.',
  [('bang', '\\$0-read'), ('120', 'tempo'), ('bang', 'stop')]),
 ('The Launchpad -- press pads and RELEASE them',
  'PASS IF: Every pad you press reports pad-NN on the OLED with its velocity. RELEASING it reports the same name with a velocity of 0 instead. Numbering runs from 11 at the bottom left to 88 at the top right. Pressure on a held pad reports NOTHING on the OLED. That is deliberate and it is not a fault.',
  [],
  {'do': 'Press pads on the Launchpad and RELEASE them.',
   'need': ['The Launchpad connected and in Programmer Mode.']}),
 ('The Launchpad ring -- and the row that must stay dark',
  'PASS IF: The ring buttons report lp-cc-NN. Check the two the documentation got wrong: the TOP LEFT CORNER is 90 and the bottom row runs from 101 to 108 in order. THEN LOOK AT CC 1 TO 8 -- AND NOTE THAT THIS EXPECTATION IS NOW THE OPPOSITE OF WHAT IT ONCE WAS. That row used to be outside the painted span and had to be DARK. It is INSIDE it now -- the span runs 1 to 108 -- so it must be lit like everything else and must go blue under a modal and red under an alert. THE REASON WAS NOT THAT ANYTHING WANTED THOSE EIGHT BUTTONS. LED state survives the Programmer Mode switch. An index outside the span keeps whatever Live Mode last drew there forever and no repaint can reach it. This bench is what caught that: the row was green from an old probe on one run and dark on the next -- with nothing in Cut It touching it either time. ONE BUTTON IS STILL OUTSIDE -- INDEX 0 -- SETUP -- and that one is measured rather than chosen. It takes no colour and it transmits nothing in Programmer Mode.',
  [],
  {'do': 'Press the Launchpad ring buttons, including the top left corner and the bottom row.',
   'need': ['The Launchpad connected and in Programmer Mode.']}),
 ('The nanoKONTROL -- the six transport keys',
  'PASS IF: Each of the six keys moves the bright lamp to its own position. This is the mode bus finally having a driver.',
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
 ('Unplug the Launchpad and leave it out',
  'PASS IF: The OLED shows a warn for m_launchpad within 10 seconds and the grid goes dark.',
  [],
  # ⚠️ THE PREDICATE READS err AND THE EYES READ THE GRID, and neither covers the
  # other. c_presence publishes the warn; g_grid going dark is m_launchpad
  # dropping ownership two boxes further on, and no bus carries "the grid stopped
  # painting".
  # ⚠️ wait 12 IS LOAD-BEARING. The warn is three missed ticks behind the unplug
  # -- up to 8 s at the shipped 2000 ms tick -- and the runner's default drain is
  # 0.4 s, which would miss it on entirely correct hardware.
  {'do': 'Unplug the Launchpad USB and leave it out, then press enter straight away -- the runner starts listening from there.',
   'need': ['The Launchpad connected and in Programmer Mode, with the grid lit.'],
   'wait': 12,
   'check': {'kind': 'bus', 'bus': 'ERR', 'has': ['warn m_launchpad']}}),
 ('Absent at load -- reload with it unplugged then plug it in',
  'PASS IF: The grid lights and the top row shows one green lamp.',
  [],
  # ⚠️ 60 SECONDS AND NOT 10. A replug is routinely missed by the FIRST re-wire
  # because the device is still enumerating -- the Launchpad used six of its eight
  # attempts on the bench, item 277 -- and the eight are spread over seventy
  # seconds. Anything under about 50 s fails intermittently on correct code.
  {'do': 'Plug the Launchpad in and wait up to 60 seconds without touching anything else.',
   'need': ['The patch freshly loaded with the Launchpad UNPLUGGED. Reload first, then resume this bench with --from 22.']}),
 ('Panic -- the surface goes back to the device',
  'PASS IF: The Launchpad visibly leaves Programmer Mode and its own display returns. BUTTON PRESSES STOP REACHING THE OLED. Watch both: the panic hands the surface back and drops ownership. THE VISIBLE HALF IS NEW AND THE STEP BEFORE THIS ONE IS WHY. This step used to say the device was already in Live Mode because the replug step had left it there. It is not any more. Presence brings a replugged Launchpad back INTO Programmer Mode with ownership restored -- so there is a live surface here for the panic to hand back. KNOWN AND DELIBERATE: it stays handed back until the patch is reloaded. EVERY REMAINING STEP IS DOWNSTREAM OF THIS ONE and nothing after it can check the grid. If you have any doubt about an earlier step go back and redo it before pressing GO here.',
  [('bang', 'panic')]),
 ('After the panic the grid must go silent -- sending it a mode change',
  'PASS IF: NOTHING HAPPENS. The Launchpad keeps showing its own display and g_grid paints nothing at all. Ownership dropped when the surface was handed back. The arbiter still runs and simply never reaches the wire.',
  [('compose mode-1', 'mode')]),
 ('Press a pad now -- after the panic',
  'PASS IF: NOTHING REACHES THE OLED. In a stock layout the notes are musical pitches rather than r*10+c and decoding them as coordinates would publish nonsense. Reload the patch to get the grid back.',
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
 ('Baseline -- the link is up and the mode is compose',
  'PASS IF: The bottom line of the phone reads ok rather than NO-LINK. Nothing else has to be true yet. This proves only that the heartbeat is flowing and the scene is bound. IF IT SAYS NO-LINK STOP HERE and check that PdParty is open on the same network. Every step below depends on it. compose is set because u_err shows warnings in compose and only failures in perform.',
  [('compose mode-1', 'mode')]),
 ('One parameter -- name value and unit',
  'PASS IF: The top line reads chop-size and the big number reads 43 on its own. The unit rides on the wire but the scene does not draw it. That is deliberate and not a fault.',
  [('chop-size 43 %', 'disp')],
  # ⚠️ THE MAC RUN IS A MIRROR AND ANSWERS A DIFFERENT QUESTION FROM THE DEVICE.
  # With u_net repointed at localhost the datagrams are readable here, so what
  # u_net FILTERS can be judged with no phone at all. What no Mac can judge is
  # what the PHONE then draws -- so the device run keeps its human verdict.
  {'targets': ('mac',),
   'check': {'kind': 'osc', 'addr': '/cutit/param', 'has': ['chop-size', '43']}}),
 ('A second parameter -- and the stale-unit trap underneath it',
  'PASS IF: The top line changes to grain and the number to 12 with it. THE POINT OF THIS STEP IS SOMETHING YOU CANNOT SEE: grain carries no unit and the step before it did. On the wire this has to arrive as grain 12 and a dash rather than grain 12 and a percent sign. The scene draws no units so a stale one would be invisible here. test/gate/phone-assert.sh is what actually proves it.',
  [('grain 12', 'disp')]),
 ('The status line -- a row that is not a parameter',
  'PASS IF: The third line reads 128-bpm and the parameter name and number ABOVE IT DO NOT CHANGE. status has its own OSC address and its own slot. Expect u_tempo to overwrite this with the real BPM at the next transport event. That is the footer being handed back and not a fault.',
  [('status 128-bpm', 'disp')]),
 ('An alert -- and it travels the whole error bus to get here',
  'PASS IF: The fourth line shows warn on the left and probe-warning on the right. This goes onto err rather than disp so u_err filtered it by mode and forwarded it. That makes this the proof that the error bus reaches the phone and not just the OLED.',
  [('warn u_bench probe-warning', 'err')]),
 ('The alert persists -- which is the entire reason it is state',
  'PASS IF: Several seconds later the fourth line STILL reads warn and probe-warning. An alert is an event and UDP cannot carry events so u_net holds the last one and repeats it on every heartbeat. On the OLED the same alert has long since timed out. THE TWO SURFACES DISAGREE ON PURPOSE and this step is where you see it.',
  []),
 ('A second alert replaces the first',
  'PASS IF: The fourth line changes to fail and probe-failure. A failure also draws on the OLED where the warning above may not have.',
  [('fail u_bench probe-failure', 'err')]),
 ('The meters must not appear -- the correct result is nothing',
  'PASS IF: NOTHING ON THE PHONE CHANGES AT ALL. in-l and in-r are the entire resting content of the disp bus once there is audio -- about twenty messages a second -- and u_net drops them on purpose. If a line here starts reading in-l then the reserved branch is broken and the whole rate budget has gone to a meter the phone does not draw.',
  [('in-l 42 dB', 'disp'), ('in-r 7 dB', 'disp')],
  # ⛔ THE has HALF IS THE WITNESS, not decoration. "in-l never appears" is
  # satisfied by a u_net that emitted nothing at all -- which is what a broken
  # one looks like -- so the heartbeat proves the link was live while the
  # meters were being dropped. The lint refuses this predicate without it.
  {'targets': ('mac',),
   'check': {'kind': 'all', 'of': [
       {'kind': 'osc', 'addr': '/cutit/hb', 'has': []},
       {'kind': 'osc', 'addr': '/cutit/param', 'has_not': ['in-l', 'in-r']}]}}),
 ('The grid vocabulary must not appear -- and the Launchpad WILL react',
  "PASS IF: Nothing on the phone changes. THE LAUNCHPAD GOING MODAL IS CORRECT. grid is g_grid's own vocabulary and this step proves only that u_net ignores it. The next step clears it.",
  [('grid modal 45', 'disp')]),
 ('Clearing the grid -- still nothing on the phone',
  'PASS IF: The Launchpad returns to its home layout and the phone does not move.',
  [('grid modal-off', 'disp')]),
 ('The aux LED -- still nothing on the phone',
  'PASS IF: The aux button goes green and the phone does not move. That is the third reserved selector proven inert in a row.',
  [('led running', 'disp')]),
 ('Sweep a nanoKONTROL fader as fast as you can',
  'PASS IF: The phone tracks the fader while it moves and then SETTLES ON THE VALUE YOU STOPPED AT. A phone left showing a number from the middle of the sweep is the trailing edge failing -- the one bug in this phase that hands can catch and that no headless run reproduces with real timing. Sweep two faders at once if you have the fingers. Both must settle correctly.',
  [],
  {'do': 'Sweep a nanoKONTROL fader as fast as you can, two at once if you have the fingers.',
   'need': ['The nanoKONTROL powered and connected.', 'PdParty open on the CutItRemote scene.']}),
 ('Close PdParty on the phone and count to ten',
  'PASS IF: NOTHING ON THE ORGANELLE CHANGES. No audio glitch and no error on the OLED. THE ORGANELLE NEVER WAITS. What has actually happened is that the phone answered with an ICMP port-unreachable and the socket was destroyed. u_net has been reconnecting every five seconds ever since with nothing to show for it.',
  [],
  {'do': 'Close PdParty on the phone and count to ten.',
   'need': ['PdParty open on the CutItRemote scene.']}),
 ('Reopen PdParty',
  'PASS IF: The phone starts updating again WITHIN ABOUT FIVE SECONDS and you touched nothing on the Organelle. THIS IS THE STEP THAT PROVES ITEM 114 ON REAL HARDWARE. A link that could not recover would be dead for the rest of the set and nothing on the instrument would say so. That is exactly what the first build did before Step 0 measured it.',
  [],
  {'do': 'Reopen PdParty on the phone. Touch NOTHING on the Organelle.',
   'need': ['PdParty open on the CutItRemote scene.']}),
]

STEPS_STATE = [
 ('Baseline -- the patch has just booted and nothing has been touched',
  'PASS IF: The Launchpad top row shows exactly ONE lit mode lamp. WHICH one is the test: a fresh install comes up on mode-1 and a restored one comes up wherever you left it. If the grid is dark then the Launchpad is not owned and nothing below can be read.',
  [],
  {'do': 'Look at the Launchpad top row. Press nothing.',
   'need': ['The Launchpad connected and in Programmer Mode.']}),
 ('Change the mode -- press transport key 4 on the nanoKONTROL',
  'PASS IF: The lit lamp moves to the fourth position. Nothing about STATE is visible yet and that is correct. u_state has it in memory and flushes within two seconds.',
  [],
  {'do': 'Press transport key 4 on the nanoKONTROL.',
   'need': ['The nanoKONTROL powered and connected.', 'The Launchpad connected and in Programmer Mode.']}),
 ('Confirm it reached the disk -- from the Mac run ./tools/fetch-state.sh --show',
  'PASS IF: cut-it-auto.txt reads mode perform mode-4. THE FILE IS THE ONLY EVIDENCE. Nothing on the instrument displays what has been saved and that is deliberate. If it still reads the old mode then the flush is not firing.',
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
 ('Commit -- on the Organelle press Storage then Save',
  'PASS IF: The screen shows Saving briefly and returns. Then cut-it-manual.txt has a NEW timestamp even though it is still empty -- no shipped contributor uses the manual policy yet. An UNCHANGED timestamp means saveState never arrived and the commit path is dead.',
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
 ('The one that matters -- power cycle the Organelle and wait for it to come back',
  'PASS IF: The same mode lamp is lit as before the power cycle. This is the only durability test that counts. A patch reload proves nothing about an SD card. DO THIS LAST IN A SESSION because it resets the wifi fault uptime clock and that fault needs about three hours to appear.',
  [],
  {'do': 'Power cycle the Organelle and wait for it to come back. DO THIS LAST IN A SESSION.',
   'need': ['The Organelle powered and in reach.', 'The Launchpad connected and in Programmer Mode.']}),
]


STEPS_MIDI = [
 ('Baseline -- read the OLED footer before touching anything',
  'PASS IF: The footer reads 57 BPM and NOT 120 BPM. This is a REAL TEST and not a formality. knobs.txt holds knob 1 at about 0.096 and mother pushes it at boot. 57 means the message went through the mapping TABLE and came out the tempo handler. 120 means u_tempo is sitting on its own default and the table never matched. Also note which mode lamp is lit on the Launchpad top row. A restored session comes up wherever you left it.',
  [],
  # ⚠️ ONLY ON THE DEVICE. 57 comes from knobs.txt, which mother reads at boot
  # and which no Mac has -- on a Mac this legitimately reads 120 and the
  # predicate would be asserting the absence of hardware.
  {'targets': ('device',),
   'check': {'kind': 'oled', 'has': ['57'], 'has_not': ['120']}}),

 ('Get to mode 1 -- press transport key 1 on the nanoKONTROL',
  'PASS IF: The lit lamp moves to the first position. Fader 1 is only bound in mode 1 so the later steps need this. If the lamp does not move then the nano is not reaching param and nothing below will work.',
  [],
  {'do': 'Press transport key 1 on the nanoKONTROL.',
   'need': ['The nanoKONTROL powered and connected.', 'The Launchpad connected and in Programmer Mode.']}),

 ('The 404 receive side -- select BANK A on the SP-404 and press pad 1',
  'PASS IF: The OLED shows sp-bank 1 and sp-pad 1 together. This is the map this project got WRONG once and pad 1 is note 48 on the wire. ⚠️ STATE WHICH BANK IS SELECTED OUT LOUD before every one of these: the 404 lights only the bank it is on and a receive test that does not state the bank cost half an hour once.',
  [],
  {'do': 'Select BANK A on the SP-404 and press pad 1.',
   'need': ['The SP-404 powered and connected.']}),

 ('The pad that breaks the old formula -- press pad 5 on bank A',
  'PASS IF: sp-pad reads 5 on the OLED. Pad 5 is note 44 and NOT note 52 as the old formula had it. Anything other than 5 means the pad table is wrong in exactly the direction this repo used to have it wrong.',
  [],
  # ⛔ THE PAD THAT CATCHES `47 + n`. Under the old formula pad 5 reads 13, and
  # 13 is a plausible-looking number on an OLED -- which is how that bug lived
  # in this repo's own docs for months. A person reads two digits; this reads
  # the bus.
  {'do': 'Press pad 5 on bank A of the SP-404.',
   'need': ['The SP-404 powered and connected.', 'BANK A selected. Say it out loud.'],
   'check': {'kind': 'bus', 'bus': 'DISP', 'has': ['sp-pad 5']}}),

 ('Walk the whole bank -- press pads 1 through 16 in order on bank A',
  'PASS IF: sp-pad counts 1 2 3 up to 16 in step with your finger while sp-bank stays at 1 throughout. The headless gate already asserts all sixteen notes. What this adds is that the DEVICE agrees with it. A run that goes 1 2 3 4 and then jumps is the old formula surviving somewhere.',
  [],
  {'do': 'Press pads 1 through 16 in order on bank A.',
   'need': ['The SP-404 powered and connected.']}),

 ('The bank is the channel -- select BANK B and press pad 1',
  'PASS IF: sp-pad still reads 1 but sp-bank CHANGES from 1 to 2 as you switch banks. There are two rows rather than one because a single row could not tell A1 from B1. It could not be one row carrying both either: g_oled formats a value with makefilename %g which refuses a symbol so sp-hit b1 is impossible.',
  [],
  {'do': 'Select BANK B on the SP-404 and press pad 1.',
   'need': ['The SP-404 powered and connected.', 'BANK B selected. Say it out loud.'],
   'check': {'kind': 'bus', 'bus': 'DISP', 'has': ['sp-pad 1', 'sp-bank 2']}}),

 ('A release is not a press -- press and hold any pad then let go',
  'PASS IF: Both rows update on the PRESS and NEITHER updates again on the release. The release is a real event and does reach param but it is not worth a display row. Two updates per hit means the velocity test on the disp side has gone.',
  [],
  # ⛔ EXACTLY ONE sp-pad ROW FOR ONE HIT. Two means the velocity test on the
  # disp side has gone and every pad is reporting itself twice -- which on a
  # screen that redraws looks like nothing at all.
  {'do': 'Press and hold any pad on the SP-404 then let go.',
   'need': ['The SP-404 powered and connected.'],
   'watch': 'The sp-pad and sp-bank rows update ONCE on the press and NOT again when you let go -- exactly one sp-pad row per hit.',
   'check': {'kind': 'bus-count', 'bus': 'DISP', 'match': 'sp-pad', 'n': 1}}),

 ('The map is mode-dependent -- in mode 1 move FADER 1 on the nanoKONTROL',
  'PASS IF: The Volca tone changes as you move it. Fader 1 is bound to Volca CC 41 in mode 1 and to NOTHING in the other five. THIS IS THE POINT OF THE WHOLE PHASE: a control means whatever the row for the current mode says it means. ⚠️ The Volca is BY EAR and always will be. It transmits nothing so there is never a readback.',
  [],
  {'do': 'In mode 1 move FADER 1 on the nanoKONTROL.',
   'need': ['The nanoKONTROL powered and connected.', 'The Volca audible. It transmits nothing so there is never a readback.']}),

 ('Now change mode and move the same fader -- transport key 4 then fader 1',
  'PASS IF: The Volca does NOT change. Nothing is broken. There is no row for fader 1 in mode 4 and an unmapped control is the normal state of most controls. SILENCE IS THE PASS. The OLED still shows the fader moving because m_nano publishes it either way.',
  [],
  {'do': 'Press transport key 4 then move fader 1.',
   'need': ['The nanoKONTROL powered and connected.', 'The Volca audible. It transmits nothing so there is never a readback.']}),

 ('And back -- transport key 1 then fader 1 again',
  'PASS IF: The Volca responds again. If it stays silent then the mode did not change back and the lit lamp will say so.',
  [],
  {'do': 'Press transport key 1 then move fader 1 again.',
   'need': ['The nanoKONTROL powered and connected.', 'The Volca audible. It transmits nothing so there is never a readback.']}),

 ('Tempo still comes from knob 1 -- turn Organelle knob 1',
  'PASS IF: The footer BPM follows the knob over roughly 10 to 500 BPM. ⛔ BUT NOT UNTIL THE KNOB PASSES THROUGH THE RESTORED VALUE. knobs.txt restored a position and the physical knob is wherever you left it. Turning it does NOTHING until it crosses. Then it takes over and tracks. That is parameter pickup and the jump it replaced was measured at 443 BPM. Knob 1 is a TABLE ROW now like everything else.',
  [],
  {'do': 'Turn Organelle knob 1. It does nothing until it crosses the restored value.',
   'need': ['The Organelle powered and in reach.']}),

 ('The transport still works -- press the Organelle aux button twice',
  'PASS IF: The aux LED changes state on each press and the footer agrees. The transport migrated into the table too so this is the proof that migrating it did not quietly drop it.',
  [],
  {'do': 'Press the Organelle aux button twice.',
   'need': ['The Organelle powered and in reach.']}),

 ('Panic is deliberately unbound -- nothing to press -- read this and move on',
  'PASS IF: You understand why there is nothing to do here. NOTHING ON THE DEVICE CAN RAISE PANIC. It was briefly bound to a nano button and that was withdrawn. Panic hands the Launchpad back to Live Mode BY DESIGN and the watchdog deliberately does not fight it back -- so an accidental brush of a bare button would kill the grid for the rest of the session with no console to explain it. m_404 now silences all ten banks when panic DOES arrive and the headless gate proves that. Choosing which control is worth that power is a v0.4 decision.',
  []),

 # ⛔ HOT-SWAP FOR BOTH OUTPUT DEVICES, AND THE TWO ARE NOT ALIKE. The SP-404 is
 # `active` -- it answers a device inquiry, so it has a last-heard clock and can
 # be declared lost. The Volca is `none`: it transmits nothing at all, can never
 # be polled, and its recovery is PARASITIC on a detectable device being missing
 # in the same moment. Step 7 below is what that costs.
 ('Unplug the SP-404 and leave it out',
  'PASS IF: The OLED shows a warn for m_404 within 10 seconds.',
  [],
  # ⚠️ wait 12 IS LOAD-BEARING -- the warn is three missed ticks behind the
  # unplug, up to 8 s, and the runner's default drain is 0.4 s.
  {'do': 'Unplug the SP-404 and leave it out, then press enter straight away -- the runner starts listening from there.',
   'need': ['The SP-404 powered and connected.'],
   'wait': 12,
   'check': {'kind': 'bus', 'bus': 'ERR', 'has': ['warn m_404']}}),
 ('Absent at load -- reload with the SP-404 unplugged then plug it in',
  'PASS IF: The OLED shows an sp-pad row.',
  [],
  # ⚠️ A PAD IS THE ORACLE AND NOT THE ABSENCE OF A WARN. The 404's detection is
  # proven by its silence at boot -- it can only stay quiet by matching byte 65 on
  # port 3 -- but silence cannot tell a working subscription from a dead one. A
  # pad under a finger can.
  {'do': 'Plug it in, wait 60 seconds, then press pad 1.',
   'need': ['The patch freshly loaded with the SP-404 UNPLUGGED. Reload first, then resume this bench with --from 15.',
            'BANK A selected. Say it out loud.']}),

 # ⛔ THE ORACLE IS THE FADER CHANGING THE SOUND \, NEVER THE VOLCA MAKING ONE.
 # Both of these steps used to read "PASS IF the Volca sounds -- BY EAR" \, which
 # is satisfied by a Volca with no MIDI cable in it at all: it is a synth with its
 # own keyboard and it sounds whenever it is powered. Measured on the rig
 # 2026-08-10 -- the interface was enumerated and completely unsubscribed for two
 # minutes and the keys still played. ref/device/volca.md said so before the step
 # was written: its only mapping is a CC that needs the device ALREADY SOUNDING.
 # ⚠️ THE TEXT CAME VERBATIM FROM THE PLAN and was checked against the punctuation
 # rules rather than against what this device can demonstrate.
 ('The Volca -- unplug it WITH the nanoKONTROL then plug both back in',
  'PASS IF: Holding a Volca key and sweeping slider 1 changes the sound -- BY EAR. Slider 1 is Volca CC 41 which is VELOCITY so sweep it UP. Left at the bottom it silences the device and that looks exactly like a dead link.',
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
  {'do': 'Unplug the Volca interface AND the nanoKONTROL together, count to fifteen so the loss is recorded, then plug both back in and sweep slider 1 while holding a Volca key.',
   'need': ['The Volca sounding and its USB interface connected.',
            'The nanoKONTROL powered and connected.',
            'Mode 1. Fader 1 is the only control bound to the Volca.']}),
 ('Absent at load -- reload with the Volca interface AND the nano out then plug both in',
  'PASS IF: Holding a Volca key and sweeping slider 1 changes the sound -- BY EAR. Sweep it UP because CC 41 is velocity.',
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
   'need': ['The patch freshly loaded with BOTH the Volca interface and the nanoKONTROL UNPLUGGED. Reload first, then resume this bench with --from 17.',
            'Mode 1. Slider 1 is the only control bound to the Volca.']}),
]
