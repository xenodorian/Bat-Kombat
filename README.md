# Bat-Kombat: Batman in Ultimate Mortal Kombat 3 (SNES)

Status: partial. A reskin exists. A real Batman fighter does not.

## What exists
- A patch script that turns Rain (fighter ID 24) into a dark blue-grey "Batman" colour reskin.
  Same sprites, moves and hit data as Rain. Name table entry changed to "-BATMAN", but the in-fight HUD
  still shows "RAIN". The roster portrait is still purple.
- Emulator test tooling, analysis scripts, and a long log of verified and unverified findings.
- ROMs and the patched ROM are NOT in this repo (commercial dumps, gitignored).

## Files
- Current_Work.md: full log. Verified facts, corrections to earlier mistakes, agent results, and the plan.
- Data_Needed.md: outside pages I could not read (Cloudflare) and what is needed from them.
- Issues_Summary.txt: summary of blockers (written when work was stopped once).
- tools/make_batman_reskin.py: builds the reskin ROM from a clean UMK3 (USA) ROM.
      python3 tools/make_batman_reskin.py "Ultimate Mortal Kombat 3 (USA).sfc" UMK3_Batman.sfc
- tools/umk3rom.py: HiROM address mapping and 65816 disassembly helpers.
- tools/libretro_harness.py: headless emulator (snes9x libretro core) with button input, frame capture,
  WRAM/VRAM reads, and RAM pokes (Pro Action Replay style).
- tools/umk3_nav.py: boots UMK3 to a fight (written by a sub-agent; roster cursor and fight start checked
  by me only in the sense that it ran to a fight with Rain vs Reptile).
- tools/br_gameplay.py: boots Batman Returns to Stage 1 (written by a sub-agent, spot-checked).
- tools/tilesheet.py, scan_id_tables.py, deluxe_diff.py: analysis scripts (scan and diff scripts are
  agent-written and their reports contained errors; see Current_Work.md).

## Requirements to rerun
apt: retroarch, libretro-snes9x (for the core file), cc65 optional. pip: capstone, pillow, numpy.
The harness loads /usr/lib/x86_64-linux-gnu/libretro/snes9x_libretro.so.

## Key verified facts
- UMK3 (USA): 4 MB HiROM, file offset = ((bank - 0xC0) << 16) | addr.
- Fighter ID is in WRAM $52C8 (P1) and mirrored at $36D0. IDs follow the name table at 0x3E544
  (0 Kano ... 24 Rain). Chameleon is ID 25 per Pro Action Replay codes (unverified here).
- Rain's sprite palette is two ROM chunks: 0x456E8 (4 words) and 0x3EAFB3 (10 words).
- The in-fight HUD name is not read from the ASCII name table. The roster portrait palette was not found
  (palette 13 of the roster screen, ROM 0x3F7C5E, is shared with other portraits; not patched).
- Batman Returns reaches Stage 1 under script; its sprite data is compressed in ROM, but its art is
  readable from emulator memory. One clean image of Batman was saved from a frame.

## Not done
Real Batman sprites, move list, new roster slot, HUD name, portrait recolour, custom special moves.
