"""Step tables for the benches -- the data half of bench-gen.py.

Each step is (title, pass_if, [(message, bus), ...]) and optionally a fourth
element, a dict -- see norm() below.

A step says what to see and what to do, nothing else: why it happens is on the
module's ref/ page. Capitals mean literally on a screen or a label, never
emphasis; bench-gen.py's lint_caps holds the literal set. bench-verify.py diffs
the generated benches' text against these tables.

A `title` or `pass_if` takes no comma, no semicolon and no sentence ending on a
bare number (the gate skill, Benches); bench-gen.py asserts it. `need` and `do`
never reach a .pd, so they take ordinary commas.
"""
import re

# ---------------------------------------------------------------------------
# One window for the bench's [del], its header prose and test/runner/'s
# predicate window.
WINDOW_MS = 10000

# A step that sends to a bus ending in this arms a timed count: the prompt says
# to wait for the printed number, and the runner holds its window open for
# WINDOW_MS instead of judging at once.
MEASURE_SUFFIX = "-zero"

# ---------------------------------------------------------------------------
# The console protocol, both halves: bench-gen.py's format strings and
# test/runner/'s regexes, kept together so runner-assert can check each regex
# against what its format writes. A drift reads as a stall on a working bench.
# The regexes are unanchored because a bare [print] puts `print: ` in front.
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

# `where` is the one question the runner can ask. GO is a single UDP datagram,
# so a lost GO and a dead patch are the same silence; the answer names the step
# and the phase, which says whether the last GO landed. A [print] prefix rather
# than a format string, because the numbers are live and the generator escapes
# every `$`.
SAY_WHERE = "bench-at"
RE_WHERE = re.compile(r"\bbench-at: (\d+) (\d+)\b")


def norm(step):
    """A step is 3 or 4 long -> (title, pass_if, actions, meta).

    The fourth element is the runner's -- what a person needs (`need`, `do`)
    and what the program needs (`check`, `wait`, `targets` ...) -- and never
    reaches a .pd, where it would face the comma and semicolon split. So
    bench-verify.py diffs three fields.
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
  # Exact rows: g_oled draws a parameter as a name row and a value row, so the
  # stale unit is a value row reading `12 %`. A screen-wide `no %` fails on the
  # previous step's chop-size 43 %, still on screen for about 1.3 s.
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
  # Not held: re-firing `modal stuck` every 0.8 s would restart the 30 s TTL
  # that the next step waits out.
  {'hold': False}),
 ('Modal safety timeout -- the wait',
  'PASS IF: The screen went back to the meters on its own with nothing touched.',
  [],
  {'do': 'Wait 30 seconds without touching anything.'}),
 # Judged with a device actually gone: the panel alone can still stop the rig.
 ('Shifted stop with the nano unplugged',
  'PASS IF: The clock stops. The beat row on the Launchpad stops walking.',
  [],
  {'do': 'Hold the aux button and press the middle key.',
   'need': ['The nanoKONTROL unplugged.',
            'The clock running -- press PLAY on the nano before unplugging it.']}),
 # oled-assert proves the roster's words and order; whether five 8px rows read
 # at arm's length, and the 21-character m_launchpad unchecked line is not
 # clipped, is a person's call (ref/module/display.md).
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
  "PASS IF: Each control draws one row named for itself -- slider-1 to slider-9 then knob-1 to knob-9 -- unless the current mode maps it. In mode 1 slider-1 reads volca-cc41 and no slider-1 row appears. None reports another's name.",
  [],
  # One row per control, and it is u_map's (item 317): an unmapped control draws
  # its own raw row, a mapped one its destination's. slider-1 is volca-cc 41 in
  # mode 1, so a slider-1 row beside volca-cc41 there is a double row.
  {'do': 'Sweep every slider and every knob. Watch slider 9 and knob 1 especially.'}),
 ('Several faders at once',
  'PASS IF: Two faders draw as stacked pairs. Three to five draw as small lines. Nine draws the five you touched first and refuses the rest. No row reshuffles while you are moving them.',
  [],
  {'do': 'Move two faders at once, then three, then all nine.'}),
 ('Every button and transport key',
  'PASS IF: All 18 buttons name themselves on press and nothing on release. REW FF LOOP and REC report xport-1 xport-3 xport-4 and xport-6 as raw rows. PLAY starts the clock and STOP stops it and neither draws a row. No toggle.',
  [],
  # REW FF LOOP and REC miss the table and draw raw rows (item 242: a control
  # that does nothing must say so). PLAY and STOP map to start and stop, button
  # destinations that draw no row, and m_nano posts no row of its own (item 317).
  {'do': 'Press every button, then all six transport keys.'}),

 # Hot-swap, three cases (item 235): lost mid-session, absent at load, and out
 # and back in. Only a device that has answered can be lost -- c_presence's warn
 # is armed by a reply -- so absent at load is its own case, and only a fresh
 # load shows it recovered.
 ('Hot-swap -- unplugged mid-session',
  'PASS IF: A bordered alert on the OLED reads warn and then m_nano.',
  [],
  # wait 20: the warn is three missed ticks behind the unplug, up to 8 s, and
  # the runner's default drain is 0.4 s.
  {'do': 'Press enter first, then unplug the nanoKONTROL and leave it out.',
   'wait': 20,
   'check': {'kind': 'bus', 'bus': 'ERR', 'has': ['warn m_nano']}}),
 ('Hot-swap -- absent at load',
  'PASS IF: Slider 1 draws a value row on the OLED.',
  [],
  # 60 s: a replug can miss the first re-wires while the device enumerates (item
  # 277). The slider is the oracle: the nano is passive, so only traffic arriving
  # proves the subscription came back.
  {'do': 'Plug it back in, wait 60 seconds, then move slider 1.',
   'reload': True,
   'need': ['The nanoKONTROL still unplugged from the last step.']}),

 # Between the unplug and the replug on purpose: the warn shows the loss was
 # seen, and this shows you can ask about it afterwards.
 ('Hot-swap -- the diag roster names it',
  'PASS IF: The m_nano line reads gone. The other four lines are unchanged and none of them reads gone.',
  [],
  {'do': 'Hold the aux button and press the lowest key. Check m_launchpad and '
         'm_404 as well as m_nano: pulling one USB cable can knock a bystander '
         'off the bus, so a second line reading gone is worth knowing about '
         'rather than a miss.',
   'need': ['The nanoKONTROL still unplugged from the last step.']}),

 # Out and back in mid-session, as a knocked cable does. Not the absent-at-load
 # path: this arms u_present's counter on the way out and has to land one of the
 # eight re-wires on the way back. Last, so nothing after it needs a cable out.
 ('Hot-swap -- unplugged and plugged back in',
  'PASS IF: Slider 1 draws a value row on the OLED again when you move it.',
  [],
  # Fifteen seconds out, because the loss is three missed ticks behind the
  # unplug; up to 60 s back, as in the step above (item 277).
  {'do': 'Press enter first. Unplug the nanoKONTROL and count to fifteen, then '
         'plug it back in and wait up to 60 seconds before moving slider 1.'}),
]

# No beat-count steps: the c_clock ratio and the clock running on after a stop
# are clock-assert's and tempo-assert's, and the counts appear on no screen. One
# claim judged in two places reports more coverage than exists.
STEPS_TEMPO = [
 ('Resting display at 120 BPM',
  'PASS IF: Two meter bars each with a small gate mark under it and 120-bpm in the footer. The aux LED is dark blue.',
  [('120', 'tempo'), ('bang', 'stop')]),
 ('Knob pickup on the first touch',
  'PASS IF: The row reads bpm 57 (10) -- the position knob 1 was saved at first and where the bench has just moved it to in brackets -- and the footer stays 120-bpm. The tempo is held until the real knob is turned back past where it was saved. If this rig has no knobs.txt the row reads bpm 10 and the footer follows down to 10-bpm instead. The row must never read og-knob-1 and never a raw 0-to-1 decimal.',
  [('120', 'tempo'), ('og-knob-1 0', 'param')],
  # The first number is the saved knob position, not the tempo: u_map draws the
  # held row from the pickup target ([tabread $0-pk-t], x490+10) with the
  # incoming value in the unit field, so a knobs.txt of 0.0957967 draws
  # `bpm 57 (10)`. Branch (a) needs a knob saved off the rail; with 0 0 0 0
  # pickup releases at once and only (b) is reachable.
  #
  # Not held: each re-fire sends a tempo and a knob mapped to tempo, so the
  # footer would walk 120 to 10 and back while being read (six round trips in
  # five seconds on the Mac). [r]epeat still works.
  {'hold': False}),
 ('Knob pickup crosses over',
  'PASS IF: The row reads bpm 500 and about a second later it ages out to show the footer underneath reading 500-bpm. The knob has crossed where it was saved and is live from here on.',
  [('og-knob-1 1', 'param')],
  # The row covers the footer (the param layer replaces home), so the footer is
  # read once the row ages out. One value is sent: one jump, no slide.
  ),
 ('Knob tracking after pickup',
  'PASS IF: The row reads bpm 10 and the footer underneath reads 10-bpm once it ages out. A row still reading 500 means the knob is stuck.',
  [('og-knob-1 0', 'param')]),
 ('Tempo above range',
  'PASS IF: The footer reads 600-bpm and exactly one alert appears -- a bordered box naming u_tempo. The second 5000 is silent.',
  [('5000', 'tempo'), ('5000', 'tempo')],
  # Exactly one: the second 5000 is the same value and must be silent, and
  # "one or more" would pass the bug.
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
  # Start (250) moves the 404's sequencer only with a pattern loaded
  # (ref/device/sp404.md); without one nothing on either device says why. The
  # two steps after this one inherit the state.
  {'need': ['The SP-404 on Pattern Select with a pattern loaded and nothing '
            'playing.']}),
 ('The 404 follows a tempo change',
  "PASS IF: The 404's EXT slides up to 180 rather than snapping and its pattern speeds up to match. The OLED fills with rows named for the pads it plays -- sp-a1 and the like -- and that is correct. Those rows cover the footer so the new tempo is not readable there until the transport stops.",
  [('180', 'tempo')],
  # 180, not 240: the 404 follows only between 40 and 200 BPM
  # (ref/device/sp404.md). No footer claim: the pad rows raise the param layer,
  # which hides it, so `Stop the transport` reads the footer instead.
  ),
 ('Stop the transport',
  'PASS IF: The aux LED goes dark blue and the 404 stops but its screen still reads EXT. Falling back to BPM is the failure. The pad rows stop arriving and the OLED settles back to the meters with 120-bpm in the footer.',
  [('120', 'tempo'), ('bang', 'stop')]),
 ('Panic',
  'PASS IF: The aux LED turns red and the footer reads panic.',
  [('bang', 'panic')]),
 ('Transport from PLAY and STOP',
  'PASS IF: PLAY turns the aux LED green and the 404 starts. STOP turns it dark blue and the 404 stops.',
  [],
  # The aux button is the keyboard's modifier now (item 305); the nano's PLAY
  # and STOP are the transport in every mode.
  {'do': 'Press PLAY on the nanoKONTROL, then STOP.'}),
 ('Knob 1 tempo sweep',
  'PASS IF: The row reads bpm and a number that tracks the knob between 10 and 500 BPM. It never reads og-knob-1 and never a raw 0-to-1 decimal. The 404 follows the sweep.',
  [],
  # No bracketed second number: the knob was released three steps ago and is
  # live. The held format is judged in `Knob pickup on the first touch`.
  {'do': 'Sweep knob 1 all the way and back.'}),
]

STEPS_LAUNCHPAD = [
 ('Resting grid',
  'PASS IF: The left column shows one bright green lamp second from the top and five dim ones around it. The bottom row of pads has a single white pad. Dim means faint and not off. The white pad is already walking and that is correct -- a frozen pad is the failure. Everything else on the surface is dark.',
  [('120', 'tempo'), ('bang', 'stop'), ('compose mode-2', 'mode')],
  # Mode 2, not 1: mode 1 is the drum page, where the beat row gives way.
  ),
 ('Mode lamp 4',
  'PASS IF: The bright lamp moves to the fourth position down and the other five go dim. Nothing else on the grid changes.',
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
 # The steps above judge the painting, off the mode bus; this one judges the
 # selection, off the lamp itself. That the release selects nothing is
 # map-assert's, since a doubled selection looks identical.
 ('Pressing a mode lamp selects it',
  'PASS IF: The bright lamp moves to the pad you pressed and stays there after you let go. The OLED does not change.',
  [],
  {'do': 'Press the third button down the left column, then the second.'}),
 ('Grid vocabulary stays off the OLED',
  'PASS IF: Nothing happens on either surface. In particular no parameter row called grid appears on the OLED.',
  [('grid no-such-thing', 'disp')]),
 ('Modal claims the surface',
  'PASS IF: Every pad and every ring button turns blue including the left column. The mode lamps are covered too. The OLED must not change.',
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
  # The modal-off is this step's own precondition: the step before paints the
  # surface green and only its 30 s timeout clears it, which a person sits out
  # in order and a --from walk does not (bench-gen.py's lint_modal).
  {'check': {'kind': 'print', 'name': 'BEATS', 'min': 19, 'max': 22}}),
 ('Beat row wrapping',
  'PASS IF: The white pad reaches the eighth pad and the next beat is back to the first -- with no gap and no stray light anywhere else.',
  [],
  {'do': 'Watch one wrap go by.'}),
 ('Beat row at 240 BPM',
  'PASS IF: The white pad moves twice as fast and keeps an even step. A visible swing is the failure.',
  [('240', 'tempo')],
  # No swing to excuse: the frame clock runs at 50 Hz (ref/module/display.md),
  # and a step that excuses a failure cannot detect it. The rate is
  # tempo-assert's; a count appears on no screen, so it is not claimed here.
  ),
 ('Back to 120 and stopped',
  'PASS IF: The beat row goes back to two a second at once and the pad keeps walking after the stop. The change is a snap and not a slide.',
  [('120', 'tempo'), ('bang', 'stop')],
  # A snap: the row follows c_clock and a new tempo takes effect on the next
  # tick. Only the SP-404 slides, chasing an external clock.
  ),
 ('Pads and releases',
  'PASS IF: Every pad you press reports pad-NN on the OLED with its velocity. Releasing it reports the same name with a velocity of 0 instead. Numbering runs from 11 at the bottom left to 88 at the top right. Pressing harder on a held pad draws no row of its own -- with aftertouch on or off -- and that is correct.',
  [],
  # Pressure draws no row with aftertouch on or off: u_map exempts a name ending
  # -at, as it exempts the keys (item 318).
  {'do': 'Press pads and release them. Press harder on one you are holding.'}),
 ('Ring buttons',
  'PASS IF: Each ring button reports lp-cc-NN on the OLED except the seven the map binds -- they draw no row. The top left corner raises panic and the top six of the left column move the mode lamp. The bottom row runs from 101 to 108 in order. One button stays dark and reports nothing -- index 0 -- SETUP.',
  [],
  # The rows are u_map's (item 317), so the bound buttons draw none: CC 90 is
  # `recover` and the six mode keys are u_map's own route. The top row is free.
  {'do': 'Press the ring buttons, including the top left corner and the bottom row.'}),
 ('The left column changes mode',
  'PASS IF: Each of the six buttons moves the bright lamp to its own position. The top row moves nothing.',
  [],
  {'do': 'Press each of the top six buttons of the left column, top to bottom. Then press the top row.'}),
 # ⛔ THESE TWO REPLACED THE REPLUG HAZARD STEP, WHICH DESCRIBED A HAZARD THAT NO
 # LONGER EXISTS. It read "the device returns in Live Mode but m_launchpad still
 # believes it owns the surface -- press a few pads and watch pad-NN names appear
 # on the OLED", and closed "Not built yet. See plan-v04.md". Presence drops
 # ownership on the third missed poll and the bounded re-wire brings the device
 # back with Programmer Mode re-asserted -- item 276, verified on the hardware --
 # so the step asserted the opposite of what the instrument does, and pointed at a
 # plan-v04 section that had already gone.
 #
 # Two cases (item 235): a device missing at load is not a transition, so only a
 # fresh load -- the second step below -- shows it recovered.
 ('Hot-swap -- unplugged mid-session',
  'PASS IF: A bordered alert on the OLED reads warn and then m_launchpad. The grid goes dark.',
  [('compose mode-2', 'mode')],
  # The predicate reads err and the eyes read the grid; no bus says the grid
  # stopped painting. Mode 2 rather than 1, so the reload in the next step
  # restores a mode with a beat row.
  # wait 20: the warn is three missed ticks behind the unplug, up to 8 s at the
  # shipped 2000 ms tick, and the runner's default drain is 0.4 s.
  # It sets compose itself: u_err shows a warn only in compose, and the step
  # before leaves the rig on mode-6, in perform.
  {'do': 'Press enter first, then unplug the Launchpad USB and leave it out.',
   'wait': 20,
   'check': {'kind': 'bus', 'bus': 'ERR', 'has': ['warn m_launchpad']}}),
 ('Hot-swap -- absent at load',
  'PASS IF: The grid ends up lit with one bright lamp in the left column. Only where it settles is the test -- what the Launchpad does on the way back is its own. The beat row runs at the tempo restored from knobs.txt rather than the one the earlier steps set.',
  [],
  # 60 s: a replug often misses the first re-wires while the device enumerates
  # -- the Launchpad once used six of its eight, spread over seventy seconds
  # (item 277). Under about 50 s fails intermittently on correct code.
  {'do': 'Plug the Launchpad back in and wait up to 60 seconds without touching anything.',
   'reload': True,
   'need': ['The Launchpad still unplugged from the last step.']}),

 # The third hot-swap case -- see the nanoKONTROL bench.
 ('Hot-swap -- unplugged and plugged back in',
  'PASS IF: The grid lights again and the left column shows one bright lamp.',
  [],
  # A lit grid is the oracle: the surface paints only while m_launchpad owns it
  # and the device is in Programmer Mode, so it proves the re-wire and the mode
  # both came back (item 276).
  {'do': 'Press enter first. Unplug the Launchpad USB and count to fifteen, then '
         'plug it back in and wait up to 60 seconds without touching anything.'}),
 # Panic keeps the surface (item 250): handing it back left the grid dead until
 # a reload, and Live Mode's clock flooded Midi-In 1. display-assert asserts the
 # same.
 ('Panic keeps the surface',
  'PASS IF: The grid keeps painting and the Launchpad stays in Programmer Mode. Its own display does not come back.',
  [('bang', 'panic')]),
 ('The grid still answers after a panic',
  'PASS IF: The bright lamp moves to the third position -- the panic silenced notes and did not surrender the surface.',
  [('compose mode-3', 'mode')],
  # Not mode 1: there the pads are the drum page, so the next step's press
  # would draw no row.
  ),
 ('Pads still reach the OLED after a panic',
  'PASS IF: A pad press still reports pad-NN on the OLED.',
  [],
  {'do': 'Press a pad.'}),
]



# Every PASS IF here describes the phone, not the Organelle. Closing PdParty is
# the only way to reach item 114's ICMP teardown on hardware. The rate limit is
# phone-assert's -- a step table cannot flood -- and the fast fader sweep is the
# closest a person gets.
STEPS_PHONE = [
 ('The link is up',
  'PASS IF: The bottom line of the phone reads ok rather than NO-LINK.',
  [('compose mode-1', 'mode')],
  {'need': ['PdParty open on the CutItRemote scene and on the same network. '
            'A NO-LINK here means nothing below can be judged.']}),
 ('One parameter',
  'PASS IF: The top line reads chop-size and the big number reads 43 on its own. The unit is not drawn and that is correct.',
  [('chop-size 43 %', 'disp')],
  # The Mac run reads u_net's datagrams, so it judges what u_net filters; what
  # the phone then draws is the device run's, and there the runner skips the
  # predicate and asks the person.
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
  # The heartbeat `has` is the witness: a dead u_net also never sends in-l
  # (bench-gen.py's _positive).
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
  # No audio claim: there is nothing to hear until v0.4.
  #
  # The warn is the action working: u_net's watchdog watches the socket, which
  # dies when nothing listens on the phone's port (ref/device/phone.md). Step 1
  # leaves the rig in compose, where u_err shows it.
  #
  # It warns once per load ($0-warngate), which `do` says rather than the
  # PASS IF, so rewording it does not stale the verdict.
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
   # The lamp is lit by the Organelle's answer, so a flash means the command
   # arrived and was accepted.
   'need': ['PdParty OSC send host and port pointed at the Organelle, port 9001. '
            'Without it every button below is silent and nothing says so.']}),
 # No step for the fork reaching the log: presence-assert proves it headlessly.
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
  'PASS IF: The Launchpad left column shows exactly one lit mode lamp -- on mode-1 for a fresh install and wherever you left it for a restored one. A dark grid means nothing below can be read.',
  [],
  {'do': 'Look at the Launchpad left column. Press nothing.'}),
 ('Change the mode',
  'PASS IF: The lit lamp moves to the fourth position down. Nothing else is visible yet and that is correct.',
  [],
  {'do': 'Press the fourth button down the Launchpad left column.'}),
 ('The change reached the disk',
  'PASS IF: Cut-it-auto.txt reads mode perform mode-4. The file is the only evidence -- nothing on the instrument shows it. The old mode still being there is the failure.',
  [],
  # The file is the only evidence, so the runner fetches it and compares. No
  # `do`, because the runner does all of it and the step is not [HANDS].
  {'targets': ('device', 'paper'),
   'check': {'kind': 'file', 'fetch': 'state',
             'path': 'device-state/cut-it-auto.txt',
             'contains': 'mode perform mode-4'}}),
 ('Front-panel Save',
  'PASS IF: The screen shows Saving briefly and returns. Then cut-it-manual.txt has a new timestamp even though it is still empty. An unchanged timestamp is the failure.',
  [],
  # A timestamp, because cut-it-manual.txt is still empty (nothing uses the
  # manual policy yet): unchanged means saveState never arrived.
  # Every Save rewrites knobs.txt from the physical knobs (item 139), and midi 1
  # and tempo 2 rest on knob 1 at 57 BPM, hence the `need`. knobs.txt is in no
  # bench's DEPS, so a wrong one would stale neither verdict.
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
  # Last in a session: a power cycle resets the wifi fault's uptime clock, and
  # the fault takes about three hours to reappear.
  {'do': 'Power cycle the Organelle and wait for it to come back.',
   'need': ['Every other bench already run. This power cycle resets the wifi '
            'fault uptime clock.']}),
]


# Paper: step 3 reloads the patch, and a driven bench runs as a third patch in
# the instrument's own Pd, so the reload would kill it and strand every later
# step. Every predicate reads a file, so there is nothing to drive or drain.
# Step 5 leaves the rig with no patch; step 7 puts it back and says so itself.
STEPS_RECOVER = [
 ('Short press -- panic and nothing more',
  'PASS IF: Everything sounding stops the instant the button goes down -- not when you let go. The whole Launchpad flashes red and clears itself about a second later. The aux LED is red and the footer reads panic. The patch is still running: the grid comes back and the beat row still walks.',
  [],
  {'do': 'Start the transport, play something on the SP-404 so there is a sound to stop, then tap the top left corner button on the Launchpad once and let go straight away.',
   'need': ['The Launchpad lit and in Programmer Mode, in any mode but 1 -- '
            'mode 1 is the drum page, where the beat row gives way.',
            'Something audible running -- the 404 sequencer is easiest.']}),

 ('Short press -- the Volca stops too',
  'PASS IF: The Volca stops sequencing. Before this was built its transport never heard anything at all -- it kept running through a panic and the mixer could only mute it.',
  [],
  # The Volca honors Start/Stop only with MIDI Clock src on Auto -- Korg's
  # documentation, not measured (ref/device/volca.md) -- hence the `need`. Only
  # the panic stop reaches port 4, never the clock (items 279, 295).
  {'do': 'Set the Volca sequencing on its own, then tap the top left corner button once.',
   'need': ['The Volca powered and its own sequencer running.',
            "The Volca's MIDI Clock src set to Auto. Set to Internal it ignores "
            'Start and Stop entirely and this step cannot pass.']}),

 ('Hold -- the patch reloads and comes back whole',
  'PASS IF: Silence at once. About two seconds later the screen goes through its boot sequence again and the instrument comes back with every device working -- the Launchpad lit and answering and both output devices reachable. A few seconds in a bordered alert reads warn and then u_map and then recovered. Knob 1 moves the tempo on the first touch with no dead sweep.',
  [],
  # The alert is deferred to about 4.5 s after the reload, clear of the boot
  # stages, and lasts about two seconds. The reload does not arm pickup -- after
  # an emergency the knobs in hand are the truth -- so a knob that needs a sweep
  # fails here.
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
  # A dead patch cannot report its own failed reload; the breadcrumb survives
  # to say one was tried, and the next step reads it.
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
  # Through the menu or /loadPatch, never killall pd: a killed Pd skips
  # m_launchpad's safe exit and strands the surface in Programmer Mode (item 96).
  # This step restores the rig step 5 removed.
  {'do': 'Over ssh run: mv "/sdcard/Patches/!/Cut It away" "/sdcard/Patches/!/Cut It" -- then load Cut It from the Organelle menu, let it settle, and leave it by selecting a different patch.',
   'need': ['The renamed folder from the step before, still renamed.']}),
]

STEPS_MIDI = [
 ('Restored tempo at boot',
  'PASS IF: The footer reads 57 BPM and not 120 BPM. The lit mode lamp is wherever you left it -- note which one it is.',
  [],
  # Device only: 57 comes from knobs.txt, which no Mac has.
  {'targets': ('device',),
   'check': {'kind': 'oled', 'has': ['57'], 'has_not': ['120']}}),

 ('Get to mode 1',
  'PASS IF: The lit lamp moves to the top position. Nothing below works until it does.',
  [],
  {'do': 'Press the top button of the Launchpad left column -- the top mode lamp.'}),

 ('SP-404 pad 1',
  'PASS IF: The OLED shows one row for the pad -- sp-a1 with the velocity beside it. No sp-pad or sp-bank row appears.',
  [],
  # The 404 lights only the selected bank, so every 404 step names it.
  {'do': 'Press enter first. Check which bank the 404 is lit on -- it lights only the selected one -- then select bank A and press pad 1.'}),

 ('SP-404 pad 5',
  'PASS IF: A row reads sp-a5 with the velocity beside it. Anything else is the failure.',
  [],
  # Pad 5 catches `47 + n`: the old formula draws sp-a13, which looks plausible
  # on an OLED.
  #
  # `wait` is the other half of "press enter first": the window opens at GO and
  # closes 0.4 s later, so a hand reaching for the pad after enter lands in an
  # empty window. On the rig three pad windows held only meter rows while a
  # person passed all three by eye.
  {'do': 'Press enter first. Check the 404 is lit on bank A -- it lights only the selected one -- then press pad 5. There are about ten seconds to do it.',
   'wait': 10,
   # `has` is a substring test; no other pad's name contains sp-a5.
   'check': {'kind': 'bus', 'bus': 'DISP', 'has': ['sp-a5']}}),

 ('All sixteen pads',
  'PASS IF: Each pad draws a row named for itself as you press it -- sp-a1 then sp-a2 up to sp-a16. A run that goes sp-a1 to sp-a4 and then jumps is the failure.',
  [],
  # About two a second: each pad is a new name, and the param layer holds five
  # and refuses a sixth until one ages out about 1.3 s after it last moved.
  {'do': 'Press enter first. Then press pads 1 through 16 in order on bank A, about two a second.'}),

 ('Bank B',
  'PASS IF: The row reads sp-b1 -- the same pad on bank B has a name of its own.',
  [],
  # ⛔ THE WINDOW HAS TO OUTLAST THE HAND -- see step 4.
  {'do': 'Press enter first. Then select bank B and press pad 1. The 404 lights only the bank it is on. There are about ten seconds to do it.',
   'wait': 10,
   # sp-b1 is also a substring of sp-b10 to sp-b16, so this proves the bank;
   # step 4 owns the pad decode.
   'check': {'kind': 'bus', 'bus': 'DISP', 'has': ['sp-b1']}}),

 ('One row for a press and its release',
  'PASS IF: One row named for the pad -- sp-b3 for bank b pad 3 -- shows the velocity on the press and 0 on the release. It is the same row both times and no sp-pad or sp-bank row appears.',
  [],
  # Exactly two sp- lines: u_map's row on the press and again at velocity 0 on
  # the release (items 283, 317). Four means m_404's sp-pad and sp-bank rows are
  # back; one means the release never arrived. The window has to outlast the
  # hand -- see step 4.
  {'do': 'Press enter first. Then press and hold any pad and let go. There are about ten seconds to do it -- one hit only.',
   'wait': 10,
   'check': {'kind': 'bus-count', 'bus': 'DISP', 'match': 'sp-', 'n': 2}}),

 ('Fader 1 in mode 1',
  'PASS IF: The Volca tone changes as you move it. The OLED shows one row for the fader -- volca-cc41 and the value -- and no slider-1 row.',
  [],
  {'do': 'In mode 1 move fader 1 on the nanoKONTROL.',
   'need': ['The Volca audible. It transmits nothing so this step and the two '
            'after it are judged by ear with no readback of any kind.']}),

 ('Fader 1 in mode 4',
  'PASS IF: The Volca does not change -- no change is the pass. The OLED shows slider-1 and its raw value because nothing maps it in mode 4 and that is correct.',
  [],
  {'do': 'Press the fourth button down the Launchpad left column then move fader 1.'}),

 ('Fader 1 back in mode 1',
  'PASS IF: The Volca responds again. Still silent means the mode did not change back -- check the lit lamp.',
  [],
  {'do': 'Press the top button of the Launchpad left column then move fader 1 again.'}),

 ('Tempo from knob 1',
  'PASS IF: The footer BPM follows the knob over roughly 10 to 500 BPM once the knob has crossed the restored value. Nothing at all happens before it crosses.',
  [],
  {'do': 'Sweep knob 1 all the way and back.'}),

 ('Transport from PLAY and STOP',
  'PASS IF: The aux LED goes green on PLAY and dark blue on STOP.',
  [],
  # No footer claim: the pad rows from the steps above raise the param layer
  # over it. The aux LED is the readout.
  {'do': 'Press PLAY on the nanoKONTROL, then STOP.'}),

 ('Panic is unbound',
  'PASS IF: The aux LED never turns red however many controls you press.',
  [],
  # That no map row names panic is map-assert's, read from cut-it-map.txt; this
  # asks only what fingers can answer -- that no control anyone reaches for
  # raises it.
  {'do': 'Press every transport key on the nanoKONTROL and every button on the '
         'Organelle. Turn the encoder. Nothing should ever go red.'}),

 # Hot-swap for both output devices, which differ: the SP-404 is `active` and can
 # be declared lost; the Volca is `none`, transmits nothing and can never be
 # polled, so u_present's re-wire heartbeat is what brings it back.
 ('Hot-swap -- SP-404 unplugged',
  'PASS IF: A bordered alert on the OLED reads warn then m_404 then device-lost.',
  [],
  # wait 20: the warn is up to 8 s behind the unplug and the runner's default
  # drain is 0.4 s. The alert lands about eight seconds after the cable is out
  # and lasts about two, so `do` says where and when to look.
  # Leave it out: plugged back in to check, the next step would reload with the
  # device present and test nothing.
  {'do': 'Press enter first, then unplug the SP-404 and watch the OLED. The alert arrives about eight seconds after the cable is out and clears itself about two seconds later. Leave it unplugged when you answer -- the next step loads without it.',
   'wait': 20,
   'check': {'kind': 'bus', 'bus': 'ERR', 'has': ['warn m_404']}}),
 ('Hot-swap -- SP-404 absent at load',
  'PASS IF: The OLED shows a row for the pad -- sp-a1.',
  [],
  # A pad is the oracle: the 404's silence at boot proves detection, but silence
  # cannot tell a working subscription from a dead one.
  # `need` is the state the runner's reload already made, not a thing to do.
  {'do': 'Plug it back in, wait 60 seconds, then press pad 1 on bank A.',
   'reload': True,
   'need': ['The SP-404 unplugged, and the patch just reloaded without it. '
            'The runner has already done the reload -- that absence is what '
            'this step tests.']}),

 # The third hot-swap case for the 404 -- see the nanoKONTROL bench.
 ('Hot-swap -- SP-404 unplugged and plugged back in',
  'PASS IF: The OLED shows a row for the pad again -- sp-a1.',
  [],
  {'do': 'Press enter first. Unplug the SP-404 and count to fifteen, then plug '
         'it back in and wait up to 60 seconds before pressing pad 1 on bank A.'}),

 # The oracle is the fader changing the sound, never the Volca sounding: it plays
 # from its own keys with no MIDI connected at all (ref/device/volca.md).
 ('Hot-swap -- Volca unplugged and plugged back in',
  'PASS IF: Holding a Volca key and sweeping slider 1 changes the sound -- by ear.',
  [],
  # The Volca alone is the test: it registers `none` and comes back through
  # u_present's re-wire heartbeat (wire-watch.sh every eight ticks, re-wiring
  # when the client names change); pulling a second device would go through the
  # loss path instead (item 275).
  # 30 s covers the heartbeat: u_root passes [u_present 4000 2000 33 8], so it
  # is eight 2000 ms ticks -- 16 s -- plus enumeration.
  # By ear, always: the Volca transmits nothing, so no predicate is possible.
  # Unplugged again at the end, because the next step reloads without it.
  {'do': 'Press enter first. Unplug the Volca interface alone and count to fifteen, then plug it back in and wait up to 30 seconds before sweeping slider 1 while holding a Volca key. Unplug it again before you answer -- the next step loads without it.',
   'need': ['Mode 1. Slider 1 is the only control bound to the Volca.']}),
 ('Hot-swap -- Volca absent at load',
  'PASS IF: Holding a Volca key and sweeping slider 1 changes the sound -- by ear. Sweep it up -- slider 1 is velocity.',
  [],
  # Absent at load is the likelier case in a room: nothing is wrong as far as
  # the instrument knows, so nothing warns, and the heartbeat recovers it (item
  # 285).
  {'do': 'Plug the Volca interface in, wait up to 30 seconds, then hold a Volca key and sweep slider 1.',
   'reload': True,
   'need': ['The Volca interface still unplugged from the last step.',
            'Mode 1. Slider 1 is the only control bound to the Volca.']}),
]


# Paper, like recover: step 2 loads another patch, which restarts Pd and would
# take a driven bench down with it. Every step is eyes: the patch's output is
# the OLED and it writes nothing to disk, and what a machine can check is
# debug-assert.sh's. The last step puts Cut It back.
STEPS_DEBUG = [
 ('It is in the menu -- under debug and not under the instrument',
  'PASS IF: The Organelle menu has a debug folder beside the one holding Cut It -- and Cut It Debug is inside it. Finding it in the same folder as the instrument is the failure. At a venue you should scroll past nothing to reach what you play.',
  [],
  {'do': 'From the Organelle menu browse the patch folders. Do not load anything yet.',
   'need': ['The debug patch deployed. tools/deploy.sh --debug puts it there.']}),

 ('It loads and comes up on the MIDI screen',
  'PASS IF: Within a couple of seconds the screen reads 1-MIDI-IN with four rows under it -- lp nano sp404 and ch -- all reading zero. A screen that stays on the menu or goes blank is the failure.',
  [],
  {'do': 'Select Cut It Debug and wait.',
   'need': ['You are not in the middle of a set. This stops the instrument.']}),

 ('It wired itself -- and proving that is the whole bench',
  'PASS IF: Moving a nanoKONTROL fader makes the nano row count up. This is the step everything else rests on: loading any patch drops the ALSA connections and the patch runs wire.sh itself to put them back. A nano row stuck on zero means the patch is measuring silence and would report a healthy rig as dead.',
  [],
  # The nano proves the probe: it transmits the moment it is touched and needs
  # no mode. If its row does not move, nothing a later step reports means
  # anything.
  {'do': 'Move fader 1 on the nanoKONTROL a few times and watch the nano row.',
   'need': ['The nanoKONTROL plugged in and its scene loaded.']}),

 ('Each device lands on its own row',
  "PASS IF: A Launchpad pad moves only the lp row. An SP-404 pad moves only the sp404 row. Each one also changes the ch row to a number in that device's own block -- ch 1 to 16 for the Launchpad and 33 to 42 for the 404 bank. Two devices sharing one row is the fault this patch exists to find.",
  [],
  # The row is the port and the port is the device only while wire.sh has undone
  # mother's auto-connect, which wires the lowest-numbered client to Midi-In 1
  # (item 274).
  {'do': 'Press a Launchpad pad and then an SP-404 pad on bank A. Watch which row moves.',
   'need': ['The Launchpad and the SP-404 both plugged in and powered.']}),

 ('The error log screen shows what the instrument left behind',
  'PASS IF: The screen reads 3-ERR-LOG and the four rows under it hold the last four lines of the instrument s own log with dots where the spaces were. Four dashes mean the log was empty or missing -- which is a real answer and not a failure if the instrument has not raised anything.',
  [],
  # The log is u_err's: loading this patch rolls the session that went wrong
  # into cut-it-err.log (ref/module/error.md).
  {'do': 'Press the fourth key from the bottom to select the error log screen.'}),

 ('The network screen shows the address you type into the phone',
  "PASS IF: The screen reads 4-NETWORK and the row under it reads ip- followed by this Organelle's own address. That is the number PdParty needs -- it will not resolve the name -- and reading it here is what removes the last reason this rig needs a laptop to fix the phone link.",
  [],
  # Item 312: PdParty needs a literal address, and on the house network the
  # lease moves (the addresses seen are on the Organelle's Reference page). On
  # the access point it is always the same. ref/device/phone.md.
  {'do': 'Press the fifth key from the bottom. Read the ip row and check it against what the phone is pointed at.'}),

 ('Both output devices answer when you fire at them',
  'PASS IF: The C an octave up plays a note on the Volca. The D above it plays pad A1 on the SP-404. The sent counter goes up by exactly one per press -- two for one finger would mean a key release is firing as well as the press.',
  [],
  # Pad A1 may hold a looping sample that nothing in the patch can stop, All
  # Notes Off included (item 311).
  {'do': 'Press the second key from the bottom to see the test screen -- then press the C an octave up and the D above it. Listen.',
   'need': ['The Volca powered and audible.',
            'The SP-404 powered and audible. Pad A1 may hold a looping sample -- '
            'if it starts one, press the pad on the device to stop it.']}),

 ('A re-wire by hand reports how many links it made',
  'PASS IF: The re-wire screen reads 5-RE-WIRE and the links row shows a number rather than a dash -- nine on the full rig. The runs row goes up by one each time you press the key. A links row still reading dash means wire.sh ran but said nothing back.',
  [],
  # It forks wire.sh itself: the presence bus's re-wire lives in the Pd this
  # patch's load has already killed.
  {'do': 'Press the sixth key from the bottom for the re-wire screen, then press the E an octave up twice.'}),

 ('You can get out of it -- and the instrument comes back',
  'PASS IF: The lowest key returns you to the Organelle menu. Cut It then loads and runs normally -- and when you leave it the Launchpad goes back to Live Mode with its Setup button responding. A Launchpad still dark and ignoring Setup is the failure.',
  [],
  # The lowest key is the only guaranteed way out: asking mother for the
  # encoder would take the click too (items 313 and 314). This step restores
  # the rig.
  {'do': 'Press the lowest key. Then load Cut It from the menu and leave it once it is up.',
   'need': ['Nothing else queued on the rig -- this is the step that puts the '
            'instrument back.']}),
]


# The drum machine on the rig: what only a person in front of the Launchpad and
# the 404 can judge -- whether the page reads, and what the 404 does with the
# notes. The notes, the frames and the file are sequencer-assert's.
STEPS_SEQUENCER = [
 ('The drum page',
  'PASS IF: The left column has its top lamp bright. The top two rows of pads are the steps and the next two rows the velocity buttons -- all dim but one velocity button. The bottom-left four by four is dim with its top-left pad lit and the bottom-right four by four is dark. No white pad walks along the bottom row.',
  [('bang', 'stop'), ('compose mode-1', 'mode')],
  # Level 13 is the second velocity row's fifth button; track 1 is the
  # top-left drum pad. Both reset at every load (ref/module/sequencer.md).
  {'need': ['A fresh load of the patch with no saved pattern -- the selection '
            'resets at every load and a saved step would be lit.']}),
 ('A drum pad plays and selects',
  'PASS IF: The 404 plays bank A pad 13 at once -- louder for a harder press. That pad lights and the top-left one goes dim. The OLED draws no row for it.',
  [],
  {'do': 'Press the bottom-left drum pad.',
   'need': ['Sounds in bank A of the 404 -- the starter kit or anything else.',
            'The 404 on bank A so its pad lights too.']}),
 ('Velocity buttons',
  'PASS IF: Each press lights the button pressed and only that one. Nothing sounds and the OLED draws nothing.',
  [],
  {'do': 'Press the top-left velocity button, then the bottom-right one.'}),
 ('Steps light by velocity',
  'PASS IF: Step 1 is bright and step 2 dark with step 3 between them -- one color getting brighter with velocity. The steps left off stay dim.',
  [],
  {'do': 'With the bottom-right velocity button lit press step 1. Pick the '
         'top-left velocity button and press step 2. Pick a velocity button in '
         'the middle and press step 3.'}),
 ('The step rule',
  'PASS IF: The first press turns step 1 off and the second turns it back on bright. The third makes it dark and leaves it on.',
  [],
  {'do': 'Pick the bottom-right velocity button and press step 1 twice. Then '
         'pick the top-left velocity button and press step 1 again.'}),
 ('PLAY from step 1',
  'PASS IF: A white pad walks the top two rows from step 1 at four steps a beat. Pad 13 sounds on the steps you lit -- softer on the dark ones. The white pad passes over a lit step and the step is still lit behind it.',
  [('120', 'tempo'), ('bang', 'start')]),
 ('Two tracks on one step',
  'PASS IF: Pad 1 sounds alone on step 9 and with pad 13 on step 1 -- both are heard there and neither is dropped.',
  [],
  {'do': 'Press the top-left drum pad. Then press step 1 and step 9.'}),
 ('STOP',
  'PASS IF: The sound stops and the white pad goes out. The steps stay lit.',
  [('bang', 'stop')]),
 ('Panic stops it too',
  'PASS IF: Everything stops at once and the grid flashes red. When it clears the white pad is gone and the steps are still lit.',
  [],
  {'do': 'Press PLAY on the nanoKONTROL. Then tap the top-left corner button of the Launchpad.'}),
 # The blueprint's open question for the rig (cut-it/drum-machine): a looping
 # pad toggles on a second note-on, and fast hats need a one-shot pad to
 # restart instead.
 ('A one-shot pad on every step',
  'PASS IF: Every step is heard as a fresh hit -- a hit cut short by the next one is fine. A step that falls silent is the failure: it means a one-shot pad toggles like a looping one.',
  [('bang', 'start')],
  {'do': 'Select pad 13. Light all sixteen of its steps. Listen for a bar or two then turn knob 1 up and listen again.',
   'need': ['Pad 13 of bank A set to one-shot on the 404 -- not loop.']}),
 ('The pattern survives a reload',
  'PASS IF: After the reload the drum page shows the same steps lit as before it.',
  [('bang', 'stop')],
  # u_state flushes within 2 s of a change, so the wait is part of the step.
  {'do': 'Look at which steps are lit. Wait two seconds then reload the patch.',
   'reload': True,
   'need': ['Steps lit on the drum page from the steps before.']}),
 ('Other modes keep their grid',
  'PASS IF: The second lamp lights and the drum page gives way to the beat row along the bottom. A pad press draws a pad-NN row on the OLED again.',
  [('compose mode-2', 'mode')],
  {'do': 'Press a pad in the top two rows.'}),
]
