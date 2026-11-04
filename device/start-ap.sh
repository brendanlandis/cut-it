#!/bin/bash
killall wpa_supplicant
killall dhcpcd

# $HOME not set when called from systemd service, so need to use /root
FW_DIR=${FW_DIR:="/root/fw_dir"}

USER_DIR=$(cat /tmp/user_dir)

AP_FILE="${USER_DIR}/ap.txt"

if [ -f "$AP_FILE" ]; then
    echo "$AP_FILE exists"
    NET=$(head -n 1 $AP_FILE)
    PW=$(tail -n 1 $AP_FILE)
else 
    echo "$AP_FILE does not exist, using default"
    NET=Organelle
    PW=coolmusic
fi

# Cut It: the AP takes the address the house router reserves for this Organelle, so the phone's
# The phone has one address everywhere (cut-it device/README.md). Factory: no -g, 192.168.12.1.
$FW_DIR/scripts/create_ap --no-virt -g 192.168.1.15 -n wlan0 $NET $PW

