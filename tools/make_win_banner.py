"""Compose the "BATMAN WINS" banner from the game's own banner letters.

Usage: python3 -I make_win_banner.py CAPTURE_DIR      (CAPTURE_DIR = output of capture_set_frames.py ROM DIR 19)
The win banners are frames of sprite set 19 (frame 1 KANO WINS, 11 KABAL WINS, 16 MOTARO WINS, ... 98 RAIN WINS).
The text is italic, so each row is shifted to make the letters upright, letters are cut at fixed columns,
joined, and the rows are shifted back. Output: art/batman_wins.png (palette index image, same indexes as the game).
"""
import os
import sys

import numpy as np
from PIL import Image

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H = 11                                  # banner text is 11 rows, object-local y -5..5
# (frame, first column, last column) in the upright image
LETTERS = [(11, 22, 32), (11, 33, 42), (16, 25, 32), (16, 2, 14), (1, 12, 21), (1, 22, 32)]   # B A T M A N
SPACE = 9
WINS = (1, 51, 91)


def shift(y):
    return (10 - y) // 3                # top rows lean right


def upright(d, frame):
    a = np.array(Image.open(os.path.join(d, "f%03d.png" % frame)))
    xs = np.nonzero(a)[1]
    a = a[176 - 5:176 + 6, xs.min():xs.max() + 1]
    out = np.zeros((H, a.shape[1] + 4), np.uint8)
    for y in range(H):
        out[y, 3 - shift(y):3 - shift(y) + a.shape[1]] = a[y]
    return out


def main(d):
    parts = [upright(d, f)[:, a:b + 1] for f, a, b in LETTERS]
    parts.append(np.zeros((H, SPACE), np.uint8))
    parts.append(upright(d, WINS[0])[:, WINS[1]:WINS[2] + 1])
    up = np.concatenate(parts, axis=1)
    out = np.zeros((H, up.shape[1] + 4), np.uint8)
    for y in range(H):
        out[y, shift(y):shift(y) + up.shape[1]] = up[y]
    im = Image.fromarray(out, "P")
    im.putpalette(sum(((17 * i, 17 * i, 17 * i) for i in range(16)), ()) + (0,) * (768 - 48))
    im.save(os.path.join(REPO, "art", "batman_wins.png"))
    print("wrote art/batman_wins.png", out.shape)


if __name__ == "__main__":
    main(sys.argv[1])
