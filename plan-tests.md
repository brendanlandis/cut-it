# Cut It — Hardware Checks, With Results

**The ordered checklist and its evidence.** It began as pre-flight tests — things to verify before
committing to a design — and has since grown a session per build phase, because every phase's
measurements belong beside the checks that preceded them.

Two things live here and nowhere else: the **numbers** (counts, rates, CPU, byte-level results) and
the **procedures** that produced them. The narrative of what each phase taught is
[ref-build-log.md](ref-build-log.md); what is still open is [plan-v03.md](plan-v03.md).

Early sessions need scratch patches only — no Cut It code. Diagnostic patches live in
[tools/](tools/). Companion to [ref-hardware.md](ref-hardware.md), which explains *why* each of these
matters.

**Status:** Sessions 2, 3b, 3c, 4, 4b, 4c, 4d, 6 and 6b complete — **Phases 3, 4 and 5 are all
verified end to end on the Organelle.** ⚠️ **Session 7 (Phase 6) is complete on the Mac only** —
items 82–93b pass, 94–97 need the device and nothing has been deployed. Session 1 is done bar the
full-load power check. Session 3 is blocked on the TRS Y-cable; Session 5 has not been attempted.

⚠️ **Item numbers are unique across the whole file and other documents cite them by bare number**
("item 21c", "item 31"). Sessions 4 and 5 were renumbered to 40–42 and 43–46 to remove a collision
with Session 3c's 15–22; items 11, 21, 21c, 23 and 31 were left alone because they are cited
elsewhere. **Never reuse a number** — add at the end, or suffix (`21b`, `21c`).

**The two tests that could have forced a redesign have both passed:** Pd can drive the
Launchpad's Programmer Mode over SysEx (LEDs, velocity, polyphonic aftertouch), and Pd's
per-device channel offsets work with multiple controllers at once. What remains is
cable-blocked — the audio topology and full-rig power draw.

**Do not treat open items as settled facts.** This file is the ordered checklist with results;
**what to do about anything still open is in [plan-v03.md](plan-v03.md) under *Open questions***,
which is the only place that carries plans. The [tools/](tools/) patches are working references
for every technique verified here.

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

See [plan-v03.md](plan-v03.md) → *The last thing that could force a redesign* for why this one
still matters, and *Deliberately skipped for now* below for the LINE IN R-only variant.

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

      ⚠️ **They were briefly decoded as a mode control inside `m_nano` and are not any more.**
      Phase 4 made all six ordinary momentary CC, read through one path; **Phase 6 mapped them to
      `mode` in `u_map`**, which is where meaning belongs. The CC numbers and the channel below are
      unchanged and still correct — see item 38b, item 90 and
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

### How both device measurements are taken

Item 21 recorded the numbers and not the method, which is why they were hard to repeat. Both
procedures are copy-paste, neither disturbs the running patch, and **both have moved to where they
get used**:

- **Running a bench on the device**, as a third patch with a real console — [tools/README.md](tools/README.md), *Running a bench on the device*. Note the `-path`: without it `c_clock` fails to create and its counts read 0, which looks exactly like a dead clock.
- **CPU, load and datagram rate** — [ref-hardware.md](ref-hardware.md), *Measuring the running patch*, with the `pgrep -nx` trap and the baseline figures for every phase. The numbers those produced are items 21, 37 and 75.

### The rest of the nanoKONTROL, and the OLED by eye

- [x] **38. The nanoKONTROL on the device**, where it is Pd input slot 2 and the channel is **17**.
      ✅ **The transport row was read on the hardware and is correct** — pressing a transport key
      displays its own name and a `1`, exactly like every other button, with no toggle and no footer
      change. That is the change Phase 4 finished on, and it works through the real `[ctlin]` at
      channel 17.

      ✅ **The remaining 36 controls have since been swept too — see item 80.** They were left
      until Phase 5 as low risk rather than untested, and the sweep is what found the `mother.pd`
      CC collision (item 76), so "low risk" was the wrong reading. If a control is ever silent,
      check `aconnect -l` before suspecting the patch.
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
      device incidentally, via item 38's transport presses.

      ⚠️ **What remains is a judgement, not a test.** Item 80 ran steps 15–16 on the hardware — two
      faders at once, then three, then all nine — so the 2-mover and 3–5-mover layouts *have* now
      been rendered on the device and their row behaviour passed. What was being checked there was
      that each control reported the right name and held its row. **Nobody has yet stood back and
      decided whether 16px and 8px rows are readable at arm's length on a dark stage**, which is
      the only question this item was ever about.

      Tracked in [plan-v03.md](plan-v03.md), where it feeds the *OLED UI refinement* work rather
      than blocking anything.

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

      The colour table, the states `g_led` maps onto it and the command to re-run the sweep are all
      in [ref-display.md](ref-display.md).

### The Phase 4 procedure, in order

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
      [plan-v03.md](plan-v03.md). **The lesson is that the obvious experiment was invalid**, which
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
      exposes `knob1Raw` and `knob1Override` if a pickup scheme is ever wanted — recorded here as
      the road not taken, not as open work.

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
- [x] **75. ⚠️ The clock is NOT free — it roughly doubled Pd's CPU. ✅ BUT THE CAUSE RECORDED HERE
      IS WRONG, AND IS NOW ISOLATED (2026-08-03).** This item blamed the 96 ALSA MIDI writes a
      second and marked it ⬜ *not confirmed by isolation*. **Confirmed now, and they are not it.**
      Tempo varies the MIDI rate while leaving DSP cost identical — `phasor~` and `threshold~`
      cost the same per sample at any frequency — so knob 1 is a clean one-variable sweep.
      Measured on the device across a **50× range**: **10 BPM (8 writes/s) → 9.9 / 9.9 / 9.8 /
      9.9 %**; **120 BPM (96/s) → 10.6–11.3 %**; **500 BPM (400/s) → 11.7–11.9 %**. That is a
      slope of **≈0.48 points per 100 writes/s**, so the 96 writes at 120 BPM are worth about
      **0.43 points** — against the **4.9 points** this item attributed to them. **Wrong by an
      order of magnitude.**
      ✅ **PROVEN BY DIRECT ISOLATION, not elimination.** `tools/dsp-toggle.pd` and `tools/dsp.sh`
      turn Pd's audio engine off from outside on the running patch. Measured on the device:
      **DSP on 11.8 / 11.7 / 11.8 %, DSP off 4.9 / 4.9 / 4.9 %, back on 12.0 / 11.8 %** —
      reversible and repeatable. **The DSP costs 6.9 points. The MIDI clock costs 0.43.**
      This item blamed the wrong thing by a factor of about sixteen.
      **What that means for v0.3**, which stacks four filter stages on this baseline: the headroom
      question is a DSP question, and the clock is nearly free. Anything spent optimising MIDI
      output here would be spent in the wrong place — including the *stop sending clock to port 1*
      idea in `plan-v03.md`, which is now worth about 0.2 points and not worth doing for CPU.
      ✅ **AND THE SPLIT IS MEASURED TOO.** A scratch copy of the patch with two EXTRA `c_clock`
      instances (appended after the last box so no `#X connect` index moved) was launched by hand
      beside the real one, which was never touched. **1 instance: 11.8 / 11.8 / 11.7 / 11.5 %.
      3 instances: 12.4 / 12.4 / 12.6 / 12.8 %.** That is ~0.85 points for two, so
      **≈0.43 points per `c_clock`** — near item 75's original 0.2 estimate and the same order.
      **So of the 6.9-point DSP total, three clocks are ~1.3 and the remaining ~5.6 is the base
      graph** — audio passthrough, the level meters and `u_tempo`'s own `phasor~`/`threshold~`.
      **This is the number poly-tempo needed**: ten more clocks would cost ~4.3 points. Clocks are
      cheap; the base graph is where the DSP budget already went.
      ⬜ One thing still does not reconcile: the Phase 4 → 5 jump of 4.9 points arrived WITH the
      first clock, yet a marginal clock costs 0.43. Either `u_tempo`'s own DSP is far more
      expensive than a `c_clock`, or the 5.3 % Phase 4 baseline is not comparable. Not worth
      chasing unless a headroom decision turns on it — the marginal cost is what v0.3 uses.
      ORIGINAL ENTRY FOLLOWS. ✅ Measured on the **deployed,
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


- [x] **80. ✅ The whole nanoKONTROL, on the device — all 42 controls, and it closes item 38.**
      `tools/phase4-bench.pd` steps 15–17 run by hand on the hardware: every slider, knob and
      button reports its own name and nothing else on the OLED, with no stray second parameter.

      **This is the sweep that had been deferred since Phase 4 as "low risk"**, and running it is
      what exposed the `mother.pd` CC 21–26 collision (item 76) — five top-row buttons each
      producing a phantom `og-knob-*` or `og-aux`. The re-run above is the confirmation that the
      `midiInGate 0` fix holds through the whole surface, not just the two buttons that showed it.

      ⚠️ **The lesson is about the deferral, not the bug.** The decode had been verified
      exhaustively off-device (item 31) and the only thing the hardware added was thought to be the
      channel offset. What it actually added was a *second decoder* running in `mother.pd` on the
      same CC numbers — invisible in every Mac test, because `mother.pd` is not there.

- [x] **55. The Phase 3 and Phase 4 regressions.** ✅ **Phase 4** is closed by item 80 — the
      `[t a a]` and the second send are exercised by every control on the surface. ✅ **Phase 3**
      is closed by the footer behaving correctly across the whole Phase 5 bench on hardware (items
      70 and 72), including the `status panic` bug that only a footer regression would have caught.
- [x] **56. Everything that is the hardware.** ✅ All of it, in Session 6b: the 404 following the
      tempo (item 71 — Phase 5's real *done when*), the LED colours by eye, mother **not** eating a
      long aux press (item 67), the knob-streaming question (item 68, now moot), and CPU plus
      datagram rate (items 74 and 75).
- [ ] **81. ⬜ The Organelle drops its wifi after a while.** Observed repeatedly across Session 6b:
      the connection is up after a deploy and gone an hour or so later, needing a manual
      reconnect. It costs nothing once a session is already underway, but it silently breaks
      `deploy.sh` and `tools/fetch-errors.sh`, and it would take the phone display down mid-set.

      **Unattributed** — dongle, hub current, the access point, or `wifi_control.py`; nothing has
      been isolated. Not urgent, and **Session 5's access-point work would sidestep it entirely**,
      which is the argument for doing that before chasing this. If it is ever chased: start by
      logging `iwconfig wlan0` and `dmesg | tail` from cron, since the failure is unattended by
      definition and the interesting evidence is whatever happens at the moment it drops.

### The Phase 5 procedure, in order

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

✅ **PARTLY ATTEMPTED — the AP works, and it is the vendor's own script rather than a hostapd
project.** Items 125–128 below are what Phase 7's session established. What is still open is the
display link *over* the AP, which needs one more pass.

**Why it matters:** the display currently rides the house wifi. In a venue that is either
absent, congested, or full of other people's phones. An Organelle-hosted AP with one client a
metre away removes the venue from the equation entirely.

**What's already known:** `hostapd` and `dnsmasq` are installed, `wlan0` exists, and `iw list`
reports **AP** among supported interface modes. ✅ The dongle is a Ralink RT5370, a
well-supported hostapd chipset.

- [x] **125. ✅ The wifi credentials live in `$USER_DIR/wifi.txt`, and `wpa_supplicant.conf` is a
      decoy.** Plain text, alternating SSID and password lines, `USER_DIR` = **`/sdcard`** which is
      mounted `rw` — so adding a network is appending two lines and needs no `remount-rw.sh`.
      `/etc/wpa_supplicant/wpa_supplicant.conf` is the stock 2015 example file and **nothing reads
      it**. ✅ An SSID containing a space and an apostrophe works, because `wifi_control.py`
      interpolates it inside double quotes. Details in [ref-hardware.md](ref-hardware.md).

- [x] **126. ✅ The AP comes up, and `create_ap` does all the work.** `start-ap.sh` reads
      `$USER_DIR/ap.txt` — first line network, last line password — and calls
      `create_ap --no-virt -n wlan0 $NET $PW`, defaulting to `Organelle` / `coolmusic`.

      Brought up as **`organelle` / `definitelycutit`**. ✅ **Two clients joined**: the iPhone, and
      the Mac at `192.168.12.145` with the Organelle as gateway on `192.168.12.1`. The phone's
      lease was **192.168.12.109**.

      ⚠️ **The passphrase must be 8–63 characters** — `create_ap` rejects anything shorter. This
      matters more than a normal typo because `start-ap.sh` runs `killall wpa_supplicant` **before**
      calling `create_ap`, so a rejected passphrase leaves the device with **no wifi and no AP**,
      recoverable only by power cycle. A five-character password was caught before it was tried.

      ⚠️ **`$NET` and `$PW` are passed UNQUOTED**, so an AP name with spaces would break — unlike
      `wifi.txt`, which handles them. Keep the AP name one word.

      ✅ **Recovery is a power cycle.** `createap.service` is `disabled`, so the device returns to
      the home network on its own. Nothing about this is sticky.

- [x] **127. ⚠️ ✅ THE AP HAS NO INTERNET, WHICH MAKES IT UNDRIVEABLE FROM THE MAC.**
      `create_ap` is called with **`-n`** — no internet sharing — so a Mac joined to `organelle` is
      off the internet, and **Claude cannot run at all**. The Organelle has one radio, so it cannot
      be both AP and client; there is no way to give that AP a route.

      **Consequence for the workflow, and it is a real one:** an AP session cannot be driven
      interactively. Either the Mac needs a **second interface** (Ethernet for internet, wifi for
      the AP), or the AP is treated as **stage-only** and everything is prepared beforehand on a
      network that has both.

      **This is what the phone's hotspot is actually for** — it is the one configuration where the
      Mac, the Organelle and the phone share a network *and* there is internet. ⚠️ It needs
      cellular, so it cannot be combined with airplane mode; that is a development network, not a
      stage one.

- [x] **128. ✅ ⚠️ BROADCAST WORKS AND IS STILL THE WRONG ANSWER — measured, then rejected.**
      `u_net`'s target is one literal IP, correct on exactly one of three networks, so a broadcast
      address that needs no subnet knowledge looked like the clean fix.

      **Everything about it checks out except the one property that matters:**

      | | |
      |---|---|
      | Linux permits it | ✅ `[netsend -u -b]` to `255.255.255.255`, no `SO_BROADCAST` error |
      | PdParty accepts it | ✅ the phone updated from a broadcast-only patch |
      | Delivery | ✅ **19–20 of 20**, against a **unicast control that managed 18 of 20** |
      | **Latency** | ❌ **up to 819 ms** |

      ⚠️ **Wifi access points buffer broadcast and multicast frames and release them on beacon
      boundaries**, so power-saving clients can receive them. Measured against a patch sending
      every 200 ms:

      ```
      unicast    200 200 199 199 201 202 199 208 196 396 206 198   median 200 ms
      broadcast    1   1   1 817   1 819   1   1   1 614   1   0   median 1 ms, max 819
      ```

      **Broadcast arrives in bursts of three or four separated by most of a second.** Throughput is
      identical, which is exactly why the delivery test saw nothing wrong — **it measured the wrong
      property.** A person moving a knob noticed within seconds what three runs of packet counting
      had missed.

      It also eats the phone's **1500 ms** `NO-LINK` margin: one 819 ms gap plus a dropped burst
      exceeds it and shows a false disconnect.

      **Reverted to unicast.** The address stays literal and has to be edited per network —
      `192.168.1.5` at home, `192.168.12.109` on the access point.

      **The real fix is for the phone to announce its own address**, which needs no new mechanism:
      the bidirectional path is already proven in `tools/osc-bridge/`. That is design work, not
      configuration, and it belongs in its own phase.

- [x] **129. ⚠️ ✅ `create_ap` DOES NOT SURVIVE A PATCH CHANGE when a patch started it — the probe
      killed its own approach.** A `Start AP` menu patch ran `setsid nohup start-ap.sh &` through
      `[shell]`. Selecting the next patch restarts Pd, and `create_ap`, `hostapd` and `dnsmasq` all
      went with it **despite `setsid`**.

      ✅ **The access point had not finished collapsing when the probe ran** — `wlan0` still held
      `192.168.12.1/24` and the phone was still associated at **−17 dBm** — which is why the screen
      was still readable. Dying, not dead.

      ✅ **The arp fallback is what saved the run.** dnsmasq was already gone so its `--dhcp-leasefile`
      argument could not be read; the address came from `/proc/net/arp` instead. **A single-strategy
      probe would have returned `none` and taught us nothing.**

      ✅ **Both other questions answered anyway:** the lease file is
      `/tmp/create_ap.wlan0.conf.*/dnsmasq.leases`, and the phone is **192.168.12.109** — the same
      address on two separate sessions, so the lease is stable.

      **The fix is to stop hanging the AP off Pd.** The Organelle already has **`Start AP` in its own
      System → WiFi Setup menu** — found in `wifi_setup.py`, predating anything built here — which
      is not a child of a patch. ⬜ **Untested, and it is the one thing left to prove**: same probe,
      start the AP from the built-in menu instead, then load `AP Probe` and read Q1.

- [x] **130. ✅ `u_net` now DISCOVERS the phone rather than being told.** `Cut It/phone-ip.sh` reads
      the dnsmasq lease off the Organelle's own access point — where the Organelle handed the
      address out and therefore already knows it — and **falls back to the creation argument**
      anywhere else, so it always prints exactly one line and no conditional lives in the patch.

      **This is what makes one build work on both networks.** A literal address is right on exactly
      one and dead on the others; item 128 ruled out broadcast as the alternative.

      ⚠️ **The `[del 700]` fallback is what keeps the Mac working.** `shell` is an external that
      exists only on the Organelle and `mac-stubs/shell.pd` answers nothing, so off-device the
      script never replies and the timer connects to the creation argument instead. It also covers
      the script hanging or failing on the device.

      ✅ Measured, rather than assumed, before wiring: `[shell]`'s output is accepted directly by
      `[symbol]`, and on the device `sh phone-ip.sh 192.168.1.5` returns `192.168.1.5` with no AP
      running.

      ⚠️ **The gate was wrong and now is not.** `phase7-assert.sh` launched Pd **without**
      `-path mac-stubs`, so `[shell]` failed to create and the fallback carried every run — 28
      checks passing against a different object graph than the real patch. *A measuring rig is code.*

- [x] **131. ⚠️ ✅ THE VENUE SEQUENCE WORKS — and it surfaced a USB fault that looked like a code
      bug.** Run end to end with no laptop: System → WiFi Setup → **Start AP**, phone in airplane
      mode joins `organelle`, load **Cut It**. ✅ **The phone display worked on the stage network**,
      with `u_net` finding the address itself via item 130. That closes the last unknown in the
      sequence, and confirms the BUILT-IN Start AP survives a patch change where the patch-started
      one of item 129 did not.

      ⚠️ **But the Launchpad came up stuck in Live Mode**, which reads exactly like the Programmer
      Mode SysEx failing. It was not a patch fault at all:

      | | |
      |---|---|
      | `lsusb` | `1235:0123 Focusrite-Novation` — **present on the USB bus** |
      | `/proc/asound/cards` | **absent** — only the nanoKONTROL |
      | `aconnect -l` | no Launchpad client, so nothing for `wire.sh` to connect |

      **The device enumerated electrically but never presented its MIDI interface**, so the SysEx
      left Pd and died. `wire.sh`'s two Launchpad lines failed silently, which is by design — every
      `aconnect` in it is allowed to fail so a missing device cannot stop the boot — and `u_err`'s
      log was clean, because nothing in the patch went wrong.

      ⚠️ **And nothing would have recovered it.** `m_launchpad`'s watchdog re-runs `wire.sh` on
      device loss, but only after an arming gate: ownership can be dropped only once an inquiry has
      actually been answered. A device that was never reachable never arms it. **The gate that
      stops a phantom detector blanking the grid also stops recovery from a device that never
      appeared** — correct in both cases, worth knowing.

      ✅ **Fixed by a physical replug plus a patch reload.** All four ALSA links correct afterwards:
      Launchpad → `128:0`, nano → `128:1`, Pd → `32:0`.

      ⬜ **Cause not established.** A device enumerating on USB without claiming its audio interface
      is usually power or a wedged device, and **item 95 predicts this exact presentation** — two
      controllers plus the wifi dongle on a hub, never load-tested. Several power cycles preceded
      it. **If it recurs after AP sessions specifically, that is a pattern; suspect power before
      code.**

      ⚠️ **A misread worth recording:** `nanoKONTROL → 128:1` was briefly taken for the Phase 6
      phantom-`lp-cc` bug. It is not — `128:1` is Pd port 1, Midi-In **2**, channels 17-32, exactly
      what `m_nano 17` wants. The bug would show as `128:0`.

- [x] **132. ✅ ⚠️ THE MAC BENCH RUN — the step this phase had skipped, and it found two things.**
      15 of 15 steps, judged on the phone, driven with `HOST=127.0.0.1 ./tools/go.sh`.

      ⚠️ **A bug of my own making, visible only at boot.** `[metro]` fires the instant it is
      started, so the reconnect metro — armed at 1600 ms — banged the address store **before the
      address had been resolved**, sending `connect` with an empty host and printing `bad host?` on
      **every single boot**. Harmless by 2200 ms when the real connect lands, and invisible to
      `deploy.sh` because the syntax check quits first. **New with discovery**: before it, the store
      was `[f $2]` and an early bang produced a valid address. Fixed by arming the retry at **3000
      ms**, after resolution on both platforms — 1550 ms on the device, 2200 on the Mac where the
      `del 700` fallback covers a `shell` that never answers. By then a successful connect has
      closed the spigot, so the metro's own first fire costs nothing.

      ⚠️ **TWO INSTRUMENTS WILL FIGHT OVER ONE PHONE, and it does not look like contention.** With
      the Organelle running Cut It *and* `main-dev.pd` running on the Mac, both were connected to
      `192.168.1.5:8000` and the status row **fluttered between `120-bpm` and the Mac's knob value**.

      The bus was innocent — a `[r disp]` tap showed `status` carrying exactly four messages and
      never repeating. **`u_net` is the sole owner of the phone WITHIN an instrument; nothing
      arbitrates ACROSS machines.** The one-owner-per-surface rule does not reach that far, and the
      symptom is a baffling flutter rather than anything resembling two writers. **It will recur
      during off-device development with the device still powered** — stop one of them.

      ✅ **Everything else passed**: the link, both parameters, the status slot, the alert arriving
      through `u_err` and persisting 14 s untouched, a second alert replacing it, and all four
      reserved selectors inert.

      ✅ **The teardown is the same failure on both platforms, differing only in the errno** —
      **61** on macOS against **111** on Linux — with an identical tally of **12 connects, 11
      refusals and exactly one `net-link-down`**.

      ✅ **THE LATE-JOIN REPEAT VERIFIED ON HARDWARE for the first time.** After the reconnect the
      phone repopulated `grain` / `12` / `128-bpm` **by itself within about two seconds**, with
      nothing touched. Before item 123 it would have sat on `READY` and blank rows until something
      moved. The alert row correctly showed `warn` / `net-link-down` — `u_net`'s own error about the
      outage, newer than the bench's, so replacing it is right.

      ⬜ **Step 12 was Mac-skipped, deliberately.** It needs a hand on a nanoKONTROL fader and the
      nano is wired to the Organelle. The per-parameter trailing edge is covered twice already —
      a real fader stopped mid-travel at 88 on the device, and two *simultaneous* synthetic sweeps
      at 200 events/s in the headless gate. Moving the nano would have risked a channel-block
      mismatch proving nothing about `u_net`.

- [x] **133. ⚠️ ITEM 81 CAUGHT IN THE ACT, and it is NOT the radio dropping the network.** It
      happened mid-bench, between steps 11 and 12 of the device run, and for several minutes it
      looked exactly like a `u_net` fault — which is precisely what item 81's entry predicts.

      **What was actually true:**

      | | |
      |---|---|
      | `iw dev wlan0 link` | **still associated** to `hildegard`, BSSID and freq intact |
      | `wpa_supplicant`, `dhcpcd` | **both running** |
      | `ip addr show wlan0` | **no IPv4 address at all** — IPv6 link-local only |
      | the patch | `error: connecting stream socket: Network is unreachable (101)` |

      **So the association survives and the IPv4 LEASE is what is lost.** That is a much sharper
      diagnosis than "the Organelle drops its wifi after about an hour", and it points somewhere
      different: DHCP renewal — the router's lease time, or `dhcpcd` failing to renew — rather than
      the dongle, the power or the access point, which is where item 81 has been pointing all along.

      ⚠️ **A `dhcpcd -n wlan0` renew did not recover it** and appeared to finish off what was left:
      mDNS stopped resolving immediately afterwards.

      ⚠️ **AND SSH KEPT WORKING THROUGHOUT — over IPv6 link-local, via mDNS.** This is the part that
      matters. Every doc in this project says *check `ssh` before debugging code*, and **SSH
      answering was not evidence the network was up.** The symptoms were a dead phone link and a
      bench that would not advance, with a reachable device.

      ✅ **The correct check is an IPv4 address, not a login:**

      ```sh
      ssh root@organelle.local 'ip addr show wlan0 | grep "inet "'   # no output == this fault
      ```

      **`go.sh` failing to advance a bench is a symptom of it**, because the GO datagram is IPv4 to
      port 9998 and has nowhere to go.

- [x] **134. ✅ THE DEVICE RE-RUN — 15 of 15 on the build that includes everything.** The earlier
      15/15 predated the late-join repeat, the broadcast round trip, discovery and the retry fix, so
      it proved a patch that no longer existed. This one covers all of them.

      **Controlled reading** — menu-launched, transport stopped, phone connected, IPv4 confirmed:
      **CPU 11.7 %** on all three readings, **UDP 122–126/s**. Consistent with the 11.7–12.2 % band
      measured twice before, and +5 to +9 over the ~117/s display baseline, which is heartbeat 2 +
      alert 2 + repeat 1.

      ⬜ **The 10.2–10.5 % readings taken earlier are still unexplained.** Both followed patch
      reloads closely. Recorded rather than rationalised.

      ✅ **All fifteen steps**, with each reserved selector confirmed by a *different* surface
      reacting — Launchpad fully blue on `grid modal 45`, aux green on `led running`, phone still in
      both cases. The fader swept and stopped mid-travel. Teardown at errno **111**, one
      `net-link-down` across 19 connects and 18 refusals, and the phone **repopulated itself** after
      the reconnect.

      ⚠️ **Two workflow traps, both cheap and both cost time here:**

      - **`/tmp` is wiped on reboot**, so `/tmp/phase7-bench.pd` vanishes with a restart and the
        by-hand launch quietly runs `mother.pd` + `main.pd` with **no bench** — the GO port is never
        bound and the bench appears frozen at step 1.
      - **`/tmp/patch` does not exist until mother has loaded the patch once.** Launching by hand
        before that leaves the working directory wrong, so **`wire.sh` never runs and the MIDI
        wiring is silently absent** — no `wire:` line in the log is the tell. Load through
        `deploy.sh` first, then launch by hand.

- [x] **43. ✅ AP up, phone joined, display working over it.** `organelle` / `definitelycutit` via the System menu; the phone leased **192.168.12.109** and Cut It found it without being told. Items 126, 130 and 131.

- [ ] ~~**43. Bring up an AP on `wlan0` and join it from the iPhone.**~~ Confirm the phone gets an
      address from `dnsmasq` and the status display still updates.
- [x] **44. ✅ Confirmed in airplane mode** — cellular off, wifi re-enabled by hand, which is the whole point of hosting the network on the Organelle rather than using the phone's hotspot. A hotspot needs cellular; this does not.

- [ ] ~~**44. Check it in airplane mode**~~
- [ ] **45. Judge the link quality.** Watch the heartbeat for gaps over a few minutes. This is
      the actual question: is it steady enough to trust mid-set?
- [x] **46. ✅ Decided: it does NOT survive a reboot, and that is deliberate.** `createap.service` stays `disabled`, so a power cycle always returns the device to the house network — which is the recovery path for every AP mistake. Starting it is two menu presses at the venue.

- [ ] ~~**46. Decide whether it survives a reboot**~~ — and whether you *want* it to. Persisting it
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

## Session 7 — Phase 6, the Launchpad and the grid

**Items 82–97.** Step 0 (82–87) was run on the **Mac with the Launchpad plugged in**, which is
new for this project and is what made the rest of the phase off-device work. 88–93b are the build
verified against the real patch. **94–97 need the Organelle and have not been run** — nothing in
Phase 6 has been deployed yet.

### Step 0 — the measurements everything else was built on

- [x] **82. ✅ The ring's CC numbers, measured — and the documented map was wrong twice.** All 41
      ring buttons pressed in order, twice, with identical results both passes.

      ✅ Confirmed as documented: top row **91–98**, right column **89 79 69 59 49 39 29 19**,
      left column **80 70 60 50 40 30 20 10**, bottom row **101–108**.

      ⚠️ **Two corrections.** There is a **second bottom row at CC 1–8**, interleaved with
      101–108 and absent from the documented map entirely; and **CC 90 exists** — the top-left
      corner — where the documentation starts at 91. Only **CC 99** (top-right corner) remains
      untested, and nothing needs it.

      **This is the one that changed a design decision**: see item 83.
- [x] **83. ✅ One SysEx carries 99 colour specs. 120 is REJECTED OUTRIGHT.** Not truncated —
      the entire message is dropped and the surface does not change at all. 64 works, 99 works.

      ⚠️ **SUPERSEDED — the cliff was not real.** This item's conclusion came from probes later
      found broken three ways over (items 105, 107, 109): a clean 120-spec message paints the
      whole surface. `g_grid` now paints indices **1–108 = 108 specs**, and the reason is not
      the extra buttons — an index *outside* the span can never be cleared, because LED state
      survives the Programmer Mode switch. Index 0 stays out and that one is measured (110).
- [x] **84. ✅ The batch SysEx lights the ring as well as the pads.** One message paints the 8×8
      grid and every perimeter button together, addressed by the same Programmer-Mode index.
- [x] **85. ✅ The Launchpad works as a Pd input on the Mac.** Set as MIDI in *and* out device 1.
      **Both entry points now pass the same arguments** — `u_root 17 1` — which they never did
      before. ⚠️ The output order is not optional: `m_launchpad` uses its channel block as the
      **lighting** channel, so input slot and output port must be the same number or every static
      pad comes up flashing.
- [x] **86. ✅ Polyphonic aftertouch confirmed on this unit.** Two pads held together reported
      independent interleaved streams (`44` and `45`), which channel pressure cannot do. Also
      confirms `polytouchin`'s outlet order is value / note / channel.
- [x] **87. ✅ Programmer ↔ Live works. ⚠️ The layout-select command does not.**
      `F0 … 0E 01` and `0E 00` both work. **`F0 … 00 <layout>` with ids 0, 4 and 5 does nothing
      at all** on this unit.

      Three further facts from the same run: Live Mode returns to **Note view** — the device's
      last built-in mode, not a fixed one; **LED state survives the round trip**, so the clear on
      re-entering Programmer Mode is confirmed mandatory; and a **power cycle returns it to
      Live**, so the escape hatch in `ref-midi.md` is sound.

      **Consequence:** `m_launchpad`'s surface-ownership state keys off the Programmer/Live
      toggle rather than a layout table, which is simpler than planned and rests on something
      measured.

### The build, verified against the real patch on the Mac

- [x] **88. ✅ Pad and ring decode.** `pad-43 127` on press, `pad-43 0` on release, `pad-88 64`,
      `lp-cc-91 127`, `lp-cc-108 64` — each on `param` first and `disp` second. **An event on
      channel 17 produced nothing**, which is the gate working. Driven through stand-ins for
      `notein` / `ctlin`, the same technique as item 31.
- [x] **89. ✅ Aftertouch decode, and it never reaches `disp`.** `pad-88-at 40` followed by
      `pad-43-at 70` — each reports its **own** pad, so the `polytouchin` note-before-value trap
      is avoided. Nothing appeared on `disp`, which is deliberate: polyphonic pressure would fill
      the OLED's five param rows for as long as a chord was held.
- [x] **90. ✅ The `mode` bus has a driver.** `xport-5` → `perform mode-5`, `xport-1` →
      `compose mode-1`, `slider-3` correctly silent. **The load seed fires once and a real mode
      arriving at 100 ms suppresses it** — one line, not two. Same "seed only if unheard" shape
      as items 61 and 78.
- [x] **91. ✅ Grid arbitration, priority and TTL — nine frames.** home → mode-4 → mode-6 →
      modal blue → *(mode changed underneath, still blue)* → modal-off revealing **mode-3** →
      alert red → home again by itself. A `warn` produced **no frame at all**.

      ⚠️ **The alert TTL was broken on the first run and the bench caught it.** Both layers
      lowered their flag on expiry but never set the dirty flag, so an expired alert would have
      left the grid **red permanently** — the display simply stopping. The comment in that very
      subpatch already claimed every expiry set it.
- [x] **92. ✅ The ownership gate.** A pad before init → nothing; after init → `pad-44 127`;
      after a `panic` → nothing. Closed before boot, open while we own the surface, closed the
      moment safe-exit hands it back.
- [x] **93. ✅ The first `c_clock` instance in the deployed patch, and an off-by-one it caught.**
      With DSP on, the beat row walks **1→8→1** with no gaps, and the repaint rate is **~2 frames
      per second at 120 BPM** exactly as designed.

      ⚠️ **`c_clock`'s beat-number outlet is ONE-BASED, 1 to 8 — measured, not assumed.** Built
      against a 0-based assumption, beat 8 landed on index 19: a right-column **ring button** lit
      white while the beat row went blank, once per bar. **Seven beats out of eight looked
      perfect**, which is why it took decoding the painted frames rather than watching the
      surface.
- [x] **93b. ✅ Every frame is one SysEx.** Measured at **305 bytes** — 7 header + 99×3 +
      terminator — with the correct header and `247`, verified byte by byte across every frame
      of every run. **Idle with the transport stopped it sends nothing at all.**
      ⚠️ **The number has since changed: the span widened to 1–108, so a frame is now 332 bytes**
      — 7 + 108×3 + terminator. The shape and the assertion are unchanged; only the count moved.

### Still to run — these need the Organelle

- [x] **94. ✅ Measured — 11.7–12.0 %.** Target: **idle CPU at or below 11.2 %**, the
      Phase 5 baseline of 10.2 % plus one point, by `ref-hardware.md` → *Measuring the running
      patch*. Three readings: idle and stopped, transport running with the beat row walking, and
      during a bench alert storm. Expected SysEx rates 0/s, ~2/s and ~6/s.
      **✅ FLOOR TAKEN 2026-08-03, and it is not the answer.** First-ever Phase 6 deploy, patch
      loaded and idle, transport stopped, **no controllers attached** — `aconnect` showed one link
      and only the wifi dongle on USB. Three readings: **10.8 %, 10.8 %, 11.0 %**. UDP out 117–119/s
      (the OLED, flat since Phase 3); load average 0.33 / 0.24 / 0.10.
      ⚠️ **This is a floor and it understates the real cost**: `g_grid` emits nothing when idle and
      stopped, and with no subscriber on the ALSA port the kernel discards what it does send —
      the USB transfer to a real Launchpad is the part that costs. **Phase 6 has therefore spent
      most of its one-point allowance before a single repaint happens**, leaving ~0.2 points.
      Keep it in proportion: **11.2 % is a self-imposed tripwire set as Phase 5 + 1 before Phase 6
      existed**, not a hardware limit, and a load average of 0.33 says the machine is not stressed.
      **✅ REAL READING TAKEN 2026-08-03, WITH THE LAUNCHPAD AND NANOKONTROL ON A USB HUB.**
      ALSA showed 4 links — Launchpad in *and* out, nanoKONTROL in. Transport stopped, DSP on, so
      the beat row was walking and the grid repainting ~2/s.
      **⚠️ OVER BUDGET: 11.7 %, 11.9 %, 12.0 %** against 11.2 %. Load 0.42–0.51, UDP 120/s.
      **The overage is not the span widening and not the frame rate.** Two things were isolated:
      the span went 99 → 108 specs (305 → 332 bytes), which at ~2 repaints/s is ~54 bytes/s and
      cannot account for a point; and `[metro 100]` → `[metro 20]` was measured directly at
      **11.5 %, 11.6 %, 12.0 %** — indistinguishable, one reading lower. The rest is the cost of
      **actually transmitting to real USB hardware** rather than into unconnected ALSA ports.
      **⚠️ The 11.2 % tripwire is not a like-for-like ceiling and should be restated.** It was set
      as "Phase 5's 10.2 % plus one point", and that 10.2 % was measured before `m_launchpad`
      existed and — like the floor above — with nothing on the other end of the MIDI ports.
      ✅ **What item 94 actually exists to prove is PROVED**: the dirty flag gates. If it did not,
      raising the frame clock 5× would have produced 5× the frames and moved the CPU. It did not
      move at all, because the repaint count is bounded by the beat rate and never by the metro.
      That is a stronger result than the number.
      **✅ READING 2 — TRANSPORT RUNNING, 120 BPM, by-hand launch with the bench loaded:**
      **10.6 %, 10.9 %, 11.3 %.** Running the transport did **not** raise CPU — it read *lower*
      than the stopped reading above. The beat row's repaints cost nothing measurable.
      **✅ READING 3 — TRANSPORT RUNNING AT 500 BPM:** **11.7 %, 11.7 %, 11.9 %.**
      That is **+1.0 point for 4.17× the clock rate** — 400 ALSA writes/s against 96.
      ⚠️ **THIS CONTRADICTS ITEM 75's ATTRIBUTION.** Item 75 blamed the Phase 4 → Phase 5 CPU
      doubling (5.3 % → 10.2 %) on the 96 clock writes a second, and marked it ⬜ *not confirmed
      by isolation*. If 96 writes cost ~5 points, adding 304 more should cost ~15. **It cost 1.**
      So the per-message cost is low and the doubling was almost certainly the **DSP** that
      arrived in the same phase, not the MIDI. Worth isolating properly before v0.3 builds on it.
      ⚠️ **THE TRIPWIRE IS FINER THAN THE MEASUREMENT IS REPEATABLE.** Between-session drift is
      ~1 point — menu-loaded vs by-hand-with-bench differ by about that — against an effect being
      resolved at 0.2. **Restate the budget with stated conditions, or stop treating it as a gate.**
      ⬜ An alert-storm reading was not taken separately: an alert is one repaint, not a rate.
- [x] **94b. ✅ The clock is accurate at the top of its range.** `u_map` maps knob 1 across 10–500
      BPM and the OLED footer reached **500**. Driven to the bench's beat-counter step with the
      knob at maximum, a machine-timed ten-second window counted **BEATS: 84** against 83.3
      expected — 504 BPM equivalent, within one beat. **The row LOOKING slow at 500 is an
      intuition error, not a fault:** the row shows beats and there are 8 to a bar, so a full
      sweep takes 0.96 s. One sweep a second is what 500 BPM looks like spread over eight pads.
      ✅ **And the LEDs were confirmed separately**, which the beat count could not do on its own:
      tapping tempo on a metronome in time with the walking row matched the BPM on the OLED. So
      the row is on the BEAT, not the bar. The suspicion that it ran slow — `c_clock 1 8` gives 8
      beats to a bar, so 500 BPM is 62.5 bars/min ≈ one sweep a second, which reads as sluggish —
      was an intuition error about what 500 BPM looks like spread across eight pads.
- [x] **111. ⚠️✅ A PHANTOM `lp-cc-N` ON EVERY NANO MOVE — a Phase 6 bug that shipped, found
      2026-08-03, fixed in `wire.sh`.** Moving one nanoKONTROL fader on the device published
      **both `slider-1` and `lp-cc-1`** to `param` and `disp`. Cause: mother's own
      `/root/fw_dir/scripts/alsaconnect.sh` wires the **lowest-numbered** MIDI client to Pd's
      Midi-In 1, and the nanoKONTROL enumerates at client 28 against the Launchpad's 32 — so
      every boot put the nano on `m_launchpad`'s channel block.
      ⚠️ **NO Pd-SIDE FIX IS POSSIBLE.** Once two devices share Midi-In 1 they are both
      genuinely channel 1; `m_launchpad`'s channel test is correct and powerless. It has to be
      undone at the ALSA level.
      ✅ **Fixed with two `aconnect -d` lines in `wire.sh`** — for the nano and the SP-404 —
      which costs **no new fork**, since `wire.sh` already runs once per load. Verified after
      deploy: Midi-In 1 shows `32:0` only, Midi-In 2 shows `28:0` only.
      ⚠️ **Invisible on the Mac**, which has explicit device slots and no mother. That is why
      Phase 6 passed 25/25 twice without catching it, and it is the clearest argument yet that
      a Mac-green bench does not mean a phase is done.
      ⚠️ It also **invalidated an earlier conclusion**: this link was first seen after a replug
      and written off as inert, because a test run *after a panic* showed no `lp-cc`. Ownership
      was 0 then and `m_launchpad` gates on **channel AND ownership** — two spigots, not one —
      so that test could not have shown anything either way.
- [x] **112. ✅ THE REPLUG WATCHDOG — BUILT AND CONFIRMED ON HARDWARE.**
      `m_launchpad` → `pd watchdog`. **Two mechanisms, because the platforms fail differently:**
      a **heartbeat** re-asserting Programmer Mode every 2 s (the Mac cannot be fixed by polling —
      the device answers the inquiry in *either* mode, so a replug is undetectable there), and a
      **poll** of the universal device inquiry whose silence detects loss on the Organelle, where
      the replug destroys the ALSA subscriptions outright.
      ✅ **Measured on the device before building:** `[sysexin]` fires (40 polls, 40 replies, no
      misses); re-asserting Programmer Mode while already in it **does not disturb the grid** —
      the assumption the heartbeat rests on; `wire.sh` costs **133 ms**, is idempotent, and does
      restore the link and resume polling; **ten forks back to back produced no audio complaint**
      on Pd's console, which is what allows the recovery to fork at all.
      ⚠️ **`$0-want` is not `$0-own`.** own = the surface IS ours; want = we still INTEND it.
      Without the split, a panic hands the device back and the heartbeat grabs it again 2 s later.
      ⚠️ **THE ARMING GATE IS LOAD-BEARING, and the assert layer is what found it.** The first
      build let three missed polls drop ownership unconditionally — so on any machine with no
      Launchpad (including the headless gate) the grid went dark 6 s in. **7 of 24 checks failed.**
      Ownership can now only be dropped after a reply has actually been seen, so a detector that
      has never proven it works can never blank the grid. No hands-on bench would have caught it.
      ⚠️ **The first recovery cadence was useless and hardware proved it**: 3 attempts 2 s apart
      meant giving up **12 s** after the unplug, and the very first test replugged at 10–12 s and
      missed the window. Now 8 attempts — first at ~14 s, then every 8 s, stopping at ~70 s.
      ✅ **CONFIRMED 2026-08-04 on the device.** Unplugged, replugged: the Launchpad returned to
      **Programmer Mode by itself**, `aconnect` showed **4 links** with the Launchpad wired both
      directions again, and the error log stayed **empty** — it recovered inside the window and
      never reached the give-up path. **And it came back CORRECT, not merely lit**: one green mode
      lamp with five dim beside it, the beat row walking, pads reporting `pad-NN`, and the nano's
      transport keys still moving the lamp. That last part matters — it means `g_grid` repainted
      from live arbiter state rather than restoring a stale frame.
      ✅ **THE GIVE-UP PATH IS CONFIRMED TOO.** Left unplugged past the window, `309000 fail
      m_launchpad grid-lost` appeared in the durable log on the SD card — **once**, not as a
      repeating stream, so `sel 33` fires exactly on the boundary. Replugging afterwards did
      **not** recover it: `aconnect` still showed 2 links with the Launchpad unconnected. The
      bound holds in both directions — it stops forking, and it stays stopped. Recovering from
      there needs a patch reload, which is the deliberate trade.
      ✅ `/proc` polling could NOT have avoided the fork: `[text read]` fails on `/proc/asound/cards`
      with `lseek: Invalid argument`, because Pd seeks to size the file.
- [ ] **95. ⬜ Full rig: three controllers plus the wifi dongle, powered at once.** Still item 5,
      still blocked by the cable shortage. **A marginal hub presents as intermittent dropouts, not
      an obvious failure, so if Phase 6 misbehaves on the device suspect the hub before the code.**
      ✅ **PARTIAL 2026-08-03: TWO controllers plus the dongle, on a hub, held up.** Launchpad and
      nanoKONTROL through a USB hub alongside the wifi adapter, across two full sessions, a
      25-step bench run, a hot replug and sustained 500 BPM clock — **no dropouts and no MIDI
      misbehaviour attributable to power.** The SP-404 is the one still untried.
- [x] **96. ✅ The safe exit after the lift — PASSES, and the obvious test is the wrong one.**
      Confirm the Launchpad returns to Live Mode when the patch ends. The code moved from `u_init`
      to `m_launchpad` this phase.
      ⚠️ **`killall pd` DOES NOT TEST THIS.** Tried 2026-08-03: the Launchpad stayed in Programmer
      Mode with a frozen beat row. That is **not** a failure of the safe exit — it hooks
      `[r quitting]`, which only `mother.pd` sends, right before mother itself quits Pd. A signal
      from the shell never produces it and Pd 0.49 has no `closebang`.
      ✅ **TESTED THE RIGHT WAY 2026-08-03: opening another patch from the Organelle's own menu
      returned the Launchpad to Live Mode.** That is mother's shutdown path and the only one the
      design covers. The lift from `u_init` to `m_launchpad` did not break it.
      ✅ **What the wrong test DID establish, and it matters more:** any exit that is not mother's
      strands the device — a crash, power loss, or `killall pd`, which the by-hand console
      workflow in [ref-conventions.md](ref-conventions.md) does every time. The Settings menu is
      locked out in Programmer Mode, so the front panel cannot recover it.
      ✅ **Recovery needs no power cycle and no Pd**: `tools/lp-live.sh` sends the Live Mode SysEx
      with `amidi`, looking the port up by name. Measured bringing a stranded device straight back.
      ✅ `deploy.sh` is unaffected — it loads via mother's `/loadPatch`, so `quitting` fires.
- [x] **97. ✅ The boot sequence in its real order.** Measured 2026-08-03 on the by-hand console,
      twice. Every boot reported `wire.sh: 4 connections`, `m_launchpad-channel: 1` and
      `m_nano-control-channel: 17` — the channel blocks land correctly, and they did so **even
      though the ALSA client numbers had swapped between sessions** (Launchpad 28/nano 32 one
      time, the reverse the next). That is `wire.sh` connecting by NAME doing exactly the job its
      header says it exists for. `errlog-roll` carried the previous session's lines, and **no
      `/sdcard/cut-it-err.cur: write failed` appeared**, so the durable error log is real here.
      ⬜ The OLED half — `modal launchpad` appearing during boot — was read from the console
      rather than watched on the screen.

### The Phase 6 procedure, in order

**Do every Mac step first. Then deploy once.** Expected result is stated *before* each action,
including the steps whose correct result is that nothing happens.

**Mac, one-time setup.** Media → MIDI Settings: **Launchpad as input device 1 AND output device
1**, nanoKONTROL as input device 2. ⚠️ **Both lists matter** — `m_launchpad` uses its channel
block as the lighting channel too, so if the input slot and output port differ, every static pad
comes up *flashing* and it looks like a bug in `g_grid`. Both `m_` layers print the block they
configured about two seconds after load; read those before suspecting anything.

**Mac, static.** `python3 tools/pd-layout-check.py "Cut It"/*.pd` — every line must say
`0 problems`. Then the syntax check on **both** entry points; **silence is the pass**.

**Mac, boot.** Open `Cut It/main-dev.pd` and tick `enable-DSP`. Expect, in order: `booting` →
`wiring` → `launchpad` → the two meters, and the footer changing to `120-bpm` at about four
seconds. **At the launchpad stage the whole Launchpad repaints at once** — that single frame is
the clear. Expect one bright green lamp at the left of the top row, five dim beside it, and a
single white pad walking the bottom row twice a second. ⚠️ **If the white pad does not move, DSP
is off** — `c_clock` hangs off `threshold~`.

**Mac, the pads.** Press pads: each reports `pad-NN` and its velocity on the OLED, `11` at the
bottom left and `88` at the top right. Press ring buttons: `lp-cc-NN`. **Now press a pad hard and
hold it: the OLED must show NOTHING new.** Pressure goes to `param` only, deliberately, because a
four-finger chord would otherwise fill all five param rows for as long as you held it.

**Mac, the modes.** Press each of the nanoKONTROL's six transport keys. Expect the bright lamp to
move to that position and the other five to go dim. That is the `mode` bus finally having a
driver.

**Mac, the tempo.** Sweep the panel's `knob1`. Expect the white pad to walk faster and the footer
to follow. The Launchpad's own flash and pulse animations track the same clock for free.

**Mac, the bench.** `pd -path "Cut It" "Cut It/main-dev.pd" tools/phase6-bench.pd`, DSP on, and
watch **the Launchpad, not the screen**. Sixteen steps, ten seconds each, about three minutes.
Steps 12, 13 and 15 will ask for hands. ⚠️ **Step 14 raises a panic and the grid does not come
back** — that is known and deliberate; reload to continue.

**Then `./deploy.sh`** — nothing was deleted this phase, so a plain deploy is enough — and do it
again on the hardware, where the additions are:

1. **The boot sequence in its real order** (item 97). `loadbang` fires before ALSA exists, so this
   is the first time the wiring, the Programmer Mode SysEx and the first paint happen for real.
   Watch for `modal launchpad` on the OLED and the grid lighting immediately after it.
2. **The safe exit** (item 96). `killall pd` over SSH mid-session. **The Launchpad must return to
   Live Mode on its own.** This is the one that costs a power cycle if it is wrong, and the code
   moved files this phase. ⬜ If it fails, the device's own display will not come back and the
   Settings menu stays locked out until you replug.
3. **CPU and the SysEx rate** (item 94), by `ref-hardware.md` → *Measuring the running patch*.
   Three readings — idle and stopped, transport running, and during the bench's alert step.
   **The budget is 11.2 %**, against Phase 5's 10.2 % idle.
4. **Full-rig power** (items 5 and 95). Three controllers plus the wifi dongle at once, for the
   first time ever. ⚠️ **A marginal hub presents as intermittent dropouts, not a failure — so if
   anything is flaky, suspect the hub before the code.**
5. `./tools/fetch-errors.sh` afterwards. The only errors the run should have raised are the two
   `u_bench` ones the bench sends on purpose.

---

## Session 8 — the test suite itself

**Items 98–109.** The benches were reworked to be **stepped by hand** rather than driven on a
ten-second timer, because the console text and the physical device used to move at the same
moment. Building that turned up three defects in the measuring rigs and one in `g_grid`; then the
Launchpad turned out to answer a device inquiry, which a `ref-` doc had flatly denied; and then
the test that had "measured" the SysEx length limit turned out to be sending illegal bytes.

⚠️ **Two long-standing findings were overturned here, both had been written down as facts, and a
third had been "measured" three times by three broken rigs and was FLATLY BACKWARDS.** The lesson
is the one this project keeps relearning: *a measuring rig is code*, and a rig that cannot say what
it did lets a bug pass for a result. Four separate flaws in one small diagnostic patch — indices
past 127, a two-element message sent as one, a byte counter that printed 368 times, and every
button painting the same colour so the second one was invisible — each produced a confident wrong
answer.

### The Launchpad CAN talk back — and the docs said it could not ✅

`tools/lp-readback.pd`, run on the Mac. **That probe has since been DELETED** — items 98–110 below
are everything it established, and nothing else depended on it. ⚠️ **`ref-midi.md` stated as fact that nothing in the rig
transmits SysEx to Pd. That is false.** The sentence was an inference from two unrelated
measurements — the nanoKONTROL's stream and Roland's chart for the 404 — and the Launchpad had
never been checked.

- [x] **98. ✅ `[sysexin]` exists AND fires in Pd 0.49.** It had never been instantiated on this
      build before. Both `[sysexin]` and `[midiin]` delivered every byte of the reply.
- [x] **99. ✅ THE LAUNCHPAD ANSWERS A UNIVERSAL DEVICE INQUIRY.** Send `F0 7E 7F 06 01 F7`:

      ```
      F0 7E 00 06 02 | 00 20 29 | 23 01 | 00 00 | 00 04 06 05 | F7
                       Novation   family  member   firmware
      ```

      `00 20 29` is the same manufacturer ID that opens every Launchpad SysEx header.

      **This is the one with consequences.** A device that answers is a device Pd can notice the
      *absence* of — poll the inquiry, expect a reply — which is the only route to fixing the
      replug hazard. Costs one round trip per poll against the 96 ALSA writes a second the clock
      already makes. Design tracked in [plan-v03.md](plan-v03.md).
- [x] **100. ✅ IT DOES NOT ANNOUNCE A MODE CHANGE.** Returned to Live Mode, then changed between
      Live modes **by hand on the device**: the console stayed completely silent.

      ⚠️ The first version of this step was impossible and had to be rerun. It asked for a
      front-panel mode change *while in Programmer Mode*, and **Programmer Mode locks out the
      device's own buttons** — which this repo already documented. Pressed there they are ordinary
      CC: `176 93 127` then `176 93 0`.

      **Consequence: there is nothing to listen for, so presence detection has to POLL.**
- [x] **99b. ✅ The inquiry still answers after an unplug and replug.** Byte-for-byte the same
      reply. Pd did **not** lose the device across the replug on the Mac.

      **This is the green light for the replug fix**: poll the inquiry, and a Launchpad that has
      gone and come back answers again. ⬜ Still worth confirming on the Organelle, which reaches
      the device through `aconnect` by name rather than CoreMIDI.
- [x] **101. ✅ 99 specs from index 10 paint cleanly.** Everything green from the top row down to
      the bottom row of the ring, with **the second bottom row at CC 1–8 left dark** — the painted
      span working exactly as designed. Reproduced across two runs, and it correctly overwrote a
      pad that a previous run had left flashing.
- [x] **105. ✅ THERE IS NO CEILING AT 120. A 368-byte message of 120 specs PAINTS — and item 83's
      "rejected outright" was wrong, along with two later attempts to confirm it.**

      120 specs from index 1, colour red, lit **every button on the surface including the
      undocumented second bottom row at CC 1–8**. Reproduced across a patch reload.

      | Attempt | What it actually sent | What it looked like |
      |---|---|---|
      | `lp-step0.pd`, and item 83 | 120 specs from index 10 → **indices 10–129** | "rejected outright" |
      | `lp-readback.pd` v1 | same | one pad left **flashing** |
      | `lp-readback.pd` v2 | bare `120` where `start count` was expected | **nothing at all** |
      | `lp-readback.pd` v3 | `1 120` — every index ≤ 127 | ✅ **the whole surface painted** |

      ⚠️ **MIDI data bytes are 7-bit.** Index 128 is `0x80`, a Note Off **status** byte, so the
      first two attempts cut their own SysEx short and the tail was parsed as channel-voice
      messages. Index 129 is `0x81` — **Note Off on channel 2, the Launchpad's *flashing*
      channel** — addressing note **21**, which is the colour byte in every spec. That is why it
      was always the same pad, row 2 column 1: **it was named by a byte meant to be a colour.**

      ⚠️ **The third attempt was worse because it looked like a clean result.** A bare `120`
      reached `[unpack f f]`, which fires only its left outlet — so *start* became 120 and *count*
      kept whatever the previous button left. Pressed after step 3 it painted 99 specs from index
      120 (indices 120–218, almost all status bytes) and the pad blinked again; pressed on its own
      it painted **zero specs**, and an empty SysEx is indistinguishable from a rejected one.
      **A bug read as a measurement.**

      ✅ **The engine is verified end to end**: 305 / 368 / 326 / 332 bytes on the wire, each
      carrying only its own colour, driven through the real message boxes. The patch prints
      `PAINT-ASKED` and `PAINT-SENT-BYTES` on every press, so an empty message can never again be
      mistaken for a rejection.

      ⚠️ **A fourth flaw showed up only once the test finally worked**: every button painted the
      same green, so after one of them covered the surface the next was **invisible**, and "no
      change" read as "the device refused it" all over again. The buttons now paint distinct
      colours — green, red, blue, yellow — so each press says something on its own.

      **Novation documents "up to 106" 📄 and this unit exceeds it.** Whether there is a limit
      further up is unknown and now uninteresting.
- [x] **109. ✅ THE WHOLE SURFACE FITS IN ONE MESSAGE.** Implied by 105 and stronger than it
      looks: **CC 101–108 is the first bottom row, i.e. specs 101–108 of the message**, and those
      lit — so at least 108 specs applied out of 120.

      **The design consequence: widening `g_grid`'s span to cover CC 1–8 would cost one SysEx,
      not two.** Nothing wants those eight buttons yet, so nothing changes today — but the
      constraint everyone believed was there is not there.
- [x] **106. ✅ Nothing is ever volunteered.** The device says nothing at load, nothing when Pd
      sends it into Programmer Mode or back to Live, and — with item 100 now answered — **nothing
      when a human changes its mode either.** It speaks only when asked.

      ⚠️ An earlier draft of this item claimed the same thing on much thinner evidence: at that
      point every event in the run had been *initiated by Pd*, so all that was actually measured
      was that Pd's own commands go unacknowledged. Item 100 is what closed it.
- [x] **107. ✅ A malformed SysEx leaves the pipe needing one throwaway message.** After the
      over-long paint, the first click of *"return to Live Mode"* did nothing and the second
      worked — reproducibly, both runs. The unterminated SysEx from item 105 is still open
      somewhere between Pd and the device, so the next `F0` only closes it and the one after
      starts a clean message. **Not a bug in the mode-change path**, which works first time when
      nothing malformed precedes it.

### Passed on the Mac

- [x] **102. ✅ An abstraction cannot shadow a built-in class.** A `midiout.pd` on the search path
      is **ignored**; the same file as `t_midiout.pd` is used. Measured both ways.

      This is why `mac-stubs/` works for `[shell]` — an *external absent on the Mac*, so Pd falls
      through to a file — and why the assert harness has to **rewrite the object boxes** in a
      scratch copy instead. `Cut It/` is never touched.
- [x] **103. ✅ The headless assert layer: 29 checks, 0 failed.** Frame shape and the **1–108**
      span, the mode lamp index, the modal claiming all **108** specs, `fail` painting red and
      `warn` painting nothing, the alert expiring back to the modal *underneath* it, the beat row
      never leaving 11–18, silence after a panic, and `m_launchpad`'s Programmer and Live SysEx.
      ✅ **Re-run clean after the span widening, the `metro 20` change and the beat-store seed** —
      29 checks, 0 failed, and the **NOTE is gone**: seeding the beat store at 1 removed the stray
      index-10 light the layer had been reporting.
- [x] **104. ✅ The assert layer has been proven to fail.** Reintroducing the one-based beat bug in
      a scratch copy — the beat-row offset back to `+ 11` — reports
      `lit outside every region: [(19, 3)]` and exits 1.

      ⚠️ **The three `home-*` checks still passed under that mutation.** That is precisely why
      *seven beats out of eight looked perfect*: only the six-second beat-row window catches it.
      **A gate that cannot fail is worth nothing** — re-run the mutation after any change to the
      analyser.

### Three defects in the measuring rigs, and one in the patch

- ⚠️ **`phase6-bench.pd`'s only automated assertion never fired.** `[r $0-zero]` and `[r $0-read]`
      existed, the comment beside them claimed the tempo steps drove them, and **nothing anywhere
      sent to either name.** Same shape as `phase5-bench`'s `[r $0-say]` that was never connected
      to its `[print]`, one phase later. Now driven from the step table.
- ⚠️ **`phase5-bench.pd` had the comma bug its own family warns about.** Two escaped commas inside
      one `PASS IF`, so that line printed as **three fragments**. `\,` satisfies the .pd *parser*;
      a message box still treats the comma atom as a separator. Re-measured here rather than
      assumed. It is the only step text that changed in the conversion.
- ⚠️ **Two of the first assertions I wrote were wrong, not the patch.** One window ran past the
      point where DSP was enabled so "idle" was not idle; another read the *last* frame of a
      window the 2 s alert TTL had already expired inside. **A measuring rig is code**, and both
      would have reported a healthy patch as broken.
- ⚠️ **`g_grid` lights LED index 10 before the first beat arrives.** The beat store starts at 0 and
      `0 + 10` is a left-column ring button, so the very first frame has a stray white light.
      **Cosmetic and Mac-only** — on the device mother enables DSP at 200 ms, so beats are already
      flowing by the time ownership rises at ~3 s. Reported as a `NOTE` by the analyser rather than
      a failure, and tracked in [plan-v03.md](plan-v03.md).

---

## Session 9 — Phase 7, the phone status link

Step 0 first, on the Mac, before anything was built on it. **Two of the four overturned something**
— which is now the sixth phase running where that has been true.

- [x] **113. ✅ `oscformat`'s creation args are path segments, and both prototype spellings are
      identical.** `tools/status-display/main.pd` uses **two conventions in one file** —
      `[oscformat /cutit/hb]` and `[oscformat cutit param]` — and since the help patch shows
      `[oscformat cat horse pig]` → `/cat/horse/pig`, the first looked like it had to be producing
      `//cutit/hb`.

      It is not. Measured through `[oscformat] → [oscparse]`, the two forms are **byte-for-byte
      the same**: `47 99 117 116 105 116 47 104 98 0 0 0` — `/cutit/hb` with three bytes of null
      padding. Pd splits the args on `/` itself. **The prototype's inconsistency is cosmetic, so
      do not "fix" it and expect a change.**

      Also confirmed in the same run: `,sfs` (`/cutit/param chop-size 43 dB`, 44 bytes), `,s`
      (`/cutit/status v0.2-ready`, 32 bytes) and `,fsss` (`/cutit/alert 3 warn u_init
      launchpad-silent`) all round-trip, and a param whose **value is a symbol** works — so
      `mode-2 compose -` is legal on the wire.

- [x] **114. ⚠️ ✅ A UDP `connect` to a port with nothing listening SURVIVES EXACTLY ONE DATAGRAM,
      and then dies in silence. This is the measurement that changed the design.**

      Twenty datagrams at 5 Hz to `127.0.0.1:9999` with no listener:

      ```
      CONN: 1          <- the connect SUCCEEDS
      SENT: 0          <- the first datagram goes out
      error: recv: Connection refused (61)
      error: netsend: Bad file descriptor (9)
      CONN: 0          <- the socket is torn down
      SENT: 1 .. 19    <- nineteen more sends, ALL SILENTLY DISCARDED
      ```

      The ICMP port-unreachable that comes back kills the socket. **After that, `send` reports
      nothing and delivers nothing.** That is the ordinary case of a phone on wifi with PdParty
      closed — and without a reconnect the link would be dead for the whole session with three
      lines on a console the device does not have.

      ✅ **A fresh `connect` revives it**, and each retry delivers exactly one more datagram before
      dying again. Once a listener appears the next reconnect **sticks** — 22 datagrams delivered,
      no further errors. So the retry loop works, and it is mandatory.

      ⚠️ **The retry must be gated on the connection state.** Reconnecting an already-open socket
      prints `error: netsend_connect: already connected` **every time**. `u_net`'s spigot starts
      open (so a connect that never came up at all still retries) and the first success closes it.

      ⚠️ **And the warning must fire once per load, not once per retry** — `u_err` writes its log
      through a shell fork, and Phase 4's rule is one fork per load, never one per event.

      ⬜ Measured on macOS. Linux behaves the same way for connected UDP sockets, but **this has
      not been confirmed on the Organelle** — item 118.

- [x] **115. ✅ `disp` is SILENT at rest, and one moving control puts 402 messages a second on it.**

      Tapped with `[r disp] → [print]` beside `main-dev.pd`. After the boot sequence settles
      (`in-l`/`in-r`, `led stopped`, three `modal` stages, `status v0.2-ready`, `status 120-bpm`)
      the bus goes **completely quiet** — zero messages over nine seconds.

      A 200-step sweep of knob 1 over one second produced **402 messages: 201 `og-knob-1` and
      201 `status`**. Two facts fall out, and one of them was not obvious:

      - **`status` moves at control rate.** Knob 1 is master tempo and `u_tempo` writes the BPM
        into the footer, so the footer alone is half the flood. **It needed its own rate limit**,
        which is not something the plan had said.
      - **The level meters are the entire resting content of the bus** once there is audio, at
        ~20/s and continuously changing. Forwarding them would have spent the whole budget on
        something the phone does not draw, which is why `u_net` drops them.

- [x] **116. ✅ The headless gate, and the proof it can fail — obtained for free.**
      `./tools/phase7-assert.sh`, 25 checks, ~25 s, no phone and no hardware.

      `u_net` was built **plumbing-first with no coalescer**, and that build failed **exactly the
      three rate ceilings** — 401, 802 and 401 packets — while every shape check passed. Adding
      the per-name store took those to **42, 84 and 42**, and all 25 pass. Total datagrams over
      the run: **1698 → 262**.

      **No mutation had to be invented afterwards**, which is the one weakness of
      `phase6-assert.sh`, whose ability to fail had to be demonstrated by reintroducing a bug.

      | Window | Before the store | After |
      |---|---|---|
      | one name swept, 401 events | 401 packets | **42**, last value 400 ✅ |
      | two names swept together | 802 packets | **84**, *both* last values 400 ✅ |
      | `status` swept, 401 events | 401 packets | **42**, last value `400-bpm` ✅ |
      | idle | 0 param | 0 param, heartbeat at 2 Hz ✅ |

- [x] **117. ✅ The phone, end to end from the Mac — the trailing edge survives on real hardware.**
      `main-dev.pd` with `u_net 192.168.1.5 8000`, sweeping `chop-size` to **777** over three
      seconds and then stopping.

      **The phone showed `chop-size` / `777` / `NO-LINK`.** All three halves of that are the
      result: the right parameter name, **the last value of the sweep and not one part-way
      through it**, and the link detector firing once the traffic stopped.

      ✅ The Mac half agrees: `connecting to port 8000`, `u_net-target: 192.168.1.5 8000`, and no
      `netsend` errors for the whole run — so the socket stayed up against a real listener, which
      is the other half of item 114.

      ⚠️ **This ran against the PROTOTYPE scene**, which draws only `/cutit/param` and `/cutit/hb`.
      `status` and `alert` were on the wire and correctly ignored by a scene that has no branch for
      them — which is the right failure, but it means neither has yet been seen rendered.

- [x] **118. ✅ Phase 7 on the Organelle — 15/15 on `phase7-bench.pd`, and the cost is 0.2 points.**
      Measured 2026-08-04 with the nanoKONTROL and Launchpad attached.

      | | Phase 6 | Phase 7 | |
      |---|---|---|---|
      | pd CPU | 11.7–12.0 % | **12.0–12.1 %** | `u_net` costs about **0.2 points** |
      | UDP out | 120/s | **121–125/s** | predicted +4 — heartbeat 2/s plus alert state 2/s |
      | load | 0.42–0.51 | 0.29–0.51 | unchanged |

      ⚠️ **`phase6-cpu.sh` reports OVER BUDGET and that is the script being stale, not a
      regression.** Its 11.2 % budget is Phase 5's baseline plus one point; **Phase 6 already
      exceeded it** at 11.7–12.0 %. The number that mattered was the UDP rate and it landed inside
      the predicted band.

      ⚠️ **A reading taken across a `deploy.sh` reload is garbage** — it caught a dying pid and
      reported `pd is not running` followed by 0.0 % CPU and 98/s. Let the patch settle first.

      **What the bench proved that the Mac could not:**

      - **The reserved selectors are inert, and each was confirmed by a DIFFERENT surface
        reacting.** `grid modal 45` turned the Launchpad fully blue while the phone did not move;
        `led running` turned the aux button green while the phone did not move. **That is the
        distinction the steps exist for** — "nothing happened on the phone" otherwise cannot be
        told apart from "the message never arrived".
      - **The trailing edge on a real fader.** Swept hard and stopped mid-travel at **88**, and the
        phone settled on 88 rather than a value from inside the sweep. ⚠️ **Stopping at an endpoint
        proves nothing** — the first attempt stopped at 127, where "settled correctly" and "stuck at
        the maximum" are indistinguishable.
      - **Real instrument data reached the phone**: the status row read `260-bpm` off the physical
        position of knob 1, through `u_map` → `u_tempo` → the footer → `u_net`.
      - **The alert persisted for 12 s** with nothing re-sending it, while the OLED's copy had long
        since timed out. The two surfaces disagreeing is the design.

- [x] **119. ✅ ⚠️ THE ICMP TEARDOWN HOLDS ON LINUX/ARM, AND THE RECONNECT RECOVERS THE LINK.**
      Item 114 was measured on macOS against **loopback**, and generalising it to "a phone on wifi
      with PdParty closed" was an inference. It is now measured directly.

      With PdParty **fully quit**, `/tmp/bench.txt` shows the cycle repeating every five seconds:

      ```
      connecting to port 8000
      error: recv: Connection refused (111)      <- errno 111 on Linux -- it was 61 on macOS
      error: netsend: Bad file descriptor (9)
      warning: 68 removed from poll list but not found
      ```

      `netstat -un` showed the socket **gone entirely**. Reopening PdParty recovered it with
      nothing touched on the Organelle: **12 connect attempts, 11 refusals, the 12th stuck**, and
      the socket back to `ESTABLISHED`.

      ✅ **`net-link-down` was raised exactly ONCE across the whole outage**, not once per retry —
      the warn-gate spigot working. Eleven forks into `/sdcard` would have broken Phase 4's
      one-fork-per-load rule.

      ✅ **The instrument played straight through eleven socket teardowns** with no audio glitch and
      nothing on the OLED. That is the fire-and-forget requirement met under real failure.

      ✅ **AND THE ALERT ABOUT THE OUTAGE SURVIVED THE OUTAGE.** On reconnect the phone displayed
      `warn` / `net-link-down` — an error raised while the phone was switched off, delivered
      afterwards because the alert is held as state and repeated on every heartbeat. **Sent as an
      event it would have been lost forever.** This is the clearest demonstration in the project of
      why the state-never-events rule is not a stylistic preference.

- [x] **120. ✅ PdParty's own lifecycle, which is not what it looks like.** Three facts, all
      measured, and the first one cost a wrong conclusion mid-session:

      - ⚠️ **Backgrounding PdParty does NOT drop the link.** iOS keeps the app running — the orange
        pill around the clock — so **UDP 8000 stays bound and the socket stays `ESTABLISHED`**. A
        first attempt at item 119 concluded the teardown did not happen on Linux; it had simply
        never been tested, because the app was still listening. **Only a full quit from the app
        switcher closes the port.** Operationally this is good news: the display survives tabbing
        away.
      - **PdParty binds 8000 whenever the app runs, with or without a scene open.** So the
        Organelle's link recovering proves *the app* is alive, not that anything is being drawn.
      - ⚠️ **The WebDAV server must be started by hand and does not survive an app restart.** With
        the app open and demonstrably listening on 8000, port 9000 refused the connection and
        `curl -T` failed with exit 7. See [ref-display.md](ref-display.md).

- [x] **124. ✅ ⚠️ The iPhone's notch covers the edge of the scene, and PdParty does not inset for
      it.** Found by eye on the device, not by any test. In landscape the speaker and camera cover
      about **44 points — 22 canvas units** — off one end of a full-width row, silently.

      Fixed by insetting **one** side rather than both: content runs `x = 4` to `x = 426`, leaving
      the margin on the right, because **turning the phone chooses which edge the notch lands on**.
      Symmetric margins would have cost 26 units of width for nothing. The bottom keeps 17 units
      clear of the home indicator. See [ref-display.md](ref-display.md).

- [x] **121. ✅ A PHONE THAT JOINS MID-SESSION SEES BLANKS — fixed, see item 123.** Found by reopening the scene after
      item 119: it showed `READY` and empty value and status rows, because **parameters and status
      are only sent when they change.** The alert did not have this problem — it is repeated on
      every heartbeat — and the OLED does not either, because it redraws from held state every
      frame. **`u_net` is the only surface where a late-joining viewer sees nothing until something
      moves.**

      Not a bug against any stated requirement, and harmless mid-performance since the next control
      movement fixes it — but opening the phone and seeing an empty screen is exactly the moment you
      most want it populated. **Found by hands, in the ordinary act of reopening a scene**, which no
      assertion in the headless gate was looking for.

- [x] **123. ✅ The late-join gap is closed, and the gate caught the change before the device did.**
      Item 121's fix: `u_net` keeps a last-sent slot for the parameter and the status and re-sends
      both every **2 s**, the same trick the alert already used. Deployed and measured — **UDP
      124/s**, inside the 121–125 band already recorded, so the cost is below the noise floor.

      ✅ **Banging an empty store needed no has-it-ever-fired flag.** Measured: it emits a valid
      `/cutit/param` carrying no arguments, and on the phone that reaches `list split 1`'s
      **too-short** outlet, so neither the name nor the value cnv is touched and nothing errors.
      The *status* store carries a dash as its creation argument instead, because its branch has no
      such guard.

      ⚠️ **`phase7-assert.sh` failed 7 of 25 checks the moment the repeat existed**, and every one
      was a check asserting *zero packets in an idle window*. **Those were proxies, and they were
      loosened into properties rather than into nothing**: the gate now asserts that **no reserved
      selector ever becomes a parameter NAME** — which is what the counts were standing in for all
      along — plus that an idle window's traffic is the repeat and only the repeat, and that each
      repeat carries an identical value rather than inventing new data. **28 checks now, and it is
      a stronger gate than the one that passed before the change.**

- [x] **122. ✅ A DIGIT FOLLOWED BY A FULL STOP IS A FLOAT, and the stop vanishes from bench text.**
      `43.` in a `PASS IF` string printed as `43` — Pd parses the atom as the number 43. Same family
      as the comma trap that splits a line into fragments, but **cosmetic rather than structural**:
      it loses punctuation, it does not mangle the message.

      ⚠️ **It is pre-existing and already present in hardware-verified benches** — one occurrence in
      phase 5 and **six in phase 6**, all printing without their full stops and never noticed.
      **The phase 3–6 tables are deliberately NOT reworded**: they are verified, `bench-verify.py`
      gates on them matching, and the defect changes no step's behaviour. Only `STEPS7` is written
      around it, and `bench-gen.py` warns rather than asserting — a hard assertion would refuse to
      generate the four existing benches.

---

## Session 10 — Phase 8 Step 0, state and presets

Step 0 before anything was built on it, as every phase has done. **Six of the eleven items below
correct something a document asserted**, and one killed a hypothesis this session had invented.
Neither of the two design forks fired, so the `u_state` design stands as planned.

Most of it was measured **without disturbing the running patch**: a second Pd launched with
`-nogui -noaudio -nomidi` opens no ALSA device and touches no Launchpad, so it can be run over
SSH while the instrument is live. ⚠️ It must **quit itself** — `killall pd` would take the running
patch with it, and `-send "pd quit"` returns before any `[del]` fires.

- [x] **135. ⚠️ THE SAVE BUDGET IS 250 ms, NOT 500 — the two scripts disagree and only one was
      ever read.** `save-patch.sh` sleeps `.5`, but **`save-new-patch.sh` sleeps `.25`**.
      [ref-conventions.md](ref-conventions.md) and the Phase 8 plan both stated 0.5 s as *the*
      budget. **Design against 250 ms**, which is the smaller of the two and the one a preset
      workflow uses most.

- [x] **136. ⚠️ THE MENU PATH IS `Storage → Save`, AND THE DOCS SAID `System → Save`.** There is no
      Save in the System menu; **Storage is a top-level menu** and holds Eject, Reload, Save and
      Save New. The `<-- System` string sitting beside them in the `mother` binary is a *back
      label*, and reading it as evidence of nesting was wrong. **This cost a wasted trip to the
      device** — the instruction was followed exactly and the menu item did not exist.

- [x] **137. ✅⚠️ `[r saveState]` FIRES — AND IT CARRIES A BANG, NOT `1`.** Seen arriving for the
      first time, twice, once per Save. `save-patch.sh` sends `/saveState i 1`, but `mother.pd`
      routes it through a `[t b b b]` before `[s saveState]`, so **the float is discarded**. A
      probe logging `$1` recorded `0`, which is what `$1` of a bang gives in a message box.
      ⚠️ **A `[route 1]` or `[select 1]` on `saveState` would never fire** — a silent dead end,
      and nothing documented it.

- [x] **138. ✅ THE FULL ROUND TRIP WORKS.** `[text write]` → `/tmp/state/` → `save-patch.sh`'s
      `cp` → the patch folder. `probe-2000.txt` (26 003 bytes) and `probe-small.txt` both landed in
      `/sdcard/Patches/!/State Probe/`. ✅ `/tmp/state/` **already exists** — created at patch load,
      and **cleared at patch load too**, which is why it reads empty after a reload.

- [x] **139. ✅ mother WRITES `knobs.txt` ON EVERY SAVE.** `mother.pd` carries
      `write /tmp/state/knobs.txt` beside `[routeOSC /saveState]`, and a Save produced
      `knobs.txt` holding `0.0997067 0 0 0;` — four normalised knob positions, matching what was
      read off two stock patches earlier the same day. **So Cut It's "ships without a `knobs.txt`"
      decision survives only until Save is pressed**, and knob 1 is master tempo. Accepted
      deliberately: a preset that restores the knobs is what a performer wants.

- [x] **140. ✅ A RELATIVE `[text write]` BYPASSES THE WHOLE MECHANISM.** Pd's working directory is
      `/tmp/patch`, which is a **symlink to the patch folder on the SD card** — so a write with no
      path lands in the deployed folder immediately, with **no Save involved**. Measured:
      `probe-relative.txt` appeared in `/sdcard/Patches/!/State Probe/` three seconds after load.
      Cuts both ways — a persistence route that needs no Save, and a way for a careless write to
      silently mutate the deployed patch.

- [x] **141. ✅ WRITE COST — 2000 LINES / 26 KB IS ~16 ms, AND THE STORAGE DOES NOT MATTER.**
      Measured with `[realtime]` around one `[text write]`, with the line count printed separately
      because **a write that fails is fast** — a failed `/sdcard` write on the Mac reported
      0.183 ms.

      | | ms |
      |---|---|
      | Mac | 1.5 |
      | Organelle, `/tmp` (**tmpfs — RAM**) | 15.8 |
      | Organelle, `/sdcard` (**ext4 on the SD card**) | 16.2 |
      | Organelle, **in situ** inside the menu-launched patch | **15.6 / 15.1** |

      tmpfs and the SD card measure the same, so **the cost is Pd's serialisation, not the
      storage**. ~6 % of the 250 ms budget; linear extrapolation puts it near **30 000 lines**.
      ✅ The in-situ numbers match the second-Pd numbers, which validates that cheaper method.

- [x] **142. ✅ A SAMPLE CAN BE WRITTEN INSIDE THE BUDGET — BUT NOT UNBOUNDEDLY.** `soundfiler`
      write, mono 44.1 kHz, to `/tmp/state`: **2 s = 6.1 ms, 10 s = 29 ms, 30 s (2.6 MB) =
      85 ms.** mother's own `cp` of 2.6 MB to the SD card cost 45 ms, outside the patch's budget.
      So ~3 × 30 s or ~8 × 10 s samples exhaust 250 ms.

      ⚠️ **NOT MEASURED, AND DO NOT GENERALISE THESE:** they ran in a second Pd with **no DSP**. In
      the running instrument an 85 ms *synchronous* `soundfiler` write sits on Pd's message thread
      with audio live and would very likely glitch. `writesf~` writes from a helper thread, or
      capture writes at capture time rather than save time. Phase 7's lesson, applied to itself.

- [x] **143. ⚠️ `[text write]` TO A MISSING DIRECTORY DOES NOT FAIL SILENTLY — it prints.** The
      Phase 8 plan asserted it did. It prints `write failed`. `[text read]` of a **missing file**
      prints three lines. ⚠️ **`deploy.sh` gates on output**, and first boot has no state file.

      ✅ **The fix needs no new mechanism.** `-send "pd quit"` returns in **735 ms**, before any
      `[del]` fires — proved with an undelayed control print that *did* appear beside a delayed
      read that did not. `u_init` already stages the restore at ~3.5 s, so the gate is satisfied
      for free. **No default state file has to be shipped**, which also avoids `deploy.sh`
      overwriting saved device state on every push.

- [x] **144. ✅ SAVE NEW WORKS FROM A MENU SELECTION — AND LANDS OUTSIDE THE CATEGORY FOLDER.**
      Menu selection leaves `/tmp/curpatchname` = `State Probe`, against the `!` a `deploy.sh`
      load leaves — **the item 130-era diagnosis confirmed by direct observation rather than by
      reading the script.** Save New then produced a complete working `/sdcard/Patches/State
      Probe 2/` — `main.pd`, all state files and `knobs.txt`.

      ⚠️ **It lands at the TOP LEVEL of `Patches`, never back inside `!`**, because
      `save-new-patch.sh` copies to `${PATCH_DIR}/${NEWNAME}`. Not fixable patch-side.

      ❌ **A hypothesis this session invented, and measurement killed it.** `save-new-patch.sh`
      reads `PATCH_DIR=${PATCH_DIR:="/usbdrive/Patches"}`, `start-mother.sh` exports only
      `USER_DIR`, and `/usbdrive` is unmounted — which predicted Save New writing nowhere.
      **mother sets `PATCH_DIR` at runtime and it works.** `/proc/<pid>/environ` shows the
      *initial* environment and is not updated by `setenv`, which is what made the reasoning look
      sound.

- [x] **145. ✅ `[savestate]` WORKS END TO END IN 0.49 — and is orthogonal to all of the above.**
      Two instances of one abstraction saved `#A saved 111;` and `#A saved 222;` into the parent
      file, immediately after each `#X obj` line, and both restored on reload. ⚠️ But it writes
      into the **parent patch file** and needs a `menusave` that nothing on the Organelle triggers,
      so it is **not** a route into mother's save mechanism. ⚠️ Its restore also **prints at load**,
      the same `deploy.sh` hazard as item 143.

      Incidental: saving a patch in 0.49 **re-wraps long comments across physical lines and
      reorders the `#X connect` block**. Diff noise, not corruption.

**Three rig bugs, every one caught by a deliberate control rather than by reading** — the Phase 5
lesson holding for a fourth phase. A failed write reporting a *fast* 0.183 ms; ⚠️ **`$0` in a
MESSAGE box is not the patch id** (`\$0-a0` resolved to `0-a0`, every `soundfiler` write hit "no
such table" and reported a very quick 0.126 ms, and only `FRAMES-WRITTEN: 0` made it visible —
the documented `$1` trap, generalised); and an off-by-one in a hand-written `#X connect` block.
After the third, **the remaining probes were generated by script rather than hand-indexed**.

---

## Session 11 — the wifi fault, caught in full

⚠️ **One transition. Do not conclude a cause from it** — that instruction is
[plan-v03.md](plan-v03.md)'s and it still applies. What follows is *mechanism*, which is
more than items 81 and 133 have ever had.

- [x] **146. ✅ THE FAULT CAUGHT END TO END, and item 133's headline SURVIVES.** Device time
      2026-08-04 22:04:48, confirmed against the Mac's independent `UNREACHABLE 18:05:48 EDT`
      (= 22:05:48 UTC) — **the two agree within 60 s**, so the device clock was correct and there
      was no clock jump.

      | | |
      |---|---|
      | association | **held** — same BSSID, `SSID: hildegard` |
      | signal | **−35 dBm** — excellent. Not range, not the radio |
      | route / ARP | default route gone, **ARP table completely empty** |
      | duration | ran **6 hours** with `ipv4=NONE`, patch alive, OLED meters moving |
      | recovery | **UNRECOVERED** — all three rungs failed |

      ⚠️ **`dmesg` gave the mechanism, and it is not lease expiry.** Immediately before the loss:
      `cfg80211: Calling CRDA to update world regulatory domain` then a full
      `authenticate` → `associate` cycle at kernel `[11531]`. **The interface went down and back
      up, re-associated cleanly, and never re-acquired an address.** An identical cycle at
      `[9398]`, ~35 min earlier, survived. So the trigger is a **re-association**, not a timer.

- [x] **147. ✅ `dhcpcd` CANNOT PERSIST A LEASE ON THIS DEVICE — the root filesystem is read-only.**
      `/dev/root / ext4 ro,relatime`, and `/var/lib/dhcpcd/` is not writable. The only lease files
      present are **image artifacts dated Oct 17 2015** for `CBCI-AD15-2.4`, `birds` and `birds2`
      — and **there is no lease file for the network it actually uses.** `dhcpcd` is **6.9.3**
      (2015), configured with `option rapid_commit` and `noipv4ll`.

      **Hypothesis, explicitly NOT a finding:** on re-association `dhcpcd` would normally REBIND a
      stored lease; with none it must run a full DISCOVER, and 6.9.3 evidently does not recover
      when that fails. ⚠️ Recorded as a lead, not a cause — item 81 has had four unevidenced
      guesses already and this must not become a fifth.

- [x] **148. ⚠️ THE RECOVERY LADDER'S TIMEOUTS WERE TOO SHORT TO BE CONCLUSIVE — 15/20/25 s, now
      45/45/60 s.** Rung 3 kills `wpa_supplicant` and re-runs `wifi-config.sh`; the association
      alone took ~8 s in this failure's own `dmesg`, leaving under 17 s for a DHCP exchange that
      retries. **An `UNRECOVERED` verdict has to mean "it did not come back", not "we did not
      wait".** The 2026-08-04 verdict is probably still sound — it then sat six hours without an
      address — but it was not *proven* sound.

- [x] **149. ✅ A LINK PROBE NOW SPLITS THE DECISION TREE, and it is the test that was missing.**
      [plan-v03.md](plan-v03.md) sends `UNRECOVERED` straight to the spare-card A/B, on
      the reasoning that a different radio proves nothing if the fault is DHCP-side — **and that
      fork had never been tested.** `wifi-watch.sh` now assigns the last-known-good address and
      route *before* the ladder runs and pings the gateway:

      - **traffic flows** → the link is fine, the fault is DHCP-side, **and a card swap would prove
        nothing**
      - **traffic does not** → the link is dead while still reporting associated → driver or dongle
        firmware, and the card swap is correct

      ⚠️ **A bug in the probe was caught before it shipped, not in the field.** The cleanup deletes
      an address and a route; run against a *healthy* interface it would have deleted the **real**
      ones and taken the device off the network unattended. It now refuses to run when an address
      is present, and only ever removes what it successfully added. Verified by calling it against
      the live interface: it skipped, and the address and gateway were byte-identical either side.
      **A measuring rig is code** — Phase 5's lesson, holding for a fifth phase.

      Also re-learned: a `/proc` scan for `wifi-watch.sh` **matches the ssh command doing the
      scanning**, which is the same self-match the file already warns about for `pgrep -f`. One
      watcher was running; the count said two.

⬜ **Still to do at landing:** items 81 and 133 should be merged **in place** with the above rather
than left pointing at a superseded description — [plan-v03.md](plan-v03.md)'s recording
rules.

---

## Session 12 — Phase 8, the data store, built and verified

**Two bugs found on the Mac before hardware, and both were invisible: the files looked entirely
plausible in each case.** Then a third found in the gate itself.

- [x] **150. ✅ THE `[text]` PRIMITIVES, MEASURED BEFORE ANYTHING RESTED ON THEM.** This project
      had already been bitten twice here (item 32, and `moses` passing `-1` into `text set`), so
      the keyed-store primitive was measured first:

      | | |
      |---|---|
      | `[text search NAME]`, one-atom list | matches field 0, returns the line number |
      | a key that is absent | **`-1`** — must be guarded, per the reject rule |
      | `[text set NAME n]` | replaces line *n* **in place**; size unchanged |
      | `[text get NAME n]`, no field range | the whole line, **silently**, as a `list` |
      | `drumkit` vs `drums` | **exact atom match — a key may safely be a prefix of another** |
      | `text get` **past the end** | returns `bang` and prints nothing — the replay loop cannot overrun into an error |
      | `until` with 0 | runs **zero** times, so an empty file replays nothing |

      ⚠️ **`list append` is load-bearing for BOTH `text set` and `text search`** — each answers a
      bare selector with `no method for 'mode'`. Seen in `u_err` first and again here.

- [x] **151. ⚠️ `read -c` AND `write -c` MUST MATCH.** A file written with `-c` and read back
      **without** it comes back as **ONE line** — `text size` 1 — because Pd is hunting for
      semicolons that are not there. Measured both ways.

- [x] **152. ⚠️ THE AUTO STORE WROTE BEFORE IT EVER READ, and saved state could never have
      survived a boot.** The seed published at 500 ms, the flush fired at 3000 ms and **overwrote
      the saved file**, and only then did the restore read at 3500 ms. Every boot replaced the
      previous session with its own defaults, and `auto.txt` looked correct throughout.

      **Fixed with an invariant rather than a timing tweak: the flush metro is armed BY THE
      RESTORE**, so `u_state` can never write a file it has not yet read. ⚠️ The consequence is
      worth knowing — if the restore never fires, the auto store never flushes. That is the safer
      failure (no writes) rather than data loss, but it means `u_init`'s outlet 2 is load-bearing.

- [x] **153. ⚠️ `text read` OF AN EMPTY FILE WIPES THE LIVE STORE**, silently discarding puts that
      arrived before the restore. On a fresh install the boot mode was discarded and `auto.txt`
      was written empty; it self-healed on the first real change, which is exactly the kind of
      thing that would never have been noticed. **Fixed by reading into a SEPARATE text and
      replaying from that** — the live store is never wiped by a load. Both cases then verified:
      empty files keep the seed, and a saved file wins over it.

- [x] **154. ✅ THE PHASE VERIFIED ON HARDWARE WITHOUT EYES.** `state-dir.sh` ran and created
      `/sdcard/cut-it-state/` with both files; `auto.txt` read `mode compose mode-1`. Then the
      test that proves the restore with no display and no Launchpad: **plant `mode perform mode-5`
      in the file, reload the patch, and see whether it survives.** It did — which it can only do
      if the restore ran and beat the 500 ms seed.

      ✅ **`Storage → Save` reaches the patch**: `cut-it-manual.txt` was rewritten at the moment of
      the press (mtime 04:28:46 against a device clock of 04:29:15) while `auto.txt` was left
      alone at 04:25:00 — so the two policies really are independent. The file is **empty and that
      is correct**: no shipped contributor uses the manual policy yet.

      ✅ **Item 139 confirmed for Cut It specifically** — mother wrote `knobs.txt` containing
      `0.0957967 0 0 0;`.

- [x] **155. ⚠️ THE GATE PASSED THE BROKEN PATCH ON ITS FIRST CAN-IT-FAIL RUN.** Phase 6's rule is
      that a bench must be proven able to fail; this one was not, and it lied. **Two faults, both
      classic:**

      1. **The driver's timing did not reproduce the real ordering.** The bug is *flush at 3000 ms,
         restore at 3500 ms*; the driver banged the restore at 600 ms, so the fatal sequence never
         occurred. The driver now uses **3600 ms and that number is load-bearing** — shortening it
         re-blinds the gate.
      2. **The final check could not fail.** It looked for `mode compose mode-1`, a value only
         `u_map`'s seed produces, and the driver has no seed — Phase 6's *"an assertion that
         nothing ever drove"*, exactly. Rewritten to assert the real property: **did the restore
         replay what was on disk at boot?**

      Now proven both ways: **15/15 on the good build, 2 failures with the bug reintroduced**, and
      the file restored byte-identical afterwards.

- [x] **156. ✅ COST: 10.4–10.7 % CPU / 115–116 UDP per second**, against Phase 7's 11.7 % and
      122–126/s. ⚠️ **Lower, and NOT evidence that `u_state` is free** — the rig was not in the
      same state as that measurement (**4 ALSA links rather than 5**, so a controller was
      unplugged, and the phone was not up). It bounds the cost as small and nothing more. The
      script's printed "WITHIN BUDGET ≤ 11.2 %" is still Phase 5's stale figure.

- [x] **157. ✅ THE PHASE 8 ACCEPTANCE RUN ON THE DEVICE — 5 of 5, INCLUDING A REAL POWER CYCLE.**
      Driven by hand with both controllers attached. Every Phase 8 bench step carries no actions,
      so the run needed **no by-hand console and no `killall pd`** — and therefore never stranded
      the Launchpad, which is the usual cost of running a bench on this device.

      | Step | Result |
      |---|---|
      | 1 baseline | the **5th** mode lamp green, other five dim white — the saved value, not the mode-1 default |
      | 2 transport key 4 | lamp moves to the **4th** |
      | 3 reached the disk | `cut-it-auto.txt` → `mode perform mode-4` at 04:43:58. **The whole chain on hardware**: nanoKONTROL → `m_nano` → `param` → `u_map` → `mode` → `state` → `u_state` → SD card |
      | 4 `Storage → Save` | `manual.txt` 04:40:41 → **04:44:50**, and ⚠️ **`auto.txt` UNTOUCHED at 04:43:58** — the two policies are genuinely independent, which is what will make "abandon a take by not saving" work. `knobs.txt` rewritten 0.5 s later |
      | 5 **power cycle** | uptime 2 min, and the **4th lamp lit again**. State survived the SD card, which a patch reload can never demonstrate |

      ⚠️ **`state-dir.sh` touches both files at every load, so `manual.txt`'s mtime also moves on a
      patch reload.** The step-4 evidence is only clean because nothing reloaded in between. A
      future run must take the baseline immediately before the Save, not from an older reading.

      ⬜ **One observation, recorded rather than interpreted:** the Organelle **needed a retry to
      rejoin wifi** after this power cycle. One occurrence, no evidence attached, and it may be
      unrelated to items 81/146 — noted only so it is not "remembered" differently later.

- [x] **158. ⚠️ A HARDWARE-VERIFIED BENCH TABLE WAS EDITED, DELIBERATELY, AND HERE IS WHY.** Item
      122 records that the phase 3–6 step tables are **not reworded** — they are verified,
      `bench-verify.py` gates on them matching, and rewording them would spend that verification.

      Dissolving `plan-v02.md` into `plan-v03.md` changed **one atom in one phase 6 step**:
      `See plan-v02.md` → `See plan-v03.md`. **The alternative was leaving a pointer to a file that
      no longer exists**, in a step a person reads while standing at the device.

      **What was NOT changed: what the step asserts.** The `PASS IF` semantics, the actions and the
      ordering are untouched, and `bench-verify.py` still reports phase 6 IDENTICAL against the
      table. Recorded because "the verified benches are not reworded" is a real rule and this is a
      real exception to it — a filename, not a claim.

⬜ **Not established, and deliberately left open:** whether a saved `knobs.txt` beats the physical
knob position at boot. Both are pushed at load and which wins was never measured. It is in
[plan-v03.md](plan-v03.md) *Open questions* rather than asserted in a bench step.

---

## What's actually left

**Nothing lives here.** Every remaining question, blocked item and purchase is in
[plan-v03.md](plan-v03.md), which is the project's single planning document.

This file is the **evidence ledger**: numbered checks with their measured results, cited bare as
"item 133" across the whole project. It accumulates; it does not plan. When a check here is still
unticked, the *work* to resolve it is described in plan-v03.

**Everything through Phase 8 has passed**, including **six phases end to end on the Organelle**:
Phase 3 (items 21–21c), Phase 4 (33–38b, 80), Phase 5 (70–79), Phase 6 (82–97), Phase 7 (113–134)
and Phase 8 (150–157).
