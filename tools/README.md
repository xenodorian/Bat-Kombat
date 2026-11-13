# Tools

Everything used to take apart Ultimate Mortal Kombat 3 (USA, SNES) and Batman Returns (USA, SNES) and to build
the Batman ROM. The scripts are written for agents and people continuing this work or doing a similar port.
Findings behind each tool are in `../Current_Work.md` (dated log), `../ROUTINES_UMK3.md` and
`../Lessons_Learned.md`. Addresses are SNES addresses (HiROM banks `$C0-$FF`, work RAM `$7E/$7F`) unless a
value is called a file offset.

## Setup

- Python 3 with numpy, Pillow and capstone (`pip install numpy pillow capstone`).
- A snes9x libretro core for plain runs: `apt install libretro-snes9x` (path overridable with `SNES9X_CORE`).
- The debug core for breakpoints and watches: `sudo tools/build_dbg_core.sh` builds snes9x with
  `tools/snes9x_dbg.patch` into `/opt/snes9x_dbg/snes9x_dbg_libretro.so` (override with `DBG_CORE`).
- ROMs, unzipped from the repo root: `unzip "Ultimate Mortal Kombat 3 (USA).zip" -d build/` and
  `unzip "Batman Returns (USA).zip" -d build/`. Tools look in `build/` by default; override with `UMK3_ROM`,
  `BR_ROM`, `DELUXE_ROM`.
- Run tools with `python3 -I` when they read files you did not make (keeps the current directory off the import path).

Build the release ROM:

```
python3 -I tools/build_batman.py "build/Ultimate Mortal Kombat 3 (USA).sfc" build/UMK3_Batman.sfc
```

## Recipes

How the common questions were answered. Each step names the tool.

- **Where is value X in RAM?** Hold the input that changes it: `rig/ram_scan.py ROM --p1 RIGHT` (found the
  fighter X position `$7E:3DA8`).
- **What code sets it, and from where?** `rig/who_writes.py ROM 7E3C38 7E3C39 --p1 RIGHT`, then disassemble the
  writer with `dis65.py ROM 88:BF70 0x20`, see where A came from, watch that address next. Repeat until you reach
  a ROM table (found the per-fighter walk tables at `$88:9729` / `$88:9799`). `--read` and `--exec` watch reads
  and instruction hits instead.
- **How long is each animation frame shown?** `rig/pose_timing.py ROM` (standard set) or `--p1 Y`; compare with
  `rig/br_actions.py` for Batman Returns. Which sleep or loop makes the time: `rig/sleep_trace.py ROM --p1 Y`.
- **Which sounds play?** `rig/sound_events.py ROM --p1 Y` (UMK3 requests and DSP key-ons with pitch).
- **Does a build crash?** `rig/liveness.py SEED ROM` for seeds 1-6 (counts frames still running ROM code;
  a crashed game can still change the picture, so frame comparison is not enough).
- **Does a special or finisher work?** `rig/exp.py` films moves put into Rain's table; `rig/fat.py` reaches
  FINISH HIM and films a finisher input.
- **Which graphics does a frame use?** `trace_dma.py`, `vram_blockfill_test.py`, `capture_set_frames.py`,
  `umk3_sprites.py` (decodes the sprite set format from ROM).
- **Does it run outside snes9x?** `rig/bsnes_check.py ROM` (bsnes-mercury accuracy core).

## Emulator and test harness

| Tool | What it does |
|---|---|
| `libretro_harness.py` | Minimal libretro frontend: load a core, feed joypad input per frame (`run`, `run2` for two pads), read work RAM, save frames. |
| `dbg_core.py` | The debug core: exec breakpoints, RAM/ROM read and write watches, pokes on exec, DSP register logging. Log entries carry PC, A, X, Y, S, D, DB, P. |
| `build_dbg_core.sh`, `snes9x_dbg.patch` | Build the debug core from the Debian snes9x source. |
| `umk3_nav.py` | Drive UMK3 from boot to the roster, pick a cell, start one- or two-player fights. |
| `br_gameplay.py` | Drive Batman Returns from boot into Stage 1 and perform named actions. Button mapping notes inside. |
| `rig/lab.py` | `lab.fight(rom)`: two-player fight (P1 top-left cell, P2 idle), save state cached in `build/rig/`. Base of all rig tools. |
| `rig/sprites_only.py` | snes9x with background layers off (core options), for clean sprite captures. |
| `rig/replay.py`, `rig/liveness.py` | Seeded random input runs and the crash check. |
| `rig/bsnes_check.py` | Same checks in bsnes-mercury accuracy. |

## Reverse engineering

| Tool | What it does |
|---|---|
| `dis65.py` | 65816 disassembler with M/X width tracking. `dis65.py ROM BANK:ADDR LEN [m x]`. |
| `umk3rom.py` | HiROM address and file-offset helpers for the 4 MB dump. |
| `umk3_sprites.py` | UMK3 sprite set format: set headers, frame records, pieces, tiles, decode a frame. |
| `scan_id_tables.py` | Static scan for tables indexed by fighter id. Heuristic; confirm with the debugger. |
| `deluxe_diff.py` | Diff UMK3 against the UMK3 Deluxe hack (read only; how Deluxe expanded the ROM). |
| `trace_dma.py` | Log DMA transfers into video RAM during a scripted run. |
| `vram_blockfill_test.py` | Fill VRAM blocks with solid colour to see which tiles a fighter uses. |
| `capture_set_frames.py` | Capture every frame of a sprite set from the running game, in object-local coordinates. |
| `record_actions.py`, `action_sheet.py` | Which sprite frames P1 shows for each action; contact sheets. |
| `rig/ram_scan.py` | RAM words that change steadily while an input is held. |
| `rig/who_writes.py` | Code that writes, reads or executes an address while an input is held. |
| `rig/pose_timing.py` | Frames shown per sprite frame for buttons, specials and being hit. |
| `rig/sleep_trace.py` | UMK3 animation sleeps (`$88:C637`) and counted holds (`$86:8B7E`) per thread. |
| `rig/sound_events.py` | UMK3 sound requests (`$84:FE62`) and DSP key-ons (sample, pitch, volume). |
| `rig/br_actions.py`, `rig/br_pose_match.py` | Play each Batman Returns control and match every frame to the ripped poses (exact sprites). |
| `analysis/*.py` | One-off scripts from the first sprite-engine investigation (OAM record formula, tile sources, Y tables). Kept as a record; findings in `Current_Work.md`. |

## Assets

| Tool | What it does |
|---|---|
| `dump_br_sprites.py` | Render Batman's tiles from Batman Returns video memory. |
| `tilesheet.py` | Render 4bpp tiles from any ROM region (find graphics by eye). |
| `batman_art.py` | Palette, pose loading and piece packing for the UMK3 sprite engine. |
| `make_frame_map.py` | `art/batman_frame_map.json`: which Batman pose replaces each ninja frame (explicit and by shape). |
| `review_map.py` | Side-by-side review sheets of the frame map. |
| `make_win_banner.py` | Compose the BATMAN WINS banner from the game's banner letters. |
| `brr.py` | SNES BRR codec (decode, encode, read a sample directory from sound RAM). |
| `extract_br_sounds.py` | Pull Batman Returns samples out of sound RAM and save WAVs. |

## ROM patches (used by `build_batman.py`)

Each module's docstring explains the game mechanism it patches and how it was found.

| Tool | What it does |
|---|---|
| `build_batman.py` | The build: expands the ROM, writes Batman's sprite set, collision boxes, and runs every patch below. |
| `exhirom.py` | 4 MB HiROM to 8 MB ExHiROM, free-space allocator, checksum. |
| `batman_moves_patch.py` | Batman's special moves and finishers (move table format documented inside). |
| `batman_controls_patch.py` | Batman Returns buttons for Batman only, during fights (pad reads at `$80:FDCE` / `$80:FDDC`). |
| `batman_timing_patch.py` | Batman Returns walk speed and frame timing (sleep hook at `$88:C637`, walk tables). |
| `batman_sound_patch.py` | Batman Returns samples on donor sound ids, Batman only. |
| `move_list_patch.py` | Move list screen before round 1; also the small `Asm` helper (labels, branches) other patches use. |
| `batman_pause_patch.py` | START pauses a fight that has Batman in it and shows the move list (START handlers `$88:A978` / `$88:A986`, BG3 save and restore). |
| `roster_portrait_patch.py`, `vs_portrait.py`, `tower_face_patch.py`, `hud_name_patch.py` | Portraits, tower face, HUD name. |
| `make_batman_fighter.py`, `make_batman_reskin.py`, `batman_vram_test.py` | Earlier approaches: a sprite overlay at the OAM DMA, a palette and name reskin, a VRAM drawing proof of concept. Superseded by `build_batman.py`; kept as a record. |

## Conventions that matter

- Patching code in banks `$80-$BF`/`$C0-$FF` of the expanded ROM: also write the same bytes at file offset
  + `0x400000` (the bank `$00-$3F` copy), as every patch here does.
- Do not keep hook state in a RAM area you have not proven unused. `$7E:03F8` looked free and was the direct page
  of a game thread; it crashed the game. Check with `rig/who_writes.py` over a long run first.
- A hook that overwrites part of an instruction must redo the overwritten instructions itself and resume after
  them (see `batman_timing_patch.py`).
- Verify every build with `rig/liveness.py` seeds before calling it done.
