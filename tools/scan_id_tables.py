#!/usr/bin/env python3
"""Static scanner: find data tables indexed by fighter ID in the UMK3 (USA) SNES ROM.

Usage:
    python3 -I /home/user/Bat-Kombat/tools/scan_id_tables.py [ROM_PATH] > report.txt

Read-only. Prints the report to stdout.

Method:
  1. Linear-sweep disassembly of banks C0-FF (65816, M=8 X=8 assumed).
  2. Register taint pass. A/X/Y are tagged 'raw' (loaded from memory),
     'imm' (immediate), or 'dbl' (ASL A applied to a loaded value; TAX/TAY/TXA/TYA
     propagate tags). Every indexed memory operand (abs,X/Y or long,X/Y) whose
     base is in ROM is recorded with its index tag. Tags reset at branch/jump
     targets, after unconditional flow, and after calls.
  3. Structural scan: maximal runs of 16-bit words that look like ROM pointers
     (0x8000-0xFFFF; 0x0000/0xFFFF allowed as empty slots) and runs of 3-byte
     long pointers (bank 80-FF, address >= 0x8000), each at least 24 long.
  4. Candidate tables = referenced bases (1/2/3-byte entries, 25 entries) union
     structural runs. Each is scored and the top ones are reported in detail.

Limitations: linear sweep can desync on data and on M/X width changes; abs,X
bases assume DBR == code bank; no emulation. Scores are heuristics, not proof.
"""
import os
import re
import sys
from collections import defaultdict

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
import umk3rom as u  # noqa: E402
from capstone import Cs, CS_ARCH_MOS65XX, CS_MODE_MOS65XX_65816_LONG_M  # noqa: E402

DEFAULT_ROM = ("/tmp/claude-0/-home-user-Bat-Kombat/afe52c5f-a404-552a-b206-05bca1c438dc/"
               "scratchpad/roms/umk3/Ultimate Mortal Kombat 3 (USA).sfc")
N_IDS = 25
NAME_TABLE_OFF = 0x3E544

BRANCH = {"bra", "brl", "beq", "bne", "bcc", "bcs", "bmi", "bpl", "bvc", "bvs"}
UNCOND = {"jmp", "jml", "rts", "rtl", "rti", "bra", "brl"}
ASL_LIKE = {"asl", "lsr", "rol", "ror", "inc", "dec"}
IDX_RE = re.compile(r"^(0x[0-9a-f]+), ([xy])$")
HEX_RE = re.compile(r"^(0x[0-9a-f]+)$")


def hexval(s):
    m = HEX_RE.match(s.strip())
    return int(m.group(1), 16) if m else None


def sweep(rom):
    """Linear sweep of banks C0-FF. Returns list of (bank, pc, mnem, ops, size)."""
    md = Cs(CS_ARCH_MOS65XX, CS_MODE_MOS65XX_65816_LONG_M)
    md.detail = False
    out = []
    for bank in range(0xC0, 0x100):
        base = u.snes_to_file(bank, 0)
        data = bytes(rom[base:base + 0x10000])
        pc = 0
        while pc < 0x10000:
            n0 = len(out)
            for ins in md.disasm(data[pc:], pc):
                out.append((bank, ins.address, ins.mnemonic, ins.op_str, ins.size))
            if len(out) > n0:
                last = out[-1]
                pc = last[1] + last[4]
            else:
                pc += 1  # undecodable byte: skip it
    return out


def label_set(insns):
    labels = set()
    for bank, pc, mn, ops, size in insns:
        if mn in BRANCH:
            t = hexval(ops)
            if t is not None:
                labels.add((bank, t & 0xFFFF))
        elif mn in ("jmp", "jsr", "jml", "jsl"):
            t = hexval(ops)
            if t is None:
                continue
            if mn in ("jml", "jsl"):
                labels.add((t >> 16, t & 0xFFFF))
            else:
                labels.add((bank, t & 0xFFFF))
    return labels


def taint_pass(insns, labels, nrom):
    sites = []
    A = X = Y = None
    prev_bank = None
    for bank, pc, mn, ops, size in insns:
        if bank != prev_bank or (bank, pc) in labels:
            A = X = Y = None
        prev_bank = bank
        opn = ops.strip()
        imm = opn.startswith("#")
        is_a = opn in ("", "a")

        m = IDX_RE.match(opn)
        if m:
            val = int(m.group(1), 16)
            reg = m.group(2)
            tag = X if reg == "x" else Y
            bb = ba = None
            if size == 4:
                bb, ba = val >> 16, val & 0xFFFF
            elif size == 3:
                bb, ba = bank, val
            if bb is not None and bb >= 0x80 and ba >= 0x8000:
                fo = u.snes_to_file(bb, ba)
                if fo < nrom:
                    sites.append({"site": (bank, pc), "mn": mn, "ops": opn,
                                  "base": (bb, ba), "off": fo, "reg": reg,
                                  "idx": tag or "none", "size": size})

        # register transfer
        if mn == "asl" and is_a:
            A = "dbl" if A in ("raw", "dbl") else None
        elif mn in ASL_LIKE and is_a:
            A = None
        elif mn in ("lda", "pla"):
            A = "imm" if imm else "raw"
        elif mn == "txa":
            A = X
        elif mn == "tya":
            A = Y
        elif mn in ("adc", "sbc", "and", "ora", "eor", "xba", "tdc", "tsc"):
            A = None
        elif mn == "tax":
            X = A
        elif mn == "tay":
            Y = A
        elif mn in ("ldx", "plx"):
            X = "imm" if imm else "raw"
        elif mn in ("ldy", "ply"):
            Y = "imm" if imm else "raw"
        elif mn in ("inx", "dex"):
            X = None
        elif mn in ("iny", "dey"):
            Y = None
        elif mn in ("jsr", "jsl"):
            A = X = Y = None
        if mn in UNCOND:
            A = X = Y = None
    return sites


def is_ascii(rom, fo, minrun=3):
    n = 0
    for k in range(40):
        if fo + k >= len(rom):
            return False
        c = rom[fo + k]
        if c == 0:
            return n >= minrun
        if 0x20 <= c < 0x7F:
            n += 1
        else:
            return False
    return False


def word_runs(rom, minlen=24):
    """Runs of words that are pointers (0x8000+) or empty slots (0000/FFFF)."""
    res = []
    n = len(rom) // 2
    start = None
    for i in range(n):
        v = rom[2 * i] | (rom[2 * i + 1] << 8)
        if v == 0xFFFF or v == 0:
            k = 2
        elif v >= 0x8000:
            k = 1
        else:
            k = 0
        if k:
            if start is None:
                start = i
        elif start is not None:
            if i - start >= minlen:
                res.append((start, i - start))
            start = None
    if start is not None and n - start >= minlen:
        res.append((start, n - start))
    return res


def long_chains(rom, minlen=24):
    """Chains of 3-byte long pointers (addr lo/hi, bank 80-FF), stride 3."""
    res = []
    ch = [0, 0, 0]
    n = len(rom) - 2
    for i in range(n + 3):
        r = i % 3
        old = ch[r]
        ok = i < n and rom[i + 1] >= 0x80 and rom[i + 2] >= 0x80
        if ok:
            ch[r] = old + 1
        else:
            if old >= minlen:
                res.append((i - 3 * old, old))
            ch[r] = 0
    return res


def analyze(rom, off, stride, count):
    if off < 0 or off + stride * count > len(rom):
        return None
    vals = [int.from_bytes(bytes(rom[off + stride * i: off + stride * i + stride]), "little")
            for i in range(count)]
    bank, addr = u.file_to_snes(off)
    t = {"off": off, "stride": stride, "count": count, "vals": vals,
         "snes": (bank, addr), "distinct": len(set(vals))}
    sent = ptr_ok = asc = 0
    banks = set()
    for v in vals:
        if stride == 1:
            if v == 0:
                sent += 1
            continue
        if stride == 2:
            if v in (0, 0xFFFF):
                sent += 1
                continue
            if v < 0x8000:
                continue
            tb, ta = bank, v
        elif stride == 3:
            if v in (0, 0xFFFFFF):
                sent += 1
                continue
            tb, ta = v >> 16, v & 0xFFFF
            if ta < 0x8000 or tb < 0x80:
                continue
        else:
            continue
        ptr_ok += 1
        banks.add(tb)
        if is_ascii(rom, u.snes_to_file(tb, ta)):
            asc += 1
    nonsent = count - sent
    t.update(sent=sent, ptr_ok=ptr_ok,
             ptr_frac=(ptr_ok / nonsent) if nonsent else 0.0,
             asc=asc, banks=sorted(banks),
             id11=vals[11] if count > 11 else None)

    def live(v):
        return v not in (0, 0xFFFF, 0xFFFFFF)

    # alias: ID21 == ID4 and ID22 == ID14, both non-empty (0 == 0 does not count)
    t["alias"] = (count > 22 and live(vals[4]) and vals[21] == vals[4]
                  and live(vals[14]) and vals[22] == vals[14])
    # weaker: ID22 == ID14 alone (SMOKE pair), non-empty
    t["pair_14_22"] = count > 22 and live(vals[14]) and vals[22] == vals[14]
    t["nonempty"] = count - sent
    return t


def score(t, n_dbl, n_raw):
    s = 0
    if n_dbl:
        s += 3
    if n_raw:
        s += 1
    if t["count"] == N_IDS:
        s += 2
    if t["distinct"] >= 2:
        s += 2
    if t["stride"] in (2, 3) and t["ptr_frac"] >= 0.8:
        s += 3
    if t["asc"] >= 5:
        s += 1
    if t["alias"]:
        s += 3
    if t["nonempty"] >= 20:
        s += 2  # dense: most IDs populated
    elif t["nonempty"] >= 12:
        s += 1
    return s


def fmt_snes(off):
    b, a = u.file_to_snes(off)
    return f"{b:02X}:{a:04X}"


def fmt_entry(v, stride):
    return {1: f"{v:02X}", 2: f"{v:04X}", 3: f"{v:06X}"}[stride]


def main(argv):
    rom_path = argv[1] if len(argv) > 1 else DEFAULT_ROM
    rom = u.load(rom_path)
    N = len(rom)
    print(f"ROM: {rom_path}")
    print(f"Size: {N} bytes (0x{N:X})")

    insns = sweep(rom)
    labels = label_set(insns)
    sites = taint_pass(insns, labels, N)
    dbl = [s for s in sites if s["idx"] == "dbl"]
    raw = [s for s in sites if s["idx"] == "raw"]
    refs = defaultdict(list)
    for s in sites:
        if s["idx"] in ("dbl", "raw"):
            refs[s["off"]].append(s)
    print(f"Linear sweep: {len(insns)} instructions over banks C0-FF")
    print(f"Indexed ROM operands: dbl-index={len(dbl)} raw-index={len(raw)} "
          f"(distinct bases dbl={len({s['off'] for s in dbl})}, raw={len({s['off'] for s in raw})})")

    wruns = word_runs(rom)
    lchains = long_chains(rom)
    print(f"Structural runs >=24: word-pointer runs={len(wruns)}, long-pointer chains={len(lchains)}")

    # candidate tables
    cands = {}

    def add(off, stride, count, src):
        key = (off, stride, count)
        if key not in cands:
            t = analyze(rom, off, stride, count)
            if t is None:
                return
            t["src"] = set()
            cands[key] = t
        cands[key]["src"].add(src)

    for base in refs:
        for stride in (1, 2, 3):
            add(base, stride, N_IDS, "ref")
    for start, cnt in wruns:
        add(2 * start, 2, cnt, "struct")
    for start, cnt in lchains:
        add(start, 3, cnt, "struct")

    kept = []
    for key, t in cands.items():
        if t["distinct"] < 2 or t["nonempty"] < 8:
            continue
        if t["stride"] != 1 and t["ptr_frac"] < 0.8:
            continue
        exact = refs.get(t["off"], [])
        n_dbl = sum(1 for s in exact if s["idx"] == "dbl")
        n_raw = sum(1 for s in exact if s["idx"] == "raw")
        interior = sum(1 for o in refs if t["off"] < o < t["off"] + t["stride"] * t["count"])
        t.update(exact=exact, n_dbl=n_dbl, n_raw=n_raw, interior=interior)
        t["score"] = score(t, n_dbl, n_raw)
        kept.append(t)
    kept.sort(key=lambda t: (-t["score"], t["off"]))
    print(f"Candidate tables after filtering: {len(kept)} "
          f"(ref-derived {sum(1 for t in kept if 'ref' in t['src'])}, "
          f"structural {sum(1 for t in kept if 'struct' in t['src'])})")
    print()

    # name table verification
    print("== Verification: fighter name table (file 0x3E544) ==")
    nt = [t for t in kept if t["off"] == NAME_TABLE_OFF and t["stride"] == 2 and t["count"] == N_IDS]
    if nt:
        t = nt[0]
        print(f"  found: score={t['score']} ptr_frac={t['ptr_frac']:.2f} sentinels={t['sent']} "
              f"id11={t['id11']:04X} alias_21_4_22_14={t['alias']} ascii={t['asc']}/{t['count']-t['sent']}")
    else:
        print("  not in candidate list")
    print()

    top = kept[:10]
    print("== Top 10 candidate tables ==")
    print(f"{'rk':>2} {'file':>8} {'snes':>7} {'strd':>4} {'cnt':>3} {'ne':>3} {'dist':>4} {'ptr%':>5} "
          f"{'asc':>3} {'id11':>6} {'alias':>5} {'14=22':>5} {'dbl':>3} {'raw':>3} {'scr':>3} src")
    for i, t in enumerate(top, 1):
        id11 = f"{t['id11']:X}" if t["id11"] is not None else "-"
        print(f"{i:>2} 0x{t['off']:05X} {fmt_snes(t['off']):>7} {t['stride']:>4} {t['count']:>3} "
              f"{t['nonempty']:>3} {t['distinct']:>4} {100*t['ptr_frac']:>5.0f} {t['asc']:>3} {id11:>6} "
              f"{str(t['alias']):>5} {str(t['pair_14_22']):>5} {t['n_dbl']:>3} {t['n_raw']:>3} "
              f"{t['score']:>3} {','.join(sorted(t['src']))}")
    print()

    print("== Details for top 10 ==")
    for i, t in enumerate(top, 1):
        print(f"[{i}] file 0x{t['off']:05X}  snes {fmt_snes(t['off'])}  entry={t['stride']} bytes  "
              f"count={t['count']}  score={t['score']}")
        print(f"    distinct={t['distinct']} sentinels={t['sent']} ptr_ok={t['ptr_ok']} "
              f"ptr_frac={t['ptr_frac']:.2f} ascii={t['asc']} "
              f"banks={[f'{b:02X}' for b in t['banks']] or '-'} interior_ref_bases={t['interior']}")
        if t["exact"]:
            for s in sorted(t["exact"], key=lambda s: s["site"]):
                b, a = s["site"]
                print(f"    ref {b:02X}:{a:04X}  {s['mn']} {s['ops']:<16} idx={s['idx']} "
                      f"base={s['base'][0]:02X}:{s['base'][1]:04X} ({'long' if s['size']==4 else 'abs assumed DBR=code bank'})")
        else:
            print("    no exact code references (structural only)")
        ents = []
        for idx, v in enumerate(t["vals"]):
            txt = fmt_entry(v, t["stride"])
            if t["stride"] == 2 and v not in (0, 0xFFFF) and v >= 0x8000 and t["asc"]:
                fo = u.snes_to_file(t["snes"][0], v)
                if is_ascii(rom, fo):
                    end = rom.index(0, fo)
                    txt += " '" + rom[fo:end].decode("latin1") + "'"
            ents.append(f"ID{idx}={txt}")
        for j in range(0, len(ents), 5):
            print("    " + "  ".join(ents[j:j + 5]))
        print()

    print("== Flags ==")
    z11 = [t for t in kept if t["id11"] is not None and (t["id11"] == 0 or t["id11"] & 1)
           and t["nonempty"] >= 12 and (t["n_dbl"] or t["ptr_frac"] >= 0.8)]
    print(f"ID 11 zero or odd (dense tables with dbl refs or pointer-like): {len(z11)} tables")
    for t in z11[:20]:
        print(f"    0x{t['off']:05X} {fmt_snes(t['off'])} stride={t['stride']} id11={t['id11']:X} score={t['score']}")
    al = [t for t in kept if t["alias"]]
    print(f"Alias check ID21==ID4 and ID22==ID14 (both non-empty): {len(al)} tables")
    for t in al:
        print(f"    0x{t['off']:05X} {fmt_snes(t['off'])} stride={t['stride']} count={t['count']} "
              f"id11={t['id11']:X} score={t['score']}")
    p = [t for t in kept if t["pair_14_22"] and not t["alias"]]
    print(f"ID22==ID14 only (non-empty, 4/21 not matching): {len(p)} tables")
    for t in p[:20]:
        print(f"    0x{t['off']:05X} {fmt_snes(t['off'])} stride={t['stride']} count={t['count']} "
              f"nonempty={t['nonempty']} score={t['score']}")
    print()

    print("== All dbl-indexed ROM operands (code sites) grouped by base ==")
    byb = defaultdict(list)
    for s in dbl:
        byb[s["off"]].append(s)
    lines = 0
    for off in sorted(byb):
        print(f"  base 0x{off:05X} {fmt_snes(off)}:")
        for s in sorted(byb[off], key=lambda s: s["site"]):
            b, a = s["site"]
            print(f"      {b:02X}:{a:04X}  {s['mn']} {s['ops']}")
            lines += 1
        if lines > 400:
            print("  ... truncated")
            break


if __name__ == "__main__":
    main(sys.argv)
