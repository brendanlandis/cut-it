#!/bin/sh
# Push both patches to the Organelle, and load one of them.
#
#   ./tools/deploy.sh                    check, push BOTH, reload, load the instrument
#   ./tools/deploy.sh --debug            same, but load the debug patch
#   ./tools/deploy.sh --clean            wipe the remote copy of the loaded one first
#   HOST=root@192.168.1.15 ./tools/deploy.sh   target by IP if mDNS is flaky
#
# ⚠️ --debug LOADS the debug patch, which STOPS THE INSTRUMENT. Run it bare
# afterwards to put Cut It back.
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

# ⛔ BOTH FOLDERS ARE PUSHED EVERY TIME; ONLY ONE IS LOADED. Copying files is
# cheap and loading is the disruptive half -- it restarts Pd and stops whatever
# is playing -- so there is no reason for the folder you did not name to go
# stale on the device. It went stale exactly that way once already, though with
# a probe rather than a patch: `Inquiry Probe` sat in `! debug` for four days
# carrying a comment citing a plan that had been deleted, and nothing said so
# because nothing ever pushed it again.
#
# $PATCH is the one that gets LOADED; $ALL_PATCHES is what gets COPIED.
# ⚠️ NEWLINE-SEPARATED, not space-separated, because both names contain a space.
ALL_PATCHES="Cut It
Cut It Debug"

# ⚠️ THE MENU DIRECTORY IS A PROPERTY OF THE FOLDER, not of the flag -- --debug
# picks which one to LOAD. This is how the push loop places each one correctly
# in a single pass.
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
# ⚠️ DEST STILL OVERRIDES, and it applies to the patch being LOADED. The push
# loop below asks dest_for for every other folder, so an override cannot send
# one patch somewhere unusual and then load it from where it is not.
DEST="${DEST:-$(dest_for "$PATCH")}"

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
    # ⛔ EVERY PATCH THAT IS ABOUT TO BE PUSHED, not just the one being loaded.
    # The check is the only thing standing between a broken patch and a device
    # with no console, and pushing an unchecked folder would put one there --
    # ready to fail silently the next time it is selected from the menu.
    # ⚠️ IFS IS SET TO A NEWLINE RATHER THAN PIPING INTO `while read`. A pipeline
    # puts the loop in a SUBSHELL, so a failure inside it exits the subshell and
    # the script carries on deploying a patch that did not pass -- and with
    # `set -e` on, a plain for-loop aborts the run the moment one does.
    _oifs=$IFS; IFS='
'
    for p in $ALL_PATCHES; do
        check_patch "$p/main.pd"
    done
    IFS=$_oifs
    # ⚠️ ONLY THE INSTRUMENT HAS A main-dev.pd. The debug patch has no Mac entry
    # point at all: u_mother-stub fakes a front panel for Cut It, and this one IS
    # a front panel -- six screens steered from the keyboard, which is the thing
    # a stub would have to fake. It is exercised headlessly by
    # test/gate/debug-assert.sh instead.
    check_patch "Cut It/main-dev.pd"
fi

# --- Copy ------------------------------------------------------------------
# ⛔ EVERY PATCH GOES, EVERY TIME. Only $PATCH is loaded afterwards.
# ⚠️ --clean WIPES ONLY THE ONE YOU NAMED. It exists to clear files deleted
# locally, which scp cannot do, and that is a question about one folder; wiping
# the other one as a side effect of a flag you passed for this one would be a
# surprise with no upside.
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
