import sys, collections
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
g=collections.defaultdict(list)
for e in log:
    y=e['y']; a=e['a']
    gx=(a&0xff)-rd(w0,y+2); gy=(a>>8)-rd(w0,y+4)
    g[hex(y)[:4]].append(((a&0xff)-rd(w0,y+2))&0xff)
    g[hex(y)[:4]+'Y'].append(((a>>8)-rd(w0,y+4))&0xff)
for k,v in sorted(g.items()): print(k, 'implied base values:', sorted(set(hex(x) for x in v)))
