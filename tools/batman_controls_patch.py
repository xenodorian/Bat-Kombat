"""Batman Returns controls for Batman (fighter id 24) in UMK3 (USA, SNES).

How UMK3 reads the pads (found with the debugger, see Current_Work.md):
  * $80:FDCE "lda $804218" reads pad 1 and $80:FDDC "lda $80421A" reads pad 2. Every later use of the buttons
    (fighters, move matcher, menus) comes from these two values.
  * UMK3 buttons: Y high punch, B low punch, X high kick, A low kick, L block, R run.
  * $7E:3A7E is the screen mode word: 0 during a fight (13 roster, 11 versus screen, 14 the stage intro).
  * Pad 1 plays object 0 (fighter id at $7E:52C8), pad 2 object 2 (fighter id at $7E:52CA).

Batman Returns (measured with tools/rig/br_actions.py): Y punch, B jump, A batarang, L or R cape block, B + Y cape
spin, X and SELECT nothing, Up and Down walk in depth.

While a fight is on and the pad's fighter is Batman, the pad value is rewritten before the game sees it:
  R -> L (block), B + Y -> R (the run button, which carries Cape Charge), B -> Up (jump).
A stays the low kick button, which carries the no-motion Batarang (see batman_moves_patch.py). Y stays high
punch. X stays high kick, so the kick finishers keep a button. The D-pad is unchanged: UMK3 needs Down for
crouching and the directions for special moves, and has no depth.
"""
import exhirom
from move_list_patch import Asm

SITES = {0x00FDCE: (bytes.fromhex("af184280"), 0x804218, 0x7E52C8),     # pad 1
         0x00FDDC: (bytes.fromhex("af1a4280"), 0x80421A, 0x7E52CA)}     # pad 2
FIGHTER = 24
SCREEN_MODE = 0x7E3A7E
B, Y, UP, L, R = 0x8000, 0x4000, 0x0800, 0x0020, 0x0010


def long_op(op, addr):
    return bytes([op, addr & 255, (addr >> 8) & 255, addr >> 16])


def hook_code(base):
    a = Asm(base)
    entries = {}
    for i, (site, (_, port, fid)) in enumerate(sorted(SITES.items())):
        entries[site] = len(a.out)
        a.b(*long_op(0xAF, port))                                  # lda pad
        a.b(0x48)                                                  # pha
        a.b(*long_op(0xAF, fid))                                   # lda fighter id
        a.branch(0x80, "common") if i == 0 else None
    a.label("common")
    a.b(0x29, 0xFF, 0x00, 0xC9, FIGHTER, 0x00); a.branch(0xD0, "out")   # and #$FF / cmp #24 / bne out
    a.b(*long_op(0xAF, SCREEN_MODE)); a.branch(0xD0, "out")              # lda $7E3A7E / bne out
    a.b(0x68)                                                            # pla (pad)
    a.b(0x89, R, 0x00); a.branch(0xF0, "noR")                            # bit #R / beq
    a.b(0x29, 0xFF ^ R, 0xFF, 0x09, L, 0x00)                             # and #~R / ora #L
    a.label("noR")
    a.b(0x48, 0x29, 0x00, 0xC0, 0xC9, 0x00, 0xC0); a.branch(0xD0, "notboth")   # pha / and #B|Y / cmp #B|Y
    a.b(0x68, 0x29, 0xFF, 0x3F, 0x09, R, 0x00, 0x6B)                     # pla / and #~(B|Y) / ora #R / rtl
    a.label("notboth")
    a.b(0x68, 0x89, 0x00, 0x80); a.branch(0xF0, "done")                  # pla / bit #B / beq done
    a.b(0x29, 0xFF, 0x7F, 0x09, 0x00, UP >> 8)                           # and #~B / ora #Up
    a.label("done")
    a.b(0x6B)                                                            # rtl
    a.label("out")
    a.b(0x68, 0x6B)                                                      # pla / rtl
    return a.done(), entries


def patch(rom, alloc, put):
    """rom: the expanded image. Each pad read becomes a JSL to the remap (both the bank $80 and $00 copies)."""
    for site, (orig, _, _) in SITES.items():
        assert bytes(rom[site:site + 4]) == orig, "unexpected bytes at the pad read %06X" % site
    size = 96
    bank, addr = alloc.alloc(size)
    base = bank << 16 | addr
    code, entries = hook_code(base)
    assert len(code) <= size
    put(bank, addr, code)
    for site, off in entries.items():
        t = base + off
        jsl = bytes([0x22, t & 255, (t >> 8) & 255, t >> 16])
        rom[site:site + 4] = jsl
        rom[exhirom.ORIG_SIZE + site:exhirom.ORIG_SIZE + site + 4] = jsl
    return dict(hook="%02X:%04X" % (bank, addr), size=len(code))
