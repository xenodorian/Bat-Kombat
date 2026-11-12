"""Give Batman (Rain's slot, fighter id 24) his own special moves and finishers in UMK3 (USA, SNES).

How the game stores special moves (found with the debugger, see Current_Work.md):
  * One pointer table per attack button in bank $82, each indexed by fighter id * 2:
      HP $82:BAC9   LP $82:BB01   BLOCK $82:BB39   HK $82:BB71   LK $82:BBA9   RUN $82:BA91
    An entry points to a stub "lda #table / jmp $D764". A zero entry means no specials on that button.
  * A move table is a list of 21-byte records ended by a zero word:
      +0  word  button state offset ($30 HP, $32 LP, $34 BLOCK, $36 HK, $38 LK, $3A RUN); the move is refused
                while any other attack button is held
      +2  word  kind: 0 ground special, 1 special also allowed in the air, 2 fatality, 6 friendship, 7 babality
      +4  word  condition routine in bank $82 (0 = none); carry set means the move is allowed
      +6  word  handler in bank $82
      +8  byte  time window in frames
      +9  6 bytes  direction codes, newest first, zero padded (6 up, 7 down, 8 left, 9 right), facing right
      +15 6 bytes  the same sequence mirrored, for facing left
  * The matcher is at $82:D75E. It reads the table and the sequences from bank $82 only.
  * Handlers are shared: any male ninja can run any other male ninja's move, because all of them use sprite
    set 27 with the same frame numbers. Moves of other body types break.
  * Fatality handlers $82:8011 (first) and $82:801F (second) jump through tables indexed by fighter id * 2
    at $82:802D and $82:8065. Fighter 24 has no fatality there in the original ($8000 = none).

Bank $82 has almost no free space, so this patch puts a copy of the matcher and one table holding all of
Batman's records in bank $FF. Every button entry of fighter 24 points to one 4-byte stub in bank $82
(written over Rain's old table at $82:EA7C) that jumps to the copy. Records for a button other than the one
pressed are refused by the game's own "no other attack button held" test.
"""
import struct

BANK = 0x020000                      # file offset of bank $82
BUTTON_TABLES = {0x30: 0xBAC9, 0x32: 0xBB01, 0x34: 0xBB39, 0x36: 0xBB71, 0x38: 0xBBA9, 0x3A: 0xBA91}
RAIN = 24
OLD_LK, OLD_HP = 0xEA7C, 0xEA93      # Rain's original tables (1 and 3 records)
STUB = OLD_LK                        # the new stub goes over the old tables
CODE_AT, CODE_END = 0x3FE000, 0x3FE400   # $FF:E000, 0xFF padding in the original
FATALITY_1, FATALITY_2 = 0x802D, 0x8065  # per-fighter jump tables in bank $82

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
# Finishers. Kind 2 runs $82:8011 / $82:801F, which jump through the per-fighter tables patched below.
# Condition $D4BF = standing close to the opponent.
FINISHERS = [
    ("Fatality 1", HK, 2, 0xD4BF, 0x8011, 0x30, "DDR"),
    ("Fatality 2", LP, 2, 0xD4BF, 0x801F, 0x30, "RRD"),
    ("Friendship", LK, 6, 0xD5B7, 0xF2D1, 0x30, "LRR"),
]
FATALITY_1_ROUTINE = 0x842E          # Ermac's second fatality: uppercut that takes the head off
FATALITY_2_ROUTINE = 0x8471          # Ermac's first fatality: lift and slam until the opponent bursts

# Not table driven, already present for fighter 24: Super Roundhouse (back + high kick), handled at $85:AF02.

MOVE_LIST = [
    ("Batarang", "Down, Forward, High Punch"),
    ("Smoke Teleport", "Down, Back, High Punch"),
    ("Grapple Gun", "Back, Back, Low Punch"),
    ("Explosive", "Down, Back, Low Punch"),
    ("Cape Charge", "Back, Forward, Low Kick"),
    ("Spin Kick", "Back + High Kick"),
    ("Fatality 1", "Down, Down, Forward, High Kick"),
    ("Fatality 2", "Forward, Forward, Down, Low Punch"),
    ("Babality", "Forward, Back, Back, High Punch"),
    ("Friendship", "Back, Forward, Forward, Low Kick"),
]


def record(button, kind, cond, handler, window, seq):
    a = bytes(_CODE[c] for c in reversed(seq)).ljust(6, b"\0")
    b = bytes(_CODE[_MIRROR[c]] for c in reversed(seq)).ljust(6, b"\0")
    return struct.pack("<HHHHB", button, kind, cond, handler, window) + a + b


def matcher(base, table_addr):
    """Copy of the matcher at $82:D75E that reads its table from the bank of `base`."""
    from move_list_patch import Asm
    bank = base >> 16
    a = Asm(base)
    a.b(0xA9, table_addr & 255, table_addr >> 8, 0x85, 0x42)        # lda #table / sta $42
    a.branch(0x80, "common")
    a.label("next")
    a.b(0x18, 0xA5, 0x42, 0x69, 0x15, 0x00, 0x85, 0x42)             # $42 += 21
    a.label("common")
    a.b(0xA9, bank, 0x00, 0x85, 0x44)                               # lda #bank / sta $44
    a.jsl(0x81A585)
    a.branch(0xB0, "exit")
    a.b(0xA7, 0x42)                                                 # lda [$42]
    a.branch(0xF0, "exit")
    a.b(0xAA, 0xA0, 0x08, 0x00, 0xB7, 0x42, 0x29, 0xFF, 0x00)       # tax / ldy #8 / lda [$42],y / and #$FF
    a.branch(0xF0, "skipseq")
    a.b(0x18, 0xA5, 0x42, 0x69, 0x08, 0x00, 0x85, 0x36)             # $36 = $42 + 8
    a.b(0xA9, bank, 0x00, 0x85, 0x38)                               # $38 = bank
    a.jsl(0x82CFFD)                                                 # sequence test, entered after its bank setup
    a.branch(0x90, "next")
    a.label("skipseq")
    a.b(0xA0, 0x04, 0x00, 0xB7, 0x42)                               # ldy #4 / lda [$42],y
    a.branch(0xF0, "run")
    a.b(0x8D, 0x00, 0x1A, 0xA9, 0x82, 0x00, 0x8D, 0x02, 0x1A)       # condition routine address at $1A00
    a.jsl(0x88C7E1)
    a.branch(0x90, "next")
    a.label("run")
    a.b(0xA0, 0x02, 0x00, 0xB7, 0x42, 0x0A, 0xAA)                   # x = kind * 2
    a.b(0xE2, 0x20, 0xA9, 0x82, 0x48, 0xC2, 0x20)                   # push bank $82
    a.b(0xBF, 0x87, 0xD3, 0x82, 0x3A, 0x48)                         # lda $82D387,x / dec / pha
    a.b(0xA0, 0x06, 0x00, 0xB7, 0x42)                               # a = handler
    a.b(0x6B)                                                       # rtl = jump to the kind routine
    a.label("exit")
    a.b(0x6B)
    return a.done()


def patch(rom):
    """rom: bytearray of the 4 MB original (apply before the ExHiROM expansion)."""
    w = lambda o: rom[o] | rom[o + 1] << 8
    assert w(BANK + BUTTON_TABLES[HP] + 2 * RAIN) == 0xBD3E and w(BANK + BUTTON_TABLES[LK] + 2 * RAIN) == 0xBD44
    assert w(BANK + FATALITY_1 + 2 * RAIN) == 0x8000 and w(BANK + FATALITY_2 + 2 * RAIN) == 0x8000
    old_baby = bytes(rom[BANK + OLD_HP + 21:BANK + OLD_HP + 42])         # babality record, kept as it is
    old_stage = bytes(rom[BANK + OLD_LK:BANK + OLD_LK + 21])             # stage fatality record, kept
    assert struct.unpack_from("<H", old_baby, 2)[0] == 7 and struct.unpack_from("<H", old_stage, 6)[0] == 0xC727

    table = b"".join(record(*m[1:]) for m in MOVES + FINISHERS) + old_baby + old_stage + b"\0\0"
    base = 0xC00000 | CODE_AT
    code = matcher(base, 0)
    table_addr = (CODE_AT + len(code)) & 0xFFFF
    code = matcher(base, table_addr)
    blob = code + table
    assert CODE_AT + len(blob) <= CODE_END
    assert all(b == 0xFF for b in rom[CODE_AT:CODE_AT + len(blob)]), "move table area is not free"
    rom[CODE_AT:CODE_AT + len(blob)] = blob
    rom[BANK + STUB:BANK + STUB + 4] = bytes([0x5C, base & 255, (base >> 8) & 255, base >> 16])   # jml matcher
    for button in {m[1] for m in MOVES + FINISHERS} | {HP, LK}:
        struct.pack_into("<H", rom, BANK + BUTTON_TABLES[button] + 2 * RAIN, STUB)
    struct.pack_into("<H", rom, BANK + FATALITY_1 + 2 * RAIN, FATALITY_1_ROUTINE)
    struct.pack_into("<H", rom, BANK + FATALITY_2 + 2 * RAIN, FATALITY_2_ROUTINE)
    return dict(matcher="%06X" % base, table="%04X" % table_addr, records=len(table) // 21)
