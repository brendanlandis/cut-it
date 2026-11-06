# Line check

**Before a set, at the rig, from the phone**: is every device there and talking to the next, and does
sound reach the PA? It judges cables, power and settings, never code. That is the development
checklists' work, so a step that fails here points at a connection rather than a bug.

Run it from the phone's checklist page: choose page 2, the drum page, the second button down the
Launchpad's left column, then tap Setup. No step
presses a mode button, because choosing a mode ends test mode and takes the page away. When it's
done, tap Setup again.

8 steps. How to read one: [the checklists' README](README.md). The cables and the signal flow:
[rig](../../ref/rig.md).

- [ ] **1. The phone and the Launchpad**
  - **Need:** Everything powered and cabled as in rig.md, Cut It loaded, page 2 chosen, then Setup tapped.
  - **Pass if:** This page reads test mode on beside a lit teal lamp. The Launchpad's second mode lamp down is lit, and its grid shows the drum page. Pass flashes as you tap it.
  - **Note:** The page coming up proves that Setup reached Cut It and that Cut It's heartbeat reached the phone. Pass flashing is the Organelle answering the phone, so the link works both ways.

- [ ] **2. Every device on the roster**
  - **Do:** Hold aux and press the Organelle's lowest key.
  - **Pass if:** The OLED lists m_launchpad, m_nano and m_streich as here, m_volca as unchecked, and m_nanokey as never or here. About eight seconds later the roster goes, and the info bar over a blank screen is left.
  - **Note:** m_volca always reads unchecked: it sends nothing, so nothing can tell it is there, and step 5 listens for it instead. m_streich is the Streichfett, which answers when asked. m_nanokey is never asked, and reads here only once a key has been played: steps 5 and 6 play it. gone or never on the others names the cable to look at ([display](../../ref/module/display.md)).

- [ ] **3. A drum pad plays through the PA**
  - **Need:** The mixer's channel 1 up, and the PA on.
  - **Do:** Press the Launchpad's bottom-left drum pad, pad 1, a few times.
  - **Pass if:** The PA plays pad 1's sample each time, as loud however hard you press. On the OLED's info bar one out meter jumps with each hit, out L, while the in meters and out R stay still.
  - **Note:** The drums are Cut It's own, played on the Organelle and out its left output to the mixer's channel 1 (Brendan, 2026-11-04). The info bar's out meters are what Cut It sends out, after the volume knob, and the drums never reach the in meters, which is how out L tells itself apart. A hit that moves out L and is silent in the PA is the cable or the mixer, and one that moves nothing is its sample missing: the deploy copies the sixteen from samples/drums/. At load Cut It warns when only some are there; with none, every pad is silent and nothing is drawn.

- [ ] **4. The mic**
  - **Need:** The SM58 in the Organelle's input.
  - **Do:** Sing or talk into the SM58.
  - **Pass if:** The PA plays your voice. On the info bar in L and out L move with it, and out L never reaches the end of its meter. Silent, every meter sits at 0.
  - **Note:** The mic goes in on the input's tip, and Cut It passes it straight to its left output beside the drums, so both come through the mixer's channel 1 and the same meter. A meter at its end is the voice clipping. A segment lit with the mic silent and the room quiet is its hiss, which should read 0: say so ([audio](../../ref/module/audio.md)).

- [ ] **5. The nanoKEY plays the Volca through the PA**
  - **Need:** The Volca on; the mixer's channels 3 and 4 up.
  - **Do:** Tap FM on this page, then play a few keys on the nanoKEY.
  - **Pass if:** FM lights on this page. The PA plays the Volca for each key, and not the Streichfett.
  - **Note:** The nanoKEY plays the synth chosen on any page, so the drum page can stay up (Brendan, 2026-11-04). This hears the nanoKEY, the Volca's MIDI link through its interface and its audio. A silent Volca can be its Velocity, CC 41, left at 0 by fader 1 on page 3, which this check cannot choose without ending test mode ([volca](../../ref/device/volca.md)).

- [ ] **6. The nanoKEY plays the Streichfett through the PA**
  - **Need:** The Streichfett on; the mixer's channels 5 and 6 up.
  - **Do:** Tap STRINGS on this page, then play a few keys on the nanoKEY.
  - **Pass if:** STRINGS lights on this page. The PA plays the Streichfett for each key, and not the Volca.
  - **Note:** The choice stays where this step leaves it, through the set, until FM or STRINGS is chosen again, here, on the phone's keyboard tab or on the Launchpad's page 3 ([synths](../../ref/module/synths.md)).

- [ ] **7. PLAY and STOP**
  - **Do:** Press PLAY on the nanoKONTROL. After a bar, press STOP.
  - **Pass if:** On PLAY the aux LED goes green and a green pad walks the Launchpad's steps; on STOP the aux LED goes dark blue and the walking stops.

- [ ] **8. The phone where it sits for the set**
  - **Do:** Put the phone where it will be during the set and leave it there for a minute.
  - **Pass if:** This page still reads test mode on beside a lit lamp, and never no link.
  - **Note:** The link is UDP over WiFi; two seconds without a heartbeat reads no link ([phone](../../ref/device/phone.md)).
