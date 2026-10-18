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
- VERIFIED (Rain's pieces, 19 OAM entries in one frame): record is 8 bytes apart; X = rec+2 + 0x3E
  (low byte stored), Y = rec+4 + 0xA2 (high byte stored), tile = rec+6 | $18. Records at $7E:56C0 and $7E:57xx.
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
