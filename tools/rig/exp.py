"""Special-move film rig (make() edits Rain's original HP table on the 4 MB ROM for experiments).
exp.py "[(typ,cond,h,seq,button),...]" out.png [bat]  : put moves in Rain's HP table (max 3) and film them."""
import lab, struct, sys, subprocess, os
from PIL import Image
D={'L':"LEFT",'R':"RIGHT",'D':"DOWN",'U':"UP"}
def rec(rom, off, btn, typ, cond, h, win, seq):
    code={'U':6,'D':7,'L':8,'R':9}; mir={'L':'R','R':'L','U':'U','D':'D'}
    a=bytes(code[c] for c in reversed(seq)).ljust(6,b'\0'); b=bytes(code[mir[c]] for c in reversed(seq)).ljust(6,b'\0')
    rom[off:off+0x15]=struct.pack("<HHHHB",btn,typ,cond,h,win)+a+b
def make(moves, bat, extra=None):
    rom=bytearray(open(lab.ORIG,'rb').read())
    for i,m in enumerate(moves):
        rec(rom,0x2EA93+0x15*i,0x30,m[0],m[1],m[2],0x20,m[3])
    if extra: extra(rom)
    open("exp.sfc","wb").write(rom)
    if bat:
        subprocess.check_call([sys.executable,"-I","/home/user/Bat-Kombat/tools/build_batman.py","exp.sfc","batexp.sfc","--work",lab.S+"/../batman_work"],stdout=subprocess.DEVNULL)
        return "batexp.sfc"
    return "exp.sfc"
def film(romfile, inputs, out, tail=110, cols=6, step=14, first=4, p2=()):
    c=lab.fight(os.path.abspath(romfile)); st=c.save(); T=3
    sheet=Image.new("RGB",(256*cols,224*len(inputs)))
    for i,(seq,btn) in enumerate(inputs):
        c.restore(st); steps=[]
        for ch in seq: steps+=[(T,[D[ch]]),(T,[])]
        steps+=[(T,list(btn)),(tail,[])]
        ids=[]; shots=[]
        for fr,b in steps:
            for _ in range(fr):
                c.run2(1,b,list(p2)); sid=c.w16(0x52F8)
                if not ids or ids[-1]!=sid: ids.append(sid)
                shots.append(Image.fromarray(c.frame))
        print(seq,btn,[(s&511) for s in ids][:40],"hp",c.w16(0x36D4),c.w16(0x3898))
        n0=len(shots)-tail
        for k in range(cols): sheet.paste(shots[min(n0+first+k*step,len(shots)-1)],(256*k,224*i))
    sheet.save(out)
if __name__=="__main__":
    moves=eval(sys.argv[1]); bat=len(sys.argv)>3
    f=make(moves,bat)
    film(f,[(m[3],m[4] if len(m)>4 else ["Y"]) for m in moves],sys.argv[2])
