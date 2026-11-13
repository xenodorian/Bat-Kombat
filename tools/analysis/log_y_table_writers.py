"""Sprite-engine investigation (2026-10), kept as a record. Usage: python3 log_y_table_writers.py [UMK3_ROM]. Findings: Current_Work.md."""
import sys, collections
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import dbg_core as d, umk3_nav as nav
ROM_PATH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'build', 'Ultimate Mortal Kombat 3 (USA).sfc')
c=d.DbgCore(); c.load(ROM_PATH)
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
