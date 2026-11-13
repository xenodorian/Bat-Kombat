"""Sprite-engine investigation (2026-10), kept as a record. Usage: python3 log_tile_dma_setup.py [UMK3_ROM]. Findings: Current_Work.md."""
import sys, collections
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import dbg_core as d, umk3_nav as nav, umk3rom as u
ROM_PATH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'build', 'Ultimate Mortal Kombat 3 (USA).sfc')
ROM=ROM_PATH
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
