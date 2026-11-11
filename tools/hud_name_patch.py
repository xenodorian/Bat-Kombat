"""Make the in-fight HUD name under the health bar read BATMAN for fighter id 24 (Rain).

Original 4 MB UMK3 (USA) HiROM ROM. No header/checksum bytes are touched.

How the HUD name works (see REPORT.md): the name graphics are one compressed 2bpp strip
("atlas", ROM E3:F261, 155 tiles) decompressed to WRAM 7F:5300 each time the HUD is set up
(routine 87:EED0). Per fighter id a 3 byte entry at 87:EEE9 + 3*id = (first tile, tile count,
right-align offset) selects a slice that is DMA'd to BG3 tiles $1BD.. (P1) or $1C7.. (P2).

Patch:
  1. 87:EEE4  JSL $88AD30  ->  JSL $FF:F800 (hook: calls the decompressor, then copies 7 extra
     tiles of BATMAN from ROM into the atlas buffer right after the original 155 tiles, 7F:5CB0).
  2. 87:EF31  entry for id 24 (RAIN) 86 04 06  ->  9B 07 03 (tile $9B, 7 tiles, offset 3).
  3. $FF:F800..  hook code (26 bytes) + 112 bytes of 2bpp tile data (BATMAN, built from the
     KABAL "BA", STRYKER "T", ERMAC "MA" and RAIN "N" glyph columns of the atlas).
"""

HOOK_ADDR = 0x3FF800            # file offset of SNES $FF:F800 (free 0xFF padding in the original)
HOOK_SNES = 0xFFF800
CALL_SITE = 0x07EEE4            # 87:EEE4  22 30 AD 88  (JSL $88AD30)
TABLE_ENTRY = 0x07EEE9 + 3 * 24  # 87:EF31, entry for fighter id 24
ATLAS_TILES = 155               # decompressed atlas = $9B0 bytes
NEW_TILE = ATLAS_TILES          # first tile of BATMAN inside the WRAM buffer
NTILES = 7

BATMAN_TILES = bytes.fromhex(
    "3c007f3e3f66746efa7cc46e5deefff91800381c3c3c7c6cfe4cfefcfd8e078e7e00ff7e7f18311819303831313173317100"
    "fb73ff735af7ffd5bfddff99f99b8700cf87c78f9f8d9f891fbfff31a2710c002e1cbc1eb61efb165eb3f7b3b3b34000e040"
    "60c0c0c0c0c080c0c080c080")
assert len(BATMAN_TILES) == NTILES * 16


def _hook(data_snes_lo):
    dst = 0x5300 + NEW_TILE * 16
    return bytes([
        0x22, 0x30, 0xAD, 0x88,              # jsl $88AD30   (original call)
        0x08,                                # php
        0xC2, 0x30,                          # rep #$30
        0x48, 0xDA, 0x5A, 0x8B,              # pha phx phy phb
        0xA2, data_snes_lo & 0xFF, data_snes_lo >> 8,   # ldx #src
        0xA0, dst & 0xFF, dst >> 8,          # ldy #$5CB0
        0xA9, NTILES * 16 - 1, 0x00,         # lda #111
        0x54, 0x7F, 0xFF,                    # mvn $FF -> $7F
        0xAB, 0x7A, 0xFA, 0x68,              # plb ply plx pla
        0x28,                                # plp
        0x6B,                                # rtl
    ])


def patch(rom: bytearray) -> None:
    assert len(rom) >= 0x400000
    assert bytes(rom[CALL_SITE:CALL_SITE + 4]) == bytes([0x22, 0x30, 0xAD, 0x88]), "unexpected ROM"
    assert bytes(rom[TABLE_ENTRY:TABLE_ENTRY + 3]) == bytes([0x86, 0x04, 0x06]), "unexpected table"
    code_len = len(_hook(0))
    assert all(b == 0xFF for b in rom[HOOK_ADDR:HOOK_ADDR + code_len + len(BATMAN_TILES)]), "area not free"
    code = _hook((HOOK_SNES & 0xFFFF) + code_len)
    rom[HOOK_ADDR:HOOK_ADDR + code_len] = code
    rom[HOOK_ADDR + code_len:HOOK_ADDR + code_len + len(BATMAN_TILES)] = BATMAN_TILES
    rom[CALL_SITE + 1:CALL_SITE + 4] = bytes([HOOK_SNES & 0xFF, (HOOK_SNES >> 8) & 0xFF, HOOK_SNES >> 16])
    rom[TABLE_ENTRY:TABLE_ENTRY + 3] = bytes([NEW_TILE, NTILES, 10 - NTILES])
