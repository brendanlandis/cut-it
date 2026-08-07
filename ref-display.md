# Cut It — Visual Feedback

⚠️ **A POINTER STUB.** Everything that was here has moved. This file survives only because ten
other files still name it by path — including two `.pd` comments, where there is no link syntax to
follow. **It goes when those become citations.**

| Looking for | Now on |
|---|---|
| The `disp` bus, the layer model, geometry, the param list, `g_grid`, the ALERT buffer | [ref/module/display.md](ref/module/display.md) |
| The OLED graphics API, the four screen buffers, fonts, the ~200 ms lag, the aux LED colours | [ref/device/organelle.md](ref/device/organelle.md) |
| The Launchpad's 96 pads, Programmer Mode, lighting, the replug watchdog | [ref/device/launchpad.md](ref/device/launchpad.md) |
| PdParty, the status protocol, the access point, the notch | [ref/device/phone.md](ref/device/phone.md) |
| Why the nanoKONTROL can show nothing | [ref/device/nanokontrol.md](ref/device/nanokontrol.md) |
| Rule C-5, one owner per surface | [ref/conventions.md](ref/conventions.md) |

**Reference patches:** `tools/oled-probe/` for the graphics API and font measurement,
`tools/osc-bridge/` and `tools/status-display/` for the phone protocol,
`tools/pdparty-scene/CutItRemote/` for the phone side, `tools/alert-buffer-probe.pd` for the
off-screen buffer. What each proves and how to run it is in [tools/README.md](tools/README.md).
