# Launchpad checklist

The grid, the grid arbiter's layers and their timeouts, the voices' lamps, the ring map, hot-swap, panic keeping the surface, and a tap on SETUP. `display-assert` and `launchpad-assert` prove the bytes the patch sends; this is what the surface shows.

Steps 22 to 24 are the three hot-swap cases, as on the [nanoKONTROL](nanokontrol.md). Every step sets up its own preconditions, a page among them. The rows are a song's voices: with nothing saved, the seed's, row 1 the drums, row 2 harmony, row 3 melody.

28 steps. How to read one, and how to send a **Send** line: [the checklists' README](README.md). Why each thing behaves as it does: [launchpad](../../ref/device/launchpad.md), [display](../../ref/module/display.md), [presence](../../ref/module/presence.md).

- [ ] **1. Resting grid**
  - **Need:** No left or right button bright: press a bright one, and it goes back to the performance page.
  - **Send:** `tempo 120; stop bang`
  - **Pass if:** The top three rows' two buttons each are dim, in three colors, pink, cyan and amber, a color a row, the same on both columns. The rest of the two columns is dark. Dim means faint and not off. Nothing on the grid is lit but what the top row and the performance page's controls in play show.

- [ ] **2. A voice's left button**
  - **Do:** Press the top button of the left column.
  - **Pass if:** It goes bright pink, and the drum page comes up on the grid. The rest of the lamps stay dim. The OLED does not change.

- [ ] **3. Another voice's**
  - **Do:** Press the second button down the left column.
  - **Pass if:** It goes bright cyan and the first goes dim. The grid is the harmony page: its top row's chords in cyan.

- [ ] **4. A voice's right button**
  - **Do:** Press the second button down the right column.
  - **Pass if:** It goes bright cyan, and the left button across from it dim. The grid goes dark but for the lamps and the edges: its setup is the phone's.

- [ ] **5. An unused row**
  - **Do:** Press the fifth button down the left column. Then the fifth down the right column.
  - **Pass if:** The left one does nothing. The right one starts a voice: both light, violet, the right bright. Save and revert light: the song has changed.

- [ ] **6. The lit button again**
  - **Do:** Press the bright button.
  - **Pass if:** It goes dim, and the grid goes back to the performance page. Revert, the lowest row's rightmost, takes the new voice back: press it on another page if you want it gone, since on the performance page that row is the nanoKONTROL's.
  - **Note:** That a release selects nothing is `voices-assert`'s, since a doubled selection would undo itself.

- [ ] **7. Grid vocabulary stays off the OLED**
  - **Send:** `disp grid no-such-thing`
  - **Pass if:** Nothing happens on either surface. In particular no parameter row called grid appears on the OLED.

- [ ] **8. Modal claims the surface**
  - **Send:** `disp grid modal 45`
  - **Pass if:** Every pad and every ring button turns blue including both columns. The OLED must not change.

- [ ] **9. A page change under a modal**
  - **Send:** `disp grid modal 45; mode drums`
  - **Pass if:** Nothing happens. The surface stays blue. The page really does change underneath and you will see it two steps from now.

- [ ] **10. Alert over a modal**
  - **Send:** `disp grid modal 45; err fail u_bench stacked`
  - **Pass if:** The surface turns red for about two seconds and then goes back to blue — not to the page.

- [ ] **11. Clearing the modal**
  - **Send:** `disp grid modal 45; disp grid modal-off`
  - **Pass if:** The grid returns, showing the drum page — the change made while the modal covered it.

- [ ] **12. A fail takes the surface**
  - **Send:** `err fail u_bench boom`
  - **Pass if:** The whole surface turns red and then goes back to the drum page by itself after about two seconds. A grid that stays red is the failure.

- [ ] **13. A warn does not**
  - **Send:** `err warn u_bench quiet`
  - **Pass if:** Nothing happens on the grid and the OLED does show the warning.

- [ ] **14. Modal safety timeout**
  - **Send:** `disp grid modal 21`
  - **Do:** Watch the grid for thirty seconds without touching anything.
  - **Pass if:** The surface turns green and then clears itself about thirty seconds later.

- [ ] **15. PLAY brings up the performance page**
  - **Send:** `disp grid modal-off`
  - **Do:** Press the top button of the left column so it is bright, then PLAY on the nanoKONTROL.
  - **Pass if:** The aux LED goes green. The bright button goes dim, and the grid goes to the performance page by itself.
  - **Note:** `grid modal-off` is this step's own precondition: step 14 paints the surface green and only its 30-second timeout clears it.

- [ ] **16. The saved tempo's pad is no PLAY**
  - **Need:** Playing, as step 15 left it.
  - **Do:** Press the top button of the left column. Press and let go of the pad under the fourth repeat pad, the second row of the right four by four, its far right.
  - **Pass if:** The drums restart at once, and the drum page stays up: the pad brightens while held and goes back to dim blue.

- [ ] **17. The playhead at 240 BPM**
  - **Send:** `tempo 240`
  - **Pass if:** The green pad moves twice as fast and keeps an even step. A visible swing is the failure.
  - **Note:** No swing to excuse: the frame clock runs at 50 Hz ([display](../../ref/module/display.md)). The rate is `tempo-assert`'s.

- [ ] **18. Back to 120 and stopped**
  - **Send:** `tempo 120; stop bang`
  - **Pass if:** The aux LED goes dark blue and the green pad goes.

- [ ] **19. Pads and releases**
  - **Need:** The performance page, with nothing in play.
  - **Do:** Press pads and release them. Press harder on one you are holding.
  - **Pass if:** Nothing appears on the OLED for any of them, pressed, released or pressed harder, with aftertouch on or off.
  - **Note:** Only a control the map binds names itself (Brendan, 2026-11-04), and a pad on this page is a column of what's in play, here nothing. Which pad is which shows on the drum page, where a step lights where it is pressed (the sequencer checklist); pressure arrives as `pad-NN-at` and no row binds it (item 318).

- [ ] **20. Ring buttons**
  - **Do:** Press the ring buttons, including the top left corner and the bottom row. Leave SETUP, the bottom left corner, for step 28.
  - **Pass if:** No ring button draws a row on the OLED. The top left corner raises panic, the two columns move the page, and the top row plays sections. SETUP stays dark.
  - **Note:** Only a control the map binds names itself, and these bound ones are buttons, which draw nothing: CC 90 is `recover`, and the columns `u_voices`' (item 317).

- [ ] **21. Every row of the left column**
  - **Do:** Press each of the eight buttons of the left column, top to bottom. Then press the top row.
  - **Pass if:** A button with a voice brightens its own lamp and changes the page. One with none does nothing. The top row moves nothing here.

- [ ] **22. Hot-swap — unplugged mid-session**
  - **Do:** Unplug the Launchpad USB and leave it out.
  - **Pass if:** A bordered alert on the OLED reads warn and then m_launchpad. The grid goes dark.
  - **Note:** The alert is up to 8 seconds behind the unplug, at the shipped 2000 ms presence tick.

- [ ] **23. Hot-swap — absent at load**
  - **Need:** The Launchpad still unplugged from the last step.
  - **Do:** Load Cut It again from the Organelle menu, with the Launchpad still unplugged, and let it boot. Plug the Launchpad back in and wait up to 60 seconds without touching anything.
  - **Pass if:** The grid ends up lit, with the voices' lamps on both columns. Only where it settles is the test — what the Launchpad does on the way back is its own. The phone's tempo reads the tempo restored from knobs.txt rather than the one the earlier steps set.
  - **Note:** 60 seconds: a replug often misses the first re-wires while the device enumerates — the Launchpad once used six of its eight, spread over seventy seconds (item 277). Under about 50 seconds fails intermittently on correct code.

- [ ] **24. Hot-swap — unplugged and plugged back in**
  - **Do:** Unplug the Launchpad USB and count to fifteen, then plug it back in and wait up to 60 seconds without touching anything.
  - **Pass if:** The grid lights again and the columns show the voices' lamps.
  - **Note:** A lit grid is the oracle: the surface paints only while `m_launchpad` owns it and the device is in Programmer Mode, so it proves the re-wire and the mode both came back (item 276).

- [ ] **25. Panic keeps the surface**
  - **Send:** `panic bang`
  - **Pass if:** The grid keeps painting and the Launchpad stays in Programmer Mode. Its own display does not come back.
  - **Note:** Panic keeps the surface (item 250): handing it back left the grid dead until a reload, and Live Mode's clock flooded Midi-In 1. `display-assert` asserts the same.

- [ ] **26. The grid still answers after a panic**
  - **Send:** `mode drums`
  - **Pass if:** The drum page comes up — the panic silenced notes and did not surrender the surface.
  - **Note:** The drum page, where a press shows on the grid itself: no pad names itself on the OLED (Brendan, 2026-11-04).

- [ ] **27. Pads still reach the instrument after a panic**
  - **Do:** Press the first step pad, top left, then press it again.
  - **Pass if:** It lights at the first press and goes dark at the second.

- [ ] **28. A tap on SETUP opens the diagnostics**
  - **Need:** Test mode off, as every load leaves it and no step before this one changes it. If in doubt, load Cut It again.
  - **Do:** Tap SETUP, the bottom left corner, once, and watch the OLED for ten seconds. Press the top row's second pad. Press it again. Tap SETUP. Then hold it for four seconds and let go.
  - **Pass if:** The tap brings up the diagnostics page: the top row's first two pads lit, green and blue, and every lamp dim, and no alert appears in the ten seconds after it. The second pad puts up a bordered alert reading warn then u_net then test-mode-on for about two seconds; pressed again, no alert. The next tap goes back to the page before, and the hold puts up nothing. SETUP stays dark and the grid keeps painting throughout.
  - **Note:** The second press turns test mode off, which is logged and not drawn; the hold sends nothing at all ([launchpad](../../ref/device/launchpad.md)). An alert every few seconds with no tap means the announcement each Programmer Mode heartbeat makes is being read as a tap: `launchpad-assert` proves it is not on the Mac, and this is the rig's wiring and timing.
