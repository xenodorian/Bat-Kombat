"""Trace DMA transfers into video RAM while a scripted run happens, using the debug core.

Usage: python3 -I trace_dma.py ROM [frames_after_select]
Watches writes to the DMA registers ($4300-$437F), DMA enable ($420B) and VRAM address ($2115-$2117), and
reconstructs each transfer: channel, source address, byte count, VRAM destination, and the PC that started it.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dbg_core as d
import umk3_nav as nav


def decode(events):
    reg = {}          # last value written per register address (canonical 0x00xxxx)
    vmadd = 0
    out = []
    for e in events:
        if e['type'] != 'W':
            continue
        a = e['addr'] & 0xFFFF
        reg[a] = e['val']
        if a in (0x2116, 0x2117):
            vmadd = reg.get(0x2116, 0) | reg.get(0x2117, 0) << 8
        if a == 0x420B and e['val']:
            for ch in range(8):
                if e['val'] >> ch & 1:
                    b = 0x4300 + ch * 0x10
                    src = reg.get(b + 2, 0) | reg.get(b + 3, 0) << 8 | reg.get(b + 4, 0) << 16
                    size = reg.get(b + 5, 0) | reg.get(b + 6, 0) << 8 or 0x10000
                    dest = reg.get(b + 1, 0)
                    out.append(dict(frame_seq=e['n'], pc=e['pc'], ch=ch, src=src, size=size, bdest=dest,
                                    ctrl=reg.get(b, 0), vram_word=vmadd))
    return out


def main(rom, extra=300):
    c = d.DbgCore()
    c.load(rom)
    nav.boot_to_roster(c)
    c.log()
    c.watch_write(0x4300, 0x437F)
    c.watch_write(0x420B)
    c.watch_write(0x2115, 0x2117)
    nav.select_fighter(c, 0, 0)
    c.run(400)
    c.run(5, ['A'])
    c.run(1000)
    c.run(5, ['START'])
    c.run(extra)
    ev = c.log(262144)
    dmas = [t for t in decode(ev) if t['bdest'] in (0x18, 0x19)]
    print("events", len(ev), "VRAM DMAs", len(dmas))
    for t in dmas:
        bank = t['src'] >> 16
        kind = 'WRAM' if bank in (0x7E, 0x7F) else ('ROM' if bank >= 0xC0 or 0x80 <= bank < 0xC0 else 'other')
        print("pc=%06X ch%d src=%06X (%s) size=%5d vram_word=%04X (byte %05X)" % (
            t['pc'], t['ch'], t['src'], kind, t['size'], t['vram_word'], t['vram_word'] * 2))


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 300)
