# Phone checklist

Every **Pass if** here describes the phone, not the Organelle. Steps 8 to 11 are the ones whose correct result is that nothing happens: the meters, the grid vocabulary and the aux LED are all on `disp` and all dropped by `u_net`, so a line reading in-l means the rate budget has gone to a meter the phone does not draw.

The rate limit is `phone-assert`'s: a checklist cannot flood, and step 12's fast sweep is the closest a person gets. Steps 13 and 14 are the only way to reach item 114 on hardware: under Pd 0.49 closing PdParty destroyed the socket, and reopening it must bring the display back with nothing touched on the Organelle. Under 0.57 the socket survives on the device too, so step 13's warn no longer comes (below). Steps 19 to 23 are the checklist page, CutItChecks, and test mode; run them from that page.

23 steps. How to read one, and how to send a **Send** line: [the checklists' README](README.md). Why each thing behaves as it does: [phone](../../ref/device/phone.md).

- [ ] **1. The link is up**
  - **Need:** PdParty open on the CutItRemote scene and on the same network. A NO-LINK here means nothing below can be judged.
  - **Send:** `mode compose mode-1`
  - **Pass if:** The bottom line of the phone reads ok rather than NO-LINK.

- [ ] **2. One parameter**
  - **Send:** `disp chop-size 43 %`
  - **Pass if:** The top line reads chop-size and the big number reads 43 on its own. The unit is not drawn and that is correct.

- [ ] **3. A second parameter**
  - **Send:** `disp grain 12`
  - **Pass if:** The top line changes to grain and the number to 12 with it.

- [ ] **4. The status line**
  - **Send:** `disp status 128-bpm`
  - **Pass if:** The third line reads 128-bpm and the parameter name and number above it do not change. u_tempo overwriting it with the real BPM at the next transport event is correct.

- [ ] **5. An alert reaches the phone**
  - **Send:** `err warn u_bench probe-warning`
  - **Pass if:** The fourth line shows warn on the left and probe-warning on the right.

- [ ] **6. The alert persists**
  - **Pass if:** Several seconds later the fourth line still reads warn and probe-warning. On the OLED the same alert has long since timed out. The two surfaces disagree on purpose.

- [ ] **7. A second alert replaces it**
  - **Send:** `err fail u_bench probe-failure`
  - **Pass if:** The fourth line changes to fail and probe-failure.

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

- [ ] **13. Link lost**
  - **Do:** Close PdParty on the phone and count to ten. u_net warns once per load, so this has to be the first time the link has dropped since Cut It was loaded.
  - **Pass if:** A bordered box reads warn then u_net then net-link-down. Nothing else on the Organelle changes.
  - **Note:** ⛔ **Fails under Pd 0.57, by design of 0.57, not of Cut It:** the warn was `u_net`'s watchdog seeing the socket die when nothing listened on the phone's port, and under 0.57 the socket survives on the device too (measured 2026-11-03, [phone](../../ref/device/phone.md)). So nothing appears on the Organelle, and the phone's own NO-LINK is the only report. How Cut It should notice a lost phone now is Brendan's to decide (cut-it/inbox); until then, record this step as failing for that reason. Step 1 left the rig in compose, where `u_err` would show it.

- [ ] **14. Link recovers**
  - **Do:** Reopen PdParty on the phone. Touch nothing on the Organelle.
  - **Pass if:** The phone starts updating again within about five seconds and you touched nothing on the Organelle.
  - **Note:** Under Pd 0.57 the socket never died, so this is PdParty binding its port again rather than `u_net` reconnecting; it should come back within a heartbeat or two.

- [ ] **15. The re-wire button**
  - **Need:** PdParty OSC send host and port pointed at the Organelle, port 9001. Without it every button below is silent and nothing says so.
  - **Do:** Tap re-wire on the phone.
  - **Pass if:** The small lamp beside the button flashes. Nothing else on the Organelle changes.
  - **Note:** The lamp is lit by the Organelle's answer, so a flash means the command arrived and was accepted. That the re-wire's fork reaches the log is `presence-assert`'s.

- [ ] **16. The clear-alert button**
  - **Do:** Tap clear-alert on the phone. Step 7 left a fail showing there — if the row is already empty raise one first.
  - **Pass if:** The fourth line goes back to none on the left and a dash on the right. The lamp beside the button flashes.

- [ ] **17. The Volca test note**
  - **Do:** Tap test-volca on the phone and listen.
  - **Pass if:** The Volca sounds one short note. The lamp beside the button flashes.

- [ ] **18. The SP-404 test note**
  - **Do:** Tap test-404 on the phone and listen.
  - **Pass if:** The SP-404 plays pad A1. The lamp beside the button flashes.

- [ ] **19. A Send line is refused while test mode is off**
  - **Need:** Cut It just loaded from the Organelle menu, which turns test mode off, and this step open on the checklist page (CutItChecks) in PdParty.
  - **Send:** `disp chop-size 43 %`
  - **Pass if:** Nothing on the Organelle changes: no chop-size row. The page's label at the top right still reads test mode off, on amber, and the Send button does not turn green.
  - **Note:** The label is the Organelle's own state, carried on the heartbeat, so it reads no link, on red, until the first heartbeat arrives and after 3 s with none. That a refused line reaches nothing is `phone-assert`'s; this is the page and the rig agreeing.

- [ ] **20. Test mode on, from the panel**
  - **Do:** On the Organelle hold aux, press the second key from the bottom (the first black key), then let go of both. Watch the page's label for ten seconds.
  - **Pass if:** The label turns green and reads test mode on, and still reads it ten seconds later. In compose the OLED shows a bordered box reading warn then u_net then test-mode-on for about two seconds; in perform it shows nothing.
  - **Note:** One press of the key can reach Cut It twice, 5 ms apart, which once turned test mode on and straight back off; a second flip within 300 ms is dropped (`phone-assert` holds it), and the ten seconds are this step's check that it held.

- [ ] **21. A Send line goes through in test mode**
  - **Need:** Test mode on, as step 20 left it.
  - **Send:** `disp chop-size 43 %`
  - **Pass if:** The Send button flashes green, and the Organelle's top line reads chop-size with a big 43 % under it.
  - **Note:** Green is the Organelle's answer, not the press: the press only darkens the button.

- [ ] **22. Pass is logged on the Organelle**
  - **Do:** Press Pass on this step.
  - **Check:** `./tools/fetch-errors.sh` on the Mac.
  - **Pass if:** The page moves on to step 23, and the log's newest lines include info phone phone-22-pass. Back to this step shows it marked passed.

- [ ] **23. A reload turns test mode off**
  - **Need:** Test mode on.
  - **Do:** Load Cut It again from the Organelle menu, and watch the page's label.
  - **Pass if:** The label reads no link while Cut It restarts, then test mode off, on amber.
