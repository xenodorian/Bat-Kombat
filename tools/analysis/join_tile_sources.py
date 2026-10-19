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
STA=[0x838405+7*k for k in range(16)]
for pc in STA: c.watch_exec(pc)
c.watch_write(0x004302,0x004306)
c.watch_write(0x002116,0x002117)
c.run(60)
log=c.log(2000000)
copies=[]
for e in log:
    if e['type']=='X' and e['pc'] in STA:
        k=(e['pc']-0x838405)//7
        copies.append(dict(stage=0x80A8+e['x'], rom=(e['db']<<16)|((e['y']+2*k)&0xffff), word=e['a']))
regs=[e for e in log if e['type']=='W']
dmas=[]; cur={}; vram=None
for e in regs:
    if e['addr'] in (0x2116,0x2117):
        if e['addr']==0x2116: vram=(vram or 0)&0xff00|e['val']
        else: vram=(vram or 0)&0x00ff|(e['val']<<8)
        continue
    cur[e['addr']]=e['val']
    if e['addr']==0x4306 and e['pc']==0x88b933:
        dmas.append(dict(src=cur.get(0x4302,0)|(cur.get(0x4303,0)<<8), size=cur.get(0x4305,0)|(cur.get(0x4306,0)<<8), vram=vram))
        cur={}
print('copied words:',len(copies),'DMAs:',len(dmas))
ok=sum(1 for cp in copies if (rom[u.snes_to_file(cp['rom']>>16,cp['rom']&0xffff)]|(rom[u.snes_to_file(cp['rom']>>16,cp['rom']&0xffff)+1]<<8))==cp['word'])
print('copied words equal ROM word:',ok,'of',len(copies))
mapped=0; out=[]
for dm in dmas:
    if dm['vram'] is None: continue
    for cp in copies:
        if dm['src']<=cp['stage']<dm['src']+dm['size']:
            mapped+=1
            off=cp['stage']-dm['src']
            out.append((dm['vram']*2+off, cp['rom']))
print('words mapped to a VRAM address:',mapped)
for v,r in sorted(out)[:12]: print('vram byte %05x <- ROM %06x'%(v,r))
