#!/bin/sh
# Deploy the Cut It patch to the Organelle, and load it.
#
#   ./deploy.sh                      check, push, reload, load
#   ./deploy.sh --clean              wipe the remote copy first
#   NOCHECK=1 ./deploy.sh            skip the local Pd syntax check
#   NORELOAD=1 ./deploy.sh           skip refreshing the patch list
#   NOLOAD=1 ./deploy.sh             push but leave the running patch alone
#   DEST=/usbdrive/Patches ./deploy.sh   push to a USB drive instead
#   HOST=root@192.168.1.15 ./deploy.sh   target by IP if mDNS is flaky
#   PD=/path/to/pd ./deploy.sh           use a different Pd for the check
#
# There is no rsync on the Organelle (Pd 0.49 / OS 4.0 build), so this uses scp.
# Note that means files DELETED locally are not removed on the device — see
# `./deploy.sh --clean` to wipe the remote copy first.

set -eu

HOST="${HOST:-root@organelle.local}"
DEST="${DEST:-/sdcard/Patches/!}"
PD="${PD:-/Applications/Pd-0.49-1.app/Contents/Resources/bin/pd}"
PATCH="Cut It"

cd "$(dirname "$0")"

if [ ! -d "$PATCH" ]; then
    echo "error: no '$PATCH' directory in $(pwd)" >&2
    exit 1
fi

# --- Syntax check ----------------------------------------------------------
# The Organelle runs Pd with -nogui and there is no console, so a load-time
# error there is completely silent. Catch it here instead: Pd 0.49-1 on the Mac
# is the same version the device runs.
#
# Pd exits 0 even when objects fail to create, so the gate is OUTPUT, not exit
# status. Silence means every object instantiated.
#
# -path mac-stubs supplies do-nothing stand-ins for externals that exist only
# on the Organelle (currently [shell]). That folder is NOT deployed, so on the
# device the real externals win — see mac-stubs/shell.pd.
check_patch() {
    out=$("$PD" -nogui -noaudio -path mac-stubs -send "pd quit" "$1" 2>&1) || true
    if [ -n "$out" ]; then
        echo "syntax check FAILED: $1" >&2
        echo "$out" >&2
        return 1
    fi
    echo "  ok: $1"
}

if [ "${NOCHECK:-}" = "1" ]; then
    echo "skipped syntax check (NOCHECK=1)"
elif [ ! -x "$PD" ]; then
    echo "warning: no Pd at $PD — skipping syntax check" >&2
    echo "         set PD=... to point at a Pd 0.49 binary" >&2
else
    echo "syntax checking ..."
    check_patch "$PATCH/main.pd"
    check_patch "$PATCH/main-dev.pd"
fi

# --- Copy ------------------------------------------------------------------
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
# Refresh the Organelle's patch list, and reset mother's current patch
# directory to the default — which the load step below depends on.
#
# /reloadNoRemount, NOT reload.sh. reload.sh sends /reload, which additionally
# runs mount.sh, and mount.sh mounts the LAST /dev/sd* on /usbdrive. With a
# Launchpad attached that is its 192 KiB write-protected onboarding drive, and
# mounting it moves USER_DIR onto a read-only volume — which breaks wifi
# config, Save, Save New and AP mode until it is unmounted. See
# plan-hardware.md. Nothing here needs a remount: the files went to /sdcard.
if [ "${NORELOAD:-}" = "1" ]; then
    echo
    echo "skipped reload (NORELOAD=1) — press Storage -> Reload on the device"
else
    echo
    echo "reloading patch list ..."
    ssh "$HOST" "oscsend localhost 4001 /reloadNoRemount i 1" || {
        echo "reload failed — press Storage -> Reload on the device instead" >&2
    }
fi

# --- Loading ---------------------------------------------------------------
# mother's /loadPatch takes a name relative to its CURRENT patch directory
# (MainMenu::runPatch builds getPatchDir() + "/" + arg). /reload above resets
# that to the default — /usbdrive/Patches if it exists, else /sdcard/Patches.
# Our DEST is a category folder underneath, so the name has to carry that
# folder: "!/Cut It", not "Cut It". A bare name silently loads nothing.
#
# The derivation assumes no USB drive with a Patches/ folder is mounted; one
# would move the default out from under it.
#
# NOTE: this kills whatever patch is currently running on the device.
#
# KNOWN SIDE EFFECT, matters in Phase 8 only: mother records the name it was
# given in /tmp/curpatchname, so loading this way leaves "!/Cut It" there where
# a menu selection would leave "Cut It". save-new-patch.sh reads that with
# `ls /tmp/curpatchname` and would see "!" — so System -> Save New after a
# deploy.sh load makes a folder called "! 2" instead of copying the patch.
# Plain Save is unaffected (it works off the /tmp/patch symlink, which is
# correct). Select the patch from the menu once before using Save New.
LOADNAME="$PATCH"
case "$DEST" in
    */Patches/*) LOADNAME="${DEST##*/Patches/}/$PATCH" ;;
esac

if [ "${NOLOAD:-}" = "1" ]; then
    echo
    echo "skipped load (NOLOAD=1) — select '$PATCH' on the device"
else
    echo
    echo "loading '$LOADNAME' ..."
    ssh "$HOST" "oscsend localhost 4001 /loadPatch s '$LOADNAME'"
fi

echo
echo "Done."
