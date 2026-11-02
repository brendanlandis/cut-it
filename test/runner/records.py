#!/usr/bin/env python3
"""The verdict channel: what was judged, when, on what machine, against what
code. Imported by run.py.

Per-run records are gitignored; the roll-up, latest.json, is committed, so
`git log` can say when a step last passed and against what code.

Each record is appended and fsynced before the next step is described: a bench
is a long loop by hand on a machine that gets closed and carried, and a crash
should cost at most the step in flight. The last record for a step wins, so a
repeat never rewrites what is already on disk.
"""
import datetime
import hashlib
import json
import os

# Redirectable so a fixture never writes the committed roll-up: latest.json is
# what hardware did, and paper mode is a normal run that rolls up. An env var
# rather than a flag, so "do not record" is no option a bench run offers.
RESULTS = os.environ.get("CUTIT_RESULTS", "test/results")
RUNS = os.path.join(RESULTS, "runs")
LATEST = os.path.join(RESULTS, "latest.json")
SCHEMA = 1

# A judgment, not a measurement: a week of patch work survives it, a verdict
# from a machine untouched for a month does not.
MAX_AGE_DAYS = 30


def now():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)


def step_sha(title, pass_if):
    """The question the verdict answered, not the verdict: reword a step and
    its old pass no longer applies."""
    h = hashlib.sha1()
    h.update(title.encode("utf-8"))
    h.update(b"\0")
    h.update(pass_if.encode("utf-8"))
    return h.hexdigest()[:12]


def deps_sha(paths):
    """Per bench, never the whole tree, or every patch commit would stale every
    bench. A missing dependency hashes as missing, so renaming one away stales
    the verdicts that rest on it."""
    h = hashlib.sha1()
    for p in sorted(paths):
        h.update(p.encode("utf-8"))
        h.update(b"\0")
        try:
            with open(p, "rb") as fh:
                h.update(fh.read())
        except OSError:
            h.update(b"<missing>")
        h.update(b"\0")
    return h.hexdigest()[:12]


def key(bench, step, target):
    """The target is part of the key: a verdict from the Mac is not one about
    the rig."""
    return "%s/%d/%s" % (bench, step, target)


class Recorder(object):
    """One run's worth of records, on disk before the next step is described."""

    def __init__(self, bench, target, auto_only):
        os.makedirs(RUNS, exist_ok=True)
        self.run_id = "%s-%s-%s" % (now().strftime("%Y%m%dT%H%M%SZ"),
                                    bench, target)
        self.path = os.path.join(RUNS, self.run_id + ".jsonl")
        self.bench, self.target, self.auto_only = bench, target, auto_only
        self.rows = []
        self._fh = open(self.path, "a", encoding="utf-8")

    def append(self, row):
        row = dict(row, run=self.run_id, ts=now().isoformat(),
                   target=self.target)
        self.rows.append(row)
        self._fh.write(json.dumps(row, sort_keys=True) + "\n")
        # Both, in this order: flush() empties Python's buffer, fsync puts it
        # on the card.
        self._fh.flush()
        os.fsync(self._fh.fileno())
        return row

    def close(self):
        self._fh.close()


def load_latest():
    try:
        with open(LATEST, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {"schema": SCHEMA, "records": {}}


def roll_up(rows):
    """Merge this run's records into the committed latest.json.

    Last write wins per key, with no merge policy, so a row carrying no verdict
    destroys a real one. run.py writes a row only when something was learned:
    see `ran` in run_bench_driven.
    """
    doc = load_latest()
    doc["schema"] = SCHEMA
    for row in rows:
        doc["records"][key(row["bench"], row["step"], row["target"])] = row
    os.makedirs(os.path.dirname(LATEST), exist_ok=True)
    with open(LATEST, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, sort_keys=True)
        fh.write("\n")
    return doc


def freshness(doc, bench, step_n, target, sha, dsha):
    """-> (fresh, why_not), the first failed condition naming itself.

    Keyed on target but not on --auto-only: a predicate and a person answer the
    same question about the same machine, so either verdict is fresh for the
    other. `auto` stays in the record as provenance.
    """
    row = doc.get("records", {}).get(key(bench, step_n, target))
    if row is None:
        return False, "never run"
    if row.get("verdict") != "pass":
        return False, "last verdict was %s" % row.get("verdict")
    if row.get("sha") != sha:
        return False, "the step was reworded since"
    if row.get("deps_sha") != dsha:
        return False, "the patch it depends on has changed since"
    try:
        when = datetime.datetime.fromisoformat(row["ts"])
    except (KeyError, ValueError):
        return False, "no usable timestamp"
    age = (now() - when).days
    if age > MAX_AGE_DAYS:
        return False, "last passed %d days ago" % age
    return True, ""
