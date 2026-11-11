"""Write art/batman_frame_map.json: which Batman pose replaces each ninja (set 27) body frame.

Usage: python3 -I make_frame_map.py NINJA_CAPTURE_DIR [--preview OUT_PREFIX]
NINJA_CAPTURE_DIR is the output of capture_set_frames.py. Also writes art/ninja_frames.json (alignment point and
bounding box of each ninja frame in object-local pixels), which the builder uses for alignment.

EXPLICIT comes from recorded gameplay (tools/record_actions.py) and from reading the frame sheets.
Frames not listed there get a pose from their silhouette shape (see fallback()). Frames 228-233 and 250+
(empty frames, severed heads, projectiles, ropes, effects) are left as the original ninja art.
Pose numbers are the indexes in art/batman_poses.tar.gz.
"""
import json
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import batman_art as ba
from build_batman import CAP_ORIGIN

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BODY_FRAMES = range(1, 250)
KEEP_ORIGINAL = {228, 229, 230, 231, 232, 233}

STANCE, GUARD, PUNCH_WIND, PUNCH, PUNCH_BACK = 0, 39, 12, 13, 14
KNEE, HIGH_KICK, SIDE_KICK_A, SIDE_KICK_B, SIDE_KICK_C = 15, 19, 47, 48, 47   # pose 49 has a grapple rope drawn in
CROUCH_DOWN, CROUCH, CROUCH_BLOCK, CROUCH_PUNCH_A, CROUCH_PUNCH_B = 52, 78, 77, 75, 76
BLOCK, HIT_HIGH, HIT_BACK, FALLING, SITTING, KNEELING, LYING = 39, 28, 74, 60, 61, 62, 65
JUMP_RISE, JUMP_PEAK, JUMP_TUCK, JUMP_FALL, JUMP_KICK, AIR_PUNCH, LANDING = 22, 23, 50, 24, 25, 29, 27
HIT_GUT = 18
ARM_UP, ARMS_UP, UPPERCUT, FRONT_A, FRONT_B, FRONT_C, TURN_A, TURN_B = 85, 38, 37, 57, 58, 59, 16, 17

EXPLICIT = {}


def seq(frames, poses):
    for f, p in zip(frames, poses):
        EXPLICIT[f] = p


seq(range(127, 133), [0, 1, 2, 3, 2, 1])                                   # stance
seq(range(181, 189), [6, 6, 7, 8, 9, 9, 10, 11])                           # walk
seq(range(105, 111), [30, 31, 33, 30, 31, 33])                             # run
seq([24, 25], [CROUCH_DOWN, CROUCH])                                       # crouch
seq([12, 13], [CROUCH_BLOCK, CROUCH_BLOCK])                                # crouch block
seq([10, 11], [BLOCK, BLOCK])                                              # block
seq([56, 57, 58], [PUNCH_WIND, PUNCH, PUNCH_BACK])                         # high punch
seq([99, 100, 101], [51, PUNCH, 51])                                       # low punch
seq(range(51, 56), [PUNCH_WIND, KNEE, KNEE, HIGH_KICK, HIGH_KICK])         # high kick
seq(range(77, 84), [KNEE, SIDE_KICK_C, SIDE_KICK_B, SIDE_KICK_B, SIDE_KICK_C, SIDE_KICK_A, KNEE])   # spinning kick
seq([74, 75, 76], [PUNCH_WIND, KNEE, KNEE])
seq(range(94, 99), [PUNCH_WIND, KNEE, SIDE_KICK_A, SIDE_KICK_B, SIDE_KICK_B])   # low kick
seq(range(120, 127), [KNEE, TURN_A, SIDE_KICK_C, SIDE_KICK_B, SIDE_KICK_A, TURN_B, 6])   # roundhouse
seq(range(147, 155), [CROUCH_DOWN, CROUCH, CROUCH_PUNCH_B, CROUCH_PUNCH_B, CROUCH_PUNCH_B, CROUCH, CROUCH, CROUCH_DOWN])  # sweep
seq([21, 22], [CROUCH_PUNCH_A, CROUCH_PUNCH_B])                            # crouching low punch
seq([16, 17, 18], [CROUCH, CROUCH_PUNCH_B, CROUCH_PUNCH_B])                # crouching high kick
seq([19, 20], [CROUCH, CROUCH_PUNCH_A])                                    # crouching low kick
seq(range(173, 178), [CROUCH_PUNCH_A, UPPERCUT, ARM_UP, ARM_UP, UPPERCUT]) # uppercut
seq([73, 72], [JUMP_PEAK, LANDING])                                        # jump straight up, landing
seq([34], [AIR_PUNCH])                                                     # jump take-off lean
seq(range(63, 70), [JUMP_RISE, JUMP_PEAK, JUMP_TUCK, 91, JUMP_TUCK, JUMP_PEAK, JUMP_FALL])   # somersault
seq([41, 42], [AIR_PUNCH, AIR_PUNCH])                                      # jump punch
seq([39, 40, 70, 71], [JUMP_KICK, JUMP_KICK, JUMP_KICK, JUMP_KICK])        # jump kicks
seq([48, 49, 50], [BLOCK, HIT_GUT, HIT_BACK])                              # hit while standing
seq([35, 36, 37, 38], [HIT_HIGH, FALLING, FALLING, FALLING])               # knocked into the air
seq([88, 89, 90], [FALLING, SITTING, LYING])                               # landing on the back
seq([43, 44, 45, 46, 47], [LYING, LYING, SITTING, KNEELING, KNEELING])     # on the ground, getting up
seq([29, 30, 31, 32, 33], [SITTING, LYING, SITTING, SITTING, KNEELING])
seq([172], [LANDING])
seq([84, 85, 86, 87], [HIT_GUT, HIT_BACK, HIT_BACK, FALLING])               # reeling from a hit
seq([133], [0])
seq([214, 215, 216, 219], [PUNCH, PUNCH, PUNCH, PUNCH])                    # pointing / casting arm
seq(range(189, 197), [66, 67, 68, 69, 68, 67, 66, 12])                     # special-move wind-up: batarang throw
seq([202, 208, 209, 203, 204, 205], [CROUCH, CROUCH, CROUCH, 79, 79, 79])  # kneeling
seq([211, 212, 213, 225, 226], [HIT_GUT] * 5)                              # hunched over
seq([220, 221, 222, 223, 246, 247, 248, 249], [FRONT_C, FRONT_C, FRONT_C, FRONT_C, FRONT_A, FRONT_A, FRONT_B, FRONT_A])
seq([155, 156], [ARMS_UP, FRONT_A])                                        # arms thrown wide
seq([167, 168, 169], [AIR_PUNCH, AIR_PUNCH, AIR_PUNCH])                    # diving attack
seq(range(140, 147), [FRONT_C, FRONT_A, FRONT_B, FRONT_A, FRONT_C, FRONT_B, FRONT_A])   # dizzy sway
seq(range(134, 140), [51, UPPERCUT, ARMS_UP, ARM_UP, ARM_UP, ARM_UP])      # victory pose
seq(range(197, 202), [FRONT_A, ARMS_UP, ARMS_UP, ARM_UP, ARM_UP])
# Batman's special moves (tools/batman_moves_patch.py)
seq(range(112, 120), [81, 82, 83, 83, 83, 83, 83, 81])                     # Grapple Gun (spear throw frames)
seq([210, 211, 212, 213], [67, 69, PUNCH, PUNCH])                          # Batarang throw (spit frames)
seq([208, 209], [68, PUNCH])                                               # Explosive throw (fireball frames)
seq([242, 243, 244], [PUNCH_WIND, PUNCH, PUNCH_BACK])                      # Cape Charge strike (dash elbow frames)


def fallback(mask):
    """Pick a pose from the silhouette shape. mask is the captured ninja frame (origin at CAP_ORIGIN)."""
    ys, xs = np.nonzero(mask)
    if len(ys) < 60:
        return None                                   # tiny or empty: leave the original
    top, bottom = ys.min() - CAP_ORIGIN[1], ys.max() - CAP_ORIGIN[1]
    left, right = xs.min() - CAP_ORIGIN[0], xs.max() - CAP_ORIGIN[0]
    h, w = bottom - top + 1, right - left + 1
    if bottom < 22:                                   # feet well above the ground line (about +40)
        return JUMP_KICK if w > 70 else (JUMP_TUCK if h < 70 else JUMP_PEAK)
    if h < 42:
        return LYING
    if h < 60 and w > h:
        return SITTING
    if h < 78:
        return CROUCH_PUNCH_B if w > 60 else CROUCH
    if top < -78:
        return ARM_UP
    if w > 62:
        # which half sticks out: arms (upper body) or a leg
        mid = (top + bottom) // 2 + CAP_ORIGIN[1]
        upper = xs[ys < mid].max() - xs[ys < mid].min()
        lower = xs[ys >= mid].max() - xs[ys >= mid].min()
        return PUNCH if upper >= lower else SIDE_KICK_B
    return PUNCH_WIND


def main(ninja_dir, preview=None):
    meta = json.load(open(os.path.join(ninja_dir, "frames.json")))
    frames, geom = {}, {}
    for f in sorted(int(k) for k in meta):
        path = os.path.join(ninja_dir, "f%03d.png" % f)
        if not os.path.exists(path):
            continue
        mask = np.array(Image.open(path)) > 0
        if not mask.any():
            continue
        fx, fy = ba.silhouette_anchor(mask)
        ys, xs = np.nonzero(mask)
        geom[str(f)] = dict(anchor=[fx - CAP_ORIGIN[0], fy - CAP_ORIGIN[1]], cy=ba.centre_row(mask) - CAP_ORIGIN[1],
                            bbox=[int(xs.min()) - CAP_ORIGIN[0], int(ys.min()) - CAP_ORIGIN[1],
                                  int(xs.max()) - CAP_ORIGIN[0], int(ys.max()) - CAP_ORIGIN[1]])
        if f not in BODY_FRAMES or f in KEEP_ORIGINAL:
            continue
        pose = EXPLICIT.get(f)
        src = "explicit"
        if pose is None:
            pose, src = fallback(mask), "shape"
        if pose is not None:
            frames[str(f)] = dict(pose=pose, src=src)
    os.makedirs(os.path.join(REPO, "art"), exist_ok=True)
    json.dump(geom, open(os.path.join(REPO, "art", "ninja_frames.json"), "w"), indent=0, sort_keys=True)
    json.dump(dict(frames=frames), open(os.path.join(REPO, "art", "batman_frame_map.json"), "w"), indent=0, sort_keys=True)
    print("mapped %d frames (%d explicit, %d by shape)" % (
        len(frames), sum(1 for v in frames.values() if v["src"] == "explicit"),
        sum(1 for v in frames.values() if v["src"] == "shape")))


if __name__ == "__main__":
    main(sys.argv[1])
