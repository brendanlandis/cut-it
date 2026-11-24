# Phone checklist

Every **Pass if** here describes the phone, not the Organelle, unless it says otherwise. The phone shows the Launchpad's current page and controls it, and leaves the OLED's alerts and rows to the OLED (Brendan, 2026-11-04): step 3 is the one whose correct result is that nothing happens on the phone, and step 10 the one where nothing happens to the tempo.

The rate limit and what `u_net` takes are `phone-assert`'s: what is left is the link, and the pages under a finger. Steps 1 to 11 are the pages and the link; steps 12 to 14 are Setup and test mode; steps 15 and 16 the drum screen; step 17 the phone blocking the app. Send their lines from the Mac with `tools/send.sh`.

17 steps. How to read one, and how to send a **Send** line: [the checklists' README](README.md). Why each thing behaves as it does: [phone](../../ref/device/phone.md), [tempo](../../ref/module/tempo.md).

- [ ] **1. The link is up, on the performance page**
  - **Need:** The Cut It app open on the phone, on the same network. A red no link bar along the top here means nothing below can be judged.
  - **Do:** If a voice's page is on show, press its lit button on the Launchpad again.
  - **Pass if:** No red no link bar tops the page. The phone shows the performance page: along the top the song's name, the section playing, the tempo and take into play; under them eight strips, each a knob, a fader and two buttons. Down each side runs a column of eight buttons, the Launchpad's, each voice's in its color and a row with none dark, and under the left one songs. Nothing sits close to the notch.

- [ ] **2. The phone and the Launchpad turn each other's page**
  - **Need:** The performance page, and a voice on row 1.
  - **Do:** Press the Launchpad's top left-column button, then its top right-column button. Press aux on the Organelle, then aux again. Press the top right-column button again. Then tap the top button of the phone's left column, and tap it again. Then tap songs, under the phone's left column, and tap it again.
  - **Pass if:** At each press the phone turns at once: row 1's voice's page, its left button lit in the voice's color; its setup page, with its name, machine and patch along the top, the right button lit; the songs page; the setup page again; the performance page. The phone's two taps turn the Launchpad the same way: row 1's page, then the performance page. Songs opens the songs page, the button going white with the aux LED, and closes it, back to the performance page.

- [ ] **3. The OLED's rows and alerts stay on the OLED**
  - **Need:** The performance page.
  - **Send:** `disp chop-size 43 %; err warn u_bench probe-warning`
  - **Pass if:** The OLED shows the chop-size row and a bordered warn box; nothing on the phone changes at all, its tempo included.
  - **Note:** The phone was the OLED's mirror until 2026-11-04; that it reads nothing on `disp` now is `phone-assert`'s.

- [ ] **4. The tempo, from knob 1**
  - **Need:** The performance page. With nothing Saved knob 1 is held at 120 until turned through about 11 o'clock, where its line puts 120; turn it through first.
  - **Do:** Turn knob 1 slowly from about 9 o'clock to 3 o'clock, then quickly back.
  - **Pass if:** The tempo at the top of the phone's page follows the knob, about 80 to 210 over that turn, and settles on the same number as the OLED's bpm row when the knob stops.

- [ ] **5. The tempo, set on the phone**
  - **Do:** Press aux on the Organelle, the songs page. Tap the plus beside tempo five times, then the minus eight times.
  - **Pass if:** The tempo moves one BPM a tap, up five and down past where it started, and the OLED shows nothing of it.
  - **Note:** Knob 1 is held at the phone's tempo afterwards, as knob 2 is at the phone's last step: its next turn reads bpm and the phone's tempo with its own in brackets, and moves nothing until turned through it ([tempo](../../ref/module/tempo.md)).

- [ ] **6. The global last step, and knob 2**
  - **Need:** The songs page, as step 5 left it, the drums playing, from the sequencer checklist's steps or `start bang`.
  - **Do:** Tap the minus beside last step from 16 down to 8. Then press aux, closing the songs page, press the drums' left-column button, and turn knob 2 a little either way.
  - **Pass if:** last step reads 8, and on the drum page the green pad walks steps 1 to 8 with the steps past them dark. Knob 2's first turn reads last-step 8 with the knob's own step in brackets on the OLED, and changes nothing until it is turned through 8, after which the phone follows it.

- [ ] **7. The swing**
  - **Need:** The drums playing.
  - **Do:** Press aux, the songs page, and tap the plus beside swing up to 66. Listen for a bar.
  - **Pass if:** At 66 every second sixteenth comes late, a long-short shuffle. Put it back to 50 before going on.

- [ ] **8. The tap button**
  - **Need:** The tempo in sight on the phone, on the songs page or the performance page.
  - **Do:** Tap the nanoKONTROL's LOOP four times, evenly, about two a second.
  - **Pass if:** From the second tap the phone's tempo reads about 120.

- [ ] **9. A pause starts the count over**
  - **Do:** Wait three seconds. Tap LOOP once. Then tap it three times quickly, about three a second.
  - **Pass if:** The single tap after the pause leaves the tempo where it was. The quick taps set it to about 180.

- [ ] **10. A pad on the drum page is a drum**
  - **Do:** Press aux, closing the songs page, then the drums' left-column button, then tap the second row's first pad three times.
  - **Pass if:** It plays its drum each time, and the phone's tempo does not move.

- [ ] **11. Link lost, and back**
  - **Do:** Load Cut It again from the Organelle menu, watching the phone. Touch nothing on the phone.
  - **Pass if:** The phone's red no link bar comes up while Cut It restarts, and goes within a few seconds of it loading, the phone turning to the page on show. Nothing on the Organelle mentions the phone.
  - **Note:** A lost phone is the phone's to report, by its no link, and the Organelle says nothing (Brendan, 2026-11-03): under Pd 0.57 the socket survives a listener going away, so the old `net-link-down` warning could not fire and was taken out ([phone](../../ref/device/phone.md)). Reloading is the rig-side way to silence the heartbeat; closing the app would close the display too.

- [ ] **12. Setup opens the diagnostics page and closes it**
  - **Need:** The performance page.
  - **Do:** Tap Setup, the Launchpad's bottom-left button. Then tap it again.
  - **Pass if:** At the first tap the phone turns at once to the diagnostics page: diagnostics and test mode, and FM voice 1 and 2 under them. At the second it turns back to the performance page, at once.

- [ ] **13. Test mode on, from the diagnostics page**
  - **Do:** Tap Setup, then press the top row's second pad. Wait ten seconds.
  - **Check:** `./tools/fetch-errors.sh` on the Mac.
  - **Pass if:** The phone's diagnostics page gives way at once to the line check, its first step, reading test mode on beside a lit lamp, and stays there. The OLED shows a bordered box reading warn then u_net then test-mode-on for about two seconds. The log's newest u_net line is warn u_net test-mode-on, with no test-mode-off after it.
  - **Note:** One press can reach Cut It twice, 5 ms apart, which once turned test mode on and straight back off; a second flip within 300 ms is dropped (`phone-assert` holds it), and the ten seconds are this step's check that it held.

- [ ] **14. A page ends test mode, and the phone follows it**
  - **Need:** Test mode on, as step 13 left it, the line check up.
  - **Do:** Press the drums' left-column button.
  - **Check:** `./tools/fetch-errors.sh` on the Mac.
  - **Pass if:** The line check gives way at once to the drum screen, and the log's newest u_net line is info u_net test-mode-off.
  - **Note:** That a page turns test mode off is `phone-assert`'s too (Brendan, 2026-11-04: staying on the checklists after a mode press was the weird part).

- [ ] **15. The drum screen's pads under a finger**
  - **Need:** The drum page on the Launchpad, so the phone shows the drum screen.
  - **Do:** Tap each of the tabs over the pads in turn, volume, pitch, last and random, then volume again. Tap a pad that is not lit, then the lit one. Put a finger on a pad and drag up slowly, then down past where you started, then a long quick drag up, and let go. Drag the first pad's volume back to 0.
  - **Pass if:** The tab tapped turns white, its word black, and every pad's number changes at once: dB and semitones with a sign, last steps, randomness. A touch on a pad that is not lit lights it, and the Launchpad selects the same one; a touch on the lit one changes nothing. A slow drag moves the number a step at a time, with no jumps.
  - **Note:** A step is about 5 points of drag for volume, 8 for pitch, 6 for a last step, and 5 for randomness's fives (`phone/CutIt/DrumsView.swift`).

- [ ] **16. The drum screen's effect controls**
  - **Need:** The drum page on the Launchpad, so the phone shows the drum screen.
  - **Do:** Tap each of the effect tabs, distortion, delay and reverb, in turn, then distortion again. Tap a pad, then another, watching the knobs.
  - **Pass if:** The tab tapped turns white. Distortion shows soft, hard, fold and crush over drive, tone and mix; delay shows 1/2 to 1/32 over straight, triplet and dotted, then feedback and level; reverb shows plate, giga and free over send, size and damping. Only the chosen effect's controls show. Selecting another pad turns each knob to that drum's setting, and size, damping and the reverb's type stay put.

- [ ] **17. The phone blocking the app shows, and its taps never arrive late**
  - **Need:** The app open with no red bar, Cut It stopped on the performance page, and a voice on rows 1 and 2.
  - **Do:** In the phone's Settings, Privacy & Security, Local Network, switch Cut It off. Back in the app, tap the top button of the left column and wait for the red bar. In Settings, switch Cut It on again, come back to the app and touch nothing for five seconds, watching the phone and the Launchpad. Then tap the left column's second button.
  - **Pass if:** With the switch off the tap turns no page, and a red not heard bar tops the page within about a second. With it on again and nothing touched, neither the phone nor the Launchpad turns a page: the tap made while blocked never arrives. The last tap turns both to row 2's voice's page, and the bar goes.
  - **Note:** A blocked app still hears the heartbeat, so the bar is not heard and never no link. What a blocked app hands iOS is sent when the block lifts, which is why the app hands it nothing ([phone](../../ref/device/phone.md), *A socket that can't send keeps what it's given*). If taps still do nothing with the switch on, quit the app and open it.
