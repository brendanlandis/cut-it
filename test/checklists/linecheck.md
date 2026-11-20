# Line check

**Before a set, at the rig, from this file**: is every device there and talking to the next, and does
sound reach the PA? It judges cables, power and settings, never code. That is the development
checklists' work, so a step that fails here points at a connection rather than a bug.

Run it from this file, on the Mac or printed: tap Setup, the Launchpad's bottom-left button, which opens
the diagnostics page on the Launchpad and on the phone; steps 1 and 2 use it. When it's done, choose a
page.

8 steps. How to read one: [the checklists' README](README.md). The cables and the signal flow:
[rig](../../ref/rig.md).

- [ ] **1. The phone and the Launchpad**
  - **Need:** Everything powered and cabled as in rig.md, Cut It loaded, the Cut It app open on the phone, Setup tapped.
  - **Do:** Tap test mode on the phone, then tap it again.
  - **Pass if:** The phone shows the diagnostics page, its diagnostics and test mode buttons, with no red no link bar over it. The Launchpad's top row of pads has its first two lit, green and blue. The first tap puts a bordered box reading warn then u_net then test-mode-on on the OLED for about two seconds; the second puts nothing up.
  - **Note:** The page coming up proves that Setup reached Cut It and that Cut It's state reached the phone. The OLED's box is the Organelle hearing the phone, so the link works both ways. Test mode puts nothing else up since the phone's checklist page went (2026-11-19; [phone](../../ref/device/phone.md), *Open*).

- [ ] **2. Every device on the roster**
  - **Do:** Press the Launchpad's top left pad, the green one.
  - **Pass if:** The OLED lists m_launchpad, m_nano and m_streich as here, m_volca as unchecked, and m_nanokey as never or here. About eight seconds later the roster goes, and the info bar over a blank screen is left.
  - **Note:** m_volca always reads unchecked: it sends nothing, so nothing can tell it is there, and step 5 listens for it instead. m_streich is the Streichfett, which answers when asked. m_nanokey is never asked, and reads here only once a key has been played: steps 5 and 6 play it. gone or never on the others names the cable to look at ([display](../../ref/module/display.md)).

- [ ] **3. The drums play through the PA**
  - **Need:** The mixer's channel 1 up, and the PA on, and a pattern in the song loaded.
  - **Do:** Press PLAY on the nanoKONTROL, listen for a bar, and press STOP.
  - **Pass if:** The PA plays the drums, and on the OLED's info bar one out meter jumps with each hit, out L, while the in meters and out R stay still.
  - **Note:** The drums are Cut It's own, played on the Organelle and out its left output, alone, to the mixer's channel 1 (Brendan, 2026-11-04; alone since 2026-11-14). The info bar's out meters are what Cut It sends out, after the volume knob, and the drums never reach the in meters, which is how out L tells itself apart. A hit that moves out L and is silent in the PA is the cable or the mixer, and one that moves nothing is its sample missing: the deploy copies the sixteen from samples/drums/. At load Cut It warns when only some are there; with none, every pad is silent and nothing is drawn.

- [ ] **4. The mic**
  - **Need:** The SM58 in the Organelle's input; the mixer's channel 2 up.
  - **Do:** Sing or talk into the SM58.
  - **Pass if:** The PA plays your voice. On the info bar in L and out R move with it, out L stays still, and out R never reaches the end of its meter. Silent, every meter sits at 0.
  - **Note:** The mic goes in on the input's tip, and Cut It passes it straight to its right output with the synths, so it comes through the mixer's channel 2 and the drums have channel 1 to themselves (Brendan, 2026-11-14). Out L moving with the voice is an older patch; the voice on channel 1 with out R moving is the headphone split's two plugs swapped. A meter at its end is the voice clipping. A segment lit with the mic silent and the room quiet is its hiss, which should read 0: say so ([audio](../../ref/module/audio.md)).

- [ ] **5. The nanoKEY plays the Volca through the PA**
  - **Need:** The Volca on; the mixer's channels 3 and 4 up; a song loaded with a voice on fm and one on strings, the machine the phone's right column names.
  - **Do:** Press the Launchpad's left-column button for the voice on fm, then play a few keys on the nanoKEY.
  - **Pass if:** The phone shows that voice's page. The PA plays the Volca for each key, and not the Streichfett.
  - **Note:** A voice's page on fm or strings chooses what the nanoKEY plays, and the performance page leaves it on the last ([voices](../../ref/module/voices.md)). This hears the nanoKEY, the Volca's MIDI link through its interface and its audio. A silent Volca can be its Velocity, CC 41, left at 0 ([volca](../../ref/device/volca.md)).

- [ ] **6. The nanoKEY plays the Streichfett through the PA**
  - **Need:** The Streichfett on; the mixer's channels 5 and 6 up.
  - **Do:** Press the Launchpad's left-column button for the voice on strings, then play a few keys on the nanoKEY.
  - **Pass if:** The phone shows that voice's page. The PA plays the Streichfett for each key, and not the Volca.
  - **Note:** The choice stays where this step leaves it until another voice's page on fm or strings is shown ([synths](../../ref/module/synths.md)).

- [ ] **7. PLAY and STOP**
  - **Do:** Press PLAY on the nanoKONTROL. After a bar, press STOP.
  - **Pass if:** On PLAY the aux LED goes green and the Launchpad stays on its two pads; on STOP the aux LED goes dark blue.

- [ ] **8. The phone where it sits for the set**
  - **Do:** Put the phone where it will be during the set and leave it there for a minute.
  - **Pass if:** The phone never shows its red no link bar.
  - **Note:** The link is UDP over WiFi; two seconds without a heartbeat reads no link ([phone](../../ref/device/phone.md)).
