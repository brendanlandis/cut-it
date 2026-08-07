#!/bin/sh
# Make u_state's data directory, and make sure both of its files EXIST.
#
#   sh state-dir.sh /sdcard/cut-it-state
#
# Run once at load by u_state, through [shell] -- the same one-fork-per-load
# pattern as wire.sh and logroll.sh, and inside Phase 4's rule of one fork per
# load and never per event.
#
# WHY IT TOUCHES THE FILES AND DOES NOT JUST MAKE THE DIRECTORY. Two measured
# facts, items 143 and 147:
#
#   - a [text write] into a directory that does not exist PRINTS `write failed`.
#     It does NOT fail silently, whatever the Phase 8 plan assumed.
#   - a [text read] of a file that does not exist prints THREE lines.
#
# u_state reads both files at every boot, so without the touch a fresh install
# would print six error lines on the console before it had done anything wrong.
# That is the same class of noise as mother's own `knobs.txt: can't open`, and
# it is worth not adding to.
#
# ⚠️ touch NEVER TRUNCATES, which is the whole reason it is safe to run at every
# load. Creating the files with `>` instead would silently destroy the saved
# state of every previous session, and it would do it before anything had a
# chance to read them.
#
# On the Mac [shell] is stubbed by mac-stubs/shell.pd, so none of this runs
# there -- which is why main-dev.pd passes a directory that already exists.
set -eu

DIR=${1:?usage: state-dir.sh <data-directory>}

mkdir -p "$DIR"
touch "$DIR/cut-it-auto.txt" "$DIR/cut-it-manual.txt"
