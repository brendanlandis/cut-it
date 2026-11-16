#!/bin/bash
# Run by launchd every hour (net.slownames.cutit-testflight.plist): when what's pushed to master has changed the app
# since the last upload, testflight.sh sends it to TestFlight, whose app on the phone installs it by itself. It took
# over from a daily install over Wi-Fi, 2026-11-16 (!projects' cut-it/phone-through-testflight).
set -uo pipefail
cd "$(dirname "$0")/.."
STATE="$HOME/Library/Application Support/cutit-testflight"
LAST="$STATE/last-upload"
FAILED="$STATE/last-failure"
LOG="$HOME/Library/Logs/cutit-testflight.log"
mkdir -p "$STATE"
since() { echo $(( $(date +%s) - $( [[ -f $1 ]] && stat -f %m "$1" || echo 0) )); }

# After a failure, the next try waits six hours; its reason is in the log.
(( $(since "$FAILED") < 21600 )) && exit 0
git fetch -q origin 2>/dev/null || exit 0
head=$(git rev-parse origin/master)
last=$(cat "$LAST" 2>/dev/null)
[[ $last == "$head" ]] && exit 0
# The app is its sources and project.yml: a commit that changes neither (the scripts, the rest of the repo) isn't one.
if [[ -n $last ]] && git cat-file -e "$last^{commit}" 2>/dev/null \
   && git diff --quiet "$last" "$head" -- phone/CutIt phone/project.yml; then
  echo "$head" >"$LAST"
  exit 0
fi
if phone/testflight.sh "$head" >/dev/null 2>>"$LOG"; then
  echo "$head" >"$LAST"
else
  touch "$FAILED"
fi
