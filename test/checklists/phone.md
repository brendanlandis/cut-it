# Phone checklist

Every **Pass if** here describes the phone, not the Organelle, unless it says otherwise. The phone shows the Launchpad's current page and controls it, and leaves the OLED's alerts and rows to the OLED (Brendan, 2026-11-04): step 4 is the one whose correct result is that nothing happens on the phone, and step 11 the one where nothing happens to the tempo.

The rate limit is `phone-assert`'s, and the page structure, what each control sends and that nothing is sent back are `touchosc-assert`'s: what is left is how the pages look and feel under a finger. Steps 1 to 12 judge the phone's pages, which the checklist page covers in test mode, so send their lines from the Mac with `tools/send.sh`, which needs no test mode. Steps 13 to 18 are the checklist page and test mode; step 19 is the arrangement page's tap button, and step 20 the drum screen's pads. The page holds the line check, not these steps, so run them from here like the rest.

20 steps. How to read one, and how to send a **Send** line: [the checklists' README](README.md). Why each thing behaves as it does: [phone](../../ref/device/phone.md), [tempo](../../ref/module/tempo.md).

- [ ] **1. The link is up, on the performance page**
  - **Need:** TouchOSC open on the phone with Cut It's layout, on the same network. A no link here means nothing below can be judged.
  - **Send:** `mode perform`
  - **Pass if:** The phone shows the arrangement screen: on the left the tempo, large and red, captioned tempo, the tap button under it, and playing or stopped with its lamp on the bottom row; on the right the time signature as 4 / 4, the last step 16, and two knobs, swing at 50% and drunk at 0%, each captioned in small grey words flush left above it, and the link lamp lit teal beside the word link rather than no link on the bottom row. Every edge lines up with the ones above and beside it, and nothing sits close to the notch.

- [ ] **2. Only the page's own tabs**
  - **Need:** The performance page, as step 1 left it.
  - **Pass if:** One tab bar runs along the top, a single tab reading arrangement, lit red. No second bar above it lists the eight pages, and nothing on the screen is cut off at the bottom or sits under the home bar.
  - **Note:** The eight pages' bar is the outer pager's, on in the layout so the Mac's editor can reach every page, and the phone's own script hides it as the layout loads. If it shows, that hiding did not work on the phone ([phone](../../ref/device/phone.md), *Open*).

- [ ] **3. The phone follows the Launchpad's page**
  - **Do:** Press the Launchpad's top left-column button, then the second, then the second's right button. Press aux on the Organelle, then aux again. Press the bright button.
  - **Pass if:** At each press the phone turns at once to that page: drums, with sixteen pads; synths, its harmony tab; the same again; songs, under its tab; synths; and arrangement again. Nothing on the phone turns the Launchpad's page.

- [ ] **4. The OLED's rows and alerts stay on the OLED**
  - **Need:** The performance page.
  - **Send:** `disp chop-size 43 %; err warn u_bench probe-warning`
  - **Pass if:** The OLED shows the chop-size row and a bordered warn box; nothing on the phone changes at all, its tempo included.
  - **Note:** The phone was the OLED's mirror until 2026-11-04; that it reads nothing on `disp` now is `phone-assert`'s.

- [ ] **5. The tempo, from knob 1**
  - **Need:** The performance page. With nothing Saved knob 1 is held at 120 until turned through about 11 o'clock, where its line puts 120; turn it through first.
  - **Do:** Turn knob 1 slowly from about 9 o'clock to 3 o'clock, then quickly back.
  - **Pass if:** The phone's tempo follows the knob, about 80 to 210 over that turn, and settles on the same number as the OLED's bpm row when the knob stops.

- [ ] **6. The tempo, dragged on the phone**
  - **Do:** Put a finger on the tempo and drag up slowly, a BPM at a time, then down past where you started, then a long quick drag up. Let go.
  - **Pass if:** The number moves one BPM at a time under a slow finger, with no jumps, and the OLED shows nothing of it: the phone is the tempo's only display at rest. A long drag reaches far but stops at 600 at the top and 5 at the bottom. When you let go it stays. 
  - **Note:** About 9 points of drag to a BPM. Knob 1 is held at the phone's tempo afterwards, as knob 2 is at the phone's last step: its next turn reads bpm and the phone's tempo with its own in brackets, and moves nothing until turned through it ([tempo](../../ref/module/tempo.md)).

- [ ] **7. The global last step, and knob 2**
  - **Need:** The performance page, the drums playing, from the sequencer checklist's steps or `start bang`.
  - **Do:** Drag the last step's box down from 16 to 8. Then press the top left-column button, the drum page, and turn knob 2 a little either way.
  - **Pass if:** The box reads 8, and on the drum page the green pad walks steps 1 to 8 with the steps past them dark. Knob 2's first turn reads last-step 8 with the knob's own step in brackets on the OLED, and changes nothing until it is turned through 8, after which the phone's box follows it.

- [ ] **8. The swing**
  - **Need:** The drums playing.
  - **Do:** Press the bright button, the performance page, and drag the swing knob to 66%. Listen for a bar.
  - **Pass if:** At 66% every second sixteenth comes late, a long-short shuffle. Put it back to 50% before going on.

- [ ] **9. The tap button**
  - **Need:** The performance page.
  - **Do:** Tap the nanoKONTROL's LOOP four times, evenly, about two a second.
  - **Pass if:** From the second tap the phone's tempo reads about 120.

- [ ] **10. A pause starts the count over**
  - **Do:** Wait three seconds. Tap LOOP once. Then tap it three times quickly, about three a second.
  - **Pass if:** The single tap after the pause leaves the tempo where it was. The quick taps set it to about 180.

- [ ] **11. A pad on the drum page is a drum**
  - **Do:** Press the top left-column button, the drum page, then tap the second row's first pad three times.
  - **Pass if:** It plays its drum each time, and the phone's tempo does not move.

- [ ] **12. Link lost, and back**
  - **Do:** Load Cut It again from the Organelle menu, watching the phone. Touch nothing on the phone.
  - **Pass if:** The phone's link lamp goes out and reads no link while Cut It restarts, then lights and reads link again within a few seconds of it loading, and the phone turns to the page on show. Nothing on the Organelle mentions the phone.
  - **Note:** A lost phone is the phone's to report, by its no link, and the Organelle says nothing (Brendan, 2026-11-03): under Pd 0.57 the socket survives a listener going away, so the old `net-link-down` warning could not fire and was taken out ([phone](../../ref/device/phone.md)). Reloading is the rig-side way to silence the heartbeat; closing TouchOSC would close the display too.

- [ ] **13. Setup opens the checklist page and closes it**
  - **Need:** The performance page.
  - **Do:** Tap Setup, the Launchpad's bottom-left button. Then tap it again.
  - **Pass if:** At the first tap the phone turns at once to the checklist page, reading test mode off. At the second it turns back to the arrangement screen, at once.

- [ ] **14. Test mode on, from the diagnostics page**
  - **Do:** Tap Setup, then press the top row's second pad. Watch the phone for ten seconds.
  - **Pass if:** The checklist page's label reads test mode on beside a lit teal lamp, and still reads it ten seconds later. The OLED shows a bordered box reading warn then u_net then test-mode-on for about two seconds.
  - **Note:** One press can reach Cut It twice, 5 ms apart, which once turned test mode on and straight back off; a second flip within 300 ms is dropped (`phone-assert` holds it), and the ten seconds are this step's check that it held.

- [ ] **15. The page holds the line check**
  - **Need:** Test mode on, as step 14 left it.
  - **Do:** On the page, tap Back until it stops, then Next through every step.
  - **Pass if:** Its tab reads line check, the only tab showing. It starts at 1 of 8, The phone and the Launchpad, and ends at 8 of 8, each step's text whole on its page. FM and STRINGS sit beside the step's position on every step. No Send button shows on any step, and nothing picks another checklist.
  - **Note:** The page carries test/checklists/linecheck.md alone, and the phone sends nothing onto Cut It's buses (Brendan, 2026-11-04); that `send` is no command any more is `phone-assert`'s. Steps 13 to 18 here run from the Mac, like the rest.

- [ ] **16. Pass is logged on the Organelle**
  - **Do:** On the page, go to the line check's step 1 and press Pass.
  - **Check:** `./tools/fetch-errors.sh` on the Mac.
  - **Pass if:** Pass flashes, the page moves on to step 2, and the log's newest lines include info phone linecheck-1-pass. Back to step 1 shows passed after its position.

- [ ] **17. A reload turns test mode off**
  - **Need:** Test mode on.
  - **Do:** Load Cut It again from the Organelle menu, and watch the page's label.
  - **Pass if:** The label reads no link while Cut It restarts. When the link is back, test mode is off. Tap the top row's second pad, on the diagnostics page, to bring it back.

- [ ] **18. A page ends test mode, and the phone follows it**
  - **Need:** Test mode on, the phone's checklist page up.
  - **Do:** Press the Launchpad's top left-column button, the drums' page. Then press the second, harmony's.
  - **Pass if:** At the first the checklist page gives way at once to the drum screen, its tab reading drums; at the second the tab reads harmony, and the keyboard tab beside it shows FM and STRINGS, with the velocity switch under them.
  - **Note:** That a page turns test mode off is `phone-assert`'s too (Brendan, 2026-11-04: staying on the checklists after a mode press was the weird part).

- [ ] **19. Tap tempo on the phone**
  - **Need:** The performance page on the Launchpad, so the phone shows the arrangement page.
  - **Do:** Tap the phone's tap button about once a second, five times. Then wait three seconds and tap it twice, half a second apart.
  - **Pass if:** After the second tap the tempo reads about 60 and stays near it as you go on. After the pause the first tap changes nothing, and the second sets it to about 120.
  - **Note:** The phone times the taps itself, as your finger lands, by the tap button's rules: four intervals averaged, starting over after two seconds. That the numbers come out right is `touchosc-assert`'s; this is whether the button answers a finger and the tempo it gives feels like your taps.

- [ ] **20. The drum screen's pads under a finger**
  - **Need:** The drum page on the Launchpad, so the phone shows the drum screen.
  - **Do:** Tap each of the show radio's four in turn, then volume again. Tap a pad that is not lit, then the lit one. Put a finger on a pad and drag up slowly, then down past where you started, then a long quick drag up, and let go. Then tap a pad with a little wobble in the finger, and drag the first pad's volume back to 0.
  - **Pass if:** The radio lights the one tapped, its word black on red, and every pad's number changes at once: dB, semitones, last steps, percent. A tap lights its pad and the Launchpad selects the same one; a tap on the lit pad changes nothing. A slow drag moves the number a step at a time, no jumps, and no drag selects its pad. The wobbly tap still selects.
  - **Note:** About 20 points of drag a step, as for the time signature's boxes (Brendan, 2026-11-05). That the state lights only a pad's fill, and a drag sends its value as it stands and nothing comes back, is `touchosc-assert`'s.

- [ ] **21. The drum screen's effect controls**
  - **Need:** The drum page on the Launchpad, so the phone shows the drum screen.
  - **Do:** Look at the two radios under sync and snap. Tap each of effect's three in turn, then distortion again. Tap a pad, then another, watching the knobs.
  - **Pass if:** Both radios run down the screen, show's volume and effect's distortion on top, and the segment lit is the one under its word, black on red. Distortion shows drive, tone and mix to the right; delay shows the time, 1/2 to 1/32 over straight, triplet and dotted, then feedback and level; reverb shows send, size and damping. Only the chosen effect's controls show. Selecting another pad turns each knob to that drum's setting, and size and damping stay put.
  - **Note:** That a vertical radio's first segment is on top at orientation 2 is inferred, not seen (`ref/device/phone.md`, *Open*): if the lit segment is at the bottom under the top word, that is this failing.
