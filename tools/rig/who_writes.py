"""Log the code that writes (or reads) a RAM or ROM range while an input is held.

    python3 who_writes.py ROM 7E3C38 [7E3C39] [--read] [--p1 RIGHT] [--p2 ...] [--frames 30]

Prints each distinct (address, PC, A, X, Y, D) with a count. D is the thread's direct page, so it tells which
fighter thread did it (UMK3: D=$0600 is player 1's main thread). Chain it: find the writer, disassemble it with
tools/dis65.py, see where A came from, watch that address next.
"""
import argparse, collections, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lab


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rom"); ap.add_argument("lo"); ap.add_argument("hi", nargs="?")
    ap.add_argument("--read", action="store_true"); ap.add_argument("--exec", action="store_true", help="lo is a code address")
    ap.add_argument("--p1", nargs="*", default=[]); ap.add_argument("--p2", nargs="*", default=[])
    ap.add_argument("--pre", type=int, default=0, help="frames to hold the input before logging starts")
    ap.add_argument("--frames", type=int, default=30)
    a = ap.parse_args()
    lo = int(a.lo, 16); hi = int(a.hi, 16) if a.hi else lo
    c = lab.fight(os.path.abspath(a.rom))
    c.run2(a.pre, a.p1, a.p2)
    c.reset_hooks()
    (c.watch_exec(lo) if a.exec else c.watch_read(lo, hi) if a.read else c.watch_write(lo, hi))
    cnt = collections.Counter()
    for _ in range(a.frames):
        c.run2(1, a.p1, a.p2)
        for e in c.log(400000):
            cnt[(e["type"], e["addr"], e["pc"], e["a"], e["x"], e["y"], e["d"])] += 1
    for k, v in sorted(cnt.items(), key=lambda kv: (kv[0][2], kv[0][1])):
        print("%s %06X pc %06X a %04X x %04X y %04X d %04X  x%d" % (k + (v,)))


if __name__ == "__main__":
    main()
