"""Find work-RAM words that move steadily while an input is held (positions, timers, counters).

    python3 ram_scan.py ROM [--p1 RIGHT] [--p2 ...] [--frames 50] [--settle 20]

Starts from the cached two-player fight (lab.fight), holds the input, then idles. Reports every word in all
128 KB of work RAM whose per-frame change is one-signed, non-zero on most frames, adds up to a moderate total,
and stays put once the input is released. Example: holding RIGHT found Batman's X at $7E:3DA8 (+ copies).
"""
import argparse, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lab


def snap(c):
    w = np.frombuffer(c.wram(), np.uint8).astype(np.int64)
    return w[:-1] + 256 * w[1:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rom"); ap.add_argument("--p1", nargs="*", default=["RIGHT"]); ap.add_argument("--p2", nargs="*", default=[])
    ap.add_argument("--frames", type=int, default=50); ap.add_argument("--settle", type=int, default=20)
    ap.add_argument("--skip", type=int, default=10, help="ignore the first frames (acceleration, start-up)")
    a = ap.parse_args()
    c = lab.fight(os.path.abspath(a.rom))
    held = []
    for _ in range(a.frames):
        c.run2(1, a.p1, a.p2); held.append(snap(c))
    idle = []
    for _ in range(a.settle):
        c.run2(1, [], []); idle.append(snap(c))
    d = np.diff(np.array(held), axis=0)[a.skip:]
    d = (d + 32768) % 65536 - 32768                              # signed 16-bit deltas
    di = np.diff(np.array(idle), axis=0)
    for addr in range(d.shape[1]):
        col = d[:, addr]
        if not (8 <= abs(col.sum()) <= 64 * len(col)):
            continue
        if not ((col >= 0).all() or (col <= 0).all()) or (col != 0).mean() < 0.5:
            continue
        if (di[:, addr] != 0).any():
            continue
        print("$7E:%04X" % addr if addr < 0x10000 else "$7F:%04X" % (addr - 0x10000),
              "%.3f per frame" % (col.sum() / len(col)), col[:16].tolist())


if __name__ == "__main__":
    main()
