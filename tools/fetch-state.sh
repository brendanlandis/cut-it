#!/bin/sh
# Back the Organelle's saved state up into the repo.
#
#   ./tools/fetch-state.sh              copy the device's state into device-state/
#   ./tools/fetch-state.sh --show       print it instead of copying
#   ./tools/fetch-state.sh --diff       show what would change, copy nothing
#   HOST=root@192.168.1.15 ./tools/...  target by IP if mDNS is flaky
#
# WHY THIS EXISTS. u_state deliberately writes OUTSIDE the patch folder, to
# /sdcard/cut-it-state/, so that deploy.sh, deploy.sh --clean and a power cycle
# cannot touch the instrument's data. The cost of that choice is that the data
# is then in exactly one place, on an SD card, in a device that has already
# lost its network once. This is the other half of the bargain.
#
# TWO FILES, AND THEY ARE NOT THE SAME KIND OF THING:
#
#   cut-it-auto.txt    running values -- the mode, and later the working
#                      pattern. Rewritten on a timer whenever something
#                      changes, so it is always the CURRENT state.
#   cut-it-manual.txt  committed takes -- written ONLY when you press
#                      Storage -> Save. This is the one you would be sad to
#                      lose, and the one worth committing to git.
#
# Contributor-owned files (a future sampler's .wav) live in the same directory
# and are copied too -- u_state records them as manifest lines in the text
# files, so the pair only makes sense together.
#
# Follows deploy.sh and fetch-errors.sh conventions: set -eu, HOST overridable,
# and every failure explained in prose rather than left as a status code.
set -eu

HOST="${HOST:-root@organelle.local}"
REMOTE="${REMOTE:-/sdcard/cut-it-state}"
LOCAL="${LOCAL:-device-state}"

cd "$(dirname "$0")/.."

MODE=copy
case "${1:-}" in
    --show) MODE=show ;;
    --diff) MODE=diff ;;
    "")     ;;
    *)      echo "unknown option '$1' — try --show or --diff" >&2; exit 1 ;;
esac

# --- Is it there at all? ---------------------------------------------------
if ! ssh -o ConnectTimeout=8 "$HOST" true 2>/dev/null; then
    echo "Cannot reach $HOST." >&2
    echo >&2
    echo "⚠️  ssh answering is NOT the reachability test on this device — it keeps" >&2
    echo "    working over IPv6 link-local while IPv4 is entirely gone. See" >&2
    echo "    plan-tests.md items 133 and 146. The check is:" >&2
    echo "        ip addr show wlan0 | grep 'inet '" >&2
    echo >&2
    echo "Nothing is lost by waiting — the state lives on /sdcard and survives a" >&2
    echo "power cycle. Restart the device and run this again." >&2
    exit 1
fi

if ! ssh "$HOST" "[ -d '$REMOTE' ]" 2>/dev/null; then
    echo "No $REMOTE on the device."
    echo
    echo "That is expected until Cut It has been loaded once with u_state in it —"
    echo "the directory is created at load by state-dir.sh. Run ./deploy.sh first."
    exit 1
fi

echo "=== on the device ================================================="
ssh "$HOST" "ls -la '$REMOTE'" | sed 's/^/  /'

if [ "$MODE" = show ]; then
    echo
    echo "=== contents ======================================================"
    ssh "$HOST" "for f in '$REMOTE'/*.txt; do
        [ -f \"\$f\" ] || continue
        echo
        echo \"--- \$f (\$(wc -l < \"\$f\") lines) ---\"
        cat \"\$f\"
    done"
    exit 0
fi

TMP=$(mktemp -d) || { echo "could not make a temp directory" >&2; exit 1; }
trap 'rm -rf "$TMP"' EXIT INT TERM

scp -rq "$HOST:$REMOTE/." "$TMP/" || {
    echo "scp failed — the directory exists but could not be read." >&2
    exit 1
}

if [ "$MODE" = diff ]; then
    echo
    echo "=== what would change in $LOCAL/ =================================="
    if [ ! -d "$LOCAL" ]; then
        echo "  $LOCAL/ does not exist yet — everything above would be new."
        exit 0
    fi
    if diff -ru "$LOCAL" "$TMP" > "$TMP/.diff" 2>&1; then
        echo "  no differences — the backup is current."
    else
        sed 's/^/  /' "$TMP/.diff"
    fi
    exit 0
fi

mkdir -p "$LOCAL"
cp -R "$TMP/." "$LOCAL/"
rm -f "$LOCAL/.diff"

echo
echo "=== copied into $LOCAL/ ==========================================="
ls -la "$LOCAL" | sed 's/^/  /'
echo
echo "⚠️  Nothing is committed — git is yours. Review and commit if you want this"
echo "    snapshot kept:  git add $LOCAL && git status"
