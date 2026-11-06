# Songs checklist

Several songs and the setlists: the phone's songs page, which makes, loads, names and arranges them;
the Organelle's keys, which load the setlist chosen's songs; and the next arrow, the Launchpad's top
row's second. `song-assert` proves what a key restores, that a song left keeps
its draft, the arrow's colors and the files; `phone-assert` and `touchosc-assert` the phone's
side. What is left is a song you can hear take over on the downbeat, a lamp you can see blink,
the phone's page under a finger, and the SD card across a real power cut.

**Before you start:**

- The drums audible through the PA, the Volca and the Streichfett on, and the phone showing Cut It.
- Two songs that sound different: on the songs page, aux on the Organelle, its songs tab: tap **new song**,
  **load** it, and on the drum page change its drum pattern and on the arrangement screen its tempo; then press save, the upper bottom row's
  rightmost button.
- A setlist of both: on the songs tab select each in turn and tap **add to set**.

13 steps. How to read one, and how to send a **Send** line: [the checklists' README](README.md).
Why each thing behaves as it does: [songs](../../ref/module/songs.md).

- [ ] **1. The songs page**
  - **Need:** The songs page, aux, the phone showing it.
  - **Do:** Look at the phone's songs tab, then tap the second row.
  - **Pass if:** The tab bar reads songs, setlists and name, songs lit. Each song is a row, its number, its name and, flush right in gray, `loaded` on the song playing. The tapped row lights and its name heads the right column, over load, new song, name, add to set and delete.

- [ ] **2. A new song, and naming it**
  - **Need:** The songs page's songs tab, the song loaded saved: the Launchpad's two rightmost bottom buttons dark.
  - **Do:** Tap **new song**, then **name**. Backspace the name away, type a new one, tap **done**.
  - **Pass if:** A row appears after the selected one, "song 2" or the next number free, selected. **name** opens the name tab, reading "name the song" over the new song's name in capitals. **done** turns back to the songs tab, where the row reads the new name in lowercase. The Launchpad's two rightmost bottom buttons stay dark throughout.

- [ ] **3. The setlist**
  - **Need:** A setlist of two songs or more.
  - **Do:** Tap the setlists tab. Tap the second row, then **move up**.
  - **Pass if:** The caption names the setlist, the pager reads `set 1 / 1`, and each row shows its key and its song. Move up swaps the rows and their keys.

- [ ] **4. Stopped, a key loads at once**
  - **Need:** The transport stopped, the setlist's first song not loaded.
  - **Do:** Press the Organelle's lowest key, then PLAY.
  - **Pass if:** At the key the phone's songs tab moves `loaded` to that song and its tempo shows on the arrangement screen; the top row shows its sections, section 1 bright. PLAY plays its pattern. Nothing shows on the OLED.

- [ ] **5. A song keeps its own draft**
  - **Need:** Two songs in the setlist, the transport stopped, the first loaded and as saved.
  - **Do:** On the drum page turn on one step of its pattern. Press the second key from the bottom, then the lowest key again.
  - **Pass if:** The step lights save and revert. After the second key the other song plays and the lamps go dark, while the songs tab reads `unsaved` beside the first. After the lowest key the first song is back, the step still on, save and revert lit again. Revert takes the step off.

- [ ] **6. Playing, a key**
  - **Need:** Playing, the setlist's first song loaded.
  - **Do:** Press the second key from the bottom mid-pattern, and listen.
  - **Pass if:** The Launchpad's next arrow blinks blue on the beat while the first song's pattern plays on to its end. The second song takes over on the pattern's step 1, its first step on that downbeat, and the button goes dark.

- [ ] **7. The next arrow**
  - **Need:** Playing, a song of the setlist on its last section, another song after it.
  - **Do:** Press the top row's second button. Press the first. Press the second again, and let the pattern come round.
  - **Pass if:** On the last section the arrow is blue. The first press makes it blink; the back arrow stops the blinking and nothing changes; the third blinks, and the next song starts as the pattern comes round.

- [ ] **8. From silence**
  - **Need:** Playing, a song on its last section, another after it.
  - **Do:** Press STOP, then the next arrow, then PLAY.
  - **Pass if:** The arrow loads the next song at once, the aux LED going from green to blue, its tempo showing. PLAY plays it from its first section.

- [ ] **9. Nothing past the setlist's end**
  - **Need:** A setlist of fewer than 25 songs, playing.
  - **Do:** Press the Organelle's highest key.
  - **Pass if:** Nothing changes: the same song plays on, the arrow doesn't blink, the phone shows nothing new.

- [ ] **10. STOP with a song queued**
  - **Need:** Playing.
  - **Do:** Press a song's key, wait for the arrow's blink, then press STOP.
  - **Pass if:** At STOP the song loads at once, ready for PLAY, and the blinking stops.

- [ ] **11. Delete asks twice**
  - **Need:** The songs page's songs tab, three songs or more, one not loaded selected.
  - **Do:** Tap **delete** once and wait four seconds. Then tap it twice, quickly.
  - **Pass if:** The first tap turns its word to sure?, and after three seconds it reads delete again with nothing deleted. The two quick taps delete the song: its row goes, the next one selected, and it is gone from the setlist too, the keys after it moving down one.

- [ ] **12. Setlists: a new one, and the arrows**
  - **Need:** Page 8's setlists tab, one setlist.
  - **Do:** Tap **new set**, press the lowest key, then tap the pager's left arrow and press the lowest key again. Tap the name tab, type a name, tap **done**.
  - **Pass if:** **new set** shows an empty "set 2", `set 2 / 2`, and the lowest key does nothing. The left arrow shows set 1, `set 1 / 2`, and the lowest key loads its first song again. The name tab reads "name the setlist"; **done** turns back to the setlists tab, its caption the new name.

- [ ] **13. A power cut keeps the songs**
  - **Need:** Two songs or more, one with an unsaved change, the other loaded; a setlist rearranged since the last load.
  - **Do:** Wait three seconds, then pull the Organelle's power. Power it on and load Cut It.
  - **Pass if:** The song that was loaded loads again, at section 1. The songs tab lists every song in its order, `unsaved` beside the one changed, and the setlists tab shows the setlist as it was rearranged.
