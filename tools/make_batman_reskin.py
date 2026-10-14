"""Build a Batman reskin of Rain in Ultimate Mortal Kombat 3 (USA, SNES).

Usage: python3 make_batman_reskin.py ORIGINAL.sfc OUTPUT.sfc

What it changes (all offsets are file offsets in the 4 MB original):
  1. Name: writes "-BATMAN" in free space at 0x3FF90 and points fighter ID 24 (Rain)
     at it in the name pointer table (0x3E544 + 2*24).
  2. Palette: Rain's sprite palette is stored in two chunks: 4 suit colours at 0x456E8
     and 10 colours at 0x3EAFB3. Cool colours (blue >= red) are turned into a dark
     blue-grey Batman ramp. Warm colours (skin, belt, brown) are left alone.
  3. Header checksum is recomputed.

Rain keeps his sprites, hit data and moves, so this is a reskin and rename only.
"""
import sys

NAME_PTR_TABLE = 0x3E544
RAIN_ID = 24
NAME_FILE_OFFSET = 0x3FF90            # 0x3FF8E..0x3FFF1 is 0xFF padding in the original
NAME_BANK_ADDR = NAME_FILE_OFFSET & 0xFFFF
NEW_NAME = b"-BATMAN\x00"
PALETTE_CHUNKS = [(0x456E8, 4), (0x3EAFB3, 10)]   # (file offset, word count)
EXPECT_OLD_NAME = b"-RAIN\x00"


def decode(w):
    return w & 31, (w >> 5) & 31, (w >> 10) & 31


def encode(r, g, b):
    clip = lambda v: max(0, min(31, int(round(v))))
    return (clip(b) << 10) | (clip(g) << 5) | clip(r)


def batman(w):
    """Map one Rain palette word to its Batman equivalent."""
    r, g, b = decode(w)
    if w == 0 or b < r:
        return w                       # transparent or warm colour: keep
    lum = 0.30 * r + 0.59 * g + 0.11 * b
    # dark navy ramp: slightly more blue than green, least red
    return encode(lum * 0.50, lum * 0.60, lum * 0.95 + 1)


def fix_checksum(rom):
    hdr = 0xFFC0
    rom[hdr + 0x1C:hdr + 0x20] = b"\x00\x00\x00\x00"
    s = sum(rom) & 0xFFFF
    comp = s ^ 0xFFFF
    rom[hdr + 0x1C:hdr + 0x1E] = comp.to_bytes(2, "little")
    rom[hdr + 0x1E:hdr + 0x20] = s.to_bytes(2, "little")


def main(src, dst):
    rom = bytearray(open(src, "rb").read())
    if len(rom) != 0x400000:
        sys.exit("expected the 4 MB original UMK3 (USA) ROM")
    # 1. name
    if rom[NAME_FILE_OFFSET:NAME_FILE_OFFSET + len(NEW_NAME)] != b"\xff" * len(NEW_NAME):
        sys.exit("free space at 0x%X is not empty" % NAME_FILE_OFFSET)
    ptr_off = NAME_PTR_TABLE + 2 * RAIN_ID
    old = rom[ptr_off] | rom[ptr_off + 1] << 8
    old_off = 0x30000 | old
    if rom[old_off:old_off + len(EXPECT_OLD_NAME)] != EXPECT_OLD_NAME:
        sys.exit("fighter ID 24 name is not -RAIN here; wrong ROM?")
    rom[NAME_FILE_OFFSET:NAME_FILE_OFFSET + len(NEW_NAME)] = NEW_NAME
    rom[ptr_off] = NAME_BANK_ADDR & 0xFF
    rom[ptr_off + 1] = NAME_BANK_ADDR >> 8
    # 2. palette
    for off, n in PALETTE_CHUNKS:
        for i in range(n):
            a = off + 2 * i
            w = rom[a] | rom[a + 1] << 8
            nw = batman(w)
            rom[a], rom[a + 1] = nw & 0xFF, nw >> 8
    fix_checksum(rom)
    open(dst, "wb").write(rom)
    print("wrote", dst)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
