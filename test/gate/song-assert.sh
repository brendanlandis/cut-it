#!/bin/sh
# The song store's headless gate -- ref/module/songs.md. No eyes, no hardware, ~30 s.
#
#   ./test/gate/song-assert.sh          run it, exit non-zero on any failure
#   ./test/gate/song-assert.sh -v       and show the detail behind every check
#   ./test/gate/song-assert.sh --keep   leave the scratch dirs, drivers and captures
#
# The rules first, test/gate/lua/u_song_test.lua, without Pd; then three runs of a scratch copy
# of the instrument: a song played, saved and reverted from the Launchpad's edges, a reload of
# what it left on disk, and a first load from a state directory written before sections. The
# drivers are generated into the scratch directories: edit song-assert-drive-gen.py, never a .pd.
exec python3 "$(dirname "$0")/scratch-gates.py" song "$@"
