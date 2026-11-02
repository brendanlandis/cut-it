#!/bin/sh
# Push both patches to the Organelle, and load one of them.
#
#   ./tools/deploy.sh                    check, push BOTH, reload, load the instrument
#   ./tools/deploy.sh --debug            same, but load the debug patch
#   ./tools/deploy.sh --clean            wipe the remote copy of the loaded one first
#   HOST=root@192.168.1.15 ./tools/deploy.sh   target by IP if mDNS is flaky
#
# --debug loads the debug patch, which stops the instrument; run it bare
# afterwards to put Cut It back. The flags and the loop are on ref/workflow.md.
#
# scp, since the device has no rsync, so a file deleted locally stays on the
# device until --clean.

set -eu

HOST="${HOST:-root@organelle.local}"
PD="${PD:-/Applications/Pd-0.49-1.app/Contents/Resources/bin/pd}"

# --- Which deployable ------------------------------------------------------
CLEAN=0
DEBUG=0
for a in "$@"; do
    case "$a" in
        --clean) CLEAN=1 ;;
        --debug) DEBUG=1 ;;
        -h|--help)
            echo "usage: tools/deploy.sh [--debug] [--clean]"
            echo
            echo "Both patch folders are pushed every time. The flag says which"
            echo "one gets LOADED, and loading restarts Pd."
            echo "  (no flags)  load Cut It        <- /sdcard/Patches/!"
            echo "  --debug     load Cut It Debug  <- /sdcard/Patches/! debug"
            echo "  --clean     wipe the remote copy of the loaded one first"
            exit 0 ;;
        *) echo "unknown flag: $a  (try --help)" >&2; exit 1 ;;
    esac
done

# Both folders are pushed every time, so the one not loaded cannot go stale on
# the device; only $PATCH is loaded. Newline-separated: both names contain a
# space.
ALL_PATCHES="Cut It
Cut It Debug"

# The menu directory belongs to the folder, not the flag.
dest_for() {
    case "$1" in
        "Cut It Debug") echo "/sdcard/Patches/! debug" ;;
        *)              echo "/sdcard/Patches/!" ;;
    esac
}

if [ "$DEBUG" = "1" ]; then
    PATCH="Cut It Debug"
else
    PATCH="Cut It"
fi
# DEST overrides only the loaded patch's directory, so the load always looks
# where its patch went.
DEST="${DEST:-$(dest_for "$PATCH")}"

cd "$(dirname "$0")/.."

if [ ! -d "$PATCH" ]; then
    echo "error: no '$PATCH' directory in $(pwd)" >&2
    exit 1
fi

# --- Syntax check ----------------------------------------------------------
# Pd exits 0 even when objects fail to create, so the check is the output:
# silence means every object instantiated (ref/workflow.md). -nomidi because
# the Mac's saved MIDI preferences print a device error whenever the hardware
# they name is not plugged in; objects create without a device either way.
check_patch() {
    out=$("$PD" -nogui -noaudio -nomidi -path mac-stubs -send "pd quit" "$1" 2>&1) || true
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
    # Every patch about to be pushed, not just the loaded one. IFS, not a pipe
    # into `while read`: a pipeline's loop is a subshell, and its failure would
    # not stop the deploy.
    _oifs=$IFS; IFS='
'
    for p in $ALL_PATCHES; do
        check_patch "$p/main.pd"
    done
    IFS=$_oifs
    # Only the instrument has a main-dev.pd (ref/module/debug.md).
    check_patch "Cut It/main-dev.pd"
fi

# --- Copy ------------------------------------------------------------------
# --clean wipes only the patch being loaded.
_oifs=$IFS; IFS='
'
for p in $ALL_PATCHES; do
    if [ "$p" = "$PATCH" ]; then d=$DEST; else d=$(dest_for "$p"); fi

    if [ "$CLEAN" = "1" ] && [ "$p" = "$PATCH" ]; then
        echo "removing remote $d/$p ..."
        ssh "$HOST" "rm -rf '$d/$p'"
    fi

    if [ "$p" = "$PATCH" ]; then
        echo "deploying '$p' -> $HOST:$d/   (this is the one that gets loaded)"
    else
        echo "deploying '$p' -> $HOST:$d/"
    fi
    ssh "$HOST" "mkdir -p '$d'"
    scp -rq "$p" "$HOST:$d/"
done
IFS=$_oifs

echo "deployed:"
ssh "$HOST" "ls -la '$DEST/$PATCH'"

# --- Reloading -------------------------------------------------------------
# Refreshes the patch list and resets mother's patch directory, which the load
# below depends on. /reloadNoRemount, never reload.sh, which runs mount.sh
# (ref/workflow.md).
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
# /loadPatch resolves against mother's patch directory, so the name carries the
# category folder ("!/Cut It"); a bare name loads nothing. That directory is
# /usbdrive/Patches when a USB drive has one, which would break this. Save New
# after a deploy makes "! 2": select the patch from the menu first (the
# Organelle's Reference page, Loading a patch from the shell).
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
    ssh "$HOST" "oscsend localhost 4001 /loadPatch s '$LOADNAME'" || {
        echo "load failed — select '$PATCH' on the device instead" >&2
        exit 1
    }

    # Verify the run, not the file: oscsend is fire-and-forget UDP, and a load
    # that did not take leaves the old build running behind current files (item
    # 243). A load restarts Pd, so Pd must be younger than main.pd
    # (ref/device-os.md, Deploying).
    echo "verifying the running patch restarted ..."
    sleep 5
    if ssh "$HOST" '
            p=$(pgrep -f "mother.pd" | head -1)
            [ -n "$p" ] || exit 3
            [ "/proc/$p" -nt "'"$DEST/$PATCH"'/main.pd" ] || exit 4
        '; then
        echo "  ok — Pd restarted after the push"
    else
        case $? in
          3) echo "⛔ NO Pd IS RUNNING on the device." >&2 ;;
          *) echo "⛔ THE FILES LANDED BUT THE PATCH DID NOT RELOAD." >&2
             echo "   The device is still running the PREVIOUS build, and nothing" >&2
             echo "   on it will say so. Select '$PATCH' from the front panel." >&2 ;;
        esac
        exit 1
    fi
fi

echo
echo "Done."
