"""Extract the Batman Returns (SNES) samples used for Batman's sounds in UMK3 and save them as WAV files.

Usage: python3 -I tools/extract_br_sounds.py BATMAN_RETURNS.sfc [OUT_DIR=art/batman_sounds]
Needs the debug core (tools/build_dbg_core.sh). The game is run to Stage 1 (tools/br_gameplay.py), the sound
RAM is read from a snes9x save state (block "SND", first 64 KB), and samples are decoded from the BRR sample
directory at sound RAM $4C00 (the DSP DIR register, logged with DbgCore.watch_dsp).

Which sample is which was worked out from the sound-chip log while Batman acts (not by listening):
  13  played on every punch and jump, broadband noise rising and falling   -> swing
  18  played twice (two voices) when a punch lands and when Batman is hurt -> impact
   8  played when the batarang is thrown and when Batman is hurt          -> batarang / crash
The WAV rate is the playback rate measured in the game: pitch register / 4096 * 32000.
"""
import os
import struct
import sys
import wave

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
import brr  # noqa: E402

SAMPLES = {"swing": (13, 0x06A5), "impact": (18, 0x0352), "batarang": (8, 0x0259)}
DIR_PAGE = 0x4C


def main(rom, out):
    import ctypes as C
    import dbg_core
    import br_gameplay as bg
    c = dbg_core.DbgCore()
    c.load(rom)
    for n, b in bg.BOOT_SCRIPT:
        c.run(n, b)
    c.run(60)
    L = c.lib
    L.retro_serialize_size.restype = C.c_size_t
    n = L.retro_serialize_size()
    buf = C.create_string_buffer(n)
    L.retro_serialize.argtypes = [C.c_void_p, C.c_size_t]
    assert L.retro_serialize(buf, n)
    st = buf.raw
    o = st.find(b"SND:066560:") + 11
    aram = st[o:o + 65536]
    os.makedirs(out, exist_ok=True)
    for name, (idx, pitch) in SAMPLES.items():
        start, _ = brr.directory(aram, DIR_PAGE, idx + 1)[idx]
        pcm = brr.decode(aram, start)
        rate = int(round(pitch / 4096 * 32000))
        with wave.open(os.path.join(out, "%s.wav" % name), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(rate)
            w.writeframes(struct.pack("<%dh" % len(pcm), *pcm))
        print(name, "sample", idx, "samples", len(pcm), "rate", rate)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(TOOLS), "art", "batman_sounds"))
