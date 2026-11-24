# Synths checklist

The nanoKEY, the two synths it plays and the choice between them: the voices' pages, the phone's
keys page and its velocity switch, and the Streichfett's place on the roster. `synths-assert` proves where every note
and every release goes, the choice's store and panic's channel; `phone-assert` the phone's side.
What is left is two synths you can hear and a chord under real fingers.

**Before you start:**

- The FM-1 and the Streichfett on, the mixer's channels 3 and 4 (the FM-1) and 5 and 6 (the
  Streichfett) up, and the PA on.
- The song's voices the seed's: row 2 harmony on the Streichfett, row 3 melody on the FM-1.

13 steps. How to read one, and how to send a **Send** line: [the checklists' README](README.md). Why
each thing behaves as it does: [synths](../../ref/module/synths.md),
[streichfett](../../ref/device/streichfett.md), [nanokey](../../ref/device/nanokey.md).

- [ ] **1. A voice's page chooses its machine**
  - **Do:** Press the second button down the Launchpad's left column.
  - **Pass if:** It goes bright, and the phone turns to row 2's harmony page, its left button lit in the voice's color and the button across from it reading strings. Save and revert stay dark: looking at a voice's page changes nothing in the song.

- [ ] **2. The right column's the same**
  - **Do:** Press the third button down the right column, and then the second.
  - **Pass if:** The phone turns to row 3's setup page, its machine reading fm, and then to row 2's, reading strings. Save and revert stay dark.

- [ ] **3. The nanoKEY plays the Streichfett**
  - **Need:** Row 2's page on show, so strings is chosen.
  - **Do:** Play a few keys and a chord on the nanoKEY, all over its range.
  - **Pass if:** The Streichfett plays every key and the FM-1 nothing. Each note stops when you let its key go.

- [ ] **4. Row 3's voice, and the nanoKEY plays the FM-1**
  - **Do:** Press the third button down the left column, then play a few keys and a chord on the nanoKEY.
  - **Pass if:** The FM-1 plays every key and the Streichfett nothing.

- [ ] **5. A switch mid-chord, fm to strings**
  - **Need:** Row 3's page on show.
  - **Do:** Hold a three-note chord on the nanoKEY. Still holding it, press row 2's left button with your other hand. Then let the chord go, and play a new one.
  - **Pass if:** The FM-1's chord keeps sounding while held and stops when you let go; nothing keeps droning. The new chord plays on the Streichfett.
  - **Note:** A key's release goes to the synth its press went to. Sent to the synth chosen when it is released, it would never reach the FM-1, which would drone until a panic.

- [ ] **6. A switch mid-chord, strings to fm**
  - **Need:** Row 2's page on show.
  - **Do:** Hold a chord on the nanoKEY, press row 3's left button with your other hand, let the chord go, then play a new one.
  - **Pass if:** The Streichfett's chord stops when you let go, and the new chord plays on the FM-1.

- [ ] **7. The choice holds on the performance page**
  - **Need:** Row 3's page on show, so fm is chosen.
  - **Do:** Press its bright button, for the performance page. Play the nanoKEY.
  - **Pass if:** The FM-1 plays: the choice did not change.

- [ ] **8. The phone's keys page**
  - **Need:** Row 3's setup page on show, the third button down the right column, the song as saved.
  - **Do:** On the phone choose keys under does. Then press row 3's left button, look at the phone, and play the nanoKEY.
  - **Pass if:** Save and revert light at the choice: a voice's method is the song's. Row 3's left page on the phone is the keys page: the voice's name in its color, fm beside it, and the velocity switch under them, lit, its word black. The FM-1 plays every key.
  - **Note:** The layout's keyboard tab chose the synth with two buttons, FM and STRINGS; the app chooses it only by the voice on show ([phone](../../ref/device/phone.md), *Open*).

- [ ] **9. The velocity switch**
  - **Need:** Row 3's keys page on show, as step 8 left it, the switch lit.
  - **Do:** Play one key very softly on the nanoKEY and one hard. Tap velocity on the phone and play the same two. Press row 2's left button and play them again. Then press row 3's left button, tap velocity once more and play them.
  - **Pass if:** At first the soft key is clearly softer than the hard one. At the tap the switch goes dim, its word white, and soft and hard presses sound the same on the FM-1 and then on the Streichfett. At the second tap it lights again, its word black, and the soft key is soft again. Every note stops when its key is let go.
  - **Note:** Off sends every note-on at 127 and leaves releases alone (Brendan, 2026-11-04). The Launchpad has no control for it.

- [ ] **10. The switch survives a reload**
  - **Need:** Row 3's keys page on show, as step 9 left it.
  - **Do:** Turn the phone's velocity switch off, wait three seconds, then load Cut It again from the Organelle menu. When it has booted, press row 3's left button if its keys page isn't on show, and play the nanoKEY, softly and hard.
  - **Pass if:** The FM-1 plays, soft and hard keys the same, and the phone's switch is out. Turn it back on, then press revert, the lowest row's rightmost button, which puts row 3 back to melody.
  - **Note:** The switch is the section's part velocity, in the song's draft, flushed within two seconds of a change ([songs](../../ref/module/songs.md)). The choice a voice's page makes isn't put, so it isn't this step's: the layout's FM and STRINGS buttons were what put one.

- [ ] **11. Panic silences a held note**
  - **Need:** Row 2's page on show, so strings is chosen.
  - **Do:** Hold one key on the nanoKEY, and while it sounds tap the Launchpad's top-left corner button. Keep holding the key for a few seconds.
  - **Pass if:** The Streichfett stops at the tap, though the key is still down, and the grid flashes red for a second.
  - **Note:** Panic is All Notes Off, CC 123, on the Streichfett's channel, since keys bypass makenote; the FM-1, which ignores it, gets a note-off for every note and sustain off ([fm1](../../ref/device/fm1.md)).

- [ ] **12. The Streichfett on the roster**
  - **Do:** Tap SETUP, the Launchpad's bottom left corner, then press the top row's first pad. Tap SETUP again after.
  - **Pass if:** The OLED lists six rows, m_streich among them as here, and m_nanokey as here once a key has been played since the load, never before.
  - **Note:** The nanoKEY is passive: it is never polled, since its identity reply carries the nanoKONTROL's byte, so a key is what says it is there ([nanokey](../../ref/device/nanokey.md)).

- [ ] **13. Hot-swap: the Streichfett unplugged and plugged back in**
  - **Do:** Pull the Streichfett's USB cable, and watch the OLED for up to eight seconds. Plug it back in, wait up to 30 seconds, press row 2's left button and play the nanoKEY.
  - **Pass if:** The OLED warns m_streich device-lost within about eight seconds of the pull. After the replug the Streichfett plays the nanoKEY's keys.
  - **Note:** It is polled every two seconds and lost after three missed replies; `u_present`'s shared re-wire brings it back ([presence](../../ref/module/presence.md)).
