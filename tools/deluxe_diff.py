#!/usr/bin/env python3
"""Diff UMK3 (USA) against UMK3 Deluxe v2.3. Read-only analysis.

Outputs go to the scratchpad agents/deluxe_diff directory:
  ranges.tsv      changed ranges of the first 4 MB with classes and hex context
  upper_map.tsv   non-00/non-FF runs in the upper 4 MB of Deluxe
  long_refs.tsv   24-bit pointers / JSL / JML in changed ranges that hit upper runs
  new_strings.txt ASCII strings (>=4 chars) present in Deluxe but not in the original
  summary.txt     counts
"""
import sys, math, collections, re, os

sys.path.insert(0, '/home/user/Bat-Kombat/tools')
from umk3rom import load, file_to_snes
from capstone import (Cs, CS_ARCH_MOS65XX, CS_MODE_MOS65XX_65816,
                      CS_MODE_MOS65XX_65816_LONG_M, CS_MODE_MOS65XX_65816_LONG_X,
                      CS_MODE_MOS65XX_65816_LONG_MX)

SCR = '/tmp/claude-0/-home-user-Bat-Kombat/afe52c5f-a404-552a-b206-05bca1c438dc/scratchpad'
ORIG = f'{SCR}/roms/umk3/Ultimate Mortal Kombat 3 (USA).sfc'
DELUXE = f'{SCR}/roms/deluxe/Ultimate Mortal Kombat 3 Deluxe (v2.3).sfc'
OUT = f'{SCR}/agents/deluxe_diff'
HALF = 0x400000
MERGE_GAP = 64
UPPER_GAP = 256

# Capstone 65816 modes available here (CS_MODE_MOS65XX_65816 alone is rejected):
#   LONG_X  -> 8-bit M (lda #imm is 2 bytes); capstone does not decode 0x22 as JSL in this mode,
#              so JSL/JML are missed in 8-bit code; treated as a limitation.
#   LONG_M  -> 16-bit M, 8-bit X (lda #imm is 3 bytes, jsl decodes)
#   LONG_MX -> 16-bit M and X
MODES = [('M8', CS_MODE_MOS65XX_65816_LONG_X), ('M16', CS_MODE_MOS65XX_65816_LONG_M),
         ('MX16', CS_MODE_MOS65XX_65816_LONG_MX)]

COMMON = set('''lda sta ldx ldy stx sty jsr jsl jmp jml rts rtl rti bra brl bne beq bcc bcs
bpl bmi bvc bvs inc dec inx iny dex dey cmp cpx cpy and ora eor adc sbc rep sep pha pla php
plp phx plx phy ply phb plb phd pld tax tay txa tya tcd tcs tdc tsc txs tsx asl lsr rol ror
bit stz clc sec cli sei clv cld sed nop xba xce tsb trb mvn mvp pea pei per'''.split())
CTRL = set('jsr jsl jmp jml rts rtl rti bra brl bne beq bcc bcs bpl bmi bvc bvs'.split())

CODE_THR = None   # set after calibration
GFX_H = 7.2       # whole-range entropy threshold for 4bpp-like data (random 7.9, code ~5.5-6.5 typ.)
TEXT_FRAC = 0.75


def entropy(b):
    if not b:
        return 0.0
    c = collections.Counter(b)
    n = len(b)
    return -sum(v / n * math.log2(v / n) for v in c.values())


def printable_frac(b):
    return sum(1 for x in b if 0x20 <= x <= 0x7E or x in (0x0A, 0x0D)) / max(1, len(b))


def ptr_stats(b):
    words = [b[i] | (b[i + 1] << 8) for i in range(0, len(b) - 1, 2)]
    if len(words) < 4:
        return 0.0, 0.0
    hi = sum(1 for w in words if w >= 0x8000) / len(words)
    distinct = len(set(words)) / len(words)
    return hi, distinct


ILLEGAL = set('brk cop wdm stp wai'.split())
CTRL_MIN = 0.12   # control-flow density: random bytes ~0.09, 65816 code ~0.14-0.21 (measured)
ILL_MAX = 0.06    # BRK/COP/WDM/STP/WAI density: random ~0.015, code 0-0.09 (measured)


def code_score(b):
    """Best (control-flow density, illegal density, mode) over the 65816 modes.
    A mode counts only if its illegal density is low enough to be plausible code."""
    best = (0.0, 1.0, '')
    for name, mode in MODES:
        ins = list(Cs(CS_ARCH_MOS65XX, mode).disasm(bytes(b), 0))
        if not ins:
            continue
        ctrl = sum(1 for i in ins if i.mnemonic in CTRL) / len(ins)
        ill = sum(1 for i in ins if i.mnemonic in ILLEGAL) / len(ins)
        if ill <= ILL_MAX and ctrl > best[0]:
            best = (ctrl, ill, name)
    return best


def classify(b):
    """Return (class, detail dict). Order: text, pointer, code, graphics, fill, other."""
    H = entropy(b)
    pf = printable_frac(b)
    hi, distinct = ptr_stats(b)
    ctrl_d, ill, mode = code_score(b)
    zero = b.count(0) / max(1, len(b))
    ff = b.count(0xFF) / max(1, len(b))
    d = dict(H=round(H, 2), printable=round(pf, 2), ptr_hi=round(hi, 2),
             ptr_distinct=round(distinct, 2), code_common=round(ctrl_d, 2), ctrl=round(ill, 2), mode=mode)
    if len(b) >= 8 and pf >= TEXT_FRAC:
        return 'text', d
    if len(b) >= 8 and hi >= 0.8 and distinct >= 0.5:
        return 'pointer', d
    if len(b) >= 64 and H >= GFX_H:
        return 'graphics', d
    if len(b) >= 16 and ctrl_d >= CTRL_MIN:
        return 'code', d
    if zero >= 0.9 or ff >= 0.9:
        return 'fill', d
    return 'other', d


def merge_positions(positions, gap):
    ranges = []
    for p in positions:
        if ranges and p - ranges[-1][1] <= gap:
            ranges[-1][1] = p + 1
        else:
            ranges.append([p, p + 1])
    return ranges


def hexs(b):
    return b.hex(' ')


def calibrate(orig):
    """Set CODE_THR from baselines: random bytes vs the reset-vector code in the original."""
    global CODE_THR
    import random
    rnd = random.Random(1)
    rand_scores = [code_score(bytes(rnd.getrandbits(8) for _ in range(512)))[0] for _ in range(20)]
    # reset vector: native-mode reset vector at 00:FFFC (file 0x00FFFC, HiROM bank C0 mirror)
    reset = orig[0xFFFC] | (orig[0xFFFD] << 8)
    reset_off = ((0xC0 << 16) | reset) - 0xC00000
    code_sample = bytes(orig[reset_off:reset_off + 512])
    code_s = code_score(code_sample)
    rand_max = max(rand_scores)
    rand_mean = sum(rand_scores) / len(rand_scores)
    CODE_THR = round(rand_max + 0.05, 2)
    return dict(reset=f'{0xC0:02X}:{reset:04X}', code_sample_score=code_s,
                random_mean=round(rand_mean, 2), random_max=round(rand_max, 2), code_thr=CODE_THR)


def fmt_snes(off):
    bank, addr = file_to_snes(off)
    return f'{bank:02X}:{addr:04X}'


def main():
    os.makedirs(OUT, exist_ok=True)
    orig = load(ORIG)
    dl = load(DELUXE)
    summary = []
    cal = calibrate(orig)
    summary.append(f'calibration: {cal}')

    # ---- 1. changed ranges in first 4 MB
    diffs = [i for i in range(HALF) if orig[i] != dl[i]]
    ranges = merge_positions(diffs, MERGE_GAP)
    changed_bytes = len(diffs)
    summary.append(f'changed bytes in first 4 MB: {changed_bytes}; ranges (gap<={MERGE_GAP}): {len(ranges)}')

    rows = []
    for s, e in ranges:
        b = bytes(dl[s:e])
        cls, d = classify(b)
        rows.append(dict(start=s, end=e, length=e - s, snes=fmt_snes(s), cls=cls, d=d,
                         before=bytes(orig[s:s + 16]), after=bytes(dl[s:s + 16])))
    cnt = collections.Counter(r['cls'] for r in rows)
    lens = collections.Counter()
    for r in rows:
        lens[r['cls']] += r['length']
    summary.append('class counts (ranges): ' + ', '.join(f'{k}={v}' for k, v in cnt.most_common()))
    summary.append('class bytes: ' + ', '.join(f'{k}={v}' for k, v in lens.most_common()))

    with open(f'{OUT}/ranges.tsv', 'w') as f:
        f.write('idx\tfile_start\tfile_end\tsnes\tbank\tlength\tclass\tH\tprintable\tptr_hi\tcode_common\tctrl\tmode\torig16\tdeluxe16\n')
        for i, r in enumerate(rows):
            d = r['d']
            f.write(f"{i}\t0x{r['start']:06X}\t0x{r['end']:06X}\t{r['snes']}\t{r['snes'][:2]}\t{r['length']}\t{r['cls']}\t"
                    f"{d['H']}\t{d['printable']}\t{d['ptr_hi']}\t{d['code_common']}\t{d['ctrl']}\t{d['mode']}\t"
                    f"{hexs(r['before'])}\t{hexs(r['after'])}\n")

    top = sorted(rows, key=lambda r: -r['length'])[:10]
    summary.append('10 largest ranges:')
    for r in top:
        summary.append(f"  0x{r['start']:06X}-0x{r['end']:06X} {r['snes']} len={r['length']} class={r['cls']} "
                       f"H={r['d']['H']} code={r['d']['code_common']}/{r['d']['ctrl']} ptrhi={r['d']['ptr_hi']}")

    # ---- 3a. upper 4 MB map
    upper_pos = [i for i in range(HALF, len(dl)) if dl[i] not in (0x00, 0xFF)]
    uruns = merge_positions(upper_pos, UPPER_GAP)
    uclass = collections.Counter()
    ubytes = collections.Counter()
    with open(f'{OUT}/upper_map.tsv', 'w') as f:
        f.write('file_start\tfile_end\tlength\tclass\tH\tprintable\tptr_hi\tcode_common\tctrl\tfirst16\n')
        for s, e in uruns:
            b = bytes(dl[s:e])
            cls, d = classify(b)
            uclass[cls] += 1
            ubytes[cls] += e - s
            f.write(f"0x{s:06X}\t0x{e:06X}\t{e - s}\t{cls}\t{d['H']}\t{d['printable']}\t{d['ptr_hi']}\t"
                    f"{d['code_common']}\t{d['ctrl']}\t{hexs(b[:16])}\n")
    summary.append(f'upper 4MB non-00/non-FF bytes: {len(upper_pos)} in {len(uruns)} runs (gap<={UPPER_GAP})')
    summary.append('upper run classes: ' + ', '.join(f'{k}={v} runs/{ubytes[k]} bytes' for k, v in uclass.most_common()))
    summary.append('upper largest runs:')
    for s, e in sorted(uruns, key=lambda x: -(x[1] - x[0]))[:12]:
        b = bytes(dl[s:e])
        cls, _ = classify(b)
        summary.append(f'  0x{s:06X}-0x{e:06X} len={e - s} class={cls} first8={hexs(b[:8])}')

    # ---- 3b. long pointers / JSL / JML from changed first-4MB ranges into upper runs
    # Pointer triple at position p: lo, hi, bank. Upper run start rel = (s - HALF).
    # Hypothesis: a bank byte b addresses upper offset rel via b - (rel >> 16) = constant (delta).
    run_starts = {}
    for s, e in uruns:
        if e - s >= 64:
            rel = s - HALF
            run_starts.setdefault(rel & 0xFFFF, []).append((rel, s, e))
    triples = []
    for s, e in ranges:
        for p in range(s, max(s, e - 2)):
            addr = dl[p] | (dl[p + 1] << 8)
            bank = dl[p + 2]
            if addr >= 0x8000 and addr in run_starts:
                triples.append((p, addr, bank))
    # Mapping scan: a triple (addr, bank) is read as upper offset rel = ((bank - d) & 0xFF) << 16 | addr
    # for d in 0..255 with (bank - d) & 0xFF < 0x40. Score d by the fraction of triples whose target
    # byte is non-00/non-FF (base rate for a random target is about 0.2).
    all_triples = []
    for s, e in ranges:
        for p in range(s, max(s, e - 2)):
            addr = dl[p] | (dl[p + 1] << 8)
            if addr >= 0x8000:
                all_triples.append((p, addr, dl[p + 2]))
    scores = []
    for dd in range(256):
        hits = tot = 0
        for p, addr, bank in all_triples:
            bb = (bank - dd) & 0xFF
            if bb >= 0x40:
                continue
            tot += 1
            rel = (bb << 16) | addr
            if dl[HALF + rel] not in (0x00, 0xFF):
                hits += 1
        if tot:
            scores.append((hits / tot, dd, tot))
    scores.sort(reverse=True)
    summary.append('mapping scan (frac target non-00/FF, delta d, triples): '
                   + ', '.join(f'{f:.2f}/d={dd:02X}/n={t}' for f, dd, t in scores[:6]))
    best_delta = scores[0][1] if scores else None
    best_frac = scores[0][0] if scores else 0.0
    summary.append(f'best mapping d={best_delta:02X}: upper target = HALF + ((bank - d) << 16 | addr)'
                   if best_delta is not None else 'no mapping')

    lrefs = []
    if best_delta is not None:
        for p, addr, bank in all_triples:
            bb = (bank - best_delta) & 0xFF
            if bb >= 0x40:
                continue
            rel = (bb << 16) | addr
            if dl[HALF + rel] in (0x00, 0xFF):
                continue
            opcode = dl[p - 1] if p > 0 else None
            kind = {0x22: 'JSL', 0x5C: 'JML'}.get(opcode, 'ptr')
            new = bytes(orig[p:p + 3]) != bytes(dl[p:p + 3])
            lrefs.append((p, kind, bank, addr, rel, HALF + rel, HALF + rel, new))
    with open(f'{OUT}/long_refs.tsv', 'w') as f:
        f.write('pos\tsnes_of_ref\tkind\tbank_byte\taddr\tupper_target_file\tupper_run_end\tchanged_vs_orig\n')
        for p, kind, bank, addr, rel, s, e, new in lrefs:
            f.write(f'0x{p:06X}\t{fmt_snes(p)}\t{kind}\t{bank:02X}\t{addr:04X}\t0x{s:06X}\t0x{e:06X}\t{new}\n')
    summary.append(f'long refs (delta {best_delta:02X}) into upper runs: {len(lrefs)}; '
                   f'of which changed vs original: {sum(1 for x in lrefs if x[7])}')

    # ---- 4. new ASCII strings
    pat = re.compile(rb'[\x20-\x7e]{4,}')
    orig_strs = set(m.group() for m in pat.finditer(bytes(orig)))
    new_strs = []
    for m in pat.finditer(bytes(dl)):
        if m.group() not in orig_strs:
            new_strs.append((m.start(), m.group().decode('ascii')))
    with open(f'{OUT}/new_strings.txt', 'w') as f:
        for off, sv in new_strs:
            f.write(f'0x{off:06X}\t{fmt_snes(off) if off < HALF else "upper"}\t{sv}\n')
    summary.append(f'ASCII strings (>=4) in Deluxe not present in original: {len(new_strs)} '
                   f'(first 4MB: {sum(1 for o, _ in new_strs if o < HALF)}, upper: {sum(1 for o, _ in new_strs if o >= HALF)})')

    # name table check
    summary.append('name table 0x3E544 identical: ' + str(orig[0x3E544:0x3E544 + 0x100] == dl[0x3E544:0x3E544 + 0x100]))

    with open(f'{OUT}/summary.txt', 'w') as f:
        f.write('\n'.join(summary) + '\n')
    print('\n'.join(summary))


if __name__ == '__main__':
    main()
