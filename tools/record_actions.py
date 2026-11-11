"""Record which sprite frames P1 shows for each action, in a two-player match with an idle opponent.

Usage: python3 -I record_actions.py ROM OUT.json
For each named action the controller script runs from a neutral stance and the P1 sprite id ($7E:52F8) is sampled
every frame. Output: {action: [frame numbers in order of first appearance]} plus "all" (every frame seen).
"""
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import libretro_harness as h
import umk3_nav

CORE = os.environ.get("DBG_CORE", "/opt/snes9x_dbg/snes9x_dbg_libretro.so")

# (name, [(frames, P1 buttons, P2 buttons)])
ACTIONS = [
    ("stance", [(90, [], [])]),
    ("walk_forward", [(50, ["RIGHT"], [])]),
    ("walk_back", [(50, ["LEFT"], [])]),
    ("crouch", [(40, ["DOWN"], [])]),
    ("jump_up", [(70, ["UP"], [])]),
    ("jump_forward", [(8, ["UP", "RIGHT"], []), (70, [], [])]),
    ("jump_back", [(8, ["UP", "LEFT"], []), (70, [], [])]),
    ("btn_Y", [(4, ["Y"], []), (40, [], [])]),
    ("btn_B", [(4, ["B"], []), (40, [], [])]),
    ("btn_X", [(4, ["X"], []), (40, [], [])]),
    ("btn_A", [(4, ["A"], []), (40, [], [])]),
    ("btn_L", [(30, ["L"], [])]),
    ("btn_R", [(30, ["R"], [])]),
    ("run_forward", [(40, ["R", "RIGHT"], [])]),
    ("crouch_Y", [(10, ["DOWN"], []), (4, ["DOWN", "Y"], []), (50, [], [])]),
    ("crouch_B", [(10, ["DOWN"], []), (4, ["DOWN", "B"], []), (40, ["DOWN"], [])]),
    ("crouch_X", [(10, ["DOWN"], []), (4, ["DOWN", "X"], []), (40, ["DOWN"], [])]),
    ("crouch_A", [(10, ["DOWN"], []), (4, ["DOWN", "A"], []), (40, ["DOWN"], [])]),
    ("crouch_L", [(10, ["DOWN"], []), (30, ["DOWN", "L"], [])]),
    ("back_X", [(4, ["LEFT", "X"], []), (50, [], [])]),
    ("back_A", [(4, ["LEFT", "A"], []), (50, [], [])]),
    ("jump_Y", [(4, ["UP"], []), (14, [], []), (4, ["Y"], []), (60, [], [])]),
    ("jump_X", [(4, ["UP"], []), (14, [], []), (4, ["X"], []), (60, [], [])]),
    ("jumpf_X", [(8, ["UP", "RIGHT"], []), (10, [], []), (4, ["X"], []), (60, [], [])]),
    ("jumpf_Y", [(8, ["UP", "RIGHT"], []), (10, [], []), (4, ["Y"], []), (60, [], [])]),
]


def main(rom, out):
    c = h.Core(CORE)
    c.load(rom)
    umk3_nav.to_fight_2p(c, 0, 0)
    res, allf = {}, []

    def sample(seq):
        w = c.wram()
        sid = struct.unpack_from("<H", w, 0x52F8)[0]
        f = sid & 0x1FF
        if (sid >> 9) == 27 and (not seq or seq[-1] != f):
            seq.append(f)

    for name, steps in ACTIONS:
        c.run(50)
        seq = []
        for frames, b1, b2 in steps:
            for _ in range(frames):
                c.run2(1, b1, b2)
                sample(seq)
        order = []
        for f in seq:
            if f not in order:
                order.append(f)
        res[name] = dict(order=order, sequence=seq[:80])
        allf += [f for f in order if f not in allf]
        print(name, order)
    res["all"] = sorted(allf)
    json.dump(res, open(out, "w"), indent=1)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
