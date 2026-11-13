# Work plan: finish porting Batman into UMK3 (SNES)

Written 2026-11-12. This file is the handoff. Read it first, then `README.md` (what exists) and the dated
sections at the end of `Current_Work.md` (how each part was found). Update the status column and push after
every step.

## Rules for whoever continues

- Owner's order of priority: moves, move list, fatalities, then everything else.
- Commit and push after each step, to `claude/keen-clarke-i6br28` and to `main`. Append a dated section to
  `Current_Work.md` with what was found, what was checked, and what was not checked.
- No em dashes or emojis in any text. Do not state something as verified unless it was run in the emulator.
- Do not ask the owner to test or patch. Build the ROM, test it in the harness, put it in `release/`.
- Only moves of the male ninjas (Scorpion, Reptile, Ermac, classic Sub-Zero, human Smoke, Noob, Rain) run
  correctly on Batman. Moves of other body types use other frame numbers and break. This was tested.

## How to build and test

```
unzip "Ultimate Mortal Kombat 3 (USA).zip" -d build/
python3 -I tools/build_batman.py "build/Ultimate Mortal Kombat 3 (USA).sfc" build/UMK3_Batman.sfc
```

- Emulator: `tools/build_dbg_core.sh` builds the patched snes9x core to `/opt/snes9x_dbg/`.
  A new container needs this first, plus `pip install numpy pillow capstone`.
- `tools/rig/lab.py`: `lab.fight(rom)` gives a live two-player fight (Batman vs idle Noob) with save states.
- `tools/rig/exp.py`: `film(rom, [("DR", ["Y"]), ...], out.png)` plays inputs and writes a contact sheet.
- `tools/rig/fat.py`: `finish_state(rom)` reaches FINISH HIM; `film(c, st, "DDR", "X", out.png)` films a finisher.
- Buttons: Y high punch, B low punch, X high kick, A low kick, L block, R run.
- Look at every screenshot you make. Most bugs so far were visible only in the picture.
- After each change run tools/rig/liveness.py on several seeds. Do not rely on identical frames to detect a
  hang: a crashed game can still change the picture (found 2026-11-13).

## Where things live in the ROM (all verified unless marked)

| Thing | Location |
|---|---|
| Batman sprite set, header | `$40:0000` (expanded ROM), swapped in for set 27 by the hook at `$FF:DC6E` |
| Batman's copy of set 16 (vial) | expanded ROM, swapped in for set 16 by the same hook (`hook_code(swaps)`) |
| Special-move pointer tables, per button | `$82:BAC9` HP, `$BB01` LP, `$BB39` BLOCK, `$BB71` HK, `$BBA9` LK, `$BA91` RUN |
| Batman's move matcher copy and table | `$FF:E000-$E17F`, reached from the stub at `$82:EA7C` |
| Sound hook | `$FF:E180` (after the move table) |
| Pad reads (controls remap) | `$80:FDCE` pad 1, `$80:FDDC` pad 2, JSL to expanded ROM |
| Walk tables | `$88:9729` forward, `$88:9799` back, 4 bytes per fighter: pose delay, speed (1/256 px) |
| Screen mode | `$7E:3A7E`: 0 fight, 13 roster, 11 VS, 14 stage intro |
| Fatality jump tables | `$82:802D` (first), `$82:8065` (second), index fighter id * 2 |
| Move list text and code | `$FF:DD00`, hooks at `$85:E834` and `$85:E8E4` |
| VS portrait tables | `$83:EEFA` gfx, `$EF2E` map, `$EF62` palette, `$EEC6` bank, `$EE92` count, `$EFE6` mirror |
| VS portrait loader | `$FF:E400`, replaces three calls to `$88:AD30` |
| Banner set 19 copy | expanded ROM, set table entry 19 at `$86:EAEC` / `$86:EB24` |
| Rain palette / mirror palette | file `0x3EAFAF` / `0x08C4AD` |
| Fighter ids in a fight | `$7E:52C8` (P1), `$7E:52CA` (P2); also `$7E:36D0` and `$7E:3894` |
| Health | `$7E:36D4` (P1), `$7E:3898` (P2) |
| Round wins | `$7E:36E0` (P1), `$7E:38A4` (P2). Seen 0 -> 1 after one round win. Not yet used. |
| Round number (candidates) | `$7E:3A90` or `$7E:3ACA`, both went 1 -> 2. Not yet told apart. |
| Tower face hook and data | `$FF:E480` code, `$FF:E500-$EAFF` face tiles, hook at `$86:DD83` |
| Free space left in bank `$FF` | `0x3FDCB7-0x3FDCFF`, after the move list (`about 0x3FDE80`) to `0x3FDFFF`, `0x3FE290` to `0x3FE3FF` (check), `0x3FE440-0x3FE47F`, `0x3FEB00-0x3FEFFF` |
| Free space in bank `$82` | `$82:FF0B-$FF70`, `$82:EA80-$EAD3` |

## Status

| # | Item | Status |
|---|---|---|
| 1 | Batman drawn by the engine, P1 and P2 | done |
| 2 | Roster portrait, health-bar name | done |
| 3 | Specials: Batarang, Smoke Teleport, Grapple Gun, Explosive, Cape Charge, Spin Kick | done |
| 4 | Move list screen before round 1 | done |
| 5 | Two fatalities, babality, stage fatality | done (stage fatality and babality are Rain's; both checked 2026-11-13 with tools/rig/move_check.py, stage fatality on stages 2 and 6) |
| 6 | BATMAN WINS banner | done |
| 7 | VS screen portrait | done |
| 8 | Mirror match palette | done |
| A | Move list shows again before every round | fixed 2026-11-12 (241 frames before round 1, 0 before round 2) |
| B | Batman Returns moves; pose review (2026-11-13: every BR animation measured and applied where UMK3 has a counterpart, see Current_Work.md) | 2026-11-12: 29 more frames mapped by hand (217 explicit, 26 by shape left: crouch variants, weapon frames 234-241, lying frames); throw now grab, roll, kick off. Earlier: | glide poses on the teleport flight done 2026-11-12; a held glide from a jump is not possible without new code; throw left as is |
| C | Effect art | C1 grapple hook and C2 explosive vial done 2026-11-12; the blast and rope are still the originals |
| D | CPU-controlled Batman | checked 2026-11-12: two full rounds, no crash, uses the dash; no projectile seen |
| E | Sounds | done 2026-11-13: Batman Returns swing, impact and batarang samples for Batman only; Rain's voice silenced (tools/batman_sound_patch.py) |
| F | Friendship, ending text, attract-mode bio | friendship added 2026-11-12; ending/bio text is compressed, location partly found, not replaced |
| G | Other emulators and real hardware | bsnes-mercury accuracy core checked 2026-11-12 (boot to specials, all fine); hardware and Mesen not checked |
| H | Small face on the one-player tower ("Choose your destiny") | done 2026-11-12 (tools/tower_face_patch.py) |
| I | Batman Returns controls for Batman | done 2026-11-13; 2026-11-12 B -> Up removed so B stays low punch and jump stays Up |
| J | Boxes fit the sprites; Batman Returns speed and timing | done 2026-11-13: full drawn bounds; walk, punch, Batarang, block, hit reaction (tools/batman_timing_patch.py) |
| N | Controls and move list work in every mode (R alone did the Cape Charge) | done 2026-11-13, fixes item M (the $3A7E controls bug): the remap tested the stage number $7E:3A7E instead of a fight flag, now $7E:36C0 = 2, 5 or 7; B + Y with a 3-frame window; matcher copy only tries the pressed button's records and no longer refuses A-button finishers for player 2. tools/rig/move_check.py: 0 failures in 6 modes |

## Steps, in order

### A. Move list only before round 1 (small)

Found: the kode text screen routine `$85:E805` runs before every round, so the list shows for four seconds
before each round (measured: 240 frames between rounds in a two-player match).
Do: in `tools/move_list_patch.py`, in both `has_batman` tests, also require both round-win counters
(`$7E:36E0` and `$7E:38A4`) to be zero. Check that the list shows before round 1 and not before round 2,
and that a match with a kombat kode still shows the kode text.
Optional: let START skip the screen (the wait loop is at `$85:E93D`, counter in `$36`).

### B. The rest of Batman's own moves

Batman Returns (SNES) move set, and what covers it now:

| Batman Returns move | In UMK3 now | Plan |
|---|---|---|
| Punch, kick, crouch attacks, jump kick | Rain's normals with Batman poses | keep; review pose timing (B4) |
| Cape block | block pose 39 | keep |
| Batarang | Batarang (Reptile spit code) | done; consider full-screen speed (B3) |
| Grapple gun | Grapple Gun (spear) | done; redraw hook (C1) |
| Test tube explosive | Explosive (Ermac fireball) | done; redraw (C2) |
| Cape glide | none | B1 |
| Grab, head slam, throw | Rain's throw with fallback poses | B2 |

- **B1 Glide.** Checked 2026-11-12: the air version of Smoke Teleport fires from a jump (frames 73, 41, 171, 172).
  Frame 41 is also the jump punch, so it cannot simply become a glide pose. A real glide needs its own frames:
  give the air teleport a private frame by pointing its animation at an unused set-27 frame, or leave as is.
  Original notes: Candidates from the ninja pool: the air version of the teleport punch (kind 1 record, already
  allowed in the air, not yet filmed), Scorpion's air throw (BLOCK table stub `$82:BCB3`, complex stub, read it
  first). Simplest honest version: map the air teleport frames 41 and 171 to glide poses 95, 96, 97 and 34 and
  name it Glide Strike. Film it from a jump: `("U" then "DL" + Y)`.
- **B2 Throw.** Checked 2026-11-12: forward + low punch at close range works. Rain's throw is a back roll,
  frames 26, 27, 28, 29, 30, 31, 33, then 172. Current poses: 12, 78, 78, 61, 65, 61, 62 (26 to 28 are shape
  fallbacks). It reads as a roll throw already. Possible polish: 26 -> pose 73 (grab), 27 and 28 -> pose 62.
  Original notes: Record which frames Rain's throw uses (`tools/record_actions.py`, add a close-range forward +
  low punch action with P2 adjacent), then map them in `EXPLICIT` in `tools/make_frame_map.py` to poses 73, 74
  (grab) and 92 to 94. The opponent's thrown frames are the opponent's own, nothing to do there.
- **B3 More specials if wanted.** Tested and working on fighter 24, not yet assigned: Reptile force ball slow
  `$C9BE` and fast `$C994`, slide `$C87C` (button code `$1A`, no direction sequence), invisibility `$C732`,
  Sub-Zero ice ball `$C9CC` and ground ice `$C9D3`, Ermac slam `$C72B` and teleport `$C8A6`, Noob disabler
  `$C9E5`, shadow throw `$C9E9`, teleport slam `$C9E1` (button code 8), Rain orb `$C9F1`, lightning `$C9ED`.
  Add a line to `MOVES` and `MOVE_LIST` in `tools/batman_moves_patch.py`. The table is in bank `$FF`, so there
  is no space limit now. Keep the move list at 38 characters per line and about 12 lines.
- **B4 Pose review.** Run `tools/action_sheet.py` on the new build and compare each action with the Batman
  Returns animation order. The poses come from `art/batman_poses.tar.gz` (see the numbered sheet made by the
  snippet in `Current_Work.md`, step 1). Frames still on shape fallback are listed by `tools/make_frame_map.py`
  (56 of 243). Fatality-only frames of the other ninjas matter only if their fatalities are assigned.

### C. Effect art

Projectiles and effects owned by Batman are drawn from Batman's set when they are set-27 frames
(checked for frames 257 to 269). Add entries next to `BATARANG` in `tools/build_batman.py`.

- **C1 Grapple hook.** Spear head is set 27 frames 290 to 292 (object slot 16). The rope is set 0 frames 8, 9
  in slots 44 to 50, and set 17 frames 6, 10, 13 in slot 6 was also seen during the spear: those sets are
  shared, leave them. Redraw 290 to 292 from pose 84 (the grapple line and hook) or from the hook end of pose 81.
  Find the palette the same way as for the batarang (dump OAM palette of slot 16 during the move).
- **C2 Explosive.** Ermac's fireball is set 16 frames 73 to 76 and the blast is set 18 frames 1 to 8. Both are
  shared sets, so they cannot be redrawn for Batman alone without a second hook like the one for set 27.
  Option: extend `hook_code` in `tools/build_batman.py` to also swap set 16 when the owner is fighter 24, with
  a copy of set 16 where 73 to 76 show the test tube (poses 86 to 88 have the tube and burst drawn in).
  Do this only if C1 went smoothly.
- **C3** Batarang hit: frames 262 to 269 keep the batarang flying to the end; if a hit spark is wanted, use
  the last two frames.

### D. CPU Batman

Not checked. In a one-player ladder Batman can also be the opponent (Rain's slot in the tower). Watch a CPU
Batman for 3 rounds and log `$7E:52F8+2` frames. Risk: the CPU logic for fighter 24 may call Rain's orb
(`$84:CD5E`) and lightning (`$84:D065`) directly instead of through the move table. Those still exist, so
this should only look wrong (orb graphics), not crash. If it does call them, find the CPU move list for
fighter 24 (watch reads of `$7E:52CA` from bank `$81`/`$82` while the CPU acts) and point it at the new handlers.

### E. Sounds (optional, large)

Rain's voice and hit sounds are unchanged. No work done on the SPC side. Batman Returns sound data has not
been looked at. Skip unless the owner asks.

### F. Text and extras

- Friendship: fighter 24 has none. A kind-6 record with handler `$F2D1` (bank `$83`) could reuse a ninja's
  friendship. Not tested.
- Ending and attract-mode bio text (2026-11-12): stored compressed, so plain searches only find fragments.
  A block around file `0x259D08` (bank `$E5`) holds Rain's text (fragments "BIR..D FROM", "ORIGIN", "RAIN'").
  The general decompressor `$88:AD30` reads a header (word: output size, byte: mode; mode 2 is a second scheme
  at `$88:AE7D`) and writes the output backwards. Command byte: bit 7 long back-reference (11-bit distance),
  bit 6 another reference form, bit 5 short reference (low 5 bits), none set = literal run of 1-31 bytes
  (jump table `$88:B15E`), 0 = end. To replace the text: write an encoder that emits only literal runs, check it
  by decompressing original blocks with a Python port and comparing to RAM, find the pointer to the Rain block,
  and point it at the new block. Seeing the ending requires finishing the one-player game (poke health).
  Old note: Strings are plain ASCII (see the string dump in
  `Current_Work.md`, step 2); search near `06B8F0` and the name table at file `0x3E544`.
- The name table entry `-RAIN` (file `0x3E544 + 48`) is used somewhere not yet identified; the old reskin
  patch changed it to `-BATMAN`. Check where `-RAIN` still shows (tournament screen is the likely place).

### G. Wider testing

- Run the release in bsnes or Mesen (more accurate than snes9x). Things to watch: the 8 MB ExHiROM header,
  the hook timing, the VS screen.
- Checked 2026-11-12: Noob Saibot's win banner, FINISH HIM and FATALITY draw correctly from the set-19 copy.
- Stage fatality: checked 2026-11-13 on stages 2 and 6 (stage forced through `$7E:3A84`, see tools/rig/move_check.py).
  Still open: every other fighter's win banner (set 19 frames 65 to 97 were copied), one-player ladder to the end.

### H. Tower portrait

In a one-player game the tower screen shows a small face for the player at the foot of the tower. For
fighter 24 it is still the purple ninja face. `tools/roster_portrait_patch.py` only covers the select grid.
Find it the same way as the VS portrait: watch which ROM data is read while the tower screen loads with
fighter 24 versus another fighter (`tools/dbg_core.py`, `watch_read`), then decode and replace.

## Known limits that are by design

- Batman's normal attacks, hit boxes and damage are Rain's. Changing them means editing per-fighter code,
  not tables, and is out of scope unless asked.
- The VS portrait is an enlarged in-game sprite because Batman Returns has no large Batman portrait in the
  sprite rip. A hand-drawn 128 x 176 picture with 63 colours can replace it: see `tools/vs_portrait.py`.
