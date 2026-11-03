#!/bin/sh
# On the Organelle: loads patches in a second Pd 0.57 beside the live instrument, with the libs'
# folder on its path as mother's launch line has it, and prints Pd's output.
#
#   sh loadcheck.sh "/sdcard/Patches/!/Cut It/main.pd"
#   LIBS= sh loadcheck.sh ...        the same without /sdcard/PdExtraLibs, to compare
#
# A clean load of Cut It prints two lines, from [shell]'s load-time scripts not being in the
# empty working directory: `sh: logroll.sh: No such file or directory`, and codec-gain.sh's.
# mother.pd adds `udpsend: connecting to port 4001`. Anything else is the patch's.
#
# Isolated from the live Pd, which it never stops or signals:
#   - -nrt: as root Pd defaults to SCHED_FIFO at the live Pd's own priority;
#   - its own network namespace (lo only), so mother.pd's udpreceive can't share port 4000;
#   - an empty working directory, so [shell]'s load-time scripts find nothing to run;
#   - -noaudio -nomidi, niced, and `pd quit` before the scheduler's first tick;
#   - 128 MiB of address space and first in line for the OOM killer: a test Pd once ran this
#     495 MB device out of memory (Reference, the Organelle's page).
PD=${PD:-/sdcard/pd-0.57-0/bin/pd}
LIBS=${LIBS-/sdcard/PdExtraLibs}
RUN=$(mktemp -d /tmp/loadcheck.XXXXXX) || exit 1
cd "$RUN" || exit 1
unshare -n sh -c 'echo 1000 > /proc/self/oom_score_adj; ulimit -v 131072; ip link set lo up && exec "$@"' sh \
    nice -n 19 timeout 120 "$PD" -nrt -nogui -noaudio -nomidi ${LIBS:+-path "$LIBS"} \
    -send "pd quit" "$@" 2>&1
rc=$?
sleep 2         # [shell]'s children outlive Pd: their lines, then the directory goes
left=$(ls -A "$RUN" | wc -l)
cd / && rm -rf "$RUN"
echo "### exit $rc, $left file(s) left in the working directory"
