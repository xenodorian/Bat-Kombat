"""Liveness check: replay a seeded random two-player input run (tools/rig/replay.py), then idle 300 frames and count
frames in which the CPU still runs code from ROM. A dead game runs from RAM or I/O space. Frame-identity checks miss
this: a crashed game can still change the picture. Usage: python3 liveness.py SEED ROM [ROM...]
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lab, replay
def bad(pc):
    b,a=(pc>>16)&0x7F,pc&0xFFFF; return b in (0x7E,0x7F) or (b<0x40 and a<0x8000)
def test(rom, seed, total=3000):
    c=lab.fight(os.path.abspath(rom))
    for i,(b1,b2) in enumerate(replay.frames(seed,total)): c.run2(1,b1,b2)
    c.watch_read(0xC00000,0xFFFFFF); ok=0
    for k in range(300):
        c.run2(1,[],[]); lg=c.log(400000)
        if lg and not all(bad(e['pc']) for e in lg): ok+=1
    return ok
if __name__=="__main__":
    for rom in sys.argv[2:]: print(rom,"seed",sys.argv[1],"frames with ROM code running in last 300:",test(rom,int(sys.argv[1])))
