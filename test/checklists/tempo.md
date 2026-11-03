# Tempo checklist

The transport, knob 1's pickup, the clamp and the SP-404 following the clock. Steps 1 to 11 set their tempo with **Send** lines; 12 and 13 are hands on the nanoKONTROL and knob 1.

No beat-count steps: the `c_clock` ratio and the clock running on after a stop are `clock-assert`'s and `tempo-assert`'s, and the counts appear on no screen. One claim judged in two places reports more coverage than exists.

13 steps. How to read one, and how to send a **Send** line: [the checklists' README](README.md). Why each thing behaves as it does: [tempo](../../ref/module/tempo.md), [sp404](../../ref/device/sp404.md).

- [ ] **1. Resting display at 120 BPM**
  - **Send:** `tempo 120; stop bang`
  - **Pass if:** Two meter bars each with a small gate mark under it and 120-bpm in the footer. The aux LED is dark blue.

- [ ] **2. Knob pickup on the first touch**
  - **Send:** `tempo 120; param og-knob-1 0`
  - **Pass if:** The row reads bpm 57 (10) — the position knob 1 was saved at first and where the Send line has just put it in brackets — and the footer stays 120-bpm. The tempo is held until the real knob is turned back past where it was saved. If this rig has no knobs.txt the row reads bpm 10 and the footer follows down to 10-bpm instead. The row must never read og-knob-1 and never a raw 0-to-1 decimal.
  - **Note:** The first number is the saved knob position, not the tempo: `u_map` draws the held row from the pickup target with the incoming value in the unit field, so a `knobs.txt` of 0.0957967 draws `bpm 57 (10)`. The held case needs a knob saved off the rail: with `0 0 0 0` pickup releases at once, and the row and the footer read as if there were no `knobs.txt`.

- [ ] **3. Knob pickup crosses over**
  - **Send:** `param og-knob-1 1`
  - **Pass if:** The row reads bpm 500 and about a second later it ages out to show the footer underneath reading 500-bpm. The knob has crossed where it was saved and is live from here on.
  - **Note:** The row covers the footer (the param layer replaces home), so the footer is read once the row ages out.

- [ ] **4. Knob tracking after pickup**
  - **Send:** `param og-knob-1 0`
  - **Pass if:** The row reads bpm 10 and the footer underneath reads 10-bpm once it ages out. A row still reading 500 means the knob is stuck.

- [ ] **5. Tempo above range**
  - **Send:** `tempo 5000; tempo 5000`
  - **Pass if:** The footer reads 600-bpm and exactly one alert appears — a bordered box naming u_tempo. The second 5000 is silent.

- [ ] **6. Tempo below range**
  - **Send:** `tempo 0`
  - **Pass if:** The footer reads 5-bpm and a second alert appears.

- [ ] **7. Back in range**
  - **Send:** `tempo 120`
  - **Pass if:** The footer reads 120-bpm and no alert appears at all.

- [ ] **8. Start the transport**
  - **Need:** The SP-404 on Pattern Select with a pattern loaded and nothing playing.
  - **Send:** `start bang`
  - **Pass if:** The aux LED turns green and the 404 starts its selected pattern in time with it. The 404's screen shows an EXT tempo. The number beside a pad never moves.
  - **Note:** Start (250) moves the 404's sequencer only with a pattern loaded ([sp404](../../ref/device/sp404.md)); without one nothing on either device says why. The two steps after this one inherit the state.

- [ ] **9. The 404 follows a tempo change**
  - **Send:** `tempo 180`
  - **Pass if:** The 404's EXT slides up to 180 rather than snapping and its pattern speeds up to match. The OLED fills with rows named for the pads it plays — sp-a1 and the like — and that is correct. Those rows cover the footer so the new tempo is not readable there until the transport stops.
  - **Note:** 180, not 240: the 404 follows only between 40 and 200 BPM ([sp404](../../ref/device/sp404.md)). No footer claim here: the pad rows raise the param layer, which hides it, so step 10 reads the footer instead.

- [ ] **10. Stop the transport**
  - **Send:** `tempo 120; stop bang`
  - **Pass if:** The aux LED goes dark blue and the 404 stops but its screen still reads EXT. Falling back to BPM is the failure. The pad rows stop arriving and the OLED settles back to the meters with 120-bpm in the footer.

- [ ] **11. Panic**
  - **Send:** `panic bang`
  - **Pass if:** The aux LED turns red and the footer reads panic.

- [ ] **12. Transport from PLAY and STOP**
  - **Do:** Press PLAY on the nanoKONTROL, then STOP.
  - **Pass if:** PLAY turns the aux LED green and the 404 starts. STOP turns it dark blue and the 404 stops.
  - **Note:** The aux button is the keyboard's modifier (item 305); the nano's PLAY and STOP are the transport in every mode.

- [ ] **13. Knob 1 tempo sweep**
  - **Do:** Sweep knob 1 all the way and back.
  - **Pass if:** The row reads bpm and a number that tracks the knob between 10 and 500 BPM. It never reads og-knob-1 and never a raw 0-to-1 decimal. The 404 follows the sweep.
  - **Note:** No bracketed second number: the knob was released in step 3 and is live. The held format is step 2's.
