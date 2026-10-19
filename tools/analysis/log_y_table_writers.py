import sys, collections
sys.path.insert(0,'/home/claude/bat-kombat/tools')
import dbg_core as d, umk3_nav as nav
S=sys.argv[1]
c=d.DbgCore(); c.load(S+'/roms_zip/Ultimate Mortal Kombat 3 (USA).sfc')
nav.to_fight(c,0,0)
c.run(2)
c.reset_hooks()
c.watch_write(0x7E2C74,0x7E2CFF)
c.watch_write(0x7EEC64,0x7EECFF)
c.run(3)
log=[e for e in c.log(400000) if e['type']=='W']
print('writes:',len(log))
cnt=collections.Counter((hex(e['addr'])[:6], hex(e['pc'])) for e in log)
for (a,pc),n in cnt.most_common(12): print('range',a,'by pc',pc,'x',n)
