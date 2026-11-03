# Phone checklist

Every **Pass if** here describes the phone, not the Organelle. Steps 8 to 11 are the ones whose correct result is that nothing happens: the meters, the grid vocabulary and the aux LED are all on `disp` and all dropped by `u_net`, so a line reading in-l means the rate budget has gone to a meter the phone does not draw.

The rate limit is `phone-assert`'s: a checklist cannot flood, and step 12's fast sweep is the closest a person gets. Steps 13 and 14 are the only way to reach item 114 on hardware: closing PdParty destroys the socket, and reopening it must bring the display back with nothing touched on the Organelle.

18 steps. How to read one, and how to send a **Send** line: [the checklists' README](README.md). Why each thing behaves as it does: [phone](../../ref/device/phone.md).

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
  - **Note:** The warn is the action working: `u_net`'s watchdog watches the socket, which dies when nothing listens on the phone's port ([phone](../../ref/device/phone.md)). Step 1 left the rig in compose, where `u_err` shows it. Under Pd 0.57 a UDP socket outlives a closed listener on the Mac, so this warn, and step 14 with it, may no longer come on the device either; untested there (cut-it/pd-057).

- [ ] **14. Link recovers**
  - **Do:** Reopen PdParty on the phone. Touch nothing on the Organelle.
  - **Pass if:** The phone starts updating again within about five seconds and you touched nothing on the Organelle.

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
