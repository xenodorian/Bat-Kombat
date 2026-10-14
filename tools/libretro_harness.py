"""Minimal libretro frontend: load a core, feed scripted joypad input, save frames as PNG.

Usage: python3 libretro_harness.py CORE.so ROM.sfc OUT_PREFIX [--script script.txt]
Script lines: "<frames> <buttons>" where buttons is a '+' list such as START, A, UP+A, or '-' for none.
Each line holds the given buttons for that many frames. A PNG is written at each line marked with '!'.
"""
import ctypes as C
import sys
import os
import numpy as np
from PIL import Image

BTN = {"B": 0, "Y": 1, "SELECT": 2, "START": 3, "UP": 4, "DOWN": 5, "LEFT": 6, "RIGHT": 7,
       "A": 8, "X": 9, "L": 10, "R": 11}

ENV_SET_PIXEL_FORMAT = 10
PIX_XRGB8888 = 1
PIX_RGB565 = 2

ENV_CB = C.CFUNCTYPE(C.c_bool, C.c_uint, C.c_void_p)
VIDEO_CB = C.CFUNCTYPE(None, C.c_void_p, C.c_uint, C.c_uint, C.c_size_t)
AUDIO_CB = C.CFUNCTYPE(None, C.c_int16, C.c_int16)
AUDIO_BATCH_CB = C.CFUNCTYPE(C.c_size_t, C.c_void_p, C.c_size_t)
INPUT_POLL_CB = C.CFUNCTYPE(None)
INPUT_STATE_CB = C.CFUNCTYPE(C.c_int16, C.c_uint, C.c_uint, C.c_uint, C.c_uint)


class GameInfo(C.Structure):
    _fields_ = [("path", C.c_char_p), ("data", C.c_void_p), ("size", C.c_size_t), ("meta", C.c_char_p)]


class Core:
    def __init__(self, path):
        self.lib = C.CDLL(path)
        self.pressed = set()
        self.pixfmt = PIX_XRGB8888
        self.frame = None
        self.w = self.h = 0
        self.pitch = 0
        self._cb_env = ENV_CB(self._env)
        self._cb_video = VIDEO_CB(self._video)
        self._cb_audio = AUDIO_CB(lambda l, r: None)
        self._cb_batch = AUDIO_BATCH_CB(lambda d, n: n)
        self._cb_poll = INPUT_POLL_CB(lambda: None)
        self._cb_input = INPUT_STATE_CB(self._input)
        L = self.lib
        L.retro_set_environment(self._cb_env)
        L.retro_set_video_refresh(self._cb_video)
        L.retro_set_audio_sample(self._cb_audio)
        L.retro_set_audio_sample_batch(self._cb_batch)
        L.retro_set_input_poll(self._cb_poll)
        L.retro_set_input_state(self._cb_input)
        L.retro_init()

    def _env(self, cmd, data):
        if cmd == ENV_SET_PIXEL_FORMAT:
            # The core picks the format; record it so frames decode correctly.
            self.pixfmt = C.cast(data, C.POINTER(C.c_uint)).contents.value
            return True
        return False

    def _video(self, data, width, height, pitch):
        if not data:
            return
        self.w, self.h, self.pitch = width, height, pitch
        buf = (C.c_uint8 * (pitch * height)).from_address(data)
        arr = np.frombuffer(buf, dtype=np.uint8).reshape(height, pitch)
        if self.pixfmt == PIX_RGB565:
            px = arr[:, : width * 2].reshape(height, width, 2).astype(np.uint16)
            v = px[:, :, 0] | (px[:, :, 1] << 8)
            r = ((v >> 11) & 31) * 255 // 31
            g = ((v >> 5) & 63) * 255 // 63
            b = (v & 31) * 255 // 31
            self.frame = np.stack([r, g, b], axis=2).astype(np.uint8)
        else:
            self.frame = np.ascontiguousarray(arr[:, : width * 4].reshape(height, width, 4)[:, :, [2, 1, 0]])

    def _input(self, port, device, index, rid):
        if port == 0 and device == 1 and rid in self.pressed:
            return 1
        return 0

    def load(self, rom_path):
        with open(rom_path, "rb") as f:
            data = f.read()
        buf = C.create_string_buffer(data, len(data))
        self._rom_buf = buf
        info = GameInfo(rom_path.encode(), C.cast(buf, C.c_void_p), len(data), None)
        ok = self.lib.retro_load_game(C.byref(info))
        if not ok:
            raise RuntimeError("retro_load_game failed")

    def run(self, frames, buttons=()):
        self.pressed = {BTN[b] for b in buttons}
        for _ in range(frames):
            self.lib.retro_run()

    def _mem(self, kind):
        L = self.lib
        L.retro_get_memory_data.restype = C.c_void_p
        L.retro_get_memory_data.argtypes = [C.c_uint]
        L.retro_get_memory_size.restype = C.c_size_t
        L.retro_get_memory_size.argtypes = [C.c_uint]
        ptr, size = L.retro_get_memory_data(kind), L.retro_get_memory_size(kind)
        return bytes((C.c_uint8 * size).from_address(ptr))

    def wram(self):
        """128 KB of SNES work RAM ($7E0000-$7FFFFF)."""
        return self._mem(2)

    def vram(self):
        """64 KB of SNES video RAM."""
        return self._mem(3)

    def save_png(self, path):
        Image.fromarray(self.frame).save(path)


def main():
    core_path, rom, out = sys.argv[1], sys.argv[2], sys.argv[3]
    script = None
    if "--script" in sys.argv:
        script = sys.argv[sys.argv.index("--script") + 1]
    core = Core(core_path)
    core.load(rom)
    if script:
        n = 0
        for line in open(script):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            frames = int(parts[0])
            btns = [] if len(parts) < 2 or parts[1] == "-" else parts[1].split("+")
            core.run(frames, btns)
            if len(parts) >= 3 and parts[2] == "!":
                n += 1
                core.save_png("%s_%03d.png" % (out, n))
    else:
        core.run(900)
        core.save_png(out + ".png")
    print("ok", core.w, core.h)


if __name__ == "__main__":
    main()
