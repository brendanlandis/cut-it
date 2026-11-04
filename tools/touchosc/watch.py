#!/usr/bin/env python3
"""Keep the phone's layout following the code while we work on it (Brendan, 2026-11-04).

    python3 tools/touchosc/watch.py        until Ctrl-C

Three things, each said in a line here and, for the ones he should see at the rig, in a Mac
notification:

- A save of anything the layout is built from (build.py, the line check, the drum page's
  layout) rebuilds it and sends it to the phone through push.sh.
- The phone dropping off TouchOSC's editor connection, and coming back, are told as they happen,
  checked every few seconds: a dropped phone keeps the old layout and says nothing.
- A CutIt.tosc saved from TouchOSC's editor is told with its changes (diff.py), and the watcher
  stops pushing until they are in build.py: build.py refuses to write over them.
"""
import importlib.util
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("build_touchosc", os.path.join(HERE, "build.py"))
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)

SOURCES = [os.path.join(HERE, "build.py"), os.path.join(B.CHECKLISTS, B.LIST + ".md"),
           B.DRUM_PAGE]
POLL, PHONE_EVERY = 0.5, 5.0


def say(line, notify=False):
    print(time.strftime("%H:%M:%S ") + line, flush=True)
    if notify:
        subprocess.run(["osascript", "-e", 'display notification "%s" with title "TouchOSC"'
                        % line.replace('"', "'")], capture_output=True)


def mtimes(paths):
    out = {}
    for p in paths:
        try:
            out[p] = os.stat(p).st_mtime
        except OSError:
            out[p] = None
    return out


def phone_connected():
    r = subprocess.run(["lsof", "-nP", "-iTCP:6666", "-sTCP:ESTABLISHED"], capture_output=True,
                       text=True)
    return any("TouchOSC" in line for line in r.stdout.splitlines()[1:])


def push():
    r = subprocess.run([os.path.join(HERE, "push.sh")], capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip()
    if r.returncode == 0:
        say("pushed: the phone has it")
    elif r.returncode == 3:
        say("built, but the phone is not connected: reconnect it to the Mac's TouchOSC", True)
    elif "saved from TouchOSC's editor" in out:
        editor_saved()
    else:
        say("push failed:\n" + out, True)


def editor_saved():
    r = subprocess.run([sys.executable, os.path.join(HERE, "diff.py")], capture_output=True,
                       text=True)
    lines = r.stdout.strip().splitlines()
    say("CutIt.tosc was saved from the editor, %d change(s); not pushing until they are in "
        "build.py:\n  %s" % (len(lines), "\n  ".join(lines)), True)


def main():
    seen = mtimes(SOURCES)
    tosc = mtimes([B.OUT])
    phone = phone_connected()
    say("watching %s; the phone is %s" % (", ".join(os.path.relpath(p, B.ROOT) for p in SOURCES),
                                         "connected" if phone else "NOT connected"))
    last_phone = time.time()
    while True:
        time.sleep(POLL)
        now = mtimes(SOURCES)
        if now != seen:
            time.sleep(POLL)                   # an editor's save can land in two writes
            seen = mtimes(SOURCES)
            push()
            tosc = mtimes([B.OUT])
            continue
        if mtimes([B.OUT]) != tosc:
            tosc = mtimes([B.OUT])
            if B.saved_from_editor(B.build()):
                editor_saved()
        if time.time() - last_phone >= PHONE_EVERY:
            last_phone = time.time()
            p = phone_connected()
            if p != phone:
                phone = p
                say("the phone is %s" % ("connected again" if p else
                                         "no longer connected: reconnect it to the Mac's TouchOSC"),
                    True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
