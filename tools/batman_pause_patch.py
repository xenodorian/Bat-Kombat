"""Pause with Batman's move list on screen: START during a fight that has Batman in it (UMK3 USA, SNES).

What START does in an unmodified fight (found with the debugger, see Current_Work.md 2026-11-13 "START pause"):
  * The main loop at $88:A863 has a pause: `lda $3C12 / beq $A8BD`, then `$36C0 == 2` (a fight is running) and
    START held on either pad ($7E:3662 | $7E:3664, bit $1000). It sets $3A68 = 1, saves the frame counter $1A0E in
    $1A10 and busy-waits on the frame counter (jsr $A90F) for START released, pressed, released; $88:A8B4 puts
    $1A0E back and clears $3A68. All game threads run from this loop, so nothing moves while it waits; the V-IRQ
    ($80:8738, line $D7) keeps running (pads, button events, OAM, PPU registers from shadows).
  * $3C12 is only set by the "GAME PAUSE ENABLED" kombat kode (kode table $85:EA3E). Without the kode, START does
    nothing in a fight (measured on the original ROM: positions and timer keep running). Poking $3C12 = 1 makes
    START freeze the fight and a second START resume it, with no text on screen.
  * Button presses also become events: the IRQ pushes them on a stack at $7E:3556 ($88:ACA8), the main loop pops
    them at $88:A8E8 and calls a handler from the table at $88:A918. START pressed on pad 1 is event 3 ($88:A978),
    on pad 2 event $1B ($88:A986). Both handlers only start process $85:9759 / $85:9766, which lets an idle pad
    join the game (challenger) and does nothing for a pad whose player is already in ($7E:36C6 / $7E:388A == 1).

Why the hook is in the START handlers and not in the main loop test: the main loop counts its iterations in $2480
and $80:FE66 uses that count to refresh the random table at $7F:0000. Any extra cycles per iteration change the
random numbers (a first version hooked $88:A869 and tools/rig/pose_timing.py came out different). The handlers only
run when START is pressed, so the game is cycle for cycle the same until then.

This patch puts a JML at the start of both handlers. The new code pauses when either fighter is Batman (fighter id
24 at $7E:52C8 or $7E:52CA, low byte), $36C0 == 2, the pressing pad's player is in the game and START is still held;
otherwise it runs the original handler. So in a one-player game the idle pad's START still lets a challenger join.
While paused (the same freeze as the game's pause: $3A68 = 1, $1A0E saved and put back):
  * In fights BG3 is the HUD layer (mode 1, BG3 on top). The stage set-up ($84:92BE) leaves its tilemap register
    value in $7E:EB76 (map at VRAM word $1000 on every stage seen) and its character base in $7E:EB77 (stage
    dependent: $1000, $3000, $4000 seen). HDMA channels 2-7 switch TM, BG1/BG3 bases and the BG scrolls at line 42
    for the HUD, so HDMA is turned off while the list is up (shadow $1A18 and $420C) and BG3 scroll is set to 0.
  * The 32x32 BG3 tilemap (2 KB) and BG3 tiles 960-1023 (1 KB, the font slot) are copied from VRAM to
    $7F:F400-$7F:FFFF with DMA channel 1 (after setting the address a dummy read of $2139/$213A is needed: the read
    latch is loaded from the same address once more before the address moves on), then the font and a full-screen
    tilemap with the move list are written from ROM.
  * Only BG3 is on the main screen (TM shadow $1A24 = $04) and the backdrop is subtracted to black (CGWSEL $00,
    CGADSUB $A0, fixed colour white), so the list reads the same on every stage.
  * On the second START both VRAM areas are copied back, BG3 registers are set back to $EB76 / $EB77 and scroll 0
    (the stage set-up value; HDMA rewrites them every frame where it drives them), the IRQ shadows are pulled back
    from the stack and written to the PPU at once. Button events queued while paused are dropped (the event stack
    pointer $3556 is put back), so buttons tapped during the pause do nothing on resume.
  * VRAM is only touched right after the frame counter changes (the V-IRQ has just returned, the PPU is in
    vertical blank), with interrupts off and forced blank on; $2100 is then set back from the shadow $1A14.
  * If BG3 is not 32x32 or the font slot overlaps the tilemap, the list is not shown and START keeps its old job.
  * With the pause kode on as well, whichever of the two sees the START first runs (in the test the list showed);
    the other one then finds START released and does nothing, so there is never a double pause.
$7F:F3F0-$7F:FFFF is only used as write-before-read scratch on the screen between matches (value 17 of $7E:3A7E);
fights never read or write it (checked with a read and write watch over random two-player runs and a one-player
fight). The text comes from move_list_patch.lines() (built from batman_moves_patch.MOVE_LIST), with FORWARD written
FWD when a line is wider than 30 columns, drawn with the game's own text font ($D4:C5A9, 8x16 per glyph, character
map $88:8D5B) cut to 2 bits per pixel in BG3 palette 2 (white, the HUD's "WINS" colours) and palette 3 for the
title (the timer's gold), one line per 16 pixels.
"""
import struct

import numpy as np

import exhirom
import move_list_patch
from move_list_patch import Asm

# START press handlers, called from the main loop's button event dispatch ($88:A8E8, table $88:A918; event 3 is
# START pressed on pad 1, event $1B on pad 2). Each is: ldy #0 / lda #process / ldx #$85 / jsl $88C6E7 / rtl.
SITES = {0x08A978: 0x9759, 0x08A986: 0x9766}
SPAWN = 0x88C6E7
ACTIVE_P2 = 0x388A - 0x36C6                     # $7E:36C6 / $7E:388A: 1 while that pad's player is in the game
FIGHTER = 24
START = 0x1000

FONT_DATA, CHAR_MAP = 0x14C5A9, 0x088D5B        # $D4:C5A9 glyphs (64 bytes, 4bpp 8x16), $88:8D5B ASCII -> glyph
FONT_TILE = 0x3C0                               # first BG3 tile of the font slot
FONT_TILES = 64
BUF = 0x7FF400                                  # $7F:F400 saved tilemap (2 KB), $7F:FC00 saved font slot (1 KB)
VARS = 0x7FF3F0                                 # $7F:F3F0 font slot VRAM address, $7F:F3F2 tilemap VRAM address
COLS, ROWS = 32, 32
TEXT_PAL, TITLE_PAL = 2, 3
FIRST_ROW = 1
MAX_COLS = 30
SHADOWS = (0x1A18, 0x1A1A, 0x1A1C, 0x1A1E, 0x1A24)   # IRQ shadows of HDMAEN, COLDATA, CGADSUB, CGWSEL, TM
PAUSE_TM = 0x04                                 # only BG3 (the list) on the main screen while paused


def text_lines():
    """The move list lines (move_list_patch.lines()), shortened to fit 30 fixed-width 8-pixel cells."""
    out = move_list_patch.lines()
    if max(len(t) for t in out) > MAX_COLS:
        out = [t.replace("FORWARD", "FWD") for t in out]
    for t in out:
        assert len(t) <= MAX_COLS, t
    return out


def _glyph(rom, ch):
    """16x8 array of 2bpp colour numbers for one character, centred in its 8-pixel cell, with a dark shadow."""
    g = rom[CHAR_MAP + ord(ch)]
    img = np.zeros((16, 8), np.uint8)
    if g == 0xFF:
        return img
    src = np.zeros((16, 8), np.uint8)
    for half in range(2):
        o = FONT_DATA + 64 * g + 32 * half
        for y in range(8):
            p = (rom[o + 2 * y], rom[o + 2 * y + 1], rom[o + 16 + 2 * y], rom[o + 17 + 2 * y])
            for x in range(8):
                src[8 * half + y, x] = sum(((p[k] >> (7 - x)) & 1) << k for k in range(4))
    cols = np.nonzero(src.any(axis=0))[0]
    shift = max(0, (7 - (cols.max() + 1)) // 2) if len(cols) else 0
    src = np.roll(src, shift, axis=1)
    img[src >= 4] = 3                              # bright body of the glyph
    img[(src > 0) & (src < 4)] = 1                 # anti-aliased edge -> dark
    body = img == 3
    shadow = np.zeros_like(body)
    shadow[1:, 1:] = body[:-1, :-1]
    img[shadow & (img == 0)] = 1                   # drop shadow, one pixel down and right
    return img


def _tile2bpp(t):
    out = bytearray(16)
    for y in range(8):
        for x in range(8):
            v = int(t[y, x])
            out[2 * y] |= (v & 1) << (7 - x)
            out[2 * y + 1] |= ((v >> 1) & 1) << (7 - x)
    return bytes(out)


def screen(rom):
    """(font tiles 2bpp, BG3 tilemap 32x32 words). Tile numbers start at FONT_TILE."""
    tiles = [bytes(16)]
    index = {tiles[0]: 0}

    def tile_of(t):
        b = _tile2bpp(t)
        if b not in index:
            index[b] = len(tiles)
            tiles.append(b)
        return index[b]

    tmap = [FONT_TILE] * (COLS * ROWS)
    for i, t in enumerate(text_lines()):
        row = FIRST_ROW + 2 * i
        pal = TITLE_PAL if i == 0 else TEXT_PAL
        col0 = (COLS - len(t)) // 2
        for k, ch in enumerate(t):
            g = _glyph(rom, ch)
            for half in range(2):
                n = tile_of(g[8 * half:8 * half + 8])
                tmap[(row + half) * COLS + col0 + k] = (FONT_TILE + n) | pal << 10 | 0x2000
    assert len(tiles) <= FONT_TILES, len(tiles)
    assert FIRST_ROW + 2 * len(text_lines()) <= 28, "move list taller than the screen"
    return b"".join(tiles).ljust(FONT_TILES * 16, b"\0"), struct.pack("<%dH" % len(tmap), *tmap)


def long(op, addr):
    return bytes([op, addr & 255, (addr >> 8) & 255, (addr >> 16) & 255])


def code(base, font, tmap):
    a = Asm(base)
    bank = base >> 16
    I = lambda op, addr: a.b(*long(op, addr))       # long-addressed instruction
    sep, rep = (lambda: a.b(0xE2, 0x20)), (lambda: a.b(0xC2, 0x20))

    def dma(vaddr_var, abus_label=None, abus=None, abank=None, size=0, read=False):
        sep(); a.b(0xA9, 0x80); I(0x8F, 0x002115); rep()                 # VMAIN: +1 word after the high byte
        I(0xAF, vaddr_var); I(0x8F, 0x002116)                             # VMADD
        if read:
            I(0xAF, 0x002139)        # dummy read: the latch is refilled from the same address before it moves on
        a.b(0xA9); a.b(*struct.pack("<H", 0x3981 if read else 0x1801)); I(0x8F, 0x004310)   # DMAP1 / BBAD1
        if abus_label:
            a.b(0xA9); a.word_of(abus_label)
        else:
            a.b(0xA9, abus & 255, abus >> 8)
        I(0x8F, 0x004312)                                                 # A1T1
        sep(); a.b(0xA9, abank); I(0x8F, 0x004314); rep()                 # A1B1
        a.b(0xA9, size & 255, size >> 8); I(0x8F, 0x004315)               # DAS1
        sep(); a.b(0xA9, 0x02); I(0x8F, 0x00420B); rep()                  # start channel 1

    def blank_on():
        a.b(0x78)                                                          # sei
        sep(); a.b(0xA9, 0x80); I(0x8F, 0x002100); rep()

    def blank_off():
        sep(); I(0xAF, 0x7E1A14); I(0x8F, 0x002100); rep()
        a.b(0x58)                                                          # cli

    def start_held():
        a.b(0x20); a.word_of("held")                                       # jsr held: Z clear if START is held

    def frame():
        a.b(0x20); a.word_of("frame")

    def bg3_regs():
        """BG3 back to the values the stage set ($7E:EB76 / $EB77), scroll 0 (the value the stage set-up writes)."""
        sep()
        a.b(0xAD, 0x76, 0xEB); I(0x8F, 0x002109)                          # BG3SC
        a.b(0xAD, 0x77, 0xEB); I(0x8F, 0x00210C)                          # BG34NBA
        a.b(0xA9, 0x00)
        for reg in (0x002111, 0x002111, 0x002112, 0x002112):              # BG3HOFS, BG3VOFS (two writes each)
            I(0x8F, reg)
        rep()

    def shadows_to_ppu():
        """Write the IRQ's shadows to the PPU now, so the next frame already uses them (DB = $7E, 8-bit A)."""
        for shadow, reg in ((0x1A18, 0x00420C), (0x1A24, 0x00212C), (0x1A1A, 0x002132), (0x1A1C, 0x002131),
                            (0x1A1E, 0x002130)):
            a.b(0xAD, shadow & 255, shadow >> 8); I(0x8F, reg)

    # entries from the START press handlers $88:A978 (pad 1) and $88:A986 (pad 2), A and X/Y 16-bit, DB = $7E
    a.label("entry1")
    a.b(0xA9, 0x59, 0x97, 0x48, 0xA2, 0x00, 0x00, 0xA0, 0x00, 0x00)       # pha #$9759 / ldx #0 / ldy #0
    a.branch(0x80, "common")
    a.label("entry2")
    a.b(0xA9, 0x66, 0x97, 0x48, 0xA2, ACTIVE_P2 & 255, ACTIVE_P2 >> 8, 0xA0, 0x02, 0x00)   # pha #$9766 / ldx / ldy #2
    a.label("common")
    a.b(0x8B, 0xF4, 0x7E, 0x7E, 0xAB, 0xAB)                               # phb / pea $7E7E / plb / plb
    a.b(0xAD, 0xC8, 0x52, 0x29, 0xFF, 0x00, 0xC9, FIGHTER, 0x00); a.branch(0xF0, "bat")   # fighter ids
    a.b(0xAD, 0xCA, 0x52, 0x29, 0xFF, 0x00, 0xC9, FIGHTER, 0x00); a.branch(0xF0, "bat")
    a.label("out")
    a.b(0xAB, 0x68)                                                        # plb / pla (process address)
    a.b(0xA0, 0x00, 0x00, 0xA2, 0x85, 0x00); a.jsl(SPAWN); a.b(0x6B)      # the original handler
    a.label("bat")
    a.b(0xAD, 0xC0, 0x36, 0xC9, 0x02, 0x00); a.branch(0xD0, "out")        # a fight is running ($36C0 == 2)
    a.b(0xBD, 0xC6, 0x36, 0xC9, 0x01, 0x00); a.branch(0xD0, "out")        # this pad's player is in the game
    a.b(0xB9, 0x62, 0x36, 0x89, START & 255, START >> 8); a.branch(0xF0, "out")   # START still held on this pad
    a.b(0xAD, 0x76, 0xEB, 0x29, 0x03, 0x00); a.branch(0xD0, "out")        # BG3 must be 32x32
    a.b(0xAD, 0x76, 0xEB, 0x29, 0xFC, 0x00, 0xEB); I(0x8F, VARS + 2)      # tilemap word address M = (SC & $FC) << 8
    a.b(0xAD, 0x77, 0xEB, 0x29, 0x0F, 0x00)                               # BG3 character base nibble
    a.b(0xEB, 0x0A, 0x0A, 0x0A, 0x0A)                                      # xba / asl x4 -> << 12
    a.b(0x18, 0x69); a.b(*struct.pack("<H", FONT_TILE * 8))               # clc / adc #font slot
    a.b(0x29, 0xFF, 0x7F); I(0x8F, VARS)                                  # and #$7FFF / sta F
    a.b(0x38); I(0xAF, VARS); I(0xEF, VARS + 2)                           # F - M
    a.b(0x29, 0xFF, 0x7F, 0xC9, 0x00, 0x04); a.branch(0x90, "out")        # font starts inside the map
    a.b(0x38); I(0xAF, VARS + 2); I(0xEF, VARS)                           # M - F
    a.b(0x29, 0xFF, 0x7F, 0xC9, FONT_TILES * 8 & 255, FONT_TILES * 8 >> 8); a.branch(0x90, "out")

    a.label("pause")
    a.b(0xAD, 0x56, 0x35, 0x48)                                            # push the button event stack pointer
    a.b(0xA9, 0x01, 0x00, 0x8D, 0x68, 0x3A)                               # lda #1 / sta $3A68 (as the game's pause)
    a.b(0xAD, 0x0E, 0x1A, 0x8D, 0x10, 0x1A)                               # lda $1A0E / sta $1A10
    for sh in SHADOWS:                                                     # push the IRQ's PPU shadows
        a.b(0xAD, sh & 255, sh >> 8, 0x48)

    frame()
    blank_on()
    dma(VARS + 2, abus=BUF & 0xFFFF, abank=BUF >> 16, size=0x800, read=True)             # save the tilemap
    dma(VARS, abus=(BUF + 0x800) & 0xFFFF, abank=BUF >> 16, size=FONT_TILES * 16, read=True)   # save the slot
    blank_off()
    frame()
    blank_on()
    dma(VARS, abus_label="font", abank=bank, size=FONT_TILES * 16)
    dma(VARS + 2, abus_label="tmap", abank=bank, size=0x800)
    bg3_regs()
    sep()
    a.b(0xA9, 0x00, 0x8D, 0x18, 0x1A)                                     # HDMA off (it splits BG3 for the HUD)
    a.b(0xA9, PAUSE_TM, 0x8D, 0x24, 0x1A)                                 # main screen: BG3 only
    a.b(0xA9, 0x00, 0x8D, 0x1E, 0x1A)                                     # CGWSEL: fixed colour, math everywhere
    a.b(0xA9, 0xA0, 0x8D, 0x1C, 0x1A)                                     # CGADSUB: subtract from the backdrop
    a.b(0xA9, 0xFF, 0x8D, 0x1A, 0x1A)                                     # COLDATA: full white -> backdrop black
    shadows_to_ppu()
    rep()
    blank_off()

    a.label("w1")                                                          # START released
    frame(); start_held(); a.branch(0xD0, "w1")
    a.label("w2")                                                          # START pressed again
    frame(); start_held(); a.branch(0xF0, "w2")

    frame()
    blank_on()
    dma(VARS, abus=(BUF + 0x800) & 0xFFFF, abank=BUF >> 16, size=FONT_TILES * 16)
    dma(VARS + 2, abus=BUF & 0xFFFF, abank=BUF >> 16, size=0x800)
    bg3_regs()
    for sh in reversed(SHADOWS):                                           # pull the shadows back
        a.b(0x68, 0x8D, sh & 255, sh >> 8)
    sep(); shadows_to_ppu(); rep()
    blank_off()
    a.label("w3")                                                          # START released
    frame(); start_held(); a.branch(0xD0, "w3")
    a.b(0xAD, 0x10, 0x1A, 0x8D, 0x0E, 0x1A, 0x9C, 0x68, 0x3A)             # frame counter back, $3A68 = 0 (as $A8B4)
    a.b(0x78, 0x68, 0x8D, 0x56, 0x35, 0x58)     # sei / drop the button events queued while paused / cli
    a.b(0x4C); a.word_of("out")                                            # jmp out: then the original handler

    a.label("held")              # START held on a pad whose player is in the game ($36C6 / $388A == 1)
    a.b(0xA9, 0x00, 0x00, 0x48)                                            # lda #0 / pha
    for active, pad, nxt in ((0x7E36C6, 0x7E3662, "h2"), (0x7E388A, 0x7E3664, "h3")):
        I(0xAF, active); a.b(0xC9, 0x01, 0x00); a.branch(0xD0, nxt)
        I(0xAF, pad); a.b(0x03, 0x01, 0x83, 0x01)                          # ora 1,s / sta 1,s
        a.label(nxt)
    a.b(0x68, 0x89, START & 255, START >> 8, 0x60)                         # pla / bit #START / rts

    a.label("frame")                                                       # wait for the V-IRQ (DB = $7E)
    a.b(0xAD, 0x0E, 0x1A)
    a.label("fl")
    a.b(0xCD, 0x0E, 0x1A); a.branch(0xF0, "fl")
    a.b(0x60)

    a.label("font")
    a.out += font
    a.label("tmap")
    a.out += tmap
    return a.done(), a.labels


def patch(rom, alloc, put):
    """rom: the expanded image. New code and data go in expanded ROM; both START handlers (both bank copies) jump to it."""
    for site, proc in SITES.items():
        expect = bytes.fromhex("a00000a9") + struct.pack("<H", proc) + bytes.fromhex("a2850022e7c6886b")
        assert bytes(rom[site:site + len(expect)]) == expect, "unexpected bytes at the START handler %06X" % site
    font, tmap = screen(rom)
    size = len(code(0x400000, font, tmap)[0])
    bank, addr = alloc.alloc(size)
    base = bank << 16 | addr
    blob, labels = code(base, font, tmap)
    assert len(blob) == size
    put(bank, addr, blob)
    for (site, _), name in zip(sorted(SITES.items()), ("entry1", "entry2")):
        t = base + labels[name]
        jml = bytes([0x5C, t & 255, (t >> 8) & 255, t >> 16])
        rom[site:site + 4] = jml
        rom[exhirom.ORIG_SIZE + site:exhirom.ORIG_SIZE + site + 4] = jml
    n_tiles = len(set(font[i:i + 16] for i in range(0, len(font), 16)))
    return dict(hook="%02X:%04X" % (bank, addr), pause="%06X" % (base + labels["pause"]), size=len(blob),
                font_tiles=n_tiles, lines=len(text_lines()))
