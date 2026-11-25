# Songs checklist

Several songs and the setlists: the phone's songs page, which makes, loads, names and arranges them;
the Organelle's keys, which load the setlist chosen's songs; and the next arrow, the Launchpad's top
row's second. `song-assert` proves what a key restores, that a song left keeps
its draft, the arrow's colors and the files; `phone-assert` the phone's
side. What is left is a song you can hear take over on the downbeat, a lamp you can see blink,
the phone's page under a finger, and the SD card across a real power cut.

**Before you start:**

- The drums audible through the PA, the FM-1 and the Streichfett on, and the phone showing Cut It.
- Two songs that sound different: on the songs page, aux on the Organelle, choose **all songs** from the dropdown
  atop its left column, tap **new** under the list, then **load**, and on the drum page change its drum pattern and
  on the songs page its tempo; then press save, the rightmost small button in the upper row under the pads.
- A setlist of both: in all songs tap each in turn, then the **…** under the list and **add to setlist**.

13 steps. How to read one, and how to send a **Send** line: [the checklists' README](README.md).
Why each thing behaves as it does: [songs](../../ref/module/songs.md).

- [ ] **1. The songs page**
  - **Need:** The songs page, aux, the phone showing it, the setlist chosen from the dropdown atop its left column.
  - **Do:** Look at the phone's songs page, then tap the second row of its left column. Then open the dropdown, and the **…** under the list.
  - **Pass if:** Three columns: on the left the setlist's name over its songs, each a row with its key's number and its name, the song loaded named in green with a green bar at its left, and load, new and **…** under them; in the middle the loaded song's name over its sections; on the right the selected section's name over length, tempo, last step, time, swing, drunk and tweaks. The tapped row lights. The dropdown lists the setlists, then all songs, new setlist and name this setlist; the **…** name, add to setlist, take off setlist, move up, move down and, in red, delete song.

- [ ] **2. A new song, and naming it**
  - **Need:** The songs page, a setlist chosen from the dropdown, the transport stopped, the song loaded saved: save and revert, the rightmost of the small buttons under the Launchpad's pads, dark.
  - **Do:** Tap **new**, then the **…** and **name**. Delete the name, type a new one with a capital, tap **Done**.
  - **Pass if:** A row appears at the end of the setlist, "song 2" or the next number free, selected and named in green with a green bar at its left, and the middle column names it over its one section. **name** opens an alert reading song's name over a field holding the new song's name. **Done** closes it, and the row reads the new name in lowercase. Save and revert stay dark throughout.

- [ ] **3. The setlist**
  - **Need:** A setlist of two songs or more.
  - **Do:** Choose the setlist from the dropdown. Tap the second row, then the **…** and **move up**.
  - **Pass if:** The dropdown names the setlist, and each row shows its key and its song. Move up swaps the rows and their keys.

- [ ] **4. Stopped, a key loads at once**
  - **Need:** The transport stopped, the setlist's first song not loaded.
  - **Do:** Press the Organelle's lowest key, then PLAY.
  - **Pass if:** At the key the phone's left column names that song in green, with the green bar, its name heads the middle column and its tempo shows in the right; the top row shows its sections, section 1 bright. PLAY plays its pattern. Nothing shows on the OLED.

- [ ] **5. A song keeps its own draft**
  - **Need:** Two songs in the setlist, the transport stopped, the first loaded and as saved.
  - **Do:** On the drum page turn on one step of its pattern. Press the second key from the bottom, then the lowest key again.
  - **Pass if:** The step lights save and revert, and the middle column's heading shows unsaved in amber. After the second key the other song plays and the lamps go dark, while the left column reads unsaved, flush right in gray, beside the first. After the lowest key the first song is back, the step still on, save and revert lit again. Revert takes the step off.

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

- [ ] **11. Delete asks first**
  - **Need:** The songs page, all songs chosen from the dropdown, three songs or more, one not loaded selected.
  - **Do:** Tap the **…** under the list, then **delete song**, then **Cancel**. Then the **…**, **delete song** and **delete**.
  - **Pass if:** **delete song** asks, naming the selected song over delete in red and Cancel. **Cancel** deletes nothing. **delete** deletes that song and no other: its row goes, the next one selected and still there, and it is gone from the setlist too, the keys after it moving down one.
  - **Note:** `u_song` deletes at every `delete` it is sent, so the asking is the phone's ([songs](../../ref/module/songs.md), *Delete asks first*).

- [ ] **12. Setlists: a new one, and the arrows**
  - **Need:** The songs page, one setlist, chosen from the dropdown.
  - **Do:** Choose **new setlist** from the dropdown, and press the lowest key. Then choose set 1 from the dropdown and press the lowest key again. Choose **name this setlist**, type a name, tap **Done**.
  - **Pass if:** **new setlist** shows an empty "set 2", named in the dropdown, and the lowest key does nothing. Set 1 shows its songs again, and the lowest key loads its first song again. The alert reads setlist's name over a field holding the setlist's name; **Done** closes it, and the dropdown reads the new name.

- [ ] **13. A power cut keeps the songs**
  - **Need:** Two songs or more, one with an unsaved change, the other loaded; a setlist rearranged since the last load.
  - **Do:** Wait three seconds, then pull the Organelle's power. Power it on and load Cut It.
  - **Pass if:** The song that was loaded loads again, at section 1. All songs lists every song in its order, unsaved beside the one changed, and the setlist shows as it was rearranged.
