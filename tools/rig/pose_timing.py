"""How long each sprite frame is shown during an action: the numbers to compare with another game's animation.

    python3 pose_timing.py ROM                      # the standard set: buttons, specials, being hit
    python3 pose_timing.py ROM --p1 Y --hold 6      # one action
    python3 pose_timing.py ROM --seq DR --p1 Y      # a motion (U D L R, facing right) then the button

Prints [sprite frame, frames shown] runs for player 1 (sprite id $7E:52F8 & $1FF), plus the X travel and the
lowest Y reached (jumps). For "being hit" runs, player 1 first walks up to player 2 (--approach frames).
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lab

D = {"L": "LEFT", "R": "RIGHT", "D": "DOWN", "U": "UP"}
STANDARD = [("", ["Y"], [], 0), ("", ["B"], [], 0), ("", ["A"], [], 0), ("", ["X"], [], 0), ("", ["L"], [], 0),
            ("", ["R"], [], 0), ("", ["B", "Y"], [], 0), ("DL", ["Y"], [], 0), ("LL", ["Y"], [], 0), ("DR", ["Y"], [], 0),
            ("", [], ["Y"], 110), ("", [], ["X"], 110)]


def runs(c, base, seq, p1, p2, approach, hold, n):
    c.restore(base)
    if approach:
        c.run2(approach, ["RIGHT"], []); c.run2(10, [], [])
    for ch in seq:
        c.run2(3, [D[ch]], []); c.run2(3, [], [])
    out, x0, ymin = [], c.w16(0x3DA8), 9999
    for i in range(n):
        c.run2(1, p1 if i < hold else [], p2 if i < hold else [])
        s = c.w16(0x52F8) & 0x1FF
        ymin = min(ymin, c.w16(0x3F18))
        if out and out[-1][0] == s:
            out[-1][1] += 1
        else:
            out.append([s, 1])
    return out, c.w16(0x3DA8) - x0, ymin


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rom"); ap.add_argument("--seq", default=""); ap.add_argument("--p1", nargs="*"); ap.add_argument("--p2", nargs="*", default=[])
    ap.add_argument("--hold", type=int, default=6); ap.add_argument("--frames", type=int, default=90); ap.add_argument("--approach", type=int, default=0)
    a = ap.parse_args()
    c = lab.fight(os.path.abspath(a.rom)); base = c.save()
    tests = [(a.seq, a.p1 or [], a.p2, a.approach)] if (a.p1 is not None or a.p2) else STANDARD
    for seq, p1, p2, appr in tests:
        r, dx, ymin = runs(c, base, seq, p1, p2, appr, a.hold, a.frames)
        print("%-3s p1=%-12s p2=%-6s dx %4d  min y %3d  %s" % (seq, "+".join(p1), "+".join(p2), dx, ymin, r[:20]))


if __name__ == "__main__":
    main()
