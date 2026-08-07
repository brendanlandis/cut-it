#!/bin/sh
# lib-scratch.sh -- the machinery every headless MIDI gate shares. SOURCED, never
# run:
#
#     . "$(dirname "$0")/lib-scratch.sh"
#
# WHY IT EXISTS. Four gates need the same five things -- a scratch copy of the
# patch, MIDI object boxes rewritten to printing stubs, a private state
# directory, a generated driver, and a watchdogged Pd run -- and until now two of
# them had two different, drifted implementations. the old phase 6 gate rewrote
# [midiout] with an anchored regex and a non-zero count; the split gates
# rewrote four other classes with an argument-tolerant regex and an exact count.
# ⛔ THE WEAKER ONE IS NOT A STYLE DIFFERENCE. It is three of the four ways a
# gate passes vacuously, shipped and green. There is one implementation now, and
# it is the strict one.
#
# ⚠️ macOS only: `sed -i ''` is BSD syntax. Every gate here is Mac-side by design.
# ⚠️ "Cut It/" IS NEVER TOUCHED. Everything happens in a scratch copy that is
# thrown away, because a built-in Pd class has no side channel -- Pd resolves the
# class table before it looks for a file, so a midiout.pd on the search path is
# simply ignored. Measured both ways.

# ---------------------------------------------------------------------------
# ⛔ THE EMITTER INVENTORY, AND IT LIVES IN EXACTLY ONE PLACE.
#
# An EXACT count per class, never "not zero". A LOWER count means boxes have
# disappeared and the assertions about them have gone vacuous; a HIGHER one means
# a new MIDI emitter no gate knows about. Both are failures and both are silent
# without this.
#
# The drift this replaces: the old phase 6 gate's comment claimed five [midiout]
# where the patch has six, and nothing noticed, because it only ever asserted the
# count was not zero.
#
# ⚠️ UPDATE THIS DELIBERATELY, NEVER TO MAKE A RED RUN GREEN. A gate going red
# here is the invariant working.
MIDI_EXPECT="midiout:6 noteout:2 ctlout:2 pgmout:1 notein:2"

# The MIDI INPUTS with no stub yet. Counted so the inventory is complete and a
# new one cannot appear unannounced -- never rewritten, because there is nothing
# to rewrite them to. ⬜ A t_ctlin would let a nanoKONTROL gate exist at all; see
# plan-v04.md.
MIDI_INVENTORY="ctlin:3 sysexin:1"

# ---------------------------------------------------------------------------
scratch_require() {
    # Every file the gate needs, before it does anything else. A gate is meant to
    # be built BEFORE the abstraction it tests, so its first run fails for a
    # known reason -- that is a real failure, not a skip.
    for f in "$@"; do
        if [ ! -f "$f" ] && [ ! -d "$f" ]; then
            echo "$f does not exist yet." >&2
            echo "That is a real failure, not a skip: the gate is meant to be built" >&2
            echo "BEFORE the abstraction, so its first run fails for a known reason." >&2
            exit 2
        fi
    done
}

scratch_make() {
    # $1 = work dir. Leaves $1/patch ready to run and $1/state empty.
    _w=$1
    mkdir -p "$_w/state" || exit 2
    cp -R "Cut It" "$_w/patch" || exit 2

    # ⛔ COPY THE STUBS WITH A HARD CHECK. A missing stub used to sail past an
    # unchecked cp and surface six windows later as confusing assertion
    # failures -- the right verdict reached by the wrong route, which costs the
    # time of a real debugging session. One clear line instead.
    for s in test/stubs/t_*.pd; do
        [ -f "$s" ] || { echo "FAIL: no stubs in test/stubs/ -- every rewritten box would" >&2
                         echo "      fail to create and every assertion would be answered" >&2
                         echo "      by an empty list." >&2; exit 2; }
        cp "$s" "$_w/patch/" || { echo "FAIL: could not copy $s" >&2; exit 2; }
    done
    cp mac-stubs/*.pd "$_w/patch/" 2>/dev/null || true

    # state-dir.sh runs through [shell], a no-op stub on the Mac, so the two
    # files have to be made here or u_state prints on every run.
    : > "$_w/state/cut-it-auto.txt"
    : > "$_w/state/cut-it-manual.txt"
}

scratch_state_dir() {
    # ⛔ OWN YOUR STATE DIRECTORY, AND ASSERT THE REPOINT WORKED. main-dev.pd
    # passes /tmp, which every run on the machine shares, and u_init restores
    # saved state at about 3.5 s. A previous test that changed mode leaves it in
    # that file, the restore republishes it mid-run, and every row keyed to
    # another mode stops matching from that instant. It cost a wrong diagnosis
    # once already: item 232.
    _w=$1
    sed -i '' "s|u_root 17 1 /tmp |u_root 17 1 $_w/state |" "$_w/patch/main-dev.pd"
    grep -q "u_root 17 1 $_w/state " "$_w/patch/main-dev.pd" || {
        echo "FAIL: could not repoint main-dev.pd's state directory." >&2
        echo "      Without that, a previous run's saved mode changes what the map" >&2
        echo "      does at 3.5 s and half the windows go silent -- item 232." >&2
        exit 2
    }
}

scratch_map_rows() {
    # $1 = work dir. Rows on stdin, APPENDED to the scratch map rather than
    # replacing it, so the shipped rows stay under test too.
    cat >> "$1/patch/cut-it-map.txt"
}

# ---------------------------------------------------------------------------
_midi_boxes() {
    # $1 = dir, $2 = class. Counts object boxes of that class, skipping the
    # stubs themselves.
    # ⚠️ THE TRAILING ARGUMENT LIST IS NOT OPTIONAL IN THIS REGEX. phase 6's was
    # anchored so the class name had to end the line, which silently skipped
    # every box with creation arguments -- and the patch has one, [ctlout 123]
    # in m_404. An anchored regex there would have made its panic assertion
    # vacuous.
    _n=0
    for _f in "$1"/*.pd; do
        case "$(basename "$_f")" in t_*) continue ;; esac
        _c=$(grep -cE "^#X obj [0-9]+ [0-9]+ $2( [^;]*)?;$" "$_f" 2>/dev/null || true)
        _n=$((_n + _c))
    done
    echo "$_n"
}

midi_check_counts() {
    # $1 = dir, $2 = the spec list. Counts only. Returns 0 if every class matches.
    _rc=0
    for _spec in $2; do
        _cls=${_spec%%:*}; _want=${_spec##*:}
        _got=$(_midi_boxes "$1" "$_cls")
        if [ "$_got" != "$_want" ]; then
            echo "FAIL: expected $_want [$_cls] box(es), found $_got." >&2
            echo "      A LOWER count means assertions about it have gone vacuous;" >&2
            echo "      a HIGHER one means a MIDI object no gate knows about." >&2
            echo "      Update MIDI_EXPECT in test/gate/lib-scratch.sh deliberately," >&2
            echo "      never silently." >&2
            _rc=2
        else
            echo "   $_got [$_cls]"
        fi
    done
    return $_rc
}

midi_rewrite() {
    # $1 = work dir. Rewrites every class in MIDI_EXPECT to its printing stub in
    # the scratch copy, asserting the exact count as it goes.
    #
    # ⚠️ IT REWRITES ALL FIVE, even for a gate that reads only one of them. That
    # is deliberate: it costs nothing -- a stub only prints -- and it means every
    # gate that makes a scratch copy enforces the whole inventory, so a new
    # emitter cannot be added without some gate going red.
    _rc=0
    for _spec in $MIDI_EXPECT; do
        _cls=${_spec%%:*}; _want=${_spec##*:}
        _got=$(_midi_boxes "$1/patch" "$_cls")
        if [ "$_got" != "$_want" ]; then
            echo "FAIL: expected $_want [$_cls] box(es), found $_got." >&2
            echo "      A LOWER count means assertions have gone vacuous; a HIGHER one" >&2
            echo "      means a new MIDI emitter the gate does not know about." >&2
            echo "      Update MIDI_EXPECT in test/gate/lib-scratch.sh deliberately," >&2
            echo "      never silently." >&2
            _rc=2
            continue
        fi
        for _f in "$1"/patch/*.pd; do
            case "$(basename "$_f")" in t_*) continue ;; esac
            sed -i '' "s/^\(#X obj [0-9]* [0-9]*\) $_cls\( [^;]*\)\{0,1\};\$/\1 t_$_cls\2;/" "$_f"
        done
        echo "   $_got [$_cls] -> [t_$_cls]"
    done
    return $_rc
}

# ---------------------------------------------------------------------------
scratch_drive() {
    # $1 = generator, $2 = output .pd, rest = generator arguments.
    #
    # ⛔ CHECK THE GENERATOR SUCCEEDED. Unchecked, the failure mode is the worst
    # kind: the driver is never written, Pd loads a file that does not exist, the
    # "; pd quit" that lives in that file never fires, and the gate HANGS FOREVER
    # instead of failing. A gate that hangs is worse than one that fails.
    _gen=$1; _out=$2; shift 2
    if ! python3 "$_gen" "$_out" "$@" >/dev/null; then
        echo "FAIL: $_gen errored -- see the traceback above." >&2
        exit 2
    fi
    [ -f "$_out" ] || { echo "FAIL: $_gen wrote no driver to $_out." >&2; exit 2; }
}

scratch_run() {
    # $1 = capture file, $2 = watchdog seconds, rest = Pd arguments.
    # ...and a watchdog on every headless run, so that no future variant of the
    # generator mistake above can hang instead of failing.
    _cap=$1; _dog=$2; shift 2
    "$PD" "$@" > "$_cap" 2>&1 &
    _pd=$!
    ( sleep "$_dog"; kill -9 "$_pd" 2>/dev/null ) 2>/dev/null &
    _watch=$!
    wait "$_pd" 2>/dev/null || true
    kill "$_watch" 2>/dev/null || true
    wait "$_watch" 2>/dev/null || true
}
