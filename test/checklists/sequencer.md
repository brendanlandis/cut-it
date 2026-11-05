# Sequencer checklist

Page 2's drum page on the Launchpad, the sequencer playing the drum samples from the Organelle, and the pattern surviving a reload. `sequencer-assert` proves the notes, the frames and the file; what is left is what only the rig can show — whether the page reads, and how the drums sound.

24 steps. How to read one, and how to send a **Send** line: [the checklists' README](README.md). Why each thing behaves as it does: [sequencer](../../ref/module/sequencer.md).

- [ ] **1. The drum page**
  - **Need:** A fresh load of the patch with no saved pattern — the selection resets at every load and a saved step would be lit.
  - **Send:** `stop bang; mode mode-2`
  - **Pass if:** The left column has its second lamp down bright. The top four rows of pads are the steps: the top two dim but the first, which is blue as a bar's first step, and the two under them dark, since the last step is 16. The bottom-left four by four is bright pink, with its bottom-left pad red. The right halves of the bottom two rows are the eight velocity buttons — white at the top left to red at the bottom right, with the second one on the bottom row brighter than the rest. The top row of the right four by four is dim purple and the row under it dark, and nothing walks along the bottom row.
  - **Note:** Level 6 is the bottom row's second velocity button; track 1 is the bottom-left drum pad. Both reset at every load ([sequencer](../../ref/module/sequencer.md)).

- [ ] **2. A drum pad plays and selects**
  - **Need:** Drum samples in `samples/drums/`, deployed with the patch (`tools/samples.sh`).
  - **Do:** Press the top-left drum pad.
  - **Pass if:** Pad 13's sample plays at once through mixer channel 1, at full volume however hard it is pressed. That pad turns red and the bottom-left one goes back to pink. The OLED draws no row for it.

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
  - **Do:** Press the bottom-left drum pad. Then press step 1 and step 9.
  - **Pass if:** Pad 1 sounds alone on step 9 and with pad 13 on step 1 — both are heard there and neither is dropped.

- [ ] **8. Knob 2 starts held at 16**
  - **Do:** With it still playing, turn knob 2 a little either way, without passing noon.
  - **Pass if:** The screen reads last-step 16 with the knob's own step in brackets beside it, and nothing changes on the grid. Keep turning through noon: the brackets go and the number follows the knob.

- [ ] **9. The last step**
  - **Do:** Turn knob 2 until the screen reads last-step 4. Then to last-step 24, then back to last-step 16.
  - **Pass if:** At 4 the green pad walks steps 1 to 4 only, and steps 5 to 32 are dark, lit ones included, and silent. At 24 the third row lights up to step 24 and the walk covers it. At 16 it is the top two rows again.

- [ ] **10. A track's own last step**
  - **Do:** Select the bottom-left drum pad. Turn knob 3 until the screen reads pad1-last 3, through the brackets if they show. Then select the top-left drum pad.
  - **Pass if:** Pad 1 now repeats every three steps against pad 13's sixteen, drifting against it. With pad 1 selected the steps past 3 are dark and the green pad walks 1 to 3. With pad 13 selected the grid shows its sixteen, and turning knob 3 a little reads pad13-last 16 with brackets: held until turned through 16.

- [ ] **11. The drum screen**
  - **Need:** TouchOSC open on the phone with Cut It's layout, linked.
  - **Do:** Look at the phone. Tap last on its show radio. Then tap the phone's pad in the second row from the bottom, first place.
  - **Pass if:** The phone's tab reads drums and shows the drum screen: sixteen pads on the left, each reading 0; on the right the two buttons, under them the show radio of four, volume, pitch, last and random, with volume lit, and the link lit. No tempo, drunk knob or time signature is on it: they are the arrangement screen's. Nothing sits low enough to touch the home bar. On last the pads read 16 but the bottom-left one, pad 1, teal and reading • 3. The tap selects pad 5 on the Launchpad without a sound: its pad lights and the grid shows its steps. On the phone pad 5 lights.

- [ ] **12. Sync first steps**
  - **Do:** Tap sync first steps on the phone and listen.
  - **Pass if:** The button flashes teal and the line under it reads sync waits for step 1. At the next step 1 of the sixteen, pad 1 starts again on its step 1 together with pad 13, then goes on repeating every three, and the line clears.

- [ ] **13. Snap to global**
  - **Do:** Tap snap to global on the phone.
  - **Pass if:** The button flashes teal and the line reads snap waits for step 1. At the next step 1 of the sixteen, pad 1 starts on step 1 with pad 13 and from then on plays all sixteen steps, and on the phone it turns red and reads 16, its dot gone.

- [ ] **14. The time signature**
  - **Do:** Press the Launchpad's top button down the left column, page 1: the phone turns to the arrangement screen. On it drag the bottom number's box up one step, then the top number's box up three. Then press page 2, the second button down.
  - **Pass if:** The phone reads 4 / 8, then 7 / 8. Back on page 2 the Launchpad's steps 1 and 15 are blue where they are not lit. The playing does not change.

- [ ] **15. Swing on knob 4**
  - **Do:** Turn knob 4 a little up, then all the way left. Then turn it all the way right, to noon, and back to all the way left.
  - **Pass if:** At first the screen reads swing 50 with the knob's own value in brackets, and nothing changes until the knob is all the way left; there the brackets go. All the way right every second step comes late, a long-short shuffle; at noon a gentler one, about 62; all the way left it plays straight again. Nothing turns it short-long.

- [ ] **16. A repeat pad**
  - **Do:** While it plays hold the top-left pad of the right four by four for a few beats, then let go. Then hold the fourth pad in that row a few beats and let go.
  - **Pass if:** The row's four pads are dim purple and the one held bright. Held, the first pad repeats one step on every step and the green pad stays put; let go, the pattern jumps on to where it would have been, not back to where it stopped. The fourth loops the last four steps.

- [ ] **17. A track's volume, pitch and randomness**
  - **Do:** On the phone tap volume on the radio, then drag pad 13 down slowly to -12 and up to +6, listening. Tap pitch and drag pad 13 up to +12, down to -12 and back to 0. Tap random and drag pad 13 to 50%, then 100%, listening for a few bars at each, and back to 0%. Drag pad 1 to 50% too, and back. Put pad 13's volume back to 0.
  - **Pass if:** Pad 13 gets quieter and louder from its next hit, and at +6 is clearly louder than before. At +12 it plays an octave higher and shorter, at -12 an octave lower and longer. At 50% randomness some of its hits drop out and others land on steps that are not lit, at other loudnesses, different ones each bar; at 100% no trace of its pattern is left; at 0% it plays as lit again. Pad 1, with fewer steps lit, gains hits at 50%. The other pads play as they did throughout, and the Launchpad's steps never change.
  - **Note:** How a drag feels under a finger is the phone checklist's step 20; the numbers it sends, and that the levels, the octaves and the coin are right, are `touchosc-assert`'s, `kit-assert`'s and `sequencer-assert`'s. This is how they sound.

- [ ] **18. Drunkenness**
  - **Do:** Press page 1 on the Launchpad, drag the arrangement screen's drunk to about 20% and listen for a few bars, then to 100% and listen again, then back to 0% and press page 2.
  - **Pass if:** At 20% most steps land on time, and now and then one comes a little early or late. At 100% no step lands where it should: each one comes early or late, some by as much as two steps, and the beat lurches on from there rather than catching up. At 0% it is steady again.

- [ ] **19. STOP**
  - **Send:** `stop bang`
  - **Pass if:** The sound stops and the green pad goes out. The steps stay lit.

- [ ] **20. Panic stops it too**
  - **Do:** Press PLAY on the nanoKONTROL. Then tap the top-left corner button of the Launchpad.
  - **Pass if:** Everything stops at once and the grid flashes red. When it clears the green pad is gone and the steps are still lit.

- [ ] **21. A one-shot pad on every step**
  - **Need:** A sample on pad 13, `samples/drums/13…`, deployed with the patch.
  - **Send:** `start bang`
  - **Do:** Select pad 13. Light all sixteen of its steps. Listen for a bar or two then turn knob 1 up and listen again.
  - **Pass if:** Every step is heard as a fresh hit, with no click where one cuts the last short. A step that falls silent is the failure.
  - **Note:** Each pad restarts its sample on every hit (the sequencer's page, *The kit*); `kit-assert` proves it on the Mac, and this is the same on the device.

- [ ] **22. The pattern survives a reload**
  - **Need:** Steps lit on the drum page from the steps before.
  - **Send:** `stop bang`
  - **Do:** On the phone tap volume and drag pad 13 to -6, then tap random and drag it to 30%. Press page 1, drag drunk to about 20%, and press page 2. Look at which steps are lit. Wait two seconds, then load Cut It again from the Organelle menu, press page 2 if the Launchpad is not on it, and on the phone tap volume, then random.
  - **Pass if:** After the reload the drum page shows the same steps lit as before it, steps 1 and 15 blue, and the phone's pad 13 reads -6 on volume and 30% on random, and plays that much quieter. On page 1 the phone shows 7 / 8 and drunk at what you left it. Knob 4's swing is back at 50%, on the phone's swing knob too.
  - **Note:** `u_state` flushes within 2 seconds of a change, so the wait is part of the step.

- [ ] **23. Other pages keep their grid**
  - **Send:** `mode mode-1`
  - **Do:** Press a pad in the top two rows.
  - **Pass if:** The top lamp lights and the drum page gives way to the beat row along the bottom and the tap pad, dim yellow, above its first cell. A pad press draws nothing on the OLED, since on page 1 only the tap pad is mapped and only a mapped control names itself, and the phone turns to the arrangement screen, its tab reading arrangement.

- [ ] **24. Knobs 2 and 4 on any page**
  - **Need:** The drums playing, from `start bang`, with steps lit. The phone linked.
  - **Send:** `mode mode-1`
  - **Do:** Turn knob 2 a little either way, then through noon and on to last-step 8. Then turn knob 4 a little, then all the way right. Then turn knob 3.
  - **Pass if:** Knob 2 reads last-step with its own step in brackets until it passes 16, then last-step alone; at 8 the drums loop in half the time, and the phone's last step reads 8. Knob 4 reads swing the same way until it is all the way left, at 50, and all the way right every second step comes late, and the phone's swing knob follows. Knob 3 draws nothing and changes nothing. Put knob 2 back to 16 and knob 4 all the way left.
  - **Note:** Knobs 2 and 4 are the drums' last step and swing on every page, as knob 1 is the tempo; knob 3, the selected track's own last step, is the drum page's alone (Brendan, 2026-11-04). The brackets are `c_steps`' latch: a reload holds both knobs again, at 16 and 50%.
