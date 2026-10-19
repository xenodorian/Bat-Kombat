import sys, collections
sys.path.insert(0,'/home/claude/bat-kombat/tools')
import dbg_core as d, umk3_nav as nav
S=sys.argv[1]
c=d.DbgCore(); c.load(S+'/roms_zip/Ultimate Mortal Kombat 3 (USA).sfc')
nav.to_fight(c,0,0)
c.run(2)
c.reset_hooks()
for a in (0x7E355C,0x7E3560,0x7E3662,0x7E3664):
    c.watch_write(a,a+1)
c.run(30)
log=[e for e in c.log(200000) if e['type']=='W']
print('writes:',len(log))
cnt=collections.Counter((hex(e['addr']),hex(e['pc'])) for e in log)
for (a,pc),n in cnt.most_common(12): print('addr',a,'by pc',pc,'x',n)
vals=collections.Counter((hex(e['addr']),hex(e['val'])) for e in log)
print('top values:', [(a,v,n) for (a,v),n in vals.most_common(10)])
