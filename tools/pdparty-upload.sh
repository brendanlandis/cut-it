#!/bin/sh
# Put both phone scenes on PdParty, over its WebDAV server: CutItRemote, and
# CutItChecks, the checklist page with its data.
#
#   ./tools/pdparty-upload.sh                  the phone at 192.168.1.9
#   PHONE=192.168.1.20 ./tools/pdparty-upload.sh
#
# PdParty's WebDAV server has to be switched on in the app first, and does not
# survive the app restarting. A PUT into a missing folder is a 409, so every
# folder is made first (an existing one answers 405, which is fine). There is no
# live reload: back out of a scene and reopen it after an upload. Reference,
# PdParty, The WebDAV server and Uploading a scene over WebDAV.

set -eu

PHONE="${PHONE:-192.168.1.9}"
URL="http://$PHONE:9000"
cd "$(dirname "$0")/pdparty-scene"

python3 build-checks.py --check

if ! nc -z -G 3 "$PHONE" 9000 2>/dev/null; then
    echo "PdParty's WebDAV server is not answering at $PHONE:9000." >&2
    echo "Switch it on in PdParty's settings, and check the phone's address." >&2
    exit 1
fi

for dir in CutItRemote CutItChecks CutItChecks/checks; do
    curl -s -o /dev/null -X MKCOL "$URL/$dir/"
done
for f in CutItRemote/_main.pd CutItChecks/_main.pd CutItChecks/checks/*.txt; do
    code=$(curl -s -o /dev/null -w '%{http_code}' -T "$f" "$URL/$f")
    case "$code" in
        2??) echo "  $f" ;;
        *) echo "upload of $f answered $code" >&2; exit 1 ;;
    esac
done
echo "Uploaded. Back out of a scene and reopen it to see the new copy."
