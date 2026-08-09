# What the instrument wrote

Backups of the data **Cut It itself produced** on the Organelle, pulled off the device by
[`tools/fetch-state.sh`](../tools/fetch-state.sh). Nothing here is deployed, and nothing here is
read by the patch — the instrument reads `/sdcard/cut-it-state/` on the device, never this folder.

⛔ **This is not [`device/`](../device/README.md), and the names are close enough to matter.**

| | Holds | Written by | If it is lost |
|---|---|---|---|
| `device/` | Configuration that exists **only on hardware** — the nanoKONTROL scene, `/root/.pdsettings`, the patched `mount.sh` | A person, once, with an editor or a Korg utility | Unrecoverable. That is why the folder exists |
| `device-state/` | What the **instrument** wrote while running — currently the mode, later the working pattern and a sampler's takes | `u_state`, on the device, unattended | Recoverable by playing the instrument again |

**Two files, and they are not the same kind of thing** — `cut-it-auto.txt` is running values,
rewritten on a timer; `cut-it-manual.txt` is committed takes, written only on Storage → Save.
The full reasoning, and why contributor-owned files land beside them, is in
[`tools/fetch-state.sh`](../tools/fetch-state.sh)'s header. The on-device format and the
`auto` / `manual` policies are on [ref/module/state.md](../ref/module/state.md).

⚠️ **20 bytes today, and that is expected.** Only `mode` persists on a v0.3 blank slate;
`cut-it-manual.txt` is empty because Save has not been pressed since the directory was last
cleared. **The value here is prospective** — v0.4 is what fills it.

⛔ **`test/gate/docs-check.py` never scans this directory** — `device-state` is in its `SKIP_DIRS`,
alongside `.git` and `__pycache__`, because the contents are instrument output rather than
authored material. **A broken link on this page will not be caught by the gate.** Check it by hand.
