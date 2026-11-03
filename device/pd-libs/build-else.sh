#!/bin/bash
# Builds ELSE rc14 for Pd 0.57 under /sdcard/libs-trial, nowhere else; logs each phase with its time.
# Start it as: nohup nice -n 19 ionice -c3 bash build-else.sh > build.log 2>&1 &
set -u
T=/sdcard/libs-trial; BD=$T/build; O=$T/else
S=$BD/pd-else-v.1.0-rc14; FF=$BD/ffmpeg-7.0.1
MK="make -k -f $BD/Makefile.else"
echo 1000 > /proc/self/oom_score_adj   # out of memory, the build is killed first, never the live Pd
ulimit -v 307200                        # and a compiler fails at 300 MiB before it gets there
stamp() { echo "=== $1 $(date -u +%FT%TZ) up=$(cut -d' ' -f1 /proc/uptime)"; }
cd $BD || exit 1
stamp start
[ -d "$S" ] || { stamp extract; tar xzf pd-else-rc14.tar.gz || { stamp FAILED-extract; exit 1; }; }
mkdir -p $O

stamp make-c;   $MK c;   echo "make-c rc=$?"
stamp make-cpp; $MK cpp; echo "make-cpp rc=$?"

# FFmpeg as Source/Shared/ffmpeg/build_ffmpeg.sh configures it on Linux, less --enable-openssl
# (upstream wants OpenSSL 3, for https; the device has 1.0.2, and local files need none)
if [ ! -f $FF/libavutil/libavutil.a ]; then
  stamp ffmpeg-extract
  [ -d $FF ] || tar xjf $S/Source/Shared/ffmpeg/ffmpeg-7.0.1.tar.bz2 -C $BD
  rm -f $FF/VERSION
  cd $FF
  stamp ffmpeg-configure
  ./configure --disable-asm --disable-libxcb --disable-bzlib --disable-lzma --disable-sdl2 --disable-libdrm --disable-vaapi --enable-static --disable-shared --enable-optimizations --disable-debug \
            --disable-programs --disable-iconv --disable-avdevice --disable-postproc \
            --disable-everything --enable-avcodec --enable-avformat --enable-avutil \
            --enable-encoder=vorbis,flac,mp3,mpeg4,aac,alac,pcm_mulaw,pcm_alaw \
            --enable-decoder=mp3*,pcm*,aac*,flac,vorbis,opus,alac,mulaw,alaw,aac,h264 \
            --enable-decoder=mpeg4,mpeg1video,mpeg2video \
            --enable-decoder=mjpeg  \
            --enable-muxer=ogg,flac,mp3,mp4,avi,mov,flv,asf,caf,au \
            --enable-demuxer=mp3,wav,aiff,flac,aac,ogg,pcm*,caf,au \
            --enable-demuxer=avi,mov,mp3,flv,asf \
            --enable-filter=aresample --enable-protocol=file \
            --enable-parser=mpegaudio,aac,mpeg4video \
            --enable-network --enable-protocol=http,https \
            --enable-swresample \
            --enable-pic \
    || stamp FAILED-ffmpeg-configure
  stamp ffmpeg-make
  make || stamp FAILED-ffmpeg-make
  cd $BD
fi
stamp make-ff; $MK ffobjs; echo "make-ff rc=$?"

# gcc 5.2 and C++17, which sfizz (sfz~) requires
stamp cxx17-probe
printf '#include <string_view>\n#include <optional>\nint main(){std::optional<int> o; std::string_view s; return 0;}\n' > $BD/cxx17.cpp
g++ -std=c++17 -fsyntax-only $BD/cxx17.cpp
g++ -std=c++1z -fsyntax-only $BD/cxx17.cpp

# Resources, as upstream's file(COPY ...) lines, less the tutorial and the PDF
stamp resources
cp $S/Abstractions/Audio/*.pd $S/Abstractions/Control/*.pd $O/
cp -r $S/Abstractions/Extra/. $O/
cp -r $S/Abstractions/Merda/Modules/. $O/
cp -r $S/Documentation/Help-files/. $O/
cp -r $S/Documentation/Extra-files/. $O/ && cp $S/Documentation/Extra-files/audio/* $O/ && rm -rf $O/audio
cp $S/Source/Extra/*.tcl $O/; cp -r $S/Source/Extra/tkdnd $O/ 2>/dev/null
cp "$S/Source/Audio/scope3d~.pd_lua" $S/Source/Control/lua/pd.lua $S/Source/Control/lua/pdx.lua $S/Source/Control/lua/luadoc/hello.lua $S/Source/Control/lua/luadoc/hello.pd_lua $O/
cp -r "$S/Source/Audio/sfz~/sfz" $O/
cp -r $S/LICENSE $O/LICENSE

stamp summary
echo "built: $(ls $O/*.pd_linux | wc -l) externals, plus $(ls $O/*.so 2>/dev/null | wc -l) shared lib(s)"
$MK -s expected | while read n; do [ -f "$O/$n.pd_linux" ] || echo "MISSING $n"; done
du -sh $O
stamp done
