"""Build a UMK3 (USA) ROM where Rain's fight sprites are Batman.

Usage: python3 tools/make_batman_fighter.py "Ultimate Mortal Kombat 3 (USA).zip" OUTPUT.sfc

The zip is the one in this repo. A loose 4 MB .sfc also works. Rain's moves and
hitboxes are untouched. His 19-piece layout clips a cape, so this does not
repaint those tiles. The hook is the OAM DMA at file 0x8BA19: it hides Rain and writes 16 sprites
of 16x16 (the whole pose scaled into 64x64, not cropped) and uploads a
16-colour Batman palette. Poses: idle, walk (LEFT/RIGHT), attack (A/B/X/Y).
HUD name, portrait and specials stay Rain's.
"""
import io
import sys
import tarfile
import zipfile
from PIL import Image

RAIN_ID = 24
# Verified this session from a live Rain-vs-Jade fight:
#   OAM low table WRAM $7E:C4AA, built by $80:8000, tail at file 0x806E (lda $0C / sta $1A30 / rtl)
#   OAM DMA $88:BA10, the sta $420B is file 0x8BA19. Hook sits on the sep #$20 before it (file 0x8BA16).
#   P1 pieces move around the OAM table. Unused slots are Y=$E8 (8 of them were
#   measured in a live fight: 81 fillers). Page-1 tile $C0 is VRAM byte $F800.
HOOK_BUILDER = 0x806E
HOOK_DMA = 0x8BA19
EXPECT_BUILDER = bytes.fromhex("a50c8d301a6b")
EXPECT_DMA = bytes.fromhex("e220a9018d0b42")
CAVE = 0x3FDC6E          # $FF:DC6E, a 0xFF run through the end of the 4 MB ROM
CAVE_BANK = 0xFF
CAVE_PC = 0xDC6E
PAL_PC = 0xE06E
TILE_BASE = 0x80         # page 1. 16x16 sprites, rows stride 16, byte VRAM $F000.
VRAM_WORD = 0x7800
POSE_BYTES = 64 * 32     # linear 8x8 in ROM; the DMA spreads each row across a 16-wide sheet
ORIGIN_X = 48
ORIGIN_Y = 112
SPRITE_N = 16            # 4x4 of 16x16 covers the 64x64 pose. 8x8 needed more free OAM than the fight has.
POSES = (
    "frames/f000_62x89.png",  # idle stance
    "frames/f006_45x90.png",  # stride, shown while LEFT or RIGHT is held
    "frames/f013_81x91.png",  # punch, shown while A/B/X/Y is held
)
# index 0 is transparent. The rest are the pose's own colours, in 5-bit steps.
PALETTE_RGB = [
    (0, 0, 0),
    (0, 0, 0),          # cowl, cape, boots
    (0, 16, 24),
    (32, 32, 48),
    (48, 64, 96),       # suit
    (72, 88, 128),
    (104, 120, 152),
    (248, 192, 0),      # belt
    (248, 144, 32),
    (176, 80, 0),
    (248, 200, 192),    # skin
    (160, 176, 200),    # eyes
    (96, 40, 0),
    (192, 104, 64),
    (248, 128, 128),
    (16, 16, 32),
]


def bgr555(r, g, b):
    return ((b // 8) << 10) | ((g // 8) << 5) | (r // 8)


def nearest(r, g, b):
    best, bi = 1 << 30, 1
    for i, (pr, pg, pb) in enumerate(PALETTE_RGB[1:], start=1):
        d = (r - pr) ** 2 + (g - pg) ** 2 + (b - pb) ** 2
        if d < best:
            best, bi = d, i
    return bi


def pose_tiles(png):
    im = Image.open(io.BytesIO(png)).convert("RGBA")
    im.thumbnail((64, 64), Image.Resampling.NEAREST)
    canvas = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    canvas.paste(im, ((64 - im.width) // 2, (64 - im.height) // 2), im)
    pix = canvas.load()
    raw = bytearray()
    for row in range(8):
        for col in range(8):
            tile = [[0] * 8 for _ in range(8)]
            for y in range(8):
                for x in range(8):
                    r, g, b, a = pix[col * 8 + x, row * 8 + y]
                    if a >= 128:
                        tile[y][x] = nearest(r, g, b)
            rows = []
            for y in range(8):
                p = [0, 0, 0, 0]
                for x in range(8):
                    v = tile[y][x]
                    bit = 0x80 >> x
                    for plane in range(4):
                        if v & (1 << plane):
                            p[plane] |= bit
                rows.append(p)
            for y in range(8):
                raw.append(rows[y][0])
                raw.append(rows[y][1])
            for y in range(8):
                raw.append(rows[y][2])
                raw.append(rows[y][3])
    if len(raw) != POSE_BYTES:
        raise SystemExit("pose tile blob is %d bytes" % len(raw))
    return raw


class Asm:
    def __init__(self, pc):
        self.pc = pc
        self.b = bytearray()
        self.labels = {}
        self.rel = []
        self.abs_ = []

    def here(self):
        return self.pc + len(self.b)

    def label(self, name):
        self.labels[name] = self.here()

    def emit(self, *xs):
        for x in xs:
            if isinstance(x, bytes):
                self.b += x
            elif isinstance(x, int):
                self.b.append(x)
            else:
                self.b += bytes(x)

    def imm(self, n):
        return bytes((n & 0xFF, (n >> 8) & 0xFF))

    def br(self, op, name):
        self.b.append(op)
        self.rel.append((len(self.b), name))
        self.b.append(0)

    def jsr(self, name):
        self.b.append(0x20)
        self.abs_.append((len(self.b), name))
        self.b += b"\x00\x00"

    def jmp(self, name):
        self.b.append(0x4C)
        self.abs_.append((len(self.b), name))
        self.b += b"\x00\x00"

    def lda_y(self, name):
        self.b.append(0xB9)
        self.abs_.append((len(self.b), name))
        self.b += b"\x00\x00"

    def finish(self):
        for at, name in self.rel:
            rel = self.labels[name] - (self.pc + at + 1)
            if not -128 <= rel < 128:
                raise SystemExit("branch %s out of range (%d)" % (name, rel))
            self.b[at] = rel & 0xFF
        for at, name in self.abs_:
            addr = self.labels[name]
            self.b[at] = addr & 0xFF
            self.b[at + 1] = (addr >> 8) & 0xFF
        return bytes(self.b)


def assemble():
    """Hook the OAM DMA itself. The sprite list is finished by then, so the
    picture the PPU scans is the one this writes. Editing earlier loses to a
    later rebuild and never reaches the screen."""
    a = Asm(CAVE_PC)
    a.emit(0x08)                  # php
    a.emit(0xC2, 0x30)            # rep #$30
    a.emit(0xDA, 0x5A)            # phx phy
    a.emit(0x8B)                  # phb
    a.emit(0xF4, 0x7E, 0x7E)      # pea #$7E7E
    a.emit(0xAB, 0xAB)            # DB=$7E
    a.emit(0xAD, 0xC8, 0x52)      # lda $52C8
    a.emit(0x29, 0xFF, 0x00)
    a.emit(0xC9, RAIN_ID, 0x00)
    a.br(0xD0, "notrain")
    a.jsr("overlay")
    a.br(0x80, "bank0")
    a.label("notrain")
    a.emit(0xE2, 0x20)
    a.emit(0x9C, 0xFE, 0x03)      # stz $03FE
    a.emit(0xC2, 0x20)
    a.label("bank0")
    a.emit(0xF4, 0x00, 0x00)      # pea #$0000
    a.emit(0xAB, 0xAB)            # DB=0 so $21xx/$42xx are registers
    a.emit(0xAF, 0xFE, 0x03, 0x7E)
    a.emit(0x29, 0xFF, 0x00)
    a.br(0xF0, "ship")
    a.emit(0xAF, 0x00, 0x17, 0x7E)  # lda $7E1700
    a.emit(0x89, 0xC0, 0xC0)      # bit #$C0C0 attack
    a.br(0xD0, "attack")
    a.emit(0x89, 0x00, 0x03)      # bit #$0300 left/right
    a.br(0xD0, "walk")
    a.emit(0xA2) ; a.emit((0xE08E).to_bytes(2, "little"))
    a.br(0x80, "upload")
    a.label("attack")
    a.emit(0xA2) ; a.emit((0xE08E + 2 * POSE_BYTES).to_bytes(2, "little"))
    a.br(0x80, "upload")
    a.label("walk")
    a.emit(0xA2) ; a.emit((0xE08E + POSE_BYTES).to_bytes(2, "little"))
    a.label("upload")
    a.jsr("xfer")
    a.label("ship")
    a.emit(0xAB)                  # plb  game's DB, the one sta $420B needs
    a.emit(0xE2, 0x20)
    a.emit(0xA9, 0x01)
    a.emit(0x8D, 0x0B, 0x42)      # sta $420B
    a.emit(0x7A, 0xFA)            # ply plx
    a.emit(0x28)                  # plp
    a.emit(0x6B)                  # rtl

    a.label("overlay")
    a.emit(0xA0, 0x00, 0x00)
    a.emit(0xA2, 0x00, 0x00)
    a.label("cloop")
    a.emit(0xBD, 0xAA, 0xC4)
    a.emit(0x29, 0x00, 0xFF)
    a.emit(0xC9, 0x00, 0xE0)
    a.br(0xB0, "cnext")
    a.emit(0xBD, 0xAC, 0xC4)
    a.emit(0x29, 0x00, 0x3F)
    a.emit(0xC9, 0x00, 0x30)
    a.br(0xD0, "cnext")
    a.emit(0xC8)
    a.label("cnext")
    a.emit(0xE8, 0xE8, 0xE8, 0xE8)
    a.emit(0xE0, 0x00, 0x02)
    a.br(0xD0, "cloop")
    a.emit(0xC0, 0x08, 0x00)
    a.br(0x90, "few")
    a.emit(0xE2, 0x20)
    a.emit(0xA9, 0x01)
    a.emit(0x8D, 0xFE, 0x03)
    a.emit(0xC2, 0x20)
    a.jsr("draw")
    a.emit(0xA2, 0x00, 0x00)
    a.label("hloop")
    a.emit(0xBD, 0xAA, 0xC4)
    a.emit(0x29, 0x00, 0xFF)
    a.emit(0xC9, 0x00, 0xE0)
    a.br(0xB0, "hnext")
    a.emit(0xBD, 0xAC, 0xC4)
    a.emit(0x29, 0x00, 0x3F)
    a.emit(0xC9, 0x00, 0x30)
    a.br(0xD0, "hnext")
    a.emit(0xBD, 0xAA, 0xC4)
    a.emit(0x29, 0xFF, 0x00)
    a.emit(0x09, 0x00, 0xE0)
    a.emit(0x9D, 0xAA, 0xC4)
    a.label("hnext")
    a.emit(0xE8, 0xE8, 0xE8, 0xE8)
    a.emit(0xE0, 0x00, 0x02)
    a.br(0xD0, "hloop")
    a.emit(0x60)
    a.label("few")
    a.emit(0xE2, 0x20)
    a.emit(0x9C, 0xFE, 0x03)
    a.emit(0xC2, 0x20)
    a.emit(0x60)

    a.label("draw")
    # Slots 57-72 stay empty for the whole fight, so this is sixteen stores
    # and five size-byte updates. Searching the table from here ran past
    # vblank and the sky's HDMA never got set, which left the top black.
    for i, slot in enumerate(range(57, 73)):
        col, row = i & 3, i >> 2
        xy = (ORIGIN_X + col * 16) | ((ORIGIN_Y + row * 16) << 8)
        ta = (TILE_BASE + row * 32 + col * 2) | 0x3100
        addr = 0xC4AA + slot * 4
        a.emit(0xA9, xy & 0xFF, (xy >> 8) & 0xFF)
        a.emit(0x8D, addr & 0xFF, (addr >> 8) & 0xFF)
        a.emit(0xA9, ta & 0xFF, (ta >> 8) & 0xFF)
        a.emit(0x8D, (addr + 2) & 0xFF, ((addr + 2) >> 8) & 0xFF)
    a.emit(0xE2, 0x20)
    a.emit(0xAD, 0xB8, 0xC6)
    a.emit(0x29, 0x03)
    a.emit(0x09, 0xA8)
    a.emit(0x8D, 0xB8, 0xC6)
    a.emit(0xA9, 0xAA)
    a.emit(0x8D, 0xB9, 0xC6)
    a.emit(0x8D, 0xBA, 0xC6)
    a.emit(0x8D, 0xBB, 0xC6)
    a.emit(0xAD, 0xBC, 0xC6)
    a.emit(0x29, 0xFC)
    a.emit(0x09, 0x02)
    a.emit(0x8D, 0xBC, 0xC6)
    a.emit(0xC2, 0x20)
    a.emit(0x60)

    a.label("fixhi")
    a.emit(0xDA, 0x5A)
    a.emit(0x8A)
    a.emit(0x29, 0x0C, 0x00)
    a.emit(0x4A)
    a.emit(0x48)
    a.emit(0x8A)
    a.emit(0x4A, 0x4A, 0x4A, 0x4A)
    a.emit(0xAA)
    a.emit(0xE2, 0x20)
    a.emit(0xA3, 0x01)
    a.br(0xF0, "hs0")
    a.emit(0xC9, 0x02)
    a.br(0xF0, "hs2")
    a.emit(0xC9, 0x04)
    a.br(0xF0, "hs4")
    a.emit(0xBD, 0xAA, 0xC6)
    a.emit(0x29, 0x3F)
    a.emit(0x09, 0x80)            # 16x16, x high clear
    a.br(0x80, "hst")
    a.label("hs0")
    a.emit(0xBD, 0xAA, 0xC6)
    a.emit(0x29, 0xFC)
    a.emit(0x09, 0x02)
    a.br(0x80, "hst")
    a.label("hs2")
    a.emit(0xBD, 0xAA, 0xC6)
    a.emit(0x29, 0xF3)
    a.emit(0x09, 0x08)
    a.br(0x80, "hst")
    a.label("hs4")
    a.emit(0xBD, 0xAA, 0xC6)
    a.emit(0x29, 0xCF)
    a.emit(0x09, 0x20)
    a.label("hst")
    a.emit(0x9D, 0xAA, 0xC6)
    a.emit(0xC2, 0x30)
    a.emit(0x68)
    a.emit(0x7A, 0xFA)
    a.emit(0x60)

    a.label("xfer")
    a.emit(0xDA)                  # phx source
    a.emit(0xE2, 0x20)
    a.emit(0xA0, 0x00, 0x00)
    a.label("sav")
    a.emit(0xB9, 0x00, 0x43)
    a.emit(0x48)
    a.emit(0xC8)
    a.emit(0xC0, 0x07, 0x00)
    a.br(0xD0, "sav")
    a.emit(0xC2, 0x20)
    a.emit(0xA3, 0x08)            # lda $08,s source under 7 dma bytes
    a.emit(0xAA)
    a.emit(0x48)                      # source
    a.emit(0xAF, 0xF8, 0x03, 0x7E)    # last source uploaded
    a.emit(0xC3, 0x01)
    a.br(0xF0, "same")
    a.emit(0x68)
    a.emit(0x8F, 0xF8, 0x03, 0x7E)
    a.jsr("tiles")
    a.jsr("palette")
    a.br(0x80, "nodma")
    a.label("same")
    a.emit(0x68)
    a.label("nodma")
    a.emit(0xE2, 0x20)
    a.emit(0xA0, 0x06, 0x00)
    a.label("res")
    a.emit(0x68)
    a.emit(0x99, 0x00, 0x43)
    a.emit(0x88)
    a.br(0x10, "res")
    a.emit(0xC2, 0x20)
    a.emit(0xFA)
    a.emit(0x60)

    a.label("tiles")
    a.emit(0xC2, 0x30)
    a.emit(0xA0, 0x00, 0x00)      # row 0..7, 8 tiles each, one row of a 16-wide sheet
    a.label("trow")
    a.emit(0xC2, 0x20)
    a.emit(0x8A)
    a.emit(0xE2, 0x20)
    a.emit(0x8D, 0x02, 0x43)
    a.emit(0xEB)
    a.emit(0x8D, 0x03, 0x43)
    a.emit(0xA9, 0x01, 0x8D, 0x00, 0x43)
    a.emit(0xA9, 0x18, 0x8D, 0x01, 0x43)
    a.emit(0xA9, CAVE_BANK, 0x8D, 0x04, 0x43)
    a.emit(0xA9, 0x00, 0x8D, 0x05, 0x43)   # 256 bytes
    a.emit(0xA9, 0x01, 0x8D, 0x06, 0x43)
    a.emit(0xC2, 0x20)
    a.emit(0x98)                  # row
    a.emit(0xEB)                  # << 8
    a.emit(0x18)
    a.emit(0x69, 0x00, 0x78)      # word $7800 + row*$100 = byte $F000 + row*$200
    a.emit(0x8D, 0x16, 0x21)
    a.emit(0xE2, 0x20)
    a.emit(0xA9, 0x80, 0x8D, 0x15, 0x21)
    a.emit(0xA9, 0x01, 0x8D, 0x0B, 0x42)
    a.emit(0xC2, 0x30)
    a.emit(0x8A)
    a.emit(0x18, 0x69, 0x00, 0x01)  # source += 256
    a.emit(0xAA)
    a.emit(0xC8)
    a.emit(0xC0, 0x08, 0x00)
    a.br(0xD0, "trow")
    a.emit(0x60)

    a.label("palette")
    a.emit(0xE2, 0x20)
    a.emit(0xA9, 0x00, 0x8D, 0x00, 0x43)
    a.emit(0xA9, 0x22, 0x8D, 0x01, 0x43)
    a.emit(0xA9, PAL_PC & 0xFF, 0x8D, 0x02, 0x43)
    a.emit(0xA9, (PAL_PC >> 8) & 0xFF, 0x8D, 0x03, 0x43)
    a.emit(0xA9, CAVE_BANK, 0x8D, 0x04, 0x43)
    a.emit(0xA9, 32, 0x8D, 0x05, 0x43)
    a.emit(0x9C, 0x06, 0x43)
    a.emit(0xA9, 128, 0x8D, 0x21, 0x21)
    a.emit(0xA9, 0x01, 0x8D, 0x0B, 0x42)
    a.emit(0xC2, 0x30)
    a.emit(0x60)
    return a.finish()


def fix_checksum(rom):
    hdr = 0xFFC0
    rom[hdr + 0x1C:hdr + 0x20] = b"\x00\x00\x00\x00"
    total = sum(rom) & 0xFFFF
    rom[hdr + 0x1C:hdr + 0x1E] = (total ^ 0xFFFF).to_bytes(2, "little")
    rom[hdr + 0x1E:hdr + 0x20] = total.to_bytes(2, "little")


def load_rom(path):
    if path.lower().endswith(".zip"):
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist() if n.lower().endswith((".sfc", ".smc"))]
            if len(names) != 1:
                sys.exit("zip needs exactly one sfc, found %r" % names)
            data = z.read(names[0])
    else:
        data = open(path, "rb").read()
    if len(data) == 0x400200:
        data = data[0x200:]
    return bytearray(data)


def main(src, dst, art):
    rom = load_rom(src)
    if len(rom) != 0x400000:
        sys.exit("expected the 4 MB UMK3 (USA) ROM")
    if rom[HOOK_BUILDER:HOOK_BUILDER + 6] != EXPECT_BUILDER:
        sys.exit("builder tail at 0x806E is not the expected lda/sta/rtl")
    if rom[HOOK_DMA:HOOK_DMA + 7] != EXPECT_DMA:
        sys.exit("OAM DMA site at 0x8BA19 is not the expected sep/lda/sta")
    code = assemble()
    if CAVE_PC + len(code) > PAL_PC:
        sys.exit("hook code overflowed the reserved $400 bytes (%d)" % len(code))
    blobs = []
    with tarfile.open(art) as tar:
        for name in POSES:
            blobs.append(pose_tiles(tar.extractfile(name).read()))
    pal = bytearray()
    for rgb in PALETTE_RGB:
        pal += bgr555(*rgb).to_bytes(2, "little")
    data = code + bytes(PAL_PC - (CAVE_PC + len(code))) + pal + b"".join(blobs)
    end = CAVE + len(data)
    if end > 0x3FFFB0:
        sys.exit("cave ran into the end of the ROM")
    if any(b != 0xFF for b in rom[CAVE:end]):
        sys.exit("cave is not empty FF padding")
    rom[CAVE:end] = data
    # Leave the sprite builder alone. Patch only the OAM DMA sta $420B.
    rom[HOOK_DMA:HOOK_DMA + 7] = bytes([0x22, CAVE_PC & 0xFF, (CAVE_PC >> 8) & 0xFF, CAVE_BANK, 0xEA, 0xEA, 0xEA])
    fix_checksum(rom)
    open(dst, "wb").write(rom)
    print("wrote", dst)
    print("dma hook $%02X:%04X (%d bytes)" % (CAVE_BANK, CAVE_PC, len(code)))
    print("tiles VRAM word $%04X, tile $%02X, poses %d x %d bytes" % (
        VRAM_WORD, TILE_BASE, len(blobs), POSE_BYTES))


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    art = sys.argv[3] if len(sys.argv) > 3 else "art/batman_poses.tar.gz"
    main(sys.argv[1], sys.argv[2], art)
