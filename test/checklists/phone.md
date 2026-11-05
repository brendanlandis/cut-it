# Phone checklist

Every **Pass if** here describes the phone, not the Organelle, unless it says otherwise. The phone shows the Launchpad's current page and controls it, and leaves the OLED's alerts and rows to the OLED (Brendan, 2026-11-04): step 4 is the one whose correct result is that nothing happens on the phone, and step 11 the one where nothing happens to the tempo.

The rate limit is `phone-assert`'s, and the page structure, what each control sends and that nothing is sent back are `touchosc-assert`'s: what is left is how the pages look and feel under a finger. Steps 1 to 12 judge the phone's pages, which the checklist page covers in test mode, so send their lines from the Mac with `tools/send.sh`, which needs no test mode. Steps 13 to 18 are the checklist page and test mode; step 19 is the arrangement page's tap button. The page holds the line check, not these steps, so run them from here like the rest.

19 steps. How to read one, and how to send a **Send** line: [the checklists' README](README.md). Why each thing behaves as it does: [phone](../../ref/device/phone.md), [tempo](../../ref/module/tempo.md).

- [ ] **1. The link is up, on page 1**
  - **Need:** TouchOSC open on the phone with Cut It's layout, on the same network. A no link here means nothing below can be judged.
  - **Send:** `mode mode-1`
  - **Pass if:** The phone shows the arrangement screen: on the left the tempo, large and red, captioned tempo, the tap button under it, and playing or stopped with its lamp on the bottom row; on the right the time signature as 4 / 4, the last step 16, and two knobs, swing at 50% and drunk at 0%, each captioned in small grey words flush left above it, and the link lamp lit teal beside the word link rather than no link on the bottom row. Every edge lines up with the ones above and beside it, and nothing sits close to the notch.

- [ ] **2. Only the page's own tabs**
  - **Need:** Page 1, as step 1 left it.
  - **Pass if:** One tab bar runs along the top, a single tab reading arrangement, lit red. No second bar above it lists the eight pages, and nothing on the screen is cut off at the bottom or sits under the home bar.
  - **Note:** The eight pages' bar is the outer pager's, on in the layout so the Mac's editor can reach every page, and the phone's own script hides it as the layout loads. If it shows, that hiding did not work on the phone ([phone](../../ref/device/phone.md), *Open*).

- [ ] **3. The phone follows the Launchpad's page**
  - **Do:** Press the Launchpad's left-column buttons in turn: the second from the top, the third, the fourth, the bottom one, then the top one again.
  - **Pass if:** At each press the phone turns at once to that page: drums, with sixteen pads; synths, with FM and STRINGS; page 4, a blank screen under its tab; songs, blank under its tab; and arrangement again. Nothing on the phone turns the Launchpad's page.

- [ ] **4. The OLED's rows and alerts stay on the OLED**
  - **Need:** Page 1.
  - **Send:** `disp chop-size 43 %; err warn u_bench probe-warning; disp status 128-bpm`
  - **Pass if:** The OLED shows the chop-size row and a bordered warn box; nothing on the phone changes at all, its tempo included.
  - **Note:** The phone was the OLED's mirror until 2026-11-04; that it reads nothing on `disp` now is `phone-assert`'s.

- [ ] **5. The tempo, from knob 1**
  - **Need:** Page 1. With nothing Saved knob 1 is held at 120 until turned through just left of noon, where its curve puts 120; turn it through first.
  - **Do:** Turn knob 1 slowly from about 9 o'clock to 3 o'clock, then quickly back.
  - **Pass if:** The phone's tempo follows the knob, 50 to 200 over that turn, and settles on the same number as the OLED's footer, in bpm, when the knob stops.

- [ ] **6. The tempo, dragged on the phone**
  - **Do:** Put a finger on the tempo and drag up slowly, a BPM at a time, then down past where you started, then a long quick drag up. Let go.
  - **Pass if:** The number moves one BPM at a time under a slow finger, with no jumps, and the OLED's footer follows it; a long drag reaches far but stops at 600 at the top and 5 at the bottom. When you let go it stays. The Launchpad's beat row walks faster or slower to match.
  - **Note:** About 9 points of drag to a BPM. Knob 1 is not held after the phone moves the tempo: its next turn sets the tempo from where it sits.

- [ ] **7. The global last step, and knob 2**
  - **Need:** Page 1, the drums playing, from the sequencer checklist's steps or `start bang`.
  - **Do:** Drag the last step's box down from 16 to 8. Then press page 2, and turn knob 2 a little either way.
  - **Pass if:** The box reads 8, and on page 2 the green pad walks steps 1 to 8 with the steps past them dark. Knob 2's first turn reads last-step 8 with the knob's own step in brackets on the OLED, and changes nothing until it is turned through 8, after which the phone's box follows it.

- [ ] **8. The swing, and knob 4**
  - **Need:** The drums playing.
  - **Do:** Press page 1 and drag the swing knob to 66%. Listen for a bar. Then press page 2 and turn knob 4 a little.
  - **Pass if:** At 66% every second sixteenth comes late, a long-short shuffle. Knob 4's first turn reads swing 66 with its own value in brackets on the OLED and changes nothing until it is turned through 66; then the phone's knob follows it. Put it back to 50% before going on.

- [ ] **9. The tap pad**
  - **Need:** Page 1.
  - **Do:** Look at the Launchpad's second row, then tap its first pad four times, evenly, about two a second.
  - **Pass if:** The pad sits dim yellow above the beat row's first cell, and flashes bright yellow at each tap, the first included. From the second tap the phone's tempo and the OLED's footer read about 120, and the beat row walks at that rate.

- [ ] **10. A pause starts the count over**
  - **Do:** Wait three seconds. Tap the pad once. Then tap it three times quickly, about three a second.
  - **Pass if:** The single tap after the pause flashes the pad and leaves the tempo where it was. The quick taps set it to about 180.

- [ ] **11. The same pad on page 2 is a drum**
  - **Do:** Press page 2, then tap the same pad, the second row's first, three times.
  - **Pass if:** It plays its drum each time, and the phone's tempo and the OLED's footer do not move. Press page 1 again: the pad is dim yellow there once more.

- [ ] **12. Link lost, and back**
  - **Do:** Load Cut It again from the Organelle menu, watching the phone. Touch nothing on the phone.
  - **Pass if:** The phone's link lamp goes out and reads no link while Cut It restarts, then lights and reads link again within a few seconds of it loading, and the phone turns to page 1. Nothing on the Organelle mentions the phone.
  - **Note:** A lost phone is the phone's to report, by its no link, and the Organelle says nothing (Brendan, 2026-11-03): under Pd 0.57 the socket survives a listener going away, so the old `net-link-down` warning could not fire and was taken out ([phone](../../ref/device/phone.md)). Reloading is the rig-side way to silence the heartbeat; closing TouchOSC would close the display too.

- [ ] **13. Setup turns the checklist page off and on**
  - **Need:** Test mode on, the phone's checklist page at the line check's step 2.
  - **Do:** Tap Setup, the Launchpad's bottom-left button. Then tap it again.
  - **Pass if:** At the first tap the page gives way to the Launchpad's page at once, and at the second it comes back at step 2, reading test mode on beside a lit teal lamp, again at once rather than half a second later.
  - **Note:** A flip sends a heartbeat at once, which is the "at once".

- [ ] **14. Test mode on, from the panel**
  - **Do:** Tap Setup to leave test mode. Then on the Organelle hold aux, press the second key from the bottom (the first black key), then let go of both. Watch the phone for ten seconds.
  - **Pass if:** The checklist page comes back at the step it was on, its label reading test mode on beside a lit teal lamp, and still reads it ten seconds later. The OLED shows a bordered box reading warn then u_net then test-mode-on for about two seconds.
  - **Note:** One press of the key can reach Cut It twice, 5 ms apart, which once turned test mode on and straight back off; a second flip within 300 ms is dropped (`phone-assert` holds it), and the ten seconds are this step's check that it held.

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
  - **Pass if:** The label reads no link while Cut It restarts. When the link is back, test mode is off and the page gives way to the arrangement screen. Tap Setup to bring it back.

- [ ] **18. A mode ends test mode, and the phone follows it**
  - **Need:** Test mode on, the phone's checklist page up.
  - **Do:** Press the Launchpad's page 2 button, the second down the left column. Then press page 3, the third.
  - **Pass if:** At page 2 the checklist page gives way at once to the drum screen, its tab reading drums; at page 3 the tab reads synths and shows the synths screen, FM and STRINGS, with the velocity switch under them.
  - **Note:** That a mode turns test mode off is `phone-assert`'s too (Brendan, 2026-11-04: staying on the checklists after a mode press was the weird part).

- [ ] **19. Tap tempo on the phone**
  - **Need:** Page 1 on the Launchpad, so the phone shows the arrangement page.
  - **Do:** Tap the phone's tap button about once a second, five times. Then wait three seconds and tap it twice, half a second apart.
  - **Pass if:** After the second tap the tempo reads about 60 and stays near it as you go on. After the pause the first tap changes nothing, and the second sets it to about 120.
  - **Note:** The phone times the taps itself, as your finger lands, by the tap pad's rules: four intervals averaged, starting over after two seconds. That the numbers come out right is `touchosc-assert`'s; this is whether the button answers a finger and the tempo it gives feels like your taps.

