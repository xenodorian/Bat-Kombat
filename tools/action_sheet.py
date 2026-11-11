"""Play a list of actions as P1 (roster cell 0,0) against an idle P2 and save a labeled contact sheet.

Usage: python3 -I action_sheet.py ROM OUT.png
Each cell is the frame where P1's silhouette is widest or tallest during the action (a cheap way to catch the key pose).
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import libretro_harness as h
import umk3_nav

CORE = os.environ.get("DBG_CORE", "/opt/snes9x_dbg/snes9x_dbg_libretro.so")
ACTIONS = [
    ("stance", [(30, [])], 29), ("walk", [(30, ["RIGHT"])], 20), ("walk back", [(40, ["LEFT"])], 30),
    ("crouch", [(30, ["DOWN"])], 25), ("block (L)", [(25, ["L"])], 20), ("crouch block", [(30, ["DOWN", "L"])], 25),
    ("jump", [(28, ["UP"])], 22), ("jump fwd", [(8, ["UP", "RIGHT"]), (30, [])], 24), ("run", [(30, ["R", "RIGHT"])], 20),
    ("high punch Y", [(4, ["Y"]), (20, [])], 9), ("low punch B", [(4, ["B"]), (20, [])], 9),
    ("high kick X", [(4, ["X"]), (25, [])], 13), ("low kick A", [(4, ["A"]), (25, [])], 13),
    ("uppercut", [(10, ["DOWN"]), (4, ["DOWN", "Y"]), (30, [])], 22), ("crouch punch", [(10, ["DOWN"]), (4, ["DOWN", "B"]), (20, ["DOWN"])], 18),
    ("crouch kick", [(10, ["DOWN"]), (4, ["DOWN", "X"]), (20, ["DOWN"])], 20), ("roundhouse", [(4, ["LEFT", "X"]), (40, [])], 20),
    ("sweep", [(4, ["LEFT", "A"]), (40, [])], 18), ("jump kick", [(8, ["UP", "RIGHT"]), (10, []), (4, ["X"]), (20, [])], 26),
    ("jump punch", [(4, ["UP"]), (14, []), (4, ["Y"]), (16, [])], 22),
]


def main(rom, out):
    c = h.Core(CORE)
    c.load(rom)
    umk3_nav.to_fight_2p(c, 0, 0)
    c.run2(40, ["LEFT"], ["RIGHT"])
    cells = []
    for name, steps, pick in ACTIONS:
        c.run(60)
        n, shot = 0, None
        for frames, b1 in steps:
            for _ in range(frames):
                c.run2(1, b1, [])
                n += 1
                if n == pick:
                    shot = c.frame.copy()
        cells.append((name, shot if shot is not None else c.frame.copy()))
    cols = 5
    rows = (len(cells) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * 256, rows * 224), (0, 0, 0))
    d = ImageDraw.Draw(sheet)
    for i, (name, fr) in enumerate(cells):
        x, y = (i % cols) * 256, (i // cols) * 224
        sheet.paste(Image.fromarray(fr), (x, y))
        d.rectangle((x, y + 212, x + 6 * len(name) + 6, y + 223), fill=(0, 0, 0))
        d.text((x + 3, y + 212), name, fill=(255, 255, 0))
    sheet.save(out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
