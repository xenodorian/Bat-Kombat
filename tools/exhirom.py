"""Expand the 4 MB UMK3 HiROM image to an 8 MB ExHiROM image and manage the new free space.

ExHiROM layout: banks $C0-$FF (and $80-$BF upper halves) read file 0x000000-0x3FFFFF, the original game.
Banks $40-$7D read file 0x400000 + ((bank - 0x40) << 16) + addr. Banks $00-$3F upper halves ($8000-$FFFF) read the same
file area as banks $40-$7D upper halves, so the original upper halves are copied there (vectors and any slow-bank access).
That leaves the lower half ($0000-$7FFF) of each bank $40-$7D free: 62 blocks of 32 KB.
"""

ORIG_SIZE = 0x400000
NEW_SIZE = 0x800000
HEADER = 0xFFC0


def expand(rom4):
    assert len(rom4) == ORIG_SIZE
    rom = bytearray(rom4) + bytearray(b"\xff" * ORIG_SIZE)
    for b in range(0x40):
        lo = (b << 16) | 0x8000
        rom[ORIG_SIZE + lo:ORIG_SIZE + lo + 0x8000] = rom4[lo:lo + 0x8000]
    for base in (0, ORIG_SIZE):
        rom[base + HEADER + 0x15] = 0x35      # map mode: ExHiROM, FastROM
        rom[base + HEADER + 0x17] = 0x0D      # 8 MB
    return rom


def file_offset(bank, addr):
    """File offset of a SNES address in the expanded image."""
    if 0x40 <= bank <= 0x7D:
        return ORIG_SIZE + ((bank - 0x40) << 16) + addr
    if bank >= 0xC0:
        return ((bank - 0xC0) << 16) + addr
    if 0x80 <= bank <= 0xBF and addr >= 0x8000:
        return ((bank - 0x80) << 16) + addr
    raise ValueError("unmapped %02X:%04X" % (bank, addr))


def fix_checksum(rom):
    for base in (0, ORIG_SIZE):
        rom[base + HEADER + 0x1C:base + HEADER + 0x20] = b"\xff\xff\x00\x00"
    s = sum(rom) & 0xFFFF
    for base in (0, ORIG_SIZE):
        rom[base + HEADER + 0x1C:base + HEADER + 0x1E] = (s ^ 0xFFFF).to_bytes(2, "little")
        rom[base + HEADER + 0x1E:base + HEADER + 0x20] = s.to_bytes(2, "little")


class Allocator:
    """Hands out space in the free lower halves of banks $40-$7D. Nothing crosses a bank."""

    def __init__(self, first_bank=0x40, last_bank=0x7D):
        self.bank, self.addr, self.last = first_bank, 0, last_bank

    def alloc(self, size, align=1):
        assert size <= 0x8000
        a = (self.addr + align - 1) // align * align
        if a + size > 0x8000:
            self.bank += 1
            a = 0
            if self.bank > self.last:
                raise MemoryError("expansion space exhausted")
        self.addr = a + size
        return self.bank, a

    def new_bank(self):
        if self.addr:
            self.bank += 1
            self.addr = 0
