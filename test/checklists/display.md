# Display checklist

The OLED's layers and the error bus, as a person sees them. `oled-assert` and `err-assert` prove the words, the order and the timeouts headlessly; this is whether the screen reads. Steps 2 to 13 put their picture on the buses with **Send** lines; 14 to 16 are hands on the rig.

16 steps. How to read one, and how to send a **Send** line: [the checklists' README](README.md). Why each thing behaves as it does: [display](../../ref/module/display.md), [error](../../ref/module/error.md).

- [ ] **1. Resting display**
  - **Pass if:** Two bars with a small gate mark under each. A BPM at the bottom. The footer changes from v0.3-ready to the tempo about four seconds in.

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
  - **Pass if:** recording disappears. You are back to the two meters and the BPM footer.

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
  - **Pass if:** Four small lines naming m_launchpad m_nano m_organelle and m_volca — each with here or gone or never or unchecked beside it. Every line is readable at arm reach and none is cut off at the right edge. About eight seconds later the meters come back on their own.
  - **Note:** `oled-assert` proves the roster's words and their order; whether four 8px rows read at arm's length, and whether the 21-character `m_launchpad unchecked` line is clipped, is a person's call ([display](../../ref/module/display.md)).
