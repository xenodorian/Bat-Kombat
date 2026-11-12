"""Batman's small face on the one-player tower screen ("Choose your destiny") of UMK3 (USA, SNES).

How the tower gets its faces (found with the debugger, see Current_Work.md):
  * $86:DD69 decompresses one sheet holding every fighter's 32 x 48 face from $C3:0000 to $7F:6300, then
    $86:9823 (Y = $0272) sets bitplane 7 of every tile, so the pixels use colours 128-255.
  * Face k is 24 8bpp tiles (4 wide, 6 tall, row-major) at $7F:6340 + k * $600. Fighter 24 (Rain) is k = 23,
    at $7F:ED40. The player's face is copied from there to video RAM (seen at VRAM byte $3440).
  * The tower palette holds the roster portrait palette (file 0x3F7BC8, 95 colours) at colours 129-223.
    The roster patch maps pictures to colours 49-143, so a tower pixel is the roster index + 80.

The patch replaces "ldy #$0272 / jml $869823" at $86:DD83 with a jump to a routine that does the same and then
copies Batman's face over entry 23.
"""
import roster_portrait_patch as rp

SITE = 0x06DD83
SITE_BYTES = bytes.fromhex("a072025c239886")
CODE_AT = 0x3FE480                   # $FF:E480
DATA_AT = 0x3FE500                   # $FF:E500, 1536 bytes
FACE_WRAM = 0xED40                   # $7F:ED40, entry 23
TOWER_OFFSET = 129 - rp.PAL_FIRST    # roster colour index -> tower colour index


def patch(rom, portrait_png_path):
    """rom: bytearray of the 4 MB original."""
    assert rom[SITE:SITE + 7] == SITE_BYTES, "unexpected bytes at the tower sheet loader"
    idx = rp.image_to_indices(rom, portrait_png_path)
    idx = [[v + TOWER_OFFSET for v in row] for row in idx]
    tiles = rp.indices_to_tiles(idx)
    assert len(tiles) == 1536
    code = bytes([
        0xA0, 0x72, 0x02,                         # ldy #$0272
        0x22, 0x23, 0x98, 0x86,                   # jsl $869823 (sets bitplane 7, ends with rtl)
        0x8B,                                     # phb
        0xA9, 0xFF, 0x05,                         # lda #$05FF
        0xA2, DATA_AT & 0xFF, (DATA_AT >> 8) & 0xFF,          # ldx #data
        0xA0, FACE_WRAM & 0xFF, FACE_WRAM >> 8,  # ldy #$ED40
        0x54, 0x7F, 0xFF,                         # mvn $7F,$FF
        0xAB,                                     # plb
        0x6B,                                     # rtl (to the caller of $86:DD69)
    ])
    assert CODE_AT + len(code) <= DATA_AT
    for a, b in ((CODE_AT, len(code)), (DATA_AT, 1536)):
        assert all(x == 0xFF for x in rom[a:a + b]), "tower face area is not free"
    rom[CODE_AT:CODE_AT + len(code)] = code
    rom[DATA_AT:DATA_AT + 1536] = tiles
    t = 0xC00000 | CODE_AT
    rom[SITE:SITE + 7] = bytes([0x5C, t & 0xFF, (t >> 8) & 0xFF, t >> 16, 0xEA, 0xEA, 0xEA])   # jml / nop x3
