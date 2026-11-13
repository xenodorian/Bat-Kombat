"""Batman's sounds in UMK3 (USA, SNES): Batman Returns samples, heard only when Batman makes the sound.

How UMK3 plays sounds (found with the debugger, see Current_Work.md):
  * Every request goes through $84:FE62 with A = address in bank $86 of a [sound id, priority] pair
    (voice tables per voice set, move scripts, special-move code). It ends in $84:EF4B with the sound id.
  * Each object runs with its own direct page; $2A on it is the object index, $7E:52C8,x its fighter id, and
    $62 the opponent's object. Projectiles carry their owner's fighter id. A hit reaction is requested on the
    victim's direct page, so $62 there is the attacker.
  * The sound id is also sent to the sound CPU, which has its own table of 146 sounds. New ids therefore cannot
    be added; Batman's sounds reuse streamed ids ("donors") and only the streamed sample is swapped.
  * Sound bank header $CE:9900: byte 0 = sample count - 1, byte 1 = size of a small table after the sample
    pointers, byte 2 = sound count; then 3-byte sample pointers, that table, 3 bytes per sound
    [sample index, flags, sound-program patch], 6 bytes, 2 bytes per sound. A sound with flag $40 streams its
    sample: the pointer leads to 9 bytes of buffer settings, then [length word][address word][bank byte] of data
    that is 3 prefix bytes plus BRR blocks. The streamer ORs $80 into the bank, so data must be in banks $C0-$FF.
    Streamed voices play at pitch $02FF, about 5992 Hz. $84:EF8C reads the sample index into $1B8A.

What this patch does:
  1. Copies the sample pointer table to the expanded ROM with Batman's samples appended (the copy keeps the
     header layout, so every computed pointer still works) and points the code at the copy.
  2. Writes the samples (art/batman_sounds, resampled to 5992 Hz) into free space in bank $FF.
  3. Hooks $84:FE62. For a request made by fighter 24 (or, for SELF_HIT ids, made by the victim of fighter 24),
     a listed sound id becomes a donor id and the sample index to use is stored at $7E:1CF8 ([donor id, sample]).
     Id SILENT means no sound.
  4. Hooks $84:EF8C: when the sound being started is the donor id stored at $7E:1CF8, that sample is used.
"""
import os
import struct
import wave

import numpy as np

import brr
import exhirom
from move_list_patch import Asm

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIGHTER = 24
BANK_HDR = 0x0E9900                       # $CE:9900
RATE = 5992                               # playback rate of streamed voices (pitch $02FF)
PREFIX = bytes.fromhex("60ff40")          # the 3 bytes in front of every streamed sample in the ROM
TEMPLATE_SAMPLE = 91                      # Rain's attack yell: buffer settings copied from it
OVERRIDE = 0x7E1CF8                       # [donor id, sample index]; never written by the game (checked in 1P and 2P play)
SITE = 0x04FE62
SITE_BYTES = bytes.fromhex("c230a8f4807eab0ba900175b840aa98600850c")
RESUME = 0x84FE75                         # "lda [$0A]" after the original setup
SITE2 = 0x04EF8C                          # lda [$45],y / and #$00FF / sta $1B8A
SITE2_BYTES = bytes.fromhex("b74529ff008d8a1b")
HOOK_AREA = (0x3FE180, 0x3FE400)          # free space in the first 4 MB (bank $FF), after the move table
OVR_AREA = (0x3FDF00, 0x3FE000)
DATA_AREAS = [(0x3FEB00, 0x3FF000), (0x3FF890, 0x400000)]
# code that reads the sound bank header: (file offset of the 3-byte operand, header offset)
REFS = [(0x03CCBD, 1), (0x03CCC7, 2), (0x04E974, 3), (0x04E979, 5), (0x04EBBF, 3), (0x04EBC4, 5),
        (0x04EC0F, 1), (0x04EC30, 0), (0x04ECB2, 0), (0x04ECCE, 1), (0x04ECDC, 2), (0x04ED56, 3),
        (0x04ED5C, 5), (0x04FE8E, 2), (0x04FEC3, 1)]
IMMS = [(0x04ECC1, 0x04ECC6), (0x04EC3F, 0x04EC4A)]   # "adc #$9903" / "lda #$CE" pairs in the pointer setup

# name, file, peak, max seconds, donor id (a streamed sound the sound CPU plays as a stream voice)
SOUNDS = [
    ("swing", "swing.wav", 22000, 0.30, 0x81),
    ("impact", "impact.wav", 26000, 0.25, 0x87),
    ("batarang", "batarang.wav", 24000, 0.40, 0x86),
]
SILENT = None
SELF = {}                                 # requests made by Batman: UMK3 id -> sound name or SILENT
for i in (0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B, 0x0E, 0x21):
    SELF[i] = "swing"                     # punch and kick swings, teleport whoosh (built-in instrument $0C)
for i in (0x00, 0x01, 0x02, 0x03, 0x05, 0x0C, 0x23, 0x24):
    SELF[i] = "impact"                    # hits Batman takes (built-in instrument $0B)
for i in (0x8C, 0x8D):
    SELF[i] = "batarang"                  # special-move launch sounds (Batarang, Grapple Gun)
for i in (0x81, 0x84, 0x85, 0x86, 0x87, 0x3C):
    SELF[i] = SILENT                      # Rain's voice: attack, jump, other yells, hurt, special hit
VICTIM = {0x5F: "impact", 0x35: "impact"}  # requested by the victim of Batman's Batarang and Grapple Gun


def load_pcm(path, peak, max_s):
    with wave.open(path) as w:
        rate = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(float)
    n = int(len(x) * RATE / rate)
    y = np.interp(np.arange(n) * rate / RATE, np.arange(len(x)), x)[:int(max_s * RATE)]
    fade = min(len(y), int(0.02 * RATE))
    y[-fade:] *= np.linspace(1, 0, fade)
    y *= peak / max(1.0, np.abs(y).max())
    return [int(v) for v in y]


def stream_data(pcm):
    return PREFIX + bytes([0xC0] + [0] * 8) + brr.encode(pcm)     # prefix, one silent block, the sound


def _w(rom, off, data):
    rom[off:off + len(data)] = data
    if off & 0x8000 and off < exhirom.ORIG_SIZE:                  # keep the bank $00-$3F mirror in step
        rom[exhirom.ORIG_SIZE + off:exhirom.ORIG_SIZE + off + len(data)] = data


ROW = 5      # old id, donor id, priority, donor id, sample index


def hook_code(base, self_rows, victim_rows):
    """Replacement for the start of $84:FE62 (A = address in bank $86 of a [sound id, priority] pair).

    A matching request uses the row's [donor, priority] pair (in this bank) and stores [donor, sample] at
    OVERRIDE; any other request clears OVERRIDE. Then the original setup, and a jump to $84:FE75.
    """
    bank = base >> 16
    ov = (OVERRIDE & 0xFF, (OVERRIDE >> 8) & 0xFF, OVERRIDE >> 16)
    a = Asm(base)
    a.b(0xC2, 0x30, 0xA8)                                       # rep #$30 / tay
    a.b(0xBB, 0xBF, 0x00, 0x00, 0x86, 0x29, 0xFF, 0x00, 0x48)   # tyx / lda $860000,x / and #$FF / pha (id)
    a.b(0xA5, 0x2A, 0xC9, 0x60, 0x00)                           # lda $2A / cmp #$60
    a.branch(0xB0, "nf")
    a.b(0xAA, 0xBF, 0xC8, 0x52, 0x7E, 0x29, 0xFF, 0x00)         # tax / lda $7E52C8,x / and #$FF
    a.b(0xC9, FIGHTER, 0x00)
    a.branch(0xD0, "victim")
    a.b(0xA2); a.word_of("self")                                # ldx #self rows
    a.branch(0x80, "search")
    a.label("victim")
    a.b(0xA5, 0x62, 0xC9, 0x60, 0x00)                           # lda $62 / cmp #$60
    a.branch(0xB0, "nf")
    a.b(0xAA, 0xBF, 0xC8, 0x52, 0x7E, 0x29, 0xFF, 0x00)         # tax / lda $7E52C8,x / and #$FF
    a.b(0xC9, FIGHTER, 0x00)
    a.branch(0xD0, "nf")
    a.b(0xA2); a.word_of("victim_t")                            # ldx #victim rows
    a.label("search")
    a.b(0xBF, 0x00, 0x00, bank, 0x29, 0xFF, 0x00)               # lda bank:0000,x / and #$FF
    a.b(0xC9, 0xFF, 0x00)
    a.branch(0xF0, "nf")
    a.b(0xC3, 0x01)                                             # cmp 1,s
    a.branch(0xF0, "found")
    a.b(0xE8, 0xE8, 0xE8, 0xE8, 0xE8)                           # inx x5
    a.branch(0x80, "search")
    a.label("found")
    a.b(0xBF, 0x03, 0x00, bank, 0x8F, *ov)                      # lda bank:0003,x / sta OVERRIDE
    a.b(0x68, 0xE8, 0x9B)                                       # pla / inx / txy  (Y -> [donor, priority])
    a.b(0xA9, bank, 0x00)                                       # lda #bank
    a.branch(0x80, "go")
    a.label("nf")
    a.b(0x68, 0xA9, 0x00, 0x00, 0x8F, *ov)                      # pla / lda #0 / sta OVERRIDE
    a.b(0xA9, 0x86, 0x00)                                       # lda #$0086
    a.label("go")
    a.b(0xAA)                                                   # tax (bank of the pair)
    a.b(0xF4, 0x80, 0x7E, 0xAB, 0x0B)                           # pea $7E80 / plb / phd   (as the original)
    a.b(0xA9, 0x00, 0x17, 0x5B)                                 # lda #$1700 / tcd
    a.b(0x84, 0x0A, 0x86, 0x0C)                                 # sty $0A / stx $0C
    a.jml(RESUME)
    a.label("self")
    for row in self_rows:
        a.b(*row)
    a.b(0xFF, 0, 0, 0, 0)
    a.label("victim_t")
    for row in victim_rows:
        a.b(*row)
    a.b(0xFF, 0, 0, 0, 0)
    return a.done()


def ovr_code(base):
    """Replacement for $84:EF8C-$EF93 (lda [$45],y / and #$FF / sta $1B8A), entered by JSL, 16-bit A."""
    ov = (OVERRIDE & 0xFF, (OVERRIDE >> 8) & 0xFF, OVERRIDE >> 16)
    ov1 = ((OVERRIDE + 1) & 0xFF, ((OVERRIDE + 1) >> 8) & 0xFF, (OVERRIDE + 1) >> 16)
    a = Asm(base)
    a.b(0xB7, 0x45, 0x29, 0xFF, 0x00, 0x8D, 0x8A, 0x1B)         # the original three instructions
    a.b(0xAF, *ov, 0x29, 0xFF, 0x00)                            # lda OVERRIDE / and #$FF (donor id)
    a.b(0xCD, 0x7A, 0x1B)                                       # cmp $1B7A (the sound being started)
    a.branch(0xD0, "done")
    a.b(0xAF, *ov1, 0x29, 0xFF, 0x00, 0x8D, 0x8A, 0x1B)         # lda OVERRIDE+1 / and #$FF / sta $1B8A
    a.b(0xA9, 0x00, 0x00, 0x8F, *ov)                            # lda #0 / sta OVERRIDE
    a.label("done")
    a.b(0x6B)                                                   # rtl
    return a.done()


def patch(rom, alloc, put):
    """rom: the expanded 8 MB image (bytearray). Returns a report dict."""
    r = rom
    ns, gap = r[BANK_HDR] + 1, r[BANK_HDR + 1]
    first_sound = BANK_HDR + 3 + 3 * ns + gap
    for off, ho in REFS:
        assert r[off + 2] == 0xCE and r[off] | r[off + 1] << 8 == 0x9900 + ho, "unexpected sound bank reference at %06X" % off
    for ia, ib in IMMS:
        assert r[ia:ia + 2] == b"\x03\x99" and r[ib] == 0xCE
    assert bytes(r[SITE:SITE + len(SITE_BYTES)]) == SITE_BYTES and bytes(r[SITE2:SITE2 + 8]) == SITE2_BYTES

    tp = r[BANK_HDR + 3 + 3 * TEMPLATE_SAMPLE:BANK_HDR + 6 + 3 * TEMPLATE_SAMPLE]
    to = exhirom.file_offset(tp[2], tp[0] | tp[1] << 8)
    settings = bytes(r[to:to + 9])

    # sample data: largest first into the smallest free area that holds it
    datas = [stream_data(load_pcm(os.path.join(REPO, "art", "batman_sounds", f), peak, max_s))
             for _, f, peak, max_s, _ in SOUNDS]
    areas = [list(x) for x in DATA_AREAS]
    placed = {}
    for k in sorted(range(len(datas)), key=lambda k: -len(datas[k])):
        area = next(x for x in sorted(areas, key=lambda x: x[1] - x[0]) if x[1] - x[0] >= len(datas[k]))
        placed[k] = area[0]
        area[0] += len(datas[k])
    for k, data in enumerate(datas):
        off = placed[k]
        assert all(b == 0xFF for b in r[off:off + len(data)]), "sound data area is not free"
        _w(r, off, data)

    # sound bank copy: header, sample pointers + new ones, then everything up to the end of the per-sound tables
    n_new = len(SOUNDS)
    nsnd = r[BANK_HDR + 2]
    end = first_sound + 3 * nsnd + 6 + 2 * nsnd
    tail = bytes(r[BANK_HDR + 3 + 3 * ns:end])
    size = 3 + 3 * (ns + n_new) + len(tail) + 14 * n_new
    bank, addr = alloc.alloc(size)
    hdr_at = addr + 3 + 3 * (ns + n_new) + len(tail)
    blob = bytearray([ns + n_new - 1, gap, nsnd]) + r[BANK_HDR + 3:BANK_HDR + 3 + 3 * ns]
    for k in range(n_new):
        blob += struct.pack("<HB", hdr_at + 14 * k, bank)
    blob += tail
    for k, data in enumerate(datas):
        off = placed[k]
        blob += settings + struct.pack("<HHB", len(data), off & 0xFFFF, 0xC0 | (off >> 16))
    assert len(blob) == size
    put(bank, addr, bytes(blob))
    for off, ho in REFS:
        _w(r, off, struct.pack("<HB", addr + ho, bank))
    for ia, ib in IMMS:
        _w(r, ia, struct.pack("<H", addr + 3))
        _w(r, ib, bytes([bank]))

    # hooks
    sample_of = {name: ns + k for k, (name, *_rest) in enumerate(SOUNDS)}
    donor_of = {name: d for name, _, _, _, d in SOUNDS}

    def rows(table):
        out = []
        for old, name in sorted(table.items()):
            if name is SILENT:
                out.append((old, 0xFF, 0x01, 0xFF, 0x00))
            else:
                out.append((old, donor_of[name], 0x01, donor_of[name], sample_of[name]))
        return out
    base = 0xC00000 | HOOK_AREA[0]
    code = hook_code(base, rows(SELF), rows(VICTIM))
    assert HOOK_AREA[0] + len(code) <= HOOK_AREA[1], "sound hook too long"
    obase = 0xC00000 | OVR_AREA[0]
    ocode = ovr_code(obase)
    for (lo, hi), c in ((HOOK_AREA, code), (OVR_AREA, ocode)):
        assert all(b == 0xFF for b in r[lo:lo + len(c)]), "sound hook area is not free"
        _w(r, lo, c)
    _w(r, SITE, bytes([0x5C, base & 0xFF, (base >> 8) & 0xFF, base >> 16]))
    _w(r, SITE2, bytes([0x22, obase & 0xFF, (obase >> 8) & 0xFF, obase >> 16, 0xEA, 0xEA, 0xEA, 0xEA]))
    return dict(bank="%02X:%04X" % (bank, addr), samples=sample_of, hook="%06X" % base,
                sizes=[len(d) for d in datas], hook_size=len(code))
