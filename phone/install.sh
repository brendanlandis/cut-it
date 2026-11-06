#!/bin/bash
# Build the Cut It app and put it on the phone over Wi-Fi. The phone needs to be unlocked. Free signing lasts 7
# days (~/Sites/!reference/apple-personal-team.md).
set -euo pipefail
cd "$(dirname "$0")"
xcodegen generate >/dev/null
xcodebuild -project CutIt.xcodeproj -scheme CutIt -destination 'generic/platform=iOS' -derivedDataPath build \
  -allowProvisioningUpdates -quiet build
id=$(xcrun devicectl list devices 2>/dev/null | awk '/available/ {for (i=1;i<=NF;i++) if ($i ~ /^[0-9A-F-]{36}$/) print $i}' | head -1)
xcrun devicectl device install app --device "$id" "build/Build/Products/Debug-iphoneos/Cut It.app"
xcrun devicectl device process launch --device "$id" net.slownames.cutit
