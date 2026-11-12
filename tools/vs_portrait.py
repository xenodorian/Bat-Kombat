"""Batman's large portrait on the VS screen of UMK3 (USA, SNES).

Format (from the loader at $83:E6D5 and a decode of Rain's portrait):
  * Per-fighter tables in bank $83, indexed by fighter id * 2:
      $EEFA graphics address   $EF2E tile map address   $EF62 palette address   $EEC6 bank of all three
      $EE92 tile count         $EFE6 first byte of the palette that the mirror-match palette replaces
  * Graphics and map are compressed (decompressor $88:AD30, source [$7A], destination [$76]).
    Graphics: 48-byte tiles = SNES 8bpp tiles without the last two bitplanes (6 bits, 64 colours).
    Map: 32 x 32 words, the portrait is the top-left 16 x 22 cells (128 x 176 pixels), word = $4000 | tile
    ($4000 = horizontal flip, so each tile is stored mirrored; checked on screen).
    The last tile is blank and fills the empty cells.
  * Palette: 64 colours raw (index 0 transparent), followed by 64 colours for a mirror match.
  * All male ninjas share one picture and differ in palette only.

No compressor is needed: the three calls to the decompressor are redirected to a small routine that copies
raw data when the source bank is the bank holding Batman's data, and calls the decompressor otherwise.
The picture is the upper body of a Batman pose, enlarged, since Batman Returns has no large portrait.
"""
import struct

import numpy as np
from PIL import Image

import exhirom
from move_list_patch import Asm

T_GFX, T_MAP, T_PAL, T_BANK, T_COUNT, T_MIRROR = 0x03EEFA, 0x03EF2E, 0x03EF62, 0x03EEC6, 0x03EE92, 0x03EFE6
CALL_SITES = (0x03E754, 0x03E77E, 0x03E822)          # jsl $88AD30
CODE_AT = 0x3FE400                                   # $FF:E400, 0xFF padding in the original
FIGHTER = 24
COLS, ROWS = 16, 22
MAX_TILES = 245                                      # the tile count of the ninja portrait it replaces
POSE, CROP = 0, (8, 0, 54, 60)                       # upper body of the standing pose (left, top, right, bottom)


def picture(rgba):
    """Enlarged upper body, RGBA, at most 128 x 176, bottom centred on the canvas."""
    src = Image.fromarray(rgba).crop(CROP)
    canvas = None
    for width in range(COLS * 8, 80, -4):
        scale = width / src.width
        im = src.resize((width, min(ROWS * 8, int(round(src.height * scale)))), Image.LANCZOS)
        a = np.array(im)
        a[:, :, 3] = np.where(a[:, :, 3] > 110, 255, 0)
        canvas = np.zeros((ROWS * 8, COLS * 8, 4), np.uint8)
        x0 = (COLS * 8 - a.shape[1]) // 2 // 8 * 8
        canvas[ROWS * 8 - a.shape[0]:, x0:x0 + a.shape[1]] = a
        yield canvas


def quantize(canvas):
    """RGBA -> (index image with 0 transparent, 64 RGB colours)."""
    op = canvas[:, :, 3] > 0
    rgb = Image.fromarray(canvas[:, :, :3])
    q = rgb.quantize(63, method=Image.MEDIANCUT, dither=Image.NONE)
    pal = q.getpalette()[:63 * 3]
    idx = np.array(q).astype(np.uint8) + 1
    idx[~op] = 0
    colours = [(0, 0, 0)] + [tuple(pal[i:i + 3]) for i in range(0, 63 * 3, 3)]
    return idx, colours


def tile48(px):
    out = bytearray(48)
    for r in range(8):
        for c in range(8):
            v = int(px[r, c])
            for plane in range(6):
                if v >> plane & 1:
                    out[16 * (plane // 2) + 2 * r + (plane & 1)] |= 0x01 << c     # stored mirrored; the map word's $4000 flips it back
    return bytes(out)


def encode(idx):
    tiles, index, cells = [], {}, []
    for r in range(ROWS):
        for c in range(COLS):
            t = tile48(idx[r * 8:r * 8 + 8, c * 8:c * 8 + 8])
            if not any(t):
                cells.append(None)
                continue
            if t not in index:
                index[t] = len(tiles)
                tiles.append(t)
            cells.append(index[t])
    blank = len(tiles)
    tiles.append(bytes(48))
    words = [0x4000 | blank] * (32 * 32)
    for i, n in enumerate(cells):
        if n is not None:
            words[(i // COLS) * 32 + i % COLS] = 0x4000 | n
    return tiles, struct.pack("<1024H", *words)


def snes(c):
    return (c[2] >> 3) << 10 | (c[1] >> 3) << 5 | (c[0] >> 3)


def loader(base, bank):
    a = Asm(base)
    a.b(0xA5, 0x7C, 0x29, 0xFF, 0x00, 0xC9, bank, 0x00)     # lda $7C / and #$FF / cmp #bank
    a.branch(0xF0, "raw")
    a.jml(0x88AD30)
    a.label("raw")
    a.b(0xA7, 0x7A, 0xAA, 0xA0, 0x02, 0x00)                 # lda [$7A] / tax / ldy #2  (word count first)
    a.label("loop")
    a.b(0xB7, 0x7A, 0x88, 0x88, 0x97, 0x76)                 # lda [$7A],y / dey / dey / sta [$76],y
    a.b(0xC8, 0xC8, 0xC8, 0xC8, 0xCA)                       # iny x4 / dex
    a.branch(0xD0, "loop")
    a.b(0x6B)
    return a.done()


def build(rom, alloc, put, poses_rgba, preview=None):
    """rom: the expanded image. Writes Batman's portrait data, the loader, and the table entries of fighter 24."""
    for canvas in picture(poses_rgba[POSE]):
        idx, colours = quantize(canvas)
        tiles, tilemap = encode(idx)
        if len(tiles) <= MAX_TILES:
            break
    else:
        raise ValueError("portrait does not fit in %d tiles" % MAX_TILES)
    gfx = b"".join(tiles)
    pal = struct.pack("<64H", *(snes(c) for c in colours))
    alt = struct.pack("<64H", *(snes((min(255, c[0] + 40), min(255, c[1] + 24), c[2])) for c in colours))   # mirror match: warmer
    blob = struct.pack("<H", len(gfx) // 2) + gfx
    map_at = len(blob)
    blob += struct.pack("<H", len(tilemap) // 2) + tilemap
    pal_at = len(blob)
    blob += pal + alt
    bank, addr = alloc.alloc(len(blob))
    put(bank, addr, blob)

    code = loader(0xC00000 | CODE_AT, bank)
    assert all(b == 0xFF for b in rom[CODE_AT:CODE_AT + len(code)]), "portrait loader area is not free"
    patches = [(CODE_AT, code)]
    for site in CALL_SITES:
        assert bytes(rom[site:site + 4]) == bytes.fromhex("2230ad88")
        patches.append((site, bytes([0x22, CODE_AT & 255, (CODE_AT >> 8) & 255, 0xFF])))
    x = 2 * FIGHTER
    patches += [(T_GFX + x, struct.pack("<H", addr)), (T_MAP + x, struct.pack("<H", addr + map_at)),
                (T_PAL + x, struct.pack("<H", addr + pal_at)), (T_BANK + x, struct.pack("<H", bank)),
                (T_COUNT + x, struct.pack("<H", len(tiles))), (T_MIRROR + x, struct.pack("<H", 0))]
    for off, data in patches:
        rom[off:off + len(data)] = data
        if off & 0x8000:
            rom[exhirom.ORIG_SIZE + off:exhirom.ORIG_SIZE + off + len(data)] = data
    if preview:
        rgb = np.zeros(idx.shape + (3,), np.uint8)
        for i, c in enumerate(colours):
            rgb[idx == i] = c
        Image.fromarray(rgb).save(preview)
    return dict(tiles=len(tiles), bank="%02X" % bank, size=idx.shape)
