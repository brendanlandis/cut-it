# What to do once the wifi fault has been caught

Hand this to an agent together with the output of `./tools/wifi-report.sh`.

This is **[plan-tests.md](plan-tests.md) items 81 and 133** — the Organelle losing its network
after roughly an hour. It has been open since Phase 6 and was misdiagnosed for two phases, so the
first section is about not repeating that.

---

## Read this before drawing any conclusion

Three things are already established. Do not re-derive them, and do not contradict them without
evidence.

- ⚠️ **The device stays ASSOCIATED.** `wpa_supplicant` and `dhcpcd` keep running, the SSID and
  BSSID are intact, the signal is fine. **What it loses is the IPv4 lease.** "The Organelle drops
  its wifi" is the wrong mental model and sent this investigation at the dongle for two phases.
- ⚠️ **SSH KEEPS WORKING** — over IPv6 link-local, via mDNS. A successful login is **not** evidence
  the network is up. The check is `ip addr show wlan0 | grep "inet "`. This is what made the fault
  look mysterious rather than simple.
- ⚠️ **A restart fixes it first try. A `dhcpcd -n` renew did not.** Whatever the mechanism, it
  survives a renew and does not survive a reboot.

**And one thing that is NOT established:** the cause. Item 81 has blamed the dongle, power, the
access point and `wifi_control.py` at various times, on no evidence. **Do not add a fifth guess.**

---

## The decision tree

`wifi-report.sh` prints which recovery rung worked. That is the discriminating evidence.

### Rung 1 worked — `dhcpcd -n wlan0` (renew)

**Meaning:** the lease expired and renewal never fired, but `dhcpcd` was healthy enough to renew
on demand.

**Do next:** compare **uptime-to-failure** against the **DHCP lease time**:

```sh
ssh root@organelle.local 'dhcpcd -U wlan0 2>/dev/null | grep -i lease'
```

If they match, that is the answer — the lease expires and renewal is not happening. Look at why
`dhcpcd` is not renewing at T/2 as it should.

⚠️ **This contradicts what was seen by hand**, where a renew did *not* recover it. If rung 1 works
now, something differs between the two occasions — say so rather than quietly overwriting item 133.

### Rung 2 worked — `dhcpcd -k` then restart

**Meaning:** `dhcpcd` itself was wedged. It was running, but not doing its job.

**Do next:** this is the most actionable outcome. A watchdog that restarts `dhcpcd` on loss of IPv4
is a real fix and is small. `dhcpcd` here is **6.9.3** (2015-vintage); check its known renewal bugs
before writing anything.

### Rung 3 worked — `wpa_supplicant` restart

**Meaning:** the association was stale in a way that *looked* healthy — `iw` reported it connected
while the link was not passing traffic.

**Do next:** ⚠️ this partially contradicts item 133's headline. Re-check the association evidence in
the log carefully before concluding, and record the contradiction explicitly.

### Nothing worked — `UNRECOVERED`

**Meaning:** consistent with what has been seen by hand — only a reboot clears it. That points below
`dhcpcd` and `wpa_supplicant`, at the driver or the dongle's firmware state.

**Do next, and only now:** ✅ **the spare USB wifi card A/B.** Brendan has a second card. It is the
*last* test rather than the first precisely because a different radio proves nothing if the fault is
DHCP-side — and if you have reached this branch, it is not DHCP-side.

Also worth capturing on this branch: `dmesg` around the failure is already in the log, and driver
resets or USB errors would show there.

### The association was LOST at the transition

**Meaning:** item 133 was wrong, or this is a second, different fault.

**Do next:** stop and re-plan. This is a radio or signal investigation, not a DHCP one, and none of
the above applies.

---

## Regardless of which branch

**Check the timing.** The log's `.. alive` heartbeats give uptime-to-failure. Compare it against
the DHCP lease time. **A match is close to conclusive**; a mismatch rules lease expiry out.

**Check whether it recurs after AP sessions specifically.** Item 131 noted the Launchpad failing to
enumerate after several power cycles, and item 95 — full-load power, never tested with everything
drawing at once — is still open. **If the wifi fault clusters around heavy USB activity, power is a
live candidate and the two open items may be one item.**

---

## Recording it

- **A new session in [plan-tests.md](plan-tests.md)**, items numbered **after the last used
  number** — currently **134**. ⚠️ Numbers are cited bare across documents; **never reuse one.**
- **Update items 81 and 133 in place** rather than adding a third entry that says something
  slightly different. Superseded text is **replaced, not annotated beside its replacement**.
- If it is fixed, [ref-hardware.md](ref-hardware.md) gains the mechanism and the fix;
  [plan-v02.md](plan-v02.md) loses the *wifi fault* section.
- ⚠️ **If it is NOT fixed, say so plainly and leave it open.** A wrong confident answer here costs
  more than an open question — that is exactly how this ran for two phases.

---

## Do not

- **Do not swap the wifi card first.** It is the last test, for the reason above.
- **Do not conclude from a single failure.** One data point cannot distinguish "the lease expired"
  from "dhcpcd wedged once".
- **Do not trust `ssh` as a reachability check** — see the top of this file.
- **Do not leave two watchers running.** `/sdcard/wifi-watch.sh` uses a pidfile for exactly this
  reason; two would run the recovery ladder against each other. ⚠️ And **do not check for it with
  `pgrep -f wifi-watch`** — that matches the ssh command doing the checking, which has already cost
  time once. Use the pidfile, or `ls -l /sdcard/wifi-watch.alive`.
