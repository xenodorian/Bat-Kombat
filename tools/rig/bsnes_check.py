"""Run a ROM in the bsnes-mercury accuracy core (apt install libretro-bsnes-mercury-accuracy) from boot through
fighter select, the VS screen, the move list and four specials, and write a contact sheet.

Usage: python3 -I tools/rig/bsnes_check.py ROM OUT.png
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import libretro_harness as h, umk3_nav as nav
from PIL import Image
class B(h.Core):
    def _video(self, data, width, height, pitch):
        super()._video(data, width, height, pitch)
        if self.frame is not None and self.frame.shape[1] == 512:
            self.frame = self.frame[:, ::2].copy()
        if self.frame is not None and self.frame.shape[0] > 224:
            self.frame = self.frame[:224].copy()
def core(rom):
    c=B("/usr/lib/x86_64-linux-gnu/libretro/bsnes_mercury_accuracy_libretro.so"); c.load(os.path.abspath(rom)); return c
if __name__=="__main__":
    c=core(sys.argv[1]); shots=[]
    try:
        nav.to_fight_2p(c,0,0,settle=0)
        for i in range(1300):
            c.run(1)
            if i%110==100: shots.append(Image.fromarray(c.frame))
        K={"D":"DOWN","L":"LEFT","R":"RIGHT"}
        for seq,b in (("DR","Y"),("LL","B"),("DL","Y"),("DL","B")):
            c.run(50)
            for ch in seq: c.run(3,[K[ch]]); c.run(3)
            c.run(3,[b]); c.run(16); shots.append(Image.fromarray(c.frame))
        print("ok")
    except Exception as e:
        print("ERR",e); c.run(60); shots.append(Image.fromarray(c.frame))
    sh=Image.new("RGB",(256*8,224*2))
    for i,s in enumerate(shots[:16]): sh.paste(s,(256*(i%8),224*(i//8)))
    sh.save(sys.argv[2]); print(len(shots), shots[-1].size)
