"""Deterministic navigation of Batman Returns (SNES, USA) from boot into Stage 1 gameplay.

Usage:
    import sys; sys.path.insert(0, '/home/user/Bat-Kombat/tools')
    import libretro_harness as h
    import br_gameplay as bg
    c = h.Core(bg.CORE)
    c.load(bg.ROM)
    bg.boot_to_gameplay(c)
    frames = bg.perform(c, 'walk_right', keep_frames=True)

Verified button mapping in Stage 1 gameplay (see the work dir screenshots):
    RIGHT  walk right (screen scrolls, enemies enter from the right)
    LEFT   walk left
    DOWN   crouch
    B      jump (Batman rises about 60 px and lands over about 50 frames)
    Y      punch (arm extended, short forward lunge)
    A      throw batarang (arm raised, small batarang flies right along the ground)
    X      no visible effect in any tested context (idle, walking, jumping)
Not identified: UP (small upward shift only), L and R (identical to each other; a sustained
hold changes the sprite pose, a short tap does nothing), SELECT, START.
"""
import os
import sys

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)
import libretro_harness as h  # noqa: E402

ROM = ('/tmp/claude-0/-home-user-Bat-Kombat/afe52c5f-a404-552a-b206-05bca1c438dc/'
       'scratchpad/roms/br/Batman Returns (USA).sfc')
CORE = '/usr/lib/x86_64-linux-gnu/libretro/snes9x_libretro.so'

# (frames, buttons) pairs run in order from power-on.
# START at frame 1000 skips the intro crawl to the title screen.
# START at frame 1204 selects GAME START; scene 1 plays and gameplay is on screen by frame 3808.
BOOT_SCRIPT = [
    (1000, []),
    (4, ['START']),
    (200, []),
    (4, ['START']),
    (2600, []),
]
BOOT_TOTAL_FRAMES = sum(n for n, _ in BOOT_SCRIPT)  # 3808

# Each action is a list of (frames, buttons) segments applied from the current state.
ACTIONS = {
    'idle': [(30, [])],
    'walk_right': [(60, ['RIGHT'])],
    'walk_left': [(60, ['LEFT'])],
    'crouch': [(30, ['DOWN'])],
    'jump': [(3, ['B']), (50, [])],
    'punch': [(3, ['Y']), (20, [])],
    'batarang': [(3, ['A']), (30, [])],
    # X produced no visible change in any tested context. Kept so the name exists;
    # it is NOT a verified kick.
    'kick_or_attack2': [(3, ['X']), (20, [])],
}


def boot_to_gameplay(core):
    """Run the fixed boot script. Returns the core, now at Stage 1 gameplay."""
    for frames, buttons in BOOT_SCRIPT:
        core.run(frames, buttons)
    return core


def perform(core, action, keep_frames=False):
    """Run a named action from the current state.

    Returns the list of frames (one copy per emulated frame) when keep_frames is True,
    otherwise an empty list.
    """
    if action not in ACTIONS:
        raise KeyError('unknown action %r; known: %s' % (action, ', '.join(sorted(ACTIONS))))
    out = []
    for frames, buttons in ACTIONS[action]:
        for _ in range(frames):
            core.run(1, buttons)
            if keep_frames:
                out.append(core.frame.copy())
    return out
