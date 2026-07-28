# Cut It — Pre-Flight Tests

Things to verify on the hardware **before** starting UI/UX design or the patch rewrite.
Ordered by what would force a redesign if it fails.

Most of this needs scratch patches only — no Cut It code. Diagnostic patches live in
[tools/](tools/). Companion to [rig-plan.md](rig-plan.md), which explains *why* each of these
matters.

**Status:** Sessions 1, 2 and 4 substantially done. Session 3 blocked on the TRS Y-cable.

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
      [CLAUDE.md](CLAUDE.md). Devices are wired to Pd's ports with `aconnect` **by name**;
      client numbers shift as devices come and go (28 was the Launchpad, then became the
      SP-404), so never hardcode them.

      Not yet done: all four devices connected at once. Blocked on cables.

- [ ] **4. Can the patch wire its own MIDI connections at load time?** ⚠️ **The real
      remaining risk in this session.** mother's `alsaconnect.sh` connects only *one* device —
      it predates multi-controller setups — so Cut It has to issue its own `aconnect` calls.

      `shell.pd_linux` is present in `/root/Pd/externals`, so `[shell]` should be able to run
      them from inside the patch. Untested. Two constraints already known:

      - Connect **by name**, never by client number.
      - **Delay it.** ALSA connections do not exist when `loadbang` fires — see Session 2.

      If `[shell]` turns out to be unusable, the fallback is overriding `alsaconnect.sh` via
      the `/sdcard/Firmware/scripts` path, which is heavier (it also wants a `mother` binary
      alongside it).

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
- [ ] **8b. Flashing and pulsing.** Static / flashing / pulsing are MIDI channels 1 / 2 / 3.
      Untested. Worth knowing before designing state colours — a blinking "queued" state costs
      one message instead of timing logic in Pd.
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

⬜ **Untouched. Blocked on the TRS Y-cable** (1× 1/4" TRS → 2× 1/4" TS), the one shopping-list
item nothing substitutes for. Needs no USB at all.

- [ ] **11. Y-cable → two independent channels.** Feed a tone into one side only; confirm
      `adc~ 1` and `adc~ 2` are genuinely separate. Foundational to the whole drums/fx split.
- [ ] **12. 404 pan split.** Pan one sample MONO Left and another MONO Right; confirm they
      arrive on separate Organelle inputs.
- [ ] **13. Mic bleed test.** Mic into MIC/GUITAR IN, play a sample panned hard left, listen
      to the **L output alone**. Expected: the mic is audible there too (it sums to both). If
      it isn't, the accepted bleed compromise is unnecessary and the design gets simpler.

See [rig-plan.md](rig-plan.md) open question 4 for the fuller version, including the
LINE IN R-only variant.

---

## Session 4 — nanoKONTROL

- [x] **14. Plug it in and print the CCs.** ✅ Class compliant, enumerates as ALSA card 4,
      arrives on Pd channel 17. A fader sends CC 2. Full 18-control map not yet catalogued,
      but the question is answered.
- [ ] **15. Does Korg Kontrol Editor run on your machine?** Needed to set buttons to momentary
      and assign per-scene CCs. 2008-era software. If it will not run, the nano is stuck with
      its current assignments and toggle-mode buttons, which changes the control mapping
      approach.

---

## Deliberately skipped for now

Not unimportant — just not blocking UI/UX decisions.

| Deferred | Why it can wait |
|---|---|
| LINE IN R-only behaviour | An upgrade path, not a requirement |
| Ground loops | Deal with hum if and when you hear it |
| 404 round-trip latency | Perform-time tuning; needs a working patch first |
| CPU headroom | Not a real risk at this scale |
| Full nanoKONTROL CC map | Catalogue it when mapping controls |

---

## What's actually left

1. **Item 4** — patch self-wiring its `aconnect` calls. The last structural unknown.
2. **Session 3** — audio topology, once the Y-cable arrives.
3. **Item 15** — Korg editor, which gates the momentary-buttons decision.
4. **Items 5 and 8b** — power under full load, and flashing/pulsing LED states.
