#!/bin/sh
# Build the phone's TouchOSC layout and put it on the phone, through TouchOSC on the Mac.
#
#   ./tools/touchosc/push.sh            build it, and push it into the document TouchOSC has open
#   ./tools/touchosc/push.sh --force    and over changes made in TouchOSC's editor, discarding
#                                       them: a saved one (build.py) or an unsaved one (live.py)
#
# TouchOSC's editor network sync is the route (its manual, Editor Network): the Mac's TouchOSC
# runs as an editor server and pushes its document, and every change to it, to each connected
# client, live. So the phone's TouchOSC is connected ONCE as an editor client of the Mac, and
# from then on this script is the whole deploy.
#
# It rebuilds CutIt.tosc, and when TouchOSC is running with its MCP server on and a CutIt
# document open, makes that document the build by editing it in place (live.py), so TouchOSC
# keeps one copy open (Brendan, 2026-11-05). Otherwise (TouchOSC not running, its MCP server off,
# or no CutIt open) it opens the file, as it always did, which adds a document every time.
#
# Both servers are off after every launch unless TouchOSC is started with
# --editor.network.state=SERVER and --mcp.enabled=true, so every launch here passes both, and the
# next push goes live; and when TouchOSC runs without its editor server, this quits and relaunches
# it with them. Everything opens with `open -g`: no window comes to the front.
#
# Then it checks the phone is connected: it drops off now and then, and keeps the old layout
# without saying so (Reference, touchosc). Exit 3 says it is not, so a caller (watch.py) can tell;
# exit 4 that TouchOSC's CutIt has changes made in its editor and not saved, which a push would
# undo (live.py says what they are).

set -eu

HERE=$(cd "$(dirname "$0")" && pwd)
APP=/Applications/TouchOSC.app
BIN="$APP/Contents/MacOS/TouchOSC"
TOSC="$HERE/CutIt.tosc"
PHONE=192.168.1.9           # the phone at home, reserved on the house router (u_root's u_net)
SERVER=6666                 # TouchOSC's editor server
FLAGS="--editor.network.state=SERVER --mcp.enabled=true"

FORCE=
for a in "$@"; do
    case $a in
        --force) FORCE=--force ;;
        *) echo "usage: $0 [--force]" >&2; exit 2 ;;
    esac
done

python3 "$HERE/build.py" $FORCE

pid() { pgrep -f "$BIN" || true; }
listening() { lsof -nP -a -p "$1" -iTCP:$SERVER -sTCP:LISTEN 2>/dev/null | awk 'NR > 1 { print $9 }'; }
phones() { lsof -nP -a -p "$1" -iTCP:$SERVER -sTCP:ESTABLISHED 2>/dev/null | awk 'NR > 1 { print $9 }'; }

p=$(pid)
live=
if [ -n "$p" ] && [ -n "$(listening "$p")" ]; then
    rc=0
    python3 "$HERE/live.py" $FORCE || rc=$?
    case $rc in
        0) live=1 ;;
        2) echo "Opening $(basename "$TOSC") in TouchOSC instead, which adds a document. Its MCP" \
                "server turns on in Preferences > MCP Server, or at its next launch from here." ;;
        *) exit "$rc" ;;
    esac
fi

if [ -z "$live" ]; then
    if [ -n "$p" ] && [ -z "$(listening "$p")" ]; then
        echo "TouchOSC is running without its editor server: restarting it with the server on"
        osascript -e 'quit app "TouchOSC"'
        i=0
        while [ -n "$(pid)" ]; do
            i=$((i + 1))
            if [ "$i" -gt 50 ]; then
                echo "TouchOSC did not quit in 10 s: is it asking to save? Answer it and run this again." >&2
                exit 1
            fi
            sleep 0.2
        done
        p=
    fi
    if [ -z "$p" ]; then
        # shellcheck disable=SC2086
        open -g -a "$APP" "$TOSC" --args $FLAGS
    else
        open -g -a "$APP" "$TOSC"
    fi
fi

# Say where the server is, once it is up.
i=0
while :; do
    p=$(pid)
    at=$([ -n "$p" ] && listening "$p" || true)
    [ -n "$at" ] && break
    i=$((i + 1))
    if [ "$i" -gt 50 ]; then
        echo "TouchOSC has the layout, but its editor server is not listening after 10 s" >&2
        exit 1
    fi
    sleep 0.2
done
echo "TouchOSC on the Mac has $(basename "$TOSC"), its editor server on $at"

# A phone that was connected stays connected through an edit and a new document; one that dropped
# off has to be connected again by hand. A phone reconnecting right after a restart gets a few
# seconds.
i=0
while [ -z "$(phones "$p")" ]; do
    i=$((i + 1))
    if [ "$i" -gt 25 ]; then
        # Which of two causes: the phone off the WiFi altogether, or only TouchOSC's editor
        # link gone (2026-11-04: both happened). Its address is the one the house router
        # reserves for it, as u_root has it; a locked iPhone may not answer either.
        if ! ping -c 1 -t 2 "$PHONE" >/dev/null 2>&1; then
            echo "The phone is not connected, and nothing answers at $PHONE: check that it is on" >&2
            echo "the house WiFi (Settings > Wi-Fi), unlocked, then connect TouchOSC to this Mac." >&2
        else
            echo "The phone is not connected, so it still has the old layout: in TouchOSC on the phone," >&2
            echo "connect to this Mac's editor again, and it takes the new one at once." >&2
        fi
        exit 3
    fi
    sleep 0.2
done
echo "The phone is connected ($(phones "$p" | head -1 | sed 's/.*->//')) and has it"
