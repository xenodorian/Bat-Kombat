import sys
sys.path.insert(0,'/home/claude/bat-kombat/tools')
import dbg_core as d, umk3_nav as nav
S=sys.argv[1]
c=d.DbgCore(); c.load(S+'/roms_zip/Ultimate Mortal Kombat 3 (USA).sfc')
nav.to_fight(c,0,0)
c.run(2)
c.reset_hooks()
c.poke_on_exec(0x80818B, 0x170A, bytes([0xa2,0x00]))
c.watch_exec(0x80818B); c.watch_exec(0x80818D)
c.run(1)
log=c.log(4000)
for e in log[:4]:
    print('pc=%06x a=%04x p=%02x'%(e['pc'],e['a'],e['p']))
