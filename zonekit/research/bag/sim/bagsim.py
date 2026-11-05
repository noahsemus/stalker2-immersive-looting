"""Bag simulator: the bare-hands WeaponLayer + FullBody pose table, after the strafe sim's graph order
(zonekit/research/strafe/strafe_context.md): base -> Slot RightHand (LBB_7, right_hand_blend_mask, local) -> Slot
LeftHand (LBB_4, left_hand_blend_mask, local) -> look additive (mesh space) -> CopyBone jnt_camera := VB jnt_camera ->
AnimBP_Player Slot FullBody (our table, mesh-space rotation additive).
Data: bagdump.json from dump_bag.py (open editor). Run with the kit's Python."""
import json, os, re, sys, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from simcore import *
D = json.load(open(os.path.join(HERE, "bagdump.json")))
sk = Skel(D); B = sk.bones; I = sk.idx
VBP = {"VB jnt_r_knee_target": "jnt_r_foot", "VB jnt_l_knee_target": "jnt_l_foot", "VB jnt_camera": "jnt_spine_03",
       "VB jnt_weapon": "jnt_spine_03", "VB jnt_item": "jnt_spine_03", "VB jnt_r_hand_jnt_weapon": "jnt_r_hand"}
VBT = {"VB jnt_r_knee_target": "jnt_r_knee_target", "VB jnt_l_knee_target": "jnt_l_knee_target", "VB jnt_camera": "jnt_camera",
       "VB jnt_weapon": "jnt_weapon", "VB jnt_item": "jnt_item", "VB jnt_r_hand_jnt_weapon": "jnt_weapon"}
for v, p in VBP.items():
    if v in I: sk.parents[I[v]] = I[p]
sk.order = sk._order()
S = D["seqs"]; M = D["meta"]
REF = to_pose(D["refpose"])


def vb_fix(pose):
    """virtual bones: local = the target's component transform relative to the source's (UE BuildVirtualBones)"""
    C = comp(sk, pose)
    for v, tgt in VBT.items():
        if v not in I or tgt not in I: continue
        sq, st = C[I[VBP[v]]]; tq, tt = C[I[tgt]]
        pose[I[v]] = [qmul(qinv(sq), tq), qrot(qinv(sq), vsub(tt, st))]
    return pose


def raw(key, k):
    """the keyed local pose of a frame (untracked bones: the reference pose), virtual bones built from it"""
    s = S[key]; rows = s["raw"][s["frames"].index(k)]
    return vb_fix([[tuple(r[0:4]), tuple(r[4:7])] if r is not None else list(REF[i]) for i, r in enumerate(rows)])


def raw_t(key, t, fps=30.0):
    f = t * fps; fr = S[key]["frames"]
    k0 = max(fr[0], min(int(math.floor(f)), fr[-1])); a = f - k0
    if a < 1e-6 or k0 + 1 not in fr: return raw(key, k0)
    return lbb_local(sk, raw(key, k0), raw(key, k0 + 1), [a] * len(B))


def mask(fn):
    names = set(re.findall(r'BoneName="([^"]*)"', open(os.path.join(HERE, "masks", fn + ".t3d"), encoding="utf-8").read()))
    return [1.0 if b in names else 0.0 for b in B]


LM, RM = mask("left_hand_blend_mask"), mask("right_hand_blend_mask")
CAM, VCAM, LW, LH, RH, SP3 = I["jnt_camera"], I["VB jnt_camera"], I["jnt_l_weapon"], I["jnt_l_hand"], I["jnt_r_hand"], I["jnt_spine_03"]
STANCE = {"stand": ("idle", "look", "idle"), "lowcrouch": ("idle_lowcrouch", "look_lowcrouch", "idle_lowcrouch")}
ARMS = [i for i, b in enumerate(B) if LM[i] or RM[i]]


def look_pose_delta(look, lookbase, pitch):
    """ClampedControlPitch time: 0 = +90, 1 s = -90 (30 fps: frame = (90 - pitch) / 6)"""
    f = (90.0 - pitch) / 6.0
    k0 = max(0, min(int(math.floor(f)), 29)); a = f - k0
    p = lbb_local(sk, raw(look, k0), raw(look, k0 + 1), [a] * len(B)) if a > 1e-6 else raw(look, k0)
    return ms_delta(sk, vb_fix(p), raw(lookbase, 0))


def table_delta(key, k):
    if str(k) in S[key]["ue_add"]:
        return to_pose(S[key]["ue_add"][str(k)])
    return ms_delta(sk, raw(key, k), raw(key, M[key]["rf"]))


def compose(stance, pitch, bag_pose=None, tdelta=None, tw=1.0):
    base_key, look, lookbase = STANCE[stance]
    pose = raw(base_key, 0)
    if bag_pose is not None:
        pose = lbb_local(sk, pose, bag_pose, RM)
        pose = lbb_local(sk, pose, bag_pose, LM)
    pose = apply_ms(sk, pose, look_pose_delta(look, lookbase, pitch))
    C0 = comp(sk, pose)
    cam = C0[VCAM]                                   # CopyBone_2: jnt_camera := VB jnt_camera
    if tdelta is not None:
        pose = apply_ms(sk, pose, tdelta, w=tw)
    return comp(sk, pose), cam, pose


def dotv(a, b): return sum(x * y for x, y in zip(a, b))


def view(C, cam, pitch, bone=LW):
    """bone - camera in view axes (fwd, right, up) of the control rotation (pitch)"""
    p = vsub(C[bone][1], cam[1]); pr = math.radians(pitch)
    f, r, u = (math.cos(pr), 0, math.sin(pr)), (0, 1, 0), (-math.sin(pr), 0, math.cos(pr))
    return tuple(round(dotv(p, a), 1) for a in (f, r, u))


def anim_view(key, t, bone=LW, pitch=None):
    """the bag sequence on its own (MainActionSlot-like: every bone from it): bone - jnt_camera in the anim camera's
    axes (its X = forward as the VB camera at level is -11.6 deg; pitch given = use control-style axes)"""
    pose = raw_t(key, t); C = comp(sk, pose)
    p = vsub(C[bone][1], C[CAM][1])
    q = C[CAM][0]
    f = qrot(q, (1, 0, 0)); r = qrot(q, (0, 1, 0)); u = qrot(q, (0, 0, 1))
    return tuple(round(dotv(p, a), 1) for a in (f, r, u)), math.degrees(math.asin(max(-1, min(1, f[2]))))
