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

# REVIEW AND PLAN (written after the full work-to-date review)

## Accomplished (verified)
- Tools: cc65, capstone (65816), Pillow, numpy, Playwright, retroarch + snes9x core,
  tools/umk3rom.py (address mapping, disassembly), tools/tilesheet.py,
  tools/libretro_harness.py (headless emulator with input scripting, frame capture).
- ROM facts: UMK3 is 4 MB HiROM (SHA-1 matches the No-Intro hash). Batman Returns is 1 MB LoROM.
  Deluxe v2.3 is 8 MB. Linear HiROM mapping: file = ((bank - 0xC0) << 16) | addr.
- Fighter name pointer table at file 0x3E544, 25 IDs (0 to 24). ID 11 has a null pointer.
  IDs 21 and 22 repeat the Sub-Zero and Smoke names.
- Name lookup code (bank C3, $E330-$E390): slot index in $F58C, per-slot fighter ID in $F548.
- Emulator works. Original UMK3 boots to the title, mode select, roster grid, and
  "Choose Your Destiny". Deluxe boots and shows a roster that looks the same as the original.
- Batman Returns graphics are compressed (raw tile views are noise).
- The libretro core exposes SYSTEM_RAM (128 KB) and VIDEO_RAM (64 KB) for reading.

## Not accomplished
- No Batman sprite extracted. No UMK3 fighter record layout found. No new fighter ID added.
- No patched ROM. No move list entry. Sheeva's selection path in Deluxe is unknown.

## Work that did not move the project (lesson)
- About half the effort went into the Deluxe AND-mask change at C5:C72E / C5:C757.
  Meaning still unknown and probably unrelated to adding a fighter. Stop pursuing it.
- Two of my own mistakes cost time: a bank-offset error (C2 vs C0 file offsets) and a harness
  pixel-format bug that produced "palette corruption" that was not in the game.

## Plan (ordered by payoff per effort)
Milestone ladder. Each milestone leaves a working ROM. Do not attempt full custom Batman
animation before M2 works.

Phase 1: Get Batman art without decoding Batman Returns compression  [size M]
 - Run Batman Returns in the harness, script input to reach gameplay, read VRAM and WRAM.
 - Isolate Batman's sprites: find the OAM shadow buffer in WRAM (544-byte structure that the
   game DMAs each frame), read tile indices and attributes, pull the 4bpp tiles from VRAM.
 - Get the palette from a frame (match tile pixels to the screen) or by finding the CGRAM
   shadow in WRAM.
 - Output: sprite sheets (PNG plus raw 4bpp) for idle, walk, punch, kick, jump, crouch, block,
   hit, fall. Visual check by rendering to PNG.

Phase 2: Find how UMK3 stores one fighter and which tables are indexed by fighter ID  [size L]
 - Use the Deluxe ROM as the answer key. Diff Deluxe against the original (124 ranges), keep
   the ranges that relate to Sheeva (graphics, pointer tables, win logic).
 - Test whether Sheeva is ID 11 (null name pointer in both ROMs). Check by reading fighter-ID
   RAM in the emulator after selecting her in Deluxe.
 - Enumerate every table with 24 or 25 entries that is indexed by fighter ID (pointer arrays,
   palettes, portrait data, move data, AI). Confirm with the emulator by reading WRAM while
   selecting each fighter.
 - Identify the fighter sprite format and compression by dumping decompressed fighter data
   from WRAM and VRAM while a known fighter is on screen, and matching it back to ROM.

Phase 3: Milestone M1, Batman selectable with a donor fighter's data  [size M]
 - Use the empty ID 11 (or a new ID 25) and copy a donor fighter's data tables.
 - Patch the name table with BATMAN, add the roster cell and portrait.
 - Expand ROM to 8 MB for new data, fix header size byte and checksum.
 - Emulator test: roster shows Batman, selecting him starts a match without crashing.

Phase 4: Milestone M2, Batman art replaces the donor's frames  [size XL]
 - Convert Batman sprite poses to UMK3's frame format. Map each donor animation frame to the
   closest Batman pose. Keep donor hitboxes and move data at first.
 - Emulator test: Batman walks, punches, kicks, jumps, blocks, gets hit, and wins or loses.

Phase 5: Milestone M3, move list entries  [size M]
 - Find the move list screen and its text encoding by driving the emulator to it and matching
   VRAM tiles to ROM data.
 - Add Batman's list (normal moves plus whatever specials he has).

Phase 6: Milestone M4, custom specials  [size XL]
 - Batarang projectile, grapple, cape move. Needs new animation scripts and hitbox entries.

## Risks
- UMK3 fighter sprite compression is unknown and may be the biggest unknown.
- Each fighter has hundreds of frames. Re-posing Batman art to match them is large.
- Without an in-emulator debugger only RAM and VRAM reads are available. Code tracing is
  static reading plus RAM diffing.
- The emulator test result is the only proof of any milestone. Do not claim a milestone
  without an emulator test.

## Agent results (verified by me against the ROM bytes)

### Deluxe diff agent (tools/deluxe_diff.py, scratchpad/agents/deluxe_diff/)
- WRONG claim in its report: "name table NOT unchanged". The 25-entry name POINTER table
  (0x3E544-0x3E575) is identical. The one byte at 0x3E5CA that differs is an immediate in code:
  orig  LDA #$000B ; STA $3A7E   ->   Deluxe LDA #$001E ; STA $3A7E.
  $3A7E is the screen-mode variable (0B = Versus Screen in the Data Crystal RAM map).
  So Deluxe sets screen mode $1E there. $1E is not in the known list. Meaning unverified.
- WRONG classification: range 0x105E1A (D0:5E1A), 3567 bytes, was labelled "pointer-like".
  It decodes as NEW CODE in Deluxe (LDA #5 / STA $36 / JSL $88:C637 ... loop with DEC $36 / BPL).
  3527 of those 3567 bytes differ from the original, which held other data there. One caller
  found in Deluxe: JSL/JML to D0:5E1A at file 0x4A194.
- Deluxe header: map byte 0x35 (ExHiROM), size byte 0x0D (8 MB). The same title bytes appear at
  both 0x00FFC0 and 0x40FFC0 (the ROM is the original 4 MB data duplicated or extended).
  The agent's attempts to infer bank deltas for the upper 4 MB failed (its long_refs.tsv is unverified).
- Ranges: 193 at gap<=64 (earlier I counted about 124 at gap<=256). Credits text at C3:BBD9,
  strings "HIDDEN CHARS" (C3:D515), "3 ON 3" (C3:DFDE), "HIDDEN PORTAL" (C5:EBF3).

### ID-table scan agent (tools/scan_id_tables.py, scratchpad/agents/id_tables/report.txt)
- Its candidate list is noisy (5403 candidates). I checked the top 25-entry word/long tables myself.
- VERIFIED: Deluxe changed NONE of these tables (0 differing bytes in table plus 4 extra entries):
  0x3E544 (name), 0x0986C, 0x0D1F7, 0x1C5A6, 0x2A242, 0x2A5A6, 0x2C071, 0x2EC7B, sparse 0x68E15.
  So Deluxe enabled its extra fighter without editing these tables.
- VERIFIED: in these tables ID 11 has a distinct non-null entry that fits its neighbours:
    C0:986C  words  ... 98FA(ID10) 9904(ID11) 990E(ID12): regular +0x0A steps, so ID 11 is a real entry.
    C1:C5A6  ID11 = C61F (unique)       C2:A5A6  ID11 = A699 (regular +0x10 steps)
    C2:EC7B  all 25 distinct, ID11 = F01C       C2:A242 ID11 = FFA1 (unique value)
  The name table is the only one with a null at ID 11.
- Inference (not verified): ID 11 is an unused fighter slot (likely Sheeva, matching the Cutting
  Room Floor note about unused Sheeva data in the ROM) with data already present in per-fighter
  tables but no name pointer. Test later in the emulator by reading fighter-ID RAM while Sheeva
  is selected in Deluxe.
- Consequence for the plan: reuse ID 11 for Batman (replace the unused slot's data) instead of
  adding ID 25. Adding ID 25 would require extending every ID-indexed table and none of the
  tables above has room (many are packed against other data).

## Round 2 findings (dispatch 2)

### Sprite site shortcut closed
- Haiku agent: spriters-resource.com (all pages) returns HTTP 403 with cf-mitigated: challenge.
  No Batman Returns sprite sheet reachable. Not bypassed. Art must come from the ROM via emulator
  memory, or from a copy the user saves from their own browser.

### What Deluxe's code changes appear to be (verified bytes, interpretation marked)
- Options menu text: original "ENABLE MOTARO" (0x3D519) is replaced by "HIDDEN CHARS " in Deluxe.
  Data Crystal says $7E3BB0 is the Motaro enable option, so Deluxe repurposed that option as a
  hidden-characters switch (inference from the text swap, not yet seen working).
- Hook at C3:D405: original LDA #$0018 ; STA $3A7E ; Deluxe JML $CE:98C4 + NOPs. The target
  code repeats the LDA/STA, then LDA #$7C ; JSL $84:FE2A ; JML $C3:D40B. Looks like a trampoline
  that adds a call with A=$7C (music or sound id, inference).
- New code in D0:5E1A (reached by a changed jump at C4:A194) loops with counter $36 and calls
  $88:C637, $80:F5B5, and $84:FE2A with A=$79. Purpose unknown.
- New code at FF:FE30-FEA6 (bank FF, empty 0xFF in the original) sets values and calls $84:FE2A with
  A=$11, $12, $13 plus $88:C7B6 with PEA arguments. Looks like ending or text sequences
  (text-like byte runs at FF:FE00-FE2F). The LDA $3BAE reads there are overwritten at once.
- The upper 4 MB of Deluxe contains a copy of the original code (e.g. the same STZ $3BB0 at
  0x4086B4 as at 0x86B4), consistent with the 0x40FFC0 header copy. So the 8 MB ROM is not simply
  4 MB original plus 4 MB of new data.
- Refined view of the AND-mask change: callers of C5:C72B pass small constants like $F8/$F9, and
  Deluxe's new code calls $84:FE2A with A=$7C, $79, $11 to $13. The readme lists new songs and
  Mortal Kombat Trilogy sound effects. Inference: the routine at C5:C72B plays sounds or music and
  the mask widening allows sound IDs above 255. Not verified. It is not fighter logic.

### Conclusion
- The Deluxe diff mixes many features (music, endings, menus, stages). Reading Sheeva's selection
  path from the diff alone is slow. Better route: use the emulator to watch RAM while selecting
  characters, and test the hidden-chars option and L+R+Start claim directly.

## TCRF text from the user, and the first RAM verification (dispatch 2)
User pasted text said to come from The Cutting Room Floor UMK3 (SNES). Provenance not verified (the
file link it gave is a Google search redirect, and some parts contradict the Deluxe readme).
Parts I am treating as claims to test:
- Sheeva was cut but leftover data remains. Access in the unpatched game: hold L+R and press Start
  "on the title screen" for 8 vs 8 Tournament mode, then Up+Start (random all 8) or A+Start
  (random current slot); random can hit an "E" icon that is Sheeva's remaining slot.
  A Haiku agent tried L+R+Start at the title, start menu, play-mode menu and grid on both ROMs and
  saw nothing special. It did not test random select inside 8 PLAYER TOURNAMENT. Still open.
- Chameleon via Pro Action Replay: 7E36D019 and 7E52C819 (uses Rain's lifebar name, Scorpion's sprite).
- Unused stage ids at $7E3A7E: 07 Bell Tower, 08 unknown, 09 Pit III (MK3), 0A Hidden Portal.
- Doubtful parts of the pasted text (conflict with the readme or my own observation, not used):
  "Sheeva is on the Deluxe grid", "Shang Tsung morphs into Sheeva with F,D,F,LK".

VERIFIED by emulator (original ROM, roster grid, reading WRAM while moving the cursor):
- WRAM word $52C8 holds the P1 cursor fighter ID and $36D0 mirrors it. Seen values:
  top-left cell 0x18 (Rain), then 0x13 (Reptile), 0x05, 0x02, 0x14, 0x0F, 0x07, 0x0A, 0x06.
  These match the name table order (0 Kano ... 24 Rain).
- This CORRECTS my earlier guess that $52C8 held state codes. The earlier writes of $0004 and $0010
  to $52C8,x are fighter IDs (Sub-Zero 4, Jade 16). The routine at C2:9D40 uses the ID as X:
  ID < 15 reads $88:9E19,X; otherwise reads $88:9D23,X or $88:9D3F,X. The 59-plus callers of
  C5:C72B pass sound-like values, so per-fighter table[ID] then feeds that routine (probably a
  per-fighter sound or announcer value; inference).
- PAR code 7E52C819 sets the P1 fighter ID to 0x19 (25). ID 25 is beyond the 25-entry tables
  (IDs 0 to 24), so Chameleon likely is a hard-coded alias; the aliases at IDs 21 and 22 are similar.
- Harness now has poke_wram() and run_poking() to emulate Pro Action Replay writes.
- First poke experiment: writing ID 11 into $52C8/$36D0 every frame while pressing START on the grid
  did not leave the grid (START does not confirm a fighter there). Needs the confirm button.

## Fight navigation script (agent-written, NOT yet verified by me)
- tools/umk3_nav.py, written by a Haiku agent that was still running when committed.
- Its docstring claims: boot ~1500 frames; START three times (200 frames apart) reaches the roster grid;
  on the grid, A (not START) confirms P1; then CHOOSE YOUR DESTINY (tower), A starts the NOVICE climb,
  START after about 1000 frames leads to the fight. Grid valid cells: row 0 cols 0-6; row 1 cols 0-6
  except col 3 (logo cell skipped); rows 2 and 3 cols 1-5.
- Run it and compare against screenshots before relying on it.
- This explains why my earlier test (pressing START on the grid with ID 11 poked) never left the grid:
  A confirms, not START.

## Batman Returns gameplay navigation (agent-written, spot-checked by me)
- tools/br_gameplay.py: boot_to_gameplay(core) then perform(core, action).
- Sequence (3808 frames): 1000 idle, START 4f, 200 idle, START 4f, 2600 idle -> Stage 1 with Batman visible.
  I ran it myself and viewed the frame: Batman in Stage 1 with HUD ("BATMAN x3", score).
- Agent-verified button map (by pixel diff and screenshots): RIGHT/LEFT walk, DOWN crouch, B jump,
  Y punch, A batarang. X has no effect. L/R unidentified, UP moves up a few pixels.
  Agent reported two separate processes gave pixel-identical frames for boot plus walk_right.
- Next for art: find the OAM shadow buffer in WRAM and the Batman tiles in VRAM, get the palette.
- Note: a reskin (palette swap of an existing fighter) needs only Batman's colours, not his sprites.

## Reskin v1 (what was actually produced)
- tools/make_batman_reskin.py: renames fighter ID 24 pointer to "-BATMAN" (string at 0x3FF90) and recolours
  Rain's sprite palette (4 words at 0x456E8, 10 words at 0x3EAFB3) from purple to dark blue-grey.
  37 bytes differ from the original (name, pointer, 14 palette words, checksum).
- Verified in snes9x via the harness: boots, roster loads, a fight loads, Rain is dark blue-grey in the fight
  and the roster standee. NOT fixed: the HUD still says RAIN (it is not read from the ASCII name table),
  the roster portrait is still purple, and sprites, moves and hit data are Rain's.
- Not done: real Batman sprites, move list, new roster slot.
- Batman picture from Batman Returns stage 1 saved at deliverables/batman_from_batman_returns_stage1.png.
- The ROM file is in deliverables/ but is gitignored (commercial dump derivative); only the script is committed.

# FINAL STATE (work stopped at the user's request)
Produced: a Rain-to-Batman colour reskin (tools/make_batman_reskin.py), 37 bytes changed. In-fight sprite and
roster standee are dark blue-grey. HUD name still reads RAIN. Portrait still purple. Moves and sprites are Rain's.
Tested only in snes9x through the harness: boots, roster loads, a fight loads. Not tested on hardware.
The ROM upload to the user failed once (server error 520); the ROM is regenerated by the script.
Not produced: real Batman sprites, move list, new roster slot.
Verified this session: fighter ID RAM ($52C8, $36D0), Rain palette locations, free space at 0x3FF8E in bank C3,
Batman Returns gameplay navigation, name table and lookup code.
Known open leads: roster portrait palette (palette 13, ROM 0x3F7C5E), HUD name graphic location, ID 11 as a spare
slot (unverified), Deluxe's hidden-fighter mechanism (HIDDEN CHARS option text replaced ENABLE MOTARO).
Agent results that were wrong and corrected are listed above. Two agents (HIDDEN CHARS option test and the
fight-nav rerun) never reported back.

## Failure note (added at the user's request)
The first crucial step, viewing Batman's actual sprite art, was skipped for hours. See Lessons_Learned.md.
It has now been done: tools/dump_br_sprites.py renders the tile pieces from Batman Returns VRAM using his
sprite palette (WRAM 0x3300). The output shows the cowl and chest with the yellow emblem, torso with the
orange belt, arm, leg and cape pieces, and effect graphics (batarang, explosion, smoke). These are the pieces
for the idle pose. Full frames still need the sprite attribute table.

## UMK3 fighter art is stored compressed (verified test)
- Method: ran UMK3 to a Rain vs Reptile fight (tools/umk3_nav.py to_fight(0,0)), dumped VRAM, and searched
  the 4 MB ROM for each non-trivial 4bpp tile (>= 8 distinct byte values).
- Result: only 19 of 1,069 non-trivial VRAM tiles occur verbatim in the ROM (VRAM 4 KB blocks 3, 12, 14, 15,
  likely patterned or UI tiles). Half-tile chunks match 43/1067 (first 16 bytes) and 27/848 (last 16 bytes);
  8-byte chunks 78/988. So fighter sprite data is not stored as plain 4bpp tiles in the ROM. It is compressed
  (or reordered). This is the real blocker for a true Batman fighter.
- Consequence: converting Batman Returns frames into UMK3 needs UMK3's decompression algorithm (to write a
  matching compressor, or a loader hook that uploads raw tiles). Neither is known yet.
- Next: find the decompressed copy of a fighter's tiles in work RAM (search WRAM for the same VRAM tiles),
  locate the matching compressed stream in ROM via the per-fighter pointer tables, and test candidate
  LZ/RLE schemes against the known output. Record each tested scheme and result here.
- External claim (unverified, from the user): a 900x1650 Batman Returns sheet cut into about 100 poses exists
  in another sandbox. If uploaded here it would replace the OAM assembly step, but the compression blocker above remains.

## Paint test result (the gate Grok proposed; run and checked by me)
- Pulled commit 15a0702 (art/batman_poses.tar.gz with 100 poses, NEXT.md, tools/batman_vram_test.py).
  Not yet unpacked or viewed by me beyond the file list.
- tools/batman_vram_test.py runs, but its sprite-table detection fails: its top candidates ($9A18 etc.) have 1 left-side tile,
  and $C200 and $C416 hold noise. Its paint_*.png files therefore paint the wrong tiles and prove nothing either way.
- My own block-fill test (tools/vram_blockfill_test.py) answers the question directly. Filling VRAM 0x4000-0x47FF
  and 0xA000-0xA7FF with solid colour deletes pieces of Rain's body in the fight frame while Reptile is unaffected.
  So Rain's live sprite tiles are plain 4bpp in VRAM and writable; no compressor is needed to change them.
  Rain's tiles are spread over many 2 KB blocks between 0x3800 and 0xFFFF (many blocks change 13-37% of his box).
- Not solved: which sprite pieces go where. Writing Batman pixels into those tiles only works if the pieces are
  placed to form his pose. Standard 544-byte OAM shadow was not found in WRAM. WRAM contains repeating 68-byte
  records (offsets 0x2281, 0x22C5, 0x2307 and 0xC45E, 0xC4A2, 0xC4E6, and 0x16B1F, 0x16B63, 0x16BA7) with entries
  in Rain's screen box; they may be per-frame sprite piece lists. Not decoded yet.
- Next: decode one 68-byte record (x, y, tile, attributes), verify by painting only the tiles it names, then map
  Batman pose pixels onto that piece layout or rewrite the entries to a grid that matches the pose.

# ISSUES (2026-10-14, Grok session — handoff)

The user stopped this session and is handing the job to another AI. Nothing below is a ROM patch.

## What the user asked for
- Port Batman Returns sprites, animations, moves, and damage onto a UMK3 fighter.
- Then, only the art import, until that worked.
- Then delete five Rain idle frames from the game so the idle list matches Batman's four frames.

## What was not done
- No Batman art was written into the ROM. Overlays were PNG composites on screenshots.
- No animation script, move, or damage data was changed.
- The ROM on disk was not modified in this session.

## The false "playback list"
- "Rain has 9 idle frames" was a count of files on
  https://www.mortalkombatwarehouse.com/umk3/rain/sprites/
  named stance/01.png through stance/09.png. Two more files there, t01.png and t02.png, are the turn.
- Batman idle was counted by looking at the top row of the Spriters Resource sheet: 4 standing frames.
- A numbered list (01, 02, 03, 04, 05, 06, 07, 08, 09, then "go back to 01") was typed into the chat.
  It was not read from the ROM. There is no address for entries 5–9.
- The user said to delete entries 5–9 from that list, then from the ROM. Only local copies of
  05.png–09.png were deleted. The ROM still plays Rain's original idle.

## Why the stance script was not found
- Do not treat the chat list as a ROM address. It is not one.
- Fighter tiles are compressed in the ROM. A earlier test found 19 of 1,069 on-screen tiles matching
  the ROM verbatim. In VRAM, during a Rain fight, painting 0x5000 and 0xA000 deletes parts of Rain,
  so the live tiles are plain 4bpp. That does not locate the script that chooses the next pose.
- Work RAM was sampled while Rain's chest pixels changed. Bytes that moved with the pose were
  decompressed tiles and sprite coordinates. No 16-bit pointer advanced only on those pose changes.
- Per-fighter word tables already noted in this file (0x0986C, 0x0D1F7, 0x1C5A6, 0x2A242, 0x2A5A6,
  0x2C071, 0x2EC7B) were read. Rain is ID 24 and shares several of those entries with other ninjas.
  None of the dumped records was verified as a 9-frame stance script.
- The 3DO source (MKANI.H) uses script commands 0–15 (ANI_END, ANI_JUMP, …) and image offsets.
  That is a different port. It was not matched to this SNES file.

## Screenshots that are not the game
These were uploaded to deliverables/ on this branch. They are pictures, not ROM state.
- batman_pasted.png — a Batman stance PNG scaled and pasted onto a fight screenshot.
- rain_original.png — the same moment with Rain.
- overlay_50.png — those two blended at 50%.
- rain_stance_4.png — four of the nine downloaded stance pictures.
- rain_from_tiles.png and the one_sprite / batman_overlay images are earlier experiments.
  The tile-replace attempts painted the wrong cells. The user rejected them.

## DEBUGGER BUILT (the missing tool)
- Built a patched snes9x libretro core with exec breakpoints, ROM/RAM read watches, RAM write watches and a ring log
  (tools/snes9x_dbg.patch, tools/build_dbg_core.sh, wrapper tools/dbg_core.py). Source came from the Ubuntu
  libretro-snes9x source package via apt (GitHub is blocked, apt works). Core installed at /opt/snes9x_dbg/ (not in git).
- Verified: the reset vector target ($C0:83D7) exec hook fires at boot; a write watch on $7E52C8 shows the code at
  $88:9813 writes the P1 fighter ID, with values 19, 5, 17 as the cursor moves to Reptile, Stryker, Mileena.
- Not logged by the hooks: opcode fetches, DMA transfers, SPC/APU. Addresses are canonical (ROM C0-FF, RAM 7E/7F).
- Next (critical path): find the decompressed fighter tiles in WRAM, write-watch that buffer to find the decompression
  routine and its ROM source pointer, then decode the 68-byte sprite piece records the same way.

## Grok session 2026-10-14 (second pass) — still no ROM edit
Looked up existing MK SNES tools instead of guessing the pointer. The public editor
https://github.com/darkmoon2321/mk-character-edit is Mortal Kombat 1 (LoROM), not UMK3.
Its animation scripts are 16-bit words: a frame index, or a command in 0xFFF6–0xFFFE, ended by 0x0000 or 0xFFFF.
The character header is a word at file 0x1B9A plus bank 0xAE. That header is not in this ROM.

A scan of the UMK3 ROM for the same shape (7–14 small words, ended by 0x0000, previous word also 0x0000)
found 39 hits. The only sequential ones are C0:9C84 (frame ids 5 through 13) and C0:AF90 (ids 9 through 17).
They sit inside other data, not in a verified animation table, and were not patched.

A fresh idle trace (Rain vs Reptile, dark pixels of the body, not the portal) still shows no script pointer:
- Pose changes repeat as `##.#.##.##.#....` about every 16 frames.
- No 16-bit RAM word steps by 2 or 4 on those changes and stays still otherwise.
- Bytes that change only on those frames: $53BA (the Y bob, values around 0x4E–0x55) and $A14C (0 or 1).
- Words in the player record that move are positions, mirrored: $52F8/$53B0, $52FA/$53B2, $5300/$53B8, $5302/$53BA.

No frames were deleted from the ROM in this pass. The ROM checksum was not touched.


## Claude session 2026-10-15: debugger findings (everything below was observed by running the patched core)
Setup: original UMK3 (USA), Rain (roster cell 0,0) vs Reptile fight, reached with tools/umk3_nav.py to_fight(0,0).
Tools added or changed: tools/dbg_core.py (exec/read/write watches, poke-on-exec), tools/trace_dma.py (DMA transfer decoder),
tools/snes9x_dbg.patch (regenerated; includes both fixes below), tools/build_dbg_core.sh (not run end to end).

### Two bugs in my own debugger, fixed
1. Register mirrors: the hook only folded RAM mirrors, so PPU/DMA register accesses through a mirrored bank (the game's data
   bank is $88, so STA $2118 is really $88:2118) never matched a watch on $00:2118. That is why my first DMA traces showed
   zero events. Fixed: addresses with offset $2000-$7FFF in banks $00-$3F and $80-$BF now fold to bank 0.
2. My first traces also stopped logging before the fight began (300 frames after START is still the VS screen). Trace after
   to_fight() returns.

### Verified facts about how UMK3 draws fighters
- Tiles reach video RAM by general DMA every frame (243 VRAM DMAs in 180 fight frames), not by CPU writes to $2118/$2119
  (zero such writes). The routine that starts them is at $88:B959 (main), with $88:B983, $88:BABB, $84:9DB3 and $84:9DCB for
  smaller uploads.
- The sources are work-RAM staging buffers (DMA source -> VRAM byte address): $7E:84A8 -> 0xC400, $7E:86A8 -> 0xC600,
  $7E:88A8 -> 0xC800, $7E:A0A8 -> 0xE000, $7E:A6A8 -> 0xE600, $7E:ACA8 -> 0xEC00. Sizes vary per frame (192 to 1376 bytes)
  with the pose. Two small uploads of 144 bytes come straight from ROM ($E3:FDBE, $E3:FE4E), so those are stored raw.
- The sprite attribute table (OAM) is sent every frame by the routine at $88:BA1D from $7E:C4AA, 544 bytes: standard layout,
  128 entries of (x, y, tile, attr) then a 32-byte high table. THIS CORRECTS my earlier claim that no standard OAM shadow
  was found in WRAM. The earlier scans assumed a pattern of many off-screen entries and a base near $C200 and missed it.
- In that frame Rain is OAM entries 15-24: five 16x16 sprites (tiles 48, 50, 52, 54, 56) and five 8x8 sprites (tiles 58-62),
  attr 0x30 = name table 0, palette 0. Reptile is entries 1-14 (name table 1, palette 1, h-flipped). Entries 25-36 are shadows or HUD
  (palette 7). Sprite sizes in use: small 8x8, large 16x16.
- Painting Rain's tiles solid at VRAM base 0xC000 (tile n at 0xC000 + n*32) deletes pieces of Rain in the frame, while painting
  at 0x4000 or 0x8000 leaves him unchanged (image: deliverables/p1_paint_base_compare.png, frames left to right: base 0x0000,
  0x4000, 0x8000, 0xC000). So name table 0 sits at VRAM byte 0xC000, which matches the DMA destinations 0xC400/0xC600/0xC800.
  Inference from the addresses: tile 48 is at VRAM 0xC600, so $7E:86A8 holds Rain's tile 48 onward for the current pose.
- The WRAM data port $2180 is written heavily during loading (about 148k bytes) by loops at $83:87AC-87BA and $83:84EC. Only 53 of
  1069 VRAM tiles appear in that byte stream, so it is not the main tile path. It is probably the decompression or copy loop for
  other data. Not verified.

### What this changes
- The earlier "68-byte records" in Current_Work.md may not be needed: the real piece layout is the OAM table at $7E:C4AA.
- No compressor is needed to show Batman. Two levers exist: (a) write Batman tiles into the staging buffers (or VRAM after the
  DMA), (b) rewrite OAM entries 15-24 plus spare entries to a grid of Batman pieces. Both can be done from the debugger core
  with poke_on_exec at the OAM DMA routine ($88:BA1D) and the tile DMA routine ($88:B959).
- For a real ROM patch the same two hooks become 65816 code in free ROM space, replacing those uploads when the fighter id is Batman.

### Not done
- Batman art has not been drawn in a fight yet. The poke-on-exec feature is built and compiles but has not been run on a frame.
- The OAM entries that belong to P1 were found in one idle frame; they change with the pose and with movement.
- Nothing in the game ROM changed in this session. The recolor reskin (tools/make_batman_reskin.py) remains the only ROM edit.

## CORRECTION: fighter tiles are NOT compressed (verified with the debugger, 2026-10-15)
My earlier conclusion ("fighter sprite art is compressed in ROM", based on 19 of 1,069 VRAM tiles matching the ROM) was wrong.
That test counted every VRAM tile (backgrounds, UI and sprites together) against the whole ROM, so it proved little about fighters.
Direct evidence:
- A write watch on the tile staging buffers ($7E:84A8-$7E:8EA7 and $7E:A0A8-$7E:AEA7) shows that during a fight they are
  written by one unrolled copy routine at $83:83ED-$83:8445: `LDA $0000,Y / STA $7E:80A8,X` repeated, reading 16-bit words
  from DB:Y. DB (source bank) was $D6, $D7 or $D8 and Y ranged $45C0-$73C0 in the sampled frames, i.e. ROM file offsets
  0x1645C0-0x1873C0 (file = ((bank - 0xC0) << 16) | Y).
- For 146 of 146 copies sampled over 40 fight frames, the 32 bytes in the staging buffer are byte-for-byte identical to the
  32 bytes at the ROM source. Zero differed. So the pose tiles are stored as plain 4bpp in ROM, and no decompressor is
  involved for them. They are then DMA'd to VRAM unchanged ($88:B959).
- Drawing the source regions as a plain grid of consecutive tiles looks like noise, which is expected: the engine copies tile
  blocks from scattered addresses and the sprite table decides how pieces are arranged. The frame is rebuilt from (the ROM tile
  sources per pose) plus (the OAM entries at $7E:C4AA), not from a sheet in ROM order.
- What may still be compressed or packed is something else (backgrounds, other data): not tested.

### What this means
- No decompression step is needed to read or replace fighter art. Replacing a pose means writing new 4bpp tiles to the ROM source
  address that the copy routine reads, and changing the sprite table pieces that place them.
- What is still unknown: the list that says, for each animation frame, which ROM tile blocks to copy and which OAM pieces to emit
  (the caller of $83:83ED and its data table), and where Rain's idle frames sit in it. The debugger can find it: watch reads of the
  ROM bytes at the $D6-$D8 sources and see which routine fetched those pointers.
- Superseded statement: "UMK3 fighter art is stored compressed" in the earlier section "UMK3 fighter art is stored compressed".


# CURRENT PLAN (written 2026-10-15; supersedes the earlier "REVIEW AND PLAN" section and NEXT.md)
Status: this is a plan only. No step below has been run. Nothing in the game ROM changes except the earlier Rain recolor.

## Goal
Batman as a playable fighter in UMK3 (SNES): his art replaces a fighter's sprites in a real fight, moves stay the donor's.
No move list screen exists in the game, so that is out of scope for now (decided with the user).

## What is already known (verified, see sections above)
- Debugger: patched snes9x core with exec, read and write watches and poke-on-exec (tools/dbg_core.py, tools/snes9x_dbg.patch).
- Fighter tiles are raw 4bpp in ROM banks $D6-$D8 (file = ((bank - 0xC0) << 16) | addr). Not compressed. The earlier "compressed" claim was wrong.
- Per frame the game copies 32-byte tile blocks with the routine at $83:83ED into staging buffers ($7E:84A8-$7E:ACA8),
  DMAs them to VRAM ($88:B959), builds the sprite table at $7E:C4AA (544 bytes) and sends it with $88:BA1D.
- Rain's idle pose is OAM entries 15-24: five 16x16 pieces (tiles 48, 50, 52, 54, 56) and five 8x8 pieces (tiles 58-62).
  Sprite name table 0 is at VRAM byte 0xC000.
- Fighter id is in WRAM $52C8 (P1). Roster ids 0-24 follow the name table at 0x3E544.
- Batman art: tile pieces dumped from Batman Returns VRAM (tools/dump_br_sprites.py) and 100 cut poses in art/batman_poses.tar.gz.
- Only ROM edit so far: tools/make_batman_reskin.py (palette recolor of Rain, name table pointer). Sprites, HUD name and portrait unchanged.

## Not known yet
- Which routine builds the sprite table and where its per-pose piece records live in ROM (the frame record format and address).
- The frame-number-to-record table, and the animation script reader (what decides the next frame).
- Whether Rain's tiles and records are shared with other ninja fighters (Scorpion, Sub-Zero, Reptile, Smoke, Ermac, Noob).
- How the fighter id selects its animation/tile bank (which of the 25-entry tables, if any).
- Free ROM space for new tiles. The original is 4 MB and full; Deluxe is 8 MB with an ExHiROM header.
- The sibling-game hint: the MK1 SNES editor (darkmoon2321/mk-character-edit) documents a frame format of piece counts plus x, y and tile references.
  Two blind ROM searches for Rain's piece deltas found nothing (a third variant was cancelled). Unconfirmed that UMK3 shares that format.

## Phases (each ends with something visible; do not start the next phase until the check passes)
A. Find the frame data (debugger, mostly scripting time).
   A1 Write-watch $7E:C4AA-$7E:C6C9 to find the routine that builds the sprite table.
   A2 Read-watch the ROM while that routine runs for a few idle frames; print the ROM addresses and bytes it reads.
   A3 CHECK: decode one record and reproduce Rain's ten OAM entries exactly. Record the format in this file.
   A4 Find the frame-number-to-record table, and the per-fighter table that selects it.
B. Record Rain's poses automatically: scripted fight covering idle, walk, jump, crouch, block, punches, kicks, hit, fall.
   Log per frame: frame id, record address, tile sources, rendered image. Also record at least one other ninja to see what is shared.
   CHECK: a contact sheet of every recorded pose.
C. Decision (needs the user only if the data says shared): Rain's data shared with other ninjas?
   Recommended: give Rain private copies in new ROM space (expand to 8 MB) and repoint only Rain's records. Alternative: in-place overwrite if sharing is absent.
D. Art tool (tools/, not yet written): scale a Batman pose to Rain's size, slice onto Rain's piece grid, quantize to a 16-colour palette,
   emit 4bpp tiles. Mapping table from Rain frame types to Batman poses (idle to stance, punch to punch, and so on).
   CHECK: a rendered mock of each mapped frame before touching the ROM.
E. Patch builder and emulator check: write tiles and pointers, fix the checksum, boot it, screenshot idle, walk, jump, punch in a real fight.
   MILESTONE: Batman visibly idling, walking and punching in a UMK3 fight.
F. Cosmetics: health-bar name (drawing code not found; not read from the ASCII name table) and roster portrait (palette 13 at ROM 0x3F7C5E is shared).

## Rules for this plan
- Do the decisive check myself before delegating; delegate only side work. Show an image for each phase. Verify every sub-agent claim.
- Superseded: the 68-byte-record idea, the 544-byte OAM "not found" claim, and "fighter art is compressed". See the correction sections above.

## Effort (honest)
First visible Batman (idle, walk, main attacks): about a day of focused work. Polished full pose set: longer, since each frame needs a matching Batman pose.

---

# STATUS 2026-10-18 (latest; supersedes CURRENT PLAN where they differ)

Verified this session (sources: UMK3 (USA) ROM from the claude branch, Batman Returns for later phases):
- Debug core built and loads (`tools/build_dbg_core.sh`, fixed so the patch path resolves; see commit 48d5539).
- The tile DMA path (83:83ED -> 88:B959) is confirmed. $88:BA1D is only a DMA start stub, NOT the sprite-table builder.
- Sprite table writers during a fight: $80:819D, $80:822A, $80:825F (write-watch on $7E:C4AA).
- Piece record format for Rain (19 of 19 OAM entries reproduced in one frame):
  X low byte = rec+2 + $3E, Y high byte = rec+4 + $A2, tile word = rec+6 | $18, records at $7E:56C0 and $7E:57xx.
  See ROUTINES_UMK3.md and tools/analysis/check_oam_record_formula.py.
- Other sprite groups in the same frame use other constant base pairs (separate objects). The $7E:73xx/74xx/7Bxx group
  fits the opponent's on-screen position; not yet proven.

Caveats:
- The debugger's watch_read reports $7E:170A as 0x00 at the Y add, but poking $170A to $A2 gives the identical result.
  Trust poke tests over logged read values for this address. (tools/analysis/poke_test_y_base.py)
- The earlier VRAM paint gate (tools/batman_vram_test.py) did NOT show Rain turning white in any of the four bases.
  The live tile store is still unconfirmed.

Not started:
- A4: how the game chooses which record set to draw each animation frame.
- B: record Rain's sprites across many poses.
- C-F: design choices, art tool, patch builder, emulator milestone, cosmetics (see CURRENT PLAN).

Repo notes:
- ROM zips are committed on the claude/keen-clarke-i6br28 branch (public repo). Recommend removing them.
  Not removed yet; needs owner confirmation because it rewrites branch history.
- Analysis scripts assume the ROM path is passed in and the scratchpad is used for dumps. No ROM-derived data is in the repo.

## Fit test (2026-10-18, latest)
- Mock only (paste on a fight frame, not a ROM edit): Batman idle (f000_62x89, from art/batman_poses.tar.gz) scaled to
  the bounding box of Rain's first 19 OAM entries (x 41-94, y 103-215). Batman covers Rain's silhouette at the right
  height and width. Rain's upper-left arm/hood piece shows past the overlay, so the piece set is not complete.
- Earlier overlay attempts used the wrong pieces (OAM 15-24 are not Rain). Those results are discarded.
- Not tested: piece-by-piece fit onto the sprite grid, tile splits, palette, and the in-game draw.
- Verdict: silhouette scale is plausible. Piece fit is the next gate before any ROM edit.

## Piece-level fit (2026-10-18, latest)
- Rain idle (19 OAM entries, sizes from the high table): 8 pieces 16x16, 11 pieces 8x8. Total 43 8x8 tiles.
  Bounding box 45x104 px. Table dump saved in the scratchpad (not in repo).
- Batman idle scaled to the same 45x104 box: 42 8x8 cells contain pixels.
- Tile count fits (42 needed, 43 available) at the count level only. Not tested: cell alignment with Rain's
  pieces (they are not on one grid) and the palette (4bpp, 16 colors per sprite palette; Batman's art must be
  quantized to Rain's palette, which has not been checked).
- Verdict: tile budget is plausible. Alignment and palette are the next gates.

## Palette test (2026-10-18, latest)
- Rain's sprite palette taken from ROM (0x456E8 x4 and 0x3EAFB3 x10, the same words the reskin script uses).
  NOT checked against live CGRAM: the harness does not expose palette memory.
- Batman idle quantized to those 14 colors (nearest RGB): 12 of 14 entries used. Silhouette, belt and cape are
  readable. The dark-blue suit comes out purple-black. Image: scratchpad fit/batman_pal_test.png.
- Verdict: palette loss is visible but the figure is recognizable. The suit colour is the main gap. A better
  palette (more blue) would need more of the 16 colors, which depends on the live palette.
- Not tested: live CGRAM values, dithering, and in-game colour.

## Alignment test (2026-10-18, latest): FAILED for the lower body
- Batman idle (scaled to Rain's 45x104 box) cut into Rain's 19 piece rectangles (sizes from the high table).
- 82% of Batman's opaque pixels fall inside a piece. 18% (about 315 px) fall outside and would be lost.
- Upper body (16x16 pieces) fits. The legs and cape fall in the 8x8 pieces, which are too narrow.
- Piece area is only 52% filled by Batman. The 42-vs-43 tile count was misleading, because it counted cells
  on a uniform grid, not the real piece layout.
- Image: scratchpad fit/align_test.png.
- Verdict: a direct swap of Rain's piece layout cannot show Batman's legs or cape. Options: (a) new piece records
  in ROM with more 8x8 pieces, (b) a different Batman pose that fits, (c) a smaller Batman scale that loses detail.

## Option 2: other Batman poses vs Rain's layout (2026-10-18, latest)
- Scored all 100 poses in art/batman_poses.tar.gz, each scaled to the 45x104 box and cut to Rain's 19 piece rectangles.
- Best: f018_49x82, 90.7% of opaque pixels inside pieces (idle was 82%). Next: f063 (88.7%), f073 and f054 (88.7%).
- Still about 9% of pixels (about 140 px in the best pose) fall outside the pieces. Not a clean fit.
- Pose choice helps but does not solve the leg/cape overflow. Option 1 (more pieces) or option 3 (smaller scale) is still needed.

## Session status, 2026-10-18 (end of session, pushed)

Accomplished and pushed to main:
- Debugger core builds and loads; build script fixed (commit 48d5539).
- Sprite-table writers located: bank $80 at $819D, $822A, $825F (write-watch on $7E:C4AA).
- Piece record X formula holds for Rain's first eight pieces. Y term is a per-piece calculation (table difference),
  not a constant; the earlier "Y base $A2" claim was withdrawn.
- Y position formula: +/-T[idx] + per-object base, verified on four stores.
- Tile copy: fighter tiles are read raw from ROM banks $D6-$D8 each frame. All 848 copied words in a 60-frame
  capture matched the ROM.
- VRAM tile slot = $C000 + tile*32. Idle range $C600-$C7E0 (tiles $30-$3E).
- Step 1 coverage: 19 slots mapped in total, only 7 in the idle range. Idle tiles are probably not recopied in a still fight.
- Layout tests on Batman's idle (f000) and best pose (f018):
  - Tile count: 42 needed vs 43 available (rough, misleading).
  - Palette (Rain's ROM palette): passes with visible suit color loss.
  - Alignment: lower body falls outside Rain's pieces. Idle covers 82%, best pose f018 covers 91%.

Not done:
- Full idle tile map, pose-cycle capture (rejected by user before running).
- Batman tile encoding (4bpp), patch file, in-game test.
- Animation-frame selection (A4), full pose set, cosmetics.

Blockers and open questions:
- Shared VRAM slots receive different ROM tiles at different poses; in-place edits can affect other poses.
- Piece-fit gap (about 9-18% of Batman's pixels) needs a decision: add pieces, accept clipping, or scale down.
- ROM zips are still on the public claude/keen-clarke-i6br28 branch. Removal needs your approval (rewrites history).

# STATUS 2026-10-19 — Batman is on screen in a fight

The patcher is tools/make_batman_fighter.py. It reads Ultimate Mortal Kombat 3 (USA).zip
from this repo and writes a 4 MB ROM. The ROM is not committed. Rain's move code and
hitboxes are not modified. The Deluxe AND-mask is not touched.

## Addresses read this session (live Rain vs Reptile, tools/umk3_nav.py to_fight(0, 0))

- Fighter id: WRAM $7E:52C8. Value 24 on roster cell (0,0) and in the fight.
- OAM low table: WRAM $7E:C4AA. 128 entries, 4 bytes each (x, y, tile, attr).
- OAM high table: WRAM $7E:C6AA. Two bits per sprite: bit 0 is x high, bit 1 is size
  (0 = 8x8, 1 = 16x16). Rain's body uses both sizes. In one idle frame, 81 unused
  entries were Y=$E8. There were no Y=$F0 fillers on the original ROM.
- Rain's pieces are whichever on-screen sprites have attr & $3F == $30 (page 0,
  palette 0, priority 3). Flips sit in the high bits ($30/$70/$B0/$F0). One idle
  frame had 16 of them, starting at slot 18, not a fixed 0-18 range.
- OAM DMA: file 0x8BA19, SNES $88:BA19. Bytes E2 20 A9 01 8D 0B 42
  (sep #$20 / lda #$01 / sta $420B). This is the hooked instruction. The next
  instruction, C2 20 6B (rep #$20 / rtl), is left as-is.
- Builder tail: file 0x806E, SNES $80:806E. Bytes A5 0C 8D 30 1A 6B
  (lda $0C / sta $1A30 / rtl). Checked, not patched. Writing the sprite list
  there is too early. The game rebuilds OAM after that return, and the PPU
  never shows those edits. The DMA site is late enough.
- Buttons, stable while held: WRAM $7E:1701. Right = bit 0 (value 1), Y = bit 6
  (value 64). The hook tests word $7E:1700 with bit #$0300 (left/right) and
  bit #$C0C0 (A/X/Y/B).
- Fight latch: WRAM $7E:03FE. Stays 0 on the roster (Rain's id is already 24
  there, but no attr-$30 sprites). Set to 1 only when a fight has at least 8.
- Sprite name table 0 is VRAM byte $C000 (tile n at $C000 + n*32). Name table 1
  is VRAM byte $E000. The pose is uploaded at page-1 tile $80 (VRAM byte $F000,
  word $7800), 8 rows of 256 bytes. The first two rows matched the ROM bytes.
- VRAM $D400 (page-0 tile $A0) is zeros and is a live background map. Writing
  tiles there destroys the graveyard.
- CGRAM sprite palette 0 ($2121 = 128) can be DMA'd without blanking the screen
  if $4300-$4306 are saved and restored first. The colours do not stick. The
  game reloads that palette after the OAM DMA, so the hook keeps the pose on
  index 15, which is bright in the reloaded palette.

The ROM frame table behind $7E:56C0 was not patched. The hook runs after the
game has already turned those records into OAM, then replaces the picture.

## What the hook does

JSL at file 0x8BA19 to $FF:DC6E (file 0x3FDC6E, previously FF padding).
If id is 24 and at least 8 Rain sprites are on screen: hide those sprites
(Y=$E0) and write 16 sprites of 16x16. An 8x8 grid does not fit. The OAM DMA
runs more than once a frame, the game keeps about 70 of the 128 slots for the
opponent, HUD and effects, and a second pass was stacking copies of the head
until the middle of the body was gone. 16 sprites of 16x16 cover the same
64x64 and survive that. Old Batman slots are reused so the copies do not pile
up. Size bit forced to 16x16. Origin (48, 112).

Tiles are the linear 8x8 pose in ROM. Eight DMAs of 256 bytes place each row
on a 16-wide name-table row starting at page-1 tile $80 (VRAM byte $F000,
word $7800). A byte compare of the first two rows against VRAM matched.

The 16-color ramp is not what the screen uses. A CGRAM DMA of those colors
does not stick: the game reloads sprite palette 0 after this hook. Index 15
is a bright white in that palette, so every opaque pixel is index 15. The
figure is a solid silhouette. A multi-index quantization comes back as Rain's
colours and breaks into stripes. Checked by drawing the same pose as one
index and as a full ramp.

Art, from art/batman_poses.tar.gz, scaled with nearest-neighbor into 64x64,
not cropped:
- idle: frames/f000_62x89.png
- walk, while LEFT or RIGHT is held: frames/f006_45x90.png
- attack, while A, B, X or Y is held: frames/f013_81x91.png

## Still Rain

- HUD name. The fight screenshots still say RAIN.
- Roster portrait. Not edited.
- Specials, hitboxes, and move code. Not edited.

## Screenshots opened this session

- deliverables/batman_idle.png — white silhouette, cowl, ears, cape, feet. Not Rain's hood.
- deliverables/batman_walk.png — stride, cape still visible.
- deliverables/batman_attack.png — punching arm out, cape still visible.

