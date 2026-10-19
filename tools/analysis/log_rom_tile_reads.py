import sys, collections
sys.path.insert(0,'/home/claude/bat-kombat/tools')
import dbg_core as d, umk3_nav as nav
S=sys.argv[1]
c=d.DbgCore(); c.load(S+'/roms_zip/Ultimate Mortal Kombat 3 (USA).sfc')
nav.to_fight(c,0,0)
c.run(2)
c.reset_hooks()
c.watch_read(0xD60000,0xD8FFFF)
c.run(3)
log=[e for e in c.log(400000) if e['type']=='R']
print('ROM D6-D8 reads:', len(log))
byPC=collections.Counter(hex(e['pc']) for e in log)
print('reader PCs:', byPC.most_common(8))
addrs=sorted(set(e['addr'] for e in log))
if addrs: print('addr range:', hex(addrs[0]), hex(addrs[-1]), 'distinct:', len(addrs))
import umk3rom as u
rom=u.load(S+'/roms_zip/Ultimate Mortal Kombat 3 (USA).sfc')
w=bytes(c.wram())
# the copy writes 16 words to 7E:80A8+x; compare the first staging block with ROM bytes at the first read address
first=min(addrs)
src=bytes(rom[first - 0xC00000 if False else u.snes_to_file(first>>16, first&0xffff): u.snes_to_file(first>>16, first&0xffff)+32])
print('ROM bytes at first read:', src[:8].hex(' '))
print('staging 7E:80A8 bytes  :', w[0x80A8:0x80A8+8].hex(' '))
ok=0; bad=0
for e in log:
    f=u.snes_to_file(e['addr']>>16, e['addr']&0xffff)
    if rom[f]==e['val']: ok+=1
    else: bad+=1
print('read values equal ROM bytes:', ok, 'differ:', bad)
