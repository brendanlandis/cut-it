#!/bin/sh
# Pull the Organelle's error log to the Mac and make it readable without SSH.
#
#   ./tools/fetch-errors.sh              summary, then detail, newest session first
#   ./tools/fetch-errors.sh --follow     poll the live session every 2s
#   ./tools/fetch-errors.sh --clear      read it, then truncate both files (asks first)
#   HOST=root@192.168.1.15 ./tools/...   target by IP if mDNS is flaky
#
# Both files, because .cur reaches .log only when the patch is next loaded, and
# a power cycle does not reload it (ref/module/error.md).

set -eu

HOST="${HOST:-root@organelle.local}"
DEST="${DEST:-/sdcard/Patches/!}"
PATCH="Cut It"
LOG=/sdcard/cut-it-err.log
CUR=/sdcard/cut-it-err.cur

cd "$(dirname "$0")/.."

FOLLOW=0
CLEAR=0
case "${1:-}" in
    --follow) FOLLOW=1 ;;
    --clear)  CLEAR=1 ;;
    "")       ;;
    *)        echo "unknown option '$1' — try --follow or --clear" >&2; exit 1 ;;
esac

TMP=$(mktemp -d) || { echo "could not make a temp directory" >&2; exit 1; }
trap 'rm -rf "$TMP"' EXIT INT TERM

# --- Is it there at all? ---------------------------------------------------
if ! ssh -o ConnectTimeout=5 -o BatchMode=no "$HOST" true 2>/dev/null; then
    echo "Cannot reach $HOST." >&2
    echo "The Organelle may be off, on a different network, or mDNS may be" >&2
    echo "failing — try HOST=root@192.168.1.15 $0" >&2
    exit 1
fi

# --- Is the patch running, and for how long? -------------------------------
# So a stamp of ms since load can be placed against now.
echo "── the device ────────────────────────────────────────────────"
pdstat=$(ssh "$HOST" '
    # -ox, the oldest: a bare pgrep matches a kernel thread here (item 36), and -n a second pd that lives a moment.
    pid=$(pgrep -ox pd 2>/dev/null || true)
    if [ -z "$pid" ]; then
        echo "pd: NOT RUNNING"
    else
        et=$(ps -o etime= -p "$pid" 2>/dev/null | tr -d " " || true)
        echo "pd: running as pid $pid, up ${et:-unknown}"
    fi
    echo "now: $(date "+%Y-%m-%d %H:%M:%S")"
' 2>/dev/null || echo "pd: could not be queried")
echo "$pdstat"

# --- Does the deployed patch still match the repo? -------------------------
# An error from a build you no longer have is read against the wrong source.
echo
echo "── deployed vs repo ──────────────────────────────────────────"
if ssh "$HOST" "cd '$DEST/$PATCH' 2>/dev/null && md5sum *.pd *.sh 2>/dev/null" \
        > "$TMP/remote.md5" 2>/dev/null && [ -s "$TMP/remote.md5" ]; then
    drift=0
    while read -r rhash rname; do
        [ -n "${rname:-}" ] || continue
        if [ ! -f "$PATCH/$rname" ]; then
            echo "  ONLY ON DEVICE: $rname"; drift=1; continue
        fi
        lhash=$(md5 -q "$PATCH/$rname" 2>/dev/null || md5sum "$PATCH/$rname" | cut -d' ' -f1)
        [ "$rhash" = "$lhash" ] || { echo "  DIFFERS: $rname"; drift=1; }
    done < "$TMP/remote.md5"
    for f in "$PATCH"/*.pd "$PATCH"/*.sh; do
        b=$(basename "$f")
        grep -q " $b\$" "$TMP/remote.md5" || { echo "  NOT DEPLOYED: $b"; drift=1; }
    done
    if [ "$drift" = 1 ]; then
        echo
        echo "  *** The deployed patch is NOT the one in this repo. ***"
        echo "  *** Any error below may come from code you no longer have. ***"
        echo "  *** ./tools/deploy.sh, reproduce, and fetch again. ***"
    else
        echo "  all files identical — the log below came from this source"
    fi
else
    echo "  could not list $DEST/$PATCH — is the patch deployed?"
fi

# --- Follow mode -----------------------------------------------------------
# Not `tail -f`: the patch rewrites .cur on every flush. Fewer lines than last
# time means the 200-line cap dropped some from the front.
if [ "$FOLLOW" = 1 ]; then
    echo
    echo "── following $CUR (flushes every 2s; Ctrl-C to stop) ─────────"
    last=0
    while :; do
        ssh "$HOST" "cat '$CUR' 2>/dev/null" > "$TMP/f.cur" 2>/dev/null || true
        n=$(wc -l < "$TMP/f.cur" | tr -d ' ')
        if [ "${n:-0}" -lt "$last" ]; then
            echo "  … the log rotated (hit its 200-line cap); re-showing from the top"
            last=0
        fi
        if [ "${n:-0}" -gt "$last" ]; then
            sed -n "$((last + 1)),\$p" "$TMP/f.cur"
            last=$n
        fi
        sleep 2
    done
fi

# --- Pull both files -------------------------------------------------------
echo
echo "── the log ───────────────────────────────────────────────────"
: > "$TMP/log"; : > "$TMP/cur"
for pair in "log:$LOG" "cur:$CUR"; do
    name=${pair%%:*}; path=${pair#*:}
    if scp -q "$HOST:$path" "$TMP/$name" 2>/dev/null; then
        mt=$(ssh "$HOST" "date -r '$path' '+%Y-%m-%d %H:%M:%S' 2>/dev/null" 2>/dev/null || true)
        printf '  %-24s %6s lines   last written %s\n' \
            "$path" "$(wc -l < "$TMP/$name" | tr -d ' ')" "${mt:-unknown}"
    else
        printf '  %-24s absent\n' "$path"
        : > "$TMP/$name"
    fi
done

cat "$TMP/log" "$TMP/cur" > "$TMP/all"
if [ ! -s "$TMP/all" ]; then
    echo
    echo "  Nothing logged. Either nothing has gone wrong, or the patch has not"
    echo "  run since logroll.sh was deployed. Raise one deliberately to check:"
    echo "    ssh $HOST \"oscsend localhost 4001 /doNothing i 1\"   # no-op"
    echo "  …or unplug a controller: a lost device raises a warn"
    echo "  (test/checklists/nanokontrol.md, step 4)."
    exit 0
fi

# --- Summary first --------------------------------------------------------
echo
echo "── summary ───────────────────────────────────────────────────"
awk '
    /^BOOT / { sessions++; next }
    NF >= 4  { total++; lvl[$2]++; src[$3]++; txt[$2" "$3" "$4]++ }
    END {
        printf "  %d error(s) across %d recorded session(s)\n", total, sessions
        if (total == 0) exit
        printf "\n  by level:\n"
        for (l in lvl) printf "    %-8s %5d\n", l, lvl[l]
        printf "\n  by source:\n"
        for (s in src) printf "    %-16s %5d\n", s, src[s]
        printf "\n  most frequent:\n"
        n = 0
        for (t in txt) { if (txt[t] > n) { n = txt[t]; top = t } }
        if (n > 0) printf "    %-40s %5d\n", top, n
    }
' "$TMP/all"

# --- Detail, newest session first -----------------------------------------
# Sessions are delimited by logroll.sh's BOOT line, the file's only wall clock;
# every other stamp is ms since that load.
echo
echo "── detail, newest session first ──────────────────────────────"
awk '
    # n starts at 0: unset, it is the subscript "", and lines before the first
    # BOOT would land in body[""] and never print.
    BEGIN { n = 0 }
    /^BOOT / { n++; hdr[n] = $0; next }
    { body[n] = body[n] "    " $0 "\n" }
    END {
        for (i = n; i >= 0; i--) {
            if (body[i] == "" && i > 0 && hdr[i] == "") continue
            if (i == 0) {
                if (body[0] == "") continue
                print "  ── before the first BOOT line (predates the roll) ──"
            } else {
                print "  ── " hdr[i] " ──"
            }
            printf "%s", body[i]
            if (body[i] == "") print "    (no errors in this session)"
            print ""
        }
    }
' "$TMP/all"

# --- Optional truncate ----------------------------------------------------
# Asks first; FORCE=1 skips the prompt.
if [ "$CLEAR" = 1 ]; then
    echo "── clear ─────────────────────────────────────────────────────"
    echo "  About to truncate BOTH files on $HOST:"
    printf '    %-24s %s lines\n' "$LOG" "$(wc -l < "$TMP/log" | tr -d ' ')"
    printf '    %-24s %s lines\n' "$CUR" "$(wc -l < "$TMP/cur" | tr -d ' ')"
    echo "  Everything above has already been printed, but it is not saved"
    echo "  anywhere on this Mac — scroll back or redirect before agreeing."
    if [ "${FORCE:-}" = 1 ]; then
        reply=y
    else
        printf '  Truncate them? [y/N] '
        read -r reply
    fi
    case "$reply" in
        y | Y)
            ssh "$HOST" ": > '$LOG'; : > '$CUR'" && echo "  cleared."
            ;;
        *)  echo "  left alone." ;;
    esac
fi
