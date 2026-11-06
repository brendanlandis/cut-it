# MIDI checklist

The page-dependent map and the Volca, its one output device. `map-assert` proves the lookup and the allowlist guard, and `volca-assert` what the Volca is sent; what is left is a real fader under a real finger, and a Volca you can hear. There is no Volca checklist: it lives here. The SP-404's steps went with it when it left the rig (2026-11-04).

Hot-swap for the Volca, which is `none`: it transmits nothing and can never be polled, so `u_present`'s re-wire heartbeat is what brings it back (9 and 10).

**Before you start:**

- Knob 1 saved at 57 BPM: step 1 reads it back from `knobs.txt`.

10 steps. How to read one, and how to send a **Send** line: [the checklists' README](README.md). Why each thing behaves as it does: [map](../../ref/module/map.md), [volca](../../ref/device/volca.md).

- [ ] **1. Restored tempo at boot**
  - **Pass if:** The phone's tempo reads 57 and not 120. The bright lamp, if any, is wherever you left it — note which one it is.
  - **Note:** Rig only: 57 comes from `knobs.txt`, which no Mac has.

- [ ] **2. Get to the drum page**
  - **Do:** Press the top button of the Launchpad's left column so it is bright.
  - **Pass if:** The drum page comes up. Nothing below works until it does.

- [ ] **3. A step pad on the drum page**
  - **Do:** Press the top left pad, then press it again.
  - **Pass if:** It lights at the first press and goes back at the second. The OLED shows nothing for it.

- [ ] **4. The same pad on the performance page**
  - **Do:** Press the bright button, for the performance page, then press the top left pad, with nothing in play.
  - **Pass if:** Nothing happens — no change is the pass. Nothing is in play for that column, and only a mapped control names itself (Brendan, 2026-11-04).

- [ ] **5. Back on the drum page**
  - **Do:** Press the top button of the left column again.
  - **Pass if:** The drum page comes back, with the step as step 3 left it. Press it once more if it's lit, to leave it as it was.

- [ ] **6. Tempo from knob 1**
  - **Do:** Sweep knob 1 all the way and back.
  - **Pass if:** Until the knob crosses the restored value the row reads bpm 57 with the knob's own tempo in brackets, and the phone's tempo stays 57. From there the row's one number and the phone's tempo follow the knob over 40 to 250 BPM.

- [ ] **7. Transport from PLAY and STOP**
  - **Do:** Press PLAY on the nanoKONTROL, then STOP.
  - **Pass if:** The aux LED goes green on PLAY and dark blue on STOP.
  - **Note:** The aux LED is the readout: nothing on the OLED shows the transport.

- [ ] **8. Panic is unbound**
  - **Do:** Press every transport key on the nanoKONTROL and every button on the Organelle. Turn the encoder. Nothing should ever go red.
  - **Pass if:** The aux LED never turns red however many controls you press.
  - **Note:** That no map row names panic is `map-assert`'s, read from `cut-it-map.txt`; this asks only what fingers can answer — that no control anyone reaches for raises it.

- [ ] **9. Hot-swap — Volca unplugged and plugged back in**
  - **Need:** Row 3's voice on the Volca, its page on show, so the nanoKEY plays it.
  - **Do:** Unplug the Volca interface alone and count to fifteen, then plug it back in and wait up to 30 seconds before playing a key on the nanoKEY. Then unplug it again: the next step loads without it.
  - **Pass if:** The Volca plays the nanoKEY's key — by ear.
  - **Note:** The oracle is the nanoKEY sounding it, never the Volca sounding: it plays from its own keys with no MIDI connected at all ([volca](../../ref/device/volca.md)). The Volca alone, because it registers `none` and comes back through `u_present`'s re-wire heartbeat (`wire-watch.sh` every eight ticks, re-wiring when the client names change); pulling a second device would go through the loss path instead (item 275). 30 seconds covers the heartbeat: `u_root` passes `[u_present 4000 2000 33 8]`, eight 2000 ms ticks, 16 seconds, plus enumeration.

- [ ] **10. Hot-swap — Volca absent at load**
  - **Need:** The Volca interface still unplugged from the last step.
  - **Do:** Load Cut It again from the Organelle menu, with the Volca interface still unplugged, and let it boot. Plug the Volca interface in, wait up to 30 seconds, press row 3's left button, then play a key on the nanoKEY.
  - **Pass if:** The Volca plays the nanoKEY's key — by ear.
  - **Note:** Absent at load is the likelier case in a room: nothing is wrong as far as the instrument knows, so nothing warns, and the heartbeat recovers it (item 285).
