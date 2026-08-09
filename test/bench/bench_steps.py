"""Step tables for the four benches -- the DATA half of bench-gen.py.

phase3/4/5 were transcribed out of the hand-authored .pd files by
test/bench/bench-extract.py and must not be reworded: those benches are verified on
the Organelle and the conversion to manual stepping is meant to change how a
step is DRIVEN, never what it claims. test/bench/bench-verify.py re-extracts from the
regenerated files and diffs against these tables.

Each step is (title, pass_if, [(message, bus), ...]) and optionally a fourth
element, a dict -- see norm() below.

ONE DELIBERATE TEXT CHANGE, and it is a bug fix rather than a reword. phase5's aux
step carried two escaped commas inside its PASS IF. `\\,` satisfies the .pd PARSER,
but a message box still treats the comma atom as a message separator -- measured
again here -- so at runtime that line printed as THREE fragments. Both are now
` -- `. This is the same defect that produced fourteen fragments on the first
Phase 6 run, in a bench family whose own README warns about it, which is why
bench-gen.py asserts against commas and semicolons rather than trusting review.
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
 ('baseline -- sending nothing',
  'PASS IF: two bars with a small gate mark under each and a BPM at the bottom -- Phase 5 hands the footer over from v0.2-ready to the tempo about four seconds in',
  []),
 ('PARAM WITH A UNIT -- sending chop-size 43 %',
  'PASS IF: chop-size on the top line and a big 43 % under it -- bars shrink to a thin strip -- then about 1.2s later the meters come back on their own',
  [('chop-size 43 %', 'disp')]),
 ('PARAM WITH NO UNIT -- sending grain 12',
  'PASS IF: grain then a big 12 and NO PERCENT SIGN left over from the last step -- this is the one that matters most',
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
 ('MODAL -- sending modal recording',
  'PASS IF: recording in mid-size text with the bars as a thin strip -- and unlike a param it STAYS and does not fade',
  [('modal recording', 'disp')]),
 ('PARAM WHILE A MODAL IS UP -- sending chop-size 43 %',
  'PASS IF: NOTHING CHANGES -- still says recording and chop-size never appears -- the modal outranks it',
  [('modal recording', 'disp'), ('chop-size 43 %', 'disp')]),
 ('WARNING OVER THE MODAL -- sending warn u_root test-warn',
  'PASS IF: a box border with warn then u_root then test-warn -- AND about 2s later it vanishes and RECORDING IS BACK underneath',
  [('modal recording', 'disp'), ('warn u_root test-warn', 'err')]),
 ('MODE TO PERFORM -- nothing is sent to the screen',
  'PASS IF: NOTHING CHANGES -- still recording. Mode is never drawn -- this only sets up the next two steps',
  [('modal recording', 'disp'), ('perform', 'mode')]),
 ('WARNING WHILE IN PERFORM -- sending warn u_root hidden-warn',
  'PASS IF: NOTHING CHANGES -- no alert box at all -- still recording. Perform mode suppresses warnings',
  [('modal recording', 'disp'), ('warn u_root hidden-warn', 'err')]),
 ('FAILURE WHILE IN PERFORM -- sending fail u_root shown-fail',
  'PASS IF: an alert DOES appear -- fail then u_root then shown-fail -- failures are never suppressed -- then recording returns after about 4s',
  [('modal recording', 'disp'), ('fail u_root shown-fail', 'err')]),
 ('MODE BACK TO COMPOSE -- nothing is sent to the screen',
  'PASS IF: NOTHING CHANGES -- still recording',
  [('modal recording', 'disp'), ('compose', 'mode')]),
 ('WARNING NOW WE ARE BACK IN COMPOSE -- sending warn u_root back-again',
  'PASS IF: the alert DOES appear this time -- warn then u_root then back-again -- the filter released',
  [('modal recording', 'disp'), ('warn u_root back-again', 'err')]),
 ('CLEARING THE MODAL -- sending modal-off',
  'PASS IF: recording disappears and you are back to the two meters and the BPM footer',
  [('modal-off', 'disp')]),
 ('SAFETY TIMEOUT -- sending modal stuck and then DELIBERATELY never clearing it',
  'PASS IF: stuck appears now -- then with NO further input it clears itself after 30s. Next line is in 35s',
  [('modal stuck', 'disp')]),
 ('THE 30 SECOND SAFETY TIMEOUT -- the deferred half of step 13',
  'PASS IF: the screen returned to the meters on its own during that 35s wait -- that was the safety timeout',
  []),
]

STEPS_NANOKONTROL = [
 ('baseline -- sending nothing',
  'PASS IF: two bars with a small gate mark under each and a BPM at the bottom -- Phase 5 hands the footer over from v0.2-ready to the tempo about four seconds in',
  []),
 ('ONE MOVER -- chop-size 43 %',
  'PASS IF: chop-size small on the top line and a BIG 43 % under it -- this is the Phase 3 layout and it must be unchanged',
  [('chop-size 43 %', 'disp')]),
 ('TWO MOVERS -- chop-size and grain together',
  'PASS IF: TWO stacked pairs -- chop-size over 43 % on top and grain over 12 below -- FIRST TOUCHED on top and the value mid-sized',
  [('chop-size 43 %', 'disp'), ('grain 12', 'disp')]),
 ('FIVE MOVERS',
  'PASS IF: FIVE small lines in the order they were first touched: chop-size then grain then slider-1 then knob-3 then btn-t-2',
  [('chop-size 43 %', 'disp'), ('grain 12', 'disp'), ('slider-1 64', 'disp'), ('knob-3 100', 'disp'), ('btn-t-2 1', 'disp')]),
 ('SEVEN MOVERS -- two more than fit',
  'PASS IF: still exactly FIVE lines -- a1 a2 a3 a4 a5 -- and a6 and a7 are REFUSED rather than pushing the rows around. Nothing shifts',
  [('a1 1', 'disp'), ('a2 2', 'disp'), ('a3 3', 'disp'), ('a4 4', 'disp'), ('a5 5', 'disp'), ('a6 6', 'disp'), ('a7 7', 'disp')]),
 ('AGEING -- only a1 is kept alive from here',
  'PASS IF: the other four fade out within about 1.3 s and a1 alone is left -- and it grows BACK to the big 24px layout',
  [('a1 1', 'disp')]),
 ('MODAL OVER PARAMETERS -- modal recording',
  'PASS IF: recording at mid size and NO parameters at all -- the modal outranks them',
  [('modal recording', 'disp'), ('chop-size 43 %', 'disp')]),
 ('WARNING OVER THE MODAL',
  'PASS IF: a bordered alert -- warn then u_root then bench-warn -- then about 2 s later it vanishes and RECORDING IS STILL THERE underneath',
  [('modal recording', 'disp'), ('warn u_root bench-warn', 'err')]),
 ('PERFORM MODE -- nothing is drawn',
  'PASS IF: NOTHING CHANGES -- still recording. This only sets up the next two steps',
  [('modal recording', 'disp'), ('perform', 'mode')]),
 ('WARNING WHILE IN PERFORM',
  'PASS IF: NOTHING CHANGES -- no alert at all. Perform suppresses warnings',
  [('modal recording', 'disp'), ('warn u_root hidden-warn', 'err')]),
 ('FAILURE WHILE IN PERFORM',
  'PASS IF: an alert DOES appear -- failures are never suppressed -- then recording returns after about 4 s',
  [('modal recording', 'disp'), ('fail u_root shown-fail', 'err')]),
 ('BACK TO COMPOSE',
  'PASS IF: NOTHING CHANGES -- still recording',
  [('modal recording', 'disp'), ('compose', 'mode')]),
 ('WARNING NOW WE ARE IN COMPOSE',
  'PASS IF: the alert DOES appear this time -- the filter released',
  [('modal recording', 'disp'), ('warn u_root back-again', 'err')]),
 ('CLEARING THE MODAL',
  'PASS IF: recording disappears and you are back to the two meters and the BPM footer',
  [('modal-off', 'disp')]),
 ('THE NANO -- sweep every slider and knob now',
  "PASS IF: each control names ITSELF -- slider-1 to slider-9 then knob-1 to knob-9 -- and none reports another's name. Watch slider 9 then knob 1 especially: CC 9 and CC 11 are where an off-by-one shows",
  [],
  {'do': 'sweep every slider and every knob on the nanoKONTROL',
   'need': ['the nanoKONTROL powered and connected']}),
 ('THE NANO -- two faders at once then three then all nine',
  'PASS IF: two stay readable as stacked pairs -- three to five become small lines -- and nine shows the FIVE YOU TOUCHED FIRST with the rest refused. Rows must not reshuffle while you move things',
  [],
  {'do': 'move two faders at once -- then three -- then all nine',
   'need': ['the nanoKONTROL powered and connected']}),
 ('THE NANO -- press every button then all six transport keys',
  'PASS IF: all 18 buttons name themselves on press and nothing on release. The six transport keys report xport-1 to xport-6 on press -- no toggle and no footer change',
  [],
  {'do': 'press every button on the nanoKONTROL then all six transport keys',
   'need': ['the nanoKONTROL powered and connected']}),
]

STEPS_TEMPO = [
 ('baseline -- re-asserting 120 BPM and stopped',
  'PASS IF: two bars with a small gate mark under each and 120-bpm in the footer -- and the aux button lit DARK BLUE. This step exists so the run repeats without reopening the patch',
  [('120', 'tempo'), ('bang', 'stop')]),
 ('COUNTING -- zeroing the beat counters for 10 s at 120 BPM',
  'PASS IF: NOTHING VISIBLE CHANGES. The transport is still stopped and the clock is running anyway -- which is exactly what is being counted',
  [('bang', '\\$0-zero')]),
 ('READ THE COUNTS -- the clock ran for 10 s while STOPPED',
  'PASS IF: M-BEATS 20 or 21 -- C1-BEATS the same number -- C2-BEATS 30 or 31. A zero anywhere means the clock does not run until the transport does -- or on the Mac it means DSP is off which looks exactly the same',
  [('bang', '\\$0-read')],
  # ⛔ THE RATIO IS THE POINT, and it is why this is not three range checks. A
  # count in a range still depends on the real-time scheduler having kept up;
  # C2/C1 cancels the scheduler entirely, because both counters were driven by
  # the same clock over the same window. tempo-assert.sh makes the same argument
  # about 24 PPQN on the wire.
  {'watch': 'M-BEATS reads 20 or 21 -- C1-BEATS-ratio-1 the same -- C2-BEATS-ratio-1.5 reads 30 or 31 -- and C2 over C1 is 1.5',
   'check': {'kind': 'all', 'of': [
      {'kind': 'print', 'name': 'M-BEATS', 'min': 19, 'max': 22},
      {'kind': 'print', 'name': 'C1-BEATS-ratio-1', 'min': 19, 'max': 22},
      {'kind': 'print', 'name': 'C2-BEATS-ratio-1.5', 'min': 29, 'max': 32},
      {'kind': 'ratio', 'a': 'C2-BEATS-ratio-1.5', 'b': 'C1-BEATS-ratio-1',
       'want': 1.5, 'tol': 0.15},
  ]}}),
 ('START THE TRANSPORT',
  "PASS IF: the aux button turns GREEN and the 404 starts its pattern. WATCH EXT ON THE 404'S PATTERN SELECT SCREEN -- the number beside a pad is that SAMPLE's BPM and never moves",
  [('bang', 'start')]),
 ('TEMPO THROUGH THE MAP -- og-knob-1 at 0 -- PICKUP HOLDS IT',
  "PASS IF: ⛔ THIS ONE DIFFERS BY WHETHER A SAVE HAS EVER HAPPENED AND THE DIFFERENCE IS PICKUP WORKING. WITH A SAVED knobs.txt -- the device after any Storage Save -- the footer does NOT move: mother restored knob 1 at boot and 0 is below that stored value so the knob is HELD until it crosses back. WITH NO knobs.txt -- always on the Mac and on the device after deploy.sh --clean -- u_map reads that the file is absent and holds nothing so this lands and the footer reads 10-bpm with the 404's EXT sliding down",
  [('og-knob-1 0', 'param')]),
 ('TEMPO THROUGH THE MAP -- og-knob-1 at 1 -- THE CROSSING',
  "PASS IF: the footer reads 500-bpm and the 404's EXT slides up. WITH A SAVED knobs.txt this is the moment the knob crosses the restored value and TAKES OVER -- held one step ago and live now. A slide rather than a snap IS the inference working -- it snaps only to a tempo it has already learned",
  [('og-knob-1 1', 'param')]),
 ('TEMPO THROUGH THE MAP -- back to 0 -- LIVE ON BOTH MACHINES',
  'PASS IF: the footer reads 10-bpm on EITHER machine. Pickup has handed over so the knob tracks normally from here -- if this one is held too then the release never happened and the knob is stuck',
  [('og-knob-1 0', 'param')]),
 ('OUT OF RANGE -- 5000 sent TWICE',
  'PASS IF: the footer reads 600-bpm and EXACTLY ONE alert appears -- a bordered box naming u_tempo. The second 5000 must be silent because the VALUE did not change',
  [('5000', 'tempo'), ('5000', 'tempo')],
  # ⛔ EXACTLY ONE, and that is the whole step. The second 5000 must be silent
  # because the VALUE did not change -- "one or more alerts" is satisfied by two
  # and would pass the bug. A person counting bordered boxes on an OLED that
  # redraws is exactly the oracle a machine should replace.
  {'check': {'kind': 'bus-count', 'bus': 'ERR', 'match': 'u_tempo', 'n': 1}}),
 ('OUT OF RANGE THE OTHER WAY -- 0',
  'PASS IF: the footer reads 5-bpm and a SECOND alert appears. The verdict did not change but the value did -- and this is the case that was broken once',
  [('0', 'tempo')]),
 ('BACK TO 120',
  'PASS IF: the footer reads 120-bpm and NO alert appears at all',
  [('120', 'tempo')]),
 ('STOP -- and the clock must NOT stop with it',
  'PASS IF: the aux button goes DARK BLUE and the 404 stops -- but its display MUST STILL SAY EXT. If it falls back to BPM the clock stopped with the transport and that is the bug this step exists for',
  [('bang', '\\$0-zero'), ('bang', 'stop')]),
 ('READ THE COUNTS WHILE STOPPED',
  'PASS IF: M-BEATS 20 or 21 again. Stop the pulse stream and the 404 stretches every sample to a stale tempo -- so this is the least obvious requirement in the phase',
  [('bang', '\\$0-read')],
  # ⛔ A ZERO HERE IS THE BUG THE STEP EXISTS FOR: the transport pauses the
  # subscribers, it does not clear the timer, and a clock that stopped with the
  # transport leaves the 404 stretching every sample to a stale tempo.
  {'check': {'kind': 'print', 'name': 'M-BEATS', 'min': 19, 'max': 22}}),
 ('PANIC',
  'PASS IF: the aux button turns RED and the footer says panic -- and the clock is STILL running underneath',
  [('bang', 'panic')]),
 ('BY HAND -- press the aux button twice',
  'PASS IF: ON THE DEVICE use the real button. ON THE MAC use aux-tap and NOT the aux toggle -- aux is momentary 1 then 0 and only the 1 is a press -- so a toggle needs two clicks per press and the uncheck is meant to do nothing. First press GREEN and the 404 starts -- second DARK BLUE and it stops. If nothing happens at all then mother is eating the press',
  [],
  {'do': 'press the aux button twice -- ON THE MAC use aux-tap and NOT the aux toggle',
   'need': ['the Organelle powered and in reach']}),
 ('BY HAND -- sweep KNOB 1 all the way and back',
  'PASS IF: the row reads bpm and a NUMBER -- never og-knob-1 and never a 0-to-1 decimal. While the knob is still held it reads bpm 57 (120) or similar: the latched tempo first and the knob position in brackets. Once it crosses it reads bpm alone and tracks between 10 and 500. The 404 follows the sweep. ⚠️ A FULL SWEEP ALWAYS CROSSES so pickup can never make this step fail -- that is why it is a sweep and not a nudge',
  [],
  {'do': 'sweep Organelle knob 1 all the way and back -- a FULL sweep always crosses',
   'need': ['the Organelle powered and in reach']}),
]

STEPS_LAUNCHPAD = [
 ('baseline -- 120 BPM -- stopped -- compose mode-1',
  'PASS IF: the top row shows ONE bright green lamp at the far left and five dim ones beside it -- and the BOTTOM row of pads has a single white pad. DIM MEANS FAINT AND NOT OFF: the five idle lamps are colour 1 which is a near-black grey and the current one is 21. THE WHITE PAD IS ALREADY WALKING and that is correct -- c_clock free-runs and the transport gates what PLAYS rather than what counts -- so a frozen pad here is the fault and a moving one is not. Everything else on the surface is dark',
  [('120', 'tempo'), ('bang', 'stop'), ('compose mode-1', 'mode')]),
 ('MODE -- selecting the fourth mode',
  'PASS IF: the bright lamp MOVES to the fourth position and the other five go dim. Nothing else on the grid changes',
  [('perform mode-4', 'mode')]),
 ('MODE -- the second lamp',
  'PASS IF: the bright lamp lands on the SECOND position. Between this step and the next four the bus drives all six lamps in turn -- until now only two of the six were ever exercised without hands',
  [('compose mode-2', 'mode')]),
 ('MODE -- the fifth lamp',
  'PASS IF: the bright lamp lands on the FIFTH position and the other five go dim',
  [('perform mode-5', 'mode')]),
 ('MODE -- the sixth and last lamp',
  'PASS IF: the bright lamp lands on the sixth and last position. ONE MESSAGE PER STEP FOR ANYTHING VISUAL: two sent back to back both land inside the same frame and only the second is ever drawn -- found by running this bench and watching the painted frames rather than the surface',
  [('perform mode-6', 'mode')]),
 ('THE grid SELECTOR MUST NOT REACH THE OLED -- sending grid vocabulary g_grid ignores',
  'PASS IF: NOTHING HAPPENS ON EITHER SURFACE. g_oled treats every selector it does not recognise as a parameter to draw -- so without grid in its route this would appear on the OLED as a nonsense parameter row called grid. That one route argument is the whole reason a third display surface was cheap',
  [('grid no-such-thing', 'disp')]),
 ('MODAL -- the whole surface claimed',
  'PASS IF: EVERY pad and every lamp on the top row turns blue. The mode lamps are covered too -- that is the point of a modal. THE OLED MUST NOT CHANGE',
  [('grid modal 45', 'disp')]),
 ('MODE CHANGE UNDERNEATH A MODAL -- nothing should be visible',
  'PASS IF: NOTHING HAPPENS. The surface stays blue. The mode really does change underneath and you will see it two steps from now. THIS STEP RE-SENDS THE MODAL BEFORE THE MODE CHANGE and so does the next one -- not decoration: the modal safety TTL is thirty seconds of WALL CLOCK and under manual stepping the gap between two steps is however long you take. Without the re-send this chain silently expires mid-test and the surface is back to mode lamps before the step that needs it runs. Re-asserting a live modal is what a caller would do anyway and it restarts the timer',
  [('grid modal 45', 'disp'), ('perform mode-3', 'mode')]),
 ('ALERT ON TOP OF A MODAL -- two layers deep',
  'PASS IF: the surface turns RED for about two seconds and then goes back to BLUE -- NOT to the mode lamps. The modal is still up underneath and the alert only borrowed the surface. This is the only step that tests the cascade more than one layer deep. The modal is re-sent first for the same reason as the last step',
  [('grid modal 45', 'disp'), ('fail u_bench stacked', 'err')]),
 ('MODAL OFF',
  'PASS IF: the grid returns to mode lamps and the beat row -- and the bright lamp is now the THIRD one -- which is the change made while the modal covered it. THIS STEP RE-SENDS THE MODAL BEFORE CLEARING IT and that is not pointless: the 30 second safety TTL is wall clock and it has expired underneath this step before -- on the first device run -- because a report was being typed between the last step and this one. When that happens the surface has ALREADY returned home by itself and modal-off clears nothing -- the step passes while proving nothing at all. Raising it again first means there is always a modal here to clear. You will not SEE the re-raise because both messages land in one frame and only the last is drawn -- that is expected and it is why the previous steps carry the visible part of this test',
  [('grid modal 45', 'disp'), ('grid modal-off', 'disp')]),
 ('ALERT -- a fail -- which outranks everything',
  'PASS IF: the whole surface turns RED -- and then goes back to the mode lamps BY ITSELF after about two seconds. A grid that stays red is the bug this step exists for',
  [('fail u_bench boom', 'err')]),
 ('ALERT -- a warn -- which the grid must ignore but the OLED must show',
  'PASS IF: NOTHING HAPPENS ON THE GRID and the OLED DOES show the warning. Only a fail is worth the whole surface. THE compose SENT FIRST IS LOAD-BEARING and not a mode test: u_err gates warns off the SCREEN in perform mode -- compose sets its verbose spigot to 1 and perform sets it to 0 -- and this bench put itself in perform at step 8. Without the compose the OLED stays blank for a legitimate reason and the step cannot tell that apart from the grid filter working. Fails ignore the spigot which is why the previous step needed no such thing',
  [('compose mode-3', 'mode'), ('warn u_bench quiet', 'err')]),
 ('THE 30 SECOND MODAL SAFETY TTL -- this step needs you to wait',
  'PASS IF: the surface turns green and then clears ITSELF about thirty seconds later with nothing sent to it. DO NOT PRESS GO -- sit and watch it. A modal is sticky by design so this timer is the only thing between a stuck modal and a grid that never comes back. It has never once been observed',
  [('grid modal 21', 'disp')]),
 ('TRANSPORT -- start -- and the beat counter starts with it',
  'PASS IF: the white pad WALKS along the bottom row -- twice a second -- and the aux LED goes green. ON THE MAC THE AUX LED IS NOT A BUTTON: it is the numeric readout labelled aux-LED on the bottom row of the dev panel next to the clock beat bng and the tempo-bus box -- with a symbol box beside it spelling the colour. Only the Organelle has a lamp to look at. On the Mac with DSP off the pad will not move -- tick enable-DSP first. A BEATS line prints about ten seconds from now',
  [('bang', 'start'), ('bang', '\\$0-zero')],
  # The eyes still judge the walking pad and the aux LED. What the machine can
  # judge is the number underneath them, which is the same evidence and is not
  # subject to anyone counting flashes.
  # ⚠️ THE EXPECTED COUNT IS STATED IN `watch` BECAUSE THE PASS IF DOES NOT SAY
  # IT -- it only promises a BEATS line "about ten seconds from now". A predicate
  # asserting a number the prose never mentions is a disagreement waiting to
  # happen, and the person reading the terminal deserves to know what it wants.
  {'watch': 'the white pad WALKS along the bottom row twice a second and the aux LED goes green -- then a BEATS line of about 20 prints about ten seconds from now',
   'check': {'kind': 'print', 'name': 'BEATS', 'min': 19, 'max': 22}}),
 ('THE BEAT ROW WRAPPING -- WATCH ONLY -- this step sends nothing on purpose',
  'PASS IF: the white pad reaches the EIGHTH pad and the next step is back to the FIRST -- with no gap and no stray light anywhere else. NO ACTION IS SENT AND THAT IS DELIBERATE rather than an omission: the wrap happens on the clock schedule and cannot be provoked on demand -- the only way to test it is to watch one go by -- and it gets its own step because folding it into the transport step is how it goes unlooked-at. Nothing here disturbs the ten second BEATS window still running underneath. THE BEAT NUMBER IS ONE-BASED: built against a zero-based assumption beat 8 landed on a right-column ring button and blanked the row once a bar -- and seven beats out of eight looked perfect',
  []),
 ('TEMPO -- 240 BPM -- so the beat row should double',
  'PASS IF: the white pad moves twice as fast. The BEATS line just printed covers ten seconds at 120 and should read about 20 -- the next one covers ten seconds at 240 and should read about 40. EXPECT A VISIBLE SWING HERE AND DO NOT FAIL THE STEP FOR IT. g_grid repaints on a metro 100 so the row can only move on a 100 ms boundary. At 120 BPM a beat is 500 ms which divides exactly and the walk is dead even. At 240 a beat is 250 ms which does not -- so beats land alternately at 200 and 300 ms and the row swings by 50 either way. The CLOCK is not swinging and the BEATS count is unaffected: this is the display quantising. It is the price of the 10 Hz repaint that keeps MIDI writes inside the CPU budget',
  [('bang', '\\$0-read'), ('240', 'tempo'), ('bang', '\\$0-zero')]),
 ('back to 120 and stopped',
  'PASS IF: the second BEATS line reads about 40 -- then the beat row slows to two a second. THE CLOCK KEEPS RUNNING WHEN THE TRANSPORT STOPS -- so the pad must keep walking after the stop',
  [('bang', '\\$0-read'), ('120', 'tempo'), ('bang', 'stop')]),
 ('HANDS ON THE LAUNCHPAD -- press pads and RELEASE them',
  'PASS IF: every pad you press reports pad-NN on the OLED with its velocity -- and RELEASING it reports the same name with 0. Bottom left is 11 and top right is 88. Pressure on a held pad reports NOTHING on the OLED -- that is deliberate and it is not a fault',
  [],
  {'do': 'press pads on the Launchpad and RELEASE them',
   'need': ['the Launchpad connected and in Programmer Mode']}),
 ('HANDS ON THE LAUNCHPAD RING -- and the row that must stay dark',
  'PASS IF: the ring buttons report lp-cc-NN. Check the two the documentation got wrong: the TOP LEFT CORNER is 90 and the bottom row is 101 to 108. THEN LOOK AT CC 1 TO 8 -- AND NOTE THAT THIS EXPECTATION IS NOW THE OPPOSITE OF WHAT IT ONCE WAS. That row used to be outside the painted span and had to be DARK. It is INSIDE it now -- the span runs 1 to 108 -- so it must be lit like everything else and must go blue under a modal and red under an alert. THE REASON WAS NOT THAT ANYTHING WANTED THOSE EIGHT BUTTONS. LED state survives the Programmer Mode switch -- so an index outside the span keeps whatever Live Mode last drew there forever and no repaint can reach it. This bench is what caught that: the row was green from an old probe on one run and dark on the next -- with nothing in Cut It touching it either time. ONE BUTTON IS STILL OUTSIDE -- INDEX 0 -- SETUP -- and that one is measured rather than chosen: it takes no colour and it transmits nothing in Programmer Mode',
  [],
  {'do': 'press the Launchpad ring buttons -- including the top left corner and the bottom row',
   'need': ['the Launchpad connected and in Programmer Mode']}),
 ('HANDS ON THE NANOKONTROL -- the six transport keys',
  'PASS IF: each of the six keys moves the bright lamp to its own position. This is the mode bus finally having a driver',
  [],
  {'do': 'press each of the six nanoKONTROL transport keys',
   'need': ['the nanoKONTROL powered and connected', 'the Launchpad connected and in Programmer Mode']}),
 ('HANDS -- THE REPLUG HAZARD -- unplug the Launchpad and plug it back in',
  'PASS IF: RECORD WHAT HAPPENS -- this step documents a known hazard rather than asserting a fix. The device returns in Live Mode but m_launchpad still believes it owns the surface -- so press a few pads afterwards and watch the OLED: pad-NN names are the hazard showing itself because a stock layout sends musical pitches that get decoded as r*10+c. THIS STEP MUST COME BEFORE THE PANIC AND THAT IS THE WHOLE POINT. The hazard IS stale ownership -- run it after the panic and ownership has already been dropped legitimately so there is nothing stale left and the step silently tests nothing. It was ordered that way on the first run and proved exactly that. MEASURED SINCE: Pd does NOT lose the device on the Mac and the Launchpad still answers a universal device inquiry after a replug -- so this IS detectable by polling and the fix is unblocked. Not built yet. See plan-v04.md',
  [],
  {'do': 'unplug the Launchpad and plug it back in -- then press a few pads',
   'need': ['the Launchpad connected and in Programmer Mode']}),
 ('PANIC -- the surface goes back to the device',
  'PASS IF: BUTTON PRESSES STOP REACHING THE OLED. That is the assertion -- not the Launchpad changing appearance -- because the step before this one already left it in Live Mode by unplugging it. Watch for the INPUT going quiet rather than the display changing. What just happened is the panic curing the hazard the replug created: ownership was still 1 over a device we no longer control -- so presses were being decoded as grid coordinates -- and the panic drops it. If the previous step was skipped the device WILL visibly leave Programmer Mode here and its own display will return. KNOWN AND DELIBERATE: it stays that way until the patch is reloaded -- so EVERY REMAINING STEP IS DOWNSTREAM OF THIS ONE and nothing after it can check the grid. If you have any doubt about an earlier step go back and redo it before pressing GO here',
  [('bang', 'panic')]),
 ('AFTER THE PANIC THE GRID MUST GO SILENT -- sending it a mode change',
  'PASS IF: NOTHING HAPPENS. The Launchpad keeps showing its own display and g_grid paints nothing at all. Ownership dropped when the surface was handed back -- so the arbiter still runs and simply never reaches the wire',
  [('compose mode-1', 'mode')]),
 ('HANDS -- press a pad now -- after the panic',
  'PASS IF: NOTHING REACHES THE OLED. In a stock layout the notes are musical pitches rather than r*10+c -- and decoding them as coordinates would publish nonsense. Reload the patch to get the grid back',
  [],
  {'do': 'press a pad on the Launchpad now that the panic has run',
   'need': ['the Launchpad connected and in Programmer Mode']}),
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
 ('baseline -- the link is up and the mode is compose',
  'PASS IF: the bottom line of the phone reads ok rather than NO-LINK. Nothing else has to be true yet -- this proves only that the heartbeat is flowing and the scene is bound. IF IT SAYS NO-LINK STOP HERE and check that PdParty is open on the same network -- every step below depends on it. compose is set because u_err shows warnings in compose and only failures in perform',
  [('compose mode-1', 'mode')]),
 ('ONE PARAMETER -- name value and unit',
  'PASS IF: the top line reads chop-size and the big number reads 43 -- the unit rides on the wire but the scene does not draw it -- deliberate and not a fault',
  [('chop-size 43 %', 'disp')]),
 ('A SECOND PARAMETER -- and the stale-unit trap underneath it',
  'PASS IF: the top line changes to grain and the number to 12 -- THE POINT OF THIS STEP IS SOMETHING YOU CANNOT SEE: grain carries no unit and the step before it did -- so on the wire this has to arrive as grain 12 and a dash rather than grain 12 and a percent sign. The scene draws no units so a stale one would be invisible here. test/gate/phone-assert.sh is what actually proves it',
  [('grain 12', 'disp')]),
 ('THE STATUS LINE -- a row that is not a parameter',
  'PASS IF: the third line reads 128-bpm and the parameter name and number ABOVE IT DO NOT CHANGE. status has its own OSC address and its own slot. Expect u_tempo to overwrite this with the real BPM at the next transport event -- that is the footer being handed back and not a fault',
  [('status 128-bpm', 'disp')]),
 ('AN ALERT -- and it travels the whole error bus to get here',
  'PASS IF: the fourth line shows warn on the left and probe-warning on the right. This goes onto err rather than disp -- so u_err filtered it by mode and forwarded it -- which makes this the proof that the error bus reaches the phone and not just the OLED',
  [('warn u_bench probe-warning', 'err')]),
 ('THE ALERT PERSISTS -- which is the entire reason it is state',
  'PASS IF: several seconds later the fourth line STILL reads warn and probe-warning. An alert is an event and UDP cannot carry events -- so u_net holds the last one and repeats it on every heartbeat. On the OLED the same alert has long since timed out. THE TWO SURFACES DISAGREE ON PURPOSE and this step is where you see it',
  []),
 ('A SECOND ALERT REPLACES THE FIRST',
  'PASS IF: the fourth line changes to fail and probe-failure. A failure also draws on the OLED where the warning above may not have',
  [('fail u_bench probe-failure', 'err')]),
 ('THE METERS MUST NOT APPEAR -- correct result is nothing',
  'PASS IF: NOTHING ON THE PHONE CHANGES AT ALL. in-l and in-r are the entire resting content of the disp bus once there is audio -- about twenty messages a second -- and u_net drops them on purpose. If a line here starts reading in-l then the reserved branch is broken and the whole rate budget has gone to a meter the phone does not draw',
  [('in-l 42 dB', 'disp'), ('in-r 7 dB', 'disp')]),
 ('THE GRID VOCABULARY MUST NOT APPEAR -- and the Launchpad WILL react',
  'PASS IF: nothing on the phone changes. THE LAUNCHPAD GOING MODAL IS CORRECT -- grid is g_grid own vocabulary and this step proves only that u_net ignores it. The next step clears it',
  [('grid modal 45', 'disp')]),
 ('CLEARING THE GRID -- still nothing on the phone',
  'PASS IF: the Launchpad returns to its home layout and the phone does not move',
  [('grid modal-off', 'disp')]),
 ('THE AUX LED -- still nothing on the phone',
  'PASS IF: the aux button goes green and the phone does not move. That is the third reserved selector proven inert in a row',
  [('led running', 'disp')]),
 ('HANDS -- sweep a nanoKONTROL fader as fast as you can',
  'PASS IF: the phone tracks the fader while it moves and then SETTLES ON THE VALUE YOU STOPPED AT. A phone left showing a number from the middle of the sweep is the trailing edge failing -- the one bug in this phase that hands can catch and that no headless run reproduces with real timing. Sweep two faders at once if you have the fingers -- both must settle correctly',
  [],
  {'do': 'sweep a nanoKONTROL fader as fast as you can -- two at once if you have the fingers',
   'need': ['the nanoKONTROL powered and connected', 'PdParty open on the CutItRemote scene']}),
 ('HANDS -- close PdParty on the phone and count to ten',
  'PASS IF: NOTHING ON THE ORGANELLE CHANGES. No audio glitch and no error on the OLED. THE ORGANELLE NEVER WAITS. What has actually happened is that the phone answered with an ICMP port-unreachable and the socket was destroyed -- and u_net has been reconnecting every five seconds ever since with nothing to show for it',
  [],
  {'do': 'close PdParty on the phone and count to ten',
   'need': ['PdParty open on the CutItRemote scene']}),
 ('HANDS -- reopen PdParty',
  'PASS IF: the phone starts updating again WITHIN ABOUT FIVE SECONDS and you touched nothing on the Organelle. THIS IS THE STEP THAT PROVES ITEM 114 ON REAL HARDWARE. A link that could not recover would be dead for the rest of the set and nothing on the instrument would say so -- which is exactly what the first build did before Step 0 measured it',
  [],
  {'do': 'reopen PdParty on the phone -- touch NOTHING on the Organelle',
   'need': ['PdParty open on the CutItRemote scene']}),
]

STEPS_STATE = [
 ('baseline -- the patch has just booted and nothing has been touched',
  'PASS IF: the Launchpad top row shows exactly ONE lit mode lamp. WHICH one is the test: a fresh install comes up on mode-1 and a restored one comes up wherever you left it. If the grid is dark then the Launchpad is not owned and nothing below can be read',
  [],
  {'do': 'look at the Launchpad top row -- press nothing',
   'need': ['the Launchpad connected and in Programmer Mode']}),
 ('CHANGE THE MODE -- press transport key 4 on the nanoKONTROL',
  'PASS IF: the lit lamp moves to the fourth position. Nothing about STATE is visible yet and that is correct -- u_state has it in memory and flushes within two seconds',
  [],
  {'do': 'press transport key 4 on the nanoKONTROL',
   'need': ['the nanoKONTROL powered and connected', 'the Launchpad connected and in Programmer Mode']}),
 ('CONFIRM IT REACHED THE DISK -- from the Mac run ./tools/fetch-state.sh --show',
  'PASS IF: cut-it-auto.txt reads mode perform mode-4. THE FILE IS THE ONLY EVIDENCE -- nothing on the instrument displays what has been saved and that is deliberate. If it still reads the old mode the flush is not firing',
  [],
  {'do': 'nothing on the instrument -- the runner reads the file for you',
   'need': []}),
 ('COMMIT -- on the Organelle press Storage then Save',
  'PASS IF: the screen shows Saving briefly and returns. Then cut-it-manual.txt has a NEW timestamp even though it is still empty -- no shipped contributor uses the manual policy yet. An UNCHANGED timestamp means saveState never arrived and the commit path is dead',
  [],
  {'do': 'on the Organelle press Storage then Save',
   'need': ['the Organelle powered and in reach']}),
 ('THE ONE THAT MATTERS -- power cycle the Organelle and wait for it to come back',
  'PASS IF: the same mode lamp is lit as before the power cycle. This is the only durability test that counts -- a patch reload proves nothing about an SD card. DO THIS LAST IN A SESSION because it resets the wifi fault uptime clock and that fault needs about three hours to appear',
  [],
  {'do': 'power cycle the Organelle and wait for it to come back -- DO THIS LAST IN A SESSION',
   'need': ['the Organelle powered and in reach', 'the Launchpad connected and in Programmer Mode']}),
]


STEPS_MIDI = [
 ('baseline -- read the OLED footer before touching anything',
  'PASS IF: the footer reads 57 BPM and NOT 120 -- this is a REAL TEST and not a formality -- knobs.txt holds knob 1 at about 0.096 and mother pushes it at boot. 57 means the message went through the mapping TABLE and came out the tempo handler. 120 means u_tempo is sitting on its own default and the table never matched. Also note which mode lamp is lit on the Launchpad top row -- a restored session comes up wherever you left it',
  [],
  # ⚠️ ONLY ON THE DEVICE. 57 comes from knobs.txt, which mother reads at boot
  # and which no Mac has -- on a Mac this legitimately reads 120 and the
  # predicate would be asserting the absence of hardware.
  {'targets': ('device',),
   'check': {'kind': 'oled', 'has': ['57'], 'has_not': ['120']}}),

 ('GET TO MODE 1 -- HANDS -- press transport key 1 on the nanoKONTROL',
  'PASS IF: the lit lamp moves to the first position. Fader 1 is only bound in mode 1 so the later steps need this. If the lamp does not move then the nano is not reaching param and nothing below will work',
  [],
  {'do': 'press transport key 1 on the nanoKONTROL',
   'need': ['the nanoKONTROL powered and connected', 'the Launchpad connected and in Programmer Mode']}),

 ('THE 404 RECEIVE SIDE -- HANDS -- select BANK A on the SP-404 and press pad 1',
  'PASS IF: the OLED shows sp-bank 1 and sp-pad 1 -- this is the map this project got WRONG once and pad 1 is note 48 -- ⚠️ STATE WHICH BANK IS SELECTED OUT LOUD before every one of these: the 404 lights only the bank it is on and a receive test that does not state the bank cost half an hour once',
  [],
  {'do': 'select BANK A on the SP-404 and press pad 1',
   'need': ['the SP-404 powered and connected']}),

 ('THE PAD THAT BREAKS THE OLD FORMULA -- HANDS -- press pad 5 on bank A',
  'PASS IF: sp-pad reads 5 -- pad 5 is note 44 and NOT note 52 -- anything other than 5 means the pad table is wrong in exactly the direction this repo used to have it wrong',
  [],
  # ⛔ THE PAD THAT CATCHES `47 + n`. Under the old formula pad 5 reads 13, and
  # 13 is a plausible-looking number on an OLED -- which is how that bug lived
  # in this repo's own docs for months. A person reads two digits; this reads
  # the bus.
  {'do': 'press pad 5 on bank A of the SP-404',
   'need': ['the SP-404 powered and connected', 'BANK A selected -- say it out loud'],
   'check': {'kind': 'bus', 'bus': 'DISP', 'has': ['sp-pad 5']}}),

 ('WALK THE WHOLE BANK -- HANDS -- press pads 1 through 16 in order on bank A',
  'PASS IF: sp-pad counts 1 2 3 up to 16 in step with your finger while sp-bank stays at 1 throughout. The headless gate already asserts all sixteen notes -- what this adds is that the DEVICE agrees with it. A run that goes 1 2 3 4 then jumps is the old formula surviving somewhere',
  [],
  {'do': 'press pads 1 through 16 in order on bank A',
   'need': ['the SP-404 powered and connected']}),

 ('THE BANK IS THE CHANNEL -- HANDS -- select BANK B and press pad 1',
  'PASS IF: sp-pad still reads 1 but sp-bank CHANGES from 1 to 2 -- two rows rather than one because a single row could not tell A1 from B1 -- and it could not be one row carrying both: g_oled formats a value with makefilename %g which refuses a symbol so sp-hit b1 is impossible',
  [],
  {'do': 'select BANK B on the SP-404 and press pad 1',
   'need': ['the SP-404 powered and connected', 'BANK B selected -- say it out loud'],
   'check': {'kind': 'bus', 'bus': 'DISP', 'has': ['sp-pad 1', 'sp-bank 2']}}),

 ('A RELEASE IS NOT A PRESS -- HANDS -- press and hold any pad then let go',
  'PASS IF: both rows update on the PRESS and NEITHER updates again on the release. The release is a real event and does reach param but it is not worth a display row. Two updates per hit means the velocity test on the disp side has gone',
  [],
  # ⛔ EXACTLY ONE sp-pad ROW FOR ONE HIT. Two means the velocity test on the
  # disp side has gone and every pad is reporting itself twice -- which on a
  # screen that redraws looks like nothing at all.
  {'do': 'press and hold any pad on the SP-404 then let go',
   'need': ['the SP-404 powered and connected'],
   'watch': 'the sp-pad and sp-bank rows update ONCE on the press and NOT again when you let go -- exactly one sp-pad row per hit',
   'check': {'kind': 'bus-count', 'bus': 'DISP', 'match': 'sp-pad', 'n': 1}}),

 ('THE MAP IS MODE-DEPENDENT -- HANDS -- in mode 1 move FADER 1 on the nanoKONTROL',
  'PASS IF: the Volca tone changes as you move it. Fader 1 is bound to Volca CC 41 in mode 1 and to NOTHING in the other five. THIS IS THE POINT OF THE WHOLE PHASE -- a control means whatever the row for the current mode says it means. ⚠️ The Volca is BY EAR and always will be -- it transmits nothing so there is never a readback',
  [],
  {'do': 'in mode 1 move FADER 1 on the nanoKONTROL',
   'need': ['the nanoKONTROL powered and connected', 'the Volca audible -- it transmits nothing so there is never a readback']}),

 ('NOW CHANGE MODE AND MOVE THE SAME FADER -- HANDS -- transport key 4 then fader 1',
  'PASS IF: the Volca does NOT change. Nothing is broken -- there is no row for fader 1 in mode 4 and an unmapped control is the normal state of most controls. SILENCE IS THE PASS. The OLED still shows the fader moving because m_nano publishes it either way',
  [],
  {'do': 'press transport key 4 then move fader 1',
   'need': ['the nanoKONTROL powered and connected', 'the Volca audible -- it transmits nothing so there is never a readback']}),

 ('AND BACK -- HANDS -- transport key 1 then fader 1 again',
  'PASS IF: the Volca responds again. If it stays silent then the mode did not change back and the lit lamp will say so',
  [],
  {'do': 'press transport key 1 then move fader 1 again',
   'need': ['the nanoKONTROL powered and connected', 'the Volca audible -- it transmits nothing so there is never a readback']}),

 ('TEMPO STILL COMES FROM KNOB 1 -- HANDS -- turn Organelle knob 1',
  'PASS IF: the footer BPM follows the knob over roughly 10 to 500 -- ⛔ BUT NOT UNTIL THE KNOB PASSES THROUGH THE RESTORED VALUE. knobs.txt restored a position and the physical knob is wherever you left it -- so turning it does NOTHING until it crosses -- and then it takes over and tracks. That is parameter pickup and the jump it replaced was measured at 443 BPM. Knob 1 is a TABLE ROW now like everything else',
  [],
  {'do': 'turn Organelle knob 1 -- it does nothing until it crosses the restored value',
   'need': ['the Organelle powered and in reach']}),

 ('THE TRANSPORT STILL WORKS -- HANDS -- press the Organelle aux button twice',
  'PASS IF: the aux LED changes state each press and the footer agrees. The transport migrated into the table too so this is the proof that migrating it did not quietly drop it',
  [],
  {'do': 'press the Organelle aux button twice',
   'need': ['the Organelle powered and in reach']}),

 ('PANIC IS DELIBERATELY UNBOUND -- nothing to press -- read this and move on',
  'PASS IF: you understand why there is nothing to do here. NOTHING ON THE DEVICE CAN RAISE PANIC. It was briefly bound to a nano button and that was withdrawn: panic hands the Launchpad back to Live Mode BY DESIGN and the watchdog deliberately does not fight it back -- so an accidental brush of a bare button would kill the grid for the rest of the session with no console to explain it. m_404 now silences all ten banks when panic DOES arrive and the headless gate proves that. Choosing which control is worth that power is a v0.4 decision',
  []),

]
