#!/bin/sh
# Deploy the Cut It patch to the Organelle.
#
#   ./deploy.sh                      push to the internal microSD
#   DEST=/usbdrive/Patches ./deploy.sh   push to a USB drive instead
#   HOST=root@192.168.1.15 ./deploy.sh   target by IP if mDNS is flaky
#
# There is no rsync on the Organelle (Pd 0.49 / OS 4.0 build), so this uses scp.
# Note that means files DELETED locally are not removed on the device — see
# `./deploy.sh --clean` to wipe the remote copy first.

set -eu

HOST="${HOST:-root@organelle.local}"
DEST="${DEST:-/sdcard/Patches/!}"
PATCH="Cut It"

cd "$(dirname "$0")"

if [ ! -d "$PATCH" ]; then
    echo "error: no '$PATCH' directory in $(pwd)" >&2
    exit 1
fi

if [ "${1:-}" = "--clean" ]; then
    echo "removing remote $DEST/$PATCH ..."
    ssh "$HOST" "rm -rf '$DEST/$PATCH'"
fi

echo "deploying '$PATCH' -> $HOST:$DEST/"
ssh "$HOST" "mkdir -p '$DEST'"
scp -rq "$PATCH" "$HOST:$DEST/"

echo "deployed:"
ssh "$HOST" "ls -la '$DEST/$PATCH'"

# --- Reloading -------------------------------------------------------------
# Refresh the Organelle's patch list. Equivalent to Storage -> Reload on the
# device, and to the refresh button in the web Patch Manager.
if [ "${NORELOAD:-}" = "1" ]; then
    echo
    echo "skipped reload (NORELOAD=1) — press Storage -> Reload on the device"
else
    echo
    echo "reloading patch list ..."
    ssh "$HOST" "/root/fw_dir/scripts/reload.sh" || {
        echo "reload failed — press Storage -> Reload on the device instead" >&2
    }
fi

echo
echo "Done. Select 'Cut It' on the Organelle."
