import sys, collections
sys.path.insert(0,'/home/claude/bat-kombat/tools')
import dbg_core as d, umk3_nav as nav
S=sys.argv[1]
c=d.DbgCore(); c.load(S+'/roms_zip/Ultimate Mortal Kombat 3 (USA).sfc')
nav.to_fight(c,0,0)
c.run(2)
c.reset_hooks()
c.watch_write(0x7E1712,0x7E1713)
c.run(30)
log=[e for e in c.log(200000) if e['type']=='W']
print('writes to $12:', len(log))
cnt=collections.Counter((hex(e['pc']), e['val']) for e in log)
for (pc,v),n in cnt.most_common(12): print(pc,'val',hex(v),'x',n)
vals=collections.Counter(e['a'] for e in log)
print('A values at writes (top):', [hex(k) for k,_ in vals.most_common(8)])
outside=[e for e in log if not (0x808100<=e['pc']<=0x808300)]
print('writes outside builder:', len(outside))
cnt2=collections.Counter((hex(e['pc']), hex(e['val'])) for e in outside)
for (pc,v),n in cnt2.most_common(15): print(' outside pc',pc,'val',v,'x',n)
