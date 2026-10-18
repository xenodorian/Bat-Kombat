import sys
sys.path.insert(0,'/home/claude/bat-kombat/tools')
import dbg_core as d, umk3_nav as nav
S=sys.argv[1]
c=d.DbgCore(); c.load(S+'/roms_zip/Ultimate Mortal Kombat 3 (USA).sfc')
nav.to_fight(c,0,0)
c.run(2)
w0=bytes(c.wram())
c.reset_hooks()
for pc in (0x80819D,0x80822A,0x80825F): c.watch_exec(pc)
c.run(1)
log=[e for e in c.log(200000) if e['type']=='X']
def rd(w,a): return w[a]|(w[a+1]<<8)
bx=rd(w0,0x1708)
print('X base',hex(bx),'stores',len(log))
for ybase in (0xA2,0xA1):
    ok=0; bad=[]
    for e in log:
        y=e['y']; a=e['a']
        X=(rd(w0,y+2)+bx)&0xff
        Y=(rd(w0,y+4)+ybase)&0xff
        if X==(a&0xff) and Y==(a>>8): ok+=1
        else: bad.append((hex(y),hex(a),hex(X),hex(Y)))
    print('ybase',hex(ybase),'match',ok,'of',len(log))
    for b in bad[:5]: print('  miss',b)

import collections
g=collections.defaultdict(lambda:[0,0])
for e in log:
    y=e['y']; a=e['a']
    X=(rd(w0,y+2)+bx)&0xff; Y=(rd(w0,y+4)+0xA2)&0xff
    key=(hex(y)[:4], e['pc'])
    g[key][0]+= (X==(a&0xff) and Y==(a>>8)); g[key][1]+=1
for k,v in sorted(g.items()): print('group',k,'match',v[0],'of',v[1])
