"""Show Batman's move list in UMK3 (USA, SNES) before a match that has Batman in it.

The game has no move list screen. It does have a text screen that appears between the VS screen and the
fight when a kombat kode is active (routine at $85:E805). It prints one centred line per active kode with
the text routine at $88:90F8 (A = string address, X = string bank, Y = screen row in pixels), 12 pixels apart,
and stays for 240 frames.

This patch makes that screen also appear when either fighter is Batman (fighter id 24 at $7E:52C8 or $7E:52CA)
and adds the move list lines to it. Two jumps are patched:
  $85:E834  jml $88C7CC (leave, no kode active)   -> jml CHECK
  $85:E8E4  lda $3C0E / beq $E91E (after the kode lines) -> jml PRINT
New code and text go in free space at $FF:DD00 (file 0x3FDD00).
"""
import struct

import batman_moves_patch

CODE_AT = 0x3FDD00                 # $FF:DD00
CODE_END = 0x3FE000
SITE_CHECK, SITE_PRINT = 0x05E834, 0x05E8E4
SITE_CHECK_BYTES = bytes.fromhex("5cccc788")
SITE_PRINT_BYTES = bytes.fromhex("ad0e3cf035")
FIGHTER = 24

_SHORT = {"High Punch": "HIGH PUNCH", "Low Punch": "LOW PUNCH", "High Kick": "HIGH KICK", "Low Kick": "LOW KICK"}


def lines():
    out = ["BATMAN MOVES"]
    for name, keys in batman_moves_patch.MOVE_LIST:
        out.append(("%s: %s" % (name, keys)).upper().replace(" + ", " AND "))
    return out


class Asm:
    """Tiny 65816 assembler: raw bytes plus labels, relative branches and 16-bit label references."""

    def __init__(self, base):
        self.base, self.out, self.labels, self.fix = base, bytearray(), {}, []

    def b(self, *bs):
        self.out += bytes(bs)

    def label(self, name):
        self.labels[name] = len(self.out)

    def branch(self, op, name):
        self.out += bytes([op, 0])
        self.fix.append(("rel", len(self.out) - 1, name))

    def jml(self, addr):
        self.out += bytes([0x5C, addr & 255, (addr >> 8) & 255, addr >> 16])

    def jsl(self, addr):
        self.out += bytes([0x22, addr & 255, (addr >> 8) & 255, addr >> 16])

    def word_of(self, name):
        self.out += b"\0\0"
        self.fix.append(("abs", len(self.out) - 2, name))

    def done(self):
        for kind, at, name in self.fix:
            t = self.labels[name]
            if kind == "rel":
                d = t - (at + 1)
                assert -128 <= d <= 127
                self.out[at] = d & 255
            else:
                struct.pack_into("<H", self.out, at, (self.base + t) & 0xFFFF)
        return bytes(self.out)


def code(base_addr):
    a = Asm(base_addr)
    bank = base_addr >> 16

    def has_batman(yes):
        a.b(0xAD, 0xC8, 0x52, 0xC9, FIGHTER, 0x00)       # lda $52C8 / cmp #24
        a.branch(0xF0, yes)
        a.b(0xAD, 0xCA, 0x52, 0xC9, FIGHTER, 0x00)       # lda $52CA / cmp #24
        a.branch(0xF0, yes)

    a.label("check")
    has_batman("show")
    a.jml(0x88C7CC)
    a.label("show")
    a.jml(0x85E838)

    a.label("print")
    has_batman("go")
    a.branch(0x80, "tail")
    a.label("go")
    a.b(0xA2, 0x00, 0x00)                                # ldx #0
    a.label("loop")
    a.b(0xBF); a.word_of("table"); a.b(bank)             # lda.l table,x
    a.branch(0xF0, "tail")
    a.b(0xDA)                                            # phx
    a.b(0xAC, 0x47, 0x1C)                                # ldy $1C47
    a.b(0xA2, bank, 0x00)                                # ldx #bank
    a.jsl(0x8890F8)
    a.b(0x18, 0xAD, 0x47, 0x1C, 0x69, 0x0C, 0x00, 0x8D, 0x47, 0x1C)   # $1C47 += 12
    a.b(0xFA, 0xE8, 0xE8)                                # plx / inx / inx
    a.branch(0x80, "loop")
    a.label("tail")
    a.b(0xAD, 0x0E, 0x3C)                                # lda $3C0E (replaced instructions)
    a.branch(0xF0, "zero")
    a.jml(0x85E8E9)
    a.label("zero")
    a.jml(0x85E91E)

    text = lines()
    a.label("table")
    for i in range(len(text)):
        a.word_of("s%d" % i)
    a.b(0, 0)
    for i, t in enumerate(text):
        a.label("s%d" % i)
        a.out += t.encode("ascii") + b"\0"
    return a.done(), a.labels


def patch(rom):
    """rom: bytearray of the 4 MB original (apply before the ExHiROM expansion)."""
    base = 0xC00000 | CODE_AT
    blob, labels = code(base)
    assert CODE_AT + len(blob) <= CODE_END
    assert all(b == 0xFF for b in rom[CODE_AT:CODE_AT + len(blob)]), "move list area is not free"
    assert rom[SITE_CHECK:SITE_CHECK + 4] == SITE_CHECK_BYTES and rom[SITE_PRINT:SITE_PRINT + 5] == SITE_PRINT_BYTES
    rom[CODE_AT:CODE_AT + len(blob)] = blob
    for site, name, pad in ((SITE_CHECK, "check", 0), (SITE_PRINT, "print", 1)):
        t = base + labels[name]
        rom[site:site + 4 + pad] = bytes([0x5C, t & 255, (t >> 8) & 255, t >> 16]) + b"\xEA" * pad
    return dict(code="%06X" % base, size=len(blob), lines=lines())
