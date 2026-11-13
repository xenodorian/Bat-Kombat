"""Trace UMK3's animation sleeps for one fighter thread: which frame waits how long, and who counts it.

    python3 sleep_trace.py ROM --p1 Y [--p2 ...] [--d 0600] [--frames 50] [--approach 0]

UMK3 move code shows a sprite frame and then sleeps with $88:C637 (A = frames). Counted holds go through
$86:8B7E (A = count, one 1-frame sleep per count, hit test each frame). Prints (game frame, routine, A, sprite
frame) for the thread with direct page D (player 1's main thread is $0600). A is the value the move code
passes, before tools/batman_timing_patch.py rewrites it. This is what
tools/batman_timing_patch.py ROWS are written from.
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lab

NAMES = {0x88C637: "sleep", 0x868B7E: "hold-loop", 0x888C42: "hold-loop2"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rom"); ap.add_argument("--p1", nargs="*", default=[]); ap.add_argument("--p2", nargs="*", default=[])
    ap.add_argument("--d", default="0600"); ap.add_argument("--frames", type=int, default=50)
    ap.add_argument("--hold", type=int, default=6); ap.add_argument("--approach", type=int, default=0)
    a = ap.parse_args()
    c = lab.fight(os.path.abspath(a.rom))
    if a.approach:
        c.run2(a.approach, ["RIGHT"], []); c.run2(10, [], [])
    c.reset_hooks()
    for addr in NAMES:
        c.watch_exec(addr)
    dp = int(a.d, 16)
    for i in range(a.frames):
        c.run2(1, a.p1 if i < a.hold else [], a.p2 if i < a.hold else [])
        for e in c.log():
            if e["d"] == dp:
                print("frame %3d  %-10s A=%3d  sprite frame %d" % (i, NAMES.get(e["pc"], "%06X" % e["pc"]), e["a"],
                                                                   c.w16(0x52F8) & 0x1FF))


if __name__ == "__main__":
    main()
