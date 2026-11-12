"""Match a Batman Returns frame against the 100 rip poses (art/batman_poses.tar.gz, extracted to build/poses).

best(frame_rgb, top) -> [(score, (pose, mirrored))]. Use a sprites-only frame (tools/rig/sprites_only.py).
The rip poses are the game's exact sprites: a clean frame scores about 1.0. Each of the 3 largest sprite blobs is tried.
"""
import sys, os, json
import numpy as np
from PIL import Image
from scipy import ndimage
SRC=os.environ.get("BR_POSES", os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "build", "poses"))
meta=json.load(open(SRC+"/frames.json"))
def q(rgb): return (rgb.astype(int)>>3)
POSES={}
for e in meta:
    a=np.array(Image.open(SRC+"/frames/"+e["file"]).convert("RGBA"))
    op=a[:,:,3]>127; c5=q(a[:,:,:3]); lit=op&(c5.sum(2)>3)
    if lit.sum()<200: continue
    for fl in (0,1):
        cc=c5[:,::-1] if fl else c5; ll=lit[:,::-1] if fl else lit
        POSES[(e["i"],fl)]=(cc,ll)
PAL=set()
for cc,ll in POSES.values():
    for v in cc[ll]: PAL.add(tuple(v))
def blobs(frame, k=3):
    c5=q(frame); key=c5[:,:,0]*1024+c5[:,:,1]*32+c5[:,:,2]
    pal=np.array([r*1024+g*32+b for r,g,b in PAL])
    m=np.isin(key,pal)&(c5.sum(2)>3)
    lab,n=ndimage.label(ndimage.binary_dilation(m,iterations=3))
    if n==0: return c5,[]
    sizes=ndimage.sum(m,lab,range(1,n+1))
    order=np.argsort(-sizes)[:k]
    return c5,[m&(lab==i+1) for i in order if sizes[i]>=100]
def score_mask(c5,m):
    ys,xs=np.nonzero(m); cy,cx=ys.mean(),xs.mean()
    res=[]
    for key,(pc,pl) in POSES.items():
        py,px=np.nonzero(pl); pcy,pcx=py.mean(),px.mean()
        bestsc=0
        for dy in range(-3,4):
            for dx in range(-3,4):
                oy=int(round(cy-pcy))+dy; ox=int(round(cx-pcx))+dx
                yy=py+oy; xx=px+ox
                ok=(yy>=0)&(yy<m.shape[0])&(xx>=0)&(xx<m.shape[1])
                hit=np.zeros(len(py),bool)
                hit[ok]=m[yy[ok],xx[ok]]&(np.abs(c5[yy[ok],xx[ok]]-pc[py[ok],px[ok]]).sum(1)<=2)
                inter=hit.sum(); sc=inter/(len(py)+m.sum()-inter)
                bestsc=max(bestsc,sc)
        res.append((bestsc,key))
    return res
def best(frame, top=3):
    c5,ms=blobs(frame)
    allr=[]
    for m in ms: allr+=score_mask(c5,m)
    allr.sort(reverse=True)
    return allr[:top]
