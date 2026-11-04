# Phone checklist

Every **Pass if** here describes the phone, not the Organelle. Steps 8 to 11 are the ones whose correct result is that nothing happens: the meters, the grid vocabulary and the aux LED are all on `disp` and all dropped by `u_net`, so a line reading in-l means the rate budget has gone to a meter the phone does not draw.

The rate limit is `phone-assert`'s: a checklist cannot flood, and step 12's fast sweep is the closest a person gets. Step 13 is the link going and coming back, reported by the phone's own no link. Steps 1 to 17 judge the phone's screens, which the checklist page covers in test mode, so send their lines from the Mac with `tools/send.sh`, which needs no test mode. Steps 18 to 22 are the checklist page and test mode. The page holds the line check, not these steps, so run them from here like the rest. Step 23 is the tab following the mode, and a mode ending test mode.

23 steps. How to read one, and how to send a **Send** line: [the checklists' README](README.md). Why each thing behaves as it does: [phone](../../ref/device/phone.md).

- [ ] **1. The link is up**
  - **Need:** TouchOSC open on the phone with Cut It's layout, on the same network. A no link here means nothing below can be judged.
  - **Send:** `mode compose mode-2`
  - **Pass if:** The phone's tab reads remote and shows the remote screen, and its link lamp is lit teal beside the word link rather than no link.

- [ ] **2. One parameter**
  - **Send:** `disp chop-size 43 %`
  - **Pass if:** The top line reads chop-size and the big red number under it reads 43 %, the unit beside the number.

- [ ] **3. A second parameter**
  - **Send:** `disp grain 12`
  - **Pass if:** The top line changes to grain and the number to 12 with it.

- [ ] **4. The status line**
  - **Send:** `disp status 128-bpm`
  - **Pass if:** The tempo line reads 128 bpm and the parameter name and number above it do not change. u_tempo overwriting it with the real BPM at the next transport event is correct.

- [ ] **5. An alert reaches the phone**
  - **Send:** `err warn u_bench probe-warning`
  - **Pass if:** The alert line lights its red lamp and reads warn  probe-warning in red.

- [ ] **6. The alert persists**
  - **Pass if:** Several seconds later the alert line still reads warn  probe-warning. On the OLED the same alert has long since timed out. The two surfaces disagree on purpose.

- [ ] **7. A second alert replaces it**
  - **Send:** `err fail u_bench probe-failure`
  - **Pass if:** The alert line changes to fail  probe-failure.

- [ ] **8. Meters must not appear**
  - **Send:** `disp in-l 42 dB; disp in-r 7 dB`
  - **Pass if:** Nothing on the phone changes at all. A line reading in-l or in-r is the failure.

- [ ] **9. Grid vocabulary must not appear**
  - **Send:** `disp grid modal 45`
  - **Pass if:** Nothing on the phone changes. The Launchpad going modal is correct and the next step clears it.

- [ ] **10. Clearing the grid**
  - **Send:** `disp grid modal-off`
  - **Pass if:** The Launchpad returns to its home layout and the phone does not move.

- [ ] **11. The aux LED**
  - **Send:** `disp led running`
  - **Pass if:** The aux LED goes green and the phone does not move.

- [ ] **12. Fast fader sweep**
  - **Do:** Sweep a nanoKONTROL fader as fast as you can. Two at once if you have the fingers — both must settle.
  - **Pass if:** The phone tracks the fader while it moves and settles on the value you stopped at. A number left over from the middle of the sweep is the failure.

- [ ] **13. Link lost, and back**
  - **Do:** Load Cut It again from the Organelle menu, watching the phone. Touch nothing on the phone.
  - **Pass if:** The phone's link lamp goes out and reads no link while Cut It restarts, then lights and reads link again within a few seconds of it loading. Nothing on the Organelle mentions the phone.
  - **Note:** A lost phone is the phone's to report, by its no link, and the Organelle says nothing (Brendan, 2026-11-03): under Pd 0.57 the socket survives a listener going away, so the old `net-link-down` warning could not fire and was taken out ([phone](../../ref/device/phone.md)). Reloading is the rig-side way to silence the heartbeat; closing TouchOSC would close the display too.

- [ ] **14. The re-wire button**
  - **Need:** TouchOSC's OSC connection sending to the Organelle, `192.168.1.15` port 9001. Without it every button below is silent and nothing says so, while everything the phone shows still works.
  - **Do:** Tap re-wire on the phone.
  - **Pass if:** The button flashes teal. Nothing else on the Organelle changes.
  - **Note:** The teal is the Organelle's answer, so a flash means the command arrived and was accepted; the brief fill under the finger is TouchOSC's own. That the re-wire's fork reaches the log is `presence-assert`'s.

- [ ] **15. The clear-alert button**
  - **Do:** Tap clear-alert on the phone. Step 7 left a fail showing there — if the row is already empty raise one first.
  - **Pass if:** The alert line goes back to no alerts, in grey, its lamp out. The button flashes teal.

- [ ] **16. The Volca test note**
  - **Do:** Tap test-volca on the phone and listen.
  - **Pass if:** The Volca sounds one short note. The button flashes teal.

- [ ] **17. The SP-404 test note**
  - **Do:** Tap test-404 on the phone and listen.
  - **Pass if:** The SP-404 plays pad A1. The button flashes teal.

- [ ] **18. Setup turns the checklist page off and on**
  - **Need:** Test mode on, the phone's checklist page at the line check's step 2.
  - **Do:** Tap Setup, the Launchpad's bottom-left button. Then tap it again.
  - **Pass if:** At the first tap the page gives way to the phone's screen at once, and at the second it comes back at step 2, reading test mode on beside a lit teal lamp, again at once rather than half a second later.
  - **Note:** A flip sends a heartbeat at once, which is the "at once".

- [ ] **19. Test mode on, from the panel**
  - **Do:** Tap Setup to leave test mode. Then on the Organelle hold aux, press the second key from the bottom (the first black key), then let go of both. Watch the phone for ten seconds.
  - **Pass if:** The checklist page comes back at the step it was on, its label reading test mode on beside a lit teal lamp, and still reads it ten seconds later. In compose the OLED shows a bordered box reading warn then u_net then test-mode-on for about two seconds; in perform it shows nothing.
  - **Note:** One press of the key can reach Cut It twice, 5 ms apart, which once turned test mode on and straight back off; a second flip within 300 ms is dropped (`phone-assert` holds it), and the ten seconds are this step's check that it held.

- [ ] **20. The page holds the line check**
  - **Need:** Test mode on, as step 19 left it.
  - **Do:** On the page, tap Back until it stops, then Next through every step.
  - **Pass if:** Its tab reads line check. It starts at 1 of 9, The phone and the Launchpad, and ends at 9 of 9, each step's text whole on its page. No Send button shows on any step, and nothing picks another checklist.
  - **Note:** The page carries test/checklists/linecheck.md alone, and the phone sends nothing onto Cut It's buses (Brendan, 2026-11-04); that `send` is no command any more is `phone-assert`'s. Steps 18 to 23 here run from the Mac, like the rest.

- [ ] **21. Pass is logged on the Organelle**
  - **Do:** On the page, go to the line check's step 1 and press Pass.
  - **Check:** `./tools/fetch-errors.sh` on the Mac.
  - **Pass if:** Pass flashes, the page moves on to step 2, and the log's newest lines include info phone linecheck-1-pass. Back to step 1 shows passed after its position.

- [ ] **22. A reload turns test mode off**
  - **Need:** Test mode on.
  - **Do:** Load Cut It again from the Organelle menu, and watch the page's label.
  - **Pass if:** The label reads no link while Cut It restarts. When the link is back, test mode is off and the page gives way to the phone's screen. Tap Setup to bring it back.

- [ ] **23. A mode ends test mode, and the tab follows it**
  - **Need:** Test mode on, the phone's checklist page up.
  - **Do:** Press the Launchpad's mode 1 button, the top of the left column. Then press mode 3, the third.
  - **Pass if:** At mode 1 the checklist page gives way at once to the drum screen, its tab reading drums; at mode 3 the tab reads remote and shows the remote screen.
  - **Note:** That a mode turns test mode off is `phone-assert`'s too (Brendan, 2026-11-04: staying on the checklists after a mode press was the weird part).
