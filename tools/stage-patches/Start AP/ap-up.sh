#!/bin/sh
# ⛔ This does not work, and is kept as the record of why: the AP started from a
# patch dies with that Pd at the next load, even behind setsid nohup (item 129).
# Use System -> WiFi Setup -> Start AP (ref/wifi.md, The stage procedure).
setsid nohup /root/fw_dir/scripts/start-ap.sh >/tmp/ap.log 2>&1 &
echo ap-requested
