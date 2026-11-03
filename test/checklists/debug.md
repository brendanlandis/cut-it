# Debug patch checklist

[The debug patch](../../ref/module/debug.md), and the only checklist whose every step is eyes: its output is the OLED and it writes nothing to disk. `debug-assert` proves the screen rows, the channel-block decode and both probes headlessly; what is left is what only hardware can show, above all step 3, that the patch wired itself.

Every step runs with Cut It stopped — selecting any patch restarts Pd — so this is not one to slot into the middle of a rig session. Step 9 puts the instrument back.

9 steps. How to read one, and how to send a **Send** line: [the checklists' README](README.md). Why each thing behaves as it does: [debug](../../ref/module/debug.md).

- [ ] **1. It is in the menu — under debug and not under the instrument**
  - **Need:** The debug patch deployed: `./tools/deploy.sh --debug` puts it there.
  - **Do:** From the Organelle menu browse the patch folders. Do not load anything yet.
  - **Pass if:** The Organelle menu has a debug folder beside the one holding Cut It — and Cut It Debug is inside it. Finding it in the same folder as the instrument is the failure. At a venue you should scroll past nothing to reach what you play.

- [ ] **2. It loads and comes up on the MIDI screen**
  - **Need:** You are not in the middle of a set. This stops the instrument.
  - **Do:** Select Cut It Debug and wait.
  - **Pass if:** Within a couple of seconds the screen reads 1-MIDI-IN with four rows under it — lp nano sp404 and ch — all reading zero. A screen that stays on the menu or goes blank is the failure.

- [ ] **3. It wired itself — and proving that is the whole checklist**
  - **Need:** The nanoKONTROL plugged in and its scene loaded.
  - **Do:** Move fader 1 on the nanoKONTROL a few times and watch the nano row.
  - **Pass if:** Moving a nanoKONTROL fader makes the nano row count up. This is the step everything else rests on: loading any patch drops the ALSA connections and the patch runs wire.sh itself to put them back. A nano row stuck on zero means the patch is measuring silence and would report a healthy rig as dead.
  - **Note:** The nano proves the probe: it transmits the moment it is touched and needs no mode.

- [ ] **4. Each device lands on its own row**
  - **Need:** The Launchpad and the SP-404 both plugged in and powered.
  - **Do:** Press a Launchpad pad and then an SP-404 pad on bank A. Watch which row moves.
  - **Pass if:** A Launchpad pad moves only the lp row. An SP-404 pad moves only the sp404 row. Each one also changes the ch row to a number in that device's own block — ch 1 to 16 for the Launchpad and 33 to 42 for the 404 bank. Two devices sharing one row is the fault this patch exists to find.
  - **Note:** The row is the port, and the port is the device only while `wire.sh` has undone mother's auto-connect, which wires the lowest-numbered client to Midi-In 1 (item 274).

- [ ] **5. The error log screen shows what the instrument left behind**
  - **Do:** Press the fourth key from the bottom to select the error log screen.
  - **Pass if:** The screen reads 3-ERR-LOG and the four rows under it hold the last four lines of the instrument s own log with dots where the spaces were. Four dashes mean the log was empty or missing — which is a real answer and not a failure if the instrument has not raised anything.
  - **Note:** The log is `u_err`'s: loading this patch rolls the session that went wrong into `cut-it-err.log` ([error](../../ref/module/error.md)).

- [ ] **6. The network screen shows the address you type into the phone**
  - **Do:** Press the fifth key from the bottom. Read the ip row and check it against what the phone is pointed at.
  - **Pass if:** The screen reads 4-NETWORK and the row under it reads ip- followed by this Organelle's own address. That is the number PdParty needs — it will not resolve the name — and reading it here is what removes the last reason this rig needs a laptop to fix the phone link.
  - **Note:** Item 312: PdParty needs a literal address, and on the house network the lease moves (the addresses seen are on the Organelle's Reference page). On the access point it is always the same ([phone](../../ref/device/phone.md)).

- [ ] **7. Both output devices answer when you fire at them**
  - **Need:** The Volca powered and audible. The SP-404 powered and audible. Pad A1 may hold a looping sample — if it starts one, press the pad on the device to stop it.
  - **Do:** Press the second key from the bottom to see the test screen — then press the C an octave up and the D above it. Listen.
  - **Pass if:** The C an octave up plays a note on the Volca. The D above it plays pad A1 on the SP-404. The sent counter goes up by exactly one per press — two for one finger would mean a key release is firing as well as the press.

- [ ] **8. A re-wire by hand reports how many links it made**
  - **Do:** Press the sixth key from the bottom for the re-wire screen, then press the E an octave up twice.
  - **Pass if:** The re-wire screen reads 5-RE-WIRE and the links row shows a number rather than a dash — nine on the full rig. The runs row goes up by one each time you press the key. A links row still reading dash means wire.sh ran but said nothing back.
  - **Note:** It forks `wire.sh` itself: the presence bus's re-wire lives in the Pd this patch's load has already stopped.

- [ ] **9. You can get out of it — and the instrument comes back**
  - **Need:** Nothing else queued on the rig — this is the step that puts the instrument back.
  - **Do:** Press the lowest key. Then load Cut It from the menu and leave it once it is up.
  - **Pass if:** The lowest key returns you to the Organelle menu. Cut It then loads and runs normally — and when you leave it the Launchpad goes back to Live Mode with its Setup button responding. A Launchpad still dark and ignoring Setup is the failure.
  - **Note:** The lowest key is the only guaranteed way out: asking mother for the encoder would take the click too (items 313 and 314).
