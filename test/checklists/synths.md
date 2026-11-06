# Synths checklist

The nanoKEY, the two synths it plays and the choice between them: the voices' pages, the phone's
keyboard tab and its velocity switch, and the Streichfett's place on the roster. `synths-assert` proves where every note
and every release goes, the choice's store and panic's channel; `phone-assert` and `touchosc-assert` the phone's side.
What is left is two synths you can hear and a chord under real fingers.

**Before you start:**

- The Volca and the Streichfett on, the mixer's channels 3 and 4 (the Volca) and 5 and 6 (the
  Streichfett) up, and the PA on.
- The song's voices the seed's: row 2 harmony on the Streichfett, row 3 melody on the Volca.
- The Volca's Velocity, CC 41, up: at the bottom the Volca plays nothing ([volca](../../ref/device/volca.md)).

13 steps. How to read one, and how to send a **Send** line: [the checklists' README](README.md). Why
each thing behaves as it does: [synths](../../ref/module/synths.md),
[streichfett](../../ref/device/streichfett.md), [nanokey](../../ref/device/nanokey.md).

- [ ] **1. A voice's page chooses its machine**
  - **Do:** Press the second button down the Launchpad's left column.
  - **Pass if:** It goes bright, and the phone's keyboard tab has STRINGS lit. Save and revert stay dark: looking at a voice's page changes nothing in the song.

- [ ] **2. The right column's the same**
  - **Do:** Press the third button down the right column, and then the second.
  - **Pass if:** The phone's keyboard tab goes to FM, and back to STRINGS. Save and revert stay dark.

- [ ] **3. The nanoKEY plays the Streichfett**
  - **Need:** STRINGS, row 2's page on show.
  - **Do:** Play a few keys and a chord on the nanoKEY, all over its range.
  - **Pass if:** The Streichfett plays every key and the Volca nothing. Each note stops when you let its key go.

- [ ] **4. Row 3's voice, and the nanoKEY plays the Volca**
  - **Do:** Press the third button down the left column, then play a few keys and a chord on the nanoKEY.
  - **Pass if:** The Volca plays every key and the Streichfett nothing.

- [ ] **5. A switch mid-chord, FM to STRINGS**
  - **Need:** Row 3's page on show.
  - **Do:** Hold a three-note chord on the nanoKEY. Still holding it, press row 2's left button with your other hand. Then let the chord go, and play a new one.
  - **Pass if:** The Volca's chord keeps sounding while held and stops when you let go; nothing keeps droning. The new chord plays on the Streichfett.
  - **Note:** A key's release goes to the synth its press went to. Sent to the synth chosen when it is released, it would never reach the Volca, which would drone until a panic.

- [ ] **6. A switch mid-chord, STRINGS to FM**
  - **Need:** Row 2's page on show.
  - **Do:** Hold a chord on the nanoKEY, press row 3's left button with your other hand, let the chord go, then play a new one.
  - **Pass if:** The Streichfett's chord stops when you let go, and the new chord plays on the Volca.

- [ ] **7. The choice holds on the performance page**
  - **Need:** Row 3's page on show, FM.
  - **Do:** Press its bright button, for the performance page. Play the nanoKEY.
  - **Pass if:** The Volca plays: the choice did not change.

- [ ] **8. The phone's keyboard tab**
  - **Need:** Row 2's page on the Launchpad, the phone showing Cut It, its keyboard tab chosen.
  - **Do:** Look at the phone, then tap STRINGS on it, then tap STRINGS again, then tap FM.
  - **Pass if:** The phone shows two large buttons, FM and STRINGS, the chosen one lit with dark text, and the velocity switch under them. Each tap of the unlit one lights it and changes the synth the nanoKEY plays. Tapping the lit one changes nothing.

- [ ] **9. The velocity switch**
  - **Need:** Row 2's page on the Launchpad, the phone showing its keyboard tab, FM chosen, the switch lit.
  - **Do:** Play one key very softly on the nanoKEY and one hard. Tap velocity on the phone and play the same two. Tap STRINGS on the phone and play them again. Then tap velocity once more and play them.
  - **Pass if:** At first the soft key is clearly softer than the hard one. At the tap the switch flashes teal and goes out, its text light, and soft and hard presses sound the same on the Volca and then on the Streichfett. At the second tap it lights again, dark text on the fill, and the soft key is soft again. Every note stops when its key is let go.
  - **Note:** Off sends every note-on at 127 and leaves releases alone (Brendan, 2026-11-04). The Launchpad has no control for it, and the line check's page no switch.

- [ ] **10. The choice survives a reload**
  - **Do:** Choose STRINGS and turn the phone's velocity switch off, wait three seconds, then load Cut It again from the Organelle menu. When it has booted, play the nanoKEY, softly and hard.
  - **Pass if:** The Streichfett plays, soft and hard keys the same. The phone's switch is out. Turn it back on.
  - **Note:** The choice and the switch are the section's parts synth and velocity, in the song's draft, flushed within two seconds of a change ([songs](../../ref/module/songs.md)).

- [ ] **11. Panic silences a held note**
  - **Need:** STRINGS chosen.
  - **Do:** Hold one key on the nanoKEY, and while it sounds tap the Launchpad's top-left corner button. Keep holding the key for a few seconds.
  - **Pass if:** The Streichfett stops at the tap, though the key is still down, and the grid flashes red for a second.
  - **Note:** Panic is All Notes Off, CC 123, on the Streichfett's channel, since keys bypass makenote; the same goes to the Volca on its own.

- [ ] **12. The Streichfett on the roster**
  - **Do:** Tap SETUP, the Launchpad's bottom left corner, then press the top row's first pad. Tap SETUP again after.
  - **Pass if:** The OLED lists six rows, m_streich among them as here, and m_nanokey as here once a key has been played since the load, never before.
  - **Note:** The nanoKEY is passive: it is never polled, since its identity reply carries the nanoKONTROL's byte, so a key is what says it is there ([nanokey](../../ref/device/nanokey.md)).

- [ ] **13. Hot-swap: the Streichfett unplugged and plugged back in**
  - **Do:** Pull the Streichfett's USB cable, and watch the OLED for up to eight seconds. Plug it back in, wait up to 30 seconds, choose STRINGS and play the nanoKEY.
  - **Pass if:** The OLED warns m_streich device-lost within about eight seconds of the pull. After the replug the Streichfett plays the nanoKEY's keys.
  - **Note:** It is polled every two seconds and lost after three missed replies; `u_present`'s shared re-wire brings it back ([presence](../../ref/module/presence.md)).
