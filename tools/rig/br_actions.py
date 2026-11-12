"""Play each Batman Returns control and print the matched rip pose per animation frame (x frames held)."""
import os, sys, json, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sprites_only as spr, br_pose_match as match, br_gameplay as bg
import ctypes as C
c=spr.SpriteOnly(bg.CORE); c.load(bg.ROM)
for n,b in bg.BOOT_SCRIPT: c.run(n,b)
c.run(30)
L=c.lib; L.retro_serialize_size.restype=C.c_size_t; n=L.retro_serialize_size()
def save():
    buf=C.create_string_buffer(n); L.retro_serialize.argtypes=[C.c_void_p,C.c_size_t]; L.retro_serialize(buf,n); return buf.raw
def restore(s):
    L.retro_unserialize.argtypes=[C.c_void_p,C.c_size_t]; L.retro_unserialize(s,len(s))
st=save()
ACTS={
 "idle":[(60,[])], "walk":[(48,["RIGHT"])], "punch":[(3,["Y"]),(30,[])], "punch x3":[(3,["Y"]),(6,[]),(3,["Y"]),(6,[]),(3,["Y"]),(30,[])],
 "jump":[(3,["B"]),(60,[])], "jump+punch":[(3,["B"]),(12,[]),(3,["Y"]),(50,[])], "jump+A":[(3,["B"]),(12,[]),(3,["A"]),(50,[])],
 "crouch":[(30,["DOWN"])], "crouch+punch":[(8,["DOWN"]),(3,["DOWN","Y"]),(25,["DOWN"])], "crouch+A":[(8,["DOWN"]),(3,["DOWN","A"]),(30,["DOWN"])],
 "batarang":[(3,["A"]),(40,[])], "X":[(3,["X"]),(30,[])], "L hold":[(40,["L"])], "R hold":[(40,["R"])], "UP":[(30,["UP"])],
 "UP+Y":[(3,["UP","Y"]),(30,[])], "DOWN+B":[(3,["DOWN","B"]),(40,[])], "B+Y":[(3,["B","Y"]),(50,[])], "SELECT":[(3,["SELECT"]),(40,[])],
 "jump fwd":[(3,["B","RIGHT"]),(50,["RIGHT"])], "Y+A":[(3,["Y","A"]),(40,[])], "L+Y":[(20,["L"]),(3,["L","Y"]),(30,[])],
}
out={}
for name,steps in ACTS.items():
    restore(st); seq=[]
    for f,b in steps:
        for _ in range(f):
            c.run(1,b)
            r=match.best(c.frame.copy(),1)
            p=(r[0][1][0], r[0][1][1], round(float(r[0][0]),2)) if r else None
            if p and (not seq or seq[-1][0]!=p[:2]): seq.append([p[:2],1,p[2]])
            elif p: seq[-1][1]+=1
    out[name]=seq
    print("%-13s"%name, " ".join("%d%s x%d(%.2f)"%(k[0],"f" if k[1] else "",n,s) for k,n,s in seq))
json.dump({k:[[list(a),b,c] for a,b,c in v] for k,v in out.items()},open("br_actions.json","w"))
