#!/bin/sh
# Put a checklist's Send line onto the instrument's buses, through u_inject.
#
#   ./tools/send.sh 'disp chop-size 43 %; disp grain 12'   the instrument on the Organelle
#   HOST=mac ./tools/send.sh '...'                         main-dev.pd open on this Mac
#   HOST=root@192.168.1.15 ./tools/send.sh '...'           target by IP if mDNS is flaky
#
# u_inject listens on 127.0.0.1 only, so on the Organelle the line goes over SSH
# to the device's own pdsend. Each message is sent as a datagram of its own: Pd's
# netreceive delivers only the first message in one (Reference, pure-data).
# pdsend's own "connected to" line is dropped; its errors still show.
# What it reaches, and what it refuses: test/checklists/README.md, Send lines.

set -eu

HOST="${HOST:-root@organelle.local}"
PDSEND="${PDSEND:-$HOME/Applications/Pd-0.57-0.app/Contents/Resources/bin/pdsend}"

if [ $# -ne 1 ] || [ -z "$1" ]; then
    echo "usage: ./tools/send.sh '<bus> <message>; <bus> <message>'" >&2
    exit 2
fi

# One message a line, each ending in the ; that pdsend's datagram needs.
lines=$(printf '%s\n' "$1" | tr ';' '\n' | sed 's/^[[:space:]]*//; s/[[:space:]]*$//' \
    | grep -v '^$' | sed 's/$/;/')

# u_inject listens 2000 above u_net's inbound port: 11001 on the device, 11002 from
# main-dev.pd. PORT= overrides it.
if [ "$HOST" = mac ]; then
    printf '%s\n' "$lines" | "$PDSEND" "${PORT:-11002}" 127.0.0.1 udp 2>&1 >/dev/null \
        | sed '/^connected to /d' >&2
else
    printf '%s\n' "$lines" | ssh "$HOST" "/sdcard/pd-0.57-0/bin/pdsend ${PORT:-11001} 127.0.0.1 udp 2>&1 >/dev/null \
        | sed '/^connected to /d' >&2"
fi
