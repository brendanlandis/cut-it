# Cut It — Pre-Flight Tests

Things to verify on the hardware **before** starting UI/UX design or the patch rewrite.
Ordered by what would force a redesign if it fails.

Most of this needs scratch patches only — no Cut It code. Diagnostic patches live in
[tools/](tools/). Companion to [ref-hardware.md](ref-hardware.md), which explains *why* each of these
matters.

**Status:** Sessions 2, 3b, 3c, 4, 4b and 4c complete. Session 1 done bar the full-load power check.
Session 3 blocked on the TRS Y-cable; Session 5 not attempted.

⚠️ **Item numbers are unique across the whole file and other documents cite them by bare number**
("item 21c", "item 31"). Sessions 4 and 5 were renumbered to 40–42 and 43–46 to remove a collision
with Session 3c's 15–22; items 11, 21, 21c, 23 and 31 were left alone because they are cited
elsewhere. **Never reuse a number** — add at the end, or suffix (`21b`, `21c`).

**The two tests that could have forced a redesign have both passed:** Pd can drive the
Launchpad's Programmer Mode over SysEx (LEDs, velocity, polyphonic aftertouch), and Pd's
per-device channel offsets work with multiple controllers at once. What remains is
cable-blocked — the audio topology and full-rig power draw.

**Do not treat open items as settled facts.** [ref-hardware.md](ref-hardware.md) has an
*Open questions* section, [ref-midi.md](ref-midi.md) has its own, and this file is the
ordered checklist with results. The [tools/](tools/) patches are working references for every
technique verified here.

---

## Session 1 — Does the plumbing exist?

- [x] **1. Organelle's Pd version.** ✅ **Pd 0.49.0**, compiled Oct 9 2018. Device reports OS
      4.0 — the release that took Organelle 1 from Pd 0.46 to 0.49.
- [x] **2. Can you edit Pd's startup flags?** ✅ **Yes — `/root/.pdsettings`**, since mother
      passes no `-noprefs` and no MIDI flags. Edited to `midiapi: 1` plus four in/out device
      entries, verified surviving a cold boot under mother; backed up in [device/](device/).
      The launch line and the read-only-rootfs procedure are in
      [ref-hardware.md](ref-hardware.md).
- [x] **3. Channel offsets confirmed in Pd**, not just at the ALSA layer. ✅ Launchpad on 1–16,
      nanoKONTROL on 17, SP-404 on 33 — the last two confirmed **simultaneously**, in distinct
      blocks, so one `[route]` on the channel outlet separates devices. Full map in
      [ref-midi.md](ref-midi.md). Required getting Pd onto ALSA MIDI first — see *MIDI: OSS
      vs ALSA* in [ref-hardware.md](ref-hardware.md). Not yet done: all four at once.
- [x] **4. Can the patch wire its own MIDI connections at load time?** ✅ **Yes, via `[shell]`**
      — necessary because mother's `alsaconnect.sh` connects only *one* device. Verified from a
      cold Pd launch with nothing pre-connected. The pattern is
      `[loadbang] → [del 1500] → [sh /tmp/wire.sh( → [shell]`, with the `aconnect` calls in a
      **shell script** rather than a message box, which sidesteps Pd's quoting rules entirely.
      Reference: `tools/self-wire.pd` + `tools/wire.sh`. Two load-bearing constraints: connect
      **by name**, never by client number, and **delay it** past `loadbang`.
- [ ] **5. Watch for brownouts** with the full rig connected. Never yet tested with three
      controllers plus the wifi dongle simultaneously — only ever two at a time, because of
      the cable shortage. A marginal hub shows up as dropouts rather than an obvious failure.

---

## Session 2 — Can Pd drive the Launchpad? ✅ PASSED

**This was the critical session** — if SysEx out from Pd had been troublesome, the
Launchpad-as-display concept would have collapsed. It works.

- [x] **6. Send the Programmer Mode SysEx from Pd.** ✅ Sent by Pd itself via `[midiout]`.
      Programmer Mode is on **port 0** (`hw:3,0,0`, seq `28:0`); ports 1 and 2 carry nothing in
      either direction.
- [x] **7. Receive pad presses.** ✅ `r*10+c` confirmed in position, both digits 1–8, so
      `div 10` / `mod 10` gives coordinates directly. Velocity is real — soft presses register
      as low as 10.
- [x] **8. Light a pad.** ✅ 64 pads individually addressable. Velocity indexes a **128-entry
      colour palette, not brightness**; arbitrary colour needs per-pad RGB SysEx — see
      `tools/lp-flicker.pd`.
- [x] **8b. Flashing and pulsing.** ✅ All three lighting modes work, animated by the device
      itself — no `[metro]` needed in Pd. Static / flashing / pulsing are MIDI channels
      **1 / 2 / 3**. See `tools/lp-modes.pd`.
- [x] **9. Read pressure.** ✅ Polyphonic aftertouch, per-pad, simultaneous — two held pads
      reported independent values. **Requires enabling on the device:** hold `Setup`, press the
      **third Track Select button**, choose *Polyphonic Aftertouch*; the default is Channel
      Pressure, one value for the whole surface. Programmer Mode locks out the Setup menu, so
      exit to Live first. An *Aftertouch Threshold* on that page is worth tuning.
- [x] **10. Return to Live mode.** ✅ Verified. Essential escape hatch — entering Programmer
      Mode by SysEx locks out the Settings menu until you send it.

Every byte sequence, palette detail and gotcha found here is catalogued in
[ref-midi.md](ref-midi.md) under *Novation Launchpad Pro MK3*.

---

## Session 3 — Audio topology

**Item 11 passed.** ⬜ Items 12 and 13 remain blocked on the TRS Y-cable (1× 1/4" TRS →
2× 1/4" TS). Needs no USB at all.

**The source side is not in question** — the 404 has discrete L and R jacks. The Y-cable is
required because of the constraint at the *other* end: the Organelle has a single TRS input
jack, and nothing else merges two mono outs into it.

- [x] **11. TRS input → two independent channels.** ✅ **PASSED.** Measured with
      `tools/audio-probe/`, a passive bass through an ordinary mono TS cable:

      | Condition | `adc~ 1` (tip) | `adc~ 2` (ring) |
      |---|---|---|
      | Cable unplugged | 18–19 | 18–19 |
      | Plugged, strings muted | mid-20s | 18–19 |
      | Playing | **90s** | **18–19** |

      The ring never leaves the noise floor while the tip swings ~70 dB. **The channels are
      independent and `adc~ 1` is the tip** — the assumption the whole drums/fx split rests on.

      **Two numbers that everything downstream uses:** the **noise floor is ~18–19** on `env~`'s
      0–100 scale (≈ −82 dBFS), which puts a sensible gate at **25–30**; and a **passive bass
      reaches the 90s**, so gain and headroom are ample. **Re-confirmed through the v0.2 patch**
      in Phase 1 — both channels report 18–19 at rest in the real signal path.
- [ ] **12. 404 pan split.** Pan one sample MONO Left and another MONO Right; confirm they
      arrive on separate Organelle inputs. Tests the 404's *internal* per-sample routing, which
      discrete output jacks do not guarantee.
- [ ] **13. Mic bleed test.** Mic into MIC/GUITAR IN, play a sample panned hard left, listen
      to the **L output alone**. Expected: the mic is audible there too (it sums to both). If
      it isn't, the accepted bleed compromise is unnecessary and the design gets simpler.

      **This is the one that could still change the design** — it is about how the 404 places
      *external input* in the stereo field, which is internal routing and unrelated to the jacks
      on the back.

See [ref-hardware.md](ref-hardware.md) open question 1 for the fuller version, including the
LINE IN R-only variant.

---

## Session 3b — USB topology ✅ CLOSED

- [x] **13a. Launchpad configures at all.** ✅ **Plugged directly.** Behind three chained hubs
      it enumerated and then failed with `can't set config #1, error -32`, so no ALSA client
      was created. Straight into the Organelle it configures immediately. The hub chain was the
      whole problem.
- [x] **13b. Why booting with the Launchpad wedges the UI.** ✅ **ROOT-CAUSED — not power, not
      the hub.** The Launchpad exposes a 192 KiB write-protected vfat volume; `mount.sh` picks
      the last `/dev/sd*` and mounts it on `/usbdrive`, `getDefaultUserDir()` then returns
      `/usbdrive`, and `wifi_control.py` dies trying to open a log for writing there. Full
      chain in [ref-hardware.md](ref-hardware.md).
- [x] **13c. Programmer Mode through the real patch.** ✅ `u_init` wires and initialises it at
      boot with no manual steps; captured pads read `r*10+c` with live velocity 5–127.
- [x] **13d. `mount.sh` guard applied.** ✅ Installed on the device; factory version kept at
      `/root/fw_dir/scripts/mount.sh.orig` and in [device/](device/). A full `/reload` with the
      Launchpad attached now mounts nothing and leaves `USER_DIR` as `/sdcard`.
- [x] **13e. Cold boot with the Launchpad attached.** ✅ Boots normally, wifi connects,
      `/usbdrive` stays unmounted — `/dev/sda1` is present with `ro=1`, so `mount.sh` saw the
      volume and declined it.

---

## Session 3c — Display arbiter and error bus (Phase 3)

Everything here except item 20 was run **headless in Pd 0.49 on the Mac** against the real
`main-dev.pd`, by tapping `oscOut` with `[print]` and driving the buses from a throwaway patch.
No hardware needed, and it is repeatable in seconds — the pattern is worth reusing for Phase 4.

- [x] **15. Cold start says something.** ✅ Before any bus traffic the home screen draws
      `L 0` / `R 0` and `cut-it v0.2`. Without the defaults every line would be text-less, and
      `pd text-out` correctly refuses those — a blank screen indistinguishable from a dead patch.
- [x] **16. Boot stages are modals.** ✅ `booting` → `wiring` → `launchpad` at 16px, then
      `modal-off` hands over to the meters with `v0.2-ready` in the footer.
- [x] **17. Parameter readout, and no stale unit.** ✅ `chop-size 43 %` draws with typetag
      `iiiiiss`; `grain 12` sent 200 ms later draws `iiiiis` with **no inherited `%`**, and
      decayed back to home 12 frames after the *second* message — the TTL follows the last
      message, not the first.
- [x] **18. Priority and restore.** ✅ A modal outranks a parameter fired underneath it; an
      alert preempts the modal; when the alert's TTL expires **the modal is still there**; then
      `modal-off` returns to home.
- [x] **19. The mode filter.** ✅ `warn` reaches the screen in compose. After `perform` the same
      warning is printed by `u_err` but never drawn, while `fail` still draws; returning to
      compose restores it. The bus is unfiltered; only the screen is filtered.
- [x] **20. Rate limiting and the trailing edge.** ✅ 877 `disp` messages in five seconds
      produced exactly **51 frames**, the drawn value advancing by 20 each frame. No coalescing
      logic exists — layers hold state, so the last value written is what the next frame draws.
- [x] **20b. The modal safety TTL.** ✅ A modal set and never cleared gives up after 30 s and
      the meters return — insurance against a lost `modal-off` covering the display forever on
      a console-less device. Confirmed on hardware by item 21c.
- [x] **21. Deployed, and the throughput question is answered.** ✅ Measured on the running
      device over SSH without disturbing the patch: all seven shipped files md5-identical to
      local, `pd` at **8.2 % CPU** and load 0.16, **110 UDP datagrams/second**, socket to
      `127.0.0.1:4001` established.

      **110/s is the proof it is Phase 3 and that it keeps up** — the home frame is 10 OSC
      messages at 10 Hz where Phase 1 drew 6, so anything under ~100 would mean the old display
      or dropped frames. **And it clears the phase's biggest unknown:** `packOSC` drops a
      mismatched typetag *before* `udpsend`, so a bad tag would show up as a missing datagram.
      The full rate means the **runtime typetag builder produces tags the real `packOSC`
      accepts** — which the Mac could never demonstrate, having no `packOSC` at all.
- [x] **21b. The OLED draws it.** ✅ Home shows both meters hovering at **17–21** against a
      measured noise floor of 18–19, so the scaling is right, with the gate-zone `gBox` marks
      under the silence range of each bar and `v0.2-ready` in the footer. That closes the whole
      home-and-modal path on hardware: text, `gFillArea` bars, `gBox` marks, the footer, the
      modal layer and `gFlip` all render correctly through the real `packOSC`.
- [x] **21c. Every layer, on the device.** ✅ **All fourteen steps of `tools/phase3-bench.pd`
      passed on hardware** — param with and without a unit, the modal outranking a parameter,
      an alert preempting the modal and the modal surviving underneath, `warn` suppressed in
      perform while `fail` still draws, the filter releasing on compose, `modal-off`, and the
      30 s safety timeout clearing a stuck modal unaided.

      **Phase 3 is verified end to end on the Organelle.**

      ⚠️ **The first run found a bug in the bench, not the patch.** Steps 07, 08 and 10 read as
      failures because step 04 set the modal at t=36 s, the safety TTL is **30 s**, and steps
      are 10 s apart — so it expired exactly as step 07 fired. Only the expected *background*
      was wrong. **Every step now re-asserts the modal.** The general lesson: a timed test
      against a layer that expires must re-assert its own preconditions.
- [x] **22. Does the ALERT buffer work?** ✅ **Yes — writable, displayable, and reversible.**
      `tools/alert-buffer-probe.pd` drew into buffer 4 while `g_oled` kept redrawing screen 3
      underneath, `setscreen 4` showed it, and `setscreen 3` brought the live meters back after
      the six-second dwell. **That closes the last ⬜ in the OLED section.**

      **It is still not adopted, deliberately** — see [ref-display.md](ref-display.md). Writable
      is not the same as safe: buffer switching is edge-triggered where every `g_oled` layer is
      state-driven, so a lost `setscreen 3` strands the display on a stale alert with no console
      to say so, whereas a dropped frame today self-corrects in 100 ms. And there is nothing to
      optimise — an alert is a 2–4 s event at ~70 msg/s against a home screen that sustains the
      same rate continuously.

      *By-product:* the probe's own second line was 24 characters and **clipped at 21**,
      re-confirming the 8px font limit and that `gPrintln` truncates rather than wrapping. The
      probe now says `buffer-4-works`.

---

## Session 4 — nanoKONTROL

- [x] **40. Plug it in and print the CCs.** ✅ Class compliant, enumerates as ALSA card 4,
      arrives on Pd channel 17.
- [x] **41. Korg Kontrol Editor — runs, and the nano is configured.** ✅ **Use version 2.4.0**,
      not the current release: Korg's 2.5.0 removed support for the first-generation
      nanoKONTROL, and 2.4.0 is the last version that sees it. It runs on macOS 26; get it from
      the *"previous versions"* section of the
      [KORG KONTROL EDITOR download page](https://www.korg.com/us/support/download/software/1/133/1355/).
      Don't go below 2.0.9 — earlier releases predate Catalina's 64-bit requirement.

      The full CC map is written to the device and catalogued in [ref-midi.md](ref-midi.md).
      All buttons are **momentary**, so Pd owns all toggle state, and **no LED Mode setting
      exists** on the mk1 — all visible state must live on the Launchpad.
- [x] **42. Transport buttons reassigned off the factory map.** ✅ Six buttons moved to
      **CC 41–46**, in physical order, on the nano's **channel 2** — arriving as **Pd channel
      18** while the control groups stay on 17.

      ⚠️ **They were reassigned as a mode control and are no longer used that way.** Phase 4 settled
      that the row is better spent on scene selection, so all six now get ordinary momentary-CC
      treatment and `m_nano` reads both channels through one path. The CC numbers and the channel
      below are unchanged and still correct — see item 38b and
      [ref-build-log.md](ref-build-log.md).

      **Verified by decoding the raw stream off the wire**, not just trusting the editor: all
      six in order with no gaps, momentary 127/0 throughout, control groups on 17, full 0–127
      range with *Upper Value* unclipped, and **no SysEx anywhere in the stream** — nothing
      emits MMC. Reasoning in [ref-midi.md](ref-midi.md).

      The factory assignment was overwritten before it was ever read, so what these buttons
      shipped with is now unknown. ✅ The scene file — device-resident state that REC + STOP +
      SCENE at power-on wipes — is backed up in [device/](device/).

---

## Session 4b — Phase 4 groundwork, measured on the Mac

Everything here was run headless against the real `main-dev.pd` with the real nanoKONTROL
attached, or against the local Pd 0.49-1 binary. **No Organelle needed**, and repeatable in
seconds — the pattern Session 3c established.

- [x] **23. `[ctlin]`'s outlet firing order.** ✅ **Channel, then controller, then value** —
      right to left, as the convention says, but *measured* because this repo has been bitten
      here before (`polytouchin` emits note before value). Proof: `tools/midi-monitor.pd` packs
      all three and is triggered by the **value**, and the very first event of a session printed
      `CC: 1 1 1` — correct controller *and* channel. That cannot happen unless both were already
      stored. **So `m_nano`'s cold stores are safe by measurement, not by hope.**
- [x] **24. What channel the nano actually reports on, and why the answer moved.** ✅ **The
      channel block follows Pd's INPUT SLOT, not the device's position in the system MIDI list.**
      `pd -listdev` first showed the nano as system device 1, then as device 2 once a Scarlett
      18i8 was plugged in — but opening it with `-midiindev 2` still put it on **channel 1**,
      because it was Pd's *first opened* input. Slot *n* carries channels `(n-1)*16+1` upward.

      **Consequence:** `main-dev.pd` passes **1** and `main.pd` passes **17**, and what a
      Mac-side change of hardware alters is only *which system device you pick* to fill Pd input
      slot 1 — not the channel. An earlier reading of this as "the Scarlett changes the channel to
      17" was wrong and is recorded here so it is not re-derived.
- [x] **25. The CC map, re-confirmed through the real patch.** ✅ Slider 1 → CC 1, slider 9 →
      CC 9, knob 1 → CC 11, top-row button → CC 23, bottom-row button → CC 36, all on channel 1;
      PLAY → CC 42 and LOOP → CC 44 on channel 2. Every button momentary **127 then 0**. Matches
      [ref-midi.md](ref-midi.md) exactly.
- [x] **26. A creation argument on `[u_root]` reaches through.** ✅ `m_nano`'s load-time print
      reported `17` from `main.pd` and `1` from `main-dev.pd`. That closes the "creation args
      reaching u_root" risk — the argument is in the patch, not on Pd's command line, so
      `mother.pd` loading `main.pd` *by name* changes nothing.

      ⚠️ **And it found a trap worth keeping.** The print at `loadbang` **broke `deploy.sh`**,
      which gates on *output* rather than exit status. The print now sits behind `[del 2000]`:
      the check quits at load and never sees it, while the by-hand SSH console — the only place
      it is useful — still gets it. **Any new `[print]` in a deployed abstraction needs the same
      treatment.**
- [x] **27. The `text` objects the multi-parameter display and the error log depend on.** ✅ All ten `text`
      methods are present in the local Pd 0.49-1 binary, and three behaviours were measured
      rather than assumed:

      | Behaviour | Result |
      |---|---|
      | `text set` at a line past the end | **appends at the end** — line 5 of a 2-line text gives 3 lines, not 6 |
      | `text search <name> 0` | line number on a match, **`-1`** when absent |
      | `write -c <file>` | plain **newline**-terminated, space-separated fields. Without `-c` Pd writes its own semicolon format and `grep`/`tail`/`awk` stop being useful |
      | `text set` / `text search` fed a non-list | **`no method for '<atom>'`** — a message whose first atom is a symbol arrives as a *selector*, so `[list append]` first. Same family as the three `route` traps |
      | `text write` on success | **silent**. On failure it prints `<path>: write failed` to stdout, so a dead SD card stays visible in the by-hand console |
- [x] **28. `makefilename` accepts `set`.** ✅ `[makefilename slider-%d]` sent `set knob-%d` then
      `7` gives `knob-7`. Measured because the pattern is a creation argument and switching it at
      runtime is not obviously supported in 0.49. *(`m_nano` ended up not needing it — routing a
      packed `<kind> <which>` list gives each kind its own `makefilename` and no ordering to get
      wrong — but the capability is confirmed for whenever a pattern must change.)*
- [x] **29. The error log, end to end on the Mac.** ✅ Driven through the real `u_err` with the
      write path pointed at a scratch file:

      - the **200-line cap holds exactly** — 210 errors in one `[until]` burst left 200 lines
      - lines read `<ms> <level> <source> <text>`, and the stamps matched the delays that
        produced them exactly: `500 warn m_test early-warn`, `700 fail m_test late-fail`
      - the 2 s dirty-flag flush fires
      - **`quitting` forces a final flush** — the file appeared at 1.3 s, long before the metro's
        first tick at 5 s. That is the case that matters, since mother gives the patch 100 ms and
        the error you most want is the one just before it went
      - the unconditional `[print err]` still fires for every error, whatever the mode
- [x] **30. `status` replaces `boot`, verified through `oscOut` rather than by grep.** ✅ The
      footer drew `v0.2-ready` from `u_init`, then `v0-9-test` pushed onto the bus. And a now-stale
      `boot stale-name` fell through to the **param** layer as name `boot`, value `0` — the
      documented "a mistyped `disp` name becomes a visible nonsense parameter rather than
      vanishing", plus a concrete demonstration of why `disp` values must be floats:
      `makefilename %g` refused the symbol and emitted `0`.

- [x] **31. `m_nano`'s decode, all 21 branches, with no hardware in the loop.** ✅ `[ctlin]` was
      swapped for `nano-testin` — a three-outlet stand-in driven by `nano-ch`, `nano-cc`,
      `nano-val` **in that order**, which is ctlin's measured order made explicit. Because the
      firing order is established separately (item 23), this tests the whole decode
      deterministically and repeatably:

      | Case | Result |
      |---|---|
      | slider 1 / 9, knob 1 / 9 (CC 1, 9, 11, 19) | `slider-1 64`, `slider-9 100`, `knob-1 5`, `knob-9 127` — **the CC 9 → CC 11 boundary is right** |
      | top / bottom buttons (CC 21, 29, 31, 39) | `btn-t-1 1`, `btn-t-9 1`, `btn-b-1 1`, `btn-b-9 1` |
      | any button RELEASE (value 0) | **silence** |
      | CC 45 on the control channel | `warn m_nano cc-45-unmapped` and **no parameter** |
      | CC 45 again | still no parameter — the flags really are cleared, so no stale name leaks |
      | a foreign channel (5) | **complete silence** |
      | PLAY / STOP | `xport-play 1` + a bang on `start`; `xport-stop 1` + a bang on `stop` |
      | LOOP, twice | `perform` then `compose`, on **both** `mode` and the footer |
      | REW / FF / REC | their own names, nothing else |
      | CC 47 on the transport channel | `warn m_nano cc-47-unmapped` |

      ⚠️ **This run found a real bug that reading the patch had not.** The transport's unmapped
      warning reported **`cc-7-unmapped` instead of `cc-47`**: `[select 1 2 3 4 5 6]`'s reject
      outlet emits the float it did *not* match — `cc − 40` — and that float landed on `[f]`'s
      **hot** inlet, overwriting the stored CC rather than reading it out. Fixed with a `[t b]`.
      The control side was already correct because its reject goes through `[t b b b]` first.
      **The lesson generalises: a reject outlet carries a value, not a bang, and any `[f]` behind
      one needs a trigger in front of it.**
- [x] **32. `text get`'s field semantics — the one that shapes the multi-parameter display.** ✅ Measured:

      | Form | Behaviour |
      |---|---|
      | `text get <name>` | the whole line |
      | `text get <name> 0 1` | field 0 only |
      | `text get <name> 1 3` on a line with only 2 fields | ⚠️ **`error: text get: field request (1 3) out of range`**, and it prints |

      **So the display cannot use a fixed field request**, because a parameter with no unit has one
      field fewer than one with a unit. The draw path fetches the whole line and strips the
      frame stamp with `[list split 1]` instead — always safe here, since every stored line has at
      least three atoms and `list split` only fails to fire its right outlet when the list is
      *exactly* the split length.

**One environment note that is not a test result:** `organelle.local` resolves from Brendan's
terminal but not from the agent's sandboxed shell, which has to use `HOST=root@192.168.1.15`.
`deploy.sh` needs no change.

---

## Session 4c — Phase 4 on the Organelle

Deployed with `./deploy.sh`. The nanoKONTROL was plugged into the **Mac** during this session, so
the on-device controller sweep is still outstanding; everything that does not need it passed.

- [x] **33. `[shell]` runs `logroll.sh`, and its return path works.** ✅ The by-hand console showed
      `errlog-roll: logroll: carried 0 line(s) from the previous session`. So `[shell]` **does**
      hand stdout back as a usable message — previously ⬜. The design deliberately does not depend
      on it, but the wall clock does come from `date` inside the script, which is what removed that
      dependency.
- [x] **34. A creation argument survives `mother.pd` loading `main.pd` by name.** ✅
      `m_nano-control-channel: 17` on the device, `1` on the Mac.
- [x] **35. The error log survives a patch reload — the whole point of step 0.** ✅ Two sessions
      driven by hand, each raising three errors, with a `killall pd` between them:

      ```
      BOOT 2026-07-30 05:01:29        <- deploy
      BOOT 2026-07-30 05:02:28        <- session 1
      2000 warn m_test session-mark
      2600 fail m_test disk-check
      3200 warn m_test third-line
      BOOT 2026-07-30 05:02:51        <- session 2
      ```

      Session 1's errors are in the durable log under **their own** `BOOT` line, and session 2's are
      still in `.cur`. **Under a plain `[text write]` design session 1 would have been erased by
      session 2's first flush** — a patch reload is the case that breaks it, and it is far more
      common than a power cycle.
- [x] **36. `tools/fetch-errors.sh` end to end.** ✅ Reported pd's uptime, confirmed all deployed
      files md5-identical to the repo, pulled both files with mtimes, and printed counts by level
      and source before the detail, newest session first and correctly grouped.

      ⚠️ **It found its own bug: `pgrep pd` matches substrings.** On this device that hits a kernel
      thread (pid 48), so the script cheerfully reported "pd running, up 01:47:20" while pd was in
      fact killed. Fixed with `pgrep -nx pd`. Verified: `pgrep pd` → `48`, `pgrep -x pd` → empty.
- [x] **37. The deployed patch is healthy with the rewritten display.** ✅ **117 UDP
      datagrams/second** at **5.3 % CPU**, load 0.31, socket established to `127.0.0.1:4001` — in
      line with the 110/s item 21 measured for the home frame, so the display rewrite costs nothing
      noticeable and the real `packOSC` still accepts every typetag the runtime builder produces.

### Still outstanding on hardware

- [x] **38. The nanoKONTROL on the device**, where it is Pd input slot 2 and the channel is **17**.
      ✅ **The transport row was read on the hardware and is correct** — pressing a transport key
      displays its own name and a `1`, exactly like every other button, with no toggle and no footer
      change. That is the change Phase 4 finished on, and it works through the real `[ctlin]` at
      channel 17.

      ⬜ **The remaining 36 controls have not been swept on the device.** Low risk rather than
      untested: all 21 decode branches were verified exhaustively off-device with a `[ctlin]`
      stand-in (item 31), and the only thing the device adds is the channel offset, which the
      transport keys just exercised. Steps 15–17 of `tools/phase4-bench.pd` remain written for it —
      worth doing opportunistically, not worth blocking on. If a control is silent, check
      `aconnect -l` before suspecting the patch.
- [x] **38b. Everything re-run after the two changes from reading it on hardware.** ✅ The
      transport row folded into the ordinary button path, and the display switched from
      most-recently-used ordering to rows that hold their positions:

      | Check | Result |
      |---|---|
      | transport keys | `xport-1`…`xport-6` on press, nothing on release, **no `mode` / `start` / `stop` traffic at all** |
      | CC ≥ 50 in the block | still `warn m_nano cc-<n>-unmapped` |
      | CC 41–49 | now a *name* (`xport-1`…`xport-9`) rather than a warning — the decode is CC-number-based within the block |
      | CC 0 | `slider-0` — there is no bounds check on the units digit, and never was |
      | two controls alternating | the first-touched **holds row 0** across every alternation. This was the whole complaint |
      | five controls | rows in first-touched order, stable |
      | a sixth control | **refused**, rows unchanged, nothing shifts |
      | ageing | the survivor grows back to the 24px layout |
      | Phase 3 regression | all layers, priorities, both alert TTLs (20 and 40 frames) and the mode filter unchanged |

      ⚠️ **A third instance of the same bug shape.** `moses`'s LEFT outlet carries the value it did
      not match — the `-1` that `text search` returns for an unseen name — and `text size` passes a
      float straight through, so `-1` arrived at `text set` as a line number:
      `error: text set: line number (-1) < 0`, seventeen times in one run. Fixed with a `[t b]`.
      **The rule is now three-for-three: a reject, left or non-matching outlet carries DATA, and
      anything behind one that expects a bang needs a trigger in front of it.**

      *(The 4 `write failed` lines in a Mac regression run are `/sdcard` not existing there. That is
      the documented diagnostic working, and it cannot affect `deploy.sh`, whose check quits at load
      before the flush metro fires.)*
- [ ] **39. The OLED read by eye** — the three type-size layouts and the ageing. The geometry is
      verified through `oscOut` on the Mac, but "is 16px actually readable at arm's length" is a
      judgement only the hardware can settle. The one-mover 24px layout has now been read on the
      device incidentally, via item 38's transport presses; the 2-mover and 3–5-mover layouts have
      not.

---

## Session 4d — the aux button LED ✅ PASSED

Run for Phase 5, which needed a transport indicator. **The answer was better than expected.**

- [x] **47. What `[s led]` accepts, and what the eight states look like.** ✅ Read off the device,
      then swept by eye:

      | Finding | |
      |---|---|
      | `[s led]` takes one number; `mother.pd` applies `[% 8]` | eight states, any float legal |
      | It reaches `SerialMCU::setLED(unsigned)` — the front-panel MCU, same serial link as the OLED | ✅ |
      | Patch-facing 0–7 → **off, red, yellow, green, cyan, dark blue, pink, white** | ✅ by eye |
      | `mother.pd` **permutes** patch-facing → hardware: `0,4,5,1,3,2,6,7` | ✅ |
      | The hardware value is a **3-bit RGB bitmask** — bit 0 green, bit 1 blue, bit 2 red | ✅ derived and consistent with all eight readings |
      | mother sets **`led 0` on `quitting`** already | ✅ safe exit needs nothing |
      | An undocumented **`/led/flash`** exists in the binary and is **not** exposed through `mother.pd` | ✅ |

      **So the Organelle has a full RGB LED, not an indicator lamp** — seven colours plus off, and the
      only state display in the rig that is not a screen. Recorded in
      [ref-display.md](ref-display.md).

      The permutation is the interesting part: mother is reordering an RGB bitmask into spectrum order
      so patch authors get `red → yellow → green → cyan → blue → magenta → white` rather than a bit
      pattern. **Design against the patch-facing numbers**; the bitmask only matters if you ever want
      to compose a colour from components, and that needs the raw `oscOut` path.

      Re-run the sweep with:

      ```sh
      ssh root@organelle.local 'for r in 0 4 5 1 3 2 6 7; do
        oscsend localhost 4001 /led i $r; echo "raw $r"; sleep 5; done
        oscsend localhost 4001 /led i 0'
      ```

### The procedure, in order

**Do every Mac step first, with the nano still on the Mac. Then move the cable once.**

**Mac, one-time setup.** ⚠️ This Mac's Pd has **no MIDI input saved in its preferences**, so
`[ctlin]` gets nothing until you set one: Pd 0.49 → *Media → MIDI Settings* → **Input Device 1 =
nanoKONTROL SLIDER/KNOB** → OK. Pick the nano *by name*: with an interface attached it is not
device 1 in the system list. What matters is that it is Pd's **input slot 1**, which is what makes
the channel 1 and matches `[u_root 1]`.

**Mac, static.** `python3 tools/pd-layout-check.py "Cut It"/*.pd tools/phase4-bench.pd` — every
line must say `0 problems`. Then the syntax check on both entry points; **silence is the pass**,
and any output at all is what `deploy.sh` would refuse on.

**Mac, boot.** Open `Cut It/main-dev.pd`. Expect `booting` → `wiring` → `launchpad` → the two
meters with `v0.2-ready` in the footer, and **`m_nano-control-channel: 1` in the Pd console about
two seconds in**. That print is the whole point of the `[del 2000]`: it is the one direct
confirmation the channel argument is right, and a wrong one otherwise looks exactly like a dead
controller.

**Mac, the sweep.** Items 1–5 of *Verification* in the Phase 4 plan. The dev panel's eight rows
show whatever is drawn, so names are readable there.

**Mac, the error log.** The dev panel's `warn` and `fail` bench buttons raise real errors. To read
the accumulated log, navigate **main-dev.pd → u_root → u_err → pd logfile** and click
`open-error-log`. ⚠️ **Do not open `u_err.pd` as a file** — that is a different instance with its
own `$0` and its log is empty. On the Mac `[shell]` is stubbed, so no file is written and only the
in-memory view works; that is expected and is why the log exists for the *device*.

**Then move the nano to the Organelle**, plugged in directly rather than through a hub, and
`./deploy.sh`. Confirm the wiring before suspecting the patch:
`ssh root@organelle.local 'aconnect -l | grep -A1 nanoKONTROL'` should show a connection to
`Pure Data` port 1. The channel is now **17**, and `main.pd` already passes it.

**Device, the log across a power cycle** — the only real test of step 0. Clear the test data first
(`./tools/fetch-errors.sh --clear`), raise errors with `tools/phase4-bench.pd`, **power-cycle**,
select the patch from the menu, then `./tools/fetch-errors.sh`. Both sessions must appear, each
under its own `BOOT` line. Selecting from the menu rather than a `deploy.sh` load also keeps
`/tmp/curpatchname` correct, which matters for Phase 8.

---

## Session 5 — Organelle as its own access point

⬜ **Not attempted.** Gates whether the PdParty status display is stage-worthy or
development-only. Everything else about the phone link is already verified — see
[ref-display.md](ref-display.md).

**Why it matters:** the display currently rides the house wifi. In a venue that is either
absent, congested, or full of other people's phones. An Organelle-hosted AP with one client a
metre away removes the venue from the equation entirely.

**What's already known:** `hostapd` and `dnsmasq` are installed, `wlan0` exists, and `iw list`
reports **AP** among supported interface modes. ✅ The dongle is a Ralink RT5370, a
well-supported hostapd chipset.

- [ ] **43. Bring up an AP on `wlan0` and join it from the iPhone.** Confirm the phone gets an
      address from `dnsmasq` and the status display still updates.
- [ ] **44. Check it in airplane mode** — cellular off, wifi manually re-enabled.
- [ ] **45. Judge the link quality.** Watch the heartbeat for gaps over a few minutes. This is
      the actual question: is it steady enough to trust mid-set?
- [ ] **46. Decide whether it survives a reboot** — and whether you *want* it to. Persisting it
      means the Organelle no longer joins the house network, which costs the `scp`/`ssh`
      workflow.

### Read this before starting

**Bringing up an AP on `wlan0` disconnects the Organelle from the network — including SSH.**
There is no console on this device, so a bad configuration could mean HDMI and a keyboard to
recover.

**Mitigation: persist nothing.** Run `hostapd` and `dnsmasq` from `/tmp`, never
`remount-rw.sh`, and a power cycle restores normal client wifi. Under those conditions the
worst case is a reboot.

Because SSH drops the moment the AP comes up, the test has to run **unattended from a script**
— start the AP, hold it for a fixed period, then exit — rather than interactively.

**A second wifi dongle would remove the risk entirely** (client on one, AP on the other) at the
cost of a USB port and some hub current. Worth considering if this turns into a fight.

---

## Deliberately skipped for now

Not unimportant — just not blocking UI/UX decisions.

| Deferred | Why it can wait |
|---|---|
| LINE IN R-only behaviour | An upgrade path, not a requirement |
| Ground loops | Deal with hum if and when you hear it |
| 404 round-trip latency | Perform-time tuning; needs a working patch first |
| CPU headroom | Not a real risk at this scale |

---

## What's actually left

1. **Session 3** — audio topology, once the Y-cable arrives. Items 11–13. The only remaining
   test that could still force a redesign.
2. **Item 5** — power under full load. Never tested with three controllers plus the wifi
   dongle at once, because of the cable shortage.
3. **Session 5** — Organelle as an access point. Doesn't block the v0.2 build; does block
   trusting the phone display on stage.
4. **Items 38 and 39** — the rest of the nano sweep and the OLED type sizes read by eye. Both are
   opportunistic; neither blocks Phase 5.

Everything else in Sessions 1, 2, 4 and 4d has passed. The full MIDI picture — every message each
device accepts and transmits — is catalogued in [ref-midi.md](ref-midi.md), which also
carries the remaining message-level unknowns, chief among them the **SP-404 pad note range**
(verified 47+*n* here, but Roland's chart says 35–51 — sweep all 16 pads before writing
sequencing code against it).
