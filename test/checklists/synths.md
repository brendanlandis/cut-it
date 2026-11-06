# Synths checklist

The nanoKEY, the two synths it plays and the choice between them: page 3's pads, the phone's
keyboard tab and its velocity switch, and the Streichfett's place on the roster. `synths-assert` proves where every note
and every release goes, the choice's store and panic's channel; `display-assert` what page 3
paints; `phone-assert` and `touchosc-assert` the phone's side. What is left is two synths you can
hear, colors you can see and a chord under real fingers.

**Before you start:**

- The Volca and the Streichfett on, the mixer's channels 3 and 4 (the Volca) and 5 and 6 (the
  Streichfett) up, and the PA on.
- Slider 1 on the nanoKONTROL up: on page 3 it is the Volca's Velocity, CC 41, and at the bottom
  the Volca plays nothing ([volca](../../ref/device/volca.md)).

13 steps. How to read one, and how to send a **Send** line: [the checklists' README](README.md). Why
each thing behaves as it does: [synths](../../ref/module/synths.md),
[streichfett](../../ref/device/streichfett.md), [nanokey](../../ref/device/nanokey.md).

- [ ] **1. Page 3's synth pads**
  - **Do:** Press the third button down the Launchpad's left column.
  - **Pass if:** The third mode lamp is lit. On the second row from the bottom the left four pads are amber and the right four cyan, and one block is clearly brighter than the other: the left, FM, on a first load, or whichever was chosen last. The bottom row is the beat row, as on page 1.

- [ ] **2. STRINGS from its pad**
  - **Need:** Page 3.
  - **Do:** Press any of the right four pads on the second row.
  - **Pass if:** The right block goes bright and the left block dim at once, and stays so after you let go.

- [ ] **3. The nanoKEY plays the Streichfett**
  - **Need:** Page 3, the right block bright.
  - **Do:** Play a few keys and a chord on the nanoKEY, all over its range.
  - **Pass if:** The Streichfett plays every key and the Volca nothing. Each note stops when you let its key go.

- [ ] **4. FM from its pad, and the nanoKEY plays the Volca**
  - **Need:** Page 3.
  - **Do:** Press any of the left four pads on the second row, then play a few keys and a chord on the nanoKEY.
  - **Pass if:** The left block goes bright and the right dim. The Volca plays every key and the Streichfett nothing.

- [ ] **5. A switch mid-chord, FM to STRINGS**
  - **Need:** Page 3, the left block bright.
  - **Do:** Hold a three-note chord on the nanoKEY. Still holding it, press a STRINGS pad with your other hand. Then let the chord go, and play a new one.
  - **Pass if:** The Volca's chord keeps sounding while held and stops when you let go; nothing keeps droning. The new chord plays on the Streichfett.
  - **Note:** A key's release goes to the synth its press went to. Sent to the synth chosen when it is released, it would never reach the Volca, which would drone until a panic.

- [ ] **6. A switch mid-chord, STRINGS to FM**
  - **Need:** Page 3, the right block bright.
  - **Do:** Hold a chord on the nanoKEY, press an FM pad with your other hand, let the chord go, then play a new one.
  - **Pass if:** The Streichfett's chord stops when you let go, and the new chord plays on the Volca.

- [ ] **7. The choice holds on every other page**
  - **Need:** FM chosen.
  - **Do:** Press the top button of the Launchpad's left column, page 1. Play the nanoKEY. Press the second row's second, third and fourth pads, then its right four, and play again.
  - **Pass if:** The Volca plays both times: the choice did not change. The second row is dark on page 1 but for its first pad, the tap pad, dim yellow, and the pads pressed do nothing.

- [ ] **8. The phone's keyboard tab**
  - **Need:** Page 3 on the Launchpad, the phone showing Cut It, its keyboard tab chosen.
  - **Do:** Look at the phone, then tap STRINGS on it, then tap STRINGS again, then tap FM.
  - **Pass if:** The phone shows two large buttons, FM and STRINGS, the chosen one lit with dark text, the same one bright on the Launchpad, and the velocity switch under them. Each tap of the unlit one lights it, swaps the Launchpad's blocks and changes the synth the nanoKEY plays. Tapping the lit one changes nothing.

- [ ] **9. The velocity switch**
  - **Need:** Page 3 on the Launchpad, the phone showing its keyboard tab, FM chosen, the switch lit.
  - **Do:** Play one key very softly on the nanoKEY and one hard. Tap velocity on the phone and play the same two. Tap STRINGS on the phone and play them again. Then tap velocity once more and play them.
  - **Pass if:** At first the soft key is clearly softer than the hard one. At the tap the switch flashes teal and goes out, its text light, and soft and hard presses sound the same on the Volca and then on the Streichfett. At the second tap it lights again, dark text on the fill, and the soft key is soft again. Every note stops when its key is let go.
  - **Note:** Off sends every note-on at 127 and leaves releases alone (Brendan, 2026-11-04). The Launchpad has no control for it, and the line check's page no switch.

- [ ] **10. The choice survives a reload**
  - **Do:** Choose STRINGS and turn the phone's velocity switch off, wait three seconds, then load Cut It again from the Organelle menu. When it has booted, press the third button down the left column and play the nanoKEY, softly and hard.
  - **Pass if:** The right block is bright and the Streichfett plays, soft and hard keys the same. The phone's switch is out. Turn it back on.
  - **Note:** The choice and the switch are the auto keys synth and velocity in cut-it-auto.txt, flushed within two seconds of a change ([state](../../ref/module/state.md)).

- [ ] **11. Panic silences a held note**
  - **Need:** STRINGS chosen.
  - **Do:** Hold one key on the nanoKEY, and while it sounds tap the Launchpad's top-left corner button. Keep holding the key for a few seconds.
  - **Pass if:** The Streichfett stops at the tap, though the key is still down, and the grid flashes red for a second.
  - **Note:** Panic is All Notes Off, CC 123, on the Streichfett's channel, since keys bypass makenote; the same goes to the Volca on its own.

- [ ] **12. The Streichfett on the roster**
  - **Do:** Hold aux and press the Organelle's lowest key.
  - **Pass if:** The OLED lists six rows, m_streich among them as here, and m_nanokey as here once a key has been played since the load, never before.
  - **Note:** The nanoKEY is passive: it is never polled, since its identity reply carries the nanoKONTROL's byte, so a key is what says it is there ([nanokey](../../ref/device/nanokey.md)).

- [ ] **13. Hot-swap: the Streichfett unplugged and plugged back in**
  - **Do:** Pull the Streichfett's USB cable, and watch the OLED for up to eight seconds. Plug it back in, wait up to 30 seconds, choose STRINGS and play the nanoKEY.
  - **Pass if:** The OLED warns m_streich device-lost within about eight seconds of the pull. After the replug the Streichfett plays the nanoKEY's keys.
  - **Note:** It is polled every two seconds and lost after three missed replies; `u_present`'s shared re-wire brings it back ([presence](../../ref/module/presence.md)).
