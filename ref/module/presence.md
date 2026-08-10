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

C-2's allowlist gained `presence` for this — one name, five selectors, disjoint by side so there is
no loop.

| Selector | Sent by | Means | Evidence | Item |
|---|---|---|---|---|
| `expect <src> <kind>` | every `m_`, once at `loadbang` | self-registration | verified | 269 |
| `tick` | `u_present`, on the metro | age your clock | verified | 269 |
| `lost <src>` / `back <src>` | a `c_presence`, on the transition only | the change | verified | 269 |
| `seen <src>` | a **passive** `m_`, whenever it decodes anything | last-heard | verified | 269 |

⚠️ **The poll is an outlet, not a bus message.** `c_presence`'s first outlet bangs *"send your
inquiry now"* straight into the `m_` that contains it. The plan that produced this file put `poll
<src>` on the bus; a cord inside one abstraction is strictly cheaper and keeps the rule that **only
the `m_` may talk to its device** structural instead of advisory.

⚠️ **`seen` is a cord for `active` and a bus message for `passive`, and the asymmetry is deliberate.**
An active device's liveness is consumed by its own `c_presence` two boxes away, so publishing it
would be traffic with no reader. A passive layer holds no `c_presence` at all, so the bus is the only
place its last-heard can go. Nothing reads `seen` today — [plan-v03.5.md](../../plan-v03.5.md)'s
diagnostic screen is what it exists for.

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

`u_root` instantiates `[u_present 4000 2000 33]`.

| | Value | Why | Evidence | Item |
|---|---|---|---|---|
| settle | 4000 ms | past `u_init`'s last stage — see [boot.md](boot.md) | verified | 271 |
| tick | 2000 ms | one poll per device per 2 s | verified | 271 |
| miss threshold | 3 ticks | `c_presence`'s second argument | verified | 271 |
| stagger | 0 / 60 / 120 ms | `c_presence`'s third argument, one per instance | verified | 271 |
| fork interval | every 4th tick | `[mod 4]` in `u_present` | verified | 271 |
| give-up | tick 33 | `[moses 33]`, so **8 forks** at ticks 4…32 | verified | 271 |
| trailing fork | **one**, off the transition to nothing-lost | not on the interval — see *Design* | verified | 275 |

### Every fork says which kind it is, on `err`

| Line | Fires | Evidence | Item |
|---|---|---|---|
| `warn u_present rewire-try` | each of the eight **scheduled** attempts | verified | 289 |
| `warn u_present rewire-last` | the **single trailing** fork, when the last lost device answers | verified | 289 |
| `fail u_present rewire-gaveup` | once, when the bound is spent | verified | 235 |

⛔ **A fork nothing records is a repair nobody can attribute.** The attempts had a `[print rewire]`
and nothing else — and a menu-launched patch runs `-nogui` with stdout on tty1, which VNC will not
show, so on the instrument they were invisible. ✅ **Measured 2026-08-10:** the Volca's interface
went from unsubscribed to wired on a **live** instrument, and `/sdcard/cut-it-err.log` had nothing to
say about it — no `BOOT`, no `device-lost`, no `rewire-gaveup`, Pd's pid unchanged. Something ran
`wire.sh` and nothing anywhere recorded it.

⚠️ **`warn`, not `fail`, and the difference is what makes it usable in a set.** Neither is a failure
— the give-up already says `fail`. The mode filter drops `warn` from the **screen** in perform mode
and [error.md](error.md)'s log is unconditional, so a performance records every attempt without any
of them drawing over it.

⛔ **The two names are separate because both forks converge on one `sh wire.sh` message box.** A
report tapped below that junction would name every scheduled attempt as the trailing one, and
telling those two apart is exactly the question item 275 turned on.

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

### Verified on the hardware, 2026-08-10

| Claim | How it was seen | Evidence | Item |
|---|---|---|---|
| A device **absent at load** is recovered — item 235's whole subject | Launchpad unplugged before launch, plugged in after: five `wire.sh` attempts missed it, the sixth caught it, `back m_launchpad` followed | verified | 235 |
| …and comes back **fully** | Programmer Mode re-asserted by the heartbeat at a device the init SysEx never reached, ownership restored, `g_grid` repainted the mode lamp | verified | 276 |
| An **absent** device raises no `warn` | no `warn m_launchpad device-lost` while it had never answered; the same device warned normally once seen and lost | verified | 276 |
| The give-up **reports** | `fail u_present rewire-gaveup` reached `err` — the path that was unreachable behind the shut spigot | verified | 235 |
| **Coalescing** | nano and 404 pulled together: two `rewire:` lines, not four. One bound served both | verified | 277 |
| The **safe exit** survived the watchdog rewrite | patch swapped away through `/loadPatch`: Launchpad returned to Live Mode and its Setup button responded | verified | 278 |
| ⛔ **USB enumeration races the retry** | replugged at ten seconds and the *first* attempt still missed — `wire.sh`'s own count showed 7 then 9. The Launchpad case used six of its eight | verified | 277 |
| The **SP-404 was lost on its own** and reported it | `/sdcard/cut-it-err.log`, session `BOOT 06:09:50`: `350000 warn m_404 device-lost` beside the nano, then `510000 warn m_404 device-lost` **alone**. A second `device-lost` for one source is only reachable through `[change]`, so it had come back in between; no `rewire-gaveup` follows, so it came back again | verified | 281 |
| ⛔ **Unplugging one USB device knocks a BYSTANDER off**, and the re-wire repairs it silently | the SP-404 was declared lost **twice** on 2026-08-10 without being touched — `488000` and `424000` in two sessions — each time while a neighbouring device was pulled. Links dipped and were restored by a scheduled fork six seconds later | verified | 286 |
| The give-up interval is **exactly** 64000 ms | `224000 warn m_nano device-lost` → `288000 fail`, and `522000` → `586000`. Two sessions, both exact — 32 ticks at the shipped 2000 ms | verified | 288 |
| …and **72000 ms** from load when the device is absent at load | `72000 fail u_present rewire-gaveup`, the **only** line in that session — no per-source `warn`, because nothing was ever seen | verified | 288 |
| ⛔ **ALSA renumbers clients across a replug, and `wire.sh` does not care** | the SP-404 went client `32 → 28` and the Volca's interface `28 → 32` — they swapped. After a reload every device was on its correct Pd port anyway: 404 on `128:2/128:6`, Volca on `128:3/128:7` | verified | 287 |
| **No false loss in 9.5 hours** with the whole rig connected | the session that began `BOOT 06:53:30` ran to 16:21 with four devices plugged in and wrote **one** line to `/sdcard/cut-it-err.cur` — `warn u_net net-link-down`, which is the phone's socket and not presence — see [phone.md](../device/phone.md). Three active layers polling every 2 s is ~17 000 polls each, and `m_organelle` sat passive and silent throughout | verified | 282 |

⚠️ **The bystander row is the one to remember at a gig: a warn can name a device you did not
touch.** Pulling any USB cable can take a neighbour off the bus long enough to cross the three-poll
threshold, and nothing on the instrument distinguishes that from a real unplug. It is also an
argument for the shared re-wire nobody had written down — the recovery is not only for the device
that went missing, and on both occasions it put the bystander back without anyone noticing.

⚠️ **The renumbering row is the phantom-control hazard NOT happening.** `wire.sh` connects by name,
which is stated in [boot.md](boot.md) and had never once been exercised against an actual
renumbering. Had it wired by number, the SP-404 would have landed on the Volca's channel block and
vice versa. ⛔ **The reload is what re-ran it** — a renumbering that happens while the bound is spent
leaves the rig wired to nothing until the patch is loaded again, which is exactly what was observed
before the reload.

⚠️ **The no-false-loss row is worth more than a gate can be.** Every headless gate here runs on a
Mac, where every device is absent by definition and `[sysexin]` is a stub — so *"a device that is
there is never reported missing"* is precisely the claim they cannot make. Nine and a half hours of
the real rig can, and the passive layer's silence is the same row: `m_organelle` is spoken to once at
load and never again (item 237), so an `m_organelle` that aged would have warned within seconds of
every one of those 148 boots.

⚠️ **That last row is an argument for the bound that nobody had written down.** Eight attempts over
seventy seconds is not only about giving a person time to reseat a cable — a single-shot recovery
would have failed every replug tested today, because the device is still enumerating when the first
attempt lands.

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
reads the same stream. `m_launchpad` used to treat **any** SysEx as proof of its own presence — true
only while nothing else in the rig transmitted any. Poll all three and the Launchpad reads as present
whenever the *nano* answers: item 235 un-fixed in the worst direction, with the watchdog believing a
device that is gone.

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

### The warn is armed and the recovery is not

A device that has never answered since load is **absent**, not lost — and absent is the normal state
of every device on a Mac. Arming the whole chain was item 235 itself: the recovery, *and* the give-up
that would have reported it, both sat behind a `[spigot]` only the missing device could open.

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
never per event*, and this is a fork on a transition. It is here because the recovery used to stop
the instant the last **detectable** device answered, which is not the same as the rig being whole: a
`none` device knocked off in the same event gets its one attempt while it is still enumerating, and
is then never retried. That is not hypothetical — it stranded the Volca on the bench, item 275. The
fork is bounded at exactly one per episode and fires at the best-informed instant available, because
a device answering its inquiry is the signal that enumeration has **finished**.

⚠️ **It narrows the gap rather than closing it.** Unplug a `none` device *on its own* and nothing is
lost, nothing forks, and nothing recovers — the trailing fork only helps when a detectable device
went down alongside it. See [volca.md](../device/volca.md).

**One bound, coalesced.** The counter runs while **any** source is lost and resets when **none** is,
so the rig gets eight attempts whether one cable came out or three. Two devices unplugged together
must not double the fork rate, and the gate asserts it by counting: three lost sources produce three
forks over the run, not nine.

**⚠️ 12 seconds was useless in a room.** The first version gave up that fast and the very first
hardware test missed the window entirely — nobody reseats a cable in twelve seconds. `wire.sh` costs
133 ms, is idempotent, and ten forks back to back produced no audio complaint, all measured before
Phase 4's *one fork per load, never per event* rule was bent.

**The quieter bug the shared re-wire also fixes, and it needed no code.** `wire.sh`'s three
`aconnect -d` lines undo mother's own autoconnect — but that undo has **already run** by the time a
device enumerates late, so a device plugged in after boot can land on the Launchpad's channel block.
That is the phantom-control incident `wire.sh`'s own comments record, and nothing noticed it before.
Re-running `wire.sh` fixes it, which is an argument for one shared owner rather than a recovery per
device.

**`c_presence` and `c_devid` are `c_` because there is more than one**, which is exactly why the
prefix exists. The alternative — a `[text]` roster inside `u_present` holding every device's miss
count — was the original design and was dropped: it puts per-device state in the one file that is
supposed to hold none, and it makes coalescing harder rather than easier.

**`c_presence`'s second outlet is connected in exactly one place.** `m_launchpad` uses it to drop
ownership of the grid, because a surface the patch no longer owns must stop being painted. The other
two layers hold nothing that goes stale while their device is away, so they leave it unconnected —
the loss is reported by `c_presence` itself and the re-wire is `u_present`'s.

**The Programmer Mode heartbeat stayed in `m_launchpad`.** It re-asserts a *mode* rather than
detecting anything, it rides `$0-want` rather than presence, and it is Mac-specific. It is not
presence and it did not move.

**Surfacing is the `warn` and the `fail`, and nothing else.** ⚠️ A dark grid already means three
different things — nothing changed, panic handed the surface back, or the watchdog gave up — and only
the OLED tells them apart. A fourth ambiguous grid state would make the display less informative, not
more. The diagnostic screen that reads all of this is
[plan-v03.5.md](../../plan-v03.5.md)'s, deliberately.

## Open

✅ **Two of the four are closed.** The bound is asserted by **reaching** it — `presence-assert.sh`'s
second run — and the eight bench steps exist, two per device, across the three benches named at the
top of this page. Both were plan-v0.3.4's, and that plan is gone.

⬜ **Not one of the eight bench steps has been RUN as written.** See
  [plan-v04.md](../../plan-v04.md) §3. ✅ **The SP-404's own transition run is no longer among them** —
  the device's error log had it all along, item 281 above. What is left is the **Volca**, and ⛔ **it
  cannot be tested alone**: it registers `none`, so pulling its interface loses nothing, forks
  nothing and recovers nothing, and its step has to unplug a detectable device beside it. The shared
  machinery underneath all of it is verified.

⬜ **A passive layer's last-heard is published and nothing reads it.** See
  [plan-v04.md](../../plan-v04.md) §3 and [plan-v03.5.md](../../plan-v03.5.md), which is the
  consumer. `seen m_organelle` goes on the bus for a screen that does not exist yet.
