#!/bin/bash
# Run by launchd every 15 minutes (net.slownames.cutit-install.plist). An app signed by a free Apple account stops
# opening after 7 days (~/Sites/!reference/apple-personal-team.md), so once a day, when the phone is on the Mac's
# network and lately unlocked, this builds what's pushed and installs it. An install closes the app, so while the app
# is running on the phone it waits, for up to 5 days. The phone away or locked is the usual state, and says nothing.
set -uo pipefail
cd "$(dirname "$0")"
STATE="$HOME/Library/Application Support/cutit-install"
STAMP="$STATE/last-success"
FAILED="$STATE/last-failure"
LOG="$HOME/Library/Logs/cutit-install.log"
PROFILES="$HOME/Library/Developer/Xcode/UserData/Provisioning Profiles"
mkdir -p "$STATE"
log() { printf '%s %s\n' "$(date '+%F %T')" "$*" >>"$LOG"; }
since() { echo $(( $(date +%s) - $( [[ -f $1 ]] && stat -f %m "$1" || echo 0) )); }

(( $(since "$STAMP") < 72000 )) && exit 0
(( $(since "$FAILED") < 3600 )) && exit 0
id=$(xcrun devicectl list devices 2>/dev/null | awk '/available/ {for (i=1;i<=NF;i++) if ($i ~ /^[0-9A-F-]{36}$/) print $i}' | head -1)
[[ -n $id ]] || exit 0
procs=$(xcrun devicectl device info processes --device "$id" 2>/dev/null) || exit 0
if grep -q 'Cut It.app' <<<"$procs" && (( $(since "$STAMP") < 5 * 86400 )); then
  log "waiting: the app is running"
  exit 0
fi

# A new profile, good for 7 days: Xcode keeps a cached one until it has expired.
for f in "$PROFILES"/*.mobileprovision; do
  [[ -f $f ]] || continue
  security cms -D -i "$f" 2>/dev/null | plutil -extract Entitlements.application-identifier raw -o - - 2>/dev/null \
    | grep -q '\.net\.slownames\.cutit$' || continue
  log "renewing the profile $f"
  rm -f "$f"
done

# What's pushed, exported clean, never the working tree.
tmp=$(mktemp -d -t cutit-install)
trap '/bin/rm -rf "$tmp"' EXIT
git -C .. fetch -q origin 2>/dev/null
git -C .. archive origin/master phone | tar -x -C "$tmp"
if (cd "$tmp/phone" && xcodegen generate >/dev/null && xcodebuild -project CutIt.xcodeproj -scheme CutIt \
      -destination 'generic/platform=iOS' -derivedDataPath build -allowProvisioningUpdates -quiet build) >>"$LOG" 2>&1 \
   && xcrun devicectl device install app --device "$id" "$tmp/phone/build/Build/Products/Debug-iphoneos/Cut It.app" >>"$LOG" 2>&1; then
  touch "$STAMP"
  log "installed $(git -C .. log -1 --format='%h %s' origin/master)"
else
  touch "$FAILED"
  log "failed: see above"
fi
