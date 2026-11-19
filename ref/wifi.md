<!-- schema: freeform -->
# Wifi

**The phone is the instrument's second screen** ([device/phone.md](device/phone.md)), so the
Organelle's network is part of the instrument: on stage it hosts its own access point, and at home
it joins the house network. Both give it `192.168.1.15`, so the phone sends to one address
([device/s2/README.md](../device/s2/README.md), *Its address*).

**The Organelle 1 dropped its wifi on the house network** (the roam fault, item 81, never solved):
what was established is under *Wifi* on its Reference page, `critter-guitari-organelle-1`, and the
tools that watched it (`wifi-watch.sh` and its service, `wifi-poll.sh`, `wifi-report.sh`,
`wifi-reassociate.sh`, `find-organelle.sh`) left the repo with it on 2026-11-19, in git history
since. The S2 takes a fixed address on the house network rather than a lease, and its
NetworkManager reconnects by itself. If it drops anyway, start from its own log:
`sudo journalctl -u NetworkManager -u wpa_supplicant`.

## Credentials

NetworkManager keeps the house network's connection on the card, in `/sdcard/system-connections`,
never copied into this repo. The access point's name and password are the two lines of
`/sdcard/ap.txt`.

## The stage procedure

**The venue sequence is the operating procedure, not one option among several.**

**No laptop, no venue wifi, phone in airplane mode:**

1. Organelle: **System → WiFi Setup → Start AP**
2. Phone: airplane mode on, wifi back on, join **`organelle`**. The Cut It app sends to
   `192.168.1.15` on both networks.
3. Organelle: load **Cut It** — `phone-ip.sh` finds the phone's address from the access point's
   lease file

✅ Verified end to end on the S2 (2026-11-19) with the Cut It app. Airplane mode is what makes this
worth doing: a phone *hotspot* needs cellular, an access point the Organelle hosts does not.

⚠️ **The S2 rejoins `hildegard` by itself at boot**: its NetworkManager connects a saved network.
So a set run without step 1 is a client on the house network, or on no network at a venue.

⚠️ **The access point is plain WPA2 with AES** (`device/s2/wifi_setup.py`): the factory's left the
ciphers to wpa_supplicant, and an iPhone saw that network but never joined it (the S2's Reference
page, *OS 5.1*).

⛔ **SO AN AP SESSION HAS TO BE SELF-SUFFICIENT BEFORE IT STARTS.** Staged on the device beforehand:

- **`/sdcard/ap.txt`**, passphrase valid (8–63 characters, one-word name).
- **The instrument deployed and loaded**, and the phone's app open.
- **Anything the session needs to record written to `/sdcard/`**, read afterwards. ⚠️ **Nothing has
  to be caught live**, which is the same reasoning as `u_err`'s persistent log.
