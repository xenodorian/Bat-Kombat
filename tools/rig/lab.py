"""Test rig: debugger core with save states.

Set UMK3_ROM to the original ROM path. Save states are cached in build/rig/ next to the repo.
    c = lab.fight(rom)      # two-player fight, P1 = top-left roster cell (Batman), P2 = idle Noob Saibot
    st = c.save(); c.restore(st); c.w16(addr)
A state made on one ROM build can be restored on another build as long as RAM layout is the same.
"""
import ctypes as C, os, sys, struct
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import dbg_core as d, umk3_nav
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
S = os.path.join(REPO, "build", "rig")
os.makedirs(S, exist_ok=True)
ORIG = os.environ.get("UMK3_ROM", os.path.join(REPO, "build", "Ultimate Mortal Kombat 3 (USA).sfc"))

class Lab(d.DbgCore):
    def save(self):
        L = self.lib
        L.retro_serialize_size.restype = C.c_size_t
        n = L.retro_serialize_size()
        buf = C.create_string_buffer(n)
        L.retro_serialize.argtypes = [C.c_void_p, C.c_size_t]; L.retro_serialize.restype = C.c_bool
        assert L.retro_serialize(buf, n)
        return buf.raw
    def restore(self, st):
        L = self.lib
        L.retro_unserialize.argtypes = [C.c_void_p, C.c_size_t]; L.retro_unserialize.restype = C.c_bool
        assert L.retro_unserialize(st, len(st))
    def w16(self, a):
        return struct.unpack_from("<H", self.wram(), a)[0]

def fight(rom=None, col=0, row=0, tag="rain2p"):
    rom = rom or ORIG
    c = Lab(); c.load(rom)
    f = "%s/%s_%s.st" % (S, tag, os.path.basename(rom))
    if os.path.exists(f):
        c.run(5); c.restore(open(f, "rb").read())
    else:
        umk3_nav.to_fight_2p(c, col, row); c.run(120)
        open(f, "wb").write(c.save())
    return c
