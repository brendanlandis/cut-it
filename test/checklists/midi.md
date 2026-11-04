# MIDI checklist

The mode-dependent map and the Volca, its one output device. `map-assert` proves the lookup and the allowlist guard, and `volca-assert` what the Volca is sent; what is left is a real fader under a real finger, and a Volca you can hear. There is no Volca checklist: it lives here. The SP-404's steps went with it when it left the rig (2026-11-04).

Hot-swap for the Volca, which is `none`: it transmits nothing and can never be polled, so `u_present`'s re-wire heartbeat is what brings it back (9 and 10).

**Before you start:**

- Knob 1 saved at 57 BPM: step 1 reads it back from `knobs.txt`.

10 steps. How to read one, and how to send a **Send** line: [the checklists' README](README.md). Why each thing behaves as it does: [map](../../ref/module/map.md), [volca](../../ref/device/volca.md).

- [ ] **1. Restored tempo at boot**
  - **Pass if:** The footer reads 57 BPM and not 120 BPM. The lit mode lamp is wherever you left it — note which one it is.
  - **Note:** Rig only: 57 comes from `knobs.txt`, which no Mac has.

- [ ] **2. Get to page 3**
  - **Do:** Press the third button down the Launchpad left column — page 3, the synths page.
  - **Pass if:** The lit lamp moves to the third position. Nothing below works until it does.

- [ ] **3. Fader 1 on page 3**
  - **Need:** The Volca audible. It transmits nothing so this step and the two after it are judged by ear with no readback of any kind.
  - **Do:** On page 3 move fader 1 on the nanoKONTROL.
  - **Pass if:** The Volca tone changes as you move it. The OLED shows one row for the fader — volca-cc41 and the value — and no slider-1 row.

- [ ] **4. Fader 1 on page 4**
  - **Do:** Press the fourth button down the Launchpad left column then move fader 1.
  - **Pass if:** The Volca does not change — no change is the pass. The OLED shows slider-1 and its raw value because nothing maps it on page 4 and that is correct.

- [ ] **5. Fader 1 back on page 3**
  - **Do:** Press the third button down the Launchpad left column then move fader 1 again.
  - **Pass if:** The Volca responds again. Still silent means the page did not change back — check the lit lamp.

- [ ] **6. Tempo from knob 1**
  - **Do:** Sweep knob 1 all the way and back.
  - **Pass if:** The footer BPM follows the knob over roughly 10 to 500 BPM once the knob has crossed the restored value. Nothing at all happens before it crosses.

- [ ] **7. Transport from PLAY and STOP**
  - **Do:** Press PLAY on the nanoKONTROL, then STOP.
  - **Pass if:** The aux LED goes green on PLAY and dark blue on STOP.
  - **Note:** No footer claim: the rows from the steps above raise the param layer over it. The aux LED is the readout.

- [ ] **8. Panic is unbound**
  - **Do:** Press every transport key on the nanoKONTROL and every button on the Organelle. Turn the encoder. Nothing should ever go red.
  - **Pass if:** The aux LED never turns red however many controls you press.
  - **Note:** That no map row names panic is `map-assert`'s, read from `cut-it-map.txt`; this asks only what fingers can answer — that no control anyone reaches for raises it.

- [ ] **9. Hot-swap — Volca unplugged and plugged back in**
  - **Need:** Page 3. Slider 1 is the only control bound to the Volca.
  - **Do:** Unplug the Volca interface alone and count to fifteen, then plug it back in and wait up to 30 seconds before sweeping slider 1 while holding a Volca key. Then unplug it again: the next step loads without it.
  - **Pass if:** Holding a Volca key and sweeping slider 1 changes the sound — by ear.
  - **Note:** The oracle is the fader changing the sound, never the Volca sounding: it plays from its own keys with no MIDI connected at all ([volca](../../ref/device/volca.md)). The Volca alone, because it registers `none` and comes back through `u_present`'s re-wire heartbeat (`wire-watch.sh` every eight ticks, re-wiring when the client names change); pulling a second device would go through the loss path instead (item 275). 30 seconds covers the heartbeat: `u_root` passes `[u_present 4000 2000 33 8]`, eight 2000 ms ticks, 16 seconds, plus enumeration.

- [ ] **10. Hot-swap — Volca absent at load**
  - **Need:** The Volca interface still unplugged from the last step. Page 3. Slider 1 is the only control bound to the Volca.
  - **Do:** Load Cut It again from the Organelle menu, with the Volca interface still unplugged, and let it boot. Plug the Volca interface in, wait up to 30 seconds, then hold a Volca key and sweep slider 1.
  - **Pass if:** Holding a Volca key and sweeping slider 1 changes the sound — by ear. Sweep it up — slider 1 is velocity.
  - **Note:** Absent at load is the likelier case in a room: nothing is wrong as far as the instrument knows, so nothing warns, and the heartbeat recovers it (item 285).
