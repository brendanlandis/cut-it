# nanoKONTROL checklist

Seven steps, and every one needs a hand on the controller: nothing but the real device exercises `[ctlin]`. Steps 1 to 3 sweep the surface; 4 to 7 pull the cable.

Hot-swap is three cases (item 235): lost mid-session (4), absent at load (6), and out and back in (7), the one that happens by accident when a cable is knocked. Only a device that has answered can be lost — `c_presence`'s warn is armed by a reply — so absent at load is its own case, and only a fresh load shows it recovered.

7 steps. How to read one, and how to send a **Send** line: [the checklists' README](README.md). Why each thing behaves as it does: [nanokontrol](../../ref/device/nanokontrol.md), [presence](../../ref/module/presence.md).

- [ ] **1. Every slider and knob**
  - **Send:** `mode mode-3`
  - **Do:** Sweep every slider and every knob. Watch slider 9 and knob 1 especially.
  - **Pass if:** Slider 1 draws one row, volca-cc41 and its value, and no slider-1 row appears. Every other slider and knob draws nothing, and none draws volca-cc41.
  - **Note:** Only a control the map binds names itself, by its destination's name, and the row is `u_map`'s alone (Brendan, 2026-11-04; item 317): slider-1 is volca-cc 41 on page 3, so a slider-1 row beside volca-cc41 is a double row, and volca-cc41 from another control is two CCs decoded as one. Which name each CC decodes to is `nano-assert`'s, every one of them.

- [ ] **2. Fader 1 beside the Organelle's knobs**
  - **Send:** `mode mode-3`
  - **Do:** Move slider 1 and turn the Organelle's knob 2 a little at the same time. Then add knob 4.
  - **Pass if:** Two controls draw as stacked pairs, volca-cc41 over last-step, first touched on top. With knob 4 as well, three small lines. No row reshuffles while you are moving them.
  - **Note:** Slider 1 is the one nanoKONTROL control page 3 maps, and knobs 2 and 4 are mapped on every page (Brendan, 2026-11-04). Turned a little they are held and change nothing. Five rows and a refused sixth are the display checklist's, sent.

- [ ] **3. Every button and transport key**
  - **Do:** Press every button, then all six transport keys.
  - **Pass if:** PLAY starts the clock, the aux LED green, and STOP stops it, dark blue. Nothing else happens, and no button or transport key draws a row on the OLED. No toggle.
  - **Note:** PLAY and STOP map to start and stop, button destinations that draw no row; the 18 buttons and REW, FF, LOOP and REC are unmapped, and only a mapped control names itself (Brendan, 2026-11-04). `m_nano` posts no row of its own (item 317). Which name each publishes is `nano-assert`'s.

- [ ] **4. Hot-swap — unplugged mid-session**
  - **Do:** Unplug the nanoKONTROL and leave it out.
  - **Pass if:** A bordered alert on the OLED reads warn and then m_nano.
  - **Note:** The alert is three missed presence ticks behind the unplug, so it comes up to 8 seconds after the cable is out.

- [ ] **5. Hot-swap — the diag roster names it**
  - **Need:** The nanoKONTROL still unplugged from the last step.
  - **Do:** Hold the aux button and press the lowest key. Check m_launchpad as well as m_nano: pulling one USB cable can knock a bystander off the bus, so a second line reading gone is worth knowing about rather than a miss.
  - **Pass if:** The m_nano line reads gone. The other four lines are unchanged and none of them reads gone.
  - **Note:** Between the unplug and the replug on purpose: the warn shows the loss was seen, and this shows you can ask about it afterwards.

- [ ] **6. Hot-swap — absent at load**
  - **Need:** The nanoKONTROL still unplugged from the last step.
  - **Do:** Load Cut It again from the Organelle menu, with the nanoKONTROL still unplugged, and let it boot. Press page 3 on the Launchpad. Plug the nanoKONTROL back in, wait 60 seconds, then move slider 1.
  - **Pass if:** Slider 1 draws volca-cc41 and its value on the OLED.
  - **Note:** 60 seconds, because a replug can miss the first re-wires while the device enumerates (item 277). The slider is the oracle: the nano is passive, so only traffic arriving proves the subscription came back.

- [ ] **7. Hot-swap — unplugged and plugged back in**
  - **Do:** Press page 3 on the Launchpad. Unplug the nanoKONTROL and count to fifteen, then plug it back in and wait up to 60 seconds before moving slider 1.
  - **Pass if:** Slider 1 draws volca-cc41 and its value on the OLED again when you move it.
  - **Note:** Not the absent-at-load path: this arms `u_present`'s counter on the way out and has to land one of the eight re-wires on the way back. Fifteen seconds out, because the loss is three missed ticks behind the unplug; up to 60 seconds back, as in step 6 (item 277). Last, so nothing after it needs a cable out.
