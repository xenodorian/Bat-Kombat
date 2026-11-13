"""Sprite-engine investigation (2026-10), kept as a record. Usage: python3 poke_test_y_base.py [UMK3_ROM]. Findings: Current_Work.md."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import dbg_core as d, umk3_nav as nav
ROM_PATH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'build', 'Ultimate Mortal Kombat 3 (USA).sfc')
c=d.DbgCore(); c.load(ROM_PATH)
nav.to_fight(c,0,0)
c.run(2)
c.reset_hooks()
c.poke_on_exec(0x80818B, 0x170A, bytes([0xa2,0x00]))
c.watch_exec(0x80818B); c.watch_exec(0x80818D)
c.run(1)
log=c.log(4000)
for e in log[:4]:
    print('pc=%06x a=%04x p=%02x'%(e['pc'],e['a'],e['p']))
