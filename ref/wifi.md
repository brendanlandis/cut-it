<!-- schema: freeform -->
# Wifi

**The Organelle drops its wifi on house networks, and what is established about why is in Reference:**
`~/Sites/!reference/critter-guitari-organelle-1.md` (under *Wifi*: where the credentials live, the roam
fault and its reproduction, the evidence ledger by item number, and the Organelle as its own access
point). It is narrowed, not solved. The fault matters because the phone display is the instrument's
second screen — [device/phone.md](device/phone.md) — and a dead display mid-set is the failure being
designed against. **Item numbers still resolve by `grep` — now in `~/Sites/!reference/`.**

**This page holds Cut It's side: the tools that watch it, what to do when it recurs, and the stage
procedure.** What is still open, what to try when it recurs and when to stop is `cut-it/wifi-roam-fault`
in `!projects` — closed 2026-10-10 after two months without a recurrence, and reopened (moved back to
`active/`) if it recurs. ⚠️ **Do not spend session time on this unless it recurs.**

**The boot hang that used to look like a wifi fault is not one** — it is a USB mass-storage fault with
wifi as its most visible casualty, and it lives on [device-os.md](device-os.md).

## Credentials

`$USER_DIR/wifi.txt` is plaintext, never copied into this repo, and [device/](../device/) deliberately
does not back it up. ⚠️ `/root/fw_dir/scripts/wifi-config.sh` is a stale template and
`/etc/wpa_supplicant/wpa_supplicant.conf` is a red herring (Reference): `tools/wifi-reassociate.sh` is
the correct sequence — it mirrors what the front panel does, with the real credentials.

## The tools that watch it

| Tool | Runs on | Does |
|---|---|---|
| `tools/wifi-watch.sh` | **the device** | Polls `wlan0`, and on a failure runs a **link probe** and a **DHCP probe** before a recovery ladder |
| `tools/wifi-poll.sh` | the Mac | Watches from outside, so a device that has gone silent still produces a record |
| `tools/wifi-report.sh` | the Mac | Summarizes `wifi-watch.log` |
| `tools/wifi-reassociate.sh` | the device | The recovery rung that mirrors what the front panel does. **The only one that has ever worked** |

⚠️ **`--mark` goes AFTER a finding is written up, never before.** It draws the analyzed-to-here line,
so running it first erases the event you were about to read.

⛔ **NEVER `pgrep -f wifi-watch`.** It matches the `ssh` command doing the checking, so a sweep that
scans and relaunches in one command kills its own session. Item 163, and it has bitten three times.

✅ **The watcher starts at boot** — `device/wifi-watch.service`, installed at
`/etc/systemd/system/` and enabled (item 244). ⛔ **A watcher that is not a service disarms itself
on every recovery**, because a reboot is how this fault gets recovered and nothing would restart it
afterwards — a drop after such a reboot leaves no evidence at all. `tools/wifi-poll.sh`'s relaunch
is the backstop for a mid-session death rather than the primary mechanism, and it counts consecutive
failed relaunches instead of retrying in silence.

⚠️ **`/root` is read-only** — `remount-rw.sh` before installing or enabling the unit, `remount-ro.sh`
after, because `systemctl enable` writes a symlink into `multi-user.target.wants/`.

⛔ **`After=network.target` is far too weak here, and the unit waits for an address instead.** At
`network.target` the clock is still at 2015, `assoc: Not connected` and `wpa_supplicant=- dhcpcd=-`;
a watcher started there runs no recovery, but its first sample is `NONE`, so the ordinary boot-time
DHCP acquisition is logged as `TRANSITION NONE -> <address>` — and **`wifi-poll.sh` counts
`TRANSITION` lines as drops**, so every boot would add a phantom one and trip *ANYTHING NEW?*. The
unit polls for an IPv4 in `ExecStartPre`, **bounded at 120 s and starting anyway when that
expires** — a device that never gets an address is exactly when the watcher is wanted.
`TimeoutStartSec` has to exceed the bound; the systemd default of 90 s does not.

✅ **Verified across a real reboot**: the service comes up `active`, its opening block carries a
populated `ipv4:` and the SSID, and **no `TRANSITION` is logged at boot**. The header is still
stamped `2015`, which is the expected proof that it starts before the clock is corrected.

⛔ **BUT THAT HOLDS ONLY IF A LEASE ARRIVES INSIDE THE 120 s BOUND, AND ON THIS RIG IT OFTEN DOES
NOT.** The device is joined to the house network **by hand at the front panel** — neither the house
network nor the AP connects automatically, and that is deliberate. So the lease normally arrives
*after* `ExecStartPre` has timed out, the opening block carries an **empty** `ipv4:`, and the
hand-connect is then logged as `TRANSITION NONE -> <address>`. ⚠️ **`wifi-poll.sh` counts
`TRANSITION` lines as drops**, so **a phantom drop is the normal outcome of a hand-connected boot**,
not a one-off. Item 299.

⛔ **Discount the first `TRANSITION` of every session before reading the log as evidence of a
drop** — its opening block reads `ipv4:` empty followed by `TRANSITION NONE -> <address>`, and
otherwise a configuration change is credited or blamed for a transition that is only somebody
pressing Connect.

## Operating the watcher

- **Run `./tools/wifi-report.sh --mark`** once a finding is written up, or the report reads the
  same before and after the next failure.
- **Do not run two watchers.** Use the pidfile, or `ls -l /sdcard/wifi-watch.alive`.
- ⚠️ **NEVER `pgrep -f wifi-watch`**, and never let one command both scan and relaunch — that
  self-match kills the ssh session doing the sweeping. Item 163.

## If it recurs

**Reopen `cut-it/wifi-roam-fault`** in `!projects` first: it holds what to try, in what order,
and when to stop: two router-side changes, then a binding stopping rule that closes item 81 as won't-fix and lets AP
mode be the answer. Verify against the repro above, not against a quiet spell.

⛔ **DO NOT RE-ENABLE THE PREFERRED-AP STEER, and it is tempting precisely because it looks like a
fallback.** It **drops IPv4 itself on every fire**, so it manufactures the symptom it is meant to
avoid — and worse, **it hides the answer by preventing recurrence**, leaving nothing to measure.
Item 214 is why it stopped being trusted.

## The stage procedure

**The venue sequence is the operating procedure, not one option among several.**

**No laptop, no venue wifi, phone in airplane mode:**

1. Organelle: **System → WiFi Setup → Start AP**
2. Phone: airplane mode on, wifi back on, join **`organelle`**
3. Organelle: load **Cut It** — `phone-ip.sh` finds the phone's address from the DHCP lease

✅ Verified end to end. Airplane mode is what makes this worth doing: a phone *hotspot* needs
cellular, an AP the Organelle hosts does not.

⛔ **NEITHER NETWORK CONNECTS AUTOMATICALLY, AND THAT IS A CHOICE RATHER THAN A GAP.** The house
network and the AP are each a couple of front-panel presses, deliberately — **there is no boot-time
service to write and none should be added.** ⚠️ The consequences are already recorded and are easy
to mistake for faults: a hand-connected boot logs a phantom `TRANSITION` (item 299), and **a set run
without step 1 is a client on house wifi again**, carrying the roam fault onto the stage.

⚠️ **Start the AP from the SYSTEM MENU, not from a patch** (Reference, item 129):
`tools/stage-patches/Start AP/` is kept only as the record of why.

⛔ **SO AN AP SESSION HAS TO BE SELF-SUFFICIENT BEFORE IT STARTS.** Staged on the device beforehand:

- **`/sdcard/ap.txt`**, passphrase valid (8–63 characters, one-word name — Reference).
- **The instrument deployed and loaded**, and the phone's scene open.
- **Anything the session needs to record written to `/sdcard/`** — the `AP Probe` pattern, read
  afterwards; it is indexed in [tools/README.md](../tools/README.md). ⚠️ **Nothing has to be caught
  live**, which is the same reasoning as `u_err`'s persistent log.

## Open

⬜ **Why nothing answers a DISCOVER after a roam.** **Not established**, and the one thing that
would turn the roam fault from narrowed into solved. ⚠️ Say so plainly — this investigation has
already produced two confident wrong answers. Owned by `cut-it/wifi-roam-fault`.

⬜ **Three drops on 2026-08-08 that did NOT match the roam signature** — nothing answered on
either protocol from the Mac, yet the device was associated with the lease held and uptime
unbroken. Not item 81's signature, and not to be folded into it without new evidence. The record
is on `cut-it/wifi-roam-fault`; item 244 exists so the *next* one is recorded.
