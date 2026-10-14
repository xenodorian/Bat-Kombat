# Current Work: Batman as playable fighter in UMK3 (SNES)

## Goal
Add Batman (sprites + moves from Batman Returns) as a new playable fighter in
Ultimate Mortal Kombat 3 (USA), with all moves shown on the move list screen.
Deliver a patched ROM (not committed to git; ROMs are commercial dumps).

## Tools installed
- cc65 (ca65/ld65/da65) via apt
- Python 3.13 with capstone 5.0.7 (65816 disassembly), py65
- No SNES emulator available in container; patches are verified by reading code and
  by static checks only.

## ROM facts (verified)
- UMK3 (USA): 4 MB HiROM, header at $C0:FFC0, title "ULTIMATE KOMBAT 3".
  File offset X maps to bank $C0 + (X >> 16), address X & $FFFF.
- Batman Returns (USA): 1 MB LoROM, header "BATMAN returns".
- Fighter name strings: ASCII, null-terminated, file 0x3E480..0x3E53E ($C3:E480..).
- Fighter ID name table: file 0x3E544, one word per ID (25 entries, IDs 0..24).
  ID: 0 KANO, 1 SONYA, 2 JAX, 3 NIGHTWOLF, 4 SUB-ZERO, 5 STRYKER, 6 SINDEL,
  7 SEKTOR, 8 CYRAX, 9 KUNG LAO, 10 KABAL, 11 (null pointer, empty slot),
  12 SHANG TSUNG, 13 LIU KANG, 14 SMOKE, 15 KITANA, 16 JADE, 17 MILEENA,
  18 SCORPION, 19 REPTILE, 20 ERMAC, 21 SUB-ZERO (duplicate ptr), 22 SMOKE (dup),
  23 NOOB SAIBOT, 24 RAIN. No RAIDEN string in ROM.
- Code reading the table: bank $C3 at $E35x-$E38x. Slot index in $F58C,
  per-slot fighter ID word at $F548,X (FFFF = none), name = table[ID]
  (FFFF -> "? ? ? ? ?" at $E480).
- Batman Returns graphics: uncompressed 4bpp rendering of 0x00000-0x7FFFF
  produces noise, so sprite data is compressed. Compression not yet identified.

## Todo
- [ ] Map fighter ID -> data tables (code that reads 0x3E544 table)
- [ ] Locate roster / select-screen tables and fighter count
- [ ] Locate fighter sprite/animation and move-list data
- [ ] Decompress/extract Batman Returns Batman sprites
- [ ] Build Batman fighter data (graphics, moves, hitboxes)
- [ ] Add move list entries for Batman
- [ ] Apply patch to a copy of the UMK3 ROM and write output
- [ ] Commit tooling and notes to claude/keen-clarke-i6br28 (no ROMs)

## Progress log
- Verified ROM headers and fighter name table.
- Mapped fighter ID -> name table and slot lookup code (bank C3, $E330-$E390).
- Rendered Batman Returns 4bpp tile sheets (tools/tilesheet.py). Output is noise
  except 0x08000 region which looks structured. Sprite decompression not yet found.

## Blockers (as of this log)
1. Batman Returns sprite compression is unidentified. Without decompressed
   Batman sprites there is no graphics to put in UMK3.
2. UMK3 fighter data layout (graphics pointers, move/hitbox tables, AI,
   move list screen) is not mapped beyond the name table.
3. No emulator in container, so no run-time verification. Patch can only be
   checked by static reading and tile rendering.
4. Adding a new roster ID means extending every ID-indexed table; none are
   fully enumerated yet. ID 11 is an empty slot that could host Batman if it
   has no other side effects, but this is unverified.

## Status
Not complete. No patch produced. Tools in tools/ are analysis helpers only.

## Online research (round 2)
- Data Crystal UMK3 SNES page: header only (HiROM, 4 MiB, CRC32 F5BFE41E). No fighter/ROM map data.
- Data Crystal and Cutting Room Floor sub-pages: 404, 403 or not indexed.
- No Batman Returns SNES ROM map or graphics compression documentation found.
- No public documentation found for UMK3 SNES fighter data, move lists or sprite compression.
- Hack leads: "Ultimate Mortal Kombat 3 Deluxe" (SNES, Lucas Ferreira, v2.3) reportedly
  makes Sheeva playable, so it added a roster entry. romhacking.net page for it returned 403.
  Its patch and notes may document the roster-expansion method. Not yet obtained.
- Generic SNES guidance found: decompression is done by the game's own 65816 code,
  so the practical method is tracing the game's loader in an emulator.
