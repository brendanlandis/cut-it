# Launchpad checklist

The grid, the grid arbiter's layers and their timeouts, the mode lamps, the beat row, the ring map, hot-swap, panic keeping the surface, and a tap on SETUP. `display-assert` and `launchpad-assert` prove the bytes the patch sends; this is what the surface shows.

Steps 22 to 24 are the three hot-swap cases, as on the [nanoKONTROL](nanokontrol.md). Every step sets up its own preconditions, a mode among them.

28 steps. How to read one, and how to send a **Send** line: [the checklists' README](README.md). Why each thing behaves as it does: [launchpad](../../ref/device/launchpad.md), [display](../../ref/module/display.md), [presence](../../ref/module/presence.md).

- [ ] **1. Resting grid**
  - **Send:** `tempo 120; stop bang; mode mode-1`
  - **Pass if:** The left column shows one bright green lamp at the top and seven dim ones below it. The bottom row of pads has a single white pad. Dim means faint and not off. The white pad is already walking and that is correct — a frozen pad is the failure. Above the bottom row's first pad sits the tap pad, dim yellow. Everything else on the surface is dark.
  - **Note:** Page 1, not 2: page 2 is the drum page, where the beat row gives way. The tap pad is page 1's own; that it taps the tempo is the phone checklist's.

- [ ] **2. Mode lamp 4**
  - **Send:** `mode mode-4`
  - **Pass if:** The bright lamp moves to the fourth position down and the other seven go dim, and the tap pad goes dark. Nothing else on the grid changes.

- [ ] **3. Mode lamp 3**
  - **Send:** `mode mode-3`
  - **Pass if:** The bright lamp lands on the third position.

- [ ] **4. Mode lamp 7**
  - **Send:** `mode mode-7`
  - **Pass if:** The bright lamp lands on the seventh position and the other seven go dim.

- [ ] **5. Mode lamp 8**
  - **Send:** `mode mode-8`
  - **Pass if:** The bright lamp lands on the eighth and last position, the bottom of the left column, just above SETUP.

- [ ] **6. Pressing a mode lamp selects it**
  - **Do:** Press the third button down the left column, then the first.
  - **Pass if:** The bright lamp moves to the pad you pressed and stays there after you let go. The OLED does not change.
  - **Note:** Steps 2 to 5 judge the painting, off the mode bus; this one judges the selection, off the lamp itself. That the release selects nothing is `map-assert`'s, since a doubled selection looks identical.

- [ ] **7. Grid vocabulary stays off the OLED**
  - **Send:** `disp grid no-such-thing`
  - **Pass if:** Nothing happens on either surface. In particular no parameter row called grid appears on the OLED.

- [ ] **8. Modal claims the surface**
  - **Send:** `disp grid modal 45`
  - **Pass if:** Every pad and every ring button turns blue including the left column. The mode lamps are covered too. The OLED must not change.

- [ ] **9. Mode change under a modal**
  - **Send:** `disp grid modal 45; mode mode-3`
  - **Pass if:** Nothing happens. The surface stays blue. The mode really does change underneath and you will see it two steps from now.

- [ ] **10. Alert over a modal**
  - **Send:** `disp grid modal 45; err fail u_bench stacked`
  - **Pass if:** The surface turns red for about two seconds and then goes back to blue — not to the mode lamps.

- [ ] **11. Clearing the modal**
  - **Send:** `disp grid modal 45; disp grid modal-off`
  - **Pass if:** The grid returns to mode lamps and the beat row. The bright lamp is now the third one — the change made while the modal covered it.

- [ ] **12. A fail takes the surface**
  - **Send:** `err fail u_bench boom`
  - **Pass if:** The whole surface turns red and then goes back to the mode lamps by itself after about two seconds. A grid that stays red is the failure.

- [ ] **13. A warn does not**
  - **Send:** `err warn u_bench quiet`
  - **Pass if:** Nothing happens on the grid and the OLED does show the warning.

- [ ] **14. Modal safety timeout**
  - **Send:** `disp grid modal 21`
  - **Do:** Watch the grid for thirty seconds without touching anything.
  - **Pass if:** The surface turns green and then clears itself about thirty seconds later.

- [ ] **15. Start the transport**
  - **Send:** `disp grid modal-off; start bang`
  - **Pass if:** The white pad walks along the bottom row twice a second and the aux LED goes green.
  - **Note:** `grid modal-off` is this step's own precondition: step 14 paints the surface green and only its 30-second timeout clears it.

- [ ] **16. Beat row wrapping**
  - **Do:** Watch one wrap go by.
  - **Pass if:** The white pad reaches the eighth pad and the next beat is back to the first — with no gap and no stray light anywhere else.

- [ ] **17. Beat row at 240 BPM**
  - **Send:** `tempo 240`
  - **Pass if:** The white pad moves twice as fast and keeps an even step. A visible swing is the failure.
  - **Note:** No swing to excuse: the frame clock runs at 50 Hz ([display](../../ref/module/display.md)). The rate is `tempo-assert`'s.

- [ ] **18. Back to 120 and stopped**
  - **Send:** `tempo 120; stop bang`
  - **Pass if:** The beat row goes back to two a second at once and the pad keeps walking after the stop. The change is a snap and not a slide.
  - **Note:** A snap: the row follows `c_clock`, and a new tempo takes effect on the next tick. Only a device chasing an external clock slides.

- [ ] **19. Pads and releases**
  - **Send:** `mode mode-1`
  - **Do:** Press pads and release them, all but the tap pad. Press harder on one you are holding.
  - **Pass if:** Nothing appears on the OLED for any of them, pressed, released or pressed harder, with aftertouch on or off.
  - **Note:** Only a control the map binds names itself (Brendan, 2026-11-04), and on page 1 only the tap pad is bound, which flashes rather than drawing. Which pad is which shows on the drum page, where a step lights where it is pressed (the sequencer checklist); pressure arrives as `pad-NN-at` and no row binds it (item 318).

- [ ] **20. Ring buttons**
  - **Do:** Press the ring buttons, including the top left corner and the bottom row. Leave SETUP, the bottom left corner, for step 28.
  - **Pass if:** No ring button draws a row on the OLED. The top left corner raises panic and the left column's eight move the mode lamp; the others do nothing. SETUP stays dark.
  - **Note:** Only a control the map binds names itself, and these bound ones are buttons, which draw nothing: CC 90 is `recover` and the eight mode keys are `u_map`'s own route (Brendan, 2026-11-04; item 317). The top row and the bottom row are free.

- [ ] **21. The left column changes mode**
  - **Do:** Press each of the eight buttons of the left column, top to bottom. Then press the top row.
  - **Pass if:** Each of the eight buttons moves the bright lamp to its own position. The top row moves nothing.

- [ ] **22. Hot-swap — unplugged mid-session**
  - **Send:** `mode mode-1`
  - **Do:** Unplug the Launchpad USB and leave it out.
  - **Pass if:** A bordered alert on the OLED reads warn and then m_launchpad. The grid goes dark.
  - **Note:** The alert is up to 8 seconds behind the unplug, at the shipped 2000 ms presence tick. Page 1 rather than 2, so the reload in step 23 restores a page with a beat row.

- [ ] **23. Hot-swap — absent at load**
  - **Need:** The Launchpad still unplugged from the last step.
  - **Do:** Load Cut It again from the Organelle menu, with the Launchpad still unplugged, and let it boot. Plug the Launchpad back in and wait up to 60 seconds without touching anything.
  - **Pass if:** The grid ends up lit with one bright lamp in the left column. Only where it settles is the test — what the Launchpad does on the way back is its own. The beat row runs at the tempo restored from knobs.txt rather than the one the earlier steps set.
  - **Note:** 60 seconds: a replug often misses the first re-wires while the device enumerates — the Launchpad once used six of its eight, spread over seventy seconds (item 277). Under about 50 seconds fails intermittently on correct code.

- [ ] **24. Hot-swap — unplugged and plugged back in**
  - **Do:** Unplug the Launchpad USB and count to fifteen, then plug it back in and wait up to 60 seconds without touching anything.
  - **Pass if:** The grid lights again and the left column shows one bright lamp.
  - **Note:** A lit grid is the oracle: the surface paints only while `m_launchpad` owns it and the device is in Programmer Mode, so it proves the re-wire and the mode both came back (item 276).

- [ ] **25. Panic keeps the surface**
  - **Send:** `panic bang`
  - **Pass if:** The grid keeps painting and the Launchpad stays in Programmer Mode. Its own display does not come back.
  - **Note:** Panic keeps the surface (item 250): handing it back left the grid dead until a reload, and Live Mode's clock flooded Midi-In 1. `display-assert` asserts the same.

- [ ] **26. The grid still answers after a panic**
  - **Send:** `mode mode-2`
  - **Pass if:** The bright lamp moves to the second position and the drum page comes up — the panic silenced notes and did not surrender the surface.
  - **Note:** Page 2, where a press shows on the grid itself: no pad names itself on the OLED (Brendan, 2026-11-04).

- [ ] **27. Pads still reach the instrument after a panic**
  - **Do:** Press the first step pad, top left, then press it again.
  - **Pass if:** It lights at the first press and goes dark at the second.

- [ ] **28. A tap on SETUP flips test mode**
  - **Need:** Test mode off, as every load leaves it and no step before this one changes it. If in doubt, load Cut It again.
  - **Do:** Tap SETUP, the bottom left corner, once, and watch the OLED for ten seconds. Tap it again. Then hold it for four seconds and let go.
  - **Pass if:** The first tap puts up a bordered alert reading warn then u_net then test-mode-on for about two seconds, and no other alert appears in the ten seconds after it. The second tap and the hold put up no alert. SETUP stays dark and the grid keeps painting throughout.
  - **Note:** The second tap turns test mode off, which is logged and not drawn; the hold sends nothing at all ([launchpad](../../ref/device/launchpad.md)). An alert every few seconds with no tap means the announcement each Programmer Mode heartbeat makes is being read as a tap: `launchpad-assert` proves it is not on the Mac, and this is the rig's wiring and timing.
