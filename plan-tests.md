# Cut It — Pre-Flight Tests

Things to verify on the hardware **before** starting UI/UX design or the patch rewrite.
Ordered by what would force a redesign if it fails.

Most of this needs scratch patches only — no Cut It code. Diagnostic patches live in
[tools/](tools/). Companion to [ref-hardware.md](ref-hardware.md), which explains *why* each of these
matters.

**Status:** Sessions 2, 3b, 3c and 4 complete. Session 1 done bar the full-load power check.
Session 3 blocked on the TRS Y-cable; Session 5 not attempted.

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

- [x] **14. Plug it in and print the CCs.** ✅ Class compliant, enumerates as ALSA card 4,
      arrives on Pd channel 17.
- [x] **15. Korg Kontrol Editor — runs, and the nano is configured.** ✅ **Use version 2.4.0**,
      not the current release: Korg's 2.5.0 removed support for the first-generation
      nanoKONTROL, and 2.4.0 is the last version that sees it. It runs on macOS 26; get it from
      the *"previous versions"* section of the
      [KORG KONTROL EDITOR download page](https://www.korg.com/us/support/download/software/1/133/1355/).
      Don't go below 2.0.9 — earlier releases predate Catalina's 64-bit requirement.

      The full CC map is written to the device and catalogued in [ref-midi.md](ref-midi.md).
      All buttons are **momentary**, so Pd owns all toggle state, and **no LED Mode setting
      exists** on the mk1 — all visible state must live on the Launchpad.
- [x] **16. Transport buttons reassigned as the master mode control.** ✅ Six buttons moved to
      **CC 41–46**, in physical order, on the nano's **channel 2** — arriving as **Pd channel
      18** while the control groups stay on 17, so a single `[route 18]` isolates every mode
      change before any CC decoding.

      **Verified by decoding the raw stream off the wire**, not just trusting the editor: all
      six in order with no gaps, momentary 127/0 throughout, control groups on 17, full 0–127
      range with *Upper Value* unclipped, and **no SysEx anywhere in the stream** — nothing
      emits MMC. Reasoning in [ref-midi.md](ref-midi.md).

      The factory assignment was overwritten before it was ever read, so what these buttons
      shipped with is now unknown. ✅ The scene file — device-resident state that REC + STOP +
      SCENE at power-on wipes — is backed up in [device/](device/).

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

- [ ] **17. Bring up an AP on `wlan0` and join it from the iPhone.** Confirm the phone gets an
      address from `dnsmasq` and the status display still updates.
- [ ] **18. Check it in airplane mode** — cellular off, wifi manually re-enabled.
- [ ] **19. Judge the link quality.** Watch the heartbeat for gaps over a few minutes. This is
      the actual question: is it steady enough to trust mid-set?
- [ ] **20. Decide whether it survives a reboot** — and whether you *want* it to. Persisting it
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

Everything else in Sessions 1, 2 and 4 has passed. The full MIDI picture — every message each
device accepts and transmits — is catalogued in [ref-midi.md](ref-midi.md), which also
carries the remaining message-level unknowns, chief among them the **SP-404 pad note range**
(verified 47+*n* here, but Roland's chart says 35–51 — sweep all 16 pads before writing
sequencing code against it).
