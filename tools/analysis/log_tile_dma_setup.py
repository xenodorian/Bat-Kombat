import sys, collections
sys.path.insert(0,'/home/claude/bat-kombat/tools')
import dbg_core as d, umk3_nav as nav, umk3rom as u
S=sys.argv[1]
ROM=S+'/roms_zip/Ultimate Mortal Kombat 3 (USA).sfc'
rom=u.load(ROM)
c=d.DbgCore(); c.load(ROM)
nav.to_fight(c,0,0)
c.run(2)
c.reset_hooks()
c.watch_exec(0x838405)
c.watch_write(0x004302,0x004306)
c.watch_write(0x002116,0x002117)
c.run(6)
log=c.log(800000)
copies=[e for e in log if e['type']=='X']
regs=[e for e in log if e['type']=='W']
print('copies:',len(copies))
srcs=collections.Counter()
for e in regs:
    if e['addr']==0x4302: srcs[('4302',hex(e['val']))]+=0
print('reg writes:',len(regs))
pcs=collections.Counter((hex(e['addr']),hex(e['pc'])) for e in regs)
for k,n in pcs.most_common(10): print(k,n)
rows=[(hex(e['addr']),hex(e['pc']),hex(e['val']),hex(e['a'])) for e in regs if e['pc'] in (0x88b94b,0x88b933,0x88b97c,0x88b971)]
for r in rows[:14]: print('addr %s pc %s val %s a %s'%r)
print('2116 writes:', [(hex(e['addr']),hex(e['pc']),hex(e['val'])) for e in regs if e['addr'] in (0x2116,0x2117)][:8])
