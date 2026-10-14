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

## Deluxe ROM analysis (v2.3)
- Uploaded file is a full 8 MB ROM (not a patch). Header "UMK3 DELUXE", map byte 0x35.
- Readme (5025readme.txt) claims: Sheeva playable (with VS screen and finishers),
  Rain and Noob Saibot available in towers, Animalities, 3x3 mode, Shang Tsung -> Smoke.
- Fighter name table at file 0x3E544 is byte-identical to the original.
  So Sheeva is not added to the original ID table. Her ID mapping is elsewhere (not found yet).
- Byte diff vs original (first 4 MB): 18,832 changed bytes in ~124 ranges spread across the ROM.
  Deluxe has extra data in the upper 4 MB (bytes 0x400000-0x7FFFFF).
- Sheeva string "PLAYABLE SHEEVA, 9 NEW STAGES" at file 0x3BC6B in Deluxe.
- Next: trace which code path the changed ranges belong to (Sheeva select/VS data).

## Community data received (user-provided)
- Base ROM SHA-1 09C094CA1114BCB6D5917E989686CA79B96CF9EA and CRC32 F5BFE41E:
  VERIFIED against the uploaded original (sha1sum and CRC32 match).
- Deluxe credit given as "Lucas Dext5r". Earlier search result said "Lucas Ferreira". Unresolved.
- Deluxe claimed ROM expansion to 16 MB. Uploaded Deluxe v2.3 file is 8 MB (8,388,608 bytes).
  CONFLICT: may be a different Deluxe build or a wrong claim.
- Claimed mask change AND #$00FF -> AND #$FFFF. Checked at C3:E348 (file 0x3E348): unchanged
  in the uploaded Deluxe file. The change, if it exists, is elsewhere.
- Screen codes 0B Versus, 0C Title, 0D Character Select, 0F Continue: consistent with the
  RAM map read earlier.

## Verified header facts (file evidence)
- Original UMK3 (USA): header ROM size byte $FFD7 = 0x0C (2^12 KB = 4 MB). File size 4,194,304 bytes.
- UMK3 Deluxe v2.3 upload: header ROM size byte $FFD7 = 0x0D (2^13 KB = 8 MB). File size 8,388,608 bytes.
  Header title "UMK3 DELUXE", map byte $FFD5 = 0x35 (original 0x31).
- Internal checksum $FFDE-$FFDF = 0x64E9 and complement $FFDC-$FFDD = 0x9B16 in BOTH ROMs.
  The Deluxe header checksum was not updated for its changes.

## Unconfirmed (not verified from files)
- Deluxe "16 MB" claim (user-provided source): not supported by the uploaded file (8 MB).
  MSU-1 explanation is a guess, not checked.
- Instruction mask change AND #$00FF -> AND #$FFFF: not found at file offset 0x3E348.
  Location still unknown. Needs a code search of the Deluxe ROM.
- Author handle "Lucas Dext5r" vs "Lucas Ferreira": same person is claimed by the user's
  source but not verified from any file in this repo.

## Mask change located (verified from bytes)
- Deluxe v2.3 changes AND #$00FF -> AND #$FFFF at two sites, file offsets 0x5C72E and 0x5C757
  (SNES C5:C72E and C5:C757). Opcode bytes: original 29 FF 00, Deluxe 29 FF FF.
- Both sites sit in the same code pattern: LDX $2A; PHX; ... AND #imm; JSL $85CD19; ... PLX.
  They share the JSL target $85:CD19.
- Only 2 bytes differ in the surrounding 256-byte block (C5:C700-C5:C7FF) and these two sites
  are the only AND #$00FF -> #$FFFF changes found in the whole ROM.
- Purpose of the code (what $2A holds, what $85:CD19 does) is NOT yet verified.
- Remaining Deluxe changes (~18,800 bytes across the ROM) are still unexplained.

## Routine $85:CD19 (verified from bytes, same in original and Deluxe)
- Entry: A = value to look up (16-bit, since the caller's AND #$FFFF widens it). Stores A to $0A,
  clears $4E.
- Compares A against 8 RAM words at $1B40, $1B3E, $1B3C, $1B3A, $1B38, $1B36, $1B34, $1B32.
  On match, returns A = 0x0E, 0x0C, 0x0A, 0x08, ... with carry clear (matching slot number).
- If no match: loop (16-bit X, step 2, X < 0x10) looks for an entry with bit 15 set (bmi).
  On a negative entry it branches to $85:CD8B. Otherwise checks $4E, returns carry set.
- Interpretation (inference, not yet verified): it maps a 16-bit ID to one of 8 RAM slots.
  Only the mask change at C5:C72E and C5:C757 widens the input to 16 bits.
- Still unknown: where A comes from before the AND at C5:C72E (caller code above C5:C700).

## Callers of $85:C72B (the block containing the mask change) - verified from bytes
- 62 JSL $85:C72B sites in the original ROM (C0, C2, C3, C6, C8 banks).
  The mask at C5:C72E sits on the path every one of these calls takes.
- 59 of 62 sites load A with LDA #imm16 (A9 lo hi) directly before the JSL. All 59 immediates
  are below $0100, so AND #$00FF and AND #$FFFF give the same result there.
  (Assumes 16-bit A at those sites; the 3-byte form implies this but it is inferred.)
- 3 sites take A from data, not a constant:
  * C0:C149  A = LDA $1C3F (RAM)
  * C2:9D79  A = LDA long $88:9D23,X or $88:9E19,X (ROM table)
  * C2:A114  A = LDA long $88:9DC9,X (ROM table)
  Read as 16-bit words, these tables contain values with nonzero high bytes
  (e.g. $0x1510, $0xAEAD, $0x8989). So the mask change could matter at these sites.
  Unverified: M flag at these sites (8-bit A would read only one byte), and what the
  table values mean.
- Inference (not verified): the Deluxe mask change targets these data-driven callers.

## M-flag and table layout check (C2:9D79, C2:A114, C0:C149)
Verified from bytes:
- The original code at C5:C72E is 29 FF 00. Under M=0 (16-bit A) this is AND #$00FF.
  Under M=1 it would decode as AND #$FF followed by BRK. So every valid caller must reach
  C5:C72E with M=0. This is a constraint from the code itself, not a flow trace.
- Tables $88:9D23, $88:9DC9 and $88:9E19 read as bytes look like 8-bit entries
  (e.g. 01 08 10 15 1A 27 ... ; 02 0A 12 17 1C 29 ...; AD AE AF B0 ... with 00 separators).
  The "high bytes" I reported earlier come from reading the next entry as the high byte in
  16-bit mode. They are not evidence that the tables hold 16-bit values.
- C0:C149 is preceded by REP #$A2 (M cleared = 16-bit) at file 0xBF37, nearest REP/SEP touching M.
  That is a straight-line result, not a verified flow result.

Not resolved (straight-line search is unreliable here):
- C2:9D79 and C2:A114: nearest M-touching instruction is SEP #$AB at file 0x9AA8 (sets 8-bit).
  That conflicts with the M=0 constraint above, so either the path has a branch the search
  does not follow, or the instruction at 0x9AA8 is not on the path. Needs a flow-aware trace.
- Index step for the tables (how X advances) not yet read.
- Net: the mask change may still have no effect at any call site. Unresolved.

## CORRECTION (supersedes the M-flag notes above)
- The earlier "SEP #$AB at 0x9AA8" result was WRONG. I passed C2:9D79 as file offset 0x9D79,
  which is bank C0, not bank C2. The correct file offset for C2:9D79 is 0x29D79.
  Also, the table reads I cited as $88:9D23 etc. are correct (file 0x89D23 maps to bank $88).
- Mapping used: bank $C2 maps linearly to file 0x20000 + address (HiROM). $C0 to 0x00000.

## Flow checks, corrected (straight-line and local consistency)
- Last M-touching REP/SEP before C2:9D79 is REP #$20 at C2:96FB (clears M = 16-bit).
  No later M-touching REP/SEP before the site. So M=0 along the straight-line path.
- Last M-touching REP/SEP before C2:A114 is REP #$A0 at C2:A073 (clears M = 16-bit).
  No later M-touching REP/SEP before the site.
- Local code agrees: C2:9D61-9D64 uses "bit #$0040" as a 3-byte immediate (89 40 00), and
  C2:9D5C uses "cpx #$000F" as 3-byte (E0 0F 00). Both only decode correctly with M=0 and X=0.
- Incoming branches to C2:9D79 come only from C2:9D6D and C2:9D73 (both internal).
  No incoming branch to C2:A114 (reached by fallthrough or by a call from elsewhere).

## Index progression (C2:9D40-9D7D)
- X = word from RAM $52C8,y. Then CPX #$000F with BMI:
  X < 15 (signed): reads $88:9E19,X (table with AD AE AF ...).
  X >= 15: tests bit $0040 of $5538,y; reads $88:9D23,X or $88:9D3F,X.
- X is not incremented in this block. The index is the value from $52C8, so each lookup
  reads a single element chosen by that value.
- With M=0, LDA long,X reads 2 bytes (table[X] and table[X+1]).
  So the 16-bit A passed to C5:C72B has low byte = table[X] and high byte = table[X+1].
  The original AND #$00FF keeps only table[X]. The Deluxe AND #$FFFF keeps both.
- Inference (not verified): if the tables are byte-indexed, the Deluxe change alters the
  value at these three sites. Whether that is intended is not verified.

## RAM table $52C8 (indexed by slot, writers found)
- 34 write sites (STA/STA abs,x/abs,y to $52C8 region) found by byte scan. Spot checks:
  * C0:89F4  STA $52C8,X  value = $52C8,Y (copy from another slot), index X = $2A (slot).
  * C0:9182  STA $52C8,Y  value = $52C8,X (copy).
  * C0:B2DE  STA $52C8,X  value = constant $0004 (after JSL $80:F5B5 check).
  * C0:D62E  STA $52C8,X  value = constant $0010.
  * C0:F770  STA $52C8,Y  value = $52C8,X (copy).
- Constants written: $0004, $0010 (and $0008 near C0:89E0 writes to a different table).
  These are small codes, which fits the C2:9D40 use of the value as an index with CPX #$000F.
  Inference only: $52C8 is a per-slot state or mode code, not a fighter ID. Not verified.
- Remaining: caller of C2:A114 (no branch into it; reached by JSR/JSL from elsewhere).
  The JSR scan was noisy (unaligned matches), so this needs a flow-aware check.

## Emulator testing (added)
- Installed retroarch (apt) and libretro-snes9x. RetroArch front end aborts here
  (GameMode D-Bus hook, unavoidable), so testing uses tools/libretro_harness.py,
  a ctypes libretro frontend that loads snes9x_libretro.so, feeds joypad input, and saves frames.
- Verified: original UMK3 boots, title screen renders, START goes to mode select,
  then to the fighter roster grid, then "CHOOSE YOUR DESTINY" (frames saved in scratchpad).
- Frame stride: core reports pitch 1208 bytes for 256x224 XRGB8888. Using 1208 gives a sane image;
  1024 gives garbage. The harness uses the reported pitch.
- Roster grid frames differ by about 16 mean intensity between consecutive frames, so the
  screen animates. Colour and portrait detail are noisy and not yet reliable for identifying
  fighters. Deluxe and original roster frames were captured at the same point (scratchpad).
- Not yet verified: that Sheeva appears in the Deluxe roster, or that any fighter plays.

## Harness colour bug (corrected)
- The earlier "palette corruption" images were a HARNESS bug, not the game. snes9x requested
  RGB565 (pixfmt 2). The harness accepted the request but decoded XRGB8888, which scrambled colours.
- Fixed: the harness now records the requested pixel format and decodes RGB565 correctly.
  The UMK3 title screen renders cleanly with the fix.
- Roster screens (original and Deluxe) now render cleanly (scratchpad roster_orig.png,
  roster_deluxe.png). Grid layouts look identical by eye: 7 cells in rows 1 and 2, 5 in rows 3
  and 4, plus the Random cell. Background colours differ (grey vs purple).
  Pixel diff is about half the pixels, which is dominated by the animated background, so it
  does not settle whether the portraits differ.
- Conclusion so far: Sheeva is not visible on the default roster grid of the Deluxe ROM.
  Her selection path is still unknown (the Deluxe readme mentions Sheeva as playable but not
  how to select her).
