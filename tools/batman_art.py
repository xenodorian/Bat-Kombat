"""Batman art preparation for the UMK3 sprite engine: palette, pose loading, and piece packing.

Poses come from art/batman_poses.tar.gz (RGBA PNGs ripped from Batman Returns, facing right).
The fighter palette has index 0 transparent, index 1 black (the game keeps it at $0000) and indexes 2-15 free.
A fighter owns 64 tiles of video RAM (the round banner text sits right after), so every frame must fit:
4 tiles per 16x16 piece plus 1 per 8x8 piece <= 64, in the slot order the engine uses (see slots()).
"""
import functools
import json
import os
import tarfile

import numpy as np
from PIL import Image

MAX_TILES = 64
N_COLOURS = 14          # palette indexes 2..15
BLACK_INDEX = 1


def load_poses(tar_path, work_dir):
    """Extract the archive (once) and return {pose index: RGBA numpy array}."""
    marker = os.path.join(work_dir, "frames.json")
    if not os.path.exists(marker):
        os.makedirs(work_dir, exist_ok=True)
        with tarfile.open(tar_path) as t:
            t.extractall(work_dir, filter="data")
    meta = json.load(open(marker))
    return {e["i"]: np.array(Image.open(os.path.join(work_dir, "frames", e["file"])).convert("RGBA")) for e in meta}


def _snes(c):
    """Round an RGB triple to what a 15-bit SNES colour can show."""
    return tuple(int(round(v / 255 * 31)) * 255 // 31 for v in c)


def build_palette(poses, use):
    """Pick N_COLOURS colours for the poses in `use`. Returns list of 16 RGB triples (index 0 unused, 1 black)."""
    counts = {}
    for i in use:
        a = poses[i]
        px = a[a[:, :, 3] > 127][:, :3]
        cols, n = np.unique(px, axis=0, return_counts=True)
        for c, k in zip(cols, n):
            counts[tuple(int(v) for v in c)] = counts.get(tuple(int(v) for v in c), 0) + int(k)
    cols = np.array([c for c in counts if max(c) > 20], float)          # near-black goes to index 1
    wts = np.array([counts[tuple(int(v) for v in c)] for c in cols], float) ** 0.5
    # farthest-point start, then weighted k-means
    centres = [cols[np.argmax(wts)]]
    while len(centres) < N_COLOURS:
        d = np.min([((cols - c) ** 2).sum(1) for c in centres], axis=0)
        centres.append(cols[np.argmax(d * wts)])
    centres = np.array(centres)
    for _ in range(40):
        lab = np.argmin(((cols[:, None, :] - centres[None]) ** 2).sum(2), axis=1)
        for k in range(N_COLOURS):
            m = lab == k
            if m.any():
                centres[k] = (cols[m] * wts[m, None]).sum(0) / wts[m].sum()
    centres = sorted((_snes(c) for c in centres), key=lambda c: 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2])
    return [(0, 0, 0), (0, 0, 0)] + centres


def to_indexed(rgba, palette):
    """RGBA array -> uint8 index array (0 = transparent)."""
    pal = np.array(palette[1:], float)                       # indexes 1..15
    rgb = rgba[:, :, :3].astype(float)
    d = ((rgb[:, :, None, :] - pal[None, None]) ** 2).sum(3)
    idx = (np.argmin(d, axis=2) + 1).astype(np.uint8)
    idx[rgba[:, :, 3] <= 127] = 0
    return idx


def palette_words(palette):
    """16 SNES colour words (BGR555). Index 0 and 1 stay $0000 as in the original fighter palettes."""
    out = []
    for i, (r, g, b) in enumerate(palette):
        out.append(0 if i < 2 else ((b * 31 // 255) << 10) | ((g * 31 // 255) << 5) | (r * 31 // 255))
    return out


# ---------------------------------------------------------------- piece packing

def _greedy(cols_occupied, width):
    """Minimal set of `width`-wide intervals covering all occupied columns. Returns start columns."""
    out, x, n = [], 0, len(cols_occupied)
    while x < n:
        if cols_occupied[x]:
            out.append(x)
            x += width
        else:
            x += 1
    return out


def _tighten(mask, p8):
    """Slide each 8x8 piece so it hugs its own pixels (keeps those pixels covered)."""
    h, w = mask.shape
    out = []
    for x, y in p8:
        sub = mask[max(y, 0):min(y + 8, h), max(x, 0):min(x + 8, w)]
        ys, xs = np.nonzero(sub)
        out.append((max(x, 0) + int(xs.min()), max(y, 0) + int(ys.min())))
    return out


def importance(idx):
    """Per-pixel weight used when a pose must be trimmed: dark cape pixels go first, the head last."""
    w = np.where(idx <= 2, 1.0, np.where(idx == 3, 3.0, 6.0))
    w[: max(1, idx.shape[0] // 4)] *= 3.0
    return w


def _count(mask, x, y, size):
    h, w = mask.shape
    return mask[max(y, 0):max(min(y + size, h), 0), max(x, 0):max(min(x + size, w), 0)]


def _bands(mask, phase):
    """For each 16-row band: option A = shared 16-wide columns (allows 16x16 pieces), option B = two free 8-row strips."""
    h, w = mask.shape
    out = []
    for y0 in range(-phase, h, 16):
        band = mask[max(y0, 0):max(min(y0 + 16, h), 0)]
        if not band.size or not band.any():
            continue
        boxes = []
        for x0 in _greedy(band.any(axis=0), 16):
            quads = [(x0 + qx, y0 + qy) for qy in (0, 8) for qx in (0, 8) if _count(mask, x0 + qx, y0 + qy, 8).any()]
            boxes.append((x0, y0, quads))
        strips = []
        for ys in (y0, y0 + 8):
            st = mask[max(ys, 0):max(min(ys + 8, h), 0)]
            if st.size and st.any():
                strips += [(x, ys) for x in _greedy(st.any(axis=0), 8)]
        out.append(dict(boxes=boxes, strips=strips, a_tiles=sum(len(q) for _, _, q in boxes), b_tiles=len(strips)))
    return out


def _assemble(bands, use_b, merge3):
    p16, p8 = [], []
    for band, b in zip(bands, use_b):
        if b:
            p8 += band["strips"]
            continue
        for x0, y0, quads in band["boxes"]:
            if len(quads) == 4 or (merge3 and len(quads) == 3):
                p16.append((x0, y0))
            else:
                p8 += quads
    return p16, p8


def pack(idx, weight=None):
    """Choose 16x16 and 8x8 pieces covering the opaque pixels of an index image, within the tile limit.

    weight: per-pixel importance (same shape as idx). When the pose cannot fit, the pieces holding the least
    total weight are dropped. Returns dict(p16=[(x,y)], p8=[(x,y)], lost=opaque pixels dropped).
    Coordinates are image pixels (top-left of each piece); pieces may overhang the image.
    """
    mask = idx > 0
    wgt = mask.astype(float) if weight is None else weight * mask
    best = None
    for phase in range(16):
        bands = _bands(mask, phase)
        for merge3 in (True, False):
            use_b = [False] * len(bands)
            while True:
                p16, p8 = _assemble(bands, use_b, merge3)
                if fits(len(p16), len(p8)):
                    break
                gain = [(bd["a_tiles"] - bd["b_tiles"], i) for i, bd in enumerate(bands) if not use_b[i]]
                gain = [g for g in gain if g[0] > 0]
                if not gain:
                    break
                use_b[max(gain)[1]] = True
            p16, p8 = list(p16), list(p8)
            lost_w, lost = 0.0, 0
            while not fits(len(p16), len(p8)):
                if p8:
                    k = min(range(len(p8)), key=lambda i: float(_count(wgt, *p8[i], 8).sum()))
                    lost_w += float(_count(wgt, *p8[k], 8).sum())
                    lost += int(_count(mask, *p8[k], 8).sum())
                    p8.pop(k)
                else:
                    k = min(range(len(p16)), key=lambda i: float(_count(wgt, *p16[i], 16).sum()))
                    x, y = p16.pop(k)
                    p8 += [(x + qx, y + qy) for qy in (0, 8) for qx in (0, 8) if _count(mask, x + qx, y + qy, 8).any()]
            key = (lost_w, len(p16) + len(p8))
            if best is None or key < best[0]:
                best = (key, p16, p8, lost)
    _, p16, p8, lost = best
    return dict(p16=p16, p8=_tighten(mask, p8) if p8 else [], lost=lost)


def render(idx, packed):
    """Index image as the engine would show it: only pixels covered by a piece survive."""
    h, w = idx.shape
    keep = np.zeros((h, w), bool)
    for size, lst in ((16, packed["p16"]), (8, packed["p8"])):
        for x, y in lst:
            keep[max(y, 0):max(min(y + size, h), 0), max(x, 0):max(min(x + size, w), 0)] = True
    return np.where(keep, idx, 0)


# ---------------------------------------------------------------- engine slot model

_ROM = None


def init_slots(rom):
    """Give the packer the ROM so slot allocation uses the engine's own tables."""
    global _ROM
    _ROM = rom
    _slots_cached.cache_clear()


def slots(n16, n8):
    """Tile slots (in tiles, relative to the object's first tile) in the order the engine hands them out.

    Mirrors the decoder at $83:8000: 16x16 pieces step through the word list at $86:E36A; 8x8 pieces start at
    $86:E3DA[n16] and step through the list that $86:E67C[n16] points to.
    """
    return _slots_cached(n16, n8)


@functools.lru_cache(maxsize=None)
def _slots_cached(n16, n8):
    rom = _ROM
    w = lambda o: rom[o] | rom[o + 1] << 8
    a, s16 = 0, []
    for k in range(n16):
        s16.append(a // 32)
        a = (a + w(0x06E36A + 2 * k)) & 0xFFFF
    e, lst, s8 = w(0x06E3DA + 2 * n16), 0x060000 | w(0x06E67C + 2 * n16), []
    for k in range(n8):
        s8.append(e // 32)
        e = (e + w(lst + 2 * k)) & 0xFFFF
    return tuple(s16), tuple(s8)


def fits(n16, n8):
    if n16 > 16 or 4 * n16 + n8 > MAX_TILES:
        return False
    s16, s8 = slots(n16, n8)
    used = set()
    for t in s16:
        used |= {t, t + 1, t + 16, t + 17}
    if len(used) != 4 * n16 or (used and max(used) >= MAX_TILES):
        return False
    for t in s8:
        if t in used or t >= MAX_TILES:
            return False
        used.add(t)
    return True
