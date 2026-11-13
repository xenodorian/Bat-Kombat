"""Measure how often the CPU opponent attacks in a one-player fight, and how much damage the player takes.

    python3 cpu_attack_rate.py ROM [--tower 0] [--level N] [--opp ID] [--cell 1 0] [--p1 idle|script]
                               [--frames 10800] [--seed 1] [--hist] [--png OUT.png]

Reaches a one-player fight from boot (tools/umk3_nav.py): P1 picks roster cell --cell, then the tower --tower
at "Choose your destiny" (0 Novice, 1 Warrior, 2 Master, 3 the tallest tower, also labelled MASTER). --opp pokes
the opponent's fighter id ($7E:3894) every frame from the tower choice to the fight, so any fighter can be the
CPU (poking it earlier turns the game into a two-player match). --level pokes the AI level $7E:3A8A once the round
is live (the game moves it after every fight, see tools/novice_ai_patch.py). The fight state is cached in
build/rig/ (per ROM content).

Then it plays --frames frames (60 per second). P1 is idle, or with --p1 script follows a seeded random script
(walk in, walk back, the four attacks, block, crouch, 8-30 frames each). Both health bars are refilled every frame
and the round clock is wound back from 19 to 99 in the clock thread's direct page (the HUD digits $7E:36B0/$36B2
are only a copy), so the round never ends and the AI still sees a running clock.

Counted from the CPU fighter thread, field $78 = current action, read once per frame. The thread is found from
the human's thread (field $2A = 0, $7C bit 0 set), whose field $68 is the opponent thread's direct page (often
$0800, but the thread can be restarted on another page). An attack start is a change of $78 to a value with high
byte $01. Action groups seen on 2026-11-13 (P1 inputs on Reptile, CPU writes): $01xx attacks ($0101 high punch,
$0102 low punch, $0103 high kick, $0104 low kick, $0105 roundhouse, $010D sweep, $010E uppercut, $0116 written by
$82:F495), $03xx stance, walk, crouch, jump ($0303 stance, $0308 jump forward), $05xx being hit (the attacker's
thread redirects the victim through $85:C6CC), $06xx attack recovery, $07xx block.
Prints attacks per minute, mean frames between attack starts, P1 damage per minute; --hist adds the action
histogram and the CPU thread pages seen.
"""
import argparse, collections, hashlib, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import lab, umk3_nav

P1_HP, P2_HP = 0x36D4, 0x3898
CLOCK_PC = 0x85A1FB        # the round clock thread copies its digits ($32 ones, $36 tens) to $7E:36B2 / $7E:36B0 here
ATTACK_KINDS = (0x01,)
SCRIPT = [[], ["RIGHT"], ["LEFT"], ["Y"], ["B"], ["X"], ["A"], ["L"], ["DOWN"], []]


def fight_state(rom, tower, col, row, opp, settle):
    digest = hashlib.md5(open(rom, "rb").read()).hexdigest()[:8]          # a rebuilt ROM gets a new state
    tag = "cpu_t%d_c%d%d_o%s_%s_%s.st" % (tower, col, row, "x" if opp is None else opp, os.path.basename(rom), digest)
    f = os.path.join(lab.S, tag)
    c = lab.Lab(); c.load(rom)
    if os.path.exists(f):
        c.run(5); c.restore(open(f, "rb").read())
        return c
    pokes = {} if opp is None else {0x3894: bytes([opp, 0])}
    umk3_nav.boot_to_roster(c)
    umk3_nav.select_fighter(c, col, row)
    c.run(400)
    for _ in range(tower):
        c.run(6, ["RIGHT"]); c.run(40)
    c.run(5, ["A"]); c.run(30)
    c.run_poking(970, [], pokes)
    c.run_poking(5, ["START"], pokes); c.run_poking(settle, [], pokes)
    # wait until the CPU fighter stands in its stance with both health bars full
    for _ in range(600):
        cpu = cpu_dp(c.wram())
        if cpu and c.w16(cpu + 0x78) >> 8 == 3 and c.w16(P1_HP) == 0xA6 and c.w16(P2_HP) == 0xA6:
            break
        c.run(1)
    open(f, "wb").write(c.save())
    return c


def w16(w, a):
    return w[a] | w[a + 1] << 8


def cpu_dp(w):
    """Direct page of the CPU fighter's thread, or None."""
    for dp in range(0x0100, 0x1000, 0x100):
        if w16(w, dp + 0x2A) == 0 and w16(w, dp + 0x7C) & 1:
            o = w16(w, dp + 0x68)
            if 0x100 <= o < 0x1000 and o & 0xFF == 0 and w16(w, o + 0x2A) == 2:
                return o
    return None


def measure(c, frames, p1="idle", seed=1, level=None):
    if level is not None:
        c.poke_wram(0x3A8A, bytes([level, 0]))
    rnd = random.Random(seed)
    hist, starts = collections.Counter(), []
    dmg = 0
    w = c.wram()
    cpu = cpu_dp(w)
    prev = w16(w, cpu + 0x78)
    dps = collections.Counter()
    c.reset_hooks(); c.watch_exec(CLOCK_PC); clock = None
    btn, left = [], 0
    for f in range(frames):
        if p1 == "script":
            if left == 0:
                btn, left = rnd.choice(SCRIPT), rnd.randint(8, 30)
            left -= 1
        c.run(1, btn)
        w = c.wram()
        cpu = cpu_dp(w) or cpu
        dps[cpu] += 1
        a = w16(w, cpu + 0x78)
        if a != prev:
            hist[a] += 1
            if a >> 8 in ATTACK_KINDS:
                starts.append(f)
            prev = a
        hp = w16(w, P1_HP)
        if hp < 0xA6:
            dmg += 0xA6 - hp
        c.poke_wram(P1_HP, b"\xA6\x00"); c.poke_wram(P2_HP, b"\xA6\x00")
        for e in c.log():
            if e["pc"] == CLOCK_PC:
                clock = e["d"]
        if clock is not None and w16(w, clock + 0x36) <= 1:          # the clock thread's tens digit
            c.poke_wram(clock + 0x36, b"\x09\x00"); c.poke_wram(clock + 0x32, b"\x09\x00")
    minutes = frames / 3600.0
    gaps = [b - a for a, b in zip(starts, starts[1:])]
    return dict(attacks=len(starts), per_min=len(starts) / minutes,
                mean_gap=(sum(gaps) / len(gaps)) if gaps else float("nan"),
                dmg=dmg, dmg_per_min=dmg / minutes, hist=hist, dps=dps, level=c.w16(0x3A8A), tower=c.w16(0x3A94),
                ids=(c.w16(0x52C8), c.w16(0x52CA)))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("rom")
    ap.add_argument("--tower", type=int, default=0)
    ap.add_argument("--level", type=int)
    ap.add_argument("--opp", type=int)
    ap.add_argument("--cell", type=int, nargs=2, default=[1, 0])
    ap.add_argument("--p1", default="idle", choices=["idle", "script"])
    ap.add_argument("--frames", type=int, default=10800)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--settle", type=int, default=360)
    ap.add_argument("--hist", action="store_true")
    ap.add_argument("--png")
    a = ap.parse_args()
    c = fight_state(os.path.abspath(a.rom), a.tower, a.cell[0], a.cell[1], a.opp, a.settle)
    r = measure(c, a.frames, a.p1, a.seed, a.level)
    if a.png:
        c.save_png(a.png)
    print("tower %d level %d ids P1 %d CPU %d p1 %s: %d attacks in %.1f min = %.1f/min, mean gap %.0f frames, "
          "P1 damage %d = %.0f/min" % (r["tower"], r["level"], r["ids"][0], r["ids"][1], a.p1, r["attacks"],
                                       a.frames / 3600.0, r["per_min"], r["mean_gap"], r["dmg"], r["dmg_per_min"]))
    if a.hist:
        print(" ".join("%04X:%d" % kv for kv in sorted(r["hist"].items())))
        print("CPU thread direct page (frames):", " ".join("%04X:%d" % kv for kv in sorted(r["dps"].items())))


if __name__ == "__main__":
    main()
