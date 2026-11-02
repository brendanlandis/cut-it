#!/bin/sh
# Reload the whole patch, the second tier of panic. Run by u_init when recover
# is raised (ref/module/map.md).
#
#   sh recover.sh
#
# The one script here that forks on an event rather than at load, within the
# rule's terms: rare, one per gesture, and it ends the patch. It is the only
# recovery for a device nothing can detect, like the Volca (item 275).
#
# Two commands, and the order matters: /reloadNoRemount resets mother's patch
# directory, and /loadPatch takes a name relative to it, so the name carries the
# category folder. A bare name loads nothing and says nothing. Never mother's
# plain reload command, which runs mount.sh (Reference,
# critter-guitari-organelle-1). The quoting is tools/deploy.sh's: the single
# quotes keep "Cut It" one OSC argument.
#
# u_init silences the rig and waits 300 ms first, and quitting still fires on
# this path (item 252), so m_launchpad's safe exit still runs. Nothing here can
# report a failure, which is why u_init writes a breadcrumb first.
set -eu

oscsend localhost 4001 /reloadNoRemount i 1

# Give mother a moment to finish resetting its patch directory.
sleep 0.3

oscsend localhost 4001 /loadPatch s '!/Cut It'
