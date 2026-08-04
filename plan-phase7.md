# Phase 7 — the phone status link (`u_net`)

The execution plan. [plan-v02.md](plan-v02.md) keeps the one-paragraph summary and **remains the
only home for open questions**.

**Done when:** every parameter shown on the OLED also reaches the phone, a fast fader sweep does
not flood the wire, and pulling the plug shows `NO-LINK` on the phone within 1.5 s.

**Where it stands: built and Mac-verified. Never deployed.** That is the exact position Phase 6
was in before it shipped three bugs, so the remaining work is not a formality.

---

## Built ✅

| | |
|---|---|
| `Cut It/u_net.pd` | The abstraction. Consumes `disp`, coalesces per name at 20 Hz, holds the alert as state, reconnects |
| `Cut It/u_root.pd` | One appended box, `u_net 192.168.1.5 8000`. 38 → 40 boxes, **7 cords unchanged** |
| `tools/phase7-assert.{sh,py}` + `-drive-gen.py` | The headless gate. **25 checks, and it was proven able to fail before it was trusted** |
| `tools/phase7-bench.pd` | 15 steps via `STEPS7` in `bench_steps.py`. `bench-verify.py` passes |
| `tools/pdparty-scene/CutItRemote/_main.pd` | Promoted: six rows, `status` and `alert` added, the value is a `cnv` label rather than an `nbx` |

Measurements are [plan-tests.md](plan-tests.md) **Session 9, items 113–118**. The design decisions
and what each cost are in the same place.

**What Step 0 changed, in one line:** a UDP `connect` to a host that is up with nothing listening
succeeds, delivers exactly one datagram, and is then destroyed by the ICMP port-unreachable — after
which every send is discarded in silence. **The reconnect is the feature, not a nicety.** Item 114.

---

## Two claims in the earlier draft of this file were wrong

Corrected here rather than annotated, and both were caught by arithmetic rather than by measuring:

- **`NO-LINK` needed no work.** The phone restarts a 1500 ms timer on every datagram and the
  heartbeat is 500 ms, so the last packet is at most 500 ms old when the link drops: `NO-LINK`
  lands **1.0–1.5 s** after the loss. The spec was already met by the prototype.
- ⚠️ **"UDP out has sat at ~117/s since Phase 3 — if `u_net` moves that number, rate limiting is
  not working" is not a usable gate.** The heartbeat alone is +2/s and the repeated alert state
  another +2/s. **The real targets are ~121–124/s idle and ≤ ~140/s under a sweep**, and what
  matters is that the number does not track the *control* rate — which at Step 0 was measured at
  402 `disp` messages per second from one moving knob.

---

## Step 7 — the device run, and it is all that is left

⚠️ **A green Mac bench does not mean the phase is done.** Phase 6 passed 25/25 on the Mac, twice,
and shipped three bugs that only existed on the Organelle. Budget for a full hardware pass and
expect it to find something.

1. **`./deploy.sh`** — it syntax-checks both entry points and refuses on any output.
2. **`tools/phase7-bench.pd`**, stepped with `./tools/go.sh`. ⚠️ **PdParty must be open on the
   `CutItRemote` scene before step 1**, which is what step 1 exists to confirm.
   ⚠️ **GO is `./tools/go.sh`, never the encoder and never netcat** — both cost time in Phase 6.
3. **`tools/phase6-cpu.sh -n 3`** against the **11.8 %** baseline, of which 6.9 points is DSP and
   only 0.43 the MIDI clock.

**The three things most likely to fail, in order:**

- ⚠️ **Item 114 on Linux/ARM.** The ICMP teardown was measured on **macOS**. Linux is documented to
  behave the same for connected UDP sockets, and this project's history is that documented claims
  are where the surprises live. **Bench steps 13–14 — close PdParty, reopen it — are the only way
  to reach it**, and if the reconnect does not work the link is dead for a whole set with nothing
  on the instrument to say so.
- **The idle UDP rate.** Anything far off ~121–124/s means something is sending that should not be.
- **`[text]` behaviour under the real scheduler.** The coalescer's flush walks the pending text on
  a 50 ms tick; it has never run alongside DSP, the MIDI clock and the grid repaint.

⚠️ **Check `ssh` before debugging any of it.** The Organelle drops its wifi after about an hour,
unattributed, and it broke a deploy mid-session during Phase 6. **It will look exactly like a
`u_net` bug and it is not.**

---

## The landing checklist, once the device run passes

Not optional — [ref-conventions.md](ref-conventions.md), *How a phase runs*, step 6.

- Phase 7's section **leaves** [plan-v02.md](plan-v02.md); its *Stage-readiness* bullets for rate
  limiting and the `nbx` cosmetic are **done** and go with it.
- The build log gains Phase 7. ⚠️ Include the two corrections above — *every phase's most valuable
  output was a correction to something the plan asserted*, and this one is no exception.
- `ref-display.md`'s ⬜ *"the link is not yet stage-worthy, on four counts"* drops to **two**: the
  access point and phone hardening. Rate limiting and the `nbx` are resolved.
- This file is deleted.

---

## Explicitly NOT in this phase

- **Organelle as its own access point.** ⚠️ **Bringing up an AP drops SSH** — read
  [plan-tests.md](plan-tests.md) Session 5's warning first. It is the last thing between the phone
  display and being stage-worthy, and it deserves its own session.
- **Phone hardening.** Do Not Disturb and Guided Access. Not code.
- ⚠️ **The wifi drop above.** Unattributed — dongle, power, AP or `wifi_control.py`.
