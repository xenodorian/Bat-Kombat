"""Batman Returns frame timing for Batman's shared moves in UMK3 (USA, SNES).

How UMK3 times animation (found with the debugger, see Current_Work.md):
  * Move code steps the animation script with $88:87DD and then sleeps with $88:C637 (A = frames). Display steps
    use small constants (2-6). Holds that decide hit windows and recovery are loops of 1-frame sleeps or one long
    sleep, and are game logic, so they are left alone.
  * The sleep runs on the object's direct page; $2A is the object, $7E:52C8,x its fighter id, $7E:52F8,x its sprite id.

This patch hooks $88:C637. When fighter 24 sleeps 1-63 frames on a set-27 frame listed in ROWS with that original
value, the sleep is replaced by the Batman Returns value (for 1-frame loop sleeps, the loop count is capped).
Everything else is unchanged.
Batman Returns timings (measured with tools/rig/br_actions.py): punch 14 x2, 13 x4, 14 x2; batarang 38 x3, 39 x2,
40 x5, 39 x4; block 63 x3, then 64 held; hit reaction 59 x24; walk 1.75 px per frame, 8 frames per pose.
"""
import struct

import exhirom
from move_list_patch import Asm

SITE = 0x08C637
SITE_BYTES = bytes.fromhex("3a850468")         # dec a / sta $04 / pla
RESUME = 0x88C63B                              # after the pla, which the JML overwrites and the hook does itself
# Walking: $88:96FB / $88:96DC read (pose delay, speed in 1/256 px per frame) for fighter id k at $88:9729 + 4k
# (forward) and $88:9799 + 4k (back). Rain's slot had (5, $340) forward and (5, $240) back. Batman Returns walks
# 1.75 px per frame (camera word $00B2 steps 2, 2, 2, 1) the same speed both ways, 8 frames per pose.
WALK_FWD, WALK_BACK = 0x089729, 0x089799
WALK = (8, 0x01C0)
FIGHTER, SET = 24, 27
# (UMK3 frame, original sleep, Batman Returns sleep). Original sleep 1 is special: those are 1-frame sleeps inside
# a counted loop ($86:8B7E: count in $32, one sleep per frame, the hit test runs each frame), so the row caps the
# loop count $32 at the new value instead.
ROWS = [
    (56, 3, 1), (57, 3, 1), (56, 2, 1), (57, 2, 1),          # high punch: wind-up 2 frames, retract 2 (was 6 and 4)
    (58, 3, 1), (58, 1, 2),                                  # high punch held out 4 frames (was 3 + 5)
    (99, 3, 1), (100, 3, 1), (99, 2, 1), (100, 2, 1),        # low punch, same
    (211, 3, 2), (212, 3, 2), (213, 3, 3),                   # Batarang: 38 x3, 39 x2, then the lunge 40 x5
    (213, 31, 2), (211, 4, 3), (210, 4, 1),                  # lunge ends after 5 frames (was 34), 39 x4, done
    (10, 3, 2),                                              # block: raise the cape in 4 frames (was 6)
    (49, 4, 6), (50, 4, 6),                                  # hit reaction: 24 frames like Batman Returns (was 17)
]


def hook_code(base):
    a = Asm(base)
    a.b(0x08, 0xC2, 0x30, 0xDA)                              # php / rep #$30 / phx
    a.b(0xC9, 0x01, 0x00); a.branch(0x90, "keep")            # cmp #1 / bcc keep
    a.b(0xC9, 0x40, 0x00); a.branch(0xB0, "keep")            # cmp #64 / bcs keep
    a.b(0x85, 0x04)                                          # sta $04 (original value)
    a.b(0xA6, 0x2A, 0xE0, 0x60, 0x00); a.branch(0xB0, "rest")    # ldx $2A / cpx #$60 / bcs rest
    a.b(0xBF, 0xC8, 0x52, 0x7E, 0x29, 0xFF, 0x00, 0xC9, FIGHTER, 0x00); a.branch(0xD0, "rest")
    a.b(0xBF, 0xF8, 0x52, 0x7E, 0x29, 0x00, 0xFE, 0xC9, 0x00, SET << 1); a.branch(0xD0, "rest")
    a.b(0xBF, 0xF8, 0x52, 0x7E, 0x29, 0xFF, 0x01, 0x48)      # lda $7E52F8,x / and #$1FF / pha (frame)
    a.b(0xA2, 0x00, 0x00)                                    # ldx #0
    a.label("loop")
    a.b(0xBF); a.word_of("rows"); a.b(base >> 16)            # lda rows,x (frame)
    a.branch(0xF0, "done")
    a.b(0xC3, 0x01); a.branch(0xD0, "next")                  # cmp 1,s / bne next
    a.b(0xBF); a.word_of("rows2"); a.b(base >> 16)           # lda rows+2,x (original, new)
    a.b(0x29, 0xFF, 0x00, 0xC5, 0x04); a.branch(0xD0, "next")    # and #$FF / cmp $04 / bne next
    a.b(0xBF); a.word_of("rows3"); a.b(base >> 16)           # lda rows+3,x
    a.b(0x29, 0xFF, 0x00)                                    # and #$FF
    a.b(0xA6, 0x04, 0xE0, 0x01, 0x00); a.branch(0xF0, "cap") # ldx $04 / cpx #1 / beq cap
    a.b(0x85, 0x04)                                          # sta $04 (new sleep)
    a.branch(0x80, "done")
    a.label("cap")
    a.b(0xC5, 0x32); a.branch(0xB0, "done")                  # cmp $32 / bcs done (count already small enough)
    a.b(0x85, 0x32)                                          # sta $32
    a.branch(0x80, "done")
    a.label("next")
    a.b(0xE8, 0xE8, 0xE8, 0xE8); a.branch(0x80, "loop")      # inx x4
    a.label("done")
    a.b(0x68)                                                # pla
    a.label("rest")
    a.b(0xA5, 0x04)                                          # lda $04
    a.label("keep")
    a.b(0xFA, 0x28, 0x3A, 0x85, 0x04, 0x68)                  # plx / plp / dec a / sta $04 / pla (the original three)
    a.jml(RESUME)
    a.label("rows")
    rows_at = len(a.out)
    for f, old, new in ROWS:
        a.b(*struct.pack("<HBB", f, old, new))
    a.b(0, 0, 0, 0)
    a.labels["rows2"] = rows_at + 2
    a.labels["rows3"] = rows_at + 3
    return a.done()


def patch(rom, alloc, put):
    """rom: the expanded image. Puts the hook in expanded ROM and patches $88:C637 (and its bank $08 mirror)."""
    assert bytes(rom[SITE:SITE + 4]) == SITE_BYTES, "unexpected bytes at the sleep routine"
    bank, addr = alloc.alloc(224)
    base = bank << 16 | addr
    code = hook_code(base)
    assert len(code) <= 224
    put(bank, addr, code)
    site = bytes([0x5C, addr & 0xFF, addr >> 8, bank])
    rom[SITE:SITE + 4] = site
    rom[exhirom.ORIG_SIZE + SITE:exhirom.ORIG_SIZE + SITE + 4] = site
    for t in (WALK_FWD, WALK_BACK):
        at = t + 4 * FIGHTER
        rom[at:at + 4] = struct.pack("<HH", *WALK)
        rom[exhirom.ORIG_SIZE + at:exhirom.ORIG_SIZE + at + 4] = struct.pack("<HH", *WALK)
    return dict(hook="%02X:%04X" % (bank, addr), rows=len(ROWS))
