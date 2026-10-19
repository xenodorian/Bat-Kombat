# UMK3 (USA) routines: verified from bytes and debugger logs

Source: UMK3 (USA) ROM, HiROM file offset = ((bank - 0xC0) << 16) | addr.
Method: write-watch on WRAM $7E:C4AA-$C4AB during a Rain fight (60 frames, tools/dbg_core.py),
then static disassembly with tools/umk3rom.py. Confidence labels: VERIFIED = seen in bytes or log;
INFERRED = plausible from the code but not yet tested.

## Sprite table (OAM) builder, bank $80
- VERIFIED: writers of $7E:C4AA/C4AB during a fight are PCs $80:819D, $80:822A, $80:825F
  (120 writes in 60 frames). Writers of $7E:C6AA (high table) are PCs $80:81AC, $80:81EB
  (clear at $80:8000 init).
- VERIFIED: loop body at $80:8164-$80:8260 reads piece records through pointer $12
  (`adc #$0006` per step) and counter $06. Each piece:
  - reads word at record+2 (X) and record+4 (Y), adds base position $08 and $0A
  - clips: Y in [$E0 .. $FFF1) skipped, X >= $0100 skipped (branches to $80:8164)
  - packs Y into the high byte (xba) and X into the low byte, stores at $C4AA+x
  - stores record+6 | $18 at $C4AC+x (tile and attribute word)
  - sets the matching bit/entry in the high table at $C6AA+y
- VERIFIED: table size $C4AA..$C6C9 = 544 bytes (0x220), high table is the last 32 bytes.
- VERIFIED (Rain's pieces, 19 OAM entries in one frame): X = rec+2 + 0x3E (low byte stored), tile = rec+6 | $18.
  Records at $7E:56C0 and $7E:57xx.
- CORRECTION: the Y term is NOT verified. The 0xA2 is the value of $7E:170A at the add in a poke test, but
  sampling $170A at frame boundaries gives 0x0000 (occasionally 0x0092). $0A is a direct-page scratch temp, so its
  value during the loop is set inside the loop and has not been traced. Treat the Y formula as unresolved.
- Other record groups in the same frame each use a constant base pair, so they are separate objects:
  $7E:5Exx uses X 0x3E, Y 0xC9. $7E:73xx/74xx use X 0x7E, Y 0x5E. $7E:7Bxx uses X 0x7E, Y 0xC9.
  The 0x7E group fits the opponent (Reptile) position in the fight screenshots. Not yet proven.
- CAUTION: the watch_read log reported $7E:170A as 0x00 at the Y add, but poking $170A to 0xA2 gives the
  identical result, so the effective Y base is 0xA2. Treat logged base values with care.
- INFERRED: $08/$0A are the fighter's screen position (values 0x3E/0xA2 in this frame). $18 is palette/priority.

## Tile DMA (earlier findings, confirmed here)
- $83:83ED copies 16 words from a source chosen by $24/$56 into staging $7E:80A8+x. VERIFIED.
- $88:B959 starts a DMA from $7E:80A8 to VRAM, VRAM address from table. VERIFIED.
- $88:BA1D is only `sta $420B` (start DMA) then `rtl`. It does NOT build the sprite table.
  The earlier label "send_sprite_table" was wrong. VERIFIED.

## A4: how the record pointer is chosen (partial, 2026-10-18)
- VERIFIED: the builder's cursor $12 (WRAM $7E:1712) is written only by the builder itself, plus two
  routines at $88:ACA8 and $88:ACD5 area that set $12 = NOT(WRAM[$355C]) (and NOT(WRAM[$3560]) for the second
  object). See tools/analysis/log_record_pointer_writers.py.
- VERIFIED: the same routine loads $0A (the Y base) from WRAM $3662 (object A) and $3664 (object B), and
  $0E/$22 from the saved values. The Y base $A2 for Rain should therefore come from WRAM $3662 at update time.
- OPEN: WRAM $355C, $355E, $3662, $3664 read as zero at the end of a frame, so these are transient or set
  at a different point in the frame. Next: log the writers of $355C and $3662 and find the animation-frame
  table they come from.

## A4 update (2026-10-18, later)
- VERIFIED: over 30 frames, WRAM $3662-$3665 (Y base table) is written only by PC $80:FE19, and
  WRAM $355C-$355D by PC $88:ACB3, $3560-$3561 by PC $88:ACDA (tools/analysis/log_base_variable_writers.py).
- VERIFIED: $80:FE19 (`sta $3662,x`) stores A=$0000 at X=$0002 and X=$0000, i.e. it clears entries.
  So the Y base $A2 is NOT written here. The value is written somewhere else and read by this loop.
- OPEN: which code writes the non-zero $A2 into the table, and what selects the animation frame.
  Not found yet. Next: watch writes to $7E:3662 across frames when the Y base changes (jump or crouch).

## A4 jump/crouch sampling (2026-10-18, latest)
- VERIFIED: WRAM $3662 and $355C each become $0800 for one frame at jump start, and $0400 for one frame at
  crouch start, then return to $0000. They act as one-frame event pulses, not per-pose base values.
  Script: tools/analysis/sample_base_words_jump_crouch.py
- VERIFIED: WRAM $3662 holds $0000 at most frame boundaries, so the Y offset is not a frame-level variable.
- OPEN: where the Y offset $A2 is set inside the builder loop (trace writes to $7E:170A/$170B during one build).

## Y term found (2026-10-18, latest)
- VERIFIED: the builder loop at $80:812A-$80:8141 computes the piece Y term per piece, not from a constant:
  `lda $2C74,y ; sec ; sbc $EC64,x ; sta $0A` (both tables are in WRAM $7E, since DB=$7E).
  So the "$A2" was this value for the first piece, not a base. Source of the earlier 0xA2: $2C74[0x00]=0x0099, $EC64[4]=0xFFF7.
- VERIFIED on 4 executions in one frame: 3 match exactly (tools/analysis/verify_piece_y_term.py).
  The 4th (y=0002) is off by 1 (expected 0x5D, got 0x5E). Cause not found; possibly $2C74 changes mid-frame.
- OPEN: where $2C74 (Y position table) and $EC64 (per-piece offset table) are filled, and the 4th-execution mismatch.
- The earlier "Y base $A2 is a constant" claim is WITHDRAWN.

## Y tables: writers found (2026-10-18, latest)
- VERIFIED: $7E:2C74..2CFF (Y position table, used by the piece loop as `lda $2C74,y`) is written only by PC
  $88:8488 (`sta $2C74,y`), about 8 writes per frame.
- INFERRED from the code at $88:8470-$88:848B (not yet traced at runtime):
  `lda $7F0D00,x` (negated for one branch), `adc $2E9C,y`, `sta $2C74,y`.
  So Y position = (value from WRAM table $7F0D00 indexed by x) + $2E9C[y]. $7F0D00 looks like a trig/curve table.
- VERIFIED: $7E:EC64.. (per-piece offset table, used as `sbc $EC64,x`) is written by several PCs in bank $84
  ($84:A5F5 through $84:A921), about 6 writes each per frame. Routine not yet decoded.
- OPEN: index x for $7F0D00 (what sets it), $2E9C source, and the bank $84 routine that fills $EC64.
- Script: tools/analysis/log_y_table_writers.py

## Y position formula (2026-10-18, latest)
- VERIFIED on 4 stores in one frame: stored Y-table value = ±T[idx] + $2E9C[y], where T = WRAM $7F0D00 (word
  table, base WRAM offset $10D00), idx = the index in X at the lookup. Examples: idx $9A -> T=$0039, stored $0099 =
  $0039 + $0060. idx $100 -> T=$0060, stored $00C0 = $0060 + $0060. idx $1E -> T=$000B, stored $0055 = -$000B + $0060
  (the negated path at $88:8474).
- VERIFIED: the two paths differ only by sign (eor/inc at $88:8478-$88:847B). Which path runs depends on idx.
- $2E9C[y] was $0060 for every object sampled (a per-object constant, probably the character's height).
- OPEN: what sets idx (the angle or height value). This is the link to the animation/jump state. Not found yet.
- Script: tools/analysis/log_y_table_writers.py (writers); the lookup check used the same approach.
