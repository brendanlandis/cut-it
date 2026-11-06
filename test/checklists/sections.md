# Sections checklist

The current song's sections: the Launchpad's top row, which plays them, save and revert on its
bottom rows, and the phone's sections page, which makes, orders, names and sets them. `song-assert` proves
what a press restores, the queue at the loop, a length handing over, the lamps' colors, the program
changes and the files across a reload; `phone-assert` and `touchosc-assert` the phone's side. What
is left is music you can hear change on the downbeat, lamps you can see blink, and the SD card
across a real power cut.

**Before you start:**

- The drums audible through the PA, the Volca and the Streichfett on, and the phone showing Cut It.
- A song of at least two sections that sound different: on the phone's sections page, tap **new**, then on the drum page
  change the drum pattern while the new section plays (step 3 says how to play it), and on the arrangement screen
  its tempo.

12 steps. How to read one, and how to send a **Send** line: [the checklists' README](README.md). Why
each thing behaves as it does: [songs](../../ref/module/songs.md).

- [ ] **1. The top row at rest**
  - **Need:** Cut It loaded, the transport stopped, a song of two or three sections.
  - **Do:** Look at the Launchpad's top row and its two bottom rows' rightmost buttons.
  - **Pass if:** The third button from the left is bright green: section 1, playing. One button to its right per further section is dim green, and the buttons past the last section are dark. The second button, the right arrow, is dim white; the first, the left arrow, is dark. Both rightmost bottom buttons are dark.

- [ ] **2. Stopped, a section starts at once**
  - **Need:** The transport stopped, section 1 playing.
  - **Do:** Press the fourth button of the top row, then press PLAY.
  - **Pass if:** The fourth button goes bright and the third dim at the press, and both arrows are lit. The phone's tempo changes to section 2's at once. PLAY plays section 2's drum pattern from its first step.

- [ ] **3. Playing, a press waits for the pattern to come round**
  - **Need:** Playing, section 2 playing, its global last step 16 or more.
  - **Do:** Press the third button mid-pattern, and listen.
  - **Pass if:** The third button blinks on the beat, full and dark, while section 2 plays on to the end of its pattern. On the pattern's step 1 section 1 takes over, its first step on that downbeat, and the third button goes solid and the fourth dim.

- [ ] **4. The arrows**
  - **Need:** Playing, section 1 playing, two sections or more.
  - **Do:** Press the second button, the right arrow, then wait for the pattern to come round; then press the first, the left arrow, and wait again.
  - **Pass if:** The right arrow queues section 2, blinking until the pattern comes round; the left arrow queues section 1 back the same way. Each arrow is dark when there is no section its way.

- [ ] **5. A length hands over by itself**
  - **Need:** Playing, two sections. On the phone's sections page, select section 1 and drag its length up to 2 bars.
  - **Do:** Press the third button to queue section 1, and count its patterns.
  - **Pass if:** Section 1 plays its pattern twice and section 2 starts on the next step 1 by itself, with nothing pressed. Section 2, a loop, plays on until a button is pressed.

- [ ] **6. A change lights save and revert**
  - **Need:** Nothing changed since the last save: both rightmost bottom buttons dark.
  - **Do:** On the drum page, turn on one step of the playing section's drum pattern.
  - **Pass if:** The upper bottom row's rightmost button lights red and the lowest row's rightmost gray, at once. Turning the step off again puts both out.

- [ ] **7. Revert**
  - **Need:** A step turned on since the last save, both lamps lit.
  - **Do:** Press the lowest row's rightmost button, the gray one.
  - **Pass if:** The step goes off on the drum page and the drums play the saved pattern, at once; both lamps go dark.

- [ ] **8. Save, and a reload**
  - **Need:** A change made, both lamps lit.
  - **Do:** Press the upper bottom row's rightmost button, the red one. Then load Cut It again from the Organelle menu.
  - **Pass if:** Both lamps go dark at the press. After the reload the change is still there and the lamps are dark.

- [ ] **9. A power cut keeps the draft**
  - **Need:** A change made since the last save, both lamps lit.
  - **Do:** Wait three seconds, then pull the Organelle's power. Power it on and load Cut It.
  - **Pass if:** The change is there, section 1 playing, and both lamps are lit: it is still unsaved. Revert takes it back to the save.

- [ ] **10. The phone's sections page**
  - **Need:** Page 7 on the Launchpad, the phone showing it.
  - **Do:** Tap the second row, then **new**, then **move up**, then drag **length** up, then **delete**.
  - **Pass if:** The phone's tab reads sections, its caption names the song, and each row shows its number, name and length, loop or bars. A tapped row lights and the right column names it. **new** adds a copy after it, named after it, "section 2" giving "section 3", and selected; **move up** moves it a row up, still selected; the length box reads loop, then 1 bar, 2 bars, as it is dragged; **delete** takes it away. The top row follows each change: as many lit buttons as sections.

- [ ] **11. Paging, and the top row scrolling**
  - **Need:** Page 7, the transport stopped.
  - **Do:** Tap **new** until there are eight sections. Page through the phone's list with its arrows. Then press the top row's right arrow seven times, a second apart.
  - **Pass if:** The list shows five rows a page, the page number with it, and the second page the rest. On the top row each press starts the next section at once, and from the seventh the six buttons scroll one section at a time, the playing one always lit on the row.

- [ ] **12. Naming a section**
  - **Need:** Page 7, a section selected.
  - **Do:** Tap the **name** tab. Tap backspace until the name is gone, type a new one with letters, a space and a digit, and tap **done**.
  - **Pass if:** The name tab opens on the selected section's name, in capitals. Each key types its character and backspace takes one off. **done** turns back to the sections tab, where the row reads the new name in lowercase.
