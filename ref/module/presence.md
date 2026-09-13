<!-- schema: module -->
# Device presence and the bounded re-wire

**Files:** `Cut It/u_present.pd`, `Cut It/c_presence.pd`, `Cut It/c_devid.pd` · **Gate:** `test/gate/presence-assert.sh` · **Bench:** `test/bench/launchpad-bench.pd`, `test/bench/nanokontrol-bench.pd`, `test/bench/midi-bench.pd`

## What it is

**Unplug a USB device and ALSA destroys the subscription outright** (item 228). Nothing in the patch
noticed, and the only remedy was a reload — so a cable knocked out mid-set ended the set. This is the
answer, and the one decision that makes it legible is the split:

> **Every device keeps its own last-heard clock. They all share ONE bounded recovery.**

Deciding *"my device is gone"* has to know about that device, so it lives inside the `m_` layer as a
`c_presence` instance. Doing something about it has to happen once for the whole rig, because the
remedy — re-running `wire.sh` — re-enumerates everything at once. Three copies of a bound is not a
bound.

⛔ **`<src>` on the bus is the ABSTRACTION's name, never the hardware's** — `m_nano`, never
"nanoKONTROL". That is the `m_` boundary rather than a naming preference, and it costs nothing here
because `err`'s `source` field already carries exactly that across the same boundary. Nothing
downstream of an `m_` learns which device it is talking to.

## Facts

### The bus

C-2's allowlist gained `presence` for this — one name, **six** selectors, disjoint by side so
there is no loop. Five are the `m_` layers' and `u_present`'s own; the sixth is the phone's
button, and it is the only one written by a file that owns no device.

| Selector | Sent by | Means | Evidence | Item |
|---|---|---|---|---|
| `expect <src> <kind>` | every `m_`, once at `loadbang` | self-registration | verified | 269 |
| `tick` | `u_present`, on the metro | age your clock | verified | 269 |
| `lost <src>` / `back <src>` | a `c_presence`, on the transition only | the change | verified | 269 |
| `seen <src>` | a **passive** `m_` on every decode, and an **active** one **once** — its device's first ever answer | last-heard | verified | 269, 302 |
| `re-wire` | `u_net`, when the phone's button is pressed | run `wire.sh` now | verified | 306 |

⚠️ **The poll is an outlet, not a bus message.** `c_presence`'s first outlet bangs *"send your
inquiry now"* straight into the `m_` that contains it. A cord inside one abstraction is cheaper than
a bus selector and keeps the rule that **only the `m_` may talk to its device** structural instead
of advisory.

⚠️ **`seen` means different things on the two sides, and the asymmetry is deliberate.** An active
device's liveness is consumed by its own `c_presence` two boxes away — a **cord**, not the bus — so
publishing it every two seconds forever would be traffic with a reader that does not need it. A
passive layer holds no `c_presence` at all, so the bus is the only place its last-heard can go, and
it publishes on **every** decode.

⛔ **An active layer publishes `seen <src>` too, EXACTLY ONCE**, the first time its device ever
answers — item 302. **That one message is the only thing on the bus that
separates a device which has GONE from one that was NEVER SEEN**, because `lost` is published
unarmed and the two are otherwise byte-identical. It is the mildest possible way to make the
selector uniform: once per device per session, no new polling, no rate concern.

**The alternative was reading the `err` bus.** `warn <src> device-lost` fires only for a device that
was seen and then lost — item 276, verified — so the screen could have inferred the same bit with no
change here at all. **It was rejected because it couples a display to another module's message
TEXT**: reword the warning and the screen silently stops telling missing from never-seen, with
nothing failing anywhere. `presence-assert.sh` asserts the count is **exactly one** per source, and
that a source which has answered nothing has published none.

### The three kinds, and every layer declares one

| Kind | Layers | Polled | Ages | Can be lost | Evidence | Item |
|---|---|---|---|---|---|---|
| `active` | `m_launchpad` `m_nano` `m_404` | yes | yes | yes | verified | 270 |
| `passive` | `m_organelle` | no | **no** | no | verified | 270 |
| `none` | `m_volca` | no | no | no | verified | 270 |

**Self-registration is `state`'s shape** — a contributor names its own key and declares its own
policy — and it is what lets an `m_` written long after `u_present` be covered with no change to
`u_present`. The roster is five, and `presence-assert.sh` asserts the number rather than printing it.

### The manufacturer byte, which is what `c_devid` matches

All three detectable devices answer a universal device inquiry — `F0 7E 7F 06 01 F7` — and byte 5 of
the reply discriminates all three. Measured on these units.

| Device | Reply | Byte 5 | `c_devid` arg | Evidence | Item |
|---|---|---|---|---|---|
| Launchpad Pro MK3 | `F0 7E 00 06 02 00 20 29 23 01 00 00 00 04 06 05 F7` | `00` | `0` | verified | 249 |
| nanoKONTROL | `F0 7E 00 06 02 42 04 01 00 00 23 00 00 00 F7` | `42` | `66` | verified | 249 |
| SP-404MKII | `F0 7E 10 06 02 41 08 04 00 00 00 03 00 00 F7` | `41` | `65` | verified | 249 |

⛔ **The argument is decimal and the reply is hex.** `42` is 66 and `41` is 65. Passing `[c_devid 42]`
for the nano matches manufacturer `0x2A`, which is nobody, and the device is then never detected —
silently, because a matcher that matches nothing looks exactly like a device that is not there.

### The arithmetic, and every number in it is load-bearing

`u_root` instantiates `[u_present 4000 2000 33 8]`.

| | Value | Why | Evidence | Item |
|---|---|---|---|---|
| settle | 4000 ms | past `u_init`'s last stage — see [boot.md](boot.md) | verified | 271 |
| tick | 2000 ms | one poll per device per 2 s | verified | 271 |
| miss threshold | 3 ticks | `c_presence`'s second argument | verified | 271 |
| stagger | 0 / 60 / 120 ms | `c_presence`'s third argument, one per instance | verified | 271 |
| fork interval | every 4th tick | `[mod 4]` in `u_present` | verified | 271 |
| give-up | tick 33 | `[moses 33]`, so **8 forks** at ticks 4…32 | verified | 271 |
| trailing fork | **one**, off the transition to nothing-lost | not on the interval — see *Design* | verified | 275 |
| watch interval | every **8 ticks**, so ~16 s | `u_present`'s fourth argument — the heartbeat below | verified | 292 |

### The heartbeat, for a device nothing ever lost

⛔ **Everything above recovers a device that WAS here and went away, and every bit of it is gated on
something being LOST.** A device registered `none` has no clock and can never be lost, so the
bounded recovery never runs for it: plug the Volca's interface into a running instrument and it
enumerates in under a second and sits **completely unsubscribed, forever** (item 285).

`u_present` forks **`wire-watch.sh`** on its own interval, off the raw tick rather than through the
recovery's spigot.

| | Value | Evidence | Item |
|---|---|---|---|
| What it hashes | the ALSA **client names** only, never the subscriptions | verified | 292 |
| Cost of the probe | **~50 ms**, measured three times on the device | verified | 292 |
| Cost of `wire.sh` itself | **~247 ms**, measured three times | verified | 292 |
| `wire.sh` is idempotent | 9 connections, twice in a row, no change | verified | 292 |

⛔ **Hashing the names and not the subscriptions is the whole trick.** `aconnect -l` prints
`Connecting To:` under each client, so hashing all of it would change the moment `wire.sh` connected
anything — the watcher would see its own work as a change and re-wire again on the next tick,
forever. ✅ Measured both ways: with the filter the hash is **byte-identical** across a `wire.sh`
run, so one device event costs one re-wire.

⚠️ **This is a fork on a real event, not a fork on a timer**, which is the distinction Phase 4's
one-fork-per-load rule is actually about. The heartbeat costs one 50 ms probe; the 247 ms re-wire
happens only when the rig has actually changed.

⛔ **Pd 0.49 cannot read `/proc` and that was measured, not assumed.** Watching
`/proc/asound/seq/clients` with `[text read]` would have cost no fork at all — but procfs reports
size 0, Pd `lseek`s, and the read fails outright: `lseek: Invalid argument`, `text size` 0.

### Every fork says which kind it is, on `err`

| Line | Fires | Evidence | Item |
|---|---|---|---|
| `info u_present rewire-try` | each of the eight **scheduled** attempts | verified | 289 |
| `info u_present rewire-last` | the **single trailing** fork, when the last lost device answers | verified | 289 |
| `info u_present rewire-phone` | the phone's button, once per press — [phone.md](../device/phone.md) | verified | 306 |
| `fail u_present rewire-gaveup` | once, when the bound is spent | verified | 235 |

⛔ **A fork nothing records is a repair nobody can attribute.** A `[print]` is not a record: a
menu-launched patch runs `-nogui` with stdout on tty1, which VNC will not show, so on the instrument
a fork that only prints is invisible, and a device can go from unsubscribed to wired with nothing in
`/sdcard/cut-it-err.log` to say so.

⚠️ **`info`, which is logged and never drawn** — see [error.md](error.md). Neither is a failure, the
give-up already says `fail`, and eight alerts per episode on a 21-character screen mid-set is noise.

⛔ **The three names are separate because all three forks converge on one `sh wire.sh` message
box.** A report tapped below that junction would name every scheduled attempt as the trailing one,
and telling those two apart is exactly the question item 275 turned on. The phone's is the only one a
person caused, which is the distinction most worth having in a log read afterwards.

Which puts the wall clock at, from load:

| At | Happens | Evidence | Item |
|---|---|---|---|
| 8 s | every unanswered device is declared lost, and the shared counter starts on that same tick | verified | 271 |
| 14 s | first `wire.sh` | verified | 271 |
| every 8 s after | forks 2 through 8 | verified | 271 |
| 70 s | the eighth and last fork | verified | 271 |
| 72 s | `fail u_present rewire-gaveup`, once, naming nobody — the per-source `warn`s already did | verified | 271 |

⚠️ **The last two rows are verified as COUNTS, and the wall clock is those counts times the tick.**
`presence-assert.sh`'s second run scales the settle and the tick by ten and leaves the counts exactly
as shipped, so the eighth fork and the give-up genuinely happen — at 7.0 s and 7.2 s, measured — and
what carries over to the shipped tick is *counter 32* and *counter 33*, not the seconds. Nothing in
`test/run.sh` runs for seventy seconds and nothing needs to.

### Behaviour on the rig

| Claim | Evidence | Item |
|---|---|---|
| A device **absent at load** is recovered by the scheduled forks — and comes back **fully**: Programmer Mode re-asserted, ownership restored, the mode lamp repainted | verified | 235, 276 |
| An **absent** device raises no `warn`; the same device warns normally once seen and then lost | verified | 276 |
| The give-up **reports** — `fail u_present rewire-gaveup` reaches `err` | verified | 235 |
| **Coalescing** — two devices pulled together produce two `rewire:` lines, not four. One bound serves both | verified | 277 |
| The **safe exit** survives a `/loadPatch` swap: the Launchpad returns to Live Mode and its Setup button responds | verified | 278 |
| ⛔ **USB enumeration races the retry** — a replug at ten seconds still misses the *first* attempt, and one case used six of the eight | verified | 277 |
| A device can be **lost and come back on its own**, twice in one session, with no `rewire-gaveup` — a second `device-lost` for one source is only reachable through `[change]` | verified | 281 |
| ⛔ **Unplugging one USB device can knock a BYSTANDER off** the bus long enough to cross the three-poll threshold; a scheduled fork puts it back within seconds, and nothing on the instrument distinguishes it from a real unplug | verified | 286 |
| The give-up interval is **exactly** 64000 ms after `device-lost` — 32 ticks at the shipped 2000 ms — and **72000 ms** from load for a device absent at load, with no per-source `warn` because nothing was ever seen | verified | 288 |
| ⛔ **ALSA renumbers clients across a replug** — the SP-404 and the Volca's interface swapped `32 ↔ 28` — and `wire.sh` does not care: it connects by name, so every device lands on its correct Pd port | verified | 287 |
| **No false loss in 9.5 hours** with four devices connected — one line in `/sdcard/cut-it-err.cur`, `warn u_net net-link-down`, which is the phone's socket and not presence ([phone.md](../device/phone.md)). Three active layers polling every 2 s is ~17 000 polls each; `m_organelle` sat passive and silent throughout | verified | 282 |

⚠️ **The bystander row is the one to remember at a gig: a warn can name a device you did not
touch.** It is also an argument for the shared re-wire — the recovery is not only for the device that
went missing.

⚠️ **The renumbering row is the phantom-control hazard NOT happening.** Wired by number, the SP-404
would land on the Volca's channel block and vice versa. ⛔ **But a renumbering that happens while the
bound is spent leaves the rig wired to nothing until something re-runs `wire.sh`** — the heartbeat
hashes client *names*, which a renumbering does not change, so that something is the phone's
`re-wire` button or a reload.

⚠️ **The no-false-loss row is worth more than a gate can be.** Every headless gate here runs on a
Mac, where every device is absent by definition and `[sysexin]` is a stub — so *"a device that is
there is never reported missing"* is precisely the claim they cannot make. Nine and a half hours of
the real rig can, and the passive layer's silence is the same row: `m_organelle` is spoken to once at
load and never again (item 237), so an `m_organelle` that aged would warn within seconds of every
boot.

⚠️ **The enumeration row is an argument for the bound.** Eight attempts over seventy seconds is not
only about giving a person time to reseat a cable — a single-shot recovery fails every replug,
because the device is still enumerating when the first attempt lands.

⚠️ **A run longer than ~70 s with a device unplugged now raises a real `fail` on `err`.** That is the
feature working. Nothing in `test/run.sh` runs that long; a hands-on bench for another device will
see it.

### The inquiry leaves through the `m_`'s own port

`[midiout]` is the one MIDI object that takes the port as a plain number rather than encoding it in
the channel, so each `m_` derives it from the channel block it already takes as a creation argument:

| | Formula | Block | Port | Evidence | Item |
|---|---|---|---|---|---|
| `m_launchpad` | literal `1` | 1 | 1 | verified | 272 |
| `m_nano` | `(n-1)/16+1` | 17 | 2 | verified | 272 |
| `m_404` | `(n-1)/16+1` | 33 | 3 | verified | 272 |

⚠️ **`m_launchpad` hardcodes its port and gets away with it only because its block and its port are
both 1.** Do not copy that into a new layer.

## Traps

### One `[sysexin]` hears every device in the rig

There is exactly one `[sysexin]` box in the patch, inside `c_devid`, and every instance of `c_devid`
reads the same stream. Treating **any** SysEx as proof of one device's presence holds only while
nothing else in the rig transmits any. Poll all three and the Launchpad reads as present whenever the
*nano* answers, with the watchdog believing a device that is gone.

**Fix:** `[c_devid <byte>]` per device, never a bare `[sysexin]`. `presence-assert.sh` drives a KORG
reply and asserts the Launchpad stays lost — **and** drives the Launchpad's own and asserts it does
not, because a matcher that accepts nothing passes the first check for the wrong reason.

### A passive device must not age

✅ **mother pushes the Organelle's knobs once at load and then says nothing** — item 237, measured. A
last-heard clock on `m_organelle` would therefore run out a few seconds into **every** boot and put a
`device-lost` warning on the screen for hardware that is bolted to the instrument.

**Fix:** `passive` layers publish `expect` and `seen` and instantiate no `c_presence`. What a passive
layer can offer is *last heard*; what it cannot offer is the difference between unplugged and
untouched, and no amount of code changes that — the operator supplies it.

### A passive layer's `seen` has to come off EVERY source it has

⛔ `m_organelle` publishes `seen m_organelle` from its fan-in. A source wired around that fan-in —
the knobs going straight to `param`, say — publishes no `seen` at all, silently, and **the knobs are
the worst possible source to lose**: ✅ mother pushes them once at load and then says nothing
(item 237), so the one thing the Organelle ever sends unprompted no longer says the Organelle is
there, and the layer reads as never-heard on a device that has in fact spoken. Nothing but a screen
that draws last-heard can see it (item 303).

**Fix:** the four knobs fan in to a `[t a b]` of their own, `b` before `a`, so `seen` goes out ahead
of the value exactly as it does for `og-aux`. ⚠️ **There are two fan-ins in that file, not one.**

### The warn is armed and the recovery is not

A device that has never answered since load is **absent**, not lost — and absent is the normal state
of every device on a Mac. Arming the whole chain on first-seen puts the recovery, *and* the give-up
that would report it, behind a `[spigot]` only the missing device can open (item 235).

**Fix:** the gate is **split, not removed**. `$0-seen-ever` gates the `warn` only. `lost` still
publishes unarmed, because that is what drives the recovery, and the give-up stays unconditional. Two
gates test the two directions: ownership must **not** drop for a device that never answered, and must
drop for one that answered and then went away.

### The stagger is not cosmetic

`u_present` broadcasts **one** `tick` and every `c_presence` hears it in the same logical instant, so
three inquiries would leave together and three replies could come back interleaved byte by byte on
the single `[sysexin]`. `c_devid`'s index would then be counting one device's frame with another
device's bytes in it.

**Fix:** `c_presence`'s third argument delays the poll — 0, 60 and 120 ms. It costs nothing and makes
the interleave impossible.

### The settle is coupled to `u_init`'s last stage

Started at `loadbang`, the first re-wire lands inside `init-assert.sh`'s 8.6 s window, and that gate
requires **exactly one** `wire.sh` — so it goes red for a reason that has nothing to do with what it
tests.

**Fix:** the 4000 ms settle, the same way `u_tempo`'s 4000 is handled. **Change a stage timing and
this changes with it** — [boot.md](boot.md) holds the table both numbers answer to.

### `[change]` is bare here, where every other one in the patch carries `-1`

A bare `[change]` starts life holding 0, which `m_organelle` and `u_level` both have to work around.
In `c_presence` that is exactly the wanted cold start, because **0 is not-lost**: the first tick
computes 0, `change` swallows it, and nothing is published until something actually crosses.

## Design

**One trailing fork, and it bends Phase 4's rule deliberately.** That rule is *one fork per load and
never per event*, and this is a fork on a transition. Without it the recovery stops the instant the
last **detectable** device answers, which is not the same as the rig being whole: a `none` device
knocked off in the same event gets its one attempt while it is still enumerating, and is then never
retried (item 275). The fork is bounded at exactly one per episode and fires at the best-informed
instant available, because a device answering its inquiry is the signal that enumeration has
**finished**.

⚠️ **It narrows the gap rather than closing it.** Unplug a `none` device *on its own* and nothing is
lost, nothing forks, and nothing recovers — the trailing fork only helps when a detectable device
went down alongside it. See [volca.md](../device/volca.md).

**One bound, coalesced.** The counter runs while **any** source is lost and resets when **none** is,
so the rig gets eight attempts whether one cable came out or three. Two devices unplugged together
must not double the fork rate, and the gate asserts it by counting: three lost sources produce three
forks over the run, not nine.

**⚠️ The bound is seventy seconds because nobody reseats a cable in twelve.** `wire.sh` is
idempotent and ten forks back to back produce no audio complaint, which is what makes bending the
*one fork per load* rule permissible. **Its cost is in the heartbeat table above.**

**The shared re-wire also fixes the phantom-control case, and it needs no code.** `wire.sh`'s three
`aconnect -d` lines undo mother's own autoconnect — but that undo has **already run** by the time a
device enumerates late, so a device plugged in after boot can land on the Launchpad's channel block.
Re-running `wire.sh` fixes it, which is an argument for one shared owner rather than a recovery per
device.

**`c_presence` and `c_devid` are `c_` because there is more than one**, which is exactly why the
prefix exists. A `[text]` roster inside `u_present` holding every device's miss count was rejected:
it puts per-device state in the one file that is supposed to hold none, and it makes coalescing
harder rather than easier.

**`c_presence`'s second outlet is connected in exactly one place.** `m_launchpad` uses it to drop
ownership of the grid, because a surface the patch no longer owns must stop being painted. The other
two layers hold nothing that goes stale while their device is away, so they leave it unconnected —
the loss is reported by `c_presence` itself and the re-wire is `u_present`'s.

**The Programmer Mode heartbeat stayed in `m_launchpad`.** It re-asserts a *mode* rather than
detecting anything, it rides `$0-want` rather than presence, and it is Mac-specific. It is not
presence and it did not move.

**Surfacing is the `warn` and the `fail`, and nothing else.** ⚠️ A dark grid already means two
different things — nothing changed, or the watchdog gave up — and only the OLED tells them apart. A
third ambiguous grid state would make the display less informative, not more. The diagnostic screen
that reads all of this is `g_oled`'s **diag** layer — item 301, on [display.md](display.md).

**Panic is not a third cause.** It does not touch the Launchpad's ownership at all (item 251), and it
paints the surface **red** for a second (item 296) — a state nothing could mistake for dark. See
[display.md](display.md).

## Open

- ⬜ **The Volca cannot be tested alone.** It registers `none`, so pulling its interface loses
  nothing, forks nothing and recovers nothing, and both its bench steps unplug the interface and
  lean on a detectable device beside it. Permanent, for a device that can never be lost, so
  **NO PLAN OWNS THIS**.
