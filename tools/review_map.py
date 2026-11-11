"""Side-by-side review sheets: each mapped ninja frame (left) next to the Batman pose that replaces it (right),
both drawn in object-local coordinates with the origin cross and the ground line.

Usage: python3 -I review_map.py NINJA_CAPTURE_DIR OUT_PREFIX [first last]
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import batman_art as ba
from build_batman import CAP_ORIGIN, REPO

CW, CH, OX, OY = 190, 150, 48, 104


def main(ninja_dir, prefix, first=1, last=249):
    fmap = json.load(open(os.path.join(REPO, "art", "batman_frame_map.json")))["frames"]
    geom = json.load(open(os.path.join(REPO, "art", "ninja_frames.json")))
    poses = ba.load_poses(os.path.join(REPO, "art", "batman_poses.tar.gz"), os.path.join(REPO, "build", "poses"))
    frames = [f for f in range(first, last + 1) if str(f) in fmap]
    per, cols = 42, 6
    for s in range((len(frames) + per - 1) // per):
        sheet = Image.new("RGB", (CW * cols, CH * 7), (95, 95, 120))
        d = ImageDraw.Draw(sheet)
        for k, f in enumerate(frames[s * per:(s + 1) * per]):
            cx, cy = (k % cols) * CW, (k // cols) * CH
            m = fmap[str(f)]
            nin = Image.open(os.path.join(ninja_dir, "f%03d.png" % f)); nin.load()
            mask = np.array(nin) > 0
            sil = Image.fromarray((mask * 255).astype("uint8"))
            sheet.paste((230, 200, 120), (cx + OX - CAP_ORIGIN[0], cy + OY - CAP_ORIGIN[1]), sil)
            pose = Image.fromarray(poses[int(m["pose"])])
            fx, fy = ba.body_anchor(np.array(pose))
            nx, ny = geom[str(f)]["anchor"]
            bx = cx + OX + 92 + nx - fx + int(m.get("dx", 0))
            if ny < ba.AIRBORNE_BOTTOM:
                by = cy + OY + geom[str(f)]["cy"] - ba.centre_row(np.array(pose)[:, :, 3] > 127) + int(m.get("dy", 0))
            else:
                by = cy + OY + ny - fy + int(m.get("dy", 0))
            sheet.paste(pose, (bx, by), pose)
            for ox in (OX, OX + 92):
                d.line((cx + ox - 3, cy + OY, cx + ox + 3, cy + OY), fill=(255, 255, 0))
                d.line((cx + ox, cy + OY - 3, cx + ox, cy + OY + 3), fill=(255, 255, 0))
            d.line((cx, cy + OY + 41, cx + CW - 1, cy + OY + 41), fill=(70, 70, 90))
            d.rectangle((cx, cy, cx + CW - 1, cy + CH - 1), outline=(60, 60, 80))
            d.text((cx + 3, cy + 2), "%d > %d %s" % (f, m["pose"], "" if m.get("src") == "explicit" else "(shape)"), fill=(255, 255, 255))
        out = "%s%d.png" % (prefix, s)
        sheet.save(out)
        print(out)


if __name__ == "__main__":
    a = sys.argv
    main(a[1], a[2], *(int(v) for v in a[3:]))
