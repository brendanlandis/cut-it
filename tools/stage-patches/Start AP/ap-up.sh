#!/bin/sh
# ⛔ THIS APPROACH DOES NOT WORK. KEPT ONLY AS THE RECORD OF WHY.
#
# The intent was to bring the Organelle's own access point up from the front
# panel with no laptop. ⚠️ IT CANNOT BE DONE FROM A PATCH. Measured, item 129
# item 129: create_ap, hostapd and dnsmasq are all children of the Pd that
# spawned them and die when the next patch loads -- which is the very next thing
# that happens, because the performer then selects Cut It from the menu.
#
# ⚠️ AND setsid + nohup DO NOT SAVE IT. An earlier version of this comment said
# they were "load-bearing" and that detaching into a new session was what let
# the AP outlive the patch. That was reasoning, not measurement, and the
# measurement contradicted it: the AP went down with Pd DESPITE setsid.
#
# ✅ USE THE DEVICE'S OWN MENU INSTEAD: System -> WiFi Setup -> Start AP. It
# predates this whole idea and is not a child of any patch. The venue sequence
# is in ref/device-os.md.
#
# start-ap.sh reads $USER_DIR/ap.txt: first line network, last line password,
# defaulting to Organelle / coolmusic. Ours says organelle / definitelycutit.
# It runs `killall wpa_supplicant` first, so ANY existing wifi connection drops
# -- including the one an ssh session is riding on. That is expected here.
setsid nohup /root/fw_dir/scripts/start-ap.sh >/tmp/ap.log 2>&1 &
echo ap-requested
