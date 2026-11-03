#!/bin/bash
# FFmpeg 7.0.1, the version ELSE rc14 carries, built on the Organelle 1 as small as ELSE's three
# file readers need: play.file~, sfload and sfinfo open a local file, decode its audio and convert
# it to float, and write nothing. So: libavformat, libavcodec, libavutil and libswresample, static
# and position-independent for linking into Pd externals; the file protocol; WAV, AIFF, MP3 and
# FLAC (the formats of ELSE's own example files); no programs, network, encoders, muxers or
# filters, and no external libraries (zlib, OpenSSL and the rest).
#
#   nohup nice -n 19 ionice -c3 bash build-ffmpeg.sh [build dir] > build-ffmpeg.log 2>&1 &
#
# The build dir holds the unpacked ELSE source (pd-else-v.1.0-rc14), whose tarball of FFmpeg this
# unpacks beside it; the libraries stay in the tree (ffmpeg-7.0.1/lib*/lib*.a), where
# Makefile.else's `ffobjs` target links them. Logs each phase with its time.
set -u
BD=${1:-/sdcard/libs-trial/build}
S=$BD/pd-else-v.1.0-rc14; FF=$BD/ffmpeg-7.0.1
echo 1000 > /proc/self/oom_score_adj   # out of memory, the build is killed first, never the live Pd
ulimit -v 307200                        # and a compiler fails at 300 MiB before it gets there
set -m                                  # each step in its own process group, for the guard
stamp() { echo "=== $1 $(date -u +%FT%TZ) up=$(cut -d' ' -f1 /proc/uptime)"; }

# Runs a step in its own process group and pauses it at 80 C, resuming at 74 C, so the SoC never
# nears its 83 C throttle point beside the live instrument; logs the temperature each minute.
step() {
  "$@" & local g=$! paused=0 n=0 t
  while kill -0 -$g 2>/dev/null; do
    t=$(cat /sys/class/thermal/thermal_zone0/temp)
    if [ $paused = 0 ] && [ $t -ge 80000 ]; then kill -STOP -$g; paused=1; echo "thermal $t pause"; fi
    if [ $paused = 1 ] && [ $t -le 74000 ]; then kill -CONT -$g; paused=0; echo "thermal $t resume"; fi
    [ $((n % 6)) = 0 ] && echo "thermal $(date -u +%T) $t"
    n=$((n + 1)); sleep 10
  done
  wait $g
}

stamp start
cd $BD || exit 1
if [ ! -d $FF ]; then
  stamp extract
  tar xjf $S/Source/Shared/ffmpeg/ffmpeg-7.0.1.tar.bz2 -C $BD || { stamp FAILED-extract; exit 1; }
fi
rm -f $FF/VERSION       # as upstream: a file named VERSION shadows C++'s <version> on some systems
cd $FF || exit 1

stamp configure
step ./configure \
    --disable-everything --disable-autodetect --disable-iconv \
    --disable-programs --disable-doc --disable-network \
    --disable-avdevice --disable-avfilter --disable-swscale --disable-postproc \
    --enable-static --disable-shared --enable-pic --disable-debug \
    --cpu=cortex-a9 --extra-cflags=-mfpu=neon \
    --enable-protocol=file \
    --enable-demuxer=wav,aiff,mp3,flac \
    --enable-parser=mpegaudio,flac \
    --enable-decoder='pcm*,mp3float,flac' \
  || { stamp FAILED-configure; tail -40 ffbuild/config.log; exit 1; }
grep -E '^(ARCH|HAVE_NEON|EXTRALIBS)' ffbuild/config.mak
echo "to compile: $(make -n 2>/dev/null | grep -c -- ' -c -o ')"

stamp make
step make || { stamp FAILED-make; exit 1; }
ls -l libavformat/libavformat.a libavcodec/libavcodec.a libswresample/libswresample.a libavutil/libavutil.a
stamp done
