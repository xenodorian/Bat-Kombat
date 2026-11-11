"""Replace Rain's roster portrait (top-left cell of the UMK3 SNES fighter select) with a supplied image.

patch(rom: bytearray, portrait_png_path: str) -> None   (in place, header checksum untouched)

How it works (see REPORT.md): roster portraits are BG1 (mode 3, 8bpp) tiles. Rain's cell is tiles
$269-$280 (4x6, sequential) at VRAM byte $9A40, fed by DMA from WRAM $7F:C540 (1536 bytes), which is
filled by a decompressor and then post-processed by the routine at $84:9703. The patch redirects the
single roster call site JSL $849703 (at $84:945F, file 0x04945F) to a stub in free space that calls the
original and then block-copies 1536 bytes of ready-made 8bpp tiles over $7F:C540.
All 23 portraits share one 95 colour palette (CGRAM idx 49..143, 190 bytes in ROM at 0x3F7BC8),
so the image is quantised to that palette; no palette is changed.
"""
import struct
from PIL import Image

STUB = 0x3FF000          # SNES $FF:F000
DATA = 0x3FF100          # SNES $FF:F100 (1536 bytes, ends before 0x3FF700)
HOOK = 0x04945F          # JSL $849703 in the roster loader
PAL_OFF, PAL_FIRST, PAL_N = 0x3F7BC8, 49, 95
CELL_W, CELL_H = 32, 48


def _palette(rom):
    out = []
    for i in range(PAL_N):
        c = struct.unpack_from('<H', rom, PAL_OFF + i * 2)[0]
        out.append(((c & 31) * 255 // 31, ((c >> 5) & 31) * 255 // 31, ((c >> 10) & 31) * 255 // 31))
    return out


def image_to_indices(rom, path, dither=False):
    """Load image, fit to 32x48 (centre crop to 2:3 if needed), map to game palette indices (49..143)."""
    im = Image.open(path).convert('RGBA')
    bg = Image.new('RGBA', im.size, (0, 0, 0, 255))
    # gradient background for transparent pixels: dark blue at top to grey-blue at bottom
    px = bg.load()
    for y in range(im.size[1]):
        t = y / max(1, im.size[1] - 1)
        col = (int(24 + 40 * t), int(30 + 40 * t), int(70 + 40 * t), 255)
        for x in range(im.size[0]):
            px[x, y] = col
    bg.alpha_composite(im)
    im = bg.convert('RGB')
    w, h = im.size
    if w * 3 > h * 2:                      # too wide: crop width
        nw = h * 2 // 3; x0 = (w - nw) // 2; im = im.crop((x0, 0, x0 + nw, h))
    elif w * 3 < h * 2:                    # too tall: crop height (keep top)
        im = im.crop((0, 0, w, w * 3 // 2))
    im = im.resize((CELL_W, CELL_H), Image.LANCZOS)
    pal = _palette(rom)
    a = [[list(map(float, im.getpixel((x, y)))) for x in range(CELL_W)] for y in range(CELL_H)]
    idx = [[0] * CELL_W for _ in range(CELL_H)]
    for y in range(CELL_H):
        for x in range(CELL_W):
            r, g, b = a[y][x]
            best = min(range(PAL_N), key=lambda i: (pal[i][0] - r) ** 2 * 3 + (pal[i][1] - g) ** 2 * 4 + (pal[i][2] - b) ** 2 * 2)
            idx[y][x] = PAL_FIRST + best
            if dither:
                e = (r - pal[best][0], g - pal[best][1], b - pal[best][2])
                for dx, dy, f in ((1, 0, 7 / 16), (-1, 1, 3 / 16), (0, 1, 5 / 16), (1, 1, 1 / 16)):
                    xx, yy = x + dx, y + dy
                    if 0 <= xx < CELL_W and 0 <= yy < CELL_H:
                        for k in range(3):
                            a[yy][xx][k] += e[k] * f * 0.6
    return idx


def indices_to_tiles(idx):
    """32x48 index image -> 24 SNES 8bpp tiles (64 bytes each), row-major 4 wide x 6 tall."""
    out = bytearray()
    for ty in range(6):
        for tx in range(4):
            t = bytearray(64)
            for y in range(8):
                for pb in range(4):
                    lo = hi = 0
                    for x in range(8):
                        v = idx[ty * 8 + y][tx * 8 + x]
                        lo |= ((v >> (2 * pb)) & 1) << (7 - x)
                        hi |= ((v >> (2 * pb + 1)) & 1) << (7 - x)
                    t[pb * 16 + y * 2] = lo
                    t[pb * 16 + y * 2 + 1] = hi
            out += t
    return bytes(out)


def _stub():
    s = bytearray()
    s += bytes([0xC9, 0x03, 0x00])            # cmp #$0003
    s += bytes([0xD0, 0x00]); b1 = len(s) - 1  # bne plain
    s += bytes([0xE0, 0x72, 0x02])            # cpx #$0272
    s += bytes([0xD0, 0x00]); b2 = len(s) - 1  # bne plain
    s += bytes([0x22, 0x03, 0x97, 0x84])      # jsl $849703 (original routine)
    s += bytes([0x8B])                        # phb
    s += bytes([0xA9, 0xFF, 0x05])            # lda #$05FF  (1536-1)
    s += bytes([0xA2, 0x00, 0xF1])            # ldx #$F100  (src, bank $FF)
    s += bytes([0xA0, 0x40, 0xC5])            # ldy #$C540  (dst, bank $7F)
    s += bytes([0x54, 0x7F, 0xFF])            # mvn $7F,$FF
    s += bytes([0xAB, 0x6B])                  # plb ; rtl
    plain = len(s)
    s += bytes([0x5C, 0x03, 0x97, 0x84])      # jml $849703 (not the roster call: behave as before)
    s[b1] = plain - (b1 + 1)
    s[b2] = plain - (b2 + 1)
    return bytes(s)


def patch(rom, portrait_png_path, dither=False):
    assert len(rom) == 0x400000
    assert rom[HOOK:HOOK + 4] == bytes([0x22, 0x03, 0x97, 0x84]), "unexpected ROM (hook site)"
    assert rom[STUB:STUB + 0x800] == b'\xff' * 0x800, "free area not empty"
    tiles = indices_to_tiles(image_to_indices(rom, portrait_png_path, dither))
    stub = _stub()
    assert len(stub) < 0x100 and len(tiles) == 1536
    rom[STUB:STUB + len(stub)] = stub
    rom[DATA:DATA + 1536] = tiles
    rom[HOOK:HOOK + 4] = bytes([0x22, 0x00, 0xF0, 0xFF])   # jsl $FF:F000
