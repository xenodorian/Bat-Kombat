"""Helpers for working with the UMK3 (USA) HiROM dump. Read-only analysis."""
import sys
from capstone import Cs, CS_ARCH_MOS65XX, CS_MODE_MOS65XX_65816_LONG_M

ROM_PATH_DEFAULT = "Ultimate Mortal Kombat 3 (USA).sfc"


def load(path=ROM_PATH_DEFAULT):
    with open(path, "rb") as f:
        return bytearray(f.read())


def file_to_snes(off):
    """HiROM: file offset -> (bank, addr)."""
    return (0xC0 + (off >> 16), off & 0xFFFF)


def snes_to_file(bank, addr):
    """HiROM: (bank, addr) -> file offset."""
    return ((bank - 0xC0) & 0x3F) << 16 | (addr & 0xFFFF)


def disasm(rom, bank, addr, count=40):
    """Disassemble `count` instructions at a SNES address (M=8 X=8 assumed)."""
    md = Cs(CS_ARCH_MOS65XX, CS_MODE_MOS65XX_65816_LONG_M)
    md.detail = False
    off = snes_to_file(bank, addr)
    out = []
    for ins in md.disasm(bytes(rom[off:off + count * 4]), addr):
        out.append(f"{bank:02X}:{ins.address:04X}  {ins.bytes.hex(' '):<12} {ins.mnemonic} {ins.op_str}")
        if len(out) >= count:
            break
    return "\n".join(out)


def find_word_refs(rom, word):
    """Return file offsets where a 16-bit little-endian word occurs."""
    lo, hi = word & 0xFF, word >> 8
    return [i for i in range(len(rom) - 1) if rom[i] == lo and rom[i + 1] == hi]


def find_long_refs(rom, bank, addr):
    """Return file offsets where a 24-bit pointer (addr lo/hi, bank) occurs."""
    pat = bytes([addr & 0xFF, addr >> 8, bank])
    out, i = [], 0
    while True:
        i = rom.find(pat, i)
        if i < 0:
            return out
        out.append(i)
        i += 1


if __name__ == "__main__":
    rom = load(sys.argv[1] if len(sys.argv) > 1 else ROM_PATH_DEFAULT)
    print(f"size {len(rom):#x}")
