#!/bin/sh
# Reload the whole patch, which is the second tier of panic.
#
#   sh recover.sh
#
# THE ONE .sh HERE THAT IS NOT RUN AT LOAD. wire.sh, state-dir.sh, logroll.sh
# and phone-ip.sh all fork once per patch load, inside Phase 4's rule of one
# fork per load and never per event. This one forks on an EVENT -- CC 90 held
# for two seconds -- and that bends the rule deliberately, on the same terms
# u_present's trailing fork does: it is rare, it is user-initiated, it is
# bounded at exactly one per gesture, and it ENDS THE PATCH. Nothing can
# cascade behind a command whose effect is to kill the process that ran it.
#
# WHY THIS IS THE ONLY RECOVERY FOR SOME OF THE RIG. Every device that can
# answer for itself is polled, declared lost and re-wired by u_present. The
# Volca answers nothing at all -- it has no MIDI out -- so it can never be
# declared lost, and it only comes back if a DETECTABLE device happened to go
# down beside it. On 2026-08-10 that failed exactly as designed: pulling the
# Volca's interface also knocked the SP-404 off the shared USB bus, the 404
# answered first, the counter reset, and the Volca sat unreachable until
# wire.sh was run by hand. Item 275. A reload re-enumerates everything.
#
# ⛔ IT IS TWO COMMANDS AND ORDER MATTERS, or it silently does nothing.
#
#   /reloadNoRemount refreshes mother's patch list AND resets its current patch
#   directory to the default -- /usbdrive/Patches if it exists, else
#   /sdcard/Patches. /loadPatch then takes a name RELATIVE to that directory
#   (MainMenu::runPatch builds getPatchDir() + "/" + arg), and Cut It lives in
#   a category folder underneath it. So the name has to carry the folder:
#   "!/Cut It", not "Cut It". A BARE NAME LOADS NOTHING AND SAYS NOTHING.
#
#   This is the same two-step tools/deploy.sh uses, and the quoting is copied
#   from it verbatim rather than rebuilt -- the single quotes are what keep the
#   space in "Cut It" from splitting the OSC argument.
#
# ⛔ NOT /reload. That one runs mount.sh, and with a Launchpad attached mount.sh
# mounts its write-protected onboarding drive and takes USER_DIR down with it.
# Nothing here needs a remount.
#
# The patch is silenced BEFORE this runs -- u_init raises panic and waits 300 ms
# -- because killing Pd mid-note never sends the note-off, and a panic that
# leaves the SP-404 holding a note is a panic that CREATED a stuck note.
#
# quitting still fires on this path. /loadPatch calls MainMenu::runPatch, which
# runs killpatch.sh FIRST, and that script's first line is /quitpd -- so the
# outgoing patch gets mother's usual ~100 ms to hand hardware back, and
# m_launchpad's safe exit still returns the Launchpad to Live Mode. Item 252.
#
# ⚠️ NOTHING HERE CAN REPORT A FAILURE. oscsend is fire-and-forget UDP and the
# patch that would read a reply is about to be killed. That is why u_init
# writes a breadcrumb to the state directory before calling this: if the load
# never lands there is no patch at all, and the NEXT boot is the only place the
# attempt can still be seen. See ref/module/map.md.
set -eu

oscsend localhost 4001 /reloadNoRemount i 1

# Give mother a moment to finish resetting its patch directory. deploy.sh gets
# this for free by running the two over separate ssh connections; here they are
# one script, so the gap has to be explicit.
sleep 0.3

oscsend localhost 4001 /loadPatch s '!/Cut It'
