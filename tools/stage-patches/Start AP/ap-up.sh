#!/bin/sh
# Bring up the Organelle's own access point, from the front panel, with no
# laptop involved. This is what makes a venue with no wifi workable.
#
# setsid + nohup are LOAD-BEARING. create_ap is started as a child of Pd, and
# the very next thing that happens is the performer selecting Cut It from the
# menu -- which quits this Pd and would take the access point with it. Detaching
# it into its own session is what lets it outlive the patch that started it.
#
# start-ap.sh reads $USER_DIR/ap.txt: first line network, last line password,
# defaulting to Organelle / coolmusic. Ours says organelle / definitelycutit.
# It runs `killall wpa_supplicant` first, so ANY existing wifi connection drops
# -- including the one an ssh session is riding on. That is expected here.
setsid nohup /root/fw_dir/scripts/start-ap.sh >/tmp/ap.log 2>&1 &
echo ap-requested
