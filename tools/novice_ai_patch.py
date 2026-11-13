"""Slower CPU opponents on the Novice tower of Ultimate Mortal Kombat 3 (USA, SNES).

What "Novice" is (found 2026-11-13, see Current_Work.md):
  * The game has two settings. The OPTIONS screen sets DIFFICULTY LEVEL (Very Easy, Easy, Medium, Hard, Very Hard)
    in $7E:3A8C (0-4, default 2 written at $80:8440). "Choose your destiny" picks the tower: Novice, Warrior,
    Master and a fourth, tallest one that is also labelled MASTER. $86:91BA stores the tower in $7E:3A94 (0-3)
    and $86:9ECC sets the AI skill level $7E:3A8A from it (0-3, table $86:9EE4). Novice is tower 0, so
    $7E:3A94 = 0. There is no "Novice" difficulty in OPTIONS.
  * The AI reads only the skill level $7E:3A8A (0-9) during a fight. After each fight $85:A8D0 raises it by 1 when
    the player won and lowers it by 1 when the player lost, with a floor from the table at $85:A944
    [options difficulty][tower] (Medium on Novice: floor 1). So on the Novice tower the level climbs one step per
    win, and the options difficulty only sets that floor. $3A8C was not read in 1200 frames of a fight (read
    watch), nor from the tower choice to the fight.
  * Levels feed the AI as chances: $81:B7CA reads a 10-word table (one word per level) and $80:FEFB rolls it
    (carry set with probability word/1024).

How the CPU fighter thinks (found with tools/dbg_core.py: write watch on P1 health and on the CPU thread's $78,
exec watch on every jump and call in bank $81):
  * A fighter runs in its own game thread (often direct page $0800 for the CPU when the human is P1; the thread
    can be restarted on another page). Field $78 is the current action: $01xx attacks (normal and special),
    $03xx stance, walk, crouch, jump, $05xx being hit, $06xx attack recovery, $07xx block. Field $7C bit 0 is set
    for a human, field $68 is the opponent thread's direct page.
  * Every time a fighter is back in its stance it passes $82:BA4B. A human goes to $86:8133 (pad control); the CPU
    goes through `jml $81:ACAC` at $82:BA71 into the AI. $81:ACAC sets the stance ($81:ACBC `jsl $88:96A3`,
    action $0303), turns to face the opponent ($81:ACC0), then decides the next action (walk, jump, attack, block,
    wait) by distance, level chances and random choices ($81:B805), runs it, and comes back to $82:BA4B.
  * A hit does not go through the AI: the attacker's thread redirects the victim's thread (resume address $26/$28,
    set by $85:C6CC from the table at $81:801B) to a hit reaction that sets action $05xx.
  * While the CPU walks or waits, its loops call $81:C171 every frame. $81:C171 compares the opponent's action
    (opponent thread field $78, read by $85:BD66) with the last one it saw ($66). On a change it jumps to a
    reaction routine from the table at $81:C227 (by action group, then action), which can block, jump or
    counter-attack the same frame. This is why the CPU seems to read the player's buttons.
  * The game's own stand-still loop is $81:B3A4 (count in $32, per frame: stance animation $88:8C2B, reaction
    check $81:C171, $86:8C42, facing check $86:8DCC, one-frame sleep $88:C637). $81:B389 uses it for a random
    48-175 frame pause.

What this patch does (only when $7E:3A94 = 0, the Novice tower; every other tower runs the original code):
  1. $81:ACBC `jsl $88:96A3` becomes a jml to new code that sets the stance as before and then stands still for a
     random WAIT_MIN to WAIT_MIN + WAIT_RANGE - 1 frames with the body of the game's own stand-still loop (stance
     animation, reaction check, facing check, one-frame sleep), then resumes the decision at $81:ACC0. If the
     fighter faces the wrong way the pause ends at once and the AI turns around as before.
     The first version hooked $82:BA71 instead and paused before the stance was set (action $0000): a hit taken
     during that pause left the fight without fighters on screen (soft lock, seen with tools/rig/cpu_attack_rate.py
     scripted input). The pause must run with the stance set, like the game's own pauses inside the AI. The code
     enters and leaves by jml and keeps nothing on the hardware stack across the sleep, because a sleeping thread
     keeps only its resume address.
  2. $81:C186 (`sta $66 / ldx $2A`, right after a new opponent action is seen) becomes a jml to new code that
     reacts only with probability REACT_CHANCE/1024; otherwise the new action is marked as seen and $81:C171
     returns, so the CPU no longer answers most of the player's moves on the same frame.
  Both apply to every CPU fighter, Batman included, at every AI level. No RAM is added: the pause counter is $32 of
  the CPU thread's direct page, which the game's own pause loop uses the same way.
  On the other towers the new code only runs its tower test (a few cycles from the slow expanded ROM) and the
  Novice-only instructions never execute (exec watch, Warrior and Master). Runs from one saved state are therefore
  not frame-identical to a build without the patch (one-frame shifts after about 145 frames), but the attack and
  damage rates match. $7E:3A94 is also 0 after a Novice game in modes this patch was not checked in (4 player
  2 on 2, 8 player tournament) if they have CPU fighters.
Measured with tools/rig/cpu_attack_rate.py (numbers in Current_Work.md).
"""
import exhirom
from move_list_patch import Asm

THINK_SITE = 0x01ACBC                          # $81:ACBC, inside the AI decision $81:ACAC
THINK_BYTES = bytes.fromhex("22a39688")        # jsl $88:96A3 (stance: action $78 = $0303)
STANCE = 0x8896A3
THINK_RESUME = 0x81ACC0                        # jsr $AED0 (turn to face the opponent), then the decision
REACT_SITE = 0x01C186                          # $81:C186
REACT_BYTES = bytes.fromhex("8566a62a")        # sta $66 / ldx $2A
REACT_RESUME = 0x81C18A                        # lda $52C8,x
TOWER = 0x7E3A94                               # 0 = Novice

WAIT_MIN, WAIT_RANGE = 210, 270              # pause before each AI decision: 210-479 frames (3.5-8 s)
REACT_CHANCE = 256                             # react to 1 in 4 new opponent actions (1/1024 units)


def hook_code(base):
    a = Asm(base)
    # think: pause on Novice, then the AI
    a.label("think")
    a.jsl(STANCE)                                                     # the instruction the jml replaced
    a.b(0xAF, TOWER & 0xFF, (TOWER >> 8) & 0xFF, TOWER >> 16)       # lda $7E3A94
    a.branch(0xD0, "go")                                              # not Novice
    a.b(0xA9, WAIT_RANGE & 0xFF, WAIT_RANGE >> 8)                     # lda #range
    a.b(0xA2, WAIT_MIN & 0xFF, WAIT_MIN >> 8)                         # ldx #min
    a.jsl(0x80FEF0)                                                   # A = min + random(0 .. range-1)
    a.b(0x85, 0x32)                                                   # sta $32
    a.label("loop")
    a.jsl(0x888C2B)                                                   # stance animation
    a.jsl(0x81C171)                                                   # reactions to the opponent
    a.jsl(0x868C42)
    a.jsl(0x868DCC)                                                   # carry clear: facing the wrong way
    a.branch(0x90, "go")
    a.b(0xA9, 0x01, 0x00)                                             # lda #1
    a.jsl(0x88C637)                                                   # sleep one frame
    a.b(0xC6, 0x32)                                                   # dec $32
    a.branch(0xD0, "loop")
    a.label("go")
    a.jml(THINK_RESUME)
    # react: on Novice, answer a new opponent action only with probability REACT_CHANCE/1024
    a.label("react")
    a.b(0x85, 0x66)                                                   # sta $66 (seen)
    a.b(0xAF, TOWER & 0xFF, (TOWER >> 8) & 0xFF, TOWER >> 16)       # lda $7E3A94
    a.branch(0xD0, "resume")
    a.b(0xA9, REACT_CHANCE & 0xFF, REACT_CHANCE >> 8)                 # lda #chance
    a.jsl(0x80FEFB)                                                   # carry set: react
    a.branch(0xB0, "resume")
    a.b(0x6B)                                                         # rtl: ignore it, back to $81:C171's caller
    a.label("resume")
    a.b(0xA6, 0x2A)                                                   # ldx $2A
    a.jml(REACT_RESUME)
    return a.done(), a.labels["think"], a.labels["react"]


def patch(rom, alloc, put):
    """rom: the expanded image. New code in expanded ROM; patches $82:BA71 and $81:C186 and their bank $00-$3F mirrors."""
    for site, want in ((THINK_SITE, THINK_BYTES), (REACT_SITE, REACT_BYTES)):
        assert bytes(rom[site:site + 4]) == want, "unexpected bytes at %06X" % site
    size = len(hook_code(0)[0])
    bank, addr = alloc.alloc(size)
    code, think, react = hook_code(bank << 16 | addr)
    put(bank, addr, code)
    for site, off in ((THINK_SITE, think), (REACT_SITE, react)):
        t = addr + off
        jml = bytes([0x5C, t & 0xFF, t >> 8, bank])
        rom[site:site + 4] = jml
        rom[exhirom.ORIG_SIZE + site:exhirom.ORIG_SIZE + site + 4] = jml
    return dict(hook="%02X:%04X" % (bank, addr), size=size, wait=(WAIT_MIN, WAIT_MIN + WAIT_RANGE - 1),
                react_chance=REACT_CHANCE)
