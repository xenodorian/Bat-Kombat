# Bat-Kombat: Batman in Ultimate Mortal Kombat 3 (SNES)

Batman, with his sprites from Batman Returns (SNES), is a playable fighter in Ultimate Mortal Kombat 3 (USA).
He takes Rain's slot (top-left cell of the fighter select grid).

**Play it:** `release/UMK3_Batman.zip` holds the patched ROM (8 MB, ExHiROM). Tested in snes9x only.

![Batman actions](deliverables/batman_actions.png)

## What works

- Batman is drawn by the game's own sprite engine, so position, facing, scrolling, shadows, hit detection and
  animation timing are the game's. He works as player 1 and as player 2 (mirrored).
- 243 of Rain's body frames are replaced by 55 Batman poses: stance, walk, run, crouch, block, jumps, punches,
  kicks, uppercut, sweep, hit reactions, knockdown, get-up, dizzy and victory.
- Select screen: Batman portrait in Rain's cell, Batman standee. Health bar name reads BATMAN.
- Other fighters are untouched, including the other ninjas that share Rain's sprite set.
- Stress test: 12,000 frames of random input in one-player and two-player modes without a hang.

## What is still Rain

- Moves, hit boxes, damage, special-move inputs and sounds are Rain's. Batman's poses are fitted to them.
- Rain's projectiles and effects (frames 250 and up of the ninja set) are unchanged, drawn in Batman's palette.
- Poses are matched by hand for the common actions and by silhouette shape for rarer ones (other ninjas'
  special moves, fatality frames). Some of those reuse the guard pose.
- The game has no move list screen, so none was added.
- See `Current_Work.md` (last section) for the VS-screen portrait and win-banner status.

## Rebuild

Needs Python 3 with numpy and Pillow. The original ROM is in `Ultimate Mortal Kombat 3 (USA).zip`.

```
unzip "Ultimate Mortal Kombat 3 (USA).zip" -d build/
python3 -I tools/build_batman.py "build/Ultimate Mortal Kombat 3 (USA).sfc" build/UMK3_Batman.sfc
```

To change which pose replaces which frame, edit `EXPLICIT` in `tools/make_frame_map.py`, rerun it (it needs a
frame capture, see below), then rebuild. `art/batman_frame_map.json` also accepts per-frame `dx`/`dy` nudges and `flip`.

## How it works

1. **Sprite format.** `tools/umk3_sprites.py` documents and decodes the engine's format: a sprite id is
   `set << 9 | frame`; each set has a header pointing to a frame table, a bank table and a tileset table; a frame
   record lists 16x16 and 8x8 pieces with positions and tile references; tilesets may be raw 4bpp.
2. **New set.** `tools/build_batman.py` writes a Batman set with the same frame numbering as set 27 (the male
   ninja set), using raw tiles, into the free space of an 8 MB ExHiROM image (`tools/exhirom.py`).
3. **Hook.** The set lookup at `$88:A47A` calls a 72-byte routine at `$FF:DC6E`. When the object's fighter id
   (`$7E:52C8,y`) is 24 and the set is 27, it loads the Batman header. Nothing else in the engine changes.
4. **Limits respected.** A fighter owns 64 tiles of video RAM and a 45-piece buffer. The packer in
   `tools/batman_art.py` keeps every frame inside both, trimming dark cape-edge pixels first when it must.
5. **Palette.** Rain's 16-colour sprite palette at file `0x3EAFAF` is replaced (14 colours plus black).
6. **Cosmetics.** `tools/roster_portrait_patch.py` and `tools/hud_name_patch.py`.

## Workflow for this kind of port

1. Get a debugger first (`tools/build_dbg_core.sh` builds a patched snes9x core; `tools/dbg_core.py` wraps it).
2. Log the ROM reads during one animation step and disassemble the reader (`tools/dis65.py`). That gives the format.
3. Write an offline decoder and prove it against the running game (`tools/capture_set_frames.py`: 355 of 380 frames match exactly).
4. Find the engine's limits before drawing anything: tile slots, piece buffers, banner memory.
5. Build the smallest end-to-end test (every frame = one pose) and look at a screenshot.
6. Record which frames each action uses (`tools/record_actions.py`), map poses, review side by side (`tools/review_map.py`).
7. Test both player sides, other fighters, round banners, and a long random-input run (`tools/action_sheet.py`).

## Files

- `tools/build_batman.py`, `batman_art.py`, `exhirom.py`, `make_frame_map.py`: the build.
- `tools/umk3_sprites.py`, `capture_set_frames.py`, `record_actions.py`, `review_map.py`, `action_sheet.py`, `dis65.py`: analysis and tests.
- `tools/libretro_harness.py`, `dbg_core.py`, `umk3_nav.py`: emulator harness, debugger, menu navigation.
- `art/batman_poses.tar.gz`: 100 Batman poses (a sprite rip of Batman Returns). `art/batman_frame_map.json`, `art/ninja_frames.json`: mapping data.
- `Current_Work.md`: full history, including earlier approaches that did not work. `ROUTINES_UMK3.md`: earlier routine notes.
- Superseded, kept for history: `tools/make_batman_fighter.py` (sprite overlay hook), `tools/make_batman_reskin.py` (palette swap), `NEXT.md`.
