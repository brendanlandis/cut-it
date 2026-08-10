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
#
# ⚠️ IT IS "EVERY CLASS THAT GETS REWRITTEN", not "every emitter" -- notein and
# ctlin are INPUTS and they are here because test/stubs/ has a source stub for
# each. The name is older than the notein stub and is kept because every gate,
# every error message and the gate skill all cite it.
# midiout went 6 -> 8 when m_nano and m_404 gained device presence: an inquiry
# has to leave through the m_'s OWN port, and midiout is the one MIDI object that
# takes the port as a number rather than encoding it in the channel.
MIDI_EXPECT="midiout:8 noteout:2 ctlout:2 pgmout:1 notein:2 ctlin:3 sysexin:1"

# The MIDI objects with no stub. Counted so the inventory is complete and a new
# one cannot appear unannounced -- never rewritten, because there is nothing to
# rewrite them to.
#
# [sysexin] used to be the only entry and it moved UP into MIDI_EXPECT when
# t_sysexin landed: the hot-swap work needed to DRIVE a device-inquiry reply,
# because a reply is the only evidence of presence there is and it arrives on a
# MIDI input, where there is no bus to fake.
#
# ⛔ [polytouchin] WAS NEVER IN EITHER LIST, AND NOTHING NOTICED. It is
# m_launchpad's polyphonic aftertouch decode -- "the most expressive control on
# the rig" by its own page -- and this file's header has claimed "these are all
# the MIDI objects in the patch" the whole time it was missing. Found by
# midi_scan_unknown on its first run, which is the check that asks the question
# in the direction that can actually answer it. ⬜ It is COUNTED and not covered:
# a t_polytouchin would be the same shape as t_ctlin, and the pressure path it
# would unlock is nobody's yet. See ref/device/launchpad.md.
MIDI_INVENTORY="polytouchin:1"

# ⛔ EVERY MIDI CLASS Pd HAS, so "these are all the MIDI objects in the patch" can
# be checked as a CLOSED question rather than by listing what we expect and
# hoping the list is complete. The old inventory could only ever find a drift in
# a class someone had already thought of.
MIDI_ALL_CLASSES="notein ctlin pgmin bendin touchin polytouchin midiin sysexin \
midirealtimein midiclkin noteout ctlout pgmout bendout touchout polytouchout \
midiout"

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

scratch_scale_present() {
    # ⛔ SCALE THE TWO TIMES AND LEAVE THE COUNTS ALONE, AND ASSERT THE REWRITE
    # WORKED. Same shape and same reason as scratch_state_dir above.
    #
    # WHY IT IS NEEDED AT ALL. u_present's bound -- eight wire.sh attempts and
    # then a give-up -- is 72 seconds wide at the shipped tick, and no gate in
    # this suite runs that long. So the only claim presence-assert could make
    # about it was arithmetic read off [moses 33], which is not a claim about a
    # run at all. u_present takes the settle, the tick and the give-up as
    # creation arguments PRECISELY so a scratch copy can divide the two TIMES by
    # ten and reach counter 33 in about seven seconds.
    #
    # ⛔ ONLY THE SETTLE AND THE TICK MOVE. 3 (c_presence's missed-tick
    # threshold) and 33 (the give-up) are the SHIPPED counts, and a gate that
    # scaled those would be asserting a different patch than the one that ships
    # -- which is the most expensive kind of green there is.
    #
    # ⚠️ IT DELIBERATELY BREAKS THE SETTLE'S COUPLING TO u_init, and that is safe
    # HERE and nowhere else. The 4000 ms settle exists so the first re-wire lands
    # past u_init's last stage; at 400 ms it does not, so u_init's own boot fork
    # at 1500 ms lands BETWEEN recovery forks 1 and 2. The bound driver's windows
    # are drawn knowing that. ⛔ Do not reuse this in a gate that counts forks
    # per window without accounting for it.
    _w=$1
    sed -i '' "s|u_present 4000 2000 33|u_present 400 200 33|" "$_w/patch/u_root.pd"
    grep -q "u_present 400 200 33" "$_w/patch/u_root.pd" || {
        echo "FAIL: could not scale u_present's settle and tick." >&2
        echo "      Without that the give-up is 72 s away, the run quits at 9 s," >&2
        echo "      and every count below is answered by a recovery that never" >&2
        echo "      got started -- which looks exactly like a bound that fires" >&2
        echo "      nothing." >&2
        exit 2
    }
}

scratch_phone_mirror() {
    # ⛔ POINT u_net AT THIS MACHINE, AND ASSERT THE REPOINT WORKED. Same shape
    # and same reason as scratch_state_dir above.
    #
    # WHY IT IS NEEDED AT ALL. u_net sends to the phone, so on a live run the
    # Mac cannot see those datagrams -- a tap on the device would prove what
    # u_net was OFFERED, not what it FILTERED, and the filtering is the whole
    # subject. Repointing it at localhost in a throwaway copy gives real OSC
    # verdicts with no phone in the room. ⚠️ It answers a DIFFERENT question
    # from a device run with a real phone, and neither replaces the other.
    #
    # ⛔ A SILENT MISS HERE IS THE WORST OUTCOME: every datagram would go to a
    # real address on the network and the predicate would read an empty socket,
    # which looks exactly like u_net being broken.
    _w=$1; _port=${2:-9995}
    sed -i '' "s|u_net 192.168.1.5 8000|u_net 127.0.0.1 $_port|" "$_w/patch/u_root.pd"
    grep -q "u_net 127.0.0.1 $_port" "$_w/patch/u_root.pd" || {
        echo "FAIL: could not repoint u_net at localhost." >&2
        echo "      Without that every datagram goes to a real address and the" >&2
        echo "      predicate reads an empty socket -- which looks exactly like" >&2
        echo "      u_net being broken." >&2
        exit 2
    }
}

scratch_udp_sink() {
    # $1 = port, $2 = seconds to live. Binds a UDP socket and prints its PID.
    #
    # ⛔ IT EXISTS BECAUSE THREE GATES SILENTLY DEPENDED ON THE MAC'S LAN. u_net
    # points at a literal phone address, and a datagram to an address that
    # answers with ICMP port-unreachable TEARS THE SOCKET DOWN -- item 114 --
    # which raises `warn u_net net-link-down`. That alert takes the OLED footer
    # and lands in the error log, so oled-assert and err-assert fail on whichever
    # window it happens to hit, with a message about u_net that has nothing to do
    # with what either gate tests.
    #
    # ⚠️ IT PASSED FOR MONTHS BY LUCK. Nothing on the network answered, the ICMP
    # never came back, and the socket stayed up. The day something did answer,
    # two gates went red and pointed at the wrong module.
    #
    # ⚠️ REPOINTING ALONE IS NOT ENOUGH, which is the trap here. Sending to
    # 127.0.0.1 with nothing bound is the WORST case -- the local stack answers
    # with ICMP immediately and reliably. The socket has to actually exist.
    # phone-assert.py binds before Pd starts for exactly this reason.
    #
    # ⚠️ ITS STDOUT MUST GO TO /dev/null OR THE CALLER HANGS. This is read back
    # through $(...), and a command substitution does not return until every
    # process holding that pipe has let go of it -- including a BACKGROUND one.
    # Without the redirect the gate waits out the sink's whole lifetime.
    python3 -c 'import socket,sys,time
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# ⚠️ REUSEADDR so a sink still lingering from an interrupted run cannot stop the
# next one binding. Without it the bind raises, the sink dies unseen behind the
# /dev/null redirect, and the gate fails on net-link-down as though nothing had
# been done about it.
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("127.0.0.1", int(sys.argv[1])))
time.sleep(float(sys.argv[2]))' "$1" "${2:-90}" >/dev/null 2>&1 &
    echo $!
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

midi_scan_unknown() {
    # $1 = dir. Fails if any MIDI class present in the patch is named by NEITHER
    # MIDI_EXPECT nor MIDI_INVENTORY.
    #
    # ⛔ THIS IS THE HALF THAT CANNOT GO VACUOUS. midi_check_counts walks a list
    # we wrote and asks the patch about each entry, so a class nobody thought of
    # is invisible to it -- and once MIDI_INVENTORY emptied, the "counted only"
    # arm of midi-emitters-assert became a loop over nothing that returned 0.
    # This walks the CLASSES and asks the list, which is the closed question the
    # gate has always claimed to answer.
    _rc=0
    _known=" $(echo "$MIDI_EXPECT $MIDI_INVENTORY" | tr ' ' '\n' \
                | sed 's/:.*//' | tr '\n' ' ')"
    for _cls in $MIDI_ALL_CLASSES; do
        _got=$(_midi_boxes "$1" "$_cls")
        [ "$_got" = "0" ] && continue
        case "$_known" in
            *" $_cls "*) ;;
            *)  echo "FAIL: $_got [$_cls] box(es) in the patch, and NO gate knows." >&2
                echo "      A MIDI object nobody inventoried is a way to talk to a" >&2
                echo "      device that nothing is watching. Add it to MIDI_EXPECT in" >&2
                echo "      test/gate/lib-scratch.sh, give it a stub, and give it a" >&2
                echo "      gate at the same time." >&2
                _rc=2 ;;
        esac
    done
    [ "$_rc" = "0" ] && echo "   no MIDI class outside the inventory"
    return $_rc
}

midi_rewrite() {
    # $1 = work dir. Rewrites every class in MIDI_EXPECT to its printing stub in
    # the scratch copy, asserting the exact count as it goes.
    #
    # ⚠️ IT REWRITES ALL SIX, even for a gate that reads only one of them. That
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
