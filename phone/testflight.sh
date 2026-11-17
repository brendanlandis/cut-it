#!/bin/bash
#
# testflight.sh: sends the phone app to TestFlight, as super-boring's bin/testflight sends its own
# (2026-11-15, !projects' cut-it/phone-through-testflight), where the TestFlight app on the phone,
# with Automatic Updates on, installs it by itself.
#
# It builds a commit's phone/, exported clean, never the working tree: HEAD once it's pushed, or
# the one given. Archived for the App Store, signed by the paid team (Xcode's own sign-in,
# -allowProvisioningUpdates), numbered by the commits behind it, which only go up, as TestFlight
# needs; then uploaded to App Store Connect with the team's API key, by altool, since Xcode's
# sign-in is refused there (found with Sundries, 2026-11-10). The key's private half is
# ~/.appstoreconnect/private_keys/AuthKey_<ID>.p8, where Apple's tools look for it, and in
# 1Password (headless vault, "App Store Connect API key"): it runs on the MacBook, which has both.
#
#   phone/testflight.sh            HEAD, once it's pushed
#   phone/testflight.sh COMMIT     that commit
#   phone/testflight.sh --dry-run  archived and exported as the App Store takes it, and put to
#                                  Apple's own check; nothing uploaded
#
# Its log: ~/Library/Logs/cutit-testflight.log.

set -euo pipefail
cd "$(dirname "$0")/.."

DRY=""
REV=HEAD
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY=1 ;;
    -*) echo "usage: phone/testflight.sh [COMMIT] [--dry-run]" >&2; exit 2 ;;
    *) REV="$arg" ;;
  esac
done
COMMIT=$(git rev-parse --verify --quiet "$REV^{commit}") || { echo "no commit $REV" >&2; exit 2; }
if [[ ! $DRY ]] && ! git merge-base --is-ancestor "$COMMIT" origin/master 2>/dev/null; then
  echo "$(git rev-parse --short "$COMMIT") isn't pushed: push it first, or try it with --dry-run" >&2
  exit 1
fi
BUILD=$(git rev-list --count "$COMMIT")
# The team's App Store Connect API key, "sundries upload", App Manager (2026-11-10): its id and
# its issuer's, which aren't secret; the .p8 is.
KEY_ID=FK35VDRYTG
ISSUER=745d05fd-d8b0-42cf-94ff-5837cb818aef
KEY="$HOME/.appstoreconnect/private_keys/AuthKey_$KEY_ID.p8"
[[ -r $KEY ]] || { echo "no App Store Connect key at $KEY (1Password's headless vault has it, \"App Store Connect API key\")" >&2; exit 1; }
LOG="$HOME/Library/Logs/cutit-testflight.log"

# The commit's phone/ in a folder of its own, outside the repo, made exactly those files as a
# checkout is: one unchanged since the last run keeps its time, so Xcode's derived data, kept
# beside them, rebuilds only what changed.
EXPORT="$HOME/Library/Caches/com.velellalabs.cutit/testflight"
mkdir -p "$EXPORT"
GIT_INDEX_FILE="$EXPORT.index" git --work-tree="$EXPORT" read-tree --reset -u "$COMMIT:phone"
echo "$(date '+%Y-%m-%d %H:%M:%S') building $BUILD ($(git log -1 --format='%h %s' "$COMMIT"))" | tee -a "$LOG"

(cd "$EXPORT" && xcodegen generate --quiet) >>"$LOG" 2>&1 || { echo "xcodegen failed (see $LOG)" >&2; exit 1; }
# Xcode's packaging runs /usr/bin/rsync, which hands off to whatever rsync is first on the PATH:
# Homebrew's refuses one of its options, and the export fails as "Copy failed". So xcodebuild
# runs with the system's own tools only.
xcodebuild() { env PATH=/usr/bin:/bin:/usr/sbin:/sbin /usr/bin/xcodebuild "$@"; }
rm -rf "$EXPORT/CutIt.xcarchive" "$EXPORT/out"
xcodebuild -project "$EXPORT/CutIt.xcodeproj" -scheme CutIt -configuration Release \
  -destination generic/platform=iOS -archivePath "$EXPORT/CutIt.xcarchive" -derivedDataPath "$EXPORT/build" \
  -allowProvisioningUpdates CURRENT_PROJECT_VERSION="$BUILD" archive >>"$LOG" 2>&1 \
  || { echo "the archive failed (see $LOG)" >&2; exit 1; }

cat >"$EXPORT/ExportOptions.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>method</key><string>app-store-connect</string>
	<key>destination</key><string>export</string>
	<key>teamID</key><string>6B24ZAPCS2</string>
	<key>signingStyle</key><string>automatic</string>
	<key>manageAppVersionAndBuildNumber</key><false/>
	<key>uploadSymbols</key><true/>
</dict>
</plist>
EOF
xcodebuild -exportArchive -archivePath "$EXPORT/CutIt.xcarchive" -exportOptionsPlist "$EXPORT/ExportOptions.plist" \
  -exportPath "$EXPORT/out" -allowProvisioningUpdates >>"$LOG" 2>&1 \
  || { echo "the export failed (see $LOG)" >&2; exit 1; }
IPA="$EXPORT/out/Cut It.ipa"
[[ -f $IPA ]] || { echo "the export made no $IPA (see $LOG)" >&2; exit 1; }
if [[ $DRY ]]; then
  # Apple's own check of the package, which uploads nothing: what an upload would be refused for.
  if xcrun altool --validate-app -f "$IPA" -t ios --apiKey "$KEY_ID" --apiIssuer "$ISSUER" >>"$LOG" 2>&1; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') exported $IPA, build $BUILD, and Apple's check passes it; nothing uploaded" | tee -a "$LOG"
  else
    echo "$(date '+%Y-%m-%d %H:%M:%S') exported $IPA, build $BUILD, but Apple's check refuses it (see $LOG); nothing uploaded" | tee -a "$LOG" >&2
    exit 1
  fi
else
  xcrun altool --upload-app -f "$IPA" -t ios --apiKey "$KEY_ID" --apiIssuer "$ISSUER" >>"$LOG" 2>&1 \
    || { echo "the upload failed (see $LOG)" >&2; exit 1; }
  echo "$(date '+%Y-%m-%d %H:%M:%S') uploaded build $BUILD to TestFlight; it's on the phone once App Store Connect has processed it" | tee -a "$LOG"
fi
