"""Build the Batman ROM: Rain (fighter id 24) is drawn with a native Batman sprite set.

Usage: python3 -I tools/build_batman.py ORIGINAL_UMK3.sfc OUT.sfc [--map art/batman_frame_map.json]

How it works (see tools/umk3_sprites.py for the data format):
  * The ROM is expanded to 8 MB ExHiROM (tools/exhirom.py). New data goes in the free lower halves of banks $40+.
  * A new sprite set is written with the same frame numbering as set 27 (the male ninja set Rain uses):
    header, bank table, frame pointer table, tileset table (the 47 ninja tilesets plus new raw Batman tilesets),
    frame records and raw 4bpp tiles. Frames listed in the map get Batman art; all others keep the ninja record
    (projectiles, ropes, fatality props), copied so every 64-frame block sits in one bank.
  * A hook in the set lookup ($88:A47A) selects the new header when the object's fighter id ($7E:52C8,y) is 24
    and the set is 27. Everything else in the engine (position, facing, animation, moves, hit boxes) is unchanged.
  * Rain's 16-colour sprite palette (file 0x3EAFAF) is replaced with Batman's.
  * tools/roster_portrait_patch.py swaps Rain's select-screen portrait; tools/hud_name_patch.py makes the
    health-bar name read BATMAN.
The frame map says which Batman pose replaces which ninja frame: {"frames": {"131": {"pose": 0, "dx": 0, "dy": 0}}}.
Each pose is aligned to the ninja frame by body centre and bottom row (art/ninja_frames.json).
"""
import argparse
import json
import os
import struct
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import batman_art as ba
import exhirom
import batman_moves_patch
import hud_name_patch
import move_list_patch
import roster_portrait_patch
import umk3_sprites

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NINJA_SET = 27
RAIN_ID = 24
RAIN_PALETTE = 0x3EAFAF            # 16 colour words, used only by Rain
HOOK_SITE = 0x08A47A               # $88:A47A  cmp $52E0,y / beq / sta $52E0,y / tax / two table loads
HOOK_SITE_BYTES = bytes.fromhex("d9e052f05299e052aabfecea86854cbf24eb86854a")
HOOK_CODE = 0x3FDC6E               # $FF:DC6E, 0xFF padding in the original
FIRST_NEW_TILESET = 47             # the ninja set uses tilesets 0-46
MAX_TILESETS = 64
PORTRAIT_POSE, PORTRAIT_CROP = 0, (26, 0, 50, 36)   # cowl and emblem of the standing pose
CAP_ORIGIN = (128, 176)            # origin pixel inside the captured ninja frame images


# Batarang: the projectile of the "spit" move (ninja frames 257-261) redrawn from poses 41 and 42.
# It is shown in the projectile's own palette (sprite palette 5 while it flies): index 1 dark steel, 4 mid, 3 white.
# frame: (pose, x, y) with x, y the object-local top-left corner. BLANK frames (hit splash, drips) show nothing.
BATARANG = {257: (41, 48, -36), 258: (42, 60, -40), 259: (41, 70, -36), 260: (42, 102, -40), 261: (41, 102, -36)}
BATARANG.update({f: (41 + f % 2, 108, -36 - 4 * (f % 2)) for f in range(262, 270)})   # the rest of the flight
BLANK = list(range(270, 275))                                                         # drips at the mouth


def effect_index(rgba):
    """RGBA art -> indexes of the projectile palette, by brightness."""
    lum = rgba[:, :, :3].astype(float).mean(axis=2)
    op = rgba[:, :, 3] > 127
    lo, hi = np.percentile(lum[op], [55, 88])
    idx = np.where(lum <= lo, 1, np.where(lum <= hi, 4, 3)).astype(np.uint8)
    idx[~op] = 0
    return idx


def tile_bytes(px):
    """8x8 index array -> 32 bytes of SNES 4bpp."""
    out = bytearray(32)
    for r in range(8):
        for c in range(8):
            v = int(px[r, c])
            bit = 7 - c
            out[2 * r] |= (v & 1) << bit
            out[2 * r + 1] |= ((v >> 1) & 1) << bit
            out[16 + 2 * r] |= ((v >> 2) & 1) << bit
            out[17 + 2 * r] |= ((v >> 3) & 1) << bit
    return bytes(out)


class TileStore:
    """Unique raw tiles, 256 per tileset. Returns tile words (tile << 8 | tileset << 2 | flips)."""

    def __init__(self):
        self.tiles, self.index = [], {}

    def word(self, px, allow_flip):
        variants = [(0, px)]
        if allow_flip:
            variants += [(1, px[:, ::-1]), (2, px[::-1, :]), (3, px[::-1, ::-1])]
        for flips, v in variants:
            n = self.index.get(tile_bytes(v))
            if n is not None:
                return self._word(n, flips)
        n = len(self.tiles)
        b = tile_bytes(px)
        self.tiles.append(b)
        self.index[b] = n
        return self._word(n, 0)

    @staticmethod
    def _word(n, flips):
        ts = FIRST_NEW_TILESET + n // 256
        if ts >= MAX_TILESETS:
            raise MemoryError("more than %d Batman tiles" % ((MAX_TILESETS - FIRST_NEW_TILESET) * 256))
        return ((n % 256) << 8) | (ts << 2) | flips


def cut(idx, x, y, size):
    """size x size block of an index image at (x, y); outside the image is transparent."""
    out = np.zeros((size, size), np.uint8)
    h, w = idx.shape
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + size, w), min(y + size, h)
    if x1 > x0 and y1 > y0:
        out[y0 - y:y1 - y, x0 - x:x1 - x] = idx[y0:y1, x0:x1]
    return out


class Pose:
    def __init__(self, idx, store, anchor):
        self.idx = idx
        packed = ba.pack(idx, ba.importance(idx))
        self.lost = packed["lost"]
        self.shown = ba.render(idx, packed)
        self.cy = ba.centre_row(idx > 0)
        self.feet = anchor                     # (x, y) image pixel that is placed on the ninja frame's anchor
        self.pieces = []                       # (x, y, size, [tile words]) in image pixels
        for x, y in packed["p16"]:
            blk = cut(idx, x, y, 16)
            words = [store.word(blk[r:r + 8, c:c + 8], False) for r in (0, 8) for c in (0, 8)]
            self.pieces.append((x, y, 16, words))
        for x, y in packed["p8"]:
            self.pieces.append((x, y, 8, [store.word(cut(idx, x, y, 8), True)]))

    def record(self, ox, oy):
        """Frame record with the image placed so image pixel (0,0) is at object-local (ox, oy)."""
        n16 = sum(1 for p in self.pieces if p[2] == 16)
        out = bytearray([len(self.pieces), n16])
        for x, y, size, words in self.pieces:
            lx, ly = x + ox, y + oy
            if not (-128 <= lx <= 127 and -128 <= ly <= 127):
                raise ValueError("piece outside the signed-byte range")
            out += bytes([0x00, lx & 0xFF, ly & 0xFF])
            for wd in words:
                out += struct.pack("<H", wd)
        return bytes(out)


def hook_code(header_bank, header_addr):
    """65816 (16-bit A and index). Entered by JSL from $88:A47A with A = set*2, Y = object index, DB = $7E.

    Returns Z=1 when the cached header is still right (the caller's beq then skips the reload), else loads
    $4A/$4C with the header pointer. Rain with the ninja set gets the Batman header and an odd cache tag,
    so a slot that changes fighter never keeps the wrong header.
    """
    S2 = NINJA_SET * 2
    prog = [
        bytes([0xAA]),                                   # tax
        bytes([0xD9, 0xE0, 0x52]),                       # cmp $52E0,y
        ("bne", "load"),
        bytes([0xE0, S2, 0x00]),                         # cpx #set*2
        ("bne", "cached"),
        bytes([0xB9, 0xC8, 0x52]),                       # lda $52C8,y   (fighter id of this object)
        bytes([0xC9, RAIN_ID, 0x00]),                    # cmp #24
        ("beq", "load_bat"),                             # Rain, but the ninja header is cached: reload
        "cached",
        bytes([0xA9, 0x00, 0x00, 0x6B]),                 # lda #0 (Z=1) / rtl
        "load",
        bytes([0x8A]),                                   # txa
        bytes([0x99, 0xE0, 0x52]),                       # sta $52E0,y
        bytes([0xBF, 0xEC, 0xEA, 0x86, 0x85, 0x4C]),     # lda $86EAEC,x / sta $4C
        bytes([0xBF, 0x24, 0xEB, 0x86, 0x85, 0x4A]),     # lda $86EB24,x / sta $4A
        bytes([0xE0, S2, 0x00]),                         # cpx #set*2
        ("bne", "done"),
        bytes([0xB9, 0xC8, 0x52]),                       # lda $52C8,y
        bytes([0xC9, RAIN_ID, 0x00]),                    # cmp #24
        ("bne", "done"),
        "load_bat",
        bytes([0xA9, S2 + 1, 0x00]),                     # lda #set*2+1  (odd tag: never equals a real set)
        bytes([0x99, 0xE0, 0x52]),                       # sta $52E0,y
        bytes([0xA9, header_bank, 0x00, 0x85, 0x4C]),    # lda #bank / sta $4C
        bytes([0xA9, header_addr & 0xFF, header_addr >> 8, 0x85, 0x4A]),   # lda #addr / sta $4A
        "done",
        bytes([0xA9, 0x01, 0x00, 0x6B]),                 # lda #1 (Z=0) / rtl
    ]
    opcodes = {"bne": 0xD0, "beq": 0xF0}
    labels, pos = {}, 0
    for item in prog:
        if isinstance(item, str):
            labels[item] = pos
        else:
            pos += 2 if isinstance(item, tuple) else len(item)
    c = bytearray()
    for item in prog:
        if isinstance(item, tuple):
            rel = labels[item[1]] - (len(c) + 2)
            assert -128 <= rel <= 127
            c += bytes([opcodes[item[0]], rel & 0xFF])
        elif isinstance(item, bytes):
            c += item
    return bytes(c)


def build(rom4, frame_map, ninja_geom, poses_rgba, report=None):
    ba.init_slots(rom4)
    ninja = umk3_sprites.SpriteSet(rom4, NINJA_SET)
    nframes = ninja.frame_count()
    used = sorted({int(v["pose"]) for v in frame_map.values()})
    palette = ba.build_palette(poses_rgba, used)
    store = TileStore()
    poses = {}

    def pose(i, flip):
        if (i, flip) not in poses:
            idx = ba.to_indexed(poses_rgba[i], palette)
            ax, ay = ba.body_anchor(poses_rgba[i])
            if flip:
                idx, ax = idx[:, ::-1], idx.shape[1] - 1 - ax
            poses[(i, flip)] = Pose(idx, store, (ax, ay))
        return poses[(i, flip)]

    # frame records
    records = {}
    for f in range(1, nframes + 1):
        m = frame_map.get(str(f))
        if m is None:
            off = ninja.frame_offset(f)
            records[f] = bytes(rom4[off:off + ninja.decode(f)[1]])
            continue
        p = pose(int(m["pose"]), bool(m.get("flip")))
        nx, ny = ninja_geom[str(f)]["anchor"]                   # ninja alignment point in object-local pixels
        ox = nx - p.feet[0] + int(m.get("dx", 0))
        if ny < ba.AIRBORNE_BOTTOM:                               # tucked mid-air frame: centre on centre
            oy = ninja_geom[str(f)]["cy"] - p.cy + int(m.get("dy", 0))
        else:                                                     # feet (or back) on the same floor line
            oy = ny - p.feet[1] + int(m.get("dy", 0))
        records[f] = p.record(ox, oy)

    for f, (i, x, y) in BATARANG.items():
        records[f] = Pose(effect_index(poses_rgba[i]), store, (0, 0)).record(x, y)
    for f in BLANK:
        records[f] = bytes([1, 0, 0x00, 0, 0]) + struct.pack("<H", store.word(np.zeros((8, 8), np.uint8), False))

    rom = exhirom.expand(rom4)
    alloc = exhirom.Allocator()

    def put(bank, addr, data):
        o = exhirom.file_offset(bank, addr)
        rom[o:o + len(data)] = data

    # control block: header, bank table, frame table, tileset table (all in one bank)
    n_sets = (len(store.tiles) + 255) // 256
    ctl_size = 16 + 8 + 2 * nframes + 4 * MAX_TILESETS
    cbank, caddr = alloc.alloc(ctl_size)
    h_addr, bt_addr = caddr, caddr + 16
    ft_addr, ts_addr = bt_addr + 8, bt_addr + 8 + 2 * nframes

    # tiles
    ts_entries = bytearray(rom4[ninja.tileset_tab:ninja.tileset_tab + 4 * FIRST_NEW_TILESET])
    for k in range(n_sets):
        tbank, taddr = alloc.alloc(0x2000, align=0x20)
        chunk = b"".join(store.tiles[k * 256:(k + 1) * 256])
        put(tbank, taddr, chunk)
        ts_entries += struct.pack("<HH", taddr, 0x2000 | tbank)      # raw 32-byte tiles, same flag as the ninja raw sets
    ts_entries += b"\x00" * (4 * MAX_TILESETS - len(ts_entries))

    # records, one bank per block of 64 frames
    frame_ptr, bank_tab = bytearray(), bytearray()
    for blk in range((nframes + 63) // 64):
        fr = range(blk * 64 + 1, min(blk * 64 + 64, nframes) + 1)
        blob, offs = bytearray(), {}
        cache = {}
        for f in fr:
            if records[f] in cache:
                offs[f] = cache[records[f]]
            else:
                offs[f] = cache[records[f]] = len(blob)
                blob += records[f]
        rbank, raddr = alloc.alloc(len(blob))
        put(rbank, raddr, blob)
        bank_tab.append(rbank)
        for f in fr:
            frame_ptr += struct.pack("<H", raddr + offs[f])
    bank_tab += b"\x00" * (8 - len(bank_tab))

    header = bytearray(ninja.header)
    struct.pack_into("<H", header, 0, bt_addr)
    struct.pack_into("<H", header, 2, ts_addr)
    header[4] = cbank
    struct.pack_into("<H", header, 5, ft_addr)
    header[7] = cbank
    put(cbank, h_addr, header)
    put(cbank, bt_addr, bank_tab)
    put(cbank, ft_addr, frame_ptr)
    put(cbank, ts_addr, ts_entries)

    # hook
    assert bytes(rom[HOOK_SITE:HOOK_SITE + len(HOOK_SITE_BYTES)]) == HOOK_SITE_BYTES, "unexpected bytes at hook site"
    code = hook_code(cbank, h_addr)
    assert all(b == 0xFF for b in rom[HOOK_CODE:HOOK_CODE + len(code)]), "hook area is not free"
    rom[HOOK_CODE:HOOK_CODE + len(code)] = code
    site = bytes([0x22, HOOK_CODE & 0xFF, (HOOK_CODE >> 8) & 0xFF, 0xFF])        # jsl $FF:DC6E
    site += bytes([0xF0, 0x51])                                                  # beq $A4D1 (header still cached)
    site += b"\xEA" * (len(HOOK_SITE_BYTES) - len(site))
    rom[HOOK_SITE:HOOK_SITE + len(site)] = site

    # palette
    rom[RAIN_PALETTE:RAIN_PALETTE + 32] = struct.pack("<16H", *ba.palette_words(palette))

    # the bank-$00-$3F mirror of the patched areas must match (vectors and slow-bank reads)
    for off, ln in ((HOOK_SITE, len(HOOK_SITE_BYTES)), (HOOK_CODE, len(code)), (RAIN_PALETTE, 32)):
        if off & 0x8000:
            rom[exhirom.ORIG_SIZE + off:exhirom.ORIG_SIZE + off + ln] = rom[off:off + ln]
    exhirom.fix_checksum(rom)

    if report is not None:
        report.update(tiles=len(store.tiles), tilesets=n_sets, poses=len(poses),
                      mapped_frames=len(frame_map), header="%02X:%04X" % (cbank, h_addr),
                      last_bank="%02X" % alloc.bank, palette=palette,
                      lost={"%d%s" % (i, "f" if fl else ""): p.lost for (i, fl), p in poses.items() if p.lost},
                      max_sprites=max(len(p.pieces) for p in poses.values()))
    return rom


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("rom")
    ap.add_argument("out")
    ap.add_argument("--map", default=os.path.join(REPO, "art", "batman_frame_map.json"))
    ap.add_argument("--ninja", default=os.path.join(REPO, "art", "ninja_frames.json"),
                    help="feet points of the ninja frames, written by tools/make_frame_map.py")
    ap.add_argument("--poses", default=os.path.join(REPO, "art", "batman_poses.tar.gz"))
    ap.add_argument("--work", default=os.path.join(REPO, "build", "poses"))
    a = ap.parse_args()
    rom4 = bytearray(open(a.rom, "rb").read())
    poses_rgba = ba.load_poses(a.poses, a.work)
    # cosmetics on the original image first: roster portrait (head of the standing pose) and the health-bar name
    face = os.path.join(a.work, "roster_face.png")
    Image.fromarray(poses_rgba[PORTRAIT_POSE]).crop(PORTRAIT_CROP).save(face)
    roster_portrait_patch.patch(rom4, face)
    hud_name_patch.patch(rom4)
    batman_moves_patch.patch(rom4)
    move_list_patch.patch(rom4)
    rom4 = bytes(rom4)
    frame_map = json.load(open(a.map))["frames"]
    report = {}
    rom = build(rom4, frame_map, json.load(open(a.ninja)), poses_rgba, report)
    open(a.out, "wb").write(rom)
    print(json.dumps({k: v for k, v in report.items() if k != "palette"}))


if __name__ == "__main__":
    main()
