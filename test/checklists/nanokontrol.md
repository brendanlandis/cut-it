# nanoKONTROL checklist

Seven steps, and every one needs a hand on the controller: nothing but the real device exercises `[ctlin]`. Steps 1 to 3 sweep the surface; 4 to 7 pull the cable.

Hot-swap is three cases (item 235): lost mid-session (4), absent at load (6), and out and back in (7), the one that happens by accident when a cable is knocked. Only a device that has answered can be lost — `c_presence`'s warn is armed by a reply — so absent at load is its own case, and only a fresh load shows it recovered.

7 steps. How to read one, and how to send a **Send** line: [the checklists' README](README.md). Why each thing behaves as it does: [nanokontrol](../../ref/device/nanokontrol.md), [presence](../../ref/module/presence.md).

- [ ] **1. Every slider and knob**
  - **Do:** Sweep every slider and every knob. Watch slider 9 and knob 1 especially.
  - **Pass if:** Each control draws one row named for itself — slider-1 to slider-9 then knob-1 to knob-9 — unless the current mode maps it. On page 3 slider-1 reads volca-cc41 and no slider-1 row appears. None reports another's name.
  - **Note:** One row per control, and it is `u_map`'s (item 317): an unmapped control draws its own raw row, a mapped one its destination's. slider-1 is volca-cc 41 on page 3, so a slider-1 row beside volca-cc41 there is a double row.

- [ ] **2. Several faders at once**
  - **Do:** Move two faders at once, then three, then all nine.
  - **Pass if:** Two faders draw as stacked pairs. Three to five draw as small lines. Nine draws the five you touched first and refuses the rest. No row reshuffles while you are moving them.

- [ ] **3. Every button and transport key**
  - **Do:** Press every button, then all six transport keys.
  - **Pass if:** All 18 buttons name themselves on press and nothing on release. REW FF LOOP and REC report xport-1 xport-3 xport-4 and xport-6 as raw rows. PLAY starts the clock and STOP stops it and neither draws a row. No toggle.
  - **Note:** REW, FF, LOOP and REC miss the map and draw raw rows (item 242: a control that does nothing must say so). PLAY and STOP map to start and stop, button destinations that draw no row, and `m_nano` posts no row of its own (item 317).

- [ ] **4. Hot-swap — unplugged mid-session**
  - **Do:** Unplug the nanoKONTROL and leave it out.
  - **Pass if:** A bordered alert on the OLED reads warn and then m_nano.
  - **Note:** The alert is three missed presence ticks behind the unplug, so it comes up to 8 seconds after the cable is out.

- [ ] **5. Hot-swap — the diag roster names it**
  - **Need:** The nanoKONTROL still unplugged from the last step.
  - **Do:** Hold the aux button and press the lowest key. Check m_launchpad as well as m_nano: pulling one USB cable can knock a bystander off the bus, so a second line reading gone is worth knowing about rather than a miss.
  - **Pass if:** The m_nano line reads gone. The other three lines are unchanged and none of them reads gone.
  - **Note:** Between the unplug and the replug on purpose: the warn shows the loss was seen, and this shows you can ask about it afterwards.

- [ ] **6. Hot-swap — absent at load**
  - **Need:** The nanoKONTROL still unplugged from the last step.
  - **Do:** Load Cut It again from the Organelle menu, with the nanoKONTROL still unplugged, and let it boot. Plug it back in, wait 60 seconds, then move slider 1.
  - **Pass if:** Slider 1 draws a value row on the OLED.
  - **Note:** 60 seconds, because a replug can miss the first re-wires while the device enumerates (item 277). The slider is the oracle: the nano is passive, so only traffic arriving proves the subscription came back.

- [ ] **7. Hot-swap — unplugged and plugged back in**
  - **Do:** Unplug the nanoKONTROL and count to fifteen, then plug it back in and wait up to 60 seconds before moving slider 1.
  - **Pass if:** Slider 1 draws a value row on the OLED again when you move it.
  - **Note:** Not the absent-at-load path: this arms `u_present`'s counter on the way out and has to land one of the eight re-wires on the way back. Fifteen seconds out, because the loss is three missed ticks behind the unplug; up to 60 seconds back, as in step 6 (item 277). Last, so nothing after it needs a cable out.
