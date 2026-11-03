# Sequencer checklist

Mode 1's drum page on the Launchpad, the sequencer playing the SP-404, and the pattern surviving a reload. `sequencer-assert` proves the notes, the frames and the file; what is left is what only the rig can show — whether the page reads, and what the 404 does with the notes.

13 steps. How to read one, and how to send a **Send** line: [the checklists' README](README.md). Why each thing behaves as it does: [sequencer](../../ref/module/sequencer.md).

- [ ] **1. The drum page**
  - **Need:** A fresh load of the patch with no saved pattern — the selection resets at every load and a saved step would be lit.
  - **Send:** `stop bang; mode compose mode-1`
  - **Pass if:** The left column has its top lamp bright. The top two rows of pads are the steps, all dim, and the two rows under them are dark. The bottom-left four by four is dim with its top-left pad lit. The right halves of the bottom two rows are the eight velocity buttons — white at the top left to red at the bottom right, with the second one on the bottom row brighter than the rest and the lit drum pad in its color. The top half of the right four by four is dark, and nothing walks along the bottom row.
  - **Note:** Level 6 is the bottom row's second velocity button; track 1 is the top-left drum pad. Both reset at every load ([sequencer](../../ref/module/sequencer.md)).

- [ ] **2. A drum pad plays and selects**
  - **Need:** Sounds in bank A of the 404 — the starter kit or anything else. The 404 on bank A so its pad lights too.
  - **Do:** Press the bottom-left drum pad.
  - **Pass if:** The 404 plays bank A pad 13 at once — louder for a harder press. That pad lights in the selected velocity's color and the top-left one goes dim. The OLED draws no row for it.

- [ ] **3. Velocity buttons**
  - **Do:** Press the top-left velocity button, then the bottom-right one.
  - **Pass if:** Each press brightens the button pressed and dims the one before, and the lit drum pad takes its color — white, then red. Nothing sounds and the OLED draws nothing.

- [ ] **4. Steps light by velocity**
  - **Do:** With the bottom-right velocity button selected press step 1. Pick the top-left velocity button and press step 2. Pick a velocity button in between and press step 3.
  - **Pass if:** Each step takes the color of the button that made it: step 2 white, step 1 red and step 3 between them. All eight buttons read as different colors. The steps left off stay dim.

- [ ] **5. The step rule**
  - **Do:** Pick the bottom-right velocity button and press step 1 twice. Then pick the top-left velocity button and press step 1 twice more.
  - **Pass if:** The first press turns step 1 off and the second turns it back on red. The third turns it off though another velocity is picked, and the fourth turns it back on white.

- [ ] **6. PLAY from step 1**
  - **Send:** `tempo 120; start bang`
  - **Pass if:** A green pad walks the top two rows from step 1 at four steps a beat. Pad 13 sounds on the steps you lit — softer on the white ones. The green pad passes over a lit step and the step is still lit behind it.

- [ ] **7. Two tracks on one step**
  - **Do:** Press the top-left drum pad. Then press step 1 and step 9.
  - **Pass if:** Pad 1 sounds alone on step 9 and with pad 13 on step 1 — both are heard there and neither is dropped.

- [ ] **8. The last step**
  - **Do:** With it still playing, turn knob 2 down until the screen reads last-step 4. Then turn it all the way up.
  - **Pass if:** At last-step 4 the green pad walks steps 1 to 4 only. Steps 5 to 16 go dark where they were empty, lit ones stay lit and are not heard. All the way up the row reads last-step 16 and the walk covers all sixteen steps again.

- [ ] **9. STOP**
  - **Send:** `stop bang`
  - **Pass if:** The sound stops and the green pad goes out. The steps stay lit.

- [ ] **10. Panic stops it too**
  - **Do:** Press PLAY on the nanoKONTROL. Then tap the top-left corner button of the Launchpad.
  - **Pass if:** Everything stops at once and the grid flashes red. When it clears the green pad is gone and the steps are still lit.

- [ ] **11. A one-shot pad on every step**
  - **Need:** Pad 13 of bank A set to one-shot on the 404 — not loop.
  - **Send:** `start bang`
  - **Do:** Select pad 13. Light all sixteen of its steps. Listen for a bar or two then turn knob 1 up and listen again.
  - **Pass if:** Every step is heard as a fresh hit — a hit cut short by the next one is fine. A step that falls silent is the failure: it means a one-shot pad toggles like a looping one.
  - **Note:** The blueprint's open question (cut-it/drum-machine): a looping pad toggles on a second note-on, and fast hats need a one-shot pad to restart instead.

- [ ] **12. The pattern survives a reload**
  - **Need:** Steps lit on the drum page from the steps before.
  - **Send:** `stop bang`
  - **Do:** Look at which steps are lit. Wait two seconds, then load Cut It again from the Organelle menu.
  - **Pass if:** After the reload the drum page shows the same steps lit as before it.
  - **Note:** `u_state` flushes within 2 seconds of a change, so the wait is part of the step.

- [ ] **13. Other modes keep their grid**
  - **Send:** `mode compose mode-2`
  - **Do:** Press a pad in the top two rows.
  - **Pass if:** The second lamp lights and the drum page gives way to the beat row along the bottom. A pad press draws a pad-NN row on the OLED again.
