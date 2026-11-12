"""Finisher test rig: reach FINISH HIM by poking P2 health ($7E:3898) to 1 and kicking, then film an input.

    c = fat.finish_state(rom); st = c.save(); fat.film(c, st, "DDR", "X", "out.png")
Buttons: Y high punch, B low punch, X high kick, A low kick. Directions: L R U D (facing right).
"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lab
from PIL import Image
D={'L':"LEFT",'R':"RIGHT",'D':"DOWN",'U':"UP"}
def finish_state(rom):
    f=rom+".fin.st"
    c=lab.fight(os.path.abspath(rom))
    if os.path.exists(f):
        c.restore(open(f,"rb").read()); return c
    hp2=lambda: c.w16(0x3898)
    for rnd in range(2):
        c.run2(60,["RIGHT"],[])
        for k in range(40):
            c.poke_wram(0x3898, struct.pack("<H",1))
            c.run2(4,["X"],[]); c.run2(16,[],[])
            if hp2()==0 or hp2()>100: break
        if rnd==0:
            for i in range(700):
                c.run2(1,[],[])
                if hp2()>100 and i>200: break
            c.run2(200,[],[])
    c.run2(25,[],[])
    open(f,"wb").write(c.save()); return c
def patch_words(src,dst,f1,f2):
    r=bytearray(open(src,"rb").read())
    for base in (0,0x400000):
        struct.pack_into("<H",r,base+0x2802D+48,f1); struct.pack_into("<H",r,base+0x28065+48,f2)
    open(dst,"wb").write(r)
def film(c,st,seq,btn,out,frames=600,cols=8,rows=3):
    c.restore(st)
    for ch in seq: c.run2(3,[D[ch]],[]); c.run2(3,[],[])
    c.run2(4,[btn],[])
    shots=[]
    for i in range(frames):
        c.run2(1,[],[]); shots.append(Image.fromarray(c.frame))
    n=cols*rows; sh=Image.new("RGB",(256*cols,224*rows))
    for k in range(n): sh.paste(shots[min(len(shots)-1,5+k*(frames//n))],(256*(k%cols),224*(k//cols)))
    sh.save(out)
if __name__=="__main__":
    f1,f2=int(sys.argv[1],16),int(sys.argv[2],16)
    patch_words("bat_f.sfc","bat_ft.sfc",f1,f2)
    c0=finish_state("bat_f.sfc"); st=c0.save()
    c=lab.Lab(); c.load(os.path.abspath("bat_ft.sfc")); c.run(5)
    film(c,st,"DDR","X","f_%04X.png"%f1)
    film(c,st,"RRD","B","f_%04X.png"%f2)
