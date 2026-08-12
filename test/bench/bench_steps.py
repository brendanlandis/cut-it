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

⚠️ `need` and `do` NEVER REACH A .pd -- see norm() -- so they carry ordinary
commas and are written as plain instructions.
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

# ⛔ WHERE THE BENCH THINKS IT IS, AND IT IS THE ONLY QUESTION THE RUNNER CAN ASK.
# Every other word in the protocol is an instruction -- go, rerun, show -- and an
# instruction that goes missing cannot be told from one the bench ignored. GO
# travels as a single UDP datagram, which has no delivery guarantee of any kind,
# so a lost one and a dead patch produce the SAME silence: no fired line, no
# described step, nothing. `where` is what tells them apart, because the answer
# names the step and the phase and so says whether the last GO landed.
#
# ⚠️ IT IS A [print] PREFIX RATHER THAN A SENTENCE, unlike every marker above.
# The numbers are live -- they come out of the two [f] stores -- and a message
# box cannot carry `$1` through the generator's escaping, which turns every `$`
# into `\$` precisely so step prose cannot smuggle one in. `print bench-at` needs
# no escaping and no format string at all.
SAY_WHERE = "bench-at"
RE_WHERE = re.compile(r"\bbench-at: (\d+) (\d+)\b")


def norm(step):
    """A step is 3 or 4 long -> (title, pass_if, actions, meta).

    ⛔ THE FOURTH ELEMENT IS RUNNER-SIDE ONLY AND NEVER REACHES A .pd. It carries
    what a person needs (`need` and `do`) and what a program needs
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
  'PASS IF: stuck appears in mid-size text and stays.',
  [('modal stuck', 'disp')],
  # ⛔ NOT HELD, AND THE TIMER IT WOULD RESET IS THE NEXT STEP'S. The hold
  # exemption is derived from a step's own prose claiming a decay -- and this
  # step no longer makes that claim, because the decay moved to the step after
  # it. Re-firing `modal stuck` every 0.8 s while this verdict is open restarts
  # the 30 s safety TTL each time, so the step that judges it would be waiting on
  # a timer that never got to run. The refusal has to be explicit here.
  {'hold': False}),
 ('Modal safety timeout -- the wait',
  'PASS IF: The screen went back to the meters on its own with nothing touched.',
  [],
  # ⛔ THE WAIT IS THE STEP. The instruction used to sit in the step before it
  # as "do not answer until it has" -- an instruction inside a PASS IF, and in
  # the wrong step, so the thing you had to do arrived while you were judging
  # something else.
  {'do': 'Wait 30 seconds without touching anything.'}),
 # ⛔ THIS IS THE HALF NO GATE CAN REACH. oled-assert proves the roster draws
 # the right words in the right order; whether five 8px rows are READABLE at
 # arm's length is a person's judgment, and m_launchpad unchecked is 21
 # characters -- the whole width of a row -- so the longest line clips silently
 # if anything about the names or the state words ever grows.
 # ⛔ THE POINT OF THE WHOLE SHIFT LAYER, and it can only be judged with a
 # device actually gone. The nano carries start and stop now, so this is the
 # step that proves the panel alone can still silence the rig.
 ('Shifted stop with the nano unplugged',
  'PASS IF: The clock stops. The beat row on the Launchpad stops walking.',
  [],
  {'do': 'Hold the aux button and press the middle key.',
   'need': ['The nanoKONTROL unplugged.',
            'The clock running -- press PLAY on the nano before unplugging it.']}),
 ('The diag roster',
  'PASS IF: Five small lines naming m_launchpad m_nano m_organelle m_volca and m_404 -- each with here or gone or never or unchecked beside it. Every line is readable at arm reach and none is cut off at the right edge. About eight seconds later the meters come back on their own.',
  [],
  {'do': 'Hold the aux button and press the lowest key. Look hardest at the '
         'longest line: m_launchpad unchecked is exactly as wide as a row gets, '
         'so that is where clipping would show first. The word shift is on '
         'screen while aux is held and the roster draws over it.'}),
]

STEPS_NANOKONTROL = [
 ('Every slider and knob',
  "PASS IF: Each control names itself on the OLED -- slider-1 to slider-9 then knob-1 to knob-9. None reports another's name.",
  [],
  {'do': 'Sweep every slider and every knob. Watch slider 9 and knob 1 especially.'}),
 ('Several faders at once',
  'PASS IF: Two faders draw as stacked pairs. Three to five draw as small lines. Nine draws the five you touched first and refuses the rest. No row reshuffles while you are moving them.',
  [],
  {'do': 'Move two faders at once, then three, then all nine.'}),
 ('Every button and transport key',
  'PASS IF: All 18 buttons name themselves on press and nothing on release. REW FF LOOP and REC report xport-1 xport-3 xport-4 and xport-6 as raw rows. PLAY starts the clock and STOP stops it. No toggle.',
  [],
  # ⚠️ FOUR OF THE SIX DRAW A RAW ROW NOW AND NONE OF THEM DID BEFORE. The row
  # used to be consumed by u_map's hardcoded mode route, above the table, so it
  # never reached the lookup at all. Mode moved to the Launchpad's lit top row,
  # so these fall through to the table -- PLAY and STOP find start and stop
  # there, and the other four miss and report their raw value, which is item
  # 242's rule and the right behaviour: a control that does nothing and says
  # nothing cannot be told from a broken one.
  {'do': 'Press every button, then all six transport keys.'}),

 # ⛔ HOT-SWAP, THREE CASES, AND ITEM 235 IS THE PROOF THE FIRST TWO ARE NOT THE
 # SAME TEST. The transition case needs the device to have ANSWERED at least
 # once, because c_presence's warn is armed by a reply -- a device that was never
 # there is ABSENT rather than lost, and absent raises nothing. The absent-at-load
 # case needs a fresh load and can see what no transition ever shows: that a
 # device missing at boot is recovered at all.
 #
 # ⛔ AND THE THIRD IS RECOVERY FROM A TRANSITION -- out and back in mid-session,
 # which is what a knocked cable does and the only one of the three that happens
 # by accident. It read as covered because the other two sit either side of it:
 # one proves the loss is SEEN and the other proves a recovery happens, and
 # neither proves the device you were playing comes back. See the last step.
 ('Hot-swap -- unplugged mid-session',
  'PASS IF: A bordered alert on the OLED reads warn and then m_nano.',
  [],
  # ⚠️ wait 12 IS LOAD-BEARING -- the warn is three missed ticks behind the
  # unplug, up to 8 s, and the runner's default drain is 0.4 s.
  {'do': 'Press enter first, then unplug the nanoKONTROL and leave it out.',
   'wait': 20,
   'check': {'kind': 'bus', 'bus': 'ERR', 'has': ['warn m_nano']}}),
 ('Hot-swap -- absent at load',
  'PASS IF: Slider 1 draws a value row on the OLED.',
  [],
  # ⚠️ 60 SECONDS AND NOT 10 -- the nano needed two of the eight attempts on the
  # bench because the device was still enumerating when the first landed (item
  # 277). ⛔ AND THE SLIDER IS THE ORACLE, not the absence of a warn: the nano is
  # PASSIVE to look at, so the only proof the subscription came back is traffic
  # arriving through it.
  {'do': 'Plug it back in, wait 60 seconds, then move slider 1.',
   'reload': True,
   'need': ['The nanoKONTROL still unplugged from the last step.']}),

 # ⛔ THE STEP THE WHOLE DIAG LAYER EXISTS FOR, and it has to live in a bench
 # where a device is genuinely missing. The warn two steps up proves the loss
 # was DETECTED and lasts two seconds; this proves you can ask afterwards, which
 # is the thing that was impossible before. ⚠️ It runs BEFORE the device goes
 # back in, so it sits between the unplug and the replug rather than at the end.
 ('Hot-swap -- the diag roster names it',
  'PASS IF: The m_nano line reads gone. The other four lines are unchanged and none of them reads gone.',
  [],
  {'do': 'Hold the aux button and press the lowest key. Check m_launchpad and '
         'm_404 as well as m_nano: pulling one USB cable can knock a bystander '
         'off the bus, so a second line reading gone is worth knowing about '
         'rather than a miss.',
   'need': ['The nanoKONTROL still unplugged from the last step.']}),

 # ⛔ THE THIRD CASE, AND IT IS THE ONE THAT HAPPENS IN A ROOM. The two above
 # are loss DETECTED and absent-at-load RECOVERED -- neither of them watches a
 # device that was working, went away, and came back, which is what a knocked
 # cable does mid-set. The recovery path is not the same one: absent-at-load has
 # nothing to lose and no transition to fire on, while this arms u_present's
 # counter on the way out and has to land one of the eight re-wire attempts on
 # the way back in. It ran last so the device is plugged in from the step above,
 # and so nothing after it depends on a cable being out.
 ('Hot-swap -- unplugged and plugged back in',
  'PASS IF: The OLED draws a slider-1 row again when you move it.',
  [],
  # ⚠️ FIFTEEN SECONDS OUT, AND THAT IS NOT PADDING. The loss is three missed
  # presence ticks behind the unplug, so pulling it and pushing it straight back
  # never registers as a loss at all and the step would prove nothing.
  # ⚠️ AND UP TO 60 SECONDS BACK, for the same reason as the step above: the
  # eight attempts are spread over about seventy seconds and the nano needed two
  # of them on the bench because it was still enumerating (item 277).
  {'do': 'Press enter first. Unplug the nanoKONTROL and count to fifteen, then '
         'plug it back in and wait up to 60 seconds before moving slider 1.'}),
]

# ⛔ THE THREE BEAT-COUNT STEPS ARE GONE AND THE COUNTERS WITH THEM. `Beat counts
# while stopped` and `Beat counts after stopping` asserted the c_clock ratio and
# that a stop does not halt the timer -- both already owned, more tightly and in
# ~16 s, by clock-assert.py ("the two instances run at 1.5x each other") and
# tempo-assert.py ("the clock KEEPS RUNNING after a stop"). Neither touched a
# device: the counters live in the bench patch and print to the runner's own
# terminal, so the step text had to admit there was nothing on the instrument to
# look at. By this project's own test -- could this run with the named device
# unplugged -- they were not bench steps. `Zero the beat counters` armed them and
# nothing else, and its one other claim (dark blue is stopped) is step 1's.
# ⚠️ THE COST OF KEEPING THEM WAS latest.json: one claim judged twice under two
# names reports more coverage than exists, which is the nanokontrol duplication
# again one level up.
STEPS_TEMPO = [
 ('Resting display at 120 BPM',
  'PASS IF: Two meter bars each with a small gate mark under it and 120-bpm in the footer. The aux LED is dark blue.',
  [('120', 'tempo'), ('bang', 'stop')]),
 ('Knob pickup on the first touch',
  'PASS IF: The row reads bpm 57 (10) -- the position knob 1 was saved at first and where the bench has just moved it to in brackets -- and the footer stays 120-bpm. The tempo is held until the real knob is turned back past where it was saved. If this rig has no knobs.txt the row reads bpm 10 and the footer follows down to 10-bpm instead. The row must never read og-knob-1 and never a raw 0-to-1 decimal.',
  [('120', 'tempo'), ('og-knob-1 0', 'param')],
  # ⛔ THE FIRST NUMBER IS THE SAVED KNOB POSITION, NOT THE TEMPO IN FORCE, and
  # this line read 120 until hardware said otherwise. u_map builds the held row
  # from [tabread $0-pk-t] -- the pickup TARGET -- scaled x490+10, while the
  # incoming value takes the parallel chain into makefilename (%g) and rides in
  # the unit field. So a knobs.txt of 0.0957967 draws `bpm 57 (10)` however many
  # times the bench sends 120 to tempo first. ⚠️ BRANCH (a) NEEDS AN ARMED KNOB,
  # which needs a knobs.txt saved off the rail -- with 0 0 0 0 the equality
  # release fires and only (b) is reachable, which is why this text went two
  # rewrites without once being exercised.
  #
  # ⛔ NOT HELD. The runner re-fires a step every 0.8 s while its verdict is
  # open, so a parameter row survives g_oled's 1.3 s life -- but this step sends
  # a tempo AND a knob that maps to tempo, so each re-fire walks the footer from
  # 120 back down to 10 under the eyes of whoever is reading it. Measured on the
  # Mac: six full round trips in five seconds. [r]epeat still works and is the
  # right control for it, because a person asks for that one deliberately.
  {'hold': False}),
 ('Knob pickup crosses over',
  'PASS IF: The row reads bpm 500 and about a second later it ages out to show the footer underneath reading 500-bpm. The knob has crossed where it was saved and is live from here on.',
  [('og-knob-1 1', 'param')],
  # ⛔ THE ROW IS WHAT YOU SEE AND THE FOOTER IS UNDERNEATH IT. This asked for a
  # footer reading while its own param message raises g_oled's param layer, which
  # REPLACES home -- the same defect as the 404 step, found the same way. ⛔ AND
  # NOTHING SLIDES: the old text asked for a slide rather than a snap, which is
  # what a HAND turning a knob produces. The bench sends one discrete value, so
  # there is exactly one jump and no slide to see.
  ),
 ('Knob tracking after pickup',
  'PASS IF: The row reads bpm 10 and the footer underneath reads 10-bpm once it ages out. A row still reading 500 means the knob is stuck.',
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
 ('Start the transport',
  "PASS IF: The aux LED turns green and the 404 starts its selected pattern in time with it. The 404's screen shows an EXT tempo. The number beside a pad never moves.",
  [('bang', 'start')],
  # ⛔ A PATTERN HAS TO BE SELECTED AND STOPPED OR THERE IS NOTHING TO START, and
  # the step read as an instrument failure without it -- the aux button goes
  # green, the 404 sits there, and nothing on either device says why. Start (250)
  # moves the sequencer on its own (ref/device/sp404.md) but only once the
  # sequencer has a pattern loaded. The two steps after it inherit this state.
  {'need': ['The SP-404 on Pattern Select with a pattern loaded and nothing '
            'playing.']}),
 ('The 404 follows a tempo change',
  "PASS IF: The 404's EXT slides up to 180 rather than snapping and its pattern speeds up to match. The OLED fills with sp-pad rows -- that is the 404 reporting what it plays and it is correct. Those rows cover the footer so the new tempo is not readable there until the transport stops.",
  [('180', 'tempo')],
  # ⛔ 180 AND NOT 240, BECAUSE THE 404 FOLLOWS ONLY BETWEEN 40 AND 200 BPM and
  # pins outside that window -- ref/device/sp404.md, verified. At 240 the step
  # asked the hardware for something it cannot do and read as an instrument
  # failure. ⛔ AND THE FOOTER CLAIM WENT WITH IT: this step's own sp-pad rows
  # raise g_oled's param layer, which REPLACES home and therefore the footer, so
  # the step asserted a reading its own text guarantees is hidden. The footer is
  # asserted by `Stop the transport` instead, once the rows have stopped.
  ),
 ('Stop the transport',
  'PASS IF: The aux LED goes dark blue and the 404 stops but its screen still reads EXT. Falling back to BPM is the failure. The sp-pad rows stop arriving and the OLED settles back to the meters with 120-bpm in the footer.',
  [('120', 'tempo'), ('bang', 'stop')]),
 ('Panic',
  'PASS IF: The aux LED turns red and the footer reads panic.',
  [('bang', 'panic')]),
 ('Aux button transport',
  'PASS IF: The first press turns the aux LED green and the 404 starts. The second press turns it dark blue and the 404 stops.',
  [],
  # ⛔ WHICH CONTROL TO PRESS IS `do`, NOT THE PASS IF. Both fields carried the
  # Mac/device sentence, so the runner printed it twice on consecutive lines --
  # and the PASS IF opened on two instructions before it reached anything to
  # look at. A PASS IF says what you can SEE.
  {'do': 'Press the aux button twice.'}),
 ('Knob 1 tempo sweep',
  'PASS IF: The row reads bpm and a number that tracks the knob between 10 and 500 BPM. It never reads og-knob-1 and never a raw 0-to-1 decimal. The 404 follows the sweep.',
  [],
  # ⛔ NO BRACKETED SECOND NUMBER IS ASSERTED HERE AND THAT AMBIGUITY WAS THE
  # DEFECT. The old text described the HELD row -- `bpm 57 (120) or similar` --
  # as something you might or might not see, so a person who saw no bracket had
  # no way to tell a pass from a failure. By this step the knob was released
  # three steps ago and is live, so there is no bracket to see. The held format
  # is asserted where it actually happens, in `Knob pickup on the first touch`.
  {'do': 'Sweep knob 1 all the way and back.'}),
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
 # ⛔ THE LAMP IS NOW THE BUTTON, which is the whole reason the mode selector
 # moved here off the nano's transport row. The five steps above drive the mode
 # bus directly and judge the PAINTING; this one judges the SELECTION, which
 # nothing above it touches.
 # ⚠️ The half a person cannot see is that the RELEASE selects nothing -- a
 # Launchpad CC button sends 127 then 0 and re-selecting the same mode is
 # idempotent, so a doubled selection looks identical. map-assert owns that.
 ('Pressing a mode lamp selects it',
  'PASS IF: The bright lamp moves to the pad you pressed and stays there after you let go. The OLED does not change.',
  [],
  {'do': 'Press the third pad along in the top row, then the first.'}),
 ('Grid vocabulary stays off the OLED',
  'PASS IF: Nothing happens on either surface. In particular no parameter row called grid appears on the OLED.',
  [('grid no-such-thing', 'disp')]),
 ('Modal claims the surface',
  'PASS IF: Every pad and every ring button turns blue including the top row. The mode lamps are covered too. The OLED must not change.',
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
  'PASS IF: The surface turns green and then clears itself about thirty seconds later.',
  [('grid modal 21', 'disp')],
  {'do': 'Watch the grid for thirty seconds without touching anything.'}),
 ('Start the transport',
  'PASS IF: The white pad walks along the bottom row twice a second and the aux LED goes green. A BEATS line prints about ten seconds from now.',
  [('grid modal-off', 'disp'), ('bang', 'start'), ('bang', '\\$0-zero')],
  # ⛔ THE modal-off IS THIS STEP'S OWN PRECONDITION AND IT IS NOT DECORATION.
  # Step 13 paints the whole surface GREEN and is cleared only by its own
  # thirty-second safety timeout -- that IS what step 13 tests. Run in order a
  # person sits out that timeout, because 13's `do` tells them to. A `--from`
  # walk does not: it fires every earlier step as fast as the console answers,
  # so 13 goes up and 14 arrives seconds later with the beat row buried under
  # it. Every step sets up its own preconditions and a modal is one.
  # ⚠️ FOUND ON HARDWARE, on `--from 16`: the grid was "stuck in all-green" and
  # then "changed to the passing state as I typed this" -- the timeout expiring
  # mid-verdict, read as a fault in a bench that was working (2026-08-11).
  # The eyes still judge the walking pad and the aux LED. What the machine can
  # judge is the number underneath them, which is the same evidence and is not
  # subject to anyone counting flashes.
  # ⛔ AND IT DOES NOT NEED SAYING TWICE. This carried a `watch` restating the
  # PASS IF, naming the count the predicate wants, and explaining what to tick
  # on the Mac dev panel -- printed at a person standing at the rig, where none
  # of it applied. The runner prints `want BEATS between 19 and 22` and `got
  # BEATS = 20` on the line above the verdict prompt, so the number was already
  # on screen from the only source that cannot drift from the predicate.
  {'check': {'kind': 'print', 'name': 'BEATS', 'min': 19, 'max': 22}}),
 ('Beat row wrapping',
  'PASS IF: The white pad reaches the eighth pad and the next beat is back to the first -- with no gap and no stray light anywhere else.',
  [],
  {'do': 'Watch one wrap go by.'}),
 ('Beat row at 240 BPM',
  'PASS IF: The white pad moves twice as fast and keeps an even step. A visible swing is the failure.',
  [('240', 'tempo')],
  # ⛔ THE SWING IS FIXED AND THIS STEP WAS STILL EXCUSING IT. The frame clock
  # ran at 10 Hz once and a 250 ms beat does not divide into 100 ms, so the row
  # swung +/-50 ms at this tempo -- which is why the clock was raised to 50 Hz
  # (ref/module/display.md, verified). At 20 ms boundaries there is nothing to
  # see. So the old text asked a person to accept the symptom of a bug that had
  # already been repaired, and would have passed just as readily if it came
  # back. ⚠️ A STEP THAT EXCUSES A FAILURE MODE CANNOT DETECT IT.
  # ⛔ THE BEATS CLAIM WENT BECAUSE NOTHING SHOWED IT. A counter reaches Pd's
  # console and the runner only ever displays one through a predicate, so these
  # two steps asked a person to check a number that never appeared anywhere. The
  # generator refuses a step whose predicate names a number its prose omits -- it
  # cannot catch the reverse, which is this. The rate claim is gate-owned anyway:
  # tempo-assert counts 24 PPQN at two tempos and the ratio between them. What is
  # left here is the visible beat row, which is what a bench is for.
  ),
 ('Back to 120 and stopped',
  'PASS IF: The beat row goes back to two a second at once and the pad keeps walking after the stop. The change is a snap and not a slide.',
  [('120', 'tempo'), ('bang', 'stop')],
  # ⚠️ "SLOWS BACK" READ AS GRADUAL AND IT IS NOT. The row follows c_clock and a
  # new tempo takes effect on the next tick -- the only thing on this rig that
  # slides is the SP-404 chasing an external clock, which is a fact about the
  # 404 rather than about anything here. Read from the rig as a possible fault
  # (2026-08-11) and it was correct behaviour.
  ),
 ('Pads and releases',
  'PASS IF: Every pad you press reports pad-NN on the OLED with its velocity. Releasing it reports the same name with a velocity of 0 instead. Numbering runs from 11 at the bottom left to 88 at the top right. Pressure on a held pad reports nothing and that is correct.',
  [],
  {'do': 'Press pads and release them.'}),
 ('Ring buttons',
  'PASS IF: Each ring button reports lp-cc-NN on the OLED. The top left corner reads 90 and the bottom row runs from 101 to 108 in order. One button stays dark and reports nothing -- index 0 -- SETUP.',
  [],
  {'do': 'Press the ring buttons, including the top left corner and the bottom row.'}),
 ('Transport keys change mode',
  'PASS IF: Each of the six keys moves the bright lamp to its own position.',
  [],
  {'do': 'Press each of the six nanoKONTROL transport keys.'}),
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
  [('compose mode-1', 'mode')],
  # ⚠️ THE PREDICATE READS err AND THE EYES READ THE GRID, and neither covers the
  # other. c_presence publishes the warn; g_grid going dark is m_launchpad
  # dropping ownership two boxes further on, and no bus carries "the grid stopped
  # painting".
  # ⚠️ wait 12 IS LOAD-BEARING. The warn is three missed ticks behind the unplug
  # -- up to 8 s at the shipped 2000 ms tick -- and the runner's default drain is
  # 0.4 s, which would miss it on entirely correct hardware.
  # ⛔ IT SETS COMPOSE ITSELF, AND WITHOUT THAT THE STEP IS UNJUDGEABLE. u_err
  # shows every error in compose and only `fail` in perform -- so a warn is
  # correctly INVISIBLE on the OLED in perform. The step before this one asks a
  # person to press all six transport keys, which leaves the rig on mode-6 and
  # therefore in perform, and this step then asked them to look for an alert the
  # instrument was right to suppress. The bus carried it and the eyes did not,
  # which is exactly the disagreement the runner records both halves of.
  {'do': 'Press enter first, then unplug the Launchpad USB and leave it out.',
   'wait': 20,
   'check': {'kind': 'bus', 'bus': 'ERR', 'has': ['warn m_launchpad']}}),
 ('Hot-swap -- absent at load',
  'PASS IF: The grid ends up lit with one bright lamp on the top row. Only where it settles is the test -- what the Launchpad does on the way back is its own. The beat row runs at the tempo restored from knobs.txt rather than the one the earlier steps set.',
  [],
  # ⚠️ 60 SECONDS AND NOT 10. A replug is routinely missed by the FIRST re-wire
  # because the device is still enumerating -- the Launchpad used six of its eight
  # attempts on the bench, item 277 -- and the eight are spread over seventy
  # seconds. Anything under about 50 s fails intermittently on correct code.
  {'do': 'Plug the Launchpad back in and wait up to 60 seconds without touching anything.',
   'reload': True,
   'need': ['The Launchpad still unplugged from the last step.']}),

 # ⛔ THE THIRD HOT-SWAP CASE -- see the nanoKONTROL bench for why the two above
 # are not it. ⚠️ IT SITS BEFORE THE PANIC DELIBERATELY: the panic hands the
 # surface back and nothing after it can check the grid.
 ('Hot-swap -- unplugged and plugged back in',
  'PASS IF: The grid lights again and the top row shows one bright lamp.',
  [],
  # ⚠️ THE GRID COMING BACK IS THE WHOLE ORACLE, and it is a stronger one than it
  # looks: the surface only paints when m_launchpad owns it AND the device is in
  # Programmer Mode, so a lit grid says presence re-wired the port and re-asserted
  # the mode (item 276). A dark grid after sixty seconds is the failure.
  {'do': 'Press enter first. Unplug the Launchpad USB and count to fifteen, then '
         'plug it back in and wait up to 60 seconds without touching anything.'}),
 # ⛔ THESE THREE ASSERTED BEHAVIOUR THAT WAS DELIBERATELY REMOVED, and the patch
 # says so in capitals: m_launchpad's comment reads "PANIC USED TO COME IN HERE
 # TOO, AND IT WAS WRONG ... DO NOT WIRE r panic BACK IN". Handing the surface
 # back set want 0, the watchdog stopped re-asserting Programmer Mode, and the
 # grid stayed dead until a reload -- at the one moment you most need the
 # instrument. Worse, in Live Mode the device floods MIDI port 1 with clock and
 # wire.sh connects that port to Pd's Midi-In 1, so a panic also buried Cut It's
 # primary MIDI input. Item 250. display-assert has asserted the current
 # behaviour all along -- "⛔ the grid SURVIVES a panic -- it must keep painting"
 # -- so the gate and the bench were testing opposite claims and only the bench
 # could be wrong.
 ('Panic keeps the surface',
  'PASS IF: The grid keeps painting and the Launchpad stays in Programmer Mode. Its own display does not come back.',
  [('bang', 'panic')]),
 ('The grid still answers after a panic',
  'PASS IF: The bright lamp moves to the first position -- the panic silenced notes and did not surrender the surface.',
  [('compose mode-1', 'mode')]),
 ('Pads still reach the OLED after a panic',
  'PASS IF: A pad press still reports pad-NN on the OLED.',
  [],
  {'do': 'Press a pad.'}),
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
  'PASS IF: The bottom line of the phone reads ok rather than NO-LINK.',
  [('compose mode-1', 'mode')],
  # ⚠️ EVERY STEP BELOW DEPENDS ON THIS ONE, so the consequence of a NO-LINK is a
  # precondition rather than something to read in a PASS IF.
  {'need': ['PdParty open on the CutItRemote scene and on the same network. '
            'A NO-LINK here means nothing below can be judged.']}),
 ('One parameter',
  'PASS IF: The top line reads chop-size and the big number reads 43 on its own. The unit is not drawn and that is correct.',
  [('chop-size 43 %', 'disp')],
  # ⚠️ THE MAC RUN IS A MIRROR AND ANSWERS A DIFFERENT QUESTION FROM THE DEVICE.
  # With u_net repointed at localhost the datagrams are readable here, so what
  # u_net FILTERS can be judged with no phone at all. What no Mac can judge is
  # what the PHONE then draws -- so the device run keeps its human verdict.
  # ⛔ AND IT DID NOT, BECAUSE THIS SAID `targets: ('mac',)` -- which skips the
  # whole STEP off the Mac, so the sentence above was false for as long as it
  # had been written and this step was never judged on the rig by anyone. The
  # runner now skips the PREDICATE where the mirror is absent and asks the
  # person, which is what that comment always described.
  {'check': {'kind': 'osc', 'addr': '/cutit/param', 'has': ['chop-size', '43']}}),
 ('A second parameter',
  'PASS IF: The top line changes to grain and the number to 12 with it.',
  [('grain 12', 'disp')]),
 ('The status line',
  'PASS IF: The third line reads 128-bpm and the parameter name and number above it do not change. u_tempo overwriting it with the real BPM at the next transport event is correct.',
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
  # ⛔ AND IT CARRIED `targets: ('mac',)` TOO -- see step 2. Skipped whole on the
  # device, which is the target whose eyes can answer it.
  {'check': {'kind': 'all', 'of': [
       {'kind': 'osc', 'addr': '/cutit/hb', 'has': []},
       {'kind': 'osc', 'addr': '/cutit/param', 'has_not': ['in-l', 'in-r']}]}}),
 ('Grid vocabulary must not appear',
  'PASS IF: Nothing on the phone changes. The Launchpad going modal is correct and the next step clears it.',
  [('grid modal 45', 'disp')]),
 ('Clearing the grid',
  'PASS IF: The Launchpad returns to its home layout and the phone does not move.',
  [('grid modal-off', 'disp')]),
 ('The aux LED',
  'PASS IF: The aux LED goes green and the phone does not move.',
  [('led running', 'disp')]),
 ('Fast fader sweep',
  'PASS IF: The phone tracks the fader while it moves and settles on the value you stopped at. A number left over from the middle of the sweep is the failure.',
  [],
  {'do': 'Sweep a nanoKONTROL fader as fast as you can. Two at once if you have the fingers -- both must settle.'}),
 ('Link lost',
  'PASS IF: A bordered box reads warn then u_net then net-link-down. Nothing else on the Organelle changes.',
  # ⛔ IT ASKED FOR THE ABSENCE OF AN AUDIO GLITCH AND THERE IS NO AUDIO. v0.4 is
  # the sound -- no effect stage exists yet -- so nobody could hear a glitch or
  # its absence and the clause was unjudgeable. Put it back when there is
  # something to hear.
  #
  # ⛔ AND IT ASKED FOR NO ERROR ON THE OLED, WHICH IS THE OPPOSITE OF WHAT
  # CLOSING PdParty DOES. u_net's watchdog watches a SOCKET, and the socket dies
  # the moment nothing is listening on the phone's port -- so `warn u_net
  # net-link-down` IS this step's action working. ref/device/phone.md says so
  # under its own heading, and it is the most common line in the error log by a
  # wide margin. Step 1 leaves the rig in compose, where u_err shows every
  # error, so the warn could not even be suppressed: the step could never pass
  # on the device. Failed on the rig 2026-08-11 against a working instrument.
  #
  # ⚠️ THE WARN IS SENT ONCE PER LOAD -- u_net's $0-warngate closes behind it,
  # so a phone switched off does not warn every five seconds for the rest of the
  # set. Every device bench run relaunches Pd, so a fresh run always sees it;
  # a second link loss inside one load does not. That belongs in `do`, which is
  # free to change, and not in the PASS IF, which would stale the verdict.
  [],
  {'do': 'Close PdParty on the phone and count to ten. u_net warns once per load, so this has to be the first time the link has dropped since the run started.'}),
 ('Link recovers',
  'PASS IF: The phone starts updating again within about five seconds and you touched nothing on the Organelle.',
  [],
  {'do': 'Reopen PdParty on the phone. Touch nothing on the Organelle.'}),
 # ⚠️ THE FOUR BUTTONS ARE APPENDED RATHER THAN SLOTTED IN, so steps 1 to 14 keep
 # the numbers every recorded verdict and test/README.md refer to.
 ('The re-wire button',
  'PASS IF: The small lamp beside the button flashes. Nothing else on the Organelle changes.',
  [],
  {'do': 'Tap re-wire on the phone.',
   # ⛔ THE LAMP IS THE ONLY EVIDENCE THERE IS, which is why this step exists at
   # all. The lamp is lit by the Organelle's answer rather than by your finger, so
   # a flash means the datagram arrived and the command was accepted.
   'need': ['PdParty OSC send host and port pointed at the Organelle, port 9001. '
            'Without it every button below is silent and nothing says so.']}),
 # ⛔ THERE IS NO STEP HERE ASSERTING THAT THE FORK REACHED THE LOG, and there was
 # one for about an hour. It read "run tools/fetch-errors.sh and read the tail",
 # which is the instruction a state step had already been rewritten to remove --
 # and presence-assert.sh proves the same claim headlessly, exactly once, in a
 # window where nothing else can fork. A bench step that duplicates a gate is a
 # bench step that costs a person time for nothing.
 ('The clear-alert button',
  'PASS IF: The fourth line goes back to none on the left and a dash on the right. The lamp beside the button flashes.',
  [],
  {'do': 'Tap clear-alert on the phone. Step 7 left a fail showing there -- if the row is already empty raise one first.'}),
 ('The Volca test note',
  'PASS IF: The Volca sounds one short note. The lamp beside the button flashes.',
  [],
  {'do': 'Tap test-volca on the phone and listen.'}),
 ('The SP-404 test note',
  'PASS IF: The SP-404 plays pad A1. The lamp beside the button flashes.',
  [],
  {'do': 'Tap test-404 on the phone and listen.'}),
]

STEPS_STATE = [
 ('Restored mode at boot',
  'PASS IF: The Launchpad top row shows exactly one lit mode lamp -- on mode-1 for a fresh install and wherever you left it for a restored one. A dark grid means nothing below can be read.',
  [],
  {'do': 'Look at the Launchpad top row. Press nothing.'}),
 ('Change the mode',
  'PASS IF: The lit lamp moves to the fourth position. Nothing else is visible yet and that is correct.',
  [],
  {'do': 'Press transport key 4 on the nanoKONTROL.'}),
 ('The change reached the disk',
  'PASS IF: Cut-it-auto.txt reads mode perform mode-4. The file is the only evidence -- nothing on the instrument shows it. The old mode still being there is the failure.',
  [],
  # ⛔ THIS STEP USED TO INSTRUCT A PERSON TO RUN A SHELL COMMAND AND READ THE
  # OUTPUT. The file is the only evidence there is -- nothing on the instrument
  # displays what has been saved, deliberately -- so the runner fetches it and
  # compares the string, which is exactly what the person was doing by eye.
  # ⛔ NO `do`, AND THAT IS WHAT MAKES THE [HANDS] TAG TRUE. A `do` reading
  # "nothing to do here" marked this step as wanting fingers when the runner
  # does all of it.
  {'targets': ('device', 'paper'),
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
  # ⛔ THIS STEP REWRITES knobs.txt, AND TWO OTHER BENCHES REST ON WHAT IS IN IT.
  # mother uses Save for the four knob positions, so EVERY Save creates knobs.txt
  # from where the knobs physically are (item 139) -- and midi 1 asserts the
  # footer reads 57 BPM at boot while tempo 2 needs a knob saved off the rail to
  # reach the held branch of parameter pickup at all. Saving with knob 1
  # somewhere else silently destroys both preconditions. ⚠️ AND NEITHER VERDICT
  # WOULD GO STALE: knobs.txt lives on the device and is in no bench's DEPS, so
  # both would stay green over a rig that could no longer produce them. Fresh
  # forever is worse than stale forever, because it is believed.
  {'do': 'Press Storage then Save on the Organelle. Storage is a top-level menu, not a System submenu.',
   'need': ['Knob 1 parked where the footer reads 57 BPM. Every Save rewrites '
            'knobs.txt from the physical knobs, and midi 1 and tempo 2 both '
            'assert that restored value.'],
   'targets': ('device', 'paper'),
   'check': {'kind': 'file',
             'path': 'device-state/cut-it-manual.txt',
             'remote': '/sdcard/cut-it-state/cut-it-manual.txt',
             'newer_than': 'step-start'}}),
 ('Survives a power cycle',
  'PASS IF: The same mode lamp is lit as before the power cycle.',
  [],
  # ⚠️ LAST IN A SESSION, and the reason is not about this bench: a power cycle
  # resets the wifi fault uptime clock and that fault needs about three hours to
  # reappear. That is a scheduling constraint on the whole run.
  {'do': 'Power cycle the Organelle and wait for it to come back.',
   'need': ['Every other bench already run. This power cycle resets the wifi '
            'fault uptime clock.']}),
]


# ⛔ THIS BENCH IS PAPER, AND IT HAS TO BE. Step 3 holds CC 90, which reloads the
# patch -- and targets.device launches the bench as a THIRD PATCH inside the
# instrument's own Pd, so /loadPatch kills the bench along with everything else.
# A driven bench would end there with every later step stranded. With no actions,
# no `reload` and only offline predicates the runner launches nothing at all: the
# person runs these against the real deployed instrument, and the one thing under
# test cannot take the runner down with it.
#
# ⚠️ SO THERE IS NOTHING TO DRIVE AND NOTHING TO DRAIN. `press enter first` and
# `wait` are meaningless here -- they exist for predicates whose traffic a person
# makes, and every predicate below reads a FILE.
#
# ⛔ STEP 5 LEAVES THE RIG WITH NO PATCH. Step 6 puts it back, and says so in its
# own `need` and `do` rather than trusting the order to be remembered.
STEPS_RECOVER = [
 ('Short press -- panic and nothing more',
  'PASS IF: Everything sounding stops the instant the button goes down -- not when you let go. The whole Launchpad flashes red and clears itself about a second later. The aux LED is red and the footer reads panic. The patch is still running: the grid comes back and the beat row still walks.',
  [],
  {'do': 'Start the transport, play something on the SP-404 so there is a sound to stop, then tap the top left corner button on the Launchpad once and let go straight away.',
   'need': ['The Launchpad lit and in Programmer Mode.',
            'Something audible running -- the 404 sequencer is easiest.']}),

 ('Short press -- the Volca stops too',
  'PASS IF: The Volca stops sequencing. Before this was built its transport never heard anything at all -- it kept running through a panic and the mixer could only mute it.',
  [],
  # 📄 KORG'S DOCUMENTATION, NOT A MEASUREMENT. The Volca honours Start/Stop only
  # when its own MIDI Clock src is Auto; set to Internal it ignores them and a
  # perfectly correct patch looks broken. That is why the setting is a `need`
  # rather than something to discover halfway through. ref/device/volca.md.
  # ⛔ AND THE CLOCK IS STILL NOT SENT THERE. Only the panic STOP reaches port 4
  # -- the Volca cannot sync to the master tempo and this step does not claim it
  # can. Item 279, item 295.
  {'do': 'Set the Volca sequencing on its own, then tap the top left corner button once.',
   'need': ['The Volca powered and its own sequencer running.',
            "The Volca's MIDI Clock src set to Auto. Set to Internal it ignores "
            'Start and Stop entirely and this step cannot pass.']}),

 ('Hold -- the patch reloads and comes back whole',
  'PASS IF: Silence at once. About two seconds later the screen goes through its boot sequence again and the instrument comes back with every device working -- the Launchpad lit and answering and both output devices reachable. A few seconds in a bordered alert reads warn and then u_map and then recovered. Knob 1 moves the tempo on the first touch with no dead sweep.',
  [],
  # ⛔ THIS STEP KILLS ANY BENCH IT IS RUN FROM, which is why this one is paper.
  # ⚠️ THE ALERT IS LATE AND BRIEF. It is deferred to about 4.5 s after the
  # reload -- clear of the boot stages, which would bury it -- and it lasts about
  # two seconds. Watch the screen from the moment the boot sequence ends.
  # ⛔ THE KNOB IS THE OTHER HALF AND IT IS EASY TO SKIP. After an emergency the
  # knobs you are holding are the truth, so the reload deliberately does NOT arm
  # parameter pickup. A knob that needs a sweep to wake up is a failure here even
  # though it is correct behaviour on an ordinary boot.
  {'do': 'Hold the top left corner button for a full two seconds and let go. Then watch the screen, and afterwards turn knob 1 a little.',
   'need': ['A Save done at some point, so knobs.txt exists. Without one '
            'nothing would be held on an ordinary boot either and the last '
            'sentence proves nothing.']}),

 ('...and the breadcrumb was consumed',
  'PASS IF: Cut-it-recover.txt reads none. The instrument wrote it just before the reload and cleared it once it had reported -- so none means the whole cycle completed. Finding the word recover still in there means the report never ran.',
  [],
  {'targets': ('device', 'paper'),
   'check': {'kind': 'file', 'fetch': 'state',
             'path': 'device-state/cut-it-recover.txt',
             'contains': 'none'}}),

 ('Break it deliberately -- a reload that cannot land',
  'PASS IF: Everything goes quiet and then nothing comes back at all. The screen stays dark or frozen and the Launchpad stops answering. That is the failure this is meant to produce.',
  [],
  # ⛔ DESIGN FOR THE FAILURE, BECAUSE IT IS WORSE THAN THE FAULT. If the load
  # does not take there is no patch at all, and a patch cannot report on its own
  # reload because it is dead by then. The breadcrumb is the only thing that
  # survives to say an attempt was made -- and the step after this one is where
  # it gets read.
  {'do': 'Over ssh run: mv "/sdcard/Patches/!/Cut It" "/sdcard/Patches/!/Cut It away" -- then hold the top left corner button for two seconds.',
   'need': ['An ssh session to the Organelle already open. The patch is about '
            'to stop existing, so this is not the moment to go looking for one.',
            'The root filesystem left alone -- the patch lives on /sdcard and '
            'needs no remount.']}),

 ('The breadcrumb survives to explain it',
  'PASS IF: Cut-it-recover.txt still reads recover and a number. Nothing on the instrument could have told you what happened -- it was dead -- so this file is the whole account of it.',
  [],
  {'targets': ('device', 'paper'),
   'check': {'kind': 'file', 'fetch': 'state',
             'path': 'device-state/cut-it-recover.txt',
             'contains': 'recover'}}),

 ('Put it back -- and the safe exit still works',
  'PASS IF: The instrument loads and runs normally again. When you leave it the Launchpad returns to Live Mode -- its pads show a built-in layout and its Setup button responds. A Launchpad still dark and ignoring Setup is the failure.',
  [],
  # ⚠️ THROUGH THE MENU OR /loadPatch, NEVER killall pd. quitting comes from
  # mother rather than from a shell signal, so a killed Pd skips m_launchpad's
  # safe exit entirely and strands the surface in Programmer Mode -- where the
  # device's own Settings menu is locked out. tools/lp-live.sh rescues one, but
  # the point of this step is that it should not be needed. Item 96.
  # ⛔ THIS STEP RESTORES THE RIG. Step 5 left it with no patch at all, and a
  # step sets up its own preconditions -- including the ones the step before it
  # destroyed.
  {'do': 'Over ssh run: mv "/sdcard/Patches/!/Cut It away" "/sdcard/Patches/!/Cut It" -- then load Cut It from the Organelle menu, let it settle, and leave it by selecting a different patch.',
   'need': ['The renamed folder from the step before, still renamed.']}),
]

STEPS_MIDI = [
 ('Restored tempo at boot',
  'PASS IF: The footer reads 57 BPM and not 120 BPM. The lit mode lamp is wherever you left it -- note which one it is.',
  [],
  # ⚠️ ONLY ON THE DEVICE. 57 comes from knobs.txt, which mother reads at boot
  # and which no Mac has -- on a Mac this legitimately reads 120 and the
  # predicate would be asserting the absence of hardware.
  {'targets': ('device',),
   'check': {'kind': 'oled', 'has': ['57'], 'has_not': ['120']}}),

 ('Get to mode 1',
  'PASS IF: The lit lamp moves to the first position. Nothing below works until it does.',
  [],
  {'do': 'Press transport key 1 on the nanoKONTROL.'}),

 ('SP-404 pad 1',
  'PASS IF: The OLED shows sp-bank 1 and sp-pad 1 together.',
  [],
  # ⚠️ THE 404 LIGHTS ONLY THE BANK IT IS ON, so which bank is selected is not
  # readable at a glance and every 404 step says it out loud instead.
  {'do': 'Press enter first. Check which bank the 404 is lit on -- it lights only the selected one -- then select bank A and press pad 1.'}),

 ('SP-404 pad 5',
  'PASS IF: sp-pad reads 5 on the OLED. Anything else is the failure.',
  [],
  # ⛔ THE PAD THAT CATCHES `47 + n`. Under the old formula pad 5 reads 13, and
  # 13 is a plausible-looking number on an OLED -- which is how that bug lived
  # in this repo's own docs for months. A person reads two digits; this reads
  # the bus.
  #
  # ⛔ `wait` IS THE OTHER HALF OF "PRESS ENTER FIRST", AND WITHOUT IT THE
  # INSTRUCTION FIXES NOTHING. The window opens at GO and closes SETTLE later --
  # 0.4 s, four tenths of a second -- so a step that asks a person to press
  # enter and THEN reach for a pad judges an empty window however correctly
  # worded it is. Measured on the rig 2026-08-11: this window held seven
  # level-meter rows and nothing else, 6 held four, and 7 held none at all,
  # while a person passed all three by eye. Two runs reported AUTO FAIL against
  # a working 404 before the missing half was found. Every pad step that carries
  # a predicate now holds the window open long enough for a hand to move.
  {'do': 'Press enter first. Check the 404 is lit on bank A -- it lights only the selected one -- then press pad 5. There are about ten seconds to do it.',
   'wait': 10,
   'check': {'kind': 'bus', 'bus': 'DISP', 'has': ['sp-pad 5']}}),

 ('All sixteen pads',
  'PASS IF: sp-pad counts 1 2 3 up to 16 in step with your finger while sp-bank stays at 1 throughout. A run that counts 1 2 3 4 and then jumps is the failure.',
  [],
  {'do': 'Press enter first. Then press pads 1 through 16 in order on bank A.'}),

 ('Bank B',
  'PASS IF: sp-pad still reads 1 but sp-bank changes from 1 to 2 as you switch banks.',
  [],
  # ⛔ THE WINDOW HAS TO OUTLAST THE HAND -- see step 4.
  {'do': 'Press enter first. Then select bank B and press pad 1. The 404 lights only the bank it is on. There are about ten seconds to do it.',
   'wait': 10,
   'check': {'kind': 'bus', 'bus': 'DISP', 'has': ['sp-pad 1', 'sp-bank 2']}}),

 ('A release is not a press',
  'PASS IF: The sp-pad and sp-bank rows update on the press and neither updates again on the release. Exactly one sp-pad row per hit -- two is the failure. A third row named for the pad itself -- sp-b3 for bank b pad 3 -- carries the velocity and does change on the release. That row is correct and belongs to u_map.',
  [],
  # ⛔ EXACTLY ONE sp-pad ROW FOR ONE HIT. Two means the velocity test on the
  # disp side has gone and every pad is reporting itself twice -- which on a
  # screen that redraws looks like nothing at all.
  # ⚠️ AND IT CARRIED A `watch` THAT SAID THE PASS IF AGAIN IN OTHER WORDS.
  # A second copy of a sentence is a second copy free to drift, and this one
  # was displayed INSTEAD of the sentence the verdict is recorded against.
  # ⛔ THE THIRD ROW IS NAMED NOW BECAUSE THE SCREEN HAS ALWAYS HAD THREE. The
  # step described two, so a person reading it correctly reported a failure --
  # "only sp-b3 updates when I lift my finger off the pad", which is exactly
  # what is supposed to happen. The per-pad name comes from u_map's generic
  # echo and carries the control's VALUE, so a release is velocity 0 and the row
  # changes (ref/device/sp404.md, item 283). A step that describes less of the
  # screen than the screen shows makes correct behaviour read as a fault.
  # ⛔ THE WINDOW HAS TO OUTLAST THE HAND -- see step 4. This one held NOTHING
  # AT ALL on the rig, which is what an exact count of 1 reads as a fail against.
  {'do': 'Press enter first. Then press and hold any pad and let go. There are about ten seconds to do it -- one hit only.',
   'wait': 10,
   'check': {'kind': 'bus-count', 'bus': 'DISP', 'match': 'sp-pad', 'n': 1}}),

 ('Fader 1 in mode 1',
  'PASS IF: The Volca tone changes as you move it.',
  [],
  {'do': 'In mode 1 move fader 1 on the nanoKONTROL.',
   'need': ['The Volca audible. It transmits nothing so this step and the two '
            'after it are judged by ear with no readback of any kind.']}),

 ('Fader 1 in mode 4',
  'PASS IF: The Volca does not change -- no change is the pass. The OLED still shows the fader moving and that is correct.',
  [],
  {'do': 'Press transport key 4 then move fader 1.'}),

 ('Fader 1 back in mode 1',
  'PASS IF: The Volca responds again. Still silent means the mode did not change back -- check the lit lamp.',
  [],
  {'do': 'Press transport key 1 then move fader 1 again.'}),

 ('Tempo from knob 1',
  'PASS IF: The footer BPM follows the knob over roughly 10 to 500 BPM once the knob has crossed the restored value. Nothing at all happens before it crosses.',
  [],
  {'do': 'Sweep knob 1 all the way and back.'}),

 ('Transport from the aux button',
  'PASS IF: The aux LED goes green on the first press and dark blue on the second.',
  [],
  # ⛔ THE FOOTER CLAIM WENT, FOR THE FOURTH TIME IN THIS SUITE. The 404's own
  # sp-pad rows raise g_oled's param layer and that REPLACES home -- so by this
  # point in the bench the footer is buried under the traffic of the steps
  # above, and it only ever carried the BPM anyway. The aux LED is the readout
  # this step is about and it is on the front panel where nothing covers it.
  {'do': 'Press the aux button twice.'}),

 ('Panic is unbound',
  'PASS IF: The aux LED never turns red however many controls you press.',
  [],
  # ⛔ IT USED TO SAY "Nothing on the rig can raise panic and nothing is meant
  # to", which is a claim about the map with nothing to do and nothing to look
  # at -- read at the rig as "this is not even a test", correctly. The map half
  # is a STATIC fact and map-assert owns it now: no row may name panic as a
  # destination, proved by reading cut-it-map.txt with no Pd at all. What is
  # left here is the half only fingers can answer -- that no control anybody
  # would actually reach for raises it.
  {'do': 'Press every transport key on the nanoKONTROL and every button on the '
         'Organelle. Turn the encoder. Nothing should ever go red.'}),

 # ⛔ HOT-SWAP FOR BOTH OUTPUT DEVICES, AND THE TWO ARE NOT ALIKE. The SP-404 is
 # `active` -- it answers a device inquiry, so it has a last-heard clock and can
 # be declared lost. The Volca is `none`: it transmits nothing at all, can never
 # be polled, and its recovery is PARASITIC on a detectable device being missing
 # in the same moment. Step 7 below is what that costs.
 ('Hot-swap -- SP-404 unplugged',
  'PASS IF: A bordered alert on the OLED reads warn then m_404 then device-lost.',
  [],
  # ⚠️ wait 20 IS LOAD-BEARING -- the warn is three missed ticks behind the
  # unplug, up to 8 s, and the runner's default drain is 0.4 s.
  #
  # ⛔ AND THE ALERT IS BRIEF AND LATE, SO THE STEP HAS TO SAY WHERE TO LOOK AND
  # WHEN. It told a person to pull a cable and judge an alert that fires about
  # eight seconds later and clears itself about two seconds after that -- while
  # their hands and eyes were on the cable. Reported from the rig as "no alert
  # on the OLED" 2026-08-11, and /sdcard/cut-it-err.log has
  # `332000 warn m_404 device-lost` at exactly that moment. ⚠️ THE STEP AFTER
  # IT SHOWED THE WARN and this one did not, off the same physical action, which
  # is what named the cause: step 16 has you counting to fifteen with the cable
  # out, so you are still watching when it lands.
  #
  # ⛔ AND A FAILURE HERE INVITES THE ONE ACTION THAT DESTROYS STEP 15. Seeing no
  # alert, a person plugs the 404 back in to check it still works -- which it
  # does -- and 15 then reloads with the device PRESENT and tests nothing. Same
  # sentence as step 17, which has said so all along.
  {'do': 'Press enter first, then unplug the SP-404 and watch the OLED. The alert arrives about eight seconds after the cable is out and clears itself about two seconds later. Leave it unplugged when you answer -- the next step loads without it.',
   'wait': 20,
   'check': {'kind': 'bus', 'bus': 'ERR', 'has': ['warn m_404']}}),
 ('Hot-swap -- SP-404 absent at load',
  'PASS IF: The OLED shows an sp-pad row.',
  [],
  # ⚠️ A PAD IS THE ORACLE AND NOT THE ABSENCE OF A WARN. The 404's detection is
  # proven by its silence at boot -- it can only stay quiet by matching byte 65 on
  # port 3 -- but silence cannot tell a working subscription from a dead one. A
  # pad under a finger can.
  # ⛔ `need` DESCRIBES THE STATE THE RELOAD ALREADY PUT THE RIG IN, NOT A THING
  # TO GO AND DO. It read "The SP-404 still unplugged from the last step" directly
  # above a `do` reading "Plug it back in", and the two land on screen together
  # after the reload has happened -- so they read as a contradiction and were
  # reported as one. NEED is what you must HAVE, DO is what you must do.
  {'do': 'Plug it back in, wait 60 seconds, then press pad 1 on bank A.',
   'reload': True,
   'need': ['The SP-404 unplugged, and the patch just reloaded without it. '
            'The runner has already done the reload -- that absence is what '
            'this step tests.']}),

 # ⛔ THE THIRD HOT-SWAP CASE for the 404 -- see the nanoKONTROL bench. The Volca
 # step below already has its own, because a `none` device can only be recovered
 # this way (item 275), which is why this gap read as covered for so long.
 ('Hot-swap -- SP-404 unplugged and plugged back in',
  'PASS IF: The OLED shows an sp-pad row again.',
  [],
  {'do': 'Press enter first. Unplug the SP-404 and count to fifteen, then plug '
         'it back in and wait up to 60 seconds before pressing pad 1 on bank A.'}),

 # ⛔ THE ORACLE IS THE FADER CHANGING THE SOUND \, NEVER THE VOLCA MAKING ONE.
 # Both of these steps used to read "PASS IF the Volca sounds -- BY EAR" \, which
 # is satisfied by a Volca with no MIDI cable in it at all: it is a synth with its
 # own keyboard and it sounds whenever it is powered. Measured on the rig
 # 2026-08-10 -- the interface was enumerated and completely unsubscribed for two
 # minutes and the keys still played. ref/device/volca.md said so before the step
 # was written: its only mapping is a CC that needs the device ALREADY SOUNDING.
 # ⚠️ THE TEXT CAME VERBATIM FROM THE PLAN and was checked against the punctuation
 # rules rather than against what this device can demonstrate.
 ('Hot-swap -- Volca unplugged and plugged back in',
  'PASS IF: Holding a Volca key and sweeping slider 1 changes the sound -- by ear.',
  [],
  # ⛔ THE VOLCA USED TO NEED A SECOND DEVICE PULLED WITH IT, AND NO LONGER DOES.
  # It registers `none` -- it transmits nothing, can never be polled, and so has
  # no clock to run out. Its recovery rode a DETECTABLE device being missing at
  # the same moment, which is why this step pulled the nanoKONTROL too (item
  # 275). u_present's re-wire heartbeat closed that: wire-watch.sh fires every
  # eight ticks whatever is or is not lost, hashes the client names, and re-wires
  # when they change. So the Volca alone is now the honest test, and it is the
  # one that exercises the heartbeat -- pulling a second device would go back
  # through the loss path and prove nothing about it.
  # ⚠️ THIRTY SECONDS COVERS THE HEARTBEAT: u_root passes [u_present 4000 2000 33
  # 8], so the watch interval is eight 2000 ms ticks -- 16 s -- plus enumeration.
  # ⚠️ AND IT IS BY EAR AND ALWAYS WILL BE. The Volca transmits nothing, so there
  # is no readback and no predicate is possible -- see ref/device/volca.md.
  # ⛔ IT HAS TO COME BACK OUT AT THE END, and it did not say so -- the step
  # after this one loads the patch with the Volca ABSENT, and the runner does
  # that reload the moment this verdict is given. So its `need` read "still
  # unplugged from the last step" against a step that had just told you to plug
  # it in. Reported from the rig on 2026-08-11.
  {'do': 'Press enter first. Unplug the Volca interface alone and count to fifteen, then plug it back in and wait up to 30 seconds before sweeping slider 1 while holding a Volca key. Unplug it again before you answer -- the next step loads without it.',
   'need': ['Mode 1. Slider 1 is the only control bound to the Volca.']}),
 ('Hot-swap -- Volca absent at load',
  'PASS IF: Holding a Volca key and sweeping slider 1 changes the sound -- by ear. Sweep it up -- slider 1 is velocity.',
  [],
  # ⛔ ABSENT AT LOAD IS STILL ITS OWN CASE, and for a `none` device it is the
  # likelier one in a room: you power the rig up and then plug the Volca in.
  # Nothing is wrong from the instrument's point of view, so nothing warns -- and
  # before the heartbeat the remedy was a reload, or unplugging a detectable
  # device to trick the recovery into running, which nobody would guess. Item
  # 285, ✅ seen on the rig after 1 day 21 hours up.
  {'do': 'Plug the Volca interface in, wait up to 30 seconds, then hold a Volca key and sweep slider 1.',
   'reload': True,
   'need': ['The Volca interface still unplugged from the last step.',
            'Mode 1. Slider 1 is the only control bound to the Volca.']}),
]
