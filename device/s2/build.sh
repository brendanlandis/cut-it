#!/bin/bash
# Builds what Cut It needs beyond the Organelle S2's factory OS 5.1: Pd 0.57 at /sdcard/pd-0.57-0,
# pdlua and ELSE in /sdcard/PdExtraLibs. The same sources and scripts as the Organelle 1's
# (device/pd-libs, device/README.md "Lua and ELSE"), compiled for the S2's Cortex-A72 with NEON
# rather than Raspbian's ARMv6 default, on all four cores.
#
# On the S2, with /sdcard/build-s2 holding the five tarballs device/README.md lists and
# device/pd-libs' files (tools/s2-build.sh puts them there and starts this):
#
#   nohup bash /sdcard/build-s2/build.sh > /sdcard/build-s2/build.log 2>&1 &
set -eu
K=/sdcard/build-s2
stamp() { echo "=== $1 $(date -u +%FT%TZ) $(cat /sys/class/thermal/thermal_zone0/temp)"; }
export MAKEFLAGS=-j4
A72="-mcpu=cortex-a72 -mfpu=neon-fp-armv8 -mfloat-abi=hard"

stamp check-sources
cd $K
sha256sum -c - <<'EOF'
269c36c968194785c32ac784e004ec9a175c67b8bd692880eaa157131e5978c0  pd-0.57-0.src.tar.gz
ad725a4bc9a50a1b9071cf2f97a30b29910ac22ee5fbc92db999d5fcaaaffd91  pd-else-rc14.tar.gz
9fbf5e28ef86c69858f6d3d34eccc32e911c1a28b4120ff3e84aaa70cfbf1e30  lua-5.4.7.tar.gz
5c39111b3fc4c1c9e56671008955a1730f54a15b95e1f1bd0752b868b929d8e3  lua-v5.4.7-git.tar.gz
7c14cf9cddc7722b33e85dc63862452caef6ed145e1259b6b7694a801ca9d626  pd-lua-0.12.24.tar.gz
EOF

# Pd, in the tree the libs build against (Makefile.else's PDSRC)
stamp pd
mkdir -p /sdcard/pd-build
rm -rf /sdcard/pd-build/pd-0.57-0
tar xzf $K/pd-0.57-0.src.tar.gz -C /sdcard/pd-build
cd /sdcard/pd-build/pd-0.57-0
./autogen.sh
./configure --prefix=/sdcard/pd-0.57-0 --disable-jack CFLAGS="-O3 $A72"
make
rm -rf /sdcard/pd-0.57-0
make install
/sdcard/pd-0.57-0/bin/pd -version

# pdlua, quiet at load (build-pdlua.sh's one change from upstream)
stamp pdlua
mkdir -p /sdcard/PdExtraLibs
bash $K/build-pdlua.sh $K /sdcard/pd-build/pd-0.57-0/src /sdcard/PdExtraLibs

# ELSE and the FFmpeg its file players read through, where build-else.sh builds them
stamp else
mkdir -p /sdcard/libs-trial/build
cp $K/Makefile.else $K/build-else.sh $K/build-ffmpeg.sh $K/pd-else-rc14.tar.gz /sdcard/libs-trial/build/
ARCH="$A72" FF_CPU=cortex-a72 FF_CFLAGS="-mfpu=neon-fp-armv8" bash /sdcard/libs-trial/build/build-else.sh
rm -rf /sdcard/PdExtraLibs/else
cp -a /sdcard/libs-trial/else /sdcard/PdExtraLibs/else

stamp done
