"""65816 linear disassembler with M/X width tracking (REP/SEP followed in order of appearance).

Usage: python3 -I dis65.py ROM BANK:ADDR LENGTH [m x]   e.g. dis65.py rom.sfc 83:8000 0x200 16 16
HiROM mapping: file = ((bank & 0x3F) << 16) | addr. Tracking is linear, so a branch target reached with
different flag state can decode wrong; restart from that address with explicit widths when that happens.
"""
import sys
from capstone import (Cs, CS_ARCH_MOS65XX, CS_MODE_MOS65XX_65816_LONG_M,
                      CS_MODE_MOS65XX_65816_LONG_X, CS_MODE_MOS65XX_65816_LONG_MX)

_MX = Cs(CS_ARCH_MOS65XX, CS_MODE_MOS65XX_65816_LONG_MX)
_M16 = Cs(CS_ARCH_MOS65XX, CS_MODE_MOS65XX_65816_LONG_M)    # 16-bit A, 8-bit index
_X16 = Cs(CS_ARCH_MOS65XX, CS_MODE_MOS65XX_65816_LONG_X)    # 8-bit A, 16-bit index
_IMM_M = {0x09, 0x29, 0x49, 0x69, 0x89, 0xA9, 0xC9, 0xE9}
_IMM_X = {0xA0, 0xA2, 0xC0, 0xE0}


def _decoder(op, m, x):
    """Only immediate operands depend on the register widths."""
    if op in _IMM_M and m == 8:
        return _X16
    if op in _IMM_X and x == 8:
        return _M16
    return _MX


def disasm(rom, bank, addr, length, m=16, x=16):
    off = ((bank & 0x3F) << 16) | addr
    end = off + length
    out = []
    while off < end:
        ins = next(_decoder(rom[off], m, x).disasm(bytes(rom[off:off + 4]), off & 0xFFFF, 1), None)
        if ins is None:
            out.append("%02X:%04X  %02x           .db" % (bank, off & 0xFFFF, rom[off]))
            off += 1
            continue
        out.append("%02X:%04X  %-12s %s %s" % (bank, ins.address, ins.bytes.hex(" "), ins.mnemonic, ins.op_str))
        b = ins.bytes
        if b[0] == 0xC2:      # REP
            if b[1] & 0x20: m = 16
            if b[1] & 0x10: x = 16
        elif b[0] == 0xE2:    # SEP
            if b[1] & 0x20: m = 8
            if b[1] & 0x10: x = 8
        off += len(b)
    return "\n".join(out)


if __name__ == "__main__":
    rom = open(sys.argv[1], "rb").read()
    bank, addr = [int(v, 16) for v in sys.argv[2].split(":")]
    m, x = (int(sys.argv[4]), int(sys.argv[5])) if len(sys.argv) > 5 else (16, 16)
    print(disasm(rom, bank, addr, int(sys.argv[3], 0), m, x))
