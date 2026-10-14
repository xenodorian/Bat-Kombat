"""Render Batman's sprite tiles from Batman Returns video memory (the step that should have come first).

Usage: python3 -I dump_br_sprites.py BATMAN_RETURNS.sfc OUT_PNG
Boots the game to Stage 1, dumps VRAM and work RAM, finds Batman's sprite palette
(WRAM 0x3300, 16 words) and draws VRAM bytes 0xC000-0xCFFF as 16-tile-wide 4bpp tiles at 4x.
These are the tile PIECES for the current pose. Frames are assembled from them using the
sprite attribute table, which this script does not read yet.
"""
import struct
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import libretro_harness as h
import br_gameplay as g
from tilesheet import decode_4bpp_tile
from PIL import Image

CORE = "/usr/lib/x86_64-linux-gnu/libretro/snes9x_libretro.so"


def main(rom, out):
    c = h.Core(CORE)
    c.load(rom)
    g.boot_to_gameplay(c)
    v, w = c.vram(), c.wram()
    pal = [((x & 31) * 255 // 31, ((x >> 5) & 31) * 255 // 31, ((x >> 10) & 31) * 255 // 31)
           for x in struct.unpack_from("<16H", w, 0x3300)]
    cols, ntiles, scale = 16, 128, 4
    img = Image.new("RGB", (cols * 8 * scale, ntiles // cols * 8 * scale), (60, 60, 60))
    for t in range(ntiles):
        px = decode_4bpp_tile(v, 0xC000 + t * 32)
        tx, ty = (t % cols) * 8 * scale, (t // cols) * 8 * scale
        for r in range(8):
            for cc in range(8):
                if px[r][cc]:
                    for dy in range(scale):
                        for dx in range(scale):
                            img.putpixel((tx + cc * scale + dx, ty + r * scale + dy), pal[px[r][cc]])
    img.save(out)
    print("wrote", out)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
