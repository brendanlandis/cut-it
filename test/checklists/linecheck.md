# Line check

**Before a set, at the rig, from the phone**: is every device there and talking to the next, and does
sound reach the PA? It judges cables, power and settings, never code. That is the development
checklists' work, so a step that fails here points at a connection rather than a bug.

Run it from the phone's checklist page: choose mode 1 on the Launchpad, then tap Setup. No step
presses a mode button, because choosing a mode ends test mode and takes the page away. When it's
done, tap Setup again.

8 steps. How to read one: [the checklists' README](README.md). The cables and the signal flow:
[rig](../../ref/rig.md).

- [ ] **1. The phone and the Launchpad**
  - **Need:** Everything powered and cabled as in rig.md, Cut It loaded, mode 1 chosen, then Setup tapped.
  - **Pass if:** This page reads test mode on beside a lit teal lamp. The Launchpad's top mode lamp is lit, and its grid shows the drum page. Pass flashes as you tap it.
  - **Note:** The page coming up proves that Setup reached Cut It and that Cut It's heartbeat reached the phone. Pass flashing is the Organelle answering the phone, so the link works both ways.

- [ ] **2. Every device on the roster**
  - **Do:** Hold aux and press the Organelle's lowest key.
  - **Pass if:** The OLED lists m_launchpad, m_nano and m_404 as here, and m_volca as unchecked. About eight seconds later the meters come back.
  - **Note:** m_volca always reads unchecked: it sends nothing, so nothing can tell it is there, and step 6 listens for it instead. gone or never names the cable to look at ([display](../../ref/module/display.md)).

- [ ] **3. The 404's MIDI settings**
  - **Do:** On the 404, hold SHIFT and press pad 13, then SYSTEM, then CTRL 3 to the MIDI tab. Read it, and press nothing.
  - **Pass if:** MIDI Mode reads A; Soft Through, USB-MIDI Thru and MIDI Sync Out all read Off.
  - **Note:** The 404's sound is out of the rig, but its pads and CTRL knobs still reach Cut It. If one of these drifts, they stop working or MIDI echoes, and nothing reports it. Pressing VALUE on a setting that is already right turns it off ([rig](../../ref/rig.md), *Before a set*).

- [ ] **4. A drum pad plays through the PA**
  - **Need:** The mixer's channel 1 up, and the PA on.
  - **Do:** Press the Launchpad's bottom-left drum pad, pad 1, a few times.
  - **Pass if:** The PA plays pad 1's sample each time, as loud however hard you press.
  - **Note:** The drums are Cut It's own, played on the Organelle and out its left output to the mixer's channel 1 (Brendan, 2026-11-04). A silent pad is its sample missing: the deploy copies the sixteen from samples/drums/. At load Cut It warns in compose when only some are there; with none, every pad is silent and nothing is drawn.

- [ ] **5. The mic**
  - **Need:** The SM58 in the Organelle's input.
  - **Do:** Sing or talk into the SM58.
  - **Pass if:** The PA plays your voice. On the OLED, in-l moves with it and never reaches 100.
  - **Note:** The mic goes in on the input's tip, and Cut It passes it straight to its left output beside the drums, so both come through the mixer's channel 1.

- [ ] **6. The Organelle's keys play the Volca**
  - **Need:** The Volca on; the mixer's channels 3 and 4 up.
  - **Do:** Play a few Organelle keys. Then hold one and move the nanoKONTROL's fader 1.
  - **Pass if:** The PA plays the Volca for each key, and its tone changes as the fader moves. The OLED shows a volca-cc41 row for the fader.
  - **Note:** The Volca sends nothing back, so the ear is the only readout. A volca-cc41 row with no change in the sound points at the MIDI interface or its DIN cable.

- [ ] **7. PLAY and STOP**
  - **Do:** Press PLAY on the nanoKONTROL. After a bar, press STOP.
  - **Pass if:** On PLAY the aux LED goes green and a green pad walks the Launchpad's steps; on STOP the aux LED goes dark blue and the walking stops.

- [ ] **8. The phone where it sits for the set**
  - **Do:** Put the phone where it will be during the set and leave it there for a minute.
  - **Pass if:** This page still reads test mode on beside a lit lamp, and never no link.
  - **Note:** The link is UDP over WiFi; two seconds without a heartbeat reads no link ([phone](../../ref/device/phone.md)).
