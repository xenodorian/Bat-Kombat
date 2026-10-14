"""Drive Ultimate Mortal Kombat 3 (USA, SNES) from boot into a 1-player fight.

Flow (verified by screenshot, snes9x via libretro_harness.Core):
  boot ~1500 frames -> title; START (3 presses, 200 frames apart) -> roster grid
  roster: move cursor, A confirms P1 -> "CHOOSE YOUR DESTINY" (Kombat Tower)
  tower: NOVICE is preselected; A starts the climb; after it settles, START -> fight
  fight: "ROUND 1" intro, then control. HUD shows P1 and P2 names under the health bars.

Roster grid (col, row), 0-based. Valid cells (verified by cursor probing):
  row 0: cols 0-6 ; row 1: cols 0-6 except col 3 (MK logo, cursor skips it)
  row 2: cols 1-5 ; row 3: cols 1-5
Cursor movement: each press moves to the next valid cell in that direction;
  if there is none, the cursor stays. No wrap.
Cursor position is read from the frame: the selected cell has a 2px pure-green
  box (about 33x48 px, top-left at (15 + 32.2*col, 21 + 48.4*row)).
"""
import numpy as np

COLS, ROWS = 7, 4
VALID = {(c, 0) for c in range(7)} | {(c, 1) for c in range(7) if c != 3} \
    | {(c, r) for c in range(1, 6) for r in (2, 3)}
DIRS = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}
PRESS_FRAMES = 4      # frames a direction is held
SETTLE_FRAMES = 20    # frames to wait after a direction press
CONFIRM_FRAMES = 5


def _green_mask(f):
    return (f[:, :, 0] < 40) & (f[:, :, 1] > 240) & (f[:, :, 2] < 40)


def cursor_cell(frame):
    """Return the (col, row) of the roster cursor box in a frame, or None."""
    g = _green_mask(frame).astype(np.int32)
    W, H = 33, 48
    Hc = np.concatenate([np.zeros((g.shape[0], 1), np.int32), np.cumsum(g, axis=1)], axis=1)
    Vc = np.concatenate([np.zeros((1, g.shape[1]), np.int32), np.cumsum(g, axis=0)], axis=0)
    X = np.arange(0, g.shape[1] - W + 1)
    Y = np.arange(0, g.shape[0] - H + 1)
    XX, YY = np.meshgrid(X, Y)
    top = Hc[YY, XX + W] - Hc[YY, XX]
    bot = Hc[YY + H - 1, XX + W] - Hc[YY + H - 1, XX]
    left = Vc[YY + H, XX] - Vc[YY, XX]
    right = Vc[YY + H, XX + W - 1] - Vc[YY, XX + W - 1]
    score = np.minimum(np.minimum(top / W, bot / W), np.minimum(left / H, right / H))
    i = np.argmax(score)
    yy, xx = np.unravel_index(i, score.shape)
    if score[yy, xx] < 0.9:
        return None
    col = int(round((int(xx) - 15) / 32.2))
    row = int(round((int(yy) - 21) / 48.4))
    return (col, row)


def _step(cell, d):
    """Model of one press: next valid cell in direction d, or the same cell."""
    dx, dy = d
    x, y = cell
    x, y = x + dx, y + dy
    while 0 <= x < COLS and 0 <= y < ROWS:
        if (x, y) in VALID:
            return (x, y)
        x, y = x + dx, y + dy
    return cell


def _path(target):
    """Shortest sequence of directions from (0,0) to target under the model."""
    from collections import deque
    start = (0, 0)
    prev = {start: None}
    q = deque([start])
    while q:
        cur = q.popleft()
        if cur == target:
            break
        for name, d in DIRS.items():
            nxt = _step(cur, d)
            if nxt != cur and nxt not in prev:
                prev[nxt] = (cur, name)
                q.append(nxt)
    if target not in prev:
        raise ValueError("cell %r is not a selectable roster cell" % (target,))
    out = []
    cur = target
    while prev[cur] is not None:
        cur, name = prev[cur]
        out.append(name)
    return list(reversed(out))


def _press(core, buttons, hold, settle):
    core.run(hold, buttons)
    core.run(settle)


def _read_cursor(core, tries=20):
    for _ in range(tries):
        cell = cursor_cell(core.frame)
        if cell is not None:
            return cell
        core.run(10)
    raise RuntimeError("roster cursor box not found in frame")


def boot_to_roster(core):
    """Boot the ROM, go through title and START screens, stop at the roster grid."""
    core.run(1500)
    for _ in range(3):
        core.run(30, ["START"])
        core.run(200)
    core.run(60)
    cur = _read_cursor(core)
    if cur != (0, 0):
        raise RuntimeError("expected roster cursor at (0,0) after boot, got %r" % (cur,))


def select_fighter(core, col, row):
    """Move the P1 cursor from the top-left cell to (col,row) and confirm with A.

    Each press is checked against the model; a mismatch raises RuntimeError.
    """
    target = (col, row)
    cur = (0, 0)
    for name in _path(target):
        core.run(PRESS_FRAMES, [name])
        core.run(SETTLE_FRAMES)
        expect = _step(cur, DIRS[name])
        seen = _read_cursor(core)
        if seen != expect:
            raise RuntimeError("after %s expected cursor %r, saw %r" % (name, expect, seen))
        cur = expect
    if cur != target:
        raise RuntimeError("cursor ended at %r, wanted %r" % (cur, target))
    core.run(CONFIRM_FRAMES, ["A"])


def to_fight(core, col, row, fight_settle=360):
    """From boot to a live round: roster pick, tower NOVICE, START, then wait for ROUND 1 intro to finish.

    Returns the frame index (number of frames run from boot) at which control is handed over.
    """
    boot_to_roster(core)
    select_fighter(core, col, row)
    core.run(400)               # tower animation starts
    core.run(CONFIRM_FRAMES, ["A"])   # NOVICE tower
    core.run(1000)              # climb settles at the tower top
    core.run(CONFIRM_FRAMES, ["START"])
    core.run(fight_settle)      # ROUND 1 intro
    return None
