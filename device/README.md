# Device configuration backups

Copies of configuration that otherwise **lives only on hardware and has no other backup**.
Nothing here is deployed with the patch — these are restore sources, and a record of what was
changed from factory.

| Here | What |
|---|---|
| [`s2/`](s2/README.md) | The Organelle S2's changes from its factory OS 5.1, and the scripts that set one up |
| `pd-libs/` | How pdlua and ELSE, with the FFmpeg that ELSE's file players read through, are built for Pd 0.57; see *Lua and ELSE* below |
| `korg nano kontrol.nktrl_set` | The nanoKONTROL's 24 control assignments plus the CC 41–46 transport map, for Korg Kontrol Editor **2.4.0**. Korg's own binary format — **not diffable**, so treat it as an opaque blob and re-export after any change |

The Organelle 1, which Cut It ran on until November 2026, was reset to its factory OS for resale on
2026-11-19; its backups and changes are in git history before then.

## Lua and ELSE

**Why:** the sequencer's rules run in Lua inside Pd, through the pdlua external
([ref/module/sequencer.md](../ref/module/sequencer.md)), and ELSE's objects may replace hand-built
parts. The Organelle ships neither, and current builds of both need Pd 0.56 or later, so both are
built on the device against Cut It's 0.57, by `s2/build.sh` ([s2/README.md](s2/README.md), *Setting
one up*). They live in `/sdcard/PdExtraLibs`, which `mother`'s own launch line puts on Pd's path
(`-path /sdcard/PdExtraLibs`), so a patch finds them with no change to `/`.

| On the device | What | Built by |
|---|---|---|
| `/sdcard/PdExtraLibs/pdlua/` | pdlua 0.12.24, Lua 5.4.7 compiled in | `pd-libs/build-pdlua.sh` |
| `/sdcard/PdExtraLibs/else/` | ELSE 1.0-0 rc14: 328 of its 332 externals, its abstractions and help files | `pd-libs/build-else.sh` with `pd-libs/Makefile.else`; its three file readers link FFmpeg 7.0.1 from `pd-libs/build-ffmpeg.sh` |

**Sources:**

| File | From |
|---|---|
| `pd-0.57-0.src.tar.gz` | `msp.ucsd.edu/Software/pd-0.57-0.src.tar.gz` |
| `pd-lua-0.12.24.tar.gz` | `github.com/ben-wes/pd-lua/archive/refs/tags/0.12.24.tar.gz`: a fork, since upstream's 0.12.23 fails on 0.57 |
| `lua-v5.4.7-git.tar.gz` | `github.com/lua/lua/archive/refs/tags/v5.4.7.tar.gz`: pdlua's `lua/` submodule, which a GitHub archive leaves empty |
| `lua-5.4.7.tar.gz` | `www.lua.org/ftp/lua-5.4.7.tar.gz`: the `lua` interpreter, for the Lua tests on the Mac |
| `pd-else-rc14.tar.gz` | `github.com/porres/pd-else/archive/refs/tags/v.1.0-rc14.tar.gz` |
| `ffmpeg-7.0.1.tar.bz2` | Inside `pd-else-rc14.tar.gz`, at `Source/Shared/ffmpeg/`: the version rc14 builds against |

`s2/build.sh` checks the first five with `sha256sum -c` before it builds.

**One change from upstream pdlua:** `build-pdlua.sh` moves the three lines it prints when it loads
to Pd's `-verbose` level. Cut It's entry points must load in silence, since `tools/deploy.sh` and the
suite take any output as a failure, and those lines would be the only output.

**pdlua on its own, not ELSE's copy.** ELSE carries a modified pdlua 0.12.23 inside its `[else]`
library binary, which works, but loading it loads the whole library: ~35 lines of banner at every
load, a GUI plugin installed, and Cut It's Lua tied to ELSE's release candidates. pdlua alone is one
~400 KB binary that loads quietly once the banner moves.

**ELSE's build:** rc14's own needs CMake 3.15 and OpenSSL 3, which the Organelle 1 lacked, so
`Makefile.else` mirrors its `CMakeLists.txt` target by target and gives every external the
`.pd_linux` suffix any Linux Pd loads. It builds under `/sdcard/libs-trial`, the paths both files
name (`T` in the script, the `?=` defaults in the Makefile). Left out: `circuit~`, `pdlink`,
`pdlink~` and `sfz~`, which are C++17; the Organelle 1's gcc 5.2 lacked it, and the S2's gcc 12 has
it, untried.

**FFmpeg, for ELSE's file players:** `play.file~`, `sfload` and `sfinfo` read sound files through
FFmpeg, and `player~`, `gran.player~`, `pvoc.player~` and `sample~` read them through those three.
rc14 builds FFmpeg with encoders, muxers, video, https and OpenSSL 3, but the three only open a local
file, decode its audio and convert it to float, so `build-ffmpeg.sh` configures 7.0.1 for that and
nothing more: libavformat, libavcodec, libavutil and libswresample, static and position-independent;
the file protocol; WAV, AIFF, MP3 and FLAC, the formats of ELSE's own example files; the ARM NEON
assembly, which upstream's build turns off; no programs, network, encoders, muxers, filters or
outside libraries. Each of the three externals carries its own copy, linked with `--exclude-libs` so
FFmpeg's symbols stay inside it (Pd loads every external into one global namespace).

⚠️ **The ELSE build caps its own memory** (`ulimit -v`, `oom_score_adj 1000`), as must anything else
run beside the live Pd: one test Pd ran the Organelle 1 out of memory on 2026-11-03.

**`loadcheck.sh`** loads patches in a second Pd beside the live one, isolated from it and capped, and
prints Pd's output; a clean load of Cut It prints only two lines, from `[shell]`'s load-time scripts
not being in its empty working directory. `LIBS= sh loadcheck.sh …` loads without
`/sdcard/PdExtraLibs`, to compare.

**On the Mac** the same two live in `~/Library/Pd`, on Pd's standard path, so Pd's own window finds
them with no preference set: `~/Library/Pd/pdlua` from `build-pdlua.sh` (Pd source:
`~/Applications/Pd-0.57-0.app/Contents/Resources/src`), and `~/Library/Pd/else` from Deken's rc14 build
for the Mac, `else[v1.0-0_rc14-with_live_electronics_tutorial](Darwin-amd64-32)(…).dek` from
`puredata.info/Members/porres/software/else`, a zip. The same `build-pdlua.sh` leaves lua.org's `lua`
in its `build/lua-5.4.7/src`, copied to `~/.local/bin/lua` for the Lua tests. The suite empties
`HOME`, so every Pd it and `tools/deploy.sh` start gets `-path ~/Library/Pd` from the account's real
home; `CUTIT_PD_LIBS=…` points them at another folder, and `LUA=…` at another interpreter.

**To remove** them from the device: `rm -rf /sdcard/PdExtraLibs/pdlua /sdcard/PdExtraLibs/else`.
Cut It's sequencer then fails to create, and says `fail c_steps no-lua` on the screen and in the log.

## Restoring the nanoKONTROL

`REC + STOP + SCENE` held at power-on performs a factory reset and wipes every assignment. If
that happens, load `korg nano kontrol.nktrl_set` in Kontrol Editor 2.4.0 and write it back.
2.5.0 will not see the device — it dropped first-generation nanoKONTROL support.

The expected result is documented in [ref/device/nanokontrol.md](../ref/device/nanokontrol.md); verify against it after
any restore, ideally by decoding the raw stream rather than trusting the editor.
