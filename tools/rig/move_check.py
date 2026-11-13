"""Perform every input of Batman's move list (tools/batman_moves_patch.py MOVE_LIST) and report pass/fail.

    python3 tools/rig/move_check.py ROM                         # every mode, every test
    python3 tools/rig/move_check.py ROM --modes 2p1 1p1 --only "Cape Charge" "R alone"
    python3 tools/rig/move_check.py ROM --list                  # modes and tests

Modes (Batman is always the human side; the other fighter is idle in 2P and the CPU in 1P):
    2p1  two-player fight, Batman on pad 1 (left)       2p2  two-player fight, Batman on pad 2 (right)
    1p1  one-player Novice tower started on pad 1        1p2  one-player Novice tower started on pad 2
    1p1w / 1p1m  one-player Warrior / Master tower on pad 1
Each mode is checked in round 1 and in round 2 (Batman won round 1; the game switches stage, $7E:3A7E = 5),
some tests again on stages 1, 2, 3, 4 and 6 (round 2 with the stage forced through $7E:3A84),
plus "fight start" tests on the first frame of the round, and finishers at FINISH HIM after Batman wins
round 2. The stage fatality is checked on stages 2 and 6 (its condition $82:D3FE accepts only those) by
setting the next stage ($7E:3A84) during the round-1 win, and on the normal stage as a negative check.
Test hooks used to get there (not gameplay): the opponent's health is set to 1 before Batman's winning kicks,
Batman's health is kept full in one-player rounds, and $3A84 for the stage fatality.

How a move is identified:
  * specials and finishers: the matcher copy's final RTL (found in the ROM by its bytes) runs with A = the
    handler of the record that fired (Cape Charge $C88A, Batarang $C99B, Smoke Teleport $C883, Grapple Gun
    $C9A2, Explosive $C9DA, Fatality 1 $8011, Fatality 2 $801F, Friendship $F2D1, Babality $C747, stage
    fatality $C727).
  * plain attacks by Batman's sprite frame ($7E:52F8 + 2 * side, low 9 bits): low punch 99-101, high punch
    56-58 (or 242-244 with no special: the close-range version), high kick 51-55, block 10-11, Spin Kick (back + high kick) 120-126.
States are cached in build/rig/ under a hash of the ROM, so a rebuilt ROM gets new states.
"""
import argparse, hashlib, os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import lab, umk3_nav

HP = (0x36D4, 0x3898)           # health of the left / right fighter
WINS = (0x36E0, 0x38A4)
GAME_STATE, STAGE, NEXT_STAGE = 0x36C0, 0x3A7E, 0x3A84
SPRITE = 0x52F8
HANDLERS = {0xC88A: "Cape Charge", 0xC99B: "Batarang", 0xC883: "Smoke Teleport", 0xC9A2: "Grapple Gun",
            0xC9DA: "Explosive", 0x8011: "Fatality 1", 0x801F: "Fatality 2", 0xF2D1: "Friendship",
            0xC747: "Babality", 0xC727: "Stage fatality"}
FRAMES = [("low punch", range(99, 102)), ("high punch", range(56, 59)), ("high kick", range(51, 56)),
          ("frames 242-244", range(242, 245)),     # high punch up close, and also the end of the Cape Charge dash
          ("block", range(10, 12)), ("Spin Kick", range(120, 127))]
MODES = {"2p1": ("2p", 0, 0), "2p2": ("2p", 1, 0), "1p1": ("1p", 0, 0), "1p2": ("1p", 1, 0),
         "1p1w": ("1p", 0, 1), "1p1m": ("1p", 0, 2)}

# Steps: list of (frames, [buttons]) with F/B for forward/back, U/D up/down; expect = what must be seen.
def tap(*keys, hold=3, gap=3):
    return [(hold, list(keys)), (gap, [])]
def motion(seq, button, hold=4):
    out = []
    for ch in seq:
        out += tap({"D": "DOWN", "U": "UP", "F": "F", "B": "BK"}[ch])
    return out + [(hold, button)]

SPECIALS = [
    ("Y: high punch", [(4, ["Y"])], "high punch"),
    ("B: low punch", [(4, ["B"])], "low punch"),
    ("X: high kick", [(4, ["X"])], "high kick"),
    ("L: block", [(12, ["L"])], "block"),
    ("R: block (R alone)", [(12, ["R"])], "block"),
    ("R tapped", [(3, ["R"])], "block"),
    ("Batarang: A", [(4, ["A"])], "Batarang"),
    ("Cape Charge: B + Y", [(4, ["B", "Y"])], "Cape Charge"),
    ("Cape Charge: B, Y 1 frame later", [(1, ["B"]), (4, ["B", "Y"])], "Cape Charge"),
    ("Cape Charge: B, Y 2 frames later", [(2, ["B"]), (4, ["B", "Y"])], "Cape Charge"),
    ("Cape Charge: Y, B 1 frame later", [(1, ["Y"]), (4, ["B", "Y"])], "Cape Charge"),
    ("Cape Charge: Y, B 2 frames later", [(2, ["Y"]), (4, ["B", "Y"])], "Cape Charge"),
    ("B, Y 5 frames later (outside the window)", [(5, ["B"]), (4, ["B", "Y"])], "low punch+"),
    ("B + Y held, B let go first", [(8, ["B", "Y"]), (12, ["Y"])], "Cape Charge"),
    ("B + Y held, Y let go first", [(8, ["B", "Y"]), (12, ["B"])], "Cape Charge"),
    ("B tapped 1 frame", [(1, ["B"])], "low punch"),
    ("Y tapped 1 frame", [(1, ["Y"])], "high punch"),
    ("Y tapped 2 frames", [(2, ["Y"])], "high punch"),
    ("X tapped 1 frame", [(1, ["X"])], "high kick"),
    ("A tapped 1 frame", [(1, ["A"])], "Batarang"),
    ("Smoke Teleport: Down, Back, Y", motion("DB", ["Y"]), "Smoke Teleport"),
    ("Grapple Gun: Back, Back, Y", motion("BB", ["Y"]), "Grapple Gun"),
    ("Explosive: Down, Forward, Y", motion("DF", ["Y"]), "Explosive"),
    ("Spin Kick: Back + X", [(6, ["BK", "X"])], "Spin Kick"),
    ("SELECT alone", [(6, ["SELECT"])], "-"),
    ("R + Forward (no run)", [(20, ["R", "F"])], "block"),
    ("L + R", [(12, ["L", "R"])], "block"),
    ("A + X", [(4, ["A", "X"])], "!special"),
    ("A + B", [(4, ["A", "B"])], "!special"),
    ("A + Y", [(4, ["A", "Y"])], "!special"),
    ("R + A", [(4, ["R", "A"])], "!special"),
    ("Back, Forward, Forward, A (no finish)", motion("BFF", ["A"]), "!Friendship"),
]
START = [("R held into the fight", "R", "block"), ("B + Y held into the fight", "BY", "-")]
FINISHERS = [
    ("Fatality 1: Down, Down, Forward, X", motion("DDF", ["X"]), "Fatality 1"),
    ("Fatality 2: Forward, Forward, Down, Y", motion("FFD", ["Y"]), "Fatality 2"),
    ("Babality: Forward, Back, Back, Y", motion("FBB", ["Y"]), "Babality"),
    ("Friendship: Back, Forward, Forward, A", motion("BFF", ["A"]), "Friendship"),
    ("Stage fatality on a normal stage", motion("FDF", ["A"]), "!Stage fatality"),
]
# A few tests repeated on other stages ($7E:3A7E), because the first remap only worked on stage 0.
OTHER_STAGES = (1, 2, 3, 4, 6)
STAGE_TESTS = ("Y: high punch", "L: block", "R: block (R alone)", "Batarang: A", "Cape Charge: B + Y",
               "Cape Charge: B, Y 2 frames later", "Explosive: Down, Forward, Y")
STAGE_FATALITY = ("Stage fatality: Forward, Down, Forward, A", motion("FDF", ["A"]), "Stage fatality")


def rom_hash(rom):
    return hashlib.sha1(open(rom, "rb").read()).hexdigest()[:12]


class Rig:
    def __init__(self, rom):
        self.rom = os.path.abspath(rom)
        self.key = rom_hash(rom)
        data = open(rom, "rb").read()
        at = data.find(bytes.fromhex("a00600b7426b"), 0x3FE000, 0x3FE200)      # ldy #6 / lda [$42],y / rtl
        assert at > 0, "matcher copy not found"
        self.rtl = 0xC00000 | (at + 5)
        self.c = lab.Lab(); self.c.load(self.rom); self.c.run(5)

    # ---- input on the pad that plays Batman, directions turned into the side's forward and back
    def run(self, pad, frames, keys=(), side=None):
        side = pad if side is None else side
        me, other = self.w(0x3DA8 + 2 * side), self.w(0x3DA8 + 2 * (1 - side))   # X positions: forward is
        fwd, back = ("RIGHT", "LEFT") if me < other else ("LEFT", "RIGHT")     # toward the opponent
        b = [fwd if k == "F" else back if k == "BK" else k for k in keys]
        if pad == 0:
            self.c.run2(frames, b, [])
        else:
            self.c.run2(frames, [], b)

    def w(self, a):
        return self.c.w16(a)

    def until(self, pad, cond, limit, keys=()):
        for i in range(limit):
            if cond():
                return i
            self.run(pad, 1, keys)
        raise RuntimeError("condition not reached in %d frames" % limit)

    # ---- states
    def cached(self, name, make):
        f = os.path.join(lab.S, "mc_%s_%s.st" % (self.key, name))
        if os.path.exists(f):
            st = open(f, "rb").read()
        else:
            try:
                make()
            except (AssertionError, RuntimeError) as e:     # reported as "no state" rows, the rest still runs
                print("state %s not reached: %s" % (name, e))
                return None
            st = self.c.save()
            open(f, "wb").write(st)
        self.c.restore(st)
        return st

    def boot(self, players, side, tower):
        c = self.c
        c.lib.retro_reset()
        if players == "2p" or side == 0:
            umk3_nav.boot_to_roster(c)
        else:
            c.run(1500)
            for _ in range(3):
                c.run2(30, [], ["START"]); c.run2(200, [], [])
            c.run2(60, [], [])
        if players == "2p":
            c.run2(6, [], ["START"]); c.run(60)
            if side == 0:
                umk3_nav.select_fighter(c, 0, 0); c.run(40)
                c.run2(5, [], ["A"])
            else:
                umk3_nav.select_fighter(c, 1, 0); c.run(40)
                for _ in range(6):
                    c.run2(4, [], ["LEFT"]); c.run2(20, [], [])
                c.run2(5, [], ["A"])
        else:
            if side == 0:
                umk3_nav.select_fighter(c, 0, 0)
            else:
                for _ in range(6):
                    c.run2(4, [], ["LEFT"]); c.run2(20, [], [])
                c.run2(5, [], ["A"])
            self.run(side, 400)
            for _ in range(tower):
                self.run(side, 5, ["RIGHT"]); self.run(side, 30)
            self.run(side, 5, ["A"]); self.run(side, 1000); self.run(side, 5, ["START"])
        ids = (self.w(0x52C8), self.w(0x52CA))
        assert ids[side] == 24 and ids[1 - side] != 24, "Batman not on the expected side: %r" % (ids,)

    def to_live(self, side, settle=10):
        """Run until the round is live ($36C0 == 2), then settle frames."""
        self.until(side, lambda: self.w(GAME_STATE) != 2, 3000)
        self.until(side, lambda: self.w(GAME_STATE) == 2, 3000)
        self.run(side, settle)

    def win_round(self, side, players, next_stage=None):
        """Batman beats the opponent in the current round (opponent health set to 1, kicks)."""
        opp = 1 - side
        wins0 = self.w(WINS[side])
        for k in range(400):
            self.c.poke_wram(HP[opp], struct.pack("<H", 1))
            if players == "1p":
                self.c.poke_wram(HP[side], struct.pack("<H", 166))
            if next_stage is not None:
                self.c.poke_wram(NEXT_STAGE, struct.pack("<H", next_stage))
            attack = (["X"], ["Y"], ["DOWN", "Y"], ["DOWN", "X"], ["A"])[k % 5]   # mixed, so a blocking CPU is hit
            self.run(side, 3, ["F"]); self.run(side, 4, attack); self.run(side, 8)
            if self.w(WINS[side]) > wins0:
                return
        raise RuntimeError("could not win the round")

    def approach(self, side):
        """FINISH HIM: let the last kick end, then walk up to the dizzy opponent (fatality range is close)."""
        self.run(side, 20)
        self.until(side, lambda: abs(self.w(0x3DA8) - self.w(0x3DAA)) <= 66, 400, ["F"])
        self.run(side, 4)
        assert self.w(GAME_STATE) == 2 and self.w(HP[1 - side]) == 0, "not at FINISH HIM (round won on time?)"

    def states(self, mode):
        players, side, tower = MODES[mode]
        out = {}
        out["r1"] = self.cached(mode + "_r1", lambda: (self.boot(players, side, tower), self.to_live(side)))
        out["pre2"] = self.cached(mode + "_pre2", lambda: (self.c.restore(out["r1"]), self.win_round(side, players)))
        out["start"] = self.cached(mode + "_start", lambda: (self.c.restore(out["pre2"]),
                                                             self.until(side, lambda: self.w(GAME_STATE) == 7, 3000),
                                                             self.until(side, lambda: self.w(GAME_STATE) == 2, 3000)))
        out["r2"] = self.cached(mode + "_r2", lambda: (self.c.restore(out["start"]), self.run(side, 10)))
        for stage in OTHER_STAGES:
            def mk2(stage=stage):
                self.c.restore(out["r1"])
                self.win_round(side, players, next_stage=stage)
                self.to_live(side)
            out["s%d" % stage] = self.cached("%s_s%d" % (mode, stage), mk2)
        out["fin"] = self.cached(mode + "_fin", lambda: (self.c.restore(out["r2"]), self.win_round(side, players),
                                                         self.approach(side)))
        for stage in (2, 6):
            def mk(stage=stage):
                self.c.restore(out["r1"])
                self.win_round(side, players, next_stage=stage)
                self.to_live(side)
                self.win_round(side, players)
                self.approach(side)
            out["fin_s%d" % stage] = self.cached("%s_fin_s%d" % (mode, stage), mk)
        return out

    # ---- one test
    def perform(self, st, side, steps, tail=70):
        self.c.restore(st)
        self.c.reset_hooks(); self.c.watch_exec(self.rtl)
        seen, frames = [], []
        for n, keys in [(1, [])] + steps + [(tail, [])]:     # the first frame after a restore drops input
            for _ in range(n):
                self.run(side, 1, keys)
                f = self.w(SPRITE + 2 * side) & 0x1FF
                if not frames or frames[-1] != f:
                    frames.append(f)
        for e in self.c.log():
            seen.append(HANDLERS.get(e["a"], "handler %04X" % e["a"]))
        self.c.reset_hooks()
        return seen, frames

    def start_test(self, st_live_prev, side, keys):
        """Hold keys from the round intro into the first frames of the fight."""
        self.c.restore(st_live_prev)
        k = ["R"] if keys == "R" else ["B", "Y"]
        self.until(side, lambda: self.w(GAME_STATE) == 7, 3000, k)
        self.c.reset_hooks(); self.c.watch_exec(self.rtl)
        frames = []
        self.until(side, lambda: self.w(GAME_STATE) == 2, 3000, k)
        for _ in range(20):
            self.run(side, 1, k)
            f = self.w(SPRITE + 2 * side) & 0x1FF
            if not frames or frames[-1] != f:
                frames.append(f)
        seen = [HANDLERS.get(e["a"], "handler %04X" % e["a"]) for e in self.c.log()]
        self.c.reset_hooks()
        return seen, frames


def describe(seen, frames):
    what = list(dict.fromkeys(seen))
    for name, r in FRAMES:
        if any(f in r for f in frames):
            what.append(name)
    return what


def verdict(expect, what):
    specials = [w for w in what if w in HANDLERS.values() or w.startswith("handler")]
    if expect.endswith("+"):                     # this must be seen; anything may follow it
        return expect[:-1] in what
    if expect == "-":
        return not specials and not any(w in ("low punch", "high punch", "high kick") for w in what)
    if expect.startswith("!"):
        bad = expect[1:]
        return (bad not in what) if bad != "special" else not [s for s in specials if s != "Batarang"]
    if expect in HANDLERS.values():
        return specials == [expect] and not any(w in ("low punch", "high punch") for w in what)
    if expect == "high punch" and "frames 242-244" in what and not specials:
        return True                              # high punch up close (seen on screen: Master tower, stage 6)
    return expect in what and not specials


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rom")
    ap.add_argument("--modes", nargs="*", default=list(MODES))
    ap.add_argument("--only", nargs="*", help="test names starting with any of these")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--verbose", "-v", action="store_true")
    a = ap.parse_args()
    if a.list:
        print("modes:", ", ".join(MODES))
        for t in SPECIALS + FINISHERS + [STAGE_FATALITY]:
            print(" ", t[0])
        for t in START:
            print(" ", t[0])
        return
    rig = Rig(a.rom)
    want = lambda name: not a.only or any(name.startswith(o) for o in a.only)
    results, fails = {}, 0
    for mode in a.modes:
        players, side, _ = MODES[mode]
        st = rig.states(mode)
        rows = [(t, "r1") for t in SPECIALS] + [(t, "r2") for t in SPECIALS] + [(t, "fin") for t in FINISHERS]
        rows += [(t, "s%d" % k) for k in OTHER_STAGES for t in SPECIALS if t[0] in STAGE_TESTS]
        rows += [(STAGE_FATALITY, "fin_s2"), (STAGE_FATALITY, "fin_s6")]
        for (name, steps, expect), where in rows:
            if not want(name):
                continue
            if st[where] is None:
                results.setdefault("%s [%s]" % (name, where), {})[mode] = ("no state", [])
                continue
            seen, frames = rig.perform(st[where], side, steps)
            what = describe(seen, frames)
            ok = verdict(expect, what)
            fails += not ok
            label = "%s [%s]" % (name, where)
            results.setdefault(label, {})[mode] = ("pass" if ok else "FAIL", what)
            if a.verbose or not ok:
                print("%-5s %-4s %-52s saw %s%s" % ("pass" if ok else "FAIL", mode, label, ", ".join(what) or "-",
                                                   "  frames %s" % frames[:24] if a.verbose else ""))
        for name, keys, expect in START:
            if not want(name):
                continue
            seen, frames = rig.start_test(st["pre2"], side, keys)
            what = describe(seen, frames)
            ok = verdict(expect, what)
            fails += not ok
            label = "%s [round 2 start]" % name
            results.setdefault(label, {})[mode] = ("pass" if ok else "FAIL", what)
            if a.verbose or not ok:
                print("%-5s %-4s %-52s saw %s" % ("pass" if ok else "FAIL", mode, label, ", ".join(what) or "-"))
    print()
    print("| Test | " + " | ".join(a.modes) + " |")
    print("|---|" + "---|" * len(a.modes))
    for label, r in results.items():
        print("| %s | %s |" % (label, " | ".join(r.get(m, ("", ""))[0] for m in a.modes)))
    print("\n%d failed" % fails)
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
