"""SNES BRR sample tools: decode BRR to 16-bit PCM, encode PCM to BRR, and read a sample directory from sound RAM.

decode(data) -> list of int16; stops at the first block with the end flag.
encode(pcm, loop=False) -> bytes (9-byte blocks; filter chosen per block by least error; end flag on the last block).
directory(aram, dir_page, count) -> [(start, loop)]
"""
import struct


def _clamp16(v):
    return -32768 if v < -32768 else 32767 if v > 32767 else v


def _predict(flt, p1, p2):
    """Filter term as in snes9x/blargg SPC_DSP: p1, p2 are the previous two output samples (16-bit, doubled)."""
    q2 = p2 >> 1
    if flt == 0:
        return 0
    if flt == 1:
        return (p1 >> 1) + ((-p1) >> 5)
    if flt == 2:
        return p1 - q2 + (q2 >> 4) + ((p1 * -3) >> 6)
    return p1 - q2 + ((q2 * 3) >> 4) + ((p1 * -13) >> 7)


def _out(s):
    s = _clamp16(s)
    s = (s * 2) & 0xFFFF
    return s - 0x10000 if s & 0x8000 else s


def decode(data, start=0, max_blocks=20000):
    out, p1, p2, o = [], 0, 0, start
    for _ in range(max_blocks):
        if o + 9 > len(data):
            break
        h = data[o]
        rng, flt, end = h >> 4, (h >> 2) & 3, h & 1
        for b in data[o + 1:o + 9]:
            for nib in (b >> 4, b & 15):
                v = nib - 16 if nib > 7 else nib
                v = (v << rng) >> 1 if rng <= 12 else (-2048 if v < 0 else 0)
                v = _out(v + _predict(flt, p1, p2))
                p2, p1 = p1, v
                out.append(v)
        o += 9
        if end:
            break
    return out


def _block(samples, p1, p2, flt, rng):
    nibs, err = [], 0
    for x in samples:
        pred = _predict(flt, p1, p2)
        want = (x >> 1) - pred
        n = int(round(want * 2 / (1 << rng)))
        n = max(-8, min(7, n))
        v = _out(((n << rng) >> 1) + pred)
        err += (v - x) ** 2
        p2, p1 = p1, v
        nibs.append(n & 15)
    return nibs, err, p1, p2


def encode(pcm, loop=False):
    """PCM (int16 list) -> BRR. Filters 0-3 and ranges 0-12 are tried per block; the first block uses filter 0."""
    pcm = list(pcm) + [0] * (-len(pcm) % 16)
    out, p1, p2 = bytearray(), 0, 0
    for i in range(0, len(pcm), 16):
        best = None
        for flt in ((0,) if i == 0 else (0, 1, 2, 3)):
            for rng in range(13):
                nibs, err, a, b = _block(pcm[i:i + 16], p1, p2, flt, rng)
                if best is None or err < best[0]:
                    best = (err, flt, rng, nibs, a, b)
        _, flt, rng, nibs, p1, p2 = best
        h = rng << 4 | flt << 2 | (1 if i + 16 >= len(pcm) else 0) | (2 if loop else 0)
        out.append(h)
        out += bytes(nibs[k] << 4 | nibs[k + 1] for k in range(0, 16, 2))
    return bytes(out)


def directory(aram, dir_page, count):
    return [struct.unpack_from("<HH", aram, dir_page * 256 + 4 * k) for k in range(count)]
