# Cut It — Rig Plan

Hardware setup plan for the Cut It instrument. Companion to
[README.md](<! v0.1 plans/README.md>), which covers the Pd patch itself.

Target hardware: **Organelle 1** (the original, not M/S/S2).

---

## Overview

The Organelle is the brains. It runs the Cut It patch, acts as USB MIDI host for every
controller, and is the clock master for the whole rig.

The SP-404MK2 is the sample store and the front end. It holds drum samples and fx samples,
takes the mic and any arbitrary audio input, and feeds two independent mono streams into
the Organelle — drums on the left, fx on the right. Cut It captures and mangles what
arrives, and its two outputs go to the mixer.

Two channels through one stereo cable is the trick that makes this work: the Organelle has
a single 1/4" TRS input jack, so the 404's L and R arrive as `adc~ 1` and `adc~ 2`.


## Signal flow — MIDI

Everything is USB. The Organelle is a USB host; all four devices are class compliant.

```
                  ┌──────────────────────────────────┐
                  │  ORGANELLE                       │
                  │  Pd / Cut It — CLOCK MASTER      │
                  └────────────────┬─────────────────┘
                                   │ USB-A
                  ┌────────────────▼─────────────────┐
                  │       POWERED USB HUB            │
                  └──┬─────────┬─────────┬────────┬──┘
          USB-A→C ┌──┘         │         │        └──┐ USB-A
                  ▼            ▼ USB-A   ▼ USB-A→C   ▼
        ┌──────────────┐  ┌─────────┐  ┌──────────┐  ┌───────────────┐
        │ LAUNCHPAD    │  │ nano    │  │SP-404MK2 │  │ USB→DIN MIDI  │
        │ PRO MK3      │  │ KONTROL │  │          │  │ INTERFACE     │
        │ ch 1–16      │  │ch 17–32 │  │ ch 33–48 │  │ ch 49–64      │
        └──────────────┘  └─────────┘  └──────────┘  └───────┬───────┘
                                                             │ DIN
                                                             ▼
                                                     ┌───────────────┐
                                                     │  VOLCA FM     │
                                                     │  (receive only)│
                                                     └───────────────┘
```

**Why no MIDI merge box.** Pd namespaces multiple MIDI input devices by channel: device 1
gets channels 1–16, device 2 gets 17–32, and so on. `notein`'s right outlet and `ctlin`'s
channel outlet tell you which device a message came from, for free. A merge box would
flatten everything into one stream and throw that away.

`MAXMIDIINDEV` is 16 in Pd (verified in both 0.49 and 0.53 source), so four devices is
nowhere near the limit.

**Done:** Pd only opens the MIDI devices it is told to at launch, and it reads that from
`/root/.pdsettings`, not command-line flags — mother passes none. The device is configured for
**4 in / 4 out** with `midiapi: 1` (which forces ALSA MIDI; without it Pd falls back to OSS
and the Launchpad's three ports collapse into one). Verified surviving a cold boot. Backup at
`/root/.pdsettings.bak`.

**Devices are wired to Pd's ports with `aconnect`, by name** — and the patch does this itself
at load time via `[shell]`, because mother's `alsaconnect.sh` only connects one device. See
`tools/wire.sh`.

**Direction:** the Organelle is clock master. Disable clock-out on every other device —
particularly the 404's "MIDI Sync Out", which will otherwise echo clock back and create a
loop.

**Keep sending clock — it is not decorative.** An earlier draft of this plan claimed it was,
on the grounds that nothing external runs its own sequencer during a performance. That was
wrong: the 404's **BPM SYNC time-stretch follows its tempo**, and the only way it learns the
tempo is by measuring incoming clock intervals. Stop the clock and it stretches to a stale
local value. See *Time-stretch* in [plan-software.md](plan-software.md).

**The Launchpad runs over USB.** Its TRS MIDI jacks go unused, and the three TRS→DIN
adapters in its box aren't needed here. USB gives it its own 16-channel block, keeps
Programmer Mode on the documented path, and means one cable does both power and data — at
the cost of the hub current, which is what the powered hub is for.


## Signal flow — audio

```
  [mic] ──────────────► SP-404 MIC/GUITAR IN  (1/4" TRS, mono)
  [arbitrary source] ─► SP-404 LINE IN

                    ┌───────────────────────────────┐
                    │        SP-404MK2              │
                    │  drum samples → pan MONO L    │
                    │  fx samples   → pan MONO R    │
                    │  use BUS 1/2 only (see below) │
                    └────────┬─────────────┬────────┘
                        OUT L│             │OUT R
                      (drums)│             │(fx)
                             ▼             ▼
                    ╔════════ Y-CABLE (2×TS → 1×TRS) ════════╗
                                     │
                    ┌────────────────▼──────────────┐
                    │  ORGANELLE   IN (TRS stereo)  │
                    │    adc~ 1  = drums  (tip)     │
                    │    adc~ 2  = fx     (ring)    │
                    │  ─────── Cut It ───────       │
                    └───────┬───────────────┬───────┘
                       OUT L│               │OUT R
                            ▼               ▼
                    ┌──────────────────────────────────┐
                    │  XENYX Q802USB                   │
                    │   ch1  Organelle L  (drums)      │
                    │   ch2  Organelle R  (fx)         │
                    │   ch3/4  Volca FM                │
                    │   ch5/6  spare                   │
                    └────────────────┬─────────────────┘
                                     ▼  MAIN OUT
                                   [ PA ]
```

Organelle L/R go to the two **mono** channels (1 and 2) rather than a stereo pair, so drums
and fx each get their own 3-band EQ and one-knob compressor.

**The Organelle's jack complement**, quoted from the official Organelle 1 manual: 📄

> The single `In`(put) `LR` port is a 1/4" TRS (stereo) jack.
> The `L`(eft) and `R`(ight) `Out`(put) ports are both 1/4" TS (mono) jacks.

So: **one stereo input jack, two mono output jacks.** This asymmetry is why the TRS Y-cable is
required — the 404's two discrete mono outputs have to merge into the Organelle's single input
jack — while the output side needs only two ordinary patch cables.

**The input split is verified on hardware.** ✅ `adc~ 1` is the **tip**, `adc~ 2` is the
**ring**, and they are genuinely independent — a mono TS cable drives the tip to the 90s on
`env~`'s scale while the ring stays at the 18–19 noise floor. Measured with
`tools/audio-probe/`; full numbers in [plan-tests.md](plan-tests.md) item 11.

Two numbers worth remembering: the **input noise floor is ~18–19** on `env~`'s 0–100 dB scale
(≈ −82 dBFS), so a noise gate belongs around 25–30; and a **passive bass reaches the 90s**, so
there is ample gain and headroom for instrument-level sources.


## Signal flow — power

```
  power strip
    ├── ORGANELLE ........ 9VDC 1000mA centre-positive   (included)
    ├── SP-404MK2 ........ Roland PSD adapter            (included)
    ├── XENYX Q802USB .... own PSU                       (included)
    ├── POWERED USB HUB .. own PSU                       (comes with hub)
    │     ├── Launchpad Pro MK3
    │     ├── nanoKONTROL
    │     └── USB→DIN MIDI interface
    └── VOLCA FM ......... Korg KA-350 9V (or 6×AA)
```

**Do not bus-power the 404.** Roland requires USB-C-to-C at 5V/1.5A for bus power and does
not guarantee operation through hubs. A USB-A→C cable from the hub carries **data only**,
which is what we want — the 404 runs off its own adapter and costs the hub nothing.

## The device itself

```sh
ssh root@organelle.local        # 192.168.1.15, password: organelle
```

| | |
|---|---|
| Home | `/root` (not `/home/music`) |
| Patches | `/sdcard/Patches/` — factory set lives here |
| User patches | `/sdcard/Patches/!/` — `!` sorts to the top of the menu |
| Pd config | `/root/.pdsettings` |
| Externals | `/root/Pd/externals` |
| Scripts | `/root/fw_dir/scripts/` |
| Extra libs | `/sdcard/PdExtraLibs` — already on Pd's search path |
| Transfer | **`scp` only — no rsync installed** |

Hardware is **i.MX-based** (`imx-spdif`, `imx-hdmi-soc`, `usb-ci_hdrc` in the ALSA card list),
armv7. 495 MB RAM, 3.3 GB free on `/sdcard`.

**The root filesystem is mounted read-only.** Run `/root/fw_dir/scripts/remount-rw.sh` before
writing to `/root`, and `remount-ro.sh` after. `/sdcard` and `/usbdrive` are writable.

**`/root/.pdsettings` is device-resident state with no off-device backup.** It holds the
`midiapi: 1` and 4-in/4-out configuration that the whole MIDI topology depends on, and
`/root/.pdsettings.bak` sits on the same card. Pull a copy into this repo. ⬜ not yet done.

### How Pd is launched

Pd is launched by the `mother` binary, not a shell script:

```
/usr/bin/pd -rt -nogui -audiobuf 6 -path /sdcard/PdExtraLibs /root/fw_dir/mother.pd main.pd
```

No `-noprefs` and no MIDI flags, so **`/root/.pdsettings` governs MIDI** and editing it is the
way to add devices. Note `-audiobuf 6` on the command line overrides `audiobuf: 4` in
`.pdsettings` — command-line flags win.

**`-nogui` means there is no Pd console.** Patch errors go to stdout on tty1, so VNC will not
show them either. This is why error reporting to the OLED is treated as an architecture
requirement rather than a debugging convenience — see [plan-conventions.md](plan-conventions.md).

### MIDI: OSS vs ALSA

Out of the box, Pd here runs on **OSS MIDI**, not ALSA — `.pdsettings` has `flags: -alsamidi`
but **no `midiapi:` line**, and the `flags:` preference is not applied under `-nogui`. Under
OSS, devices appear as `/dev/midiN` where N tracks the ALSA card number, one node per card —
so the Launchpad's three separate ports collapse into one and Programmer Mode may be
unreachable.

ALSA MIDI *does* work on this build (`pd -alsamidi` registers a `Pure Data` client with in/out
ports). The fix is adding `midiapi: 1` to `/root/.pdsettings`. Under ALSA, Pd creates its own
virtual ports and hardware is wired to them with `aconnect` **by name**, which also solves
USB-enumeration-order drift across reboots.

### Deploying

Deploy with `./deploy.sh`, then press **Storage → Reload** on the device. Because there is no
rsync, locally-deleted files linger remotely — use `./deploy.sh --clean` after renaming or
removing an abstraction, or a stale `.pd` will shadow the new one.

Patch storage falls back from `/usbdrive` to `/sdcard` based on whether `/usbdrive` is
*mounted*, not whether it holds patches. An empty mounted USB drive yields an empty patch
menu; Storage → Eject unmounts it without physical removal.


## Device capabilities

What each box can actually do, verified on hardware. What to *build* with it lives in
[plan-software.md](plan-software.md); the message-by-message detail — every CC, note and
SysEx each device accepts and transmits — lives in [plan-midi.md](plan-midi.md).

### Launchpad Pro MK3 — a genuine blank slate

**Physical layout.** An 8×8 grid of RGB pads, surrounded by large function buttons on the
left, right and top, plus a double row of smaller buttons across the bottom. Left column
selects modes (Session, Note, Chord, Custom, Sequencer, Projects); right column is scene
launch; top row is navigation; bottom rows are track select and Ableton controls. In
Programmer Mode all of that labelling becomes meaningless — every button is just a note
number you define.

The pads are **velocity *and* pressure sensitive** (polyphonic aftertouch). They are not
switches.

**Programmer Mode** is officially documented (Novation publishes a
[Programmer's Reference Manual](https://fael-downloads-prod.focusrite.com/customer/prod/s3fs-public/downloads/LPP3_prog_ref_guide_200415.pdf)),
not a hack. In it:

- All built-in modes are disabled. The firmware gets out of the way completely; every pad
  just sends note-on/note-off.
- You drive every LED yourself. Note-on to a pad's note number, velocity selects from a
  128-colour palette. SysEx gives full RGB.
- Static / flashing / pulsing are MIDI channels 1 / 2 / 3 — so blinking a pad costs one
  message, no timing logic in Pd.
- Note layout is row/column encoded: pad at row *r*, column *c* is note `r*10+c` (11–88).
  `div 10` and `mod 10` gets you coordinates, no lookup table.
- Entering it is either a button combo (hold SETUP, press the bottom Scene Launch) or a
  SysEx message. Documented gotcha: entering via SysEx locks out the Settings menu until
  you send a SysEx selecting a different layout.

Unit is a **MK3** (MK3 announced Jan 2020; a 09/2020 build date rules out MK1). Use the MK3
reference — SysEx headers and side-button note numbers differ from MK1.

### nanoKONTROL (mk1) — visible position, no host LEDs

Replaces the BeatStep (see *BeatStep retired*, below). 9 channels, each with **1 fader,
1 knob, 2 buttons**, plus a transport section and 4 on-device scenes. Class compliant,
USB bus-powered.

**The fit is good:** 9 knobs + 9 faders = 18 continuous controls against Cut It's 16.
**Two channels per filter** gives 2 knobs + 2 faders — exactly the four per filter — across
8 channels, leaving **one channel spare** for global volume or master tempo.

**The win over endless encoders is visible position.** A knob's physical position *is* the
display, which is the legibility problem the BeatStep could never solve.

**The cost is parameter pickup.** Any control serving two parameters stops matching its
stored value on a bank switch. The primary layer avoids this entirely via the 1:1 mapping,
but the shift layer still doubles up. Options are jump (snaps, jarring), pickup (dead until
it crosses the old value) or scaled. **Use jump** — a sudden parameter jolt is entirely on
brand here, so the usual reason to avoid absolute controllers mostly does not apply.

**No host-controllable LEDs.** External LED mode is a nanoKONTROL2-only feature; on the mk1
the button LEDs reflect local state only and Pd cannot drive them.

**Therefore: set every button to momentary** in Korg Kontrol Editor, and let Pd own all
toggle state, displayed on the Launchpad. A toggle button with no host LED control keeps its
own state, and that state can silently desync from Pd's — exactly the invisible-failure mode
the FX-send routing was rejected over. Momentary buttons are pure events with no state to
desync.

**On the four scenes:** useful for multiplying control count, but they are hidden state — the
device switches locally and Pd has no idea. Assign **distinct CC numbers per scene** so Pd
infers the active scene from which CCs arrive. Do that and scene switching self-announces;
don't, and it is the unlabelled-knob problem in a worse form.

**Configured and verified on hardware.** Editor version **2.4.0** is required — Korg's 2.5.0
dropped first-generation nanoKONTROL support, and it's available from the "previous versions"
list on the [KONTROL EDITOR download page](https://www.korg.com/us/support/download/software/1/133/1355/).

| Control | CC | Pd decode |
|---|---|---|
| Sliders 1–9 | 1–9 | `div 10` = 0 |
| Knobs 1–9 | 11–19 | `div 10` = 1 |
| Buttons, top row 1–9 | 21–29 | `div 10` = 2 |
| Buttons, bottom row 1–9 | 31–39 | `div 10` = 3 |

`cc mod 10` gives the channel number in every case — the same addressing idiom as the
Launchpad's `r*10+c` grid, so one decode pattern covers both surfaces.

All buttons are **momentary**, verified sending 127 on press and 0 on release. Pd owns all
toggle state. Arrives on **Pd channel 17** (device 2).

**No LED Mode setting exists** on the mk1 — confirmed in the editor, not just inferred. All
visible state has to live on the Launchpad.

### BeatStep retired

Dropped from the plan. Its sequencer is beaten by the Launchpad's (4 tracks × 32 steps ×
8-note poly vs 16 steps mono), its 16 pads are beaten comprehensively by 64 RGB
pressure-sensitive ones, and its CV/Gate outputs are irrelevant with no modular in the rig.

It does have host-controllable pad LEDs (red, on/off) which the nanoKONTROL mk1 lacks — the
one axis where it wins. But the Launchpad covers every state-display need in the rig, and
visible knob position plus a bank of faders is worth more here than a second grid of red
lights.

### SP-404 MIDI — verified working, both directions
Confirmed on hardware, no settings changes required. The 404's factory MIDI config is
already correct for this rig.

**Receive (404 → Pd):** pad presses and knob moves arrive on **Pd channel 33** (device 3).
Pads transmit notes, CTRL knobs transmit CC 16 and 17.

**Send (Pd → 404):** `[noteout 33]` triggers pads. **Pad *n* on bank A = note 47 + *n***
(pad 1 = 48, pad 2 = 49), established empirically. Velocity 100 works; `[makenote]` handles
note-offs.

**Relevant device settings, all already correct:**

| Setting | Value | Why |
|---|---|---|
| MIDI Sync Out | Off | No clock echoed back to the Organelle |
| Soft Through | Off | No MIDI echo loop |
| USB-MIDI Thru | Off | Same |
| PAD Note Out | On | Pads transmit |
| SEQ Note Out | On | Pattern sequencer transmits — enables compose-time capture |
| MIDI Mode | A | Bank A receives on MIDI channel 1 |

**Cable warning:** the 404 needs a genuine **data** USB cable. Charge-only USB-A→C cables are
visually identical and extremely common; two were tried before one worked. If the device does
not appear in `lsusb`, suspect the cable before anything else.


---


## Open questions to verify on the hardware

### Resolved

| Question | Answer |
|---|---|
| Organelle's Pd version | **Pd 0.49.0**, compiled Oct 9 2018. OS 4.0. |
| Where Pd's startup flags live | **`/root/.pdsettings`** — mother passes no `-noprefs` and no MIDI flags. Already edited to 4 in / 4 out with `midiapi: 1`. |
| USB enumeration stability | **Moot.** Devices are wired with `aconnect` **by name**, so client renumbering is harmless — demonstrated live when client 28 changed from Launchpad to SP-404 mid-session. No udev rules needed. |
| Does the 404 transmit its own pad presses? | **Yes**, `PAD Note Out: On`. Verified arriving in Pd on channel 33. |
| Does Korg Kontrol Editor run? | **Yes, version 2.4.0** — 2.5.0 dropped first-generation nanoKONTROL support. Nano is configured and written. |

Details in [plan-tests.md](plan-tests.md) and *Device capabilities* above.

### Still open

**1. How the 404 places external input in the stereo field — and whether it can be pinned to
one side.** The load-bearing unknown for the drums/fx split, and the only substantial one
left. The claim that a mono input sums to both sides comes from user documentation, not
Roland's spec sheet, and nothing documents whether it can be constrained.

**Not answered by the 404's discrete L/R jacks.** It has separate L and R connectors on both
line in and line out, so two independent signals certainly *leave* the box — but this question
is about internal routing of the external input, which the connectors say nothing about. The
Y-cable is also still required regardless: the constraint is the **Organelle's single TRS input
jack**, not the 404's outputs.

One session answers it. Monitor the 404's L and R outputs separately (headphones, or the
mixer one channel at a time), play a sample panned hard MONO(Left), and:

- **a.** Feed the **MIC/GUITAR IN**. Does the mic appear on the L output alongside the drum
  sample? Expected: yes, it sums to both. If it doesn't, the accepted bleed compromise is
  unnecessary and the design gets simpler.
- **b.** Look for **any pan or routing control for the external input** — input FX settings,
  bus assignment, anything that shifts it off centre.
- **c.** Feed **LINE IN R only**, nothing in L/MONO. Does the signal stay on the right, or sum
  to both? Its partner jack being labelled L/MONO is suggestive but not conclusive. A "stays
  right" result opens up the mic → mixer preamp → LINE IN R path, giving hard-panned live
  vocals through the 404's input FX.

Outcome (a) confirms the plan as written. Outcomes (b) or (c) would be upgrades, not
requirements — the rig works either way. This is Session 3 in the pre-flight list and needs
the TRS Y-cable.

**2. Does the 404's *pattern playback* transmit notes?** Partially answered: `SEQ Note Out`
is **On** in the device settings, which is the setting that governs it, and pad presses
demonstrably transmit. But no pattern has actually been run and captured. Low stakes —
determines whether the 404 works as a compose-time authoring surface alongside the Launchpad,
and there are scattered reports of a stray continuous C-note when external input is on, which
would need filtering on capture.

**Deferred: the footswitch and expression pedal.** `mother.pd` exposes `fs` / `fsRaw` /
`footSwitchPolarity` and `exp` / `expRaw` / `expOverride` on the 1/4" pedal jack — a
sustain-style switch or an expression pedal, one or the other, not both. Deliberately **not
used in v0.2**; noted so it isn't rediscovered as news. It remains the obvious control to reach
for when both hands are busy.

**3. How do you see Pd's error output?** Unsolved, and it will bite during the rewrite. Pd is
launched with `-nogui`, so there is no console; errors go to stdout on tty1, which VNC will
not show either. Running Pd manually over SSH works for diagnostics (see [tools/](tools/)) but
not for patches loaded normally through the Organelle's menu. Options not yet explored:
redirecting mother's output to a file, reading tty1 remotely, or having the patch report
errors to the OLED.


## Gear

### Owned
| Item | Role |
|---|---|
| Organelle (original) | Brains — Pd, USB MIDI host, clock master |
| Roland SP-404MK2 | Sample store, mic/line front end, drums + fx source |
| Behringer Xenyx Q802USB | Mixer, and free session recording over USB |
| Korg Volca FM | Pitched voice (DIN MIDI in only) |
| Korg nanoKONTROL (mk1) | Continuous control — 9 faders, 9 knobs, 18 buttons, transport |
| Novation Launchpad Pro MK3 | Cut It interface (Programmer Mode) + compose-time sequencing |
| MeeBlip cubit (original) | **See below — does not do what we need** |
| Arturia BeatStep | **Retired from the plan** — see *BeatStep retired* above |

### The original cubit does not work here
The original cubit is a **thru box only**: 1 DIN in → 4 DIN out. Its USB port supplies
**power only and carries no data**, so it cannot act as a USB MIDI interface for the
Organelle. (That capability came later, in the cubit *go* and cubit *duo*.)

Keep it. It becomes useful the moment you add a second or third DIN-only synth — put it
downstream of the MIDI interface and fan out to four destinations. For now only the Volca
FM needs DIN, so a 1×1 interface is enough.


## Shopping list

Power supplies are all assumed covered. Everything below is either a box you don't own or a
cable to dig for first.

### Definitely buy — hardware you don't have

| # | Item | Notes |
|---|---|---|
| 1 | **Powered USB hub**, 4+ USB-A ports, own PSU | Not optional. The Launchpad Pro MK3 is a real power draw; bus-powering it plus the other USB devices off the Organelle will brown out, and it presents as intermittent MIDI dropouts rather than an obvious failure. |
| 2 | **Class-compliant USB→DIN MIDI interface** | For the Volca FM. Roland UM-ONE mk2 (set to the class-compliant "TAB" position), iConnectivity mio, or similar. |
| 3 | **Dynamic microphone** | SM58 or equivalent. Dynamic rather than condenser — better SPL handling and far better feedback behaviour, and you're building a rig where a mic feeds a processor that feeds the PA. |

### Cables — check the cable box first

Most of these are ordinary. Item 4 is the one you probably don't already have.

| # | Cable | For | Likely already own? |
|---|---|---|---|
| 4 | **1/4" TRS male → 2× 1/4" TS male** ("insert cable") | 404 OUT L/R → Organelle's single stereo input | ⚠️ **Unlikely.** The critical cable in the whole rig — nothing else does this job. |
| 5 | **USB-A → USB-C** | Hub → SP-404MK2 (data only) | Probably. The 404 ships with no USB cable, but these are everywhere now. |
| 6 | **2× 1/4" TS patch cables** | Organelle OUT L/R → mixer ch1/ch2 | Probably |
| 7 | **3.5mm TRS → 2× 1/4" TS** | Volca FM → mixer ch3/4 | Maybe. Volca's output runs hot — start with channel gain low. |
| 8 | **XLR female → 1/4" TRS** | Mic → 404 MIC/GUITAR IN | Maybe. The 404 has no XLR, so a plain mic cable won't do it. An XLR→1/4" adapter on a normal mic cable also works. |
| 9 | **2× 1/4" TS** | Mixer MAIN OUT → PA | Probably. Length to suit the venue. |

### Already in the box with gear you own — don't buy
- **Launchpad Pro MK3**: USB-C→USB-A *and* USB-C→USB-C cables, a USB-A power adapter, and
  3× TRS-minijack→DIN MIDI adapters.
- **nanoKONTROL**: bus-powered over its own USB cable — check which connector the mk1 uses
  before assuming you have a spare.
- **SP-404MK2**: PSD AC adapter (but no USB cable — see item 5).

### Optional / probably eventually
- **MeeBlip cubit duo** — replaces item 2 *and* your original cubit in one box (USB MIDI
  interface + 4-port thru, switchable, class compliant, tight timing). Worth it if you
  expect to add more DIN synths; overkill for one Volca.
- **Ground loop isolator** — five separately-powered devices tied together by unbalanced
  cables makes 50/60Hz hum likely. Don't buy pre-emptively, but know this is the cause if it
  appears, rather than chasing a "bad cable".
- **Cable labels or tape.** With this many identical 1/4" cables, worth the ten minutes.
