#!/bin/sh
# Build the patched snes9x libretro core with exec/read/write hooks (see tools/dbg_core.py).
# NOTE: the same steps were done by hand in this session; this script as a whole was not run end to end.
# Needs: apt deb-src enabled, build-essential, dpkg-dev. Output: /opt/snes9x_dbg/snes9x_dbg_libretro.so
set -e
sed -i 's/^Types: deb$/Types: deb deb-src/' /etc/apt/sources.list.d/ubuntu.sources || true
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq dpkg-dev build-essential
mkdir -p /opt/snes9x_build && cd /opt/snes9x_build
apt-get source libretro-snes9x
# apply the repo patch (paths in it are absolute diff roots; -p4 strips them)
cd libretro-snes9x-1.61+dfsg
patch -p4 < "$(dirname "$0")/snes9x_dbg.patch" || patch -p3 < "$(dirname "$0")/snes9x_dbg.patch"
cd libretro && make clean >/dev/null 2>&1 || true && make -j"$(nproc)"
mkdir -p /opt/snes9x_dbg && cp snes9x_libretro.so /opt/snes9x_dbg/snes9x_dbg_libretro.so
echo built /opt/snes9x_dbg/snes9x_dbg_libretro.so
