# Sequencer checklist

Mode 1's drum page on the Launchpad, the sequencer playing the SP-404, and the pattern surviving a reload. `sequencer-assert` proves the notes, the frames and the file; what is left is what only the rig can show — whether the page reads, and what the 404 does with the notes.

12 steps. How to read one, and how to send a **Send** line: [the checklists' README](README.md). Why each thing behaves as it does: [sequencer](../../ref/module/sequencer.md).

- [ ] **1. The drum page**
  - **Need:** A fresh load of the patch with no saved pattern — the selection resets at every load and a saved step would be lit.
  - **Send:** `stop bang; mode compose mode-1`
  - **Pass if:** The left column has its top lamp bright. The top two rows of pads are the steps and the next two rows the velocity buttons — all dim but one velocity button. The bottom-left four by four is dim with its top-left pad lit and the bottom-right four by four is dark. No white pad walks along the bottom row.
  - **Note:** Level 13 is the second velocity row's fifth button; track 1 is the top-left drum pad. Both reset at every load ([sequencer](../../ref/module/sequencer.md)).

- [ ] **2. A drum pad plays and selects**
  - **Need:** Sounds in bank A of the 404 — the starter kit or anything else. The 404 on bank A so its pad lights too.
  - **Do:** Press the bottom-left drum pad.
  - **Pass if:** The 404 plays bank A pad 13 at once — louder for a harder press. That pad lights and the top-left one goes dim. The OLED draws no row for it.

- [ ] **3. Velocity buttons**
  - **Do:** Press the top-left velocity button, then the bottom-right one.
  - **Pass if:** Each press lights the button pressed and only that one. Nothing sounds and the OLED draws nothing.

- [ ] **4. Steps light by velocity**
  - **Do:** With the bottom-right velocity button lit press step 1. Pick the top-left velocity button and press step 2. Pick a velocity button in the middle and press step 3.
  - **Pass if:** Step 1 is bright and step 2 dark with step 3 between them — one color getting brighter with velocity. The steps left off stay dim.

- [ ] **5. The step rule**
  - **Do:** Pick the bottom-right velocity button and press step 1 twice. Then pick the top-left velocity button and press step 1 again.
  - **Pass if:** The first press turns step 1 off and the second turns it back on bright. The third makes it dark and leaves it on.

- [ ] **6. PLAY from step 1**
  - **Send:** `tempo 120; start bang`
  - **Pass if:** A white pad walks the top two rows from step 1 at four steps a beat. Pad 13 sounds on the steps you lit — softer on the dark ones. The white pad passes over a lit step and the step is still lit behind it.

- [ ] **7. Two tracks on one step**
  - **Do:** Press the top-left drum pad. Then press step 1 and step 9.
  - **Pass if:** Pad 1 sounds alone on step 9 and with pad 13 on step 1 — both are heard there and neither is dropped.

- [ ] **8. STOP**
  - **Send:** `stop bang`
  - **Pass if:** The sound stops and the white pad goes out. The steps stay lit.

- [ ] **9. Panic stops it too**
  - **Do:** Press PLAY on the nanoKONTROL. Then tap the top-left corner button of the Launchpad.
  - **Pass if:** Everything stops at once and the grid flashes red. When it clears the white pad is gone and the steps are still lit.

- [ ] **10. A one-shot pad on every step**
  - **Need:** Pad 13 of bank A set to one-shot on the 404 — not loop.
  - **Send:** `start bang`
  - **Do:** Select pad 13. Light all sixteen of its steps. Listen for a bar or two then turn knob 1 up and listen again.
  - **Pass if:** Every step is heard as a fresh hit — a hit cut short by the next one is fine. A step that falls silent is the failure: it means a one-shot pad toggles like a looping one.
  - **Note:** The blueprint's open question (cut-it/drum-machine): a looping pad toggles on a second note-on, and fast hats need a one-shot pad to restart instead.

- [ ] **11. The pattern survives a reload**
  - **Need:** Steps lit on the drum page from the steps before.
  - **Send:** `stop bang`
  - **Do:** Look at which steps are lit. Wait two seconds, then load Cut It again from the Organelle menu.
  - **Pass if:** After the reload the drum page shows the same steps lit as before it.
  - **Note:** `u_state` flushes within 2 seconds of a change, so the wait is part of the step.

- [ ] **12. Other modes keep their grid**
  - **Send:** `mode compose mode-2`
  - **Do:** Press a pad in the top two rows.
  - **Pass if:** The second lamp lights and the drum page gives way to the beat row along the bottom. A pad press draws a pad-NN row on the OLED again.
