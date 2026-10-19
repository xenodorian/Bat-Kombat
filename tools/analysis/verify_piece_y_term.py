import sys
sys.path.insert(0,'/home/claude/bat-kombat/tools')
import dbg_core as d, umk3_nav as nav
S=sys.argv[1]
c=d.DbgCore(); c.load(S+'/roms_zip/Ultimate Mortal Kombat 3 (USA).sfc')
nav.to_fight(c,0,0)
c.run(2)
w=bytes(c.wram())
rd=lambda a: w[a]|(w[a+1]<<8)
c.reset_hooks()
c.watch_exec(0x808141)
c.run(1)
log=[e for e in c.log(200000) if e['type']=='X']
ok=0
for e in log:
    # x,y at $808141 are the sbc inputs: y indexes $2C74, x indexes $EC64 (both WRAM $7E)
    a_expect=(rd(0x2C74+e['y'])-rd(0xEC64+e['x']))&0xffff
    ok += (a_expect==e['a'])
print('executions',len(log),'match',ok)
for e in log[:6]:
    print('y=%04x x=%04x  2C74[y]=%04x  EC64[x]=%04x  A=%04x'%(e['y'],e['x'],rd(0x2C74+e['y']),rd(0xEC64+e['x']),e['a']))
