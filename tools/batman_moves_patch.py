"""Give Batman (Rain's slot, fighter id 24) his own special moves in UMK3 (USA, SNES).

How the game stores special moves (found with the debugger, see Current_Work.md):
  * One pointer table per attack button in bank $82, each indexed by fighter id * 2:
      HP $82:BAC9   LP $82:BB01   BLOCK $82:BB39   HK $82:BB71   LK $82:BBA9   RUN $82:BA91
    An entry points to a stub "lda #table / jmp $D764". A zero entry means no specials on that button.
  * A move table is a list of 21-byte records ended by a zero word:
      +0  word  button state offset ($30 HP, $32 LP, $34 BLOCK, $36 HK, $38 LK, $3A RUN)
      +2  word  kind: 0 ground special, 1 special also allowed in the air, 2 fatality, 6 and 7 other finishers
      +4  word  condition routine in bank $82 (0 = none); carry set means the move is allowed
      +6  word  handler in bank $82
      +8  byte  time window in frames
      +9  6 bytes  direction codes, newest first, zero padded (6 up, 7 down, 8 left, 9 right), facing right
      +15 6 bytes  the same sequence mirrored, for facing left
  * The matcher is at $82:D75E. Handlers are shared: any male ninja can run any other male ninja's move,
    because all of them use sprite set 27 with the same frame numbers. Moves of other body types break.

This patch writes new tables for fighter 24 and points the HP, LP and LK entries at them.
Rain's two old tables ($82:EA7C, $82:EA93) and the free bytes at $82:FF0B are reused for the new data.
"""
import struct

BANK = 0x020000                      # file offset of bank $82
HP_TABLE, LP_TABLE, LK_TABLE = 0xBAC9, 0xBB01, 0xBBA9
RAIN = 24
OLD_LK, OLD_HP = 0xEA7C, 0xEA93      # Rain's original tables (1 and 3 records)
FREE, FREE_END = 0xFF0B, 0xFF71      # 0xFF padding at the end of bank $82
HP_STUB, LK_STUB = 0xBD3E, 0xBD44    # Rain's existing stubs

HP, LP, BLOCK, HK, LK, RUN = 0x30, 0x32, 0x34, 0x36, 0x38, 0x3A
_CODE = {"U": 6, "D": 7, "L": 8, "R": 9}        # L = back, R = forward when facing right
_MIRROR = {"U": "U", "D": "D", "L": "R", "R": "L"}

# name, button, kind, condition, handler, window, sequence (press order, facing right; B = back, F = forward)
MOVES = [
    ("Batarang",        HP, 0, 0x0000, 0xC99B, 0x18, "DR"),    # Reptile's spit handler, projectile redrawn
    ("Smoke Teleport",  HP, 1, 0xDCC9, 0xC883, 0x18, "DL"),    # Scorpion's teleport punch
    ("Grapple Gun",     LP, 0, 0xDD1A, 0xC9A2, 0x14, "LL"),    # Scorpion's spear
    ("Explosive",       LP, 0, 0x0000, 0xC9DA, 0x18, "DL"),    # Ermac's fireball
    ("Cape Charge",     LK, 0, 0x0000, 0xC88A, 0x14, "LR"),    # Reptile's dash
]
# Not table driven, already present for fighter 24: Super Roundhouse (back + high kick), handled at $85:AF02.

MOVE_LIST = [
    ("Batarang", "Down, Forward, High Punch"),
    ("Smoke Teleport", "Down, Back, High Punch"),
    ("Grapple Gun", "Back, Back, Low Punch"),
    ("Explosive", "Down, Back, Low Punch"),
    ("Cape Charge", "Back, Forward, Low Kick"),
    ("Spin Kick", "Back + High Kick"),
]


def record(button, kind, cond, handler, window, seq):
    a = bytes(_CODE[c] for c in reversed(seq)).ljust(6, b"\0")
    b = bytes(_CODE[_MIRROR[c]] for c in reversed(seq)).ljust(6, b"\0")
    return struct.pack("<HHHHB", button, kind, cond, handler, window) + a + b


def patch(rom):
    """rom: bytearray of the 4 MB original (apply before the ExHiROM expansion)."""
    w = lambda o: rom[o] | rom[o + 1] << 8
    assert w(BANK + HP_TABLE + 2 * RAIN) == HP_STUB and w(BANK + LK_TABLE + 2 * RAIN) == LK_STUB, "unexpected stubs"
    assert w(BANK + LP_TABLE + 2 * RAIN) == 0, "fighter 24 already has low-punch specials"
    assert rom[BANK + HP_STUB:BANK + HP_STUB + 6] == bytes([0xA9, OLD_HP & 255, OLD_HP >> 8, 0x4C, 0x64, 0xD7])
    assert all(b == 0xFF for b in rom[BANK + FREE:BANK + FREE_END]), "free area in bank $82 is in use"
    old_finisher = bytes(rom[BANK + OLD_HP + 21:BANK + OLD_HP + 42])     # kind 7 record, kept as it is
    old_stage = bytes(rom[BANK + OLD_LK:BANK + OLD_LK + 21])             # stage fatality record, kept
    assert struct.unpack_from("<H", old_finisher, 2)[0] == 7 and struct.unpack_from("<H", old_stage, 6)[0] == 0xC727

    tables = {HP: b"", LP: b"", LK: b""}
    for _, button, kind, cond, handler, window, seq in MOVES:
        tables[button] += record(button, kind, cond, handler, window, seq)
    tables[HP] += old_finisher
    tables[LK] += old_stage
    for k in tables:
        tables[k] += b"\0\0"

    # HP table goes over Rain's two old tables; LP and LK tables and the LP stub go in the free area
    assert len(tables[HP]) <= OLD_HP + 3 * 21 + 2 - OLD_LK
    hp_at = OLD_LK
    lp_at = FREE
    lk_at = lp_at + len(tables[LP])
    lp_stub = lk_at + len(tables[LK])
    assert lp_stub + 6 <= FREE_END
    rom[BANK + hp_at:BANK + hp_at + len(tables[HP])] = tables[HP]
    rom[BANK + lp_at:BANK + lp_at + len(tables[LP])] = tables[LP]
    rom[BANK + lk_at:BANK + lk_at + len(tables[LK])] = tables[LK]
    rom[BANK + lp_stub:BANK + lp_stub + 6] = bytes([0xA9, lp_at & 255, lp_at >> 8, 0x4C, 0x64, 0xD7])
    struct.pack_into("<H", rom, BANK + HP_STUB + 1, hp_at)
    struct.pack_into("<H", rom, BANK + LK_STUB + 1, lk_at)
    struct.pack_into("<H", rom, BANK + LP_TABLE + 2 * RAIN, lp_stub)
    return dict(hp_table=hp_at, lp_table=lp_at, lk_table=lk_at, lp_stub=lp_stub)
