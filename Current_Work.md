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
