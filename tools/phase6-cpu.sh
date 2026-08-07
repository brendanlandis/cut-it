#!/bin/sh
# item 94 -- the Phase 6 repaint budget, measured on the device.
#
#     ./tools/phase6-cpu.sh              # one reading
#     ./tools/phase6-cpu.sh -n 3         # three, so you can see it settle
#     HOST=root@192.168.1.15 ./tools/phase6-cpu.sh
#
# Wraps the /proc arithmetic from ref-hardware.md -> Measuring the running patch,
# which reads /proc rather than using top because the device has busybox. Takes
# the reading over five seconds WITHOUT disturbing the running patch.
#
# THE BUDGET IS 11.2 %: Phase 5's measured idle baseline of 10.2 % plus one
# point. g_grid should come nowhere near it, because it repaints only when
# something changed -- nothing at all when idle, about two SysEx a second at
# 120 BPM. If this is over budget, the dirty flag is not gating.
#
# Take three readings, per item 94: idle and stopped, transport running with the
# beat row walking, and during the bench's alert step.
set -e

HOST=${HOST:-root@organelle.local}
N=1
[ "$1" = "-n" ] && N=$2

BUDGET=11.2

echo "measuring $HOST -- five seconds a reading, $N reading(s)"
echo "budget: ${BUDGET} % (Phase 5 idle baseline 10.2 % plus one point)"
echo

i=1
while [ "$i" -le "$N" ]; do
    # -nx, never a bare pgrep: the substring match hits a KERNEL THREAD on this
    # device, which is the bug that had fetch-errors.sh reporting pd alive while
    # it was killed (item 36).
    out=$(ssh "$HOST" '
        P=$(pgrep -nx pd) || { echo "NOPD"; exit 0; }
        col() { awk "/^Udp:/{ if(h==\"\"){h=1; for(i=1;i<=NF;i++) if(\$i==\"OutDatagrams\") c=i; next} print \$c }" /proc/net/snmp; }
        T1=$(awk "{print \$14+\$15}" /proc/$P/stat)
        C1=$(awk "/^cpu /{print \$2+\$3+\$4+\$5+\$6+\$7+\$8}" /proc/stat)
        U1=$(col)
        sleep 5
        T2=$(awk "{print \$14+\$15}" /proc/$P/stat)
        C2=$(awk "/^cpu /{print \$2+\$3+\$4+\$5+\$6+\$7+\$8}" /proc/stat)
        U2=$(col)
        awk -v a=$T1 -v b=$T2 -v c=$C1 -v d=$C2 "BEGIN{printf \"%.1f\n\", 100*(b-a)/(d-c)}"
        echo $(( (U2-U1)/5 ))
        cut -d" " -f1-3 /proc/loadavg
        aconnect -l | grep -c "Connecting To"
    ')

    if [ "$out" = "NOPD" ]; then
        echo "reading $i: pd is not running on $HOST"
        i=$((i + 1))
        continue
    fi

    cpu=$(echo "$out"  | sed -n 1p)
    udp=$(echo "$out"  | sed -n 2p)
    load=$(echo "$out" | sed -n 3p)
    alsa=$(echo "$out" | sed -n 4p)

    verdict=$(awk -v c="$cpu" -v b="$BUDGET" \
        'BEGIN{print (c+0 <= b+0) ? "WITHIN BUDGET" : "OVER BUDGET"}')

    echo "reading $i"
    echo "   pd CPU        ${cpu} %       ${verdict} (<= ${BUDGET} %)"
    echo "   UDP out       ${udp}/s        the display -- flat at ~117 since Phase 3"
    echo "   load          ${load}"
    echo "   ALSA links    ${alsa}         expect 5 with three controllers wired both ways"
    echo
    i=$((i + 1))
done

cat <<'EOF'
Record these in item 94, and add the row ref-hardware.md ->
Measuring the running patch is holding open for Phase 6.

The SysEx rate is not visible here -- UDP out is the OLED. To see the grid's
own traffic, run the by-hand console (ref-conventions.md -> There IS a console)
and count F0 bytes: 0/s idle and stopped, ~2/s at 120 BPM, ~6/s worst case.
EOF
