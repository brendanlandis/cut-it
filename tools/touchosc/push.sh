#!/bin/sh
# Build the phone's TouchOSC layout and put it on the phone, through TouchOSC on the Mac.
#
#   ./tools/touchosc/push.sh
#
# TouchOSC's editor network sync is the route (its manual, Editor Network): the Mac's TouchOSC
# runs as an editor server and pushes its document, and every change to it, to each connected
# client, live. So the phone's TouchOSC is connected ONCE as an editor client of the Mac, and
# from then on this script is the whole deploy: it rebuilds CutIt.tosc and opens it in the
# Mac's TouchOSC, which sends it on.
#
# The server is off after every launch unless TouchOSC is started with
# --editor.network.state=SERVER, so when TouchOSC runs without it, this quits and relaunches it
# with it. Everything opens with `open -g`: no window comes to the front.
#
# Then it checks the phone is connected: it drops off now and then, and keeps the old layout
# without saying so (Reference, touchosc). Exit 3 says it is not, so a caller (watch.py) can tell.

set -eu

HERE=$(cd "$(dirname "$0")" && pwd)
APP=/Applications/TouchOSC.app
BIN="$APP/Contents/MacOS/TouchOSC"
TOSC="$HERE/CutIt.tosc"

python3 "$HERE/build.py"

pid() { pgrep -f "$BIN" || true; }
listening() { lsof -nP -a -p "$1" -iTCP -sTCP:LISTEN 2>/dev/null | awk 'NR > 1 { print $9 }'; }
phones() { lsof -nP -a -p "$1" -iTCP:6666 -sTCP:ESTABLISHED 2>/dev/null | awk 'NR > 1 { print $9 }'; }

p=$(pid)
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
    open -g -a "$APP" "$TOSC" --args --editor.network.state=SERVER
else
    open -g -a "$APP" "$TOSC"
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

# A phone that was connected stays connected through a new document; one that dropped off has to
# be connected again by hand. A phone reconnecting right after a restart gets a few seconds.
i=0
while [ -z "$(phones "$p")" ]; do
    i=$((i + 1))
    if [ "$i" -gt 25 ]; then
        echo "The phone is not connected, so it still has the old layout: in TouchOSC on the phone," >&2
        echo "connect to this Mac's editor again, and it takes the new one at once." >&2
        exit 3
    fi
    sleep 0.2
done
echo "The phone is connected ($(phones "$p" | head -1 | sed 's/.*->//')) and has it"
