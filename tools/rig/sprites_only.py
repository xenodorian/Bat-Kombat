"""snes9x core with background layers switched off through its core options, so frames show sprites only."""
import os, sys, ctypes as C
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import libretro_harness as h
class Var(C.Structure): _fields_=[("key",C.c_char_p),("value",C.c_char_p)]
class SpriteOnly(h.Core):
    """snes9x with background layers 1-4 switched off through core options (sprites only)."""
    OFF={b"snes9x_layer_1":b"disabled",b"snes9x_layer_2":b"disabled",b"snes9x_layer_3":b"disabled",b"snes9x_layer_4":b"disabled"}
    def __init__(self, path, sprites_only=True):
        self.sprites_only=sprites_only; self._vals=[]; self._upd=True
        super().__init__(path)
    def _env(self, cmd, data):
        if cmd==15 and data:
            v=C.cast(data,C.POINTER(Var)).contents
            k=v.key
            if self.sprites_only and k in self.OFF:
                b=C.create_string_buffer(self.OFF[k]); self._vals.append(b); v.value=C.cast(b,C.c_char_p); return True
            return False
        if cmd==17 and data:
            C.cast(data,C.POINTER(C.c_bool))[0]=self._upd; self._upd=False; return True
        return super()._env(cmd,data)
