"""Debug-capable snes9x core wrapper: exec breakpoints, ROM/RAM read and write watches.

The core is a patched snes9x libretro build (see tools/snes9x_dbg.patch and tools/build_dbg_core.sh).
Addresses are canonical: ROM in banks C0-FF (HiROM), work RAM at 7E0000-7FFFFF. Mirrors are folded for you.

    import dbg_core as d
    c = d.DbgCore()
    c.load(rom_path)
    c.watch_exec(0xC3E363)             # log every time this instruction runs
    c.watch_write(0x7E52C8, 0x7E52C9)  # log every CPU write to this range, with the writing PC
    c.watch_read(0xC8A000, 0xC8AFFF)   # log every CPU data read of this ROM range, with the reading PC
    c.run(300, [])
    for e in c.log(): print(e)

Log entries: dict(type 'X'/'R'/'W', addr, val, pc, a, x, y, s, d, db, p). pc is the 24-bit address of the instruction.
Not logged: opcode fetches, DMA transfers, and APU/SPC reads.
"""
import ctypes as C
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import libretro_harness as h

DBG_CORE = os.environ.get("DBG_CORE", "/opt/snes9x_dbg/snes9x_dbg_libretro.so")


class _Entry(C.Structure):
    _fields_ = [("type", C.c_uint8), ("val", C.c_uint8), ("pad", C.c_uint16),
                ("addr", C.c_uint32), ("pc", C.c_uint32),
                ("a", C.c_uint16), ("x", C.c_uint16), ("y", C.c_uint16), ("s", C.c_uint16), ("d", C.c_uint16),
                ("db", C.c_uint8), ("p", C.c_uint8), ("n", C.c_uint32)]


class DbgCore(h.Core):
    def __init__(self, path=DBG_CORE):
        super().__init__(path)
        L = self.lib
        assert C.sizeof(_Entry) == L.dbg_entry_size(), "log entry size mismatch"
        L.dbg_add_exec.argtypes = [C.c_uint32]
        L.dbg_add_read.argtypes = [C.c_uint32, C.c_uint32]
        L.dbg_add_write.argtypes = [C.c_uint32, C.c_uint32]
        L.dbg_log_read.argtypes = [C.POINTER(_Entry), C.c_int]
        L.dbg_log_read.restype = C.c_int
        L.dbg_add_poke.argtypes = [C.c_uint32, C.c_uint32, C.c_char_p, C.c_int]
        L.dbg_add_poke.restype = C.c_int
        L.dbg_log_total.restype = C.c_uint32

    def reset_hooks(self):
        self.lib.dbg_reset()

    def watch_exec(self, addr):
        self.lib.dbg_add_exec(addr)

    def watch_read(self, lo, hi=None):
        self.lib.dbg_add_read(lo, lo if hi is None else hi)

    def watch_write(self, lo, hi=None):
        self.lib.dbg_add_write(lo, lo if hi is None else hi)

    def poke_on_exec(self, exec_addr, wram_off, data):
        """Just before the instruction at exec_addr runs, copy data into work RAM at wram_off (max 8192 bytes, 16 pokes)."""
        r = self.lib.dbg_add_poke(exec_addr, wram_off, bytes(data), len(data))
        if r < 0:
            raise ValueError("poke rejected (too many pokes, too long, or out of range)")
        return r

    def clear_pokes(self):
        self.lib.dbg_clear_pokes()

    def log(self, max_entries=100000):
        buf = (_Entry * max_entries)()
        n = self.lib.dbg_log_read(buf, max_entries)
        out = []
        for e in buf[:n]:
            out.append(dict(type=chr(e.type), addr=e.addr, val=e.val, pc=e.pc, a=e.a, x=e.x, y=e.y,
                            s=e.s, d=e.d, db=e.db, p=e.p, n=e.n))
        return out
