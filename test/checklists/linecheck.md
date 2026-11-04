# Line check

**Before a set, at the rig, from the phone**: is every device there and talking to the next, and does
sound reach the PA? It judges cables, power and settings, never code. That is the development
checklists' work, so a step that fails here points at a connection rather than a bug.

Run it from the phone's checklist page: choose mode 1 on the Launchpad, then tap Setup. No step
presses a mode button, because choosing a mode ends test mode and takes the page away. When it's
done, tap Setup again.

9 steps. How to read one: [the checklists' README](README.md). The cables and the signal flow:
[rig](../../ref/rig.md).

- [ ] **1. The phone and the Launchpad**
  - **Need:** Everything powered and cabled as in rig.md, Cut It loaded, mode 1 chosen, then Setup tapped.
  - **Pass if:** This page reads test mode on beside a lit teal lamp. The Launchpad's top mode lamp is lit, and its grid shows the drum page. Pass flashes as you tap it.
  - **Note:** The page coming up proves that Setup reached Cut It and that Cut It's heartbeat reached the phone. Pass flashing is the Organelle answering the phone, so the link works both ways.

- [ ] **2. Every device on the roster**
  - **Do:** Hold aux and press the Organelle's lowest key.
  - **Pass if:** The OLED lists m_launchpad, m_nano and m_404 as here, and m_volca as unchecked. About eight seconds later the meters come back.
  - **Note:** m_volca always reads unchecked: it sends nothing, so nothing can tell it is there, and step 7 listens for it instead. gone or never names the cable to look at ([display](../../ref/module/display.md)).

- [ ] **3. The 404's MIDI settings**
  - **Do:** On the 404, hold SHIFT and press pad 13, then SYSTEM, then CTRL 3 to the MIDI tab. Read it, and press nothing.
  - **Pass if:** MIDI Mode reads A; Soft Through, USB-MIDI Thru and MIDI Sync Out all read Off.
  - **Note:** If one of these drifts, Cut It stops driving the 404 and nothing reports it. Pressing VALUE on a setting that is already right turns it off ([rig](../../ref/rig.md), *Before a set*).

- [ ] **4. The 404 on Cut It's clock**
  - **Do:** Put the 404 on its Pattern Select screen.
  - **Pass if:** It reads EXT and the tempo on the OLED's footer.
  - **Note:** Cut It sends clock whether or not the transport runs. A 404 that has lost it falls back to its own tempo and reads BPM, not EXT.

- [ ] **5. A drum pad plays the 404, through the PA**
  - **Need:** The 404 on bank A with sounds there; the mixer's channels 1 and 2 up, and the PA on.
  - **Do:** Press the Launchpad's bottom-left drum pad, hard and then softly.
  - **Pass if:** The 404 plays bank A pad 13 each time, louder for the harder press, and the PA plays it. On the OLED, in-l moves with each hit and never reaches 100, while in-r stays still.
  - **Note:** Drums leave the 404 hard left, down the Y-cable's tip. The 404's volume, well past 10 o'clock, is set so its loudest hit peaks around 94, 6 dB under full scale; Cut It turns the input down 12 dB at every load, and that makes it up ([rig](../../ref/rig.md), *Signal flow — audio*).

- [ ] **6. The fx side**
  - **Do:** On the 404 itself, play an fx sample, one panned hard right.
  - **Pass if:** The PA plays it. On the OLED, in-r moves and in-l stays still.
  - **Note:** fx leave hard right, down the Y-cable's ring to the mixer's channel 2. One side silent is that cable or its plug.

- [ ] **7. The Organelle's keys play the Volca**
  - **Need:** The Volca on; the mixer's channels 3 and 4 up.
  - **Do:** Play a few Organelle keys. Then hold one and move the nanoKONTROL's fader 1.
  - **Pass if:** The PA plays the Volca for each key, and its tone changes as the fader moves. The OLED shows a volca-cc41 row for the fader.
  - **Note:** The Volca sends nothing back, so the ear is the only readout. A volca-cc41 row with no change in the sound points at the MIDI interface or its DIN cable.

- [ ] **8. PLAY and STOP**
  - **Do:** Press PLAY on the nanoKONTROL. After a bar, press STOP.
  - **Pass if:** On PLAY the aux LED goes green and a green pad walks the Launchpad's steps; on STOP the aux LED goes dark blue and the walking stops.

- [ ] **9. The phone where it sits for the set**
  - **Do:** Put the phone where it will be during the set and leave it there for a minute.
  - **Pass if:** This page still reads test mode on beside a lit lamp, and never no link.
  - **Note:** The link is UDP over WiFi; two seconds without a heartbeat reads no link ([phone](../../ref/device/phone.md)).
