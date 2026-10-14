"""Find where a fighter's live sprite tiles sit in video RAM by filling blocks with solid colour.

Usage: python3 -I tools/vram_blockfill_test.py "Ultimate Mortal Kombat 3 (USA).sfc" OUTDIR
Boots a Rain (roster cell 0,0) vs Reptile fight, then for each 2 KB VRAM block: fill it with 0xFF for one
frame, measure how much of Rain's screen box and Reptile's screen box changed, restore VRAM.
Blocks that change Rain's box but not Reptile's hold Rain's live sprite tiles. Frames with a large Rain change
are saved as blockfill_XXXX.png. Verified result (original ROM): fills at VRAM 0x4000 and 0xA000 visibly delete
pieces of Rain's body, so the tiles are plain 4bpp in VRAM and writable. Rain's tiles are spread over 0x3800-0xFFFF.
"""
import os
import sys
import ctypes as C
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import libretro_harness as h
import umk3_nav as nav

CORE = "/usr/lib/x86_64-linux-gnu/libretro/snes9x_libretro.so"


def main(rom, outdir):
    os.makedirs(outdir, exist_ok=True)
    c = h.Core(CORE)
    c.load(rom)
    nav.to_fight(c, 0, 0)
    c.run(120, [])

    def poke(off, data):
        L = c.lib
        L.retro_get_memory_data.restype = C.c_void_p
        L.retro_get_memory_data.argtypes = [C.c_uint]
        C.memmove(L.retro_get_memory_data(3) + off, bytes(data), len(data))

    orig = c.vram()
    rain = (slice(88, 195), slice(25, 75))
    rept = (slice(88, 195), slice(150, 215))
    print("block vram_off rain_changed reptile_changed")
    for blk in range(32):
        off = blk * 0x800
        poke(off, b"\xff" * 0x800)
        c.run(1, [])
        f = c.frame.copy().astype(int)
        poke(0, orig)
        c.run(4, [])
        nb = c.frame.copy().astype(int)
        d1 = (np.abs(f[rain] - nb[rain]).sum(axis=2) > 90).mean()
        d2 = (np.abs(f[rept] - nb[rept]).sum(axis=2) > 90).mean()
        print("%2d 0x%04X %.2f %.2f" % (blk, off, d1, d2))
        if d1 > 0.15:
            Image.fromarray(f.astype("uint8")).save(os.path.join(outdir, "blockfill_%04X.png" % off))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
