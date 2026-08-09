#!/usr/bin/env python3
"""THE VERDICT CHANNEL -- what was judged, when, on what machine, against what code.

Imported by run.py, never run on its own.

WHY IT EXISTS. Until now a bench run left no trace at all. Seven benches and a
hundred-odd steps were judged by a person reading prose, and the answer to "when
did phone step 12 last pass, and against what code?" was nowhere -- not in git,
not on disk, not in anybody's head. A suite whose results evaporate is a suite
that gets re-run from scratch or, more often, not re-run.

⛔ PER-RUN RECORDS ARE GITIGNORED AND THE ROLL-UP IS COMMITTED. The individual
runs are noise -- one file per invocation, most of them partial. latest.json is
the answer to the question above, and it is committed precisely so `git log` can
be asked it.

⛔ APPEND AND FSYNC BEFORE THE NEXT STEP. A bench is a twenty-minute human loop
and the machine it runs on gets closed, unplugged and carried to a venue. Losing
the whole run to a crash at step 19 is how a suite teaches people not to bother;
losing at most the step in flight is survivable.

⚠️ THE FILE IS APPEND-ONLY AND THE LAST RECORD FOR A STEP WINS. That is what
makes [u]ndo and [r]epeat safe without rewriting history mid-run -- a rewrite is
the one operation that could corrupt what has already been fsynced.
"""
import datetime
import hashlib
import json
import os

RUNS = "test/results/runs"
LATEST = "test/results/latest.json"
SCHEMA = 1

# ⚠️ THIRTY DAYS, AND IT IS A JUDGEMENT RATHER THAN A MEASUREMENT. Long enough
# that a bench run survives a normal week of patch work, short enough that a
# verdict from a machine nobody has touched since is not quietly believed.
MAX_AGE_DAYS = 30


def now():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)


def step_sha(title, pass_if):
    """⛔ THE QUESTION THE VERDICT ANSWERED, not the verdict.

    Reword a step and the old pass is worthless -- it answered something else.
    Hashing title and pass_if together is what makes that automatic instead of
    remembered.
    """
    h = hashlib.sha1()
    h.update(title.encode("utf-8"))
    h.update(b"\0")
    h.update(pass_if.encode("utf-8"))
    return h.hexdigest()[:12]


def deps_sha(paths):
    """⛔ PER BENCH, NEVER THE WHOLE TREE.

    Hashing all of "Cut It/" would make every bench stale on every patch commit,
    and a signal that is always red is a signal that gets ignored -- the mirror
    image of a gate that lies. Per-bench, staleness is actionable: "you changed
    u_tempo.pd, so the tempo bench's verdicts no longer apply."

    ⚠️ A MISSING DEPENDENCY IS HASHED AS MISSING, NOT SKIPPED. A path that has
    been renamed away must change the sha -- silently ignoring it would keep
    every verdict fresh across exactly the change most likely to invalidate them.
    """
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
    """⚠️ THE TARGET IS PART OF THE KEY. A verdict from the Mac is not a verdict
    about the rig -- that is the whole reason `mac` exists as a separate target
    rather than as a cheaper way of answering the same question."""
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
        # ⛔ BOTH, AND IN THIS ORDER. flush() only moves it out of Python's
        # buffer; fsync is what puts it on the card.
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

    ⚠️ LAST WRITE WINS PER KEY, which is what makes [u]ndo work: the undone
    verdict stays in the run file as history and is simply overwritten here.
    """
    doc = load_latest()
    doc["schema"] = SCHEMA
    for row in rows:
        if row.get("verdict") == "undone":
            doc["records"].pop(key(row["bench"], row["step"], row["target"]),
                               None)
            continue
        doc["records"][key(row["bench"], row["step"], row["target"])] = row
    os.makedirs(os.path.dirname(LATEST), exist_ok=True)
    with open(LATEST, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, sort_keys=True)
        fh.write("\n")
    return doc


def freshness(doc, bench, step_n, target, sha, dsha):
    """-> (fresh, why_not). All four conditions, and the first failure names itself.

    ⚠️ IT KEYS ON TARGET BUT NOT ON --auto-only. A predicate and a person answer
    the same question about the same machine, so either verdict is fresh for the
    other; the record still carries `auto` because which oracle answered is
    provenance worth keeping even when it does not change validity.
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
