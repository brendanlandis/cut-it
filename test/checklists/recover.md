# Recover checklist

Panic's second tier, and the only checklist that deliberately breaks the instrument. `recover-assert` lints the two-step OSC by reading it and drives both tiers against a stubbed `[shell]`; what no gate can do is load a patch, so the reload itself is here and only here, with the case that matters most: a reload that cannot land.

Steps 1 and 2 are the short press, step 3 the hold, step 4 the breadcrumb consumed. Steps 5 and 6 make the reload fail on purpose, and step 7 puts the rig back. Step 5 leaves the rig with no patch at all.

7 steps. How to read one, and how to send a **Send** line: [the checklists' README](README.md). Why each thing behaves as it does: [map](../../ref/module/map.md), [boot](../../ref/module/boot.md).

- [ ] **1. Short press — panic and nothing more**
  - **Need:** The Launchpad lit and in Programmer Mode, in any mode but 1 — mode 1 is the drum page, where the beat row gives way. Something audible running — the drums, with a pattern stored, are easiest.
  - **Do:** Start the transport so the drums play, then tap the top left corner button on the Launchpad once and let go straight away.
  - **Pass if:** The drums stop the instant the button goes down — not when you let go — and no new hit sounds after it. The whole Launchpad flashes red and clears itself about a second later. The aux LED is red and the footer reads panic. The patch is still running: the grid comes back and the beat row still walks.

- [ ] **2. Short press — the Volca stops too**
  - **Need:** The Volca powered and its own sequencer running. The Volca's MIDI Clock src set to Auto. Set to Internal it ignores Start and Stop entirely and this step cannot pass.
  - **Do:** Set the Volca sequencing on its own, then tap the top left corner button once.
  - **Pass if:** The Volca stops sequencing. Before this was built its transport never heard anything at all — it kept running through a panic and the mixer could only mute it.
  - **Note:** The Volca honors Start and Stop only with MIDI Clock src on Auto — Korg's documentation, not measured ([volca](../../ref/device/volca.md)). Only panic's stop reaches port 4, never the clock (items 279, 295).

- [ ] **3. Hold — the patch reloads and comes back whole**
  - **Need:** A Save done at some point, so knobs.txt exists. Without one nothing would be held on an ordinary boot either and the last sentence proves nothing.
  - **Do:** Hold the top left corner button for a full two seconds and let go. Then watch the screen, and afterwards turn knob 1 a little.
  - **Pass if:** Silence at once. About two seconds later the screen goes through its boot sequence again and the instrument comes back with every device working — the Launchpad lit and answering and both output devices reachable. A few seconds in a bordered alert reads warn and then u_map and then recovered. Knob 1 moves the tempo on the first touch with no dead sweep.
  - **Note:** The alert is deferred to about 4.5 seconds after the reload, clear of the boot stages, and lasts about two. The reload does not arm pickup — after an emergency the knobs in hand are the truth — so a knob that needs a sweep fails here.

- [ ] **4. ...and the breadcrumb was consumed**
  - **Check:** `./tools/fetch-state.sh --show` and read `cut-it-recover.txt`.
  - **Pass if:** Cut-it-recover.txt reads none. The instrument wrote it just before the reload and cleared it once it had reported — so none means the whole cycle completed. Finding the word recover still in there means the report never ran.

- [ ] **5. Break it deliberately — a reload that cannot land**
  - **Need:** An ssh session to the Organelle already open. The patch is about to stop existing, so this is not the moment to go looking for one. The root filesystem left alone — the patch lives on /sdcard and needs no remount.
  - **Do:** Over ssh run `mv "/sdcard/Patches/!/Cut It" "/sdcard/Patches/!/Cut It away"`, then hold the top left corner button for two seconds.
  - **Pass if:** Everything goes quiet and then nothing comes back at all. The screen stays dark or frozen and the Launchpad stops answering. That is the failure this is meant to produce.
  - **Note:** A dead patch cannot report its own failed reload; the breadcrumb survives to say one was tried, and step 6 reads it.

- [ ] **6. The breadcrumb survives to explain it**
  - **Check:** `./tools/fetch-state.sh --show` and read `cut-it-recover.txt`.
  - **Pass if:** Cut-it-recover.txt still reads recover and a number. Nothing on the instrument could have told you what happened — it was dead — so this file is the whole account of it.

- [ ] **7. Put it back — and the safe exit still works**
  - **Need:** The renamed folder from the step before, still renamed.
  - **Do:** Over ssh run `mv "/sdcard/Patches/!/Cut It away" "/sdcard/Patches/!/Cut It"`, then load Cut It from the Organelle menu, let it settle, and leave it by selecting a different patch.
  - **Pass if:** The instrument loads and runs normally again. When you leave it the Launchpad returns to Live Mode — its pads show a built-in layout and its Setup button responds. A Launchpad still dark and ignoring Setup is the failure.
  - **Note:** Through the menu or `/loadPatch`, never `killall pd`: a killed Pd skips `m_launchpad`'s safe exit and strands the surface in Programmer Mode (item 96).
