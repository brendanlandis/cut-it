<!-- schema: freeform -->
# The development loop

Two devices, neither with a usable console, both reachable over the network.

**Most work happens on the Mac, with the Organelle switched off.** Open `Cut It/main-dev.pd` in
Pd 0.49: `u_mother-stub` supplies `knob1`–`knob4`, `vol`, `notes`, `aux`, `enc` and `encbut` as
GUI controls, and previews everything the patch writes to `screenLine1`–`5` and `oscOut`. It
shows *what* is drawn, not *where* — pixel-accurate OLED rendering is deliberately out of
scope. Reach for the hardware when the thing you are testing is the hardware.

**The Pd rules this loop exists to serve are [conventions.md](conventions.md)**, `C-1`…`C-14`.
This page is how you run the thing; that page is how you write it.

## `./tools/deploy.sh` — the whole loop, one command

```
edit in repo  →  syntax check  →  scp  →  reload patch list  →  load the patch
```

No walking to the device, no Storage → Reload, no selecting from the menu.

| Env | Effect |
|---|---|
| `--clean` | wipe the remote copy first |
| `NOCHECK=1` | skip the syntax check |
| `NORELOAD=1` | skip refreshing the patch list (which uses `/reloadNoRemount` — see below) |
| `NOLOAD=1` | push but leave the running patch alone |
| `HOST=` `DEST=` `PD=` | target, destination, Pd binary |

**The syntax check is built in and blocking.** Pd 0.49-1 on the Mac is the same version the
Organelle runs:

```sh
/Applications/Pd-0.49-1.app/Contents/Resources/bin/pd \
    -nogui -noaudio -send "pd quit" path/to/main.pd
```

Silence means it parsed and every object instantiated. **Pd exits 0 even when objects fail to
create, so the gate is output, not exit status** — `tools/deploy.sh` captures stdout and stderr and
refuses to copy anything if either is non-empty. This catches the entire class of load-time
errors — misspelled objects, malformed iemgui lines, bad connections — that would otherwise
vanish into tty1 on a device with no console.

**Refresh with `/reloadNoRemount`, never `reload.sh`.** `reload.sh` sends `/reload`, which also
runs `mount.sh`, which mounts the last `/dev/sd*` on `/usbdrive`. With a Launchpad attached that
is its write-protected onboarding drive, and mounting it moves `USER_DIR` onto a read-only
volume — breaking wifi config, Save and Save New. The guard that stops it, and how to revert it,
are in [device/README.md](../device/README.md).

**The load step needs the category folder in the name.** `mother`'s `/loadPatch` resolves
against its *current* patch directory (`MainMenu::runPatch` builds `getPatchDir() + "/" + arg`),
and `/reload` resets that to the default — `/usbdrive/Patches` if it exists, else
`/sdcard/Patches`. Since the patch lives in `/sdcard/Patches/!`, the argument is `!/Cut It`.
A bare `Cut It` loads nothing, silently. `tools/deploy.sh` derives this from `DEST`.

| Target | Deploy |
|---|---|
| Organelle | `./tools/deploy.sh` |
| iPhone (PdParty) | `curl -T <file> http://<phone>:9000/<scene>/_main.pd` over WebDAV |

Neither needs a cable. See [device/phone.md](device/phone.md) for addresses and ports.

**What the check cannot catch** is runtime behaviour — wrong message types, silent OSC
failures, logic errors. That is what the error bus (`C-12`) and the PdParty remote console are
for — and the run-it-yourself trick immediately below, which is better than both.

## Small macOS gotchas

Each of these has cost a wasted command:

- **There is no `timeout`.** Use a background PID and `kill`, or have the patch quit itself.
- **`airport -I` is deprecated** and reports "not associated" even when Wi-Fi is up. Use
  `ipconfig getifaddr en0`.
- **`cat -A` is GNU.** Use `cat -e`.

## There IS a console — launch the patch by hand

"The Organelle has no Pd console" is true only of the **menu-launched** patch, whose stdout goes
to tty1. Launch it yourself over SSH and you get the real thing:

⚠️ **`killall pd` STRANDS THE LAUNCHPAD IN PROGRAMMER MODE**, and the front panel cannot recover
it. **Run `./tools/lp-live.sh` afterwards.** Why the safe exit cannot fire from a shell signal, and
what `lp-live.sh` does about it, are on [device/launchpad.md](device/launchpad.md).
`tools/deploy.sh` is unaffected: it loads through mother's `/loadPatch`, so `quitting` fires
normally.

**If the probe only needs to SEND MIDI, do not use this at all — load a menu patch instead.**
`oscsend localhost 4001 /loadPatch s "!/<name>"` swaps the patch and swaps back through mother, so
`quitting` fires, the Launchpad is never stranded, and there is no `lp-live.sh` to remember.
`tools/stage-patches/PGM Probe/` is the worked example (item 228). ⚠️ **The probe must `aconnect`
Pd's output port for itself** — a patch load drops the connections, which is what `wire.sh` exists
to undo. Keep this section's console for when you need `[print]` output *back*.

```sh
ssh root@organelle.local
  killall pd; sleep 1        # ⚠️ then ./tools/lp-live.sh when you are done
  cd /tmp/patch
  nohup pd -nogui -rt -audiobuf 6 -path /root/Pd/externals \
      -path '/sdcard/Patches/!/Cut It' \
      /root/fw_dir/mother.pd main.pd /tmp/diag.pd > /tmp/diag.txt 2>&1 &
  sleep 6; killall pd
  cat /tmp/diag.txt
```

⚠️ **Single quotes around that path, not double.** The patch folder is `/sdcard/Patches/!/…`, and
**`!` inside double quotes is a history event in interactive zsh** — pasting the block gives
`zsh: event not found: /Cut` before anything reaches the device. Single quotes are literal in both
zsh and the device's busybox `ash`, so one form works everywhere. `tools/deploy.sh` never hit this
because a script is not an interactive shell.

Loading `mother.pd` alongside `main.pd` gives the patch its real environment — `inL`/`inR` carry
live audio, `oscOut` reaches the display. A third patch (`diag.pd`) can tap any bus with
`[print]` without touching the deployed files: `[r disp] → [print DISP]`, `[r oscOut] →
[print OSCOUT]`.

Restore normal operation with `./tools/deploy.sh`, which reloads and relaunches through the menu path.

**This found the `[list trim]` bug in Phase 1** — a `disp` message that `route` silently
rejected, showing as a plausible-looking zero on the OLED (`C-6`). Nothing else in the toolkit
would have caught it. Expect `error: /tmp/patch/knobs.txt: can't open` in the output; that is
mother looking for the optional knob-label file and is harmless.

## How a phase runs

Six phases have used the same shape and it is worth stating rather than rediscovering:

1. **A decisions table first**, with the *consequence* of each decision beside it — settled with
   Brendan before any code, because most of them change the shape of the work rather than its
   details.
2. **A Step 0 of measurements.** Anything the rest of the phase rests on that is still unverified —
   manufacturer documentation, or nothing but an assumption — gets measured *before* anything is
   built on it. **Every phase so far has had at least one assumption turn out wrong here**, and
   Phase 6's Step 0 changed two design decisions in an afternoon.
3. **Numbered build steps, each ending with both gates** before the next begins:

   ```sh
   python3 test/gate/pd-layout-check.py "Cut It"/*.pd
   /Applications/Pd-0.49-1.app/Contents/Resources/bin/pd -nogui -noaudio \
       -path mac-stubs -send "pd quit" "Cut It/main-dev.pd"     # silence == pass
   ```
4. **A bench** — a printed `PASS IF` *before* each step **including the ones whose correct result
   is that nothing happens**, and honest about which steps need hands. **Stepped by hand, never on
   a timer**: a self-driving bench moves the console text and the physical device at the same
   moment, so you can read one or watch the other and not both. Press GO to run the described step,
   press GO again to describe the next. Every bench is generated from the step tables in
   `test/bench/bench_steps.py` — edit those and re-run `test/bench/bench-gen.py`.

   ⚠️ **A measuring rig is code and gets the same scrutiny as the thing it measures.** Phase 5 had
   two bugs in its own probes, one of which produced a confident wrong answer about the clock;
   Phase 6's bench had an automated assertion that **nothing ever drove**, with a comment beside it
   claiming otherwise. **Where the rig can assert without eyes, make it** —
   `test/gate/display-assert.sh` rewrites `[midiout]` in a scratch copy so a headless run can read back
   every byte the patch emits, and it is proven to fail by reintroducing a real bug.
5. **A verification section separating Mac from device**, so what has actually been proven is never
   in doubt.
6. **A landing checklist**, and it is not optional — see *Where the abstractions go* in
   [conventions.md](conventions.md) and the doc-hygiene rules in [CLAUDE.md](../CLAUDE.md).
   Finished work moves to the git history; the phase's section *leaves*
   [plan-v04.md](../plan-v04.md) rather than being annotated; superseded designs are replaced, not
   annotated beside their replacement; anything unresolved moves to *Open questions*; and a new
   commit records the measurements, with items numbered **after the last used
   number in the file** — numbers are cited bare across documents, so **never reuse one**.
7. **The phase ends with a procedure, not a summary** — expected result stated *before* each
   action, for both machines. It lands in the commit **and** in chat, because chat is where
   it gets used.

**The bench proves the cases it contains and nothing else.** Phase 5's stickiest bugs — a stale
footer, a filter on the verdict instead of the value — were found by a person doing what a
performer would do. Budget hands-on time *after* the bench passes, not instead of it.
