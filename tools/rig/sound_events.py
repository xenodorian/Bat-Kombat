"""What UMK3 asks the sound CPU to play during an action, and what the DSP actually keys on.

    python3 sound_events.py ROM --p1 Y [--p2 ...] [--frames 60] [--hold 4]

Sound requests: every one passes $84:FE62 with A = address of an [id, priority] pair in bank $86; the id
is printed. Key-ons: DSP register $4C writes (needs the debug core's DSP logging, tools/snes9x_dbg.patch), with
each keyed voice's sample number (SRCN), pitch and volume at that moment. See tools/batman_sound_patch.py.
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lab


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rom"); ap.add_argument("--p1", nargs="*", default=[]); ap.add_argument("--p2", nargs="*", default=[])
    ap.add_argument("--frames", type=int, default=60); ap.add_argument("--hold", type=int, default=4)
    a = ap.parse_args()
    rom = open(os.path.abspath(a.rom), "rb").read()
    c = lab.fight(os.path.abspath(a.rom))
    c.reset_hooks(); c.watch_exec(0x84FE62); c.watch_dsp(True); c.log(400000)
    regs = [[0] * 16 for _ in range(8)]
    for i in range(a.frames):
        c.run2(1, a.p1 if i < a.hold else [], a.p2 if i < a.hold else [])
        for e in c.log(400000):
            if e["type"] == "X":
                p = e["a"] & 0xFFFF
                print("frame %3d  request id $%02X (pair at $86:%04X, thread D=$%04X)" % (i, rom[0x060000 | p], p, e["d"]))
            elif e["type"] == "D":
                r, v = e["addr"], e["val"]
                if r < 0x80 and (r & 0x0F) < 10:
                    regs[r >> 4][r & 0x0F] = v
                if r == 0x4C and v:
                    for k in range(8):
                        if v >> k & 1:
                            p = regs[k][2] | regs[k][3] << 8
                            print("frame %3d  key on voice %d  sample %d  pitch $%04X (%.0f Hz)  vol %d %d"
                                  % (i, k, regs[k][4], p, p / 4096 * 32000, regs[k][0], regs[k][1]))


if __name__ == "__main__":
    main()
