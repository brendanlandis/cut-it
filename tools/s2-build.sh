#!/bin/bash
# Copies device/s2/build.sh, device/pd-libs and the five source tarballs to the Organelle S2 and
# starts the build there in the background. Follow it with:
#   ssh music@<s2> tail -f /sdcard/build-s2/build.log
#
#   tools/s2-build.sh <dir holding the tarballs> [music@<s2's address>]
#
# The tarballs, and where each comes from: device/README.md, "Lua and ELSE", plus
# pd-0.57-0.src.tar.gz from msp.ucsd.edu/Software. build.sh checks all five.
set -eu
SRC=${1:?usage: s2-build.sh <tarball dir> [host]}
HOST=${2:-${S2_HOST:-music@192.168.1.11}}
HERE=$(cd "$(dirname "$0")/.." && pwd)

ssh "$HOST" mkdir -p /sdcard/build-s2
scp -q "$HERE/device/s2/build.sh" "$HERE"/device/pd-libs/* \
    "$SRC"/pd-0.57-0.src.tar.gz "$SRC"/pd-else-rc14.tar.gz "$SRC"/lua-5.4.7.tar.gz \
    "$SRC"/lua-v5.4.7-git.tar.gz "$SRC"/pd-lua-0.12.24.tar.gz "$HOST:/sdcard/build-s2/"
ssh "$HOST" 'nohup bash /sdcard/build-s2/build.sh > /sdcard/build-s2/build.log 2>&1 < /dev/null & echo started $!'
