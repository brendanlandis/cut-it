# Cut It — Pre-Flight Tests

Things to verify on the hardware **before** starting UI/UX design or the patch rewrite.
Ordered by what would force a redesign if it fails.

Most of this needs scratch patches only — no Cut It code. Diagnostic patches live in
[tools/](tools/). Companion to [plan-hardware.md](plan-hardware.md), which explains *why* each of these
matters.

**Status:** Sessions 2, 3b and 4 complete. Session 1 done bar the full-load power check.
Session 3 blocked on the TRS Y-cable.

**The two tests that could have forced a redesign have both passed:** Pd can drive the
Launchpad's Programmer Mode over SysEx (LEDs, velocity, polyphonic aftertouch), and Pd's
per-device channel offsets work with multiple controllers at once. What remains is
cable-blocked — the audio topology and full-rig power draw.

**Do not treat open items as settled facts.** [plan-hardware.md](plan-hardware.md) has an
*Open questions* section, [plan-midi.md](plan-midi.md) has its own, and this file is the
ordered checklist with results. The [tools/](tools/) patches are working references for every
technique verified here.

---

## Session 1 — Does the plumbing exist?

- [x] **1. Organelle's Pd version.** ✅ **Pd 0.49.0**, compiled Oct 9 2018, confirmed with
      `pd -version`. Device reports OS 4.0 — the release that took Organelle 1 from Pd 0.46
      to 0.49.

- [x] **2. Can you edit Pd's startup flags?** ✅ **Yes — `/root/.pdsettings`.** Pd is launched
      by the `mother` binary:

      ```
      /usr/bin/pd -rt -nogui -audiobuf 6 -path /sdcard/PdExtraLibs /root/fw_dir/mother.pd main.pd
      ```

      No `-noprefs` and no MIDI flags, so `.pdsettings` governs MIDI. **Already edited** —
      `midiapi: 1` plus four in/out device entries, verified surviving a cold boot under
      mother. Backup at `/root/.pdsettings.bak`.

      The rootfs is mounted **read-only**: run `/root/fw_dir/scripts/remount-rw.sh` before
      writing to `/root`, `remount-ro.sh` after.

- [x] **3. Channel offsets confirmed in Pd.** ✅ Verified in Pd, not just at the ALSA layer:

      | Device | Pd device | Channel | Status |
      |---|---|---|---|
      | Launchpad Pro MK3 | 1 | 1–16 | ✅ `[notein 1]` received pad presses |
      | nanoKONTROL | 2 | 17 | ✅ `ctlin` reported channel 17 |
      | SP-404MK2 | 3 | 33 | ✅ `ctlin` reported channel 33 |
      | USB→DIN interface | 4 | 49–64 | ⬜ Not purchased yet |

      nanoKONTROL and SP-404 were confirmed **simultaneously**, in distinct blocks. One
      `[route]` on the channel outlet separates devices.

      Required getting Pd onto ALSA MIDI first — see *MIDI: OSS vs ALSA* in
      [plan-hardware.md](plan-hardware.md). Devices are wired to Pd's ports by name with
      `aconnect`;
      client numbers shift as devices come and go (28 was the Launchpad, then became the
      SP-404), so never hardcode them.

      Not yet done: all four devices connected at once. Blocked on cables.

- [x] **4. Can the patch wire its own MIDI connections at load time?** ✅ **Yes, via
      `[shell]`.** Necessary because mother's `alsaconnect.sh` connects only *one* device — it
      predates multi-controller setups.

      `shell.pd_linux` is in `/root/Pd/externals` and loads fine. The working pattern is
      `[loadbang] → [del 1500] → [sh /tmp/wire.sh( → [shell]`, with the `aconnect` calls in a
      **shell script** rather than a Pd message box — that sidesteps Pd's quoting rules around
      quotes and colons entirely. Reference implementation: `tools/self-wire.pd` and
      `tools/wire.sh`.

      Verified wiring all connections from a cold Pd launch with nothing pre-connected.

      Two constraints, both load-bearing:

      - Connect **by name**, never by client number.
      - **Delay it.** ALSA connections do not exist when `loadbang` fires — see Session 2.

- [ ] **5. Watch for brownouts** with the full rig connected. Never yet tested with three
      controllers plus the wifi dongle simultaneously — only ever two at a time, because of
      the cable shortage. A marginal hub shows up as dropouts rather than an obvious failure.

---

## Session 2 — Can Pd drive the Launchpad? ✅ PASSED

**This was the critical session** — if SysEx out from Pd had been troublesome, the
Launchpad-as-display concept would have collapsed. It works.

- [x] **6. Send the Programmer Mode SysEx from Pd.** ✅ Pd sent it itself via `[midiout]`.
      Programmer Mode is on **port 0** (`hw:3,0,0`, seq `28:0`); ports 1 and 2 carry nothing
      in either direction. Enter: `F0 00 20 29 02 0E 0E 01 F7`.
- [x] **7. Receive pad presses.** ✅ `r*10+c` layout confirmed (notes 43, 44, 45, 53, 54, 55…),
      both digits 1–8. `div 10` / `mod 10` gives coordinates directly. Velocity is real —
      soft presses register as low as 10.
- [x] **8. Light a pad.** ✅ 64 pads individually addressable. Velocity indexes a **128-entry
      colour palette, not brightness**. For arbitrary colour use per-pad RGB SysEx:
      `F0 00 20 29 02 0E 03 03 <pad> <r> <g> <b> F7` — see `tools/lp-flicker.pd`.
- [x] **8b. Flashing and pulsing.** ✅ All three lighting modes work, animated by the device
      itself — no `[metro]` needed in Pd. Static / flashing / pulsing are MIDI channels
      **1 / 2 / 3**, so `[noteout 1]`, `[noteout 2]`, `[noteout 3]`.

      **Flashing alternates the channel-1 and channel-2 colours** for that pad, so send both:
      ch1 sets one colour, ch2 the other. Pulsing takes a single ch3 colour.

      **Pick bright palette indices for pulsing** — it ramps brightness toward zero, so it
      spends real time dim and a mid-brightness colour reads as weak. See `tools/lp-modes.pd`.
- [x] **9. Read pressure.** ✅ Polyphonic aftertouch working, per-pad, simultaneous — two held
      pads reported independent values. **Requires enabling on the device:** hold `Setup`,
      press the **third Track Select button**, choose *Polyphonic Aftertouch*. Default is
      Channel Pressure (one value for the whole surface). Programmer Mode locks out the Setup
      menu, so exit to Live first. An *Aftertouch Threshold* on that page is worth tuning.
- [x] **10. Return to Live mode.** ✅ `F0 00 20 29 02 0E 0E 00 F7`, verified. Essential escape
      hatch — entering Programmer Mode by SysEx locks out the Settings menu until you send it.

**Gotchas found here, all recorded in [tools/README.md](tools/README.md):**

- **`loadbang` fires before ALSA connections exist.** Init SysEx sent on `loadbang` goes
  nowhere. Use `[loadbang] → [del 2000]` or longer.
- **`polytouchin` emits note before value**, so wiring it straight to `[noteout]` lights a pad
  with the previous event's pressure.
- **LED state survives mode switches** — entering Programmer Mode does not blank the grid. The
  patch must clear it on init.

---

## Session 3 — Audio topology

**Item 11 passed.** ⬜ Items 12 and 13 remain blocked on the TRS Y-cable (1× 1/4" TRS →
2× 1/4" TS). Needs no USB at all.

**The source side is not in question.** The SP-404MKII has **discrete L and R jacks on both
line in and line out**, so two independent signals demonstrably leave the box. The Y-cable is
still required, because the constraint is at the other end: **the Organelle has a single TRS
input jack**, and the cable is what merges two mono outs into it. Nothing substitutes for it.

- [x] **11. TRS input → two independent channels.** ✅ **PASSED.** Measured with
      `tools/audio-probe/`, which puts `env~` levels for both channels on the OLED. A passive
      bass through an ordinary mono TS cable:

      | Condition | `adc~ 1` (tip) | `adc~ 2` (ring) |
      |---|---|---|
      | Cable unplugged | 18–19 | 18–19 |
      | Plugged, strings muted | mid-20s | 18–19 |
      | Playing | **90s** | **18–19** |

      The ring never leaves the noise floor while the tip swings ~70 dB. **The channels are
      independent and `adc~ 1` is the tip** — the assumption the whole drums/fx split rests on.

      Two useful by-products: the **noise floor is ~18–19** on `env~`'s 0–100 dB scale (about
      −82 dBFS), which sets a sensible gate threshold around 25–30; and a **passive bass
      reaches the 90s**, so input gain is ample and headroom is fine for instrument-level
      sources.

      **Re-confirmed through the v0.2 patch** (Phase 1, `u_level` + `g_levels`): both channels
      report 18–19 at rest, reproducing the diagnostic's numbers in the real signal path rather
      than a test patch.
- [ ] **12. 404 pan split.** Pan one sample MONO Left and another MONO Right; confirm they
      arrive on separate Organelle inputs. Tests the 404's *internal* per-sample routing, which
      discrete output jacks do not guarantee.
- [ ] **13. Mic bleed test.** Mic into MIC/GUITAR IN, play a sample panned hard left, listen
      to the **L output alone**. Expected: the mic is audible there too (it sums to both). If
      it isn't, the accepted bleed compromise is unnecessary and the design gets simpler.

      **This is the one that could still change the design** — it is about how the 404 places
      *external input* in the stereo field, which is internal routing and unrelated to the jacks
      on the back.

See [plan-hardware.md](plan-hardware.md) open question 1 for the fuller version, including the
LINE IN R-only variant.

---

## Session 3b — USB topology ⚠️ blocking Phase 2 verification

- [x] **13a. Launchpad configures at all.** ✅ **PASSED — plugged directly.** Behind three
      chained hubs it enumerated and then failed with `can't set config #1, error -32`, so no
      ALSA client was created. Connected straight to the Organelle it configures immediately
      and appears as `client 28`. The hub chain was the whole problem; full evidence in
      [plan-hardware.md](plan-hardware.md).
- [x] **13c. Programmer Mode through the real patch.** ✅ `u_init` wires and initialises it at
      boot with no manual steps. Captured pads read **`r*10+c`** (64, 65, 34, 24, 43, 63),
      which is the Programmer Mode layout, with live velocity 5–127.
- [x] **13b. Why booting with the Launchpad wedges the UI.** ✅ **ROOT-CAUSED — not power, not
      the hub.** The Launchpad exposes a 192 KiB write-protected vfat volume ("Novation
      Onboarding Drive"). `mount.sh` picks the last `/dev/sd*`, mounts it on `/usbdrive`,
      `getDefaultUserDir()` then returns `/usbdrive`, and `wifi_control.py` dies trying to open
      a log for writing there. Full chain in [plan-hardware.md](plan-hardware.md).
- [x] **13d. `mount.sh` guard applied.** ✅ Installed on the device; factory version kept at
      `/root/fw_dir/scripts/mount.sh.orig` and in [device/](device/). Verified that a full
      `/reload` with the Launchpad attached mounts nothing and leaves `USER_DIR` as `/sdcard`.
- [x] **13e. Cold boot with the Launchpad attached.** ✅ **PASSED.** Boots normally, wifi
      connects, `/usbdrive` stays unmounted and `USER_DIR` stays `/sdcard` — `/dev/sda1` is
      still present with `ro=1`, so `mount.sh` saw the volume and declined it. Loading the
      patch then wires the Launchpad both directions with no manual step. **Session 3b closed.**

---

## Session 4 — nanoKONTROL

- [x] **14. Plug it in and print the CCs.** ✅ Class compliant, enumerates as ALSA card 4,
      arrives on Pd channel 17. A fader sends CC 2. Full 18-control map not yet catalogued,
      but the question is answered.
- [x] **15. Korg Kontrol Editor — runs, and the nano is configured.** ✅

      **Use version 2.4.0**, not the current release. Korg's 2.5.0 removed support for the
      first-generation nanoKONTROL ("Remove nanoKEY, nanoPAD, nanoKONTROL"). 2.4.0 is the last
      version that sees it, and it runs on macOS 26. Get it from the *"Click here for previous
      versions"* section of the
      [KORG KONTROL EDITOR download page](https://www.korg.com/us/support/download/software/1/133/1355/).
      Don't go below 2.0.9 — earlier releases predate Catalina's 64-bit requirement.

      **Configured and written to the device:**

      | Control | CC |
      |---|---|
      | Sliders 1–9 | 1–9 |
      | Knobs 1–9 | 11–19 |
      | Buttons, top row 1–9 | 21–29 |
      | Buttons, bottom row 1–9 | 31–39 |

      All buttons set to **momentary** — verified sending 127 on press, 0 on release, so Pd
      owns all toggle state. Decode in Pd with `cc div 10` for control type (0=slider, 1=knob,
      2=top button, 3=bottom button) and `cc mod 10` for channel number — the same idiom as
      the Launchpad's `r*10+c` grid.

      **No LED Mode setting exists** for the mk1, confirming it has no host-controllable LEDs.
      All visible state must live on the Launchpad.

- [x] **16. Transport buttons reassigned as the master mode control.** ✅ Six buttons moved off
      their factory assignment to **CC 41–46**, in physical order, on the nano's **channel 2**
      — arriving as **Pd channel 18** while the control groups stay on 17. Assign Type
      *Control Change*, Button Behavior *Momentary*.

      This extends the `div 10` idiom: 4 = transport, `mod 10` = which button. And a single
      `[route 18]` isolates every mode change before any CC decoding, so a mode switch can
      never be confused with a performance control.

      **Verified by decoding the raw stream off the wire**, not just trusting the editor:

      | Checked | Result |
      |---|---|
      | Six transport buttons | CC 41, 42, 43, 44, 45, 46 — in order, no gaps |
      | Transport channel | 2 → Pd channel 18 |
      | Control group channel | 1 → Pd channel 17 (slider 1 = CC 1, knob 1 = CC 11) |
      | Button behaviour | 127 press / 0 release throughout |
      | SysEx / MMC | **none in the stream** — nothing emits MMC |
      | Slider and knob range | full 0–127, *Upper Value* not clipped |

      Rationale for the change is in [plan-midi.md](plan-midi.md) under *Recommendation*. The
      factory assignment was overwritten before it was ever read, so what these buttons
      shipped with is now unknown — it stopped mattering, but it is not a finding.

      **The scene file is device-resident state with no backup.** REC + STOP + SCENE held at
      power-on wipes it. Export it from Kontrol Editor and commit it here.

---

## Session 5 — Organelle as its own access point

⬜ **Not attempted.** Gates whether the PdParty status display is stage-worthy or
development-only. Everything else about the phone link is already verified — see
[plan-display.md](plan-display.md).

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
device accepts and transmits — is catalogued in [plan-midi.md](plan-midi.md), which also
carries the remaining message-level unknowns, chief among them the **SP-404 pad note range**
(verified 47+*n* here, but Roland's chart says 35–51 — sweep all 16 pads before writing
sequencing code against it).
