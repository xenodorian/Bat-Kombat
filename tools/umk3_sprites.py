"""UMK3 (USA, SNES) sprite set format: decode frames from the ROM.

Engine model (from the decoder at $83:8000 and the set lookup at $88:A471):
  sprite id word ($7E:52F8,obj) = set << 9 | frame (frame is 1-based, 1..511)
  set table: bank words at $86:EAEC, address words at $86:EB24, indexed by set*2 -> 16-byte header
  header: +0 bank-table addr (w)   +2 tileset-table addr (w)  +4 tileset-table bank (b)
          +5 frame-pointer-table addr (w)  +7 bank of frame-pointer table and bank table (b)
          +8 bbox-table bank (b)  +9 word (unknown)  +11 delta-table bank (b)  +12 delta-table addr (w)
          +14 bbox-table addr (w, $FFFF = none)
  frame pointer = word at frame-table[(frame-1)*2], bank = byte at bank-table[(frame-1)>>6]
  frame record: [pieces][n16] then pieces (the n16 16x16 pieces first, then 8x8 pieces):
      control byte: high nibble = x code, low nibble = y code. Code 0 = an explicit signed byte follows
      (x first, then y). Code n = add delta-table entry (x: table[1+n], y: table[16+n]) to the previous value.
      Start values: x = table[0], y = table[1].
      then 4 tile words (16x16: top-left, top-right, bottom-left, bottom-right) or 1 tile word (8x8).
  tile word: bits 0-1 = h/v flip, bits 2-7 = tileset index (entry = 4 bytes), bits 8-15 = tile number in the tileset.
  tileset entry: address word, then word with bank in the low byte; bit 15 = compressed, bit 14 = 16-byte (2bpp-style) tile,
      neither = raw 32-byte 4bpp tile at address + tile*32.
HiROM: file offset = ((bank & 0x3F) << 16) | addr.
"""
import struct

SET_BANKS, SET_ADDRS = 0x06EAEC, 0x06EB24


def fo(bank, addr):
    return ((bank & 0x3F) << 16) | (addr & 0xFFFF)


def s8(v):
    return v - 256 if v > 127 else v


class SpriteSet:
    def __init__(self, rom, index):
        self.rom, self.index = rom, index
        w = lambda o: rom[o] | rom[o + 1] << 8
        hb, ha = w(SET_BANKS + 2 * index) & 0xFF, w(SET_ADDRS + 2 * index)
        o = fo(hb, ha)
        self.header_off = o
        self.banktab = fo(rom[o + 7], w(o))
        self.tileset_tab = fo(rom[o + 4], w(o + 2))
        self.frametab = fo(rom[o + 7], w(o + 5))
        self.delta = fo(rom[o + 11], w(o + 12))
        self.bbox = None if w(o + 14) == 0xFFFF else fo(rom[o + 8], w(o + 14))
        self.header = bytes(rom[o:o + 16])

    def frame_offset(self, frame):
        rom = self.rom
        a = rom[self.frametab + 2 * (frame - 1)] | rom[self.frametab + 2 * (frame - 1) + 1] << 8
        return fo(rom[self.banktab + ((frame - 1) >> 6)], a)

    def tileset(self, idx):
        o = self.tileset_tab + 4 * idx
        addr, flags = struct.unpack_from("<HH", self.rom, o)
        kind = "compressed" if flags & 0x8000 else ("half" if flags & 0x4000 else "raw")
        return dict(addr=addr, bank=flags & 0xFF, kind=kind, flags=flags)

    def decode(self, frame):
        """Return (pieces, record_length). piece = dict(x, y, size, tiles=[tile words])."""
        rom, p = self.rom, self.frame_offset(frame)
        start = p
        total, n16 = rom[p], rom[p + 1]
        p += 2
        d = self.delta
        x, y = rom[d], rom[d + 1]
        out = []
        for i in range(total):
            c = rom[p]; p += 1
            if c >> 4:
                x = (x + rom[d + 1 + (c >> 4)]) & 0xFF
            else:
                x = rom[p]; p += 1
            if c & 15:
                y = (y + rom[d + 16 + (c & 15)]) & 0xFF
            else:
                y = rom[p]; p += 1
            n = 4 if i < n16 else 1
            tiles = [rom[p + 2 * k] | rom[p + 2 * k + 1] << 8 for k in range(n)]
            p += 2 * n
            out.append(dict(x=s8(x), y=s8(y), size=16 if i < n16 else 8, tiles=tiles))
        return out, p - start

    def tile_pixels(self, word):
        """8x8 list of palette indexes for a raw tile word, or None when the tileset is not raw."""
        ts = self.tileset((word & 0xFC) >> 2)
        if ts["kind"] != "raw":
            return None
        o = fo(ts["bank"], ts["addr"]) + (word >> 8) * 32
        t = self.rom[o:o + 32]
        px = [[0] * 8 for _ in range(8)]
        for r in range(8):
            for c in range(8):
                b = 7 - c
                px[r][c] = ((t[2*r] >> b) & 1) | ((t[2*r+1] >> b) & 1) << 1 | ((t[16+2*r] >> b) & 1) << 2 | ((t[17+2*r] >> b) & 1) << 3
        if word & 1:
            px = [row[::-1] for row in px]
        if word & 2:
            px = px[::-1]
        return px

    def frame_count(self):
        return (self.banktab - self.frametab) // 2 if self.banktab > self.frametab else None
