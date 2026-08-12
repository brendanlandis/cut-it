#!/bin/sh
# Deploy a patch to the Organelle, and load it.
#
#   ./tools/deploy.sh                    check, push, reload, load
#   ./tools/deploy.sh --debug            the debug patch instead of the instrument
#   ./tools/deploy.sh --clean            wipe the remote copy first
#   HOST=root@192.168.1.15 ./tools/deploy.sh   target by IP if mDNS is flaky
#
# Every flag, and the reasoning behind the loop, is on ref/workflow.md.
#
# There is no rsync on the Organelle (Pd 0.49 / OS 4.0 build), so this uses scp.
# Note that means files DELETED locally are not removed on the device — see
# `--clean` to wipe the remote copy first.

set -eu

HOST="${HOST:-root@organelle.local}"
PD="${PD:-/Applications/Pd-0.49-1.app/Contents/Resources/bin/pd}"

# --- Which deployable ------------------------------------------------------
# ⛔ TWO PATCH FOLDERS AND TWO MENU DIRECTORIES, and the second one is not a
# variant of the first. `! debug` exists so that at a venue you scroll past
# nothing to reach the instrument -- anything you might reach for INSTEAD of
# playing lives there. ⚠️ --debug DOES NOT DEPLOY Cut It, and deploying either
# one loads it, which stops whatever is running.
#
# ⚠️ THE FLAGS ARE PARSED BEFORE ANYTHING ELSE so --clean and --debug compose in
# either order. --clean used to be read as literally $1 and would have been
# silently ignored after --debug.
CLEAN=0
DEBUG=0
for a in "$@"; do
    case "$a" in
        --clean) CLEAN=1 ;;
        --debug) DEBUG=1 ;;
        -h|--help)
            echo "usage: tools/deploy.sh [--debug] [--clean]"
            echo "  (no flags)  the instrument -> /sdcard/Patches/!"
            echo "  --debug     the debug patch -> /sdcard/Patches/! debug"
            echo "  --clean     wipe the remote copy of whichever one first"
            exit 0 ;;
        *) echo "unknown flag: $a  (try --help)" >&2; exit 1 ;;
    esac
done

if [ "$DEBUG" = "1" ]; then
    PATCH="Cut It Debug"
    DEST="${DEST:-/sdcard/Patches/! debug}"
else
    PATCH="Cut It"
    DEST="${DEST:-/sdcard/Patches/!}"
fi

# The repo root, not tools/ — $PATCH, mac-stubs and the scp source are all
# relative to it.
cd "$(dirname "$0")/.."

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
#
# -nomidi because this gate reads OUTPUT, and Pd prints a device error at
# startup whenever its saved MIDI preferences name hardware that is not plugged
# in — "could not open midi input 0 (...): PortMidi: `Invalid device ID'". That
# is the Mac's MIDI config, not the patch, and it blocked a deploy the moment
# the controllers were moved to the Organelle. Object creation does not depend
# on a device being open, so [midiout] and friends still instantiate and the
# gate loses nothing.
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
    check_patch "$PATCH/main.pd"
    # ⚠️ ONLY THE INSTRUMENT HAS A main-dev.pd. The debug patch has no Mac entry
    # point at all: u_mother-stub fakes a front panel for Cut It, and this one IS
    # a front panel -- six screens steered from the keyboard, which is the thing
    # a stub would have to fake. It is exercised headlessly by
    # test/gate/debug-assert.sh instead.
    [ "$DEBUG" = "1" ] || check_patch "$PATCH/main-dev.pd"
fi

# --- Copy ------------------------------------------------------------------
if [ "$CLEAN" = "1" ]; then
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
# /reloadNoRemount, NOT reload.sh. reload.sh sends /reload, which also runs
# mount.sh -- and with a Launchpad attached that mounts its write-protected
# onboarding drive and takes USER_DIR down with it. The chain is on
# ref/workflow.md. Nothing here needs a remount: the files went to /sdcard.
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
# deploy makes a folder called "! 2" instead of copying the patch.
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
    ssh "$HOST" "oscsend localhost 4001 /loadPatch s '$LOADNAME'" || {
        echo "load failed — select '$PATCH' on the device instead" >&2
        exit 1
    }

    # ⛔ VERIFY THE RUN, NOT THE FILE. The scp can land a current patch while the
    # RUNNING one stays stale, and until this check existed nothing anywhere said
    # so: the deployed file greps as current, the instrument behaves like the old
    # build, and the two cannot be told apart from the Mac. It cost a whole
    # debugging session -- item 243. It happens whenever the load does not take,
    # and a wifi drop between the scp and the load is all it needs. oscsend is
    # fire-and-forget UDP, so a clean exit from it proves nothing at all.
    #
    # A successful load RESTARTS Pd, so the test is whether pd is younger than
    # the files we just pushed. /proc/<pid> carries the process start time as its
    # mtime, which makes this one `test -nt` and no dependency on ps flags that
    # differ between busybox and procps.
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
