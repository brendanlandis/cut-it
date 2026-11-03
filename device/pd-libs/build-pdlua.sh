#!/bin/bash
# Builds pdlua 0.12.24 with Lua 5.4.7 compiled in, and lua.org's own `lua`, on the Organelle or
# the Mac, and installs pdlua as <install dir>/pdlua. device/README.md, "Lua and ELSE", says where
# each tarball comes from and when to run this.
#
#   build-pdlua.sh <dir holding the three tarballs> <Pd 0.57's src dir> <install dir>
#
# Organelle: build-pdlua.sh /sdcard/libs-build /sdcard/pd-build/pd-0.57-0/src /sdcard/PdExtraLibs
#            (start it with nohup nice -n 19, ~5 min; it caps its own memory)
# Mac:       build-pdlua.sh <dir> ~/Applications/Pd-0.57-0.app/Contents/Resources/src ~/Library/Pd
#
# One change from upstream: the three lines pdlua prints when it loads go to Pd's -verbose level,
# so Cut It's entry points still load in silence (tools/deploy.sh and the suite read Pd's output).
set -eu
SRC=$1; PDSRC=$2; DEST=$3
B=$SRC/build
stamp() { echo "=== $1 $(date -u +%FT%TZ)"; }

if [ "$(uname)" = Linux ]; then
    # Out of memory, the build is killed first, never the live Pd; a compiler fails at 300 MiB.
    echo 1000 > /proc/self/oom_score_adj
    ulimit -v 307200
    LUATARGET=linux; SHA="sha256sum"
else
    LUATARGET=macosx; SHA="shasum -a 256"
fi

stamp check-sources
cd "$SRC"
$SHA -c - <<'EOF'
9fbf5e28ef86c69858f6d3d34eccc32e911c1a28b4120ff3e84aaa70cfbf1e30  lua-5.4.7.tar.gz
5c39111b3fc4c1c9e56671008955a1730f54a15b95e1f1bd0752b868b929d8e3  lua-v5.4.7-git.tar.gz
7c14cf9cddc7722b33e85dc63862452caef6ed145e1259b6b7694a801ca9d626  pd-lua-0.12.24.tar.gz
EOF

stamp extract
rm -rf "$B"; mkdir -p "$B/luagit"
tar xzf lua-5.4.7.tar.gz -C "$B"
tar xzf pd-lua-0.12.24.tar.gz -C "$B"
tar xzf lua-v5.4.7-git.tar.gz -C "$B/luagit"

# lua.org's interpreter: the Mac's runs the sequencer's Lua tests (test/gate/lua/).
stamp lua
make -C "$B/lua-5.4.7" "$LUATARGET"
"$B/lua-5.4.7/src/lua" -v

# pdlua compiles Lua in from its git submodule, which a GitHub archive leaves empty: the
# lua/lua archive at the same tag fills it.
stamp pdlua-patch
P=$B/pd-lua-0.12.24
rm -rf "$P/lua"; cp -R "$B/luagit/lua-5.4.7" "$P/lua"
sed -e 's/^\( *\)post(pdluaver);/\1logpost(NULL, 4, "%s", pdluaver);/' \
    -e 's/^\( *\)post(compiled);/\1logpost(NULL, 4, "%s", compiled);/' \
    -e 's/^\( *\)post(luaversionStr);/\1logpost(NULL, 4, "%s", luaversionStr);/' \
    "$P/pdlua.c" > "$P/pdlua.c.quiet"
n=$(grep -cE 'logpost\(NULL, 4, "%s", (pdluaver|compiled|luaversionStr)\);' "$P/pdlua.c.quiet" || true)
[ "$n" = 3 ] || { echo "the banner patch matched $n of 3 lines: pdlua.c has changed"; exit 1; }
mv "$P/pdlua.c.quiet" "$P/pdlua.c"

stamp pdlua-make
make -C "$P" PDINCLUDEDIR="$PDSRC" pdlua_version=0.12.24
rm -rf "$DEST/pdlua"
make -C "$P" install PDINCLUDEDIR="$PDSRC" pdlua_version=0.12.24 objectsdir="$DEST"
ls -la "$DEST/pdlua"
stamp done
