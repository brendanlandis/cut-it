# Tempo checklist

The transport, knob 1's pickup and the clamp. Steps 1 to 10 set their tempo with **Send** lines; 11 to 14 are hands on the nanoKONTROL, knob 1, the tap pad and the phone. The tempo is read off the phone's arrangement screen: the OLED draws it only as knob 1's row while the knob moves (Brendan, 2026-11-04).

No beat-count steps: the `c_clock` ratio and the clock running on after a stop are `clock-assert`'s and `tempo-assert`'s, and the counts appear on no screen. One claim judged in two places reports more coverage than exists. No device follows the clock by ear since the SP-404 left the rig (2026-11-04), so no step listens for one.

14 steps. How to read one, and how to send a **Send** line: [the checklists' README](README.md). Why each thing behaves as it does: [tempo](../../ref/module/tempo.md).

- [ ] **1. Resting display at 120 BPM**
  - **Need:** The phone linked.
  - **Send:** `mode mode-1; tempo 120; stop bang`
  - **Pass if:** The OLED shows the info bar and nothing under it: no tempo anywhere on it. The phone's arrangement screen reads 120. The aux LED is dark blue.

- [ ] **2. Knob pickup on the first touch**
  - **Send:** `mode mode-1; tempo 120; param og-knob-1 0`
  - **Pass if:** The row reads bpm 57 (10) — the position knob 1 was saved at first and where the Send line has just put it in brackets — and the phone's tempo stays 120. The tempo is held until the real knob is turned back past where it was saved. If this rig has no knobs.txt the row reads bpm 120 (10) instead: knob 1 is held at 120 until it is turned through it. Either way the phone's tempo stays 120. The row must never read og-knob-1 and never a raw 0-to-1 decimal.
  - **Note:** The first number is the saved knob position, not the tempo: `u_map` draws the held row from the pickup target with the incoming value in the unit field, so knob 1 saved at 57 BPM draws `bpm 57 (10)`. The held case needs a knob saved off the rail: with `0 0 0 0` pickup releases at once, and the row and the phone's tempo read as if there were no `knobs.txt`.

- [ ] **3. Knob pickup crosses over**
  - **Send:** `mode mode-1; param og-knob-1 1`
  - **Pass if:** The row reads bpm 500 and the phone's tempo 500. About a second later the row ages out to the blank screen under the info bar. The knob has crossed where it was saved and is live from here on.

- [ ] **4. Knob tracking after pickup**
  - **Send:** `mode mode-1; param og-knob-1 0`
  - **Pass if:** The row reads bpm 10 and the phone's tempo 10. A row still reading 500 means the knob is stuck.

- [ ] **5. Tempo above range**
  - **Send:** `mode mode-1; tempo 5000; tempo 5000`
  - **Pass if:** The phone's tempo reads 600 and exactly one alert appears on the OLED — a bordered box naming u_tempo. The second 5000 is silent.

- [ ] **6. Tempo below range**
  - **Send:** `mode mode-1; tempo 0`
  - **Pass if:** The phone's tempo reads 5 and a second alert appears.

- [ ] **7. Back in range**
  - **Send:** `mode mode-1; tempo 120`
  - **Pass if:** The phone's tempo reads 120 and no alert appears at all.

- [ ] **8. Start the transport**
  - **Send:** `start bang`
  - **Pass if:** The aux LED turns green, and the OLED still shows the info bar alone.

- [ ] **9. Stop the transport**
  - **Send:** `stop bang`
  - **Pass if:** The aux LED goes dark blue, and the OLED still shows the info bar alone.

- [ ] **10. Panic**
  - **Send:** `panic bang`
  - **Pass if:** The aux LED turns red, and the OLED shows the info bar alone: panic is the LED's and the grid's to show (Brendan, 2026-11-04).

- [ ] **11. Transport from PLAY and STOP**
  - **Do:** Press PLAY on the nanoKONTROL, then STOP.
  - **Pass if:** PLAY turns the aux LED green and STOP turns it dark blue.
  - **Note:** The aux button is the keyboard's modifier (item 305); the nano's PLAY and STOP are the transport in every mode.

- [ ] **12. Knob 1 tempo sweep**
  - **Do:** Sweep knob 1 all the way and back.
  - **Pass if:** The row reads bpm and a number that tracks the knob between 10 and 500 BPM. It never reads og-knob-1 and never a raw 0-to-1 decimal.
  - **Note:** No bracketed second number: the knob was released in step 3 and is live. The held format is step 2's.

- [ ] **13. Nothing Saved: knob 1 starts held at 120**
  - **Need:** No knobs.txt in Cut It's folder: no Save since the last `tools/deploy.sh --clean`. Knob 1 turned well down, toward 8 o'clock.
  - **Do:** Load Cut It from the Organelle's menu, wait for the boot's words to clear, then turn knob 1 slowly up past 12 o'clock.
  - **Pass if:** The phone's tempo reads 120 wherever knob 1 sits. Turning it, the row reads bpm 120 and the knob's own tempo in brackets until the knob passes just before 12 o'clock; from there the row follows the knob.
  - **Note:** 0.48 of the knob's turn is 120 on its curve ([map](../../ref/module/map.md), *Parameter pickup*). With a knobs.txt the saved position is restored instead, as in step 2.

- [ ] **14. Knob 1 waits for a tapped tempo, and for the phone's**
  - **Need:** Page 1 chosen on the Launchpad, the phone linked, and knob 1 live: turned through where it was held, as in step 3 or 13.
  - **Do:** Tap the tap pad four times, about two a second. Then turn knob 1 a little either way. Then drag the phone's tempo to 160 and turn knob 1 a little again.
  - **Pass if:** From the second tap the phone's tempo reads about 120. Knob 1's first turn after the taps reads bpm and that tempo with the knob's own in brackets, and the phone's tempo does not move until the knob is turned through it; from there the row and the phone follow the knob. After the drag the same: bpm 160 with the knob's own in brackets, until it passes 160.
  - **Note:** A tap or the phone sets the tempo, and knob 1 is held there until turned through it, as knob 2 is held at the phone's last step (Brendan, 2026-11-04; [tempo](../../ref/module/tempo.md)). Without the hold its first turn would jump the tempo back to wherever the knob sits.
