"""Capture every frame of a fighter sprite set from the running game, as indexed images in object-local coordinates.

Usage: python3 -I capture_set_frames.py ROM OUT_DIR [set=27] [roster_col=0 roster_row=0]
Method: start a fight, then before each draw pass ($88:A520) force P1's sprite id ($7E:52F8) to set<<9|frame.
After the engine redraws, read the sprite table ($7E:C4AA) and video RAM, keep P1's sprites (name table 0,
tiles $30-$9F), and place them relative to the object origin. The origin is the offset that most sprite/piece pairs agree on, using the decoded ROM record
(tools/umk3_sprites.py); a frame is marked ok when every piece has a sprite at its expected position.
Writes OUT_DIR/fNNN.png (palette index image, 256x256, origin at (128,176)), frames.json and palette.json.
"""
import json
from collections import Counter
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dbg_core
import umk3_nav
import umk3_sprites
from PIL import Image

OX, OY, SIZE = 128, 176, 256


def tile_px(vram, n):
    t = vram[0xC000 + n * 32:0xC000 + n * 32 + 32]
    return [[((t[2*r] >> (7-c)) & 1) | ((t[2*r+1] >> (7-c)) & 1) << 1 | ((t[16+2*r] >> (7-c)) & 1) << 2 |
             ((t[17+2*r] >> (7-c)) & 1) << 3 for c in range(8)] for r in range(8)]


def sprite_px(vram, tile, size, hflip, vflip):
    if size == 8:
        px = tile_px(vram, tile)
    else:
        a, b, c, d = (tile_px(vram, tile + k) for k in (0, 1, 16, 17))
        px = [a[r] + b[r] for r in range(8)] + [c[r] + d[r] for r in range(8)]
    if hflip:
        px = [row[::-1] for row in px]
    if vflip:
        px = px[::-1]
    return px


def p1_sprites(wram):
    out = []
    for i in range(128):
        x, y, t, a = wram[0xC4AA + 4*i:0xC4AA + 4*i + 4]
        hi = (wram[0xC6AA + (i >> 2)] >> ((i & 3) * 2)) & 3
        if y >= 0xE0 or (a & 1) or not (0x30 <= t < 0xA0):
            continue
        x |= (hi & 1) << 8
        if x >= 256:
            x -= 512
        out.append(dict(x=x, y=y if y < 0xE0 else y - 256, tile=t, attr=a, size=16 if hi & 2 else 8))
    return out


def main(rom_path, out_dir, set_index=27, col=0, row=0):
    os.makedirs(out_dir, exist_ok=True)
    rom = open(rom_path, "rb").read()
    sset = umk3_sprites.SpriteSet(rom, set_index)
    c = dbg_core.DbgCore()
    c.load(rom_path)
    umk3_nav.to_fight(c, col, row)
    c.run(120, [])
    meta, pal_saved = {}, False
    for f in range(1, sset.frame_count() + 1):
        pieces, _ = sset.decode(f)
        sid = (set_index << 9) | f
        c.clear_pokes()
        c.poke_on_exec(0x88A520, 0x52F8, struct.pack("<H", sid))
        c.poke_on_exec(0x88A520, 0x3DA8, struct.pack("<H", 390))     # keep P1 mid-screen so nothing clips
        c.run(6, [])
        wram, vram = c.wram(), c.vram()
        spr = p1_sprites(wram)
        info = dict(pieces=len(pieces), sprites=len(spr), ok=False)
        if spr and pieces:
            # Other objects (blood, sparks) can share the tile range, so vote for the origin and match by position.
            votes = Counter((sp["x"] - p["x"], sp["y"] - p["y"]) for sp in spr for p in pieces if sp["size"] == p["size"])
            (ox, oy), _ = votes.most_common(1)[0]
            want = {(p["x"] + ox, p["y"] + oy, p["size"]) for p in pieces}
            spr = [sp for sp in spr if (sp["x"], sp["y"], sp["size"]) in want]
            info["sprites"] = len(spr)
            info["ok"] = len(spr) == len(pieces)
            img = Image.new("P", (SIZE, SIZE), 0)
            pix = img.load()
            minx = miny = 999; maxx = maxy = -999
            for s in reversed(spr):            # lower sprite index is drawn on top
                px = sprite_px(vram, s["tile"], s["size"], s["attr"] & 0x40, s["attr"] & 0x80)
                for r in range(s["size"]):
                    for q in range(s["size"]):
                        v = px[r][q]
                        if v:
                            lx, ly = s["x"] - ox + q, s["y"] - oy + r
                            X, Y = lx + OX, ly + OY
                            if 0 <= X < SIZE and 0 <= Y < SIZE:
                                pix[X, Y] = v
                                minx, maxx = min(minx, lx), max(maxx, lx)
                                miny, maxy = min(miny, ly), max(maxy, ly)
            pal_i = (spr[0]["attr"] >> 1) & 7
            words = struct.unpack_from("<16H", wram, 0xC100 + 32 * pal_i)
            flat = []
            for wd in words:
                flat += [(wd & 31) * 255 // 31, ((wd >> 5) & 31) * 255 // 31, ((wd >> 10) & 31) * 255 // 31]
            img.putpalette(flat + [0] * (768 - len(flat)))
            img.save(os.path.join(out_dir, "f%03d.png" % f))
            info.update(bbox=[minx, miny, maxx, maxy], pal=pal_i,
                        n16=sum(1 for p in pieces if p["size"] == 16))
            if not pal_saved:
                json.dump(list(words), open(os.path.join(out_dir, "palette.json"), "w")); pal_saved = True
        meta[f] = info
    json.dump(meta, open(os.path.join(out_dir, "frames.json"), "w"), indent=0)
    good = sum(1 for v in meta.values() if v["ok"])
    print("frames %d, decoded-and-matched %d" % (len(meta), good))
    print("not matched:", [k for k, v in meta.items() if not v["ok"]][:60])


if __name__ == "__main__":
    a = sys.argv
    main(a[1], a[2], *(int(v) for v in a[3:]))
