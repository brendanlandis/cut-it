# MIDI checklist

The mode-dependent map, both output devices, and the SP-404 in both directions. `sp404-assert` proves all sixteen pads, the rate limiter and the allowlist guard, and `map-assert` the lookup; what is left is a real pad under a real finger, and a Volca you can hear. There is no SP-404 checklist and no Volca checklist: both live here.

Hot-swap for both output devices, which differ: the SP-404 is `active` and can be declared lost (14 to 16); the Volca is `none`, transmits nothing and can never be polled, so `u_present`'s re-wire heartbeat is what brings it back (17 and 18).

**Before you start:**

- Knob 1 saved at 57 BPM: step 1 reads it back from `knobs.txt`.

18 steps. How to read one, and how to send a **Send** line: [the checklists' README](README.md). Why each thing behaves as it does: [map](../../ref/module/map.md), [sp404](../../ref/device/sp404.md), [volca](../../ref/device/volca.md).

- [ ] **1. Restored tempo at boot**
  - **Pass if:** The footer reads 57 BPM and not 120 BPM. The lit mode lamp is wherever you left it — note which one it is.
  - **Note:** Rig only: 57 comes from `knobs.txt`, which no Mac has.

- [ ] **2. Get to mode 1**
  - **Do:** Press the top button of the Launchpad left column — the top mode lamp.
  - **Pass if:** The lit lamp moves to the top position. Nothing below works until it does.

- [ ] **3. SP-404 pad 1**
  - **Do:** Check which bank the 404 is lit on — it lights only the selected one — then select bank A and press pad 1.
  - **Pass if:** The OLED shows one row for the pad — sp-a1 with the velocity beside it. No sp-pad or sp-bank row appears.

- [ ] **4. SP-404 pad 5**
  - **Do:** Check the 404 is lit on bank A — it lights only the selected one — then press pad 5.
  - **Pass if:** A row reads sp-a5 with the velocity beside it. Anything else is the failure.
  - **Note:** Pad 5 catches `47 + n`: the old formula draws sp-a13, which looks plausible on an OLED.

- [ ] **5. All sixteen pads**
  - **Do:** Press pads 1 through 16 in order on bank A, about two a second.
  - **Pass if:** Each pad draws a row named for itself as you press it — sp-a1 then sp-a2 up to sp-a16. A run that goes sp-a1 to sp-a4 and then jumps is the failure.
  - **Note:** About two a second: each pad is a new name, and the param layer holds five and refuses a sixth until one ages out, about 1.3 seconds after it last moved.

- [ ] **6. Bank B**
  - **Do:** Select bank B and press pad 1. The 404 lights only the bank it is on.
  - **Pass if:** The row reads sp-b1 — the same pad on bank B has a name of its own.
  - **Note:** sp-b1 proves the bank; step 4 owns the pad decode.

- [ ] **7. One row for a press and its release**
  - **Do:** Press and hold any pad and let go. One hit only.
  - **Pass if:** One row named for the pad — sp-b3 for bank b pad 3 — shows the velocity on the press and 0 on the release. It is the same row both times and no sp-pad or sp-bank row appears.
  - **Note:** Exactly two sp- rows: `u_map`'s on the press and again at velocity 0 on the release (items 283, 317). Four means `m_404`'s sp-pad and sp-bank rows are back; one means the release never arrived.

- [ ] **8. Fader 1 in mode 1**
  - **Need:** The Volca audible. It transmits nothing so this step and the two after it are judged by ear with no readback of any kind.
  - **Do:** In mode 1 move fader 1 on the nanoKONTROL.
  - **Pass if:** The Volca tone changes as you move it. The OLED shows one row for the fader — volca-cc41 and the value — and no slider-1 row.

- [ ] **9. Fader 1 in mode 4**
  - **Do:** Press the fourth button down the Launchpad left column then move fader 1.
  - **Pass if:** The Volca does not change — no change is the pass. The OLED shows slider-1 and its raw value because nothing maps it in mode 4 and that is correct.

- [ ] **10. Fader 1 back in mode 1**
  - **Do:** Press the top button of the Launchpad left column then move fader 1 again.
  - **Pass if:** The Volca responds again. Still silent means the mode did not change back — check the lit lamp.

- [ ] **11. Tempo from knob 1**
  - **Do:** Sweep knob 1 all the way and back.
  - **Pass if:** The footer BPM follows the knob over roughly 10 to 500 BPM once the knob has crossed the restored value. Nothing at all happens before it crosses.

- [ ] **12. Transport from PLAY and STOP**
  - **Do:** Press PLAY on the nanoKONTROL, then STOP.
  - **Pass if:** The aux LED goes green on PLAY and dark blue on STOP.
  - **Note:** No footer claim: the pad rows from the steps above raise the param layer over it. The aux LED is the readout.

- [ ] **13. Panic is unbound**
  - **Do:** Press every transport key on the nanoKONTROL and every button on the Organelle. Turn the encoder. Nothing should ever go red.
  - **Pass if:** The aux LED never turns red however many controls you press.
  - **Note:** That no map row names panic is `map-assert`'s, read from `cut-it-map.txt`; this asks only what fingers can answer — that no control anyone reaches for raises it.

- [ ] **14. Hot-swap — SP-404 unplugged**
  - **Do:** Unplug the SP-404 and watch the OLED. The alert arrives about eight seconds after the cable is out and clears itself about two seconds later. Leave it unplugged: the next step loads without it.
  - **Pass if:** A bordered alert on the OLED reads warn then m_404 then device-lost.
  - **Note:** The alert is three missed presence ticks behind the unplug. Left out on purpose: plugged back in, step 15 would load with the device present and test nothing.

- [ ] **15. Hot-swap — SP-404 absent at load**
  - **Need:** The SP-404 still unplugged from the last step.
  - **Do:** Load Cut It again from the Organelle menu, with the SP-404 still unplugged, and let it boot. Plug it back in, wait 60 seconds, then press pad 1 on bank A.
  - **Pass if:** The OLED shows a row for the pad — sp-a1.
  - **Note:** A pad is the oracle: the 404's silence at boot proves detection, but silence cannot tell a working subscription from a dead one.

- [ ] **16. Hot-swap — SP-404 unplugged and plugged back in**
  - **Do:** Unplug the SP-404 and count to fifteen, then plug it back in and wait up to 60 seconds before pressing pad 1 on bank A.
  - **Pass if:** The OLED shows a row for the pad again — sp-a1.

- [ ] **17. Hot-swap — Volca unplugged and plugged back in**
  - **Need:** Mode 1. Slider 1 is the only control bound to the Volca.
  - **Do:** Unplug the Volca interface alone and count to fifteen, then plug it back in and wait up to 30 seconds before sweeping slider 1 while holding a Volca key. Then unplug it again: the next step loads without it.
  - **Pass if:** Holding a Volca key and sweeping slider 1 changes the sound — by ear.
  - **Note:** The oracle is the fader changing the sound, never the Volca sounding: it plays from its own keys with no MIDI connected at all ([volca](../../ref/device/volca.md)). The Volca alone, because it registers `none` and comes back through `u_present`'s re-wire heartbeat (`wire-watch.sh` every eight ticks, re-wiring when the client names change); pulling a second device would go through the loss path instead (item 275). 30 seconds covers the heartbeat: `u_root` passes `[u_present 4000 2000 33 8]`, eight 2000 ms ticks, 16 seconds, plus enumeration.

- [ ] **18. Hot-swap — Volca absent at load**
  - **Need:** The Volca interface still unplugged from the last step. Mode 1. Slider 1 is the only control bound to the Volca.
  - **Do:** Load Cut It again from the Organelle menu, with the Volca interface still unplugged, and let it boot. Plug the Volca interface in, wait up to 30 seconds, then hold a Volca key and sweep slider 1.
  - **Pass if:** Holding a Volca key and sweeping slider 1 changes the sound — by ear. Sweep it up — slider 1 is velocity.
  - **Note:** Absent at load is the likelier case in a room: nothing is wrong as far as the instrument knows, so nothing warns, and the heartbeat recovers it (item 285).
