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

### The two device measurements, with the commands that were missing

Item 21 recorded the numbers and not the method, which is why they were hard to repeat. Both
blocks are copy-paste and neither disturbs the running patch.

**The bench on the device** — as a third patch, with a real console:

```sh
scp tools/phase5-bench.pd root@organelle.local:/tmp/
ssh root@organelle.local
  killall pd; sleep 1
  cd /tmp/patch
  nohup pd -nogui -rt -audiobuf 6 -path /root/Pd/externals \
      -path '/sdcard/Patches/!/Cut It' \
      /root/fw_dir/mother.pd main.pd /tmp/phase5-bench.pd > /tmp/bench.txt 2>&1 &
  tail -f /tmp/bench.txt          # Ctrl-C when step 15 prints
  killall pd
```

⚠️ **The `-path` is not optional here.** The bench's own `declare` is `../Cut\ It`, which resolves
from `tools/` on the Mac but not from `/tmp/` on the device. Without it `c_clock` fails to create
and both its counts read 0 — which looks exactly like a dead clock.

**CPU, load and datagram rate** — `/proc` rather than `top`, so it works on busybox:

```sh
ssh root@organelle.local '
  P=$(pgrep -nx pd)
  col() { awk "/^Udp:/{ if(h==\"\"){h=1; for(i=1;i<=NF;i++) if(\$i==\"OutDatagrams\") c=i; next} print \$c }" /proc/net/snmp; }
  T1=$(awk "{print \$14+\$15}" /proc/$P/stat); C1=$(awk "/^cpu /{print \$2+\$3+\$4+\$5+\$6+\$7+\$8}" /proc/stat); U1=$(col)
  sleep 5
  T2=$(awk "{print \$14+\$15}" /proc/$P/stat); C2=$(awk "/^cpu /{print \$2+\$3+\$4+\$5+\$6+\$7+\$8}" /proc/stat); U2=$(col)
  awk -v a=$T1 -v b=$T2 -v c=$C1 -v d=$C2 "BEGIN{printf \"pd CPU: %.1f %%\n\", 100*(b-a)/(d-c)}"
  echo "UDP out:  $(( (U2-U1)/5 )) datagrams/sec"
  echo "load:     $(cat /proc/loadavg)"
  aconnect -l | grep -c "Connecting To"
'
```

`pgrep -nx pd`, not `pgrep pd` — the substring match hits a kernel thread on this device, which is
the bug item 36 found in `fetch-errors.sh`. Compare against **8.2 % / 110 per second** (item 21)
and **5.3 % / 117** (item 37); Phase 5 adds ~96 MIDI messages a second on top.

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

## Session 6 — Phase 5, clock and transport, measured on the Mac

Everything here was run headless against the real `main-dev.pd` under **real DSP**, with no
Organelle and no MIDI device attached — the pattern Session 4b established. `-noaudio` still
computes the DSP graph, which is what makes a `phasor~`-derived clock testable without a sound
card. Numbers are from `tools/phase5-bench.pd` and two throwaway probe patches.

- [x] **48. The pulse rate, and the beat cut from it.** ✅ `u_tempo`'s `[phasor~]` at BPM ÷ 60 × 24
      with `[threshold~ 0.5 2 0.1 2]`, counting `[mod 24]`:

      | Window | Tempo | Beats | Expected |
      |---|---|---|---|
      | 3 s | 120 | **6** | 6 |
      | 3 s | 60 | **3** | 3 |
      | 10 s | 120 | **20** | 20 |

      So the pulse train is 24 PPQN and the beat is the 24th pulse, measured rather than asserted.
- [x] **49. Two `c_clock` instances at different rates, and their alignment to master.** ✅ Over a
      10.25 s window at 120 BPM: master **21** beats, `[c_clock 1 4]` **21**, `[c_clock 1.5 4]`
      **31**, and **6** bar bangs with `beat-in-bar` cycling 1 2 3 4. That is the poly in
      poly-tempo, working.

      **The alignment number is the one that matters: the worst difference between a master beat
      and the ratio-1 `c_clock` beat over the whole run was `0.000000 ms`** — every pair landed in
      the same logical instant. That is what the `[*~ 24] → [wrap~]` construction buys, and it is
      why a threshold on the beat phasor directly would have been wrong: it would have fired half
      a beat away, uniformly, and looked fine in isolation.
- [x] **50. The clock does not stop when the transport does.** ✅ Counters zeroed, `stop` sent,
      10 s later: **20 / 20 / 30** — identical to the running case. This is the least obvious
      requirement in the phase: stop the pulse stream and the 404 stretches every sample to a
      stale tempo, so a stopped clock is a *wrong* tempo rather than no tempo.
- [x] **51. Out of range clamps, and warns once per distinct value.** ✅ Against a legal range of
      **5–600 BPM**: `5000` `5000` `0` `0` `300` `5000` produced alerts on the **first, third and
      sixth** only. A repeat of the same out-of-range value is silent; a *different* one is not.

      ⚠️ **This is the second version.** The first filtered the out-of-range *verdict* with
      `[change]`, so `5000` warned and a `0` sent straight afterwards did not — the flag had never
      changed, and a second, opposite fault was silent. **Brendan caught it by hand** (procedure
      step 14) after the automated run had passed, because the bench only ever sent one out-of-range
      value. The `[change]` is on the **value** now. See item 57.
- [x] **52. The whole `disp` conversation through a boot and a transport cycle.** ✅ In order:
      `led stopped`, `status 120-bpm`, then `led running` on start, `status 60-bpm` on a tempo
      change, `led stopped` on stop. The LED is told a state and never a colour, and the BPM lands
      in the footer rather than the param layer.
- [x] **52b. ⚠️ A bare `[change]` swallows a control that is parked at zero — found by driving the
      real chain rather than by reading it.** ✅ `knob1 0` → `param og-knob-1 0` → `tempo 60`
      produced **nothing at all** on the first attempt: `[change]` starts life holding 0, so the
      first value never looked like a change. Every knob in `m_organelle` is now `[change -1]`,
      which is what `u_level` has always used and for the same reason. -1 cannot collide, since
      mother's knobs are 0 to 1.

      **The consequence had this stayed:** boot with knob 1 turned fully down and the tempo would
      silently sit at its 120 default instead of 60, until you touched the knob. Verified fixed —
      `og-knob-1 0` → `TEMPO: 60`, `1` → `180`, `0.5` → `120`, and `og-aux 1` alternating
      `START` / `STOP` through the real `u_map`.
- [x] **53. ⚠️ Pd 0.49 does not warn about extra creation arguments — so the `[midiout]` port
      question cannot be answered by the syntax check.** ✅ Measured as a negative: `[loadbang 7]`
      and `[wrap~ 9]` both load in complete silence. A clean check on `[midiout 3]` therefore
      proves nothing at all about whether the 3 reaches anything. `u_tempo` uses `u_init`'s proven
      pattern — the port set into the cold inlet at load — and the question stays ⬜ in
      [plan-v02.md](plan-v02.md). **The lesson is that the obvious experiment was invalid**, which
      is worth more than the answer would have been.
- [x] **54. Both entry points still load clean, and every file passes the layout check.** ✅
      `main.pd` and `main-dev.pd` both silent under the syntax check with the five new
      abstractions instantiated; `pd-layout-check.py` reports `0 problems` on all eleven patch
      files and on the bench.

### Found by testing it by hand, after the automated run had passed

- [x] **57. ⚠️ The out-of-range warning filtered the verdict instead of the value.** ✅ Fixed and
      re-measured — see item 51. **The automated bench could not have found this**, because it only
      ever sent one out-of-range value; it took a person clicking the low button after the high one.
      A bench proves the cases it contains and nothing else.
- [x] **58. ⚠️ THE CLOCK LOST PULSES ABOVE ~430 BPM, and the cause is a Pd detail worth keeping.**
      ✅ **`threshold~` decrements its debounce timer once per DSP *block*, not per millisecond.**
      So *any* non-zero debounce costs a whole 1.45 ms block on every state change, and two of them
      per cycle put a floor of four blocks under the pulse period. Measured with the original
      `[threshold~ 0.5 2 0.1 2]`:

      | Tempo | Beats in 3 s | Expected |
      |---|---|---|
      | 500 | **17** | 25 |
      | 600 | **15** | 30 |

      **With both debounces set to 0** the same test gives **25** and **30**, exactly. A `phasor~`
      is monotonic and cannot bounce, so there was never anything for a debounce to protect against.

      **The real ceiling, measured on a bare `phasor~` with no clamp in the way:** 200 Hz ✅,
      240 Hz ✅, 300 Hz ✅, **344 Hz ✅**, 400 Hz ✗ (579 pulses where 800 were due), 500 Hz ✗. So the
      limit is **two DSP blocks per pulse — 344 Hz, which is 44100 / 64 / 2 to the digit** — or
      **860 BPM**. `u_tempo` clamps at 600, leaving 43 % of headroom.

      ⚠️ **A `c_clock`'s ratio multiplies this**: `ratio × tempo` must stay under ~860 BPM
      equivalent, so at the 600 BPM clamp the highest safe ratio is about 1.4.
- [x] **59. Tempo at both ends of the new range.** ✅ 10 BPM: 2 beats in 12 s. 500 BPM: 25 beats in
      3 s. 600 BPM (the clamp): 30 in 3 s. Anything above 600 pins to 600 and reads 30, which is the
      clamp working rather than a ceiling — it fooled one round of measurement before the bare
      `phasor~` test separated the two.
- [x] **60. The bench resolves `c_clock` on its own.** ✅ `#X declare -path ../Cut\ It` — the escaped
      space survives Pd's parser, verified with a one-object patch first. Opening
      `tools/phase5-bench.pd` straight from Pd's File menu now works; before this it printed
      `c_clock ... couldn't create` and both `c_clock` counts read 0, which looks like a dead clock
      rather than a missing search path. ✅ Also confirmed `#X declare` does **not** occupy an object
      index, so inserting it at the top of a file does not rewire anything.

- [x] **61. ⚠️ A `c_clock` created after startup never ran, because nothing re-publishes the tempo.**
      ✅ `u_tempo` writes 120 to `tempo` exactly once, at load, and afterwards only *stores* what it
      hears — deliberately, so it cannot loop with a bus it also listens to. The consequence was
      invisible until someone opened the bench **after** the patch was already running: both
      `c_clock` counts read **0** while the master read 20. Their `[r tempo]` had simply never fired,
      so the phasor sat at 0 Hz.

      **Fixed inside `c_clock`, not in `u_tempo`** — an instance should be correct whenever it is
      born, and re-publishing on a request bus would reintroduce the loop. It now holds
      `[f 120]` fed by `[r tempo]`, banged once at 300 ms: whatever tempo has arrived, or 120 if
      none has. Measured with a control build:

      | Late-created clock, 6 s at 120 BPM | Beats |
      |---|---|
      | without the seed | **0** |
      | with the seed | **12** |

      ⚠️ **And a lesson about the rig again:** the first attempt to reproduce this used
      `#X declare -path /path/with a space` **unescaped**, so the abstraction never loaded and the
      count was 0 for an entirely different reason. A test that fails for the wrong reason looks
      exactly like a test that fails for the right one. The real evidence came from Brendan's run,
      where the declare was correct.
- [x] **62. Two BPM readouts on the dev panel, and they are meant to disagree.** ✅ `tempo-bus`
      shows the **bus** — what was requested, so `5000` — while the OLED row shows what `u_tempo`
      did with it, `600`. Both are useful and neither is wrong; the readout was previously labelled
      `bpm`, which implied it was the effective tempo. Renamed. The LED word readout was likewise
      labelled `empty`: **atom boxes use `-` for "no label", not the iemgui `empty`.**

- [x] **63. ✅ `[midiout]` with the port set into the cold inlet DOES reach that port — the ⬜ that
      has been open since the phase began.** Test A of `tools/midiout-probe.pd` — raw note-on bytes
      out of `[midiout]` with `1` sent to its right inlet at load — fired pad 1 on the SP-404.
      That is `u_tempo`'s exact mechanism, so the clock's emission path is confirmed rather than
      assumed. *(The creation-argument form, `[midiout 3]`, remains ⬜ and unneeded — see item 53.)*
- [x] **64. ⚠️ THE 404 WAS FOLLOWING THE CLOCK ALL ALONG — the wrong number was being read.** ✅
      The BPM shown beside a pad is that **sample's** tempo (150 for pad 1, 160 for pad 2) and never
      moves under external sync. The external tempo is on the **Pattern Select** screen as
      `EXT nnn`. Measured: a 20.833 ms pulse interval gave `EXT 120`, and 30.833 ms gave `EXT 81`
      — 81.08 BPM to the digit. Full behaviour in [ref-midi.md](ref-midi.md).

      **Three behaviours that fell out of the same session:** it *slides* into a tempo it has not
      seen and *snaps* to one it has; `250` alone starts the pattern sequencer with no clock at all,
      which makes Start the unambiguous "is it listening" test; and **when clock stops it reverts to
      its own internal tempo** (`EXT 81` → `BPM 125`) rather than holding the last external one.
      That last one is the first direct evidence for why `u_tempo` must keep sending 248 while
      stopped — previously an inference from the manual.

- [x] **65. ✅ The 404 follows external clock only between 40 and 200 BPM.** Swept `u_tempo` across
      its full 10–500: `EXT` slides down to **40** and stops, up to **200** and stops. A device
      limit, not a fault — but it means **clock-following cannot cover this instrument's range even
      in principle**, which is empirical backing for a decision
      [ref-software.md](ref-software.md) had already taken on structural grounds: *Pd sequences
      everything and timing rides in note events*. When tight 404 sync matters, stay inside
      40–200; outside it, the 404 has to be driven pad by pad.
- [x] **66. The dev panel's `aux` toggle takes two clicks per press, and that is correct.** ✅ `aux`
      is momentary 1/0 and `m_organelle` acts on the **1** only, so on a toggle the check is the
      press and the uncheck is the release — the release is *supposed* to do nothing. `aux-tap`
      exists for this reason: it sends 1 then 0, 120 ms apart, which is one real press per click.
      Reported as a partial failure of the bench's aux step, which is a fair reading of a step that
      did not say which widget to use. The step says so now.

- [x] **67. ✅ mother does NOT intercept a long aux press — the last open assumption in Phase 5.**
      Holding aux for two seconds has an identical effect to tapping it: one press, one transport
      toggle. So `[r aux]` is genuinely ours, and `u_map`'s toggle needs no long-press handling.
      This was ⬜ purely because *nothing had claimed it* — which is exactly the reasoning that
      turned out wrong about the encoder, so it was worth checking rather than assuming.
- [x] **68. ✅ Hands off the device, the OLED sits on the meters and the footer.** No `og-knob-*`
      rows persist, so nothing pins the param layer open. ⚠️ **This does not distinguish "mother
      does not stream knob positions" from "the `[change -1]` guard filters them"** — and it cannot,
      without removing the guard. The outcome is correct either way and the guard stays; the
      underlying question is now moot rather than answered.
- [x] **69. ⚠️ THE PATCH BOOTS AT WHATEVER KNOB 1 IS PHYSICALLY SET TO, not at 120.** ✅ Observed on
      the device: knob 1 was near its minimum, so the footer came up at **10-bpm** and the 404
      pinned at its own floor of 40. `u_tempo` seeds 120 at 300 ms and mother then pushes the real
      knob positions, which win.

      **Two things this confirms:** mother **does** send knob values at load ✅, and
      `m_organelle`'s `[change -1]` is doing real work — a bare `[change]` would have swallowed a
      knob sitting at 0 and left the tempo at 120, which is the bug fixed in item 52b, now seen
      from the other side.

      ✅ **Decided: this is the wanted behaviour.** The instrument comes up at whatever the knob is
      physically set to, which is the honest reading and avoids any pickup mismatch. No
      `knob1Override` scheme is needed. The rest of this note is kept because the *reason* it
      happens is not obvious.

      **The alternative, for the record** — physical-control-wins
      means no pickup mismatch, but it also means the instrument can boot at 10 BPM. `mother.pd`
      exposes `knob1Raw` and `knob1Override` if a pickup scheme is ever wanted. Tracked in
      [plan-v02.md](plan-v02.md).

### Session 6b — Phase 5 on the Organelle

Deployed with `./deploy.sh`, then the bench run by hand as a third patch for a real console.

- [x] **70. The whole bench, on the device.** ✅ All fifteen steps. `wire.sh` reported **3
      connections** (nano in, 404 in and out — the Launchpad is not attached, cable shortage), and
      `m_nano-control-channel: 17` confirmed the channel block through the real `[ctlin]`. Counts
      **30 / 20 / 20** at step 3 *and* step 11 — so two `c_clock` instances at ratios 1 and 1.5 run
      correctly under real DSP on the hardware, and the clock keeps running while the transport is
      stopped.
- [x] **71. The 404 follows, and stops following where it must.** ✅ `EXT` tracked knob 1 through
      the map, pinning at the device's own 40 and 200 limits (item 65). Start and stop drove its
      pattern. **This is Phase 5's *done when*, met on the hardware.**
- [x] **72. ⚠️ `status panic` was sticky and nothing cleared it.** Found on the device: after the
      panic step, pressing aux started the transport, turned the LED green and started the 404 —
      **and the footer still read `panic`.** Correct per the code as written and wrong for a
      performer: `status` is sticky by design and only a *tempo* message rewrote it, so the footer
      described a state the instrument had already left.

      **Fixed:** a start or a stop now bangs the stored BPM back into the footer, so it always
      describes the state you are in. Measured: `panic` → footer `panic`; `start` → LED `running`
      **and footer `120-bpm`**. Both transport triggers gained an outlet for it, firing last so the
      display is updated after the state it reports.

      ⚠️ **The edit itself found a trap worth recording.** Inserting the new boxes "before the first
      `#X connect`" put them inside the first **subpatch**, because a subpatch's own connects come
      earlier in the file. `pd-layout-check.py` caught it as `BAD CONNECT`, and Pd printed
      `connection failed` — but only because the indices happened to be out of range. **Top-level
      objects must be inserted before the first connect at depth 1**, and any script that walks a
      `.pd` file has to honour `#N canvas` / `#X restore` nesting or every index after the first
      subpatch is wrong.
- [x] **73. The error log proves the alerts fired.** ✅ Reading it back with
      `tools/fetch-errors.sh` after the run: `66000 warn u_tempo bpm-out-of-range` and
      `76000 warn u_tempo bpm-out-of-range` — bench steps 7 and 8 fire at 66 s and 76 s, so both
      alerts were raised exactly once each at exactly the right moments. **That answers a question
      the eye could not**: watching a 2 s alert on a 128×64 screen while also watching a 404 is not
      reliable, and the log settles it afterwards. All deployed files md5-identical to the repo.
- [x] **74. Throughput with the clock added.** ✅ **119 UDP datagrams/second**, load 0.44, ALSA 3
      connections — in line with item 37's 117/s, so the display keeps up with ~96 MIDI messages a
      second alongside it. ⚠️ **CPU read 10.6 %, but under the by-hand launch with the bench still
      loaded** — two extra `c_clock`s and fifteen delay chains — so it is a worst case, not the
      deployed baseline. The deployed figure is still to be taken.
- [x] **75. ⚠️ The clock is NOT free — it roughly doubled Pd's CPU.** ✅ Measured on the **deployed,
      idle** patch: **10.2 %** CPU, **117 UDP datagrams/second**, load 0.50. The display is
      unchanged (117/s matches item 37 exactly); the CPU is not — Phase 4 measured **5.3 %**.

      **Two measurements bracket the cause.** The by-hand run *with the bench loaded and two extra
      `c_clock` instances* read **10.6 %**, against **10.2 %** deployed with none — so two more
      phasors and fifteen delay chains cost about **0.4 points**. The DSP is therefore not what
      doubled it, and the remaining candidate is the **96 ALSA MIDI writes a second** the two
      clock ports produce. Not confirmed by isolation ⬜, but the arithmetic only points one way.

      **Still comfortable** — 10 % with load 0.5 on a device that idles near zero — but the plan
      predicted this would be "almost certainly free" and it was not, which matters for v0.3, where
      four filter stages arrive on top.
- [x] **76. ⚠️ A NANO BUTTON WAS TOGGLING THE TRANSPORT, and the culprit was `mother.pd`.** ✅ Found
      by running `phase4-bench` steps 15–17 on the device: five top-row buttons each produced a
      *second*, unrelated parameter —

      | Pressed | Also produced |
      |---|---|
      | `btn-t-1`…`btn-t-4` | `og-knob-1`…`og-knob-4` |
      | `btn-t-5` | **`og-aux`** — which toggles the transport |

      **Cause, read out of `/root/fw_dir/mother.pd`:** it runs `[ctlin 21]`–`[ctlin 26]` with **no
      channel argument, so OMNI**, and maps them onto `knob1`–`knob4` and `aux`. The nano's top row
      is CC 21–29 by this project's own by-tens scheme, so the two overlap exactly. `btn-t-1` was
      therefore slamming knob 1 — **500 BPM on press, 10 on release** — and `btn-t-5` was pressing
      aux. ⚠️ mother also **loads a different patch on any program change**, which the SP-404 can
      send.

      **Phase 5 is what made this dangerous.** Before aux drove the transport, CC 25 did nothing
      visible. The collision existed through all of Phase 4 and could not have been noticed.

      **Fixed:** `u_init` sends **`midiInGate 0`** at load **and again at 2 s** — and the second one
      is the one that works. ⚠️ **The mother binary pushes its own `midiInGate 1` over OSC about half
      a second after the patch loads**, overwriting anything sent at `loadbang`, so the first
      attempt at this fix silently did nothing and the collision survived a deploy. Measured with an
      `[r midiInGate] → [print]` loaded *before* `main.pd` so it could see both writers:

      ```
      GATE: 0     <- our loadbang
      GATE: 1     <- the mother binary, before 0.5 s
         mark-2s
      GATE: 0     <- our delayed copy wins
      ```

      No further pushes out to twelve seconds, so one late send is enough. ⬜ Using the System menu's
      *MIDI Config* page mid-session may push it again; `/sdcard/MIDI-Config.txt` stores only the
      **channel**, so there is no persistent gate setting to set instead.

      ✅ Verified from the source that it gates only the MIDI-derived paths — mother has two `s notes`, one fed by `oscIn` (the physical
      keyboard) and one behind the gate (`notein`), and the knobs split the same way — so the front
      panel is untouched and Cut It's own `[ctlin]` objects are unaffected.
- [x] **77. The Launchpad's flash and pulse do track our clock — within limits.** ✅ Three pads lit
      static / flashing / pulsing from `tools/lp-modes.pd` alongside the running patch, and sweeping
      knob 1 visibly changed the flash and pulse rates. **So Phase 6's assumption holds**: animation
      follows `u_tempo` for free and does not have to be driven from `clock`.

      ⚠️ **But it has its own range**, ⬜ not pinned down: past an upper and a lower limit the
      animation **reverts to a default rate** rather than continuing to track, and a Start makes it
      dip briefly before settling back. Same shape as the 404's 40–200 window (item 65) and almost
      certainly the same kind of device-side limit — the pulse stream itself is known good, since
      the 404 tracks it to the digit across its whole range. **Noted, not chased**; it matters only
      if Phase 6 wants animation locked at extreme tempi.

- [x] **78. ✅ The 120 BPM seed is now a fallback rather than a default, and the boot tempo is
      deterministic.** The patch had started at the knob's position one day and at 120 the next —
      a **race** between mother pushing the real knob positions and `u_tempo`'s `del 200` seed,
      with no guarantee either way. `u_tempo`'s seed now goes through a **spigot that any incoming
      `tempo` closes**, so it can only ever fill a silence.

      Measured both ways on the Mac — knob pushed at load → `TEMPO: 255` and no seed; nothing pushed
      → `TEMPO: 120` — and then on the device:

      ```
      PARAM: og-knob-4 0 … og-knob-1 0     <- mother pushes the knob positions
      TEMPO: 10                            <- the knob wins, the seed never fires
      ```

      Same "seed only if unheard" shape as `c_clock`'s fix in item 61. **It still matters on the
      Mac**, where nothing pushes a knob position at all.
- [x] **79. ✅ mother's MIDI *output* echo is off too — `midiOutGate 0`.** mother routes the
      Organelle's **keys as MIDI notes and its knobs as CC 21–24** to every output port. Observed:
      playing the keyboard lit pads on the Launchpad — and with the SP-404 attached instead it would
      have **triggered pads**. The design has the keys going to the Volca and nowhere else, so
      mother must not route them at all; Cut It will send them deliberately once the DIN interface
      exists.

      ✅ It gates only mother's own `[noteout]` and `[ctlout]`; our `[midiout]` is untouched, which
      the device trace confirms — the clock still leaves on ports 1 and 3 with both gates closed.
      Sent from the same message box as `midiInGate`, so it inherits the 2 s re-send.


### Still outstanding

- [ ] **55. The Phase 3 and Phase 4 regressions.** `m_nano` gained a `[t a a]` and a second send,
      and the footer now carries the BPM — so `phase4-bench.pd` is the gate on the first and
      `phase3-bench.pd` on the second. Needs the nanoKONTROL attached; nothing else about them
      changed.
- [ ] **56. Everything that is the hardware.** The 404 following the tempo is the real *done
      when* and no amount of Mac testing can stand in for it. Also the four LED colours by eye,
      whether mother eats a long aux press, whether mother streams knob positions when nothing is
      moving, and CPU + datagram rate against items 21 and 37 — clock on two ports adds about 96
      MIDI messages a second.

### The procedure, in order

**Do every Mac step first. Then deploy once.** Expected result is stated *before* each action,
including the steps whose correct result is that nothing happens.

**Mac, one-time setup.** ⚠️ **Tick `enable-DSP` on the dev panel.** `threshold~` is a signal
object, so with DSP off there is no phasor, no pulse and no beat — and the failure looks exactly
like a broken clock rather than like a setting. This is the Phase 5 equivalent of Phase 4's "no
MIDI input saved in preferences". Nothing else is needed: **tempo is the Organelle's knob 1 now,
so the whole clock is drivable from the panel with no MIDI configured at all.**

**Mac, static.** `python3 tools/pd-layout-check.py "Cut It"/*.pd tools/phase5-bench.pd` — every
line must say `0 problems`. Then the syntax check on both entry points; **silence is the pass**.

**Mac, boot.** Open `Cut It/main-dev.pd` and tick `enable-DSP`. Expect, in order: `booting` →
`wiring` → `launchpad` → the two meters, and then at about four seconds the footer changing from
`v0.2-ready` to **`120-bpm`**. The `aux-LED` radio on the panel should sit on cell **5**, dark
blue, and the `beat` bng should flash twice a second. **If the beat bng is dark, DSP is off.**

**Mac, the transport.** Click `start`: the LED radio moves to **3** (green) and nothing else
changes — the beat was already running. Click `stop`: back to **5**. Click `panic`: **1** (red)
and the footer says `panic`. The beat must keep flashing through all three.

**Mac, the map.** Sweep the panel's `knob1` slider. Expect `og-knob-1` to appear as a parameter
row, the `bpm` readout to track **10 → 500**, and the footer to follow it. Click `bpm-hi` (5000):
the footer clamps to `600-bpm` and one alert appears. Click it again: **nothing happens** — that
is the pass. Click `bpm-lo` (0): clamps to `5-bpm` and alerts **again**, because the value
changed even though the verdict did not.

**Mac, the aux button.** Click `aux-tap`: the LED goes green. Click it again: dark blue. This is
the same path the real aux button takes, so if it works here and not on the device, mother is
eating the press.

**Mac, the bench.** `pd -path "Cut It" "Cut It/main-dev.pd" tools/phase5-bench.pd`, DSP on, and
watch the console. Steps 3 and 10 must print **20 / 20 / 30**; step 7 must produce exactly one
alert. Steps 12 and 13 will ask for hands you do not have on the Mac — they are for the device.

**Then `./deploy.sh`** and do it again on the hardware, where the additions are:

1. **The aux button, by hand.** Press: green, and the 404 starts. Press again: dark blue, and it
   stops. ⬜ If nothing happens at all, check whether mother is intercepting the press before
   suspecting `u_map` — the encoder is the precedent for a control that turned out not to be free.
2. **Knob 1, by hand.** ⚠️ **The 404 following the sweep is the real *done when* of Phase 5** —
   and read it in the right place: **`EXT nnn` on the Pattern Select screen**, never the BPM beside
   a pad, which is that sample's own tempo and never moves. Expect `EXT` to *slide* rather than
   snap; the slide is the several-pulse inference working, not a fault. Item 64.
3. **The four colours by eye**, which is the only way to settle whether dark blue reads as
   "stopped" or as "off" at arm's length on a dark stage.
4. **Hands off the device for thirty seconds.** The OLED must fall back to the two meters and the
   footer. ⬜ If four `og-knob-*` rows sit there permanently, `mother.pd` streams knob positions
   continuously and the `[change]` guard in `m_organelle` is doing real work.
5. **CPU and datagram rate**, comparable to items 21 and 37.
6. `./tools/fetch-errors.sh` afterwards — the only error the run should have raised is
   `bpm-out-of-range`, twice.

⚠️ On the Mac an error also prints `/sdcard/cut-it-err.cur: write failed`. That is `/sdcard` not
existing there, it is the documented diagnostic working, and it cannot affect `deploy.sh` — the
check quits before the flush metro fires.

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
   opportunistic; neither blocked Phase 5.
5. **Items 55 and 56** — Phase 5 on the hardware. Everything that can be measured off-device has
   been (items 48–54); what is left is the 404 actually following the tempo, the aux button, the
   LED colours by eye, and the two regressions that need the nanoKONTROL attached.

Everything else in Sessions 1, 2, 4 and 4d has passed. The full MIDI picture — every message each
device accepts and transmits — is catalogued in [ref-midi.md](ref-midi.md), which also
carries the remaining message-level unknowns, chief among them the **SP-404 pad note range**
(verified 47+*n* here, but Roland's chart says 35–51 — sweep all 16 pads before writing
sequencing code against it).
