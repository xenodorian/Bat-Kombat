"""Prove Batman can be drawn in a UMK3 fight without a compressor.

The fighter tiles are compressed in the ROM. They are plain 4bpp once the
fight has uploaded them to video RAM. This script does not decompress anything.

Usage:
  python3 tools/batman_vram_test.py "Ultimate Mortal Kombat 3 (USA).sfc" OUTDIR

What it does:
  1. Boots to a Rain (roster cell 0,0) fight.
  2. Finds WRAM addresses that look like the 544-byte sprite-attribute table.
  3. Reads the tile numbers of on-screen sprites.
  4. For each likely sprite-tile base in VRAM, paints those tiles solid white
     for one frame and saves a PNG. The PNG where Rain turns white is the
     live tile store. That is the place a Batman pose gets written.

Rain stays at cell (0,0): the verified cursor id there is 0x18, Rain.
"""
import os
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
import libretro_harness as h
import umk3_nav as nav

CORE = "/usr/lib/x86_64-linux-gnu/libretro/snes9x_libretro.so"
# Byte offsets tried as the OBJ tile base. $2101 picks one of these in practice.
VRAM_BASES = (0x0000, 0x4000, 0x8000, 0xC000)


def poke(core, kind, addr, data):
    L = core.lib
    L.retro_get_memory_data.restype = h.C.c_void_p
    L.retro_get_memory_data.argtypes = [h.C.c_uint]
    ptr = L.retro_get_memory_data(kind)
    h.C.memmove(ptr + addr, bytes(data), len(data))


def oam_candidates(wram, limit=8):
    found = []
    n = len(wram)
    for addr in range(0, n - 544, 2):
        off = 0
        on = 0
        for i in range(128):
            if wram[addr + 1 + i * 4] >= 0xE0:
                off += 1
            else:
                on += 1
        if off < 40 or not (12 <= on <= 80):
            continue
        found.append((on, addr))
    found.sort(key=lambda t: -t[0])
    # Drop addresses that are just shifted copies of a higher-scoring one.
    kept = []
    for on, addr in found:
        if any(abs(addr - prev) < 544 for _, prev in kept):
            continue
        kept.append((on, addr))
        if len(kept) >= limit:
            break
    return kept


def sprite_tiles(wram, addr):
    """Tile indexes for sprites that are on screen and on the left (P1)."""
    tiles = []
    for i in range(128):
        x = wram[addr + i * 4]
        y = wram[addr + 1 + i * 4]
        tile = wram[addr + 2 + i * 4]
        attr = wram[addr + 3 + i * 4]
        if y >= 0xE0:
            continue
        x |= (wram[addr + 512 + (i >> 2)] >> ((i & 3) * 2) & 1) << 8
        if x > 140:
            continue
        tiles.append(tile | ((attr & 1) << 8))
    return sorted(set(tiles))


def main(rom, outdir):
    os.makedirs(outdir, exist_ok=True)
    core = h.Core(CORE)
    core.load(rom)
    nav.to_fight(core, 0, 0)
    core.save_png(os.path.join(outdir, "fight.png"))
    wram = core.wram()
    cands = oam_candidates(wram)
    print("oam candidates (on-screen sprites, addr):")
    for on, addr in cands:
        tiles = sprite_tiles(wram, addr)
        print("  $%04X  on=%d  left_tiles=%d  first=%s" % (addr, on, len(tiles), tiles[:12]))
    if not cands:
        print("no OAM-shaped buffer; the paint test cannot pick tiles")
        return
    tiles = sprite_tiles(wram, cands[0][1])
    if not tiles:
        print("top candidate has no left-side sprites")
        return
    original = core.vram()
    for base in VRAM_BASES:
        # Repaint every frame so a per-frame upload does not erase the test.
        def paint(base=base):
            for t in tiles:
                off = base + (t & 0x1FF) * 32
                if 0 <= off and off + 32 <= len(original):
                    poke(core, 3, off, b"\xff" * 32)
        for _ in range(3):
            paint()
            core.run(1)
        core.save_png(os.path.join(outdir, "paint_%04X.png" % base))
        # Put the original bytes back, then let one frame settle.
        poke(core, 3, 0, original)
        core.run(2)
        print("wrote paint_%04X.png" % base)
    print("The paint_*.png where Rain's body turns white is the live sprite base.")
    print("Poses to write there are in art/batman_poses.tar.gz (idle = f000_62x89.png).")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
