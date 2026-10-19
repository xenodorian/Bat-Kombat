import sys
sys.path.insert(0,'/home/claude/bat-kombat/tools')
import dbg_core as d, umk3_nav as nav
S=sys.argv[1]
c=d.DbgCore(); c.load(S+'/roms_zip/Ultimate Mortal Kombat 3 (USA).sfc')
nav.to_fight(c,0,0)
c.run(2)
def words():
    w=bytes(c.wram())
    rd=lambda a: w[a]|(w[a+1]<<8)
    return rd(0x3662), rd(0x355C), rd(0x1708), rd(0x170A)
seq=[]
for label,btn,n in (("idle",[],20),("jump",["UP"],25),("air",[],40),("crouch",["DOWN"],25),("stand",[],20)):
    for i in range(n//5):
        c.run(5,btn) if btn and i==0 else c.run(5)
        seq.append((label,)+tuple('%04x'%v for v in words()))
prev=None
for row in seq:
    if row[1:]!=prev: print(row)
    prev=row[1:]
