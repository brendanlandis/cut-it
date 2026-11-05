# Display checklist

The OLED's layers and the error bus, as a person sees them. `oled-assert` and `err-assert` prove the words, the order and the timeouts headlessly; this is whether the screen reads. Steps 2 to 13 put their picture on the buses with **Send** lines; 1 and 14 to 18 are hands on the rig.

18 steps. How to read one, and how to send a **Send** line: [the checklists' README](README.md). Why each thing behaves as it does: [display](../../ref/module/display.md), [error](../../ref/module/error.md).

- [ ] **1. Resting display**
  - **Do:** Load Cut It from the Organelle's menu and wait for the boot's words to clear.
  - **Pass if:** Two wide bars, one over the screen's top half and one over its bottom half, each with a small readout above it: out-l over the first and out-r over the second. Nothing else: no tempo, no version, no marks under the bars. With nothing playing both bars sit at their left edge.
  - **Note:** The OLED is for alerts and warnings, the output's levels and the name of a control as it moves (Brendan, 2026-11-04): the tempo is the phone's, and a panic the LED's and the grid's ([display](../../ref/module/display.md)).

- [ ] **2. Parameter with a unit**
  - **Send:** `disp chop-size 43 %`
  - **Pass if:** chop-size on the top line and a big 43 % under it. The bars shrink to a thin strip. About 1.2 s later the meters come back on their own.

- [ ] **3. Parameter with no unit**
  - **Send:** `disp grain 12`
  - **Pass if:** grain and then a big 12 with no percent sign left over from the last step.

- [ ] **4. Two parameters**
  - **Send:** `disp chop-size 43 %; disp grain 12`
  - **Pass if:** Two stacked pairs — chop-size over 43 % on top and grain over 12 below. First touched on top. The values are mid-sized.

- [ ] **5. Five parameters**
  - **Send:** `disp chop-size 43 %; disp grain 12; disp slider-1 64; disp knob-3 100; disp btn-t-2 1`
  - **Pass if:** Five small lines in the order they were first touched: chop-size then grain then slider-1 then knob-3 then btn-t-2.

- [ ] **6. Seven parameters — two too many**
  - **Send:** `disp a1 1; disp a2 2; disp a3 3; disp a4 4; disp a5 5; disp a6 6; disp a7 7`
  - **Pass if:** Still exactly five lines — a1 a2 a3 a4 a5. a6 and a7 are refused rather than pushing the rows around. Nothing shifts.

- [ ] **7. A single parameter is drawn big**
  - **Send:** `disp a1 1`
  - **Pass if:** a1 alone on screen at the big 24px layout. One parameter is drawn big where five are drawn as small lines.

- [ ] **8. Modal**
  - **Send:** `disp modal recording`
  - **Pass if:** recording in mid-size text with the bars as a thin strip. It stays and does not fade.

- [ ] **9. Parameter under a modal**
  - **Send:** `disp modal recording; disp chop-size 43 %`
  - **Pass if:** Nothing changes. Still recording. chop-size never appears.

- [ ] **10. Warning over a modal**
  - **Send:** `disp modal recording; err warn u_root test-warn`
  - **Pass if:** A bordered box reads warn then u_root then test-warn. About 2 s later it vanishes and recording is back underneath.

- [ ] **11. A warning on any page**
  - **Send:** `disp modal recording; mode mode-5; err warn u_root page-5`
  - **Pass if:** A bordered box reads warn then u_root then page-5. About 2 s later it vanishes and recording is back underneath. Nothing on the OLED names the page.
  - **Note:** Every page draws every warning and failure (Brendan, 2026-11-04); `err-assert` proves it on each kind of page, and this is the box reading on the rig.

- [ ] **12. Clearing the modal**
  - **Send:** `disp modal recording; disp modal-off`
  - **Pass if:** recording disappears. You are back to the two meters and nothing else.

- [ ] **13. Modal safety timeout**
  - **Send:** `disp modal stuck`
  - **Pass if:** stuck appears in mid-size text and stays.

- [ ] **14. Modal safety timeout — the wait**
  - **Do:** Wait 30 seconds without touching anything.
  - **Pass if:** The screen went back to the meters on its own with nothing touched.

- [ ] **15. Shifted stop with the nano unplugged**
  - **Need:** The nanoKONTROL unplugged. The clock running — press PLAY on the nano before unplugging it.
  - **Do:** Hold the aux button and press the middle key.
  - **Pass if:** The clock stops. The beat row on the Launchpad stops walking.
  - **Note:** Judged with a device actually gone: the Organelle's own panel can still stop the rig.

- [ ] **16. The diag roster**
  - **Do:** Hold the aux button and press the lowest key. Look hardest at the longest line: m_launchpad unchecked is exactly as wide as a row gets, so that is where clipping would show first. The word shift is on screen while aux is held and the roster draws over it.
  - **Pass if:** Six small lines naming m_launchpad m_nano m_organelle m_volca m_streich and m_nanokey — each with here or gone or never or unchecked beside it — over two thin bars at the bottom that still move with the output. Every line is readable at arm reach, the sixth sits clear of the bars, and none is cut off at the right edge. About eight seconds later the meters come back on their own.
  - **Note:** `oled-assert` proves the roster's words, their order and where the rows and bars are drawn; whether six 8px rows read at arm's length, the sixth just above the 4 px bars, and whether the 21-character `m_launchpad unchecked` line is clipped, is a person's call ([display](../../ref/module/display.md)). m_nanokey reads never until a key has been played since the load.

- [ ] **17. The meters are the output**
  - **Need:** The SM58 in the Organelle's input, the drum samples deployed, and the mixer's channels 1 and 2 up.
  - **Do:** Press page 2 and hit the bottom-left drum pad a few times. Then talk into the SM58. Then press nothing and wait.
  - **Pass if:** out-l's bar jumps with each hit and moves with your voice, and out-r's stays at its left edge throughout. Silent, both bars sit at their left edge. Nothing under either bar marks a level.
  - **Note:** The meters are what Cut It sends to its two outputs, read where `u_root` throws them: the mic passed through and, on the left, the drums (Brendan, 2026-11-04). A bar that never moves while the PA plays is the meter and not the sound; one that moves while the PA is silent is a cable or the mixer. `audio-assert` proves by the signal which side each reads ([audio](../../ref/module/audio.md)).

- [ ] **18. Only a mapped control names itself**
  - **Need:** The nanoKONTROL plugged in.
  - **Send:** `mode mode-3`
  - **Do:** Move fader 1, then fader 2. Then turn the Organelle's knob 2 a little, then knob 3.
  - **Pass if:** Fader 1 draws volca-cc41 and its value, and knob 2 last-step and a step, with the knob's own in brackets while it is held. Fader 2 and knob 3 draw nothing. No row reads slider-1, slider-2 or og-knob anything.
  - **Note:** A control names itself by its destination's name, and only when the page binds it (Brendan, 2026-11-04): fader 1 is the Volca's CC 41 on page 3, knob 2 the drums' last step on every page, and fader 2 and knob 3 are bound to nothing here ([map](../../ref/module/map.md)).
