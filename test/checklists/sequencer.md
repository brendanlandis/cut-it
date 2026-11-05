# Sequencer checklist

Page 2's drum page on the Launchpad, the sequencer playing the drum samples from the Organelle, and the pattern surviving a reload. `sequencer-assert` proves the notes, the frames and the file; what is left is what only the rig can show — whether the page reads, and how the drums sound.

54 steps. How to read one, and how to send a **Send** line: [the checklists' README](README.md). Why each thing behaves as it does: [sequencer](../../ref/module/sequencer.md).

- [ ] **1. The drum page**
  - **Need:** A fresh load of the patch with no saved pattern — the selection resets at every load and a saved step would be lit.
  - **Send:** `stop bang; mode mode-2`
  - **Pass if:** The left column has its second lamp down bright. The top four rows of pads are the steps: the top two dim but their first and fifth pads, which are blue, every fourth step at 4/4, and the two under them dark, since the last step is 16. The bottom-left four by four is bright pink, with its bottom-left pad red. The right halves of the bottom two rows are the eight velocity buttons — white at the top left to red at the bottom right, with the second one on the bottom row brighter than the rest. The top row of the right four by four is dim purple and the row under it dark, and nothing walks along the bottom row.
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
  - **Pass if:** The phone reads 4 / 8, then 7 / 8. Back on page 2 the steps are rows of seven, each row's eighth pad dark, and each row's first pad is blue where it is not lit. The playing does not change, at 4 / 8 or at 7 / 8.

- [ ] **15. Swing on the phone**
  - **Do:** On the phone's page 1 drag the swing knob all the way up, to about 62, and back to 50.
  - **Pass if:** All the way up every second step comes late, a long-short shuffle; at about 62 a gentler one; at 50 it plays straight again. Nothing turns it short-long.

- [ ] **16. A repeat pad**
  - **Do:** While it plays hold the top-left pad of the right four by four for a few beats, then let go. Then hold the fourth pad in that row a few beats and let go.
  - **Pass if:** The row's four pads are dim purple and the one held bright. Held, the first pad repeats one step on every step and the green pad stays put; let go, the pattern jumps on to where it would have been, not back to where it stopped. The fourth loops the last four steps.

- [ ] **17. A repeat plays what randomness played**
  - **Need:** The drums playing at 120 BPM on page 2, the phone linked, nothing muted or soloed, drunk at 0%. Pad 13, the top-left drum pad, selected, with its steps 1, 5, 9 and 13 lit.
  - **Do:** On the phone tap random and drag pad 13 to 100%, and listen for a bar. Hold the fourth pad of the right four by four's top row for a few bars, then let go. Hold it again, and while it is held tap the M under pad 13, wait a bar and tap it again; then let go. Press page 1, drag drunk to 100% and press page 2; hold the fourth pad for a few bars and let go. Put drunk and pad 13's random back to 0%.
  - **Pass if:** At 100% pad 13's hits and loudnesses change every bar. Held, the fourth pad loops the last four steps exactly as they just sounded, the same hits at the same loudnesses every time round; let go, they change every bar again. At the M pad 13 drops out of the held loop from its next step, and at the M again it comes back with the same hits as before. Drunk, the held loop lurches the same way every time round, and let go, the lurching wanders again.
  - **Note:** A repeat plays exactly what was played, what the randomness chose that time included (Brendan, 2026-11-05). The edge cases, a repeat pressed just after PLAY and a step edited or a section changed under one, are `sequencer-assert`'s ([sequencer](../../ref/module/sequencer.md), *A repeat replays what was decided*).

- [ ] **18. A track's volume, pitch and randomness**
  - **Do:** On the phone tap volume on the radio, then drag pad 13 down slowly to -12 and up to +6, listening. Tap pitch and drag pad 13 up to +12, down to -12 and back to 0. Tap random and drag pad 13 to 50%, then 100%, listening for a few bars at each, and back to 0%. Drag pad 1 to 50% too, and back. Put pad 13's volume back to 0.
  - **Pass if:** Pad 13 gets quieter and louder from its next hit, and at +6 is clearly louder than before. At +12 it plays an octave higher and shorter, at -12 an octave lower and longer. At 50% randomness some of its hits drop out and others land on steps that are not lit, at other loudnesses, different ones each bar; at 100% no trace of its pattern is left; at 0% it plays as lit again. Pad 1, with fewer steps lit, gains hits at 50%. The other pads play as they did throughout, and the Launchpad's steps never change.
  - **Note:** How a drag feels under a finger is the phone checklist's step 20; the numbers it sends, and that the levels, the octaves and the coin are right, are `touchosc-assert`'s, `kit-assert`'s and `sequencer-assert`'s. This is how they sound.

- [ ] **19. Drunkenness**
  - **Do:** Press page 1 on the Launchpad, drag the arrangement screen's drunk to about 20% and listen for a few bars, then to 100% and listen again, then back to 0% and press page 2.
  - **Pass if:** At 20% most steps land on time, and now and then one comes a little early or late. At 100% no step lands where it should: each one comes early or late, some by as much as two steps, and the beat lurches on from there rather than catching up. At 0% it is steady again.

- [ ] **20. STOP**
  - **Send:** `stop bang`
  - **Pass if:** The sound stops and the green pad goes out. The steps stay lit.

- [ ] **21. Panic stops it too**
  - **Do:** Press PLAY on the nanoKONTROL. Then tap the top-left corner button of the Launchpad.
  - **Pass if:** Everything stops at once and the grid flashes red. When it clears the green pad is gone and the steps are still lit.

- [ ] **22. A one-shot pad on every step**
  - **Need:** A sample on pad 13, `samples/drums/13…`, deployed with the patch.
  - **Send:** `start bang`
  - **Do:** Select pad 13. Light all sixteen of its steps. Listen for a bar or two then turn knob 1 up and listen again.
  - **Pass if:** Every step is heard as a fresh hit, with no click where one cuts the last short. A step that falls silent is the failure.
  - **Note:** Each pad restarts its sample on every hit (the sequencer's page, *The kit*); `kit-assert` proves it on the Mac, and this is the same on the device.

- [ ] **23. The pattern survives a reload**
  - **Need:** Steps lit on the drum page from the steps before.
  - **Send:** `stop bang`
  - **Do:** On the phone tap volume and drag pad 13 to -6, then tap random and drag it to 30%. Press page 1, drag drunk to about 20%, and press page 2. Look at which steps are lit. Wait two seconds, then load Cut It again from the Organelle menu, press page 2 if the Launchpad is not on it, and on the phone tap volume, then random.
  - **Pass if:** After the reload the drum page shows the same steps lit as before it, in rows of seven with each row's first pad blue, and the phone's pad 13 reads -6 on volume and 30% on random, and plays that much quieter. On page 1 the phone shows 7 / 8 and drunk at what you left it. The phone's swing knob is back at 50%.
  - **Note:** `u_state` flushes within 2 seconds of a change, so the wait is part of the step.

- [ ] **24. Other pages keep their grid**
  - **Send:** `mode mode-1`
  - **Do:** Press a pad in the top two rows.
  - **Pass if:** The top lamp lights and the drum page gives way to the beat row along the bottom and the tap pad, dim yellow, above its first cell. A pad press draws nothing on the OLED, since on page 1 only the tap pad is mapped and only a mapped control names itself, and the phone turns to the arrangement screen, its tab reading arrangement.

- [ ] **25. Knob 2 on any page**
  - **Need:** The drums playing, from `start bang`, with steps lit. The phone linked.
  - **Send:** `mode mode-1`
  - **Do:** Turn knob 2 a little either way, then through noon and on to last-step 8. Then turn knob 3.
  - **Pass if:** Knob 2 reads last-step with its own step in brackets until it passes 16, then last-step alone; at 8 the drums loop in half the time, and the phone's last step reads 8. Knob 3 draws nothing and changes nothing. Put knob 2 back to 16 and knob 4 all the way left.
  - **Note:** Knob 2 is the drums' last step on every page, as knob 1 is the tempo; knob 3, the selected track's own last step, is the drum page's alone (Brendan, 2026-11-04). The brackets are `c_steps`' latch: a reload holds it again, at 16.

- [ ] **26. Rows at 4/4 and 3/4**
  - **Need:** The phone linked. The drum page stopped.
  - **Send:** `stop bang; mode mode-2`
  - **Do:** Press page 1 and on the arrangement screen drag the time signature to 4 / 4 and the last step all the way up. Press page 2, select the bottom-left drum pad, and light its step 9, the second row's first pad, if it is not lit. Look at the top four rows. Then press page 1, drag the top number down to 3, and press page 2.
  - **Pass if:** At 4/4 the last step's box stops at 32, and all four rows are steps, eight a row, the first and fifth pad of every row blue where not lit. At 3/4 the phone's last step reads 24, each row is six steps with its last two pads dark, and each row's first and fourth pads are blue where not lit. Step 9 is now the second row's third pad, still lit.

- [ ] **27. A press on a row at 3/4**
  - **Need:** 3/4 from the step before, the bottom-left drum pad selected, on page 2.
  - **Do:** Press the second row's first pad. Then press the top row's seventh pad. Then press PLAY on the nanoKONTROL and watch the green pad.
  - **Pass if:** The second row's first pad lights and the seventh stays dark: nothing happens there. The green pad walks six pads of a row and drops to the next row's first, and pad 1 sounds when it lands on the pad you lit, the seventh step.

- [ ] **28. 5/4 and 9/8**
  - **Need:** Playing, from the step before.
  - **Do:** Press page 1, drag the top number to 5 and press page 2. Then press page 1, drag the top number to 9 and the bottom number to 8, and press page 2.
  - **Pass if:** At 5/4 the rows are five steps, each row's last three pads dark, each row's first pad blue where not lit, and the phone's last step reads 20. At 9/8 the rows are eight again and the last step reads 32 again, and the blue steps one pad to the right on each row down: the top row's first, the second row's second, the third row's third, the fourth row's fourth. The beat never changes speed.

- [ ] **29. The last step reaches four rows**
  - **Need:** Playing, from the step before.
  - **Do:** Press page 1 and drag the top number to 3. Turn knob 2 all the way left, then all the way right. Then drag the phone's last step box all the way up. Press page 2, select the top-left drum pad and turn knob 3 all the way left, then all the way right.
  - **Pass if:** Knob 2 reads last-step 24 at its right end, the brackets gone, and the walk covers all four rows of six. The phone's box stops at 24 however far it is dragged. Knob 3 reads pad13-last 24 at its right end.

- [ ] **30. The bottom number changes nothing you hear**
  - **Need:** Playing, from the step before.
  - **Do:** Press page 1. Drag the bottom number from 4 up to 16, listening, then down to 1, then back to 4. Then drag the top number back to 4.
  - **Pass if:** The drums keep exactly the same speed and pattern while the bottom number moves, and the Launchpad's page does not change with it: only the phone's bottom number moves. At 4/4 the rows are eight again.

- [ ] **31. Distortion on one drum**
  - **Need:** Brendan's samples deployed, the phone linked, 4/4 at 120 BPM. On page 2, the bottom-left drum pad, pad 1, with steps 1, 5, 9 and 13 lit and nothing else lit on any track.
  - **Send:** `start bang; mode mode-2`
  - **Do:** On the phone tap pad 1, then effect's distortion. Turn mix all the way up, then drive from all the way left to all the way right, listening, then tone from right to left. Then turn mix back to 0.
  - **Pass if:** At drive 0 the drum sounds much as it did; turning drive up makes it fuzzier and more compressed, its tail louder against its attack, and at the top it is a hard square buzz. Tone turned left takes the fizz off until it is a dull thud. Back at mix 0 the drum is exactly as it was before the step, and no other drum changed throughout.

- [ ] **32. Delays of different note values on two drums**
  - **Need:** Playing, from the step before, with mix back at 0. Light the bottom row's second pad, pad 2's, steps 3 and 11.
  - **Do:** On the phone tap pad 1, then delay. Tap 1/4 and straight, and turn feedback to about 30% and level all the way up. Then tap pad 2, tap 1/8 and dotted, feedback about 50%, level all the way up. Listen for a few bars, then on page 1 drag the tempo from 120 to 90 and back.
  - **Pass if:** Pad 1 repeats a quarter note after each hit, a few times, quieter each time; pad 2 repeats a dotted eighth after its hits, more times, so the two drums echo on different grids at once. Dragging the tempo slows both delays with the beat, the echoes still on it, sliding in pitch while it moves. Switching pad 2 to triplet moves its echoes onto a triplet grid.

- [ ] **33. A delay rings out when its level goes down**
  - **Need:** Playing, from the step before.
  - **Do:** On the phone tap pad 2, and with the delay showing turn its level all the way down in one move. Then press STOP on the nanoKONTROL and wait.
  - **Pass if:** Pad 2 stops making new echoes at once, but the ones already sounding die away on their own over a few repeats rather than cutting off. After STOP pad 1's last echoes ring out the same way and then there is silence.

- [ ] **34. The reverb send**
  - **Need:** The pattern from the steps before, stopped.
  - **Send:** `start bang`
  - **Do:** On the phone tap pad 1, then reverb. Turn send to about 50%, then all the way up. Turn size from left to right, then damping from left to right. Tap pad 2 and turn its send up, then pad 1's back to 0.
  - **Pass if:** Pad 1 gets a room around it that grows with the send, while pad 2 stays dry; size takes it from a short room to a long wash; damping takes the brightness out of the tail. Once pad 2's send is up it has the same reverb, and with pad 1's at 0, pad 1 is dry again while pad 2 keeps its tail. Size and damping are the same whichever pad is selected: there is one reverb.

- [ ] **35. The effects are saved with a section**
  - **Need:** The pattern and effects from the steps before: pad 1 with its quarter-note delay, pad 2 with its reverb send. The Launchpad's top row with two sections.
  - **Do:** Press the top row's second pad, the second section, and let it start; on the phone tap pad 1, then delay, and turn its level to 0, then tap pad 2, reverb, and turn its send to 0. Press the top row's first pad and let it start, then the second again. Then press save, the upper bottom row's rightmost button, the red one, load Cut It again from the Organelle menu, and press PLAY.
  - **Pass if:** In the second section the two drums are dry; going back to the first, pad 1 echoes and pad 2 has its reverb again, and the phone's controls for each show the first section's settings; back in the second, dry again. After the reload each section has the effects it had when saved.
  - **Note:** The effects are a section's, with its pattern, as volume and pitch are (Brendan, 2026-11-05). That every effect reaches `c_kit` at a restore, and the delay's time and levels, are `sequencer-assert`'s and `kit-assert`'s; this is how they sound.

- [ ] **36. Mute a drum from the phone**
  - **Need:** Brendan's samples deployed, the phone linked, 4/4 at 120 BPM, nothing muted or soloed and every effect off. On page 2, light pad 1's steps 1, 5, 9 and 13, pad 2's steps 3 and 11, and pad 3's steps 7 and 15, pads 1 to 3 being the bottom row's first three; then select pad 2.
  - **Send:** `start bang; mode mode-2`
  - **Do:** On the phone's drum screen tap the M under pad 1. Then press pad 1 on the Launchpad. Then tap the M under pad 1 again.
  - **Pass if:** At the M pad 1 stops from its next hit while pads 2 and 3 play on; the M lights red, its letter black; on the Launchpad pad 1 turns dim pink and pad 2 stays red. Pressing pad 1 on the Launchpad still plays it, once, and it turns dim red, selected. Tapped again, the M goes out, pad 1 comes back in on its own beat, and the Launchpad's pad 1 is red again.
  - **Note:** A press on a muted pad playing it is a judgment call, so a muted drum can be heard before it comes back in ([sequencer](../../ref/module/sequencer.md), *Mute and solo stop the hits, not the sound*). Which notes play, muted, soloed and both, is `sequencer-assert`'s; this is what the rig shows.

- [ ] **37. A mute lets the tails ring out**
  - **Need:** Playing, from the step before, nothing muted.
  - **Do:** On the phone tap pad 1, then delay: tap 1/4 and straight, turn feedback to about 60% and level all the way up. Then reverb: turn send to about 70% and size to about 80%. Listen for a bar, then tap the M under pad 1 and listen. After the tails have gone, tap the M again, then turn pad 1's send and its delay's level back to 0.
  - **Pass if:** At the M pad 1's hits stop at once, but the echoes and the reverb already sounding die away on their own over a few repeats rather than cutting off. Unmuted, it comes back with its echoes and its room.

- [ ] **38. Solo**
  - **Need:** Playing, from the step before, nothing muted or soloed, every effect off, pad 2 selected.
  - **Do:** Tap the M under pad 1. Then tap the S under pad 2. Then tap the S under pad 1. Then tap both S again, and last the M under pad 1.
  - **Pass if:** With pad 1 muted, pads 2 and 3 play. At the S under pad 2, lit teal, only pad 2 plays, and on the Launchpad every pad but pad 2 turns dim pink while pad 2 stays red. At the S under pad 1 pads 1 and 2 play, pad 1 though its M is still lit, and its Launchpad pad is bright pink again. With both S out, pads 2 and 3 play and pad 1 is silent and dim again; at the M, all three play and every pad is bright.

- [ ] **39. Mute and solo are saved with a section**
  - **Need:** The pattern from the steps before, playing, nothing muted or soloed, in section 1, and section 2 a copy of it: on the phone's sections page, page 7, select section 1 and tap **new, a copy of**.
  - **Do:** Press the fourth button of the top row, section 2, and let it start; on the phone tap the M under pad 1 and the S under pad 3. Press the third button, section 1, and let it start, then the fourth again. Then press save, the upper bottom row's rightmost button, the red one, load Cut It again from the Organelle menu, and press PLAY with each section in turn.
  - **Pass if:** In section 2 only pad 3 plays, and the phone shows pad 1's M and pad 3's S lit and the Launchpad every pad but pad 3 dim. In section 1 all three play, every M and S out and every pad bright; back in section 2, pad 1's M and pad 3's S again. After the reload each section has what it had when saved.
  - **Note:** Mute and solo are a section's, with its pattern (Brendan, 2026-11-05). That a section saved before them loads with nothing muted is `sequencer-assert`'s.

- [ ] **40. More drive is louder and dirtier, never quieter**
  - **Need:** Brendan's samples deployed, the phone linked, 4/4 at 120 BPM, every effect off. On page 2, light pad 1's steps 1, 5, 9 and 13, pad 1 being the bottom-left drum pad, and nothing else on any track.
  - **Send:** `start bang; mode mode-2`
  - **Do:** On the phone tap pad 1, then effect's distortion. Leave character on soft and tone where it starts. Turn mix all the way up, then drive slowly from all the way left to all the way right, listening, then back to about three quarters.
  - **Pass if:** Tone starts all the way right, and the drum is bright, not dulled. As drive goes up the drum gets fuzzier, fatter and a little louder, its tail coming up against its attack, and at no point does it get quieter or thinner than at drive 0. Its peaks never jump out louder than the dry drum's did.
  - **Note:** The makeup stops at −8 dB, so drive keeps adding level instead of taking it away (Brendan, 2026-11-05). That drive 100 is no quieter than 50, and never past the dry's peak, is `kit-assert`'s; this is how it sounds.

- [ ] **41. The four characters on one drum**
  - **Need:** Playing, from the step before: pad 1 with its distortion's mix all the way up and drive at about three quarters, soft.
  - **Do:** On the phone, above drive, tone and mix, tap each character in turn, hard, fold, crush, listening to a bar of each, then soft again. Then on crush, turn drive from all the way left to all the way right.
  - **Pass if:** The radio is one row of four, soft, hard, fold and crush, the chosen one lit with its word black. Each is a different sound at the same drive: soft a round, thick fuzz; hard harsher and buzzier, with a gritty, lopsided edge; fold a metallic, ringing, almost pitched sound; crush grainy and lo-fi, with an aliased, digital fizz. Switching never clicks, drops out or stops the beat, and soft again sounds as it did at the start. On crush, more drive makes it coarser and lower-pitched in its grain.
  - **Note:** A character is a handful of numbers to `e_drive`, so switching costs nothing; crush's rounding and hold run only while it is chosen ([sequencer](../../ref/module/sequencer.md), *The effects*). That each character is a shape of its own is `kit-assert`'s; whether each sounds right is this step's.

- [ ] **42. A drive means the same on a quiet drum**
  - **Need:** Playing, from the step before, pad 1 back on soft. Light steps 3, 7, 11 and 15 of the track whose sample is the quietest of the kit, a hat if there is one.
  - **Do:** On the phone tap that track's pad, then distortion: mix all the way up, character soft, drive at about three quarters, the same as pad 1. Listen to both. Then turn the quiet track's mix back to 0.
  - **Pass if:** The quiet drum is as plainly distorted as pad 1 at the same drive, not barely touched, and stays about as loud against pad 1 as it was dry. At mix 0 it is exactly as it was.
  - **Note:** Each sample's own peak scales what goes into the distortion (Brendan, 2026-11-05): `c_voice` tells `e_drive` the peak once the sample is read.

- [ ] **43. The character is saved with a section**
  - **Need:** Pad 1's distortion from the steps before, soft, mix up. The Launchpad's top row with two sections, the second a copy of the first: on the phone's sections page, page 7, select section 1 and tap **new, a copy of**.
  - **Do:** Press the fourth button of the top row, section 2, and let it start; on the phone tap pad 1, then distortion, and tap crush. Press the third button, section 1, and let it start, then the fourth again. Then press save, the upper bottom row's rightmost button, the red one, load Cut It again from the Organelle menu, and press PLAY with each section in turn. Last, on the phone turn pad 1's mix back to 0 in each section and save.
  - **Pass if:** In section 2 pad 1 is crushed and the phone's radio shows crush; in section 1 it is soft again and the radio shows soft; back in section 2, crush. After the reload each section has the character it had when saved.
  - **Note:** A section saved before the characters loads every track soft, and keeps the tone it was saved with, so one saved with the old tone of 60 stays dull until its tone is turned up. That is `sequencer-assert`'s and the Lua's; this is the rig.

- [ ] **44. The reverb's three types, on the drums**
  - **Need:** Brendan's samples deployed, the phone linked, 4/4 at 120 BPM, nothing muted or soloed and every effect off. On page 2, light pad 1's steps 1, 9 and 11, pad 5's steps 5 and 13, and pad 4's every odd step: pad 1 the bottom row's first, pad 4 its fourth, pad 5 the second row's first, the kick, hat and snare of the research's renders.
  - **Send:** `start bang; mode mode-2`
  - **Do:** On the phone tap pad 5, then reverb: plate is lit under size and damping. Turn its send to about 70%, then tap pad 4 and turn its send to about 40%, and set size to about 30% and damping to about 50%. Listen for two bars, then tap gigaverb, two bars, then freeverb, two bars, then plate again. Then tap a type just after a snare, while its tail is sounding.
  - **Pass if:** The snare and the hats each have a room around them in every type, and each type changes the room's character but not its loudness or its length: nothing jumps louder or quieter at a tap. A tail sounding at the tap dies away on its own rather than cutting off, and the next hits sound in the new type. No click, crackle or dropout at any tap.
  - **Note:** Which of the three he wants is his call (Brendan, 2026-11-05: "a choice on the phone between all three"); tell the session, which can make it the starting point. That each type plays its own engine, rings out when changed away from, and matches the others' level is `kit-assert`'s ([sequencer](../../ref/module/sequencer.md), *Three reverbs behind the same controls*); this is how they sound on his drums.

- [ ] **45. Size and damping mean the same in each type**
  - **Need:** Playing, from the step before, plate lit.
  - **Do:** Turn size all the way down, then to about 80%, then back to about 30%. Turn damping all the way left, then all the way right, then back to about 50%. Tap gigaverb and do both again, then freeverb.
  - **Pass if:** In each type size takes the tail from about half a second to a long wash, about as long in all three at the same setting; damping takes the brightness out of each tail alike, none going dull or silent at its right end. Size and damping keep where they were set across a change of type: there is one reverb.

- [ ] **46. The type is saved with a section**
  - **Need:** The pattern from the steps before, playing, in section 1 with plate lit, and section 2 a copy of it: on the phone's sections page, page 7, select section 1 and tap **new, a copy of**.
  - **Do:** Press the fourth button of the top row, section 2, and let it start; on the phone's drum screen tap reverb, then freeverb. Press the third button, section 1, and let it start, then the fourth again. Then press save, the upper bottom row's rightmost button, the red one, load Cut It again from the Organelle menu, and press PLAY with each section in turn.
  - **Pass if:** Section 2 plays freeverb and the phone shows it lit; section 1 plays the plate, plate lit; back in section 2, freeverb again. After the reload each section has the type it had when saved, and a section saved before the types plays the plate.
  - **Note:** The type is a section's, as size and damping are (Brendan, 2026-11-05). That a line without it loads as the plate is `sequencer-assert`'s.

- [ ] **47. A held repeat replays its tails and makes no new ones**
  - **Need:** Brendan's samples deployed, the phone linked, 4/4 at 120 BPM, nothing muted or soloed and every effect off. On page 2, light pad 1's steps 1, 5, 9 and 13. On the phone tap pad 1, then delay: 1/8, dotted, feedback about 60%, level about 70%. Then reverb: send about 50%, size about 50%.
  - **Send:** `start bang; mode mode-2`
  - **Do:** Listen for a few bars. Then hold the second repeat pad, the top row of the right 4×4, for about ten seconds, and let it go. Then the same with the fourth repeat pad.
  - **Pass if:** Held, the echoes and the reverb you heard go round with the hits, in time and the same every pass, and don't build up, however long it is held. The sound doesn't get wetter, and no echo of a repeated hit is ever heard: not while it is held, and not after. Let go, the pattern plays on from where it would have been, its echoes and reverb coming back with it.
  - **Note:** Two steps of a tail is what the second pad loops, so a short one is a stutter of it (Brendan, 2026-11-05). What the loop holds and when is `kit-assert`'s, read off the signal; how it sounds is this step's.

- [ ] **48. No click going in, round or coming out**
  - **Need:** Playing, from the step before.
  - **Do:** Turn the reverb's size up to about 80%. Press and let go of each repeat pad in turn, holding some for a moment and some for a few seconds. Press one again right after letting go, a few times, quickly.
  - **Pass if:** No click, pop or thump as a repeat starts, as its loop comes round, or as it is let go, on any pad, however quickly they come. A dip in the tail where a quick press reads back across the last one is fine; a click isn't.

- [ ] **49. The tails follow the tempo**
  - **Need:** Playing, from the step before.
  - **Do:** Hold the fourth repeat pad. Turn knob 1 slowly up past where it is, well past, then back down, past where it was. Then, still holding, drag the tempo on the phone's arrangement screen up and down, or if the page is in the way, have the tempo already set by a tap before you hold.
  - **Pass if:** As the tempo rises the tails go round faster and higher, as the hits do, and as it falls slower and lower, like tape, and they stay with the hits all the way. Let go at any tempo and the tempo stays where it was left.

- [ ] **50. The new pads' lamps**
  - **Do:** Look at the right 4×4 on page 2. Press and hold the first repeat pad, let go. Do the same with the pad under it, then with the pad under the fourth repeat pad.
  - **Pass if:** The top row and the pad under the first of them are a full bright purple. The pad under the fourth is a dim blue. The two between those are dark, and nothing happens when pressed. Each purple pad held goes a whiter purple, never dimmer; the blue one goes a bright blue; each goes back when let go.

- [ ] **51. The 500 BPM repeat**
  - **Need:** Playing, from the step before, at a tempo you know, 120 on the phone. Note the Launchpad's save and revert lamps.
  - **Do:** Hold the pad under the first repeat pad for a few seconds while watching the phone's tempo. Turn knob 1 through its range short of its top end. Let go. Turn knob 1 a little.
  - **Pass if:** Held, one step machine-guns, the tempo reads 500 and the tails go round fast and high with it. Knob 1 changes nothing and the OLED's row reads `bpm 500 (…)`. Let go, the tempo reads what it was, the pattern plays on from the step it was pressed on, not back on the beat, and the knob changes nothing until it is turned through that tempo. Save and revert don't light for any of it.
  - **Note:** That it does not keep the canonical beat is a judgment call: Brendan said there is no need to (2026-11-05). Say so if it should.

- [ ] **52. Knob 1 from its end**
  - **Need:** Playing, from the step before.
  - **Do:** Hold the same pad and turn knob 1 all the way up to its end, then back down part way. Let go.
  - **Pass if:** From its end, the knob moves the tempo, and the repeat and its tails follow it. Let go, the tempo snaps back to what it was before the press, and the knob is held again.

- [ ] **53. The saved tempo**
  - **Need:** On the phone, the tempo at 110. Press save, the upper bottom row's rightmost button, so it goes dark. Turn knob 1 through 110 and on to about 150: save and revert light.
  - **Do:** Press the pad under the fourth repeat pad. Turn knob 1 a little. Press it again with the tempo where it is. Then on the sections page make a new section and start it, turn knob 1 to something else and press the pad.
  - **Pass if:** The press snaps the tempo to 110, and the phone says so. Save and revert go dark if nothing else changed. The knob changes nothing until it is turned through 110. A press at that tempo does nothing. In a section that has never been saved, the pad snaps to the tempo its draft holds, which is where the knob just left it, so nothing moves.

- [ ] **54. A track's random pitch**
  - **Need:** Playing, 4/4 at 120 BPM, nothing muted or soloed, pad 1's steps 1, 5, 9 and 13 lit, its pitch at 0, the effects as you like.
  - **Do:** On the phone tap pad 1. Tap random on the show radio and drag pad 1 up to about 50%. Listen for a few bars. Tap **rnd pitch**, under the radio. Listen. Tap the first repeat pad and hold it on a hit whose pitch has moved, a few seconds. Tap another pad on the phone, and pad 1 again. Tap **rnd pitch** off.
  - **Pass if:** Before the tap some hits drop or move but all at the same pitch. With it on, the button is lit and hits the randomness adds or changes come at different pitches, up to an octave either way, while hits as written stay at pad 1's pitch. The repeat plays the same pitch every time. The button is out on the other pad and lit again back on pad 1, so it is that track's. Off, every hit is at its pitch again.
  - **Note:** Saved with the section, and off in a section saved before it. That and the die's range are `c_steps_test`'s. Whether an octave either way is the right range is his call (Brendan, 2026-11-05: "up to ±12").

- [ ] **55. Rush on knob 4**
  - **Need:** Playing a sixteen-step pattern at about 120 BPM, a few steps lit, nothing held. Tempo saved with the section.
  - **Do:** Turn knob 4 a little, staying one side of about half past nine. Then all the way left, slowly, listening at the bottom. Then slowly all the way right. Press the pad under the fourth repeat pad. Turn knob 4 a little, then knob 1 a little. Then turn knob 4 through 120 again and hold the third repeat pad on the way up.
  - **Pass if:** At first the screen reads rush 120 with the knob's own rate in brackets and nothing changes. Through 120 it has the tempo, down to rush 10 bpm at the bottom, a step every second and a half. Going up the steps race, faster at an even rate; near 1000 the row turns to Hz, about 4 Hz, the pattern looping at the speed it had, with no jump in what you hear; and the loop keeps climbing past hearing, harsh and folding back, with nothing smoothing it. The pad stops the loop at once, the tempo is the saved BPM and step 1 plays, and both knobs read rush 120 and bpm 120 with their own in brackets and change nothing until turned through it. Under the repeat pad the loop is its three steps, about 22 Hz at the handoff, and reaches the same top. Save and revert have not lit from knob 4.
  - **Note:** Whichever knob moved last wins: knob 1 through its hold takes the tempo back, on the record, and holds knob 4 there. The even rate, the handoff and how the pattern reads as it climbs are his to judge ([sequencer](../../ref/module/sequencer.md), *Rush*).
