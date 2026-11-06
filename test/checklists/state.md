# State checklist

Most of the data store is deliberately invisible: state is files, and `state-assert` proves the logic headlessly. What is left is only what hardware can show — the front-panel Save, a real power cycle and the page's lamp. Five steps rather than a padded twenty, because a checklist proves the cases it contains and nothing else.

5 steps. How to read one, and how to send a **Send** line: [the checklists' README](README.md). Why each thing behaves as it does: [state](../../ref/module/state.md).

- [ ] **1. Restored page at boot**
  - **Do:** Look at the Launchpad's two columns. Press nothing.
  - **Pass if:** The columns show the song's voices, dim, and one button bright if a voice's page was on show when it last went off, or none, for the performance page. A dark grid means nothing below can be read.

- [ ] **2. Change the page**
  - **Do:** Press the second button down the left column.
  - **Pass if:** It goes bright. Nothing else is visible yet and that is correct.

- [ ] **3. The change reached the disk**
  - **Check:** `./tools/fetch-state.sh --show` and read `cut-it-auto.txt`.
  - **Pass if:** Cut-it-auto.txt reads page voice 2. The file is the only evidence — nothing on the instrument shows it. The old page still being there is the failure.

- [ ] **4. Front-panel Save**
  - **Need:** Knob 1 parked where its row and the phone's tempo read 57 BPM. Every Save rewrites knobs.txt from the physical knobs, and midi 1 and tempo 2 both assert that restored value.
  - **Do:** Press Storage then Save on the Organelle. Storage is a top-level menu, not a System submenu.
  - **Check:** `ssh root@organelle.local date -r /sdcard/cut-it-state/cut-it-manual.txt` before the Save and again after it.
  - **Pass if:** The screen shows Saving briefly and returns. Then cut-it-manual.txt has a new timestamp even though it is still empty. An unchanged timestamp is the failure.
  - **Note:** A timestamp, because `cut-it-manual.txt` is still empty (nothing uses the manual policy yet): unchanged means `saveState` never arrived. Every Save rewrites `knobs.txt` from the physical knobs (item 139), hence the need.

- [ ] **5. Survives a power cycle**
  - **Need:** Every other checklist already run.
  - **Do:** Power cycle the Organelle and wait for it to come back.
  - **Pass if:** The same button is bright as before the power cycle.
  - **Note:** Last because a power cycle resets the device's uptime, which the wifi fault was measured against ([wifi](../../ref/wifi.md); closed since 2026-10-10 with no recurrence).
