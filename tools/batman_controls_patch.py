"""Batman Returns controls for Batman (fighter id 24) in UMK3 (USA, SNES).

How UMK3 reads the pads (found with the debugger, see Current_Work.md):
  * $80:FDCE "lda $804218" reads pad 1 and $80:FDDC "lda $80421A" reads pad 2. Every later use of the buttons
    (fighters, move matcher, menus) comes from these two values. The routine then stores, per pad (X = 0 / 2):
    $3668,x the value it read (after its own Up+Down and Left+Right clean-up), $3670,x the previous value
    after the input mask $366C,x, $3674,x the newly pressed buttons, $3662,x the held buttons.
  * UMK3 buttons: Y high punch, B low punch, X high kick, A low kick, L block, R run.
  * $7E:36C0 is the game state: 2 while a round is live (also during FINISH HIM), 7 the ROUND n / FIGHT intro,
    5 round over, 6 the tower and move list screens, 3 match over, 9 roster, 4 and 13 attract and title.
    The game's own pause code ($88:A86E) tests $36C0 == 2.
  * $7E:3A7E is NOT a screen mode: it is the stage (background) number. $80:84C8 sets it from $3A84 when a
    round is set up (5 when $3A84 is 0). The first version of this patch tested $3A7E == 0, which held only on
    the first stage of a match; from round 2 on (stage 5) the remap was off and R was the run button again,
    which fires Batman's no-motion Cape Charge. That was the owner's "R alone does the Cape Charge".
  * Pad 1 always plays the left fighter (object 0, fighter id at $7E:52C8) and pad 2 the right one (object 2,
    $7E:52CA): checked in two-player fights and in one-player games started on pad 1 or on pad 2.

Batman Returns (measured with tools/rig/br_actions.py): Y punch, B jump, A batarang, L or R cape block, B + Y cape
spin, X and SELECT nothing, Up and Down walk in depth.

While $36C0 is 2, 5 or 7 and the pad's fighter is Batman, the pad value is rewritten before the game sees it:
  * R -> L (block).
  * B + Y -> R (the run button, which carries Cape Charge as a no-motion record, batman_moves_patch.py).
    Once the combination is made, R stays held until both B and Y are released, so letting go of one of
    them a frame early does not start a punch.
  * B or Y pressed alone is held back for up to WINDOW frames. If the other one arrives in that time, the
    pair counts as B + Y; otherwise the punch is reported WINDOW frames late (or on release, for a shorter
    tap). Without this, pressing B a frame before Y gave a low punch and no Cape Charge.
B is left as low punch. Jump stays Up on the D-pad, so a combo can still use low punch.
A stays the low kick button, which carries the no-motion Batarang (see batman_moves_patch.py). Y stays high
punch. X stays high kick, so the kick finishers keep a button. The D-pad is unchanged: UMK3 needs Down for
crouching and the directions for special moves, and has no depth.

Work RAM used (never read or written by the game in attract, menus, a 1P ladder and 2P fights, checked with
watches; $1CF8 is the sound patch's): $7E:1CF0 pad 1 and $7E:1CF2 pad 2 hold-back state (high byte: the held
back B/Y bits, low byte: frames held), $7E:1CF4 scratch. Cleared whenever the remap is off.
"""
import exhirom
from move_list_patch import Asm

SITES = {0x00FDCE: bytes.fromhex("af184280"),     # pad 1: lda $804218
         0x00FDDC: bytes.fromhex("af1a4280")}     # pad 2: lda $80421A
FIGHTER = 24
GAME_STATE = 0x7E36C0
LIVE_STATES = (2, 7, 5)
FIGHTER_ID = 0x7E52C8          # ,x with x = 0 (pad 1) or 2 (pad 2)
PAD_PORT = 0x804218            # ,x
LAST_READ = 0x7E3668           # ,x the value this routine stored on the previous frame
STATE = 0x7E1CF0               # ,x
SCRATCH = 0x7E1CF4
WINDOW = 3
B, Y, L, R = 0x8000, 0x4000, 0x0020, 0x0010
BY = B | Y


def long_op(op, addr):
    return bytes([op, addr & 255, (addr >> 8) & 255, addr >> 16])


def imm(op, v):
    return bytes([op, v & 255, v >> 8])


def hook_code(base, window=None):
    window = WINDOW if window is None else window
    a = Asm(base)
    entries = {}
    for i, site in enumerate(sorted(SITES)):
        entries[site] = len(a.out)
        a.b(0xDA, 0xA2, 2 * i, 0x00)                                # phx / ldx #pad*2
        if i == 0:
            a.branch(0x80, "common")
    a.label("common")
    a.b(0x5A)                                                       # phy
    a.b(*long_op(0xBF, PAD_PORT), 0xA8)                             # lda $804218,x / tay
    a.b(*long_op(0xAF, GAME_STATE))                                 # lda $7E36C0
    for k, s in enumerate(LIVE_STATES):
        a.b(*imm(0xC9, s))                                          # cmp #state
        a.branch(0xF0, "on") if k < len(LIVE_STATES) - 1 else a.branch(0xD0, "off")
    a.label("on")
    a.b(*long_op(0xBF, FIGHTER_ID), *imm(0x29, 0xFF), *imm(0xC9, FIGHTER))   # lda id,x / and #$FF / cmp #24
    a.branch(0xD0, "off")
    a.b(0x98, *imm(0x89, 0x000F)); a.branch(0xD0, "off")            # tya / bit #$F: not a standard pad
    a.b(*imm(0x89, R)); a.branch(0xF0, "noR")                       # R -> L
    a.b(*imm(0x29, 0xFFFF ^ R), *imm(0x09, L))
    a.label("noR")
    a.b(0xA8, *imm(0x29, BY)); a.branch(0xF0, "none")               # tay / and #B|Y / beq none
    a.b(*imm(0xC9, BY)); a.branch(0xF0, "combo")                    # both held
    a.b(*long_op(0x8F, SCRATCH))                                    # sta scratch (the one button held)
    a.b(*long_op(0xBF, LAST_READ), *imm(0x89, R))                   # combination still held from before
    a.branch(0xD0, "combo")
    a.b(*long_op(0x2F, SCRATCH)); a.branch(0xD0, "pass")            # already reported as held: pass
    if window:
        a.b(*long_op(0xBF, STATE), *imm(0x29, 0xFF), *imm(0xC9, window))   # frames held back so far
        a.branch(0xB0, "pass")                                     # window over: report the press now
        a.b(0x1A, *long_op(0x0F, SCRATCH), *long_op(0x9F, STATE))   # inc / ora scratch / sta state,x
        a.b(0x98, *long_op(0x4F, SCRATCH))                          # tya / eor scratch: hide the button
        a.branch(0x80, "ret")
    else:
        a.branch(0x80, "pass")
    a.label("combo")
    a.b(0x98, *imm(0x29, 0xFFFF ^ BY), *imm(0x09, R), 0xA8)         # tya / and #~(B|Y) / ora #R / tay
    a.branch(0x80, "pass")
    a.label("none")
    a.b(*long_op(0xBF, STATE), *imm(0x29, BY)); a.branch(0xF0, "pass")   # a held-back tap was released:
    a.b(*long_op(0x8F, SCRATCH), 0x98, *long_op(0x0F, SCRATCH), 0xA8)    # report its press on this frame
    a.label("pass")
    a.label("off")
    a.b(*imm(0xA9, 0), *long_op(0x9F, STATE), 0x98)                 # lda #0 / sta state,x / tya
    a.label("ret")
    a.b(0x7A, 0xFA, 0x6B)                                           # ply / plx / rtl
    return a.done(), entries


def patch(rom, alloc, put):
    """rom: the expanded image. Each pad read becomes a JSL to the remap (both the bank $80 and $00 copies)."""
    for site, orig in SITES.items():
        assert bytes(rom[site:site + 4]) == orig, "unexpected bytes at the pad read %06X" % site
    size = 192
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
    return dict(hook="%02X:%04X" % (bank, addr), size=len(code), window=WINDOW, ram="7E:1CF0-7E:1CF5")
