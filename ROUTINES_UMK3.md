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
- INFERRED: record layout is 6 bytes with tile word at +6 and X/Y at +2/+4. Not yet decoded
  against Rain's known OAM entries (next check: A3 in Current_Work.md).
- INFERRED: $18 is a palette/priority base, $08/$0A are the fighter's screen position.

## Tile DMA (earlier findings, confirmed here)
- $83:83ED copies 16 words from a source chosen by $24/$56 into staging $7E:80A8+x. VERIFIED.
- $88:B959 starts a DMA from $7E:80A8 to VRAM, VRAM address from table. VERIFIED.
- $88:BA1D is only `sta $420B` (start DMA) then `rtl`. It does NOT build the sprite table.
  The earlier label "send_sprite_table" was wrong. VERIFIED.
