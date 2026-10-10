"""Builds /ImmersiveLooting/Runtime/AS_ImmLoot_Grab in the open editor (through the harness ue_exec tool):
a copy of the vanilla left-hand grab (fp_ar_weapon_grab) with the hand raised into view around the grab.

Build 3 report: "the left hand moves quickly in the lower bottom left, it needs to come in full view". In the vanilla
grab the hand takes the item about 15-17 cm below the eye and 16-21 cm left (camera space, frames 12-21). Here the
left arm is re-solved with a two-bone IK (upper arm + forearm; the hand keeps its mesh-space rotation, the elbow
stays on the side it was) toward hand + w(frame) * OFFSET, w rising from frame 3 to 11, holding to 20, gone by 27
(the move to the belt / pocket stays as it was). The HandIK notifies of the vanilla montage (left hand off the grip,
back on it) are added to the sequence, so it can be played as a dynamic montage in the LeftHand slot.
Output: <SCRATCH>/make_grab_seq.txt
"""
import math
import os
import unreal

AL = unreal.AnimationLibrary
EAL = unreal.EditorAssetLibrary
SRC = "/Game/_STALKER2/Animations/Player/AnimSequences/ar/common/grabitem/fp_ar_weapon_grab"
MONT = "/Game/_STALKER2/Animations/Player/AnimSequences/ar/ak74/MG_fp_ak74_weapon_grab"
DIR = f"{MOD_ROOT}/Runtime"
NAME = "AS_ImmLoot_Grab"
OFFSET = tuple(float(x) for x in ARGS.get("OFFSET", "-3,7,12").split(","))   # mesh space: +X forward, +Y right, +Z up
W_IN, W_FULL, W_HOLD, W_OUT = 3, 11, 20, 27
ARM, FORE, HAND, SHOULDER = "jnt_l_arm", "jnt_l_fore_arm", "jnt_l_hand", "jnt_l_shoulder"
out = []


def qmul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz)


def qinv(a):
    return (-a[0], -a[1], -a[2], a[3])


def qrot(a, p):
    r = qmul(qmul(a, (p[0], p[1], p[2], 0.0)), qinv(a))
    return (r[0], r[1], r[2])


def add(a, b): return (a[0] + b[0], a[1] + b[1], a[2] + b[2])
def sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def mul(a, s): return (a[0] * s, a[1] * s, a[2] * s)
def dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def norm(a): return math.sqrt(dot(a, a))
def unit(a): n = norm(a); return mul(a, 1.0 / n) if n > 1e-9 else (0.0, 0.0, 0.0)


def q_between(u, v):
    """Shortest rotation taking direction u to direction v."""
    u, v = unit(u), unit(v)
    c = cross(u, v)
    d = dot(u, v)
    if d < -0.999999:
        axis = unit(cross(u, (1.0, 0.0, 0.0)) if abs(u[0]) < 0.9 else cross(u, (0.0, 1.0, 0.0)))
        return (axis[0], axis[1], axis[2], 0.0)
    q = (c[0], c[1], c[2], 1.0 + d)
    n = math.sqrt(sum(x * x for x in q))
    return tuple(x / n for x in q)


def smooth(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def weight(f):
    if f <= W_IN or f >= W_OUT:
        return 0.0
    if f < W_FULL:
        return smooth((f - W_IN) / (W_FULL - W_IN))
    if f <= W_HOLD:
        return 1.0
    return 1.0 - smooth((f - W_HOLD) / (W_OUT - W_HOLD))


def local(seq, bone, k):
    t = AL.get_bone_pose_for_frame(seq, bone, k, False)
    return ((t.translation.x, t.translation.y, t.translation.z),
            (t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w),
            (t.scale3d.x, t.scale3d.y, t.scale3d.z))


def cs(seq, bone, k):
    q, p = (0.0, 0.0, 0.0, 1.0), (0.0, 0.0, 0.0)
    for b in reversed([str(x) for x in AL.find_bone_path_to_root(seq, bone)]):
        lp, lq, _ = local(seq, b, k)
        p = add(p, qrot(q, lp))
        q = qmul(q, lq)
    return p, q


try:
    src = unreal.load_asset(SRC)
    path = f"{DIR}/{NAME}"
    if not EAL.does_asset_exist(path):
        dup = unreal.AssetToolsHelpers.get_asset_tools().duplicate_asset(NAME, DIR, src)
        out.append(f"duplicated: {dup}")
    seq = unreal.load_asset(path)
    nkeys = AL.get_num_keys(src)
    out.append(f"keys {nkeys}, offset {OFFSET}")
    keys = {b: ([], [], []) for b in (ARM, FORE, HAND)}
    for k in range(nkeys):
        sh_p, sh_q = cs(src, SHOULDER, k)
        a_l, f_l, h_l = local(src, ARM, k), local(src, FORE, k), local(src, HAND, k)
        a_q = qmul(sh_q, a_l[1]); A = add(sh_p, qrot(sh_q, a_l[0]))
        f_q = qmul(a_q, f_l[1]); E = add(A, qrot(a_q, f_l[0]))
        h_q = qmul(f_q, h_l[1]); H = add(E, qrot(f_q, h_l[0]))
        w = weight(k)
        T = add(H, mul(OFFSET, w))
        l1, l2 = norm(sub(E, A)), norm(sub(H, E))
        to_t = sub(T, A)
        d = max(abs(l1 - l2) + 0.01, min(l1 + l2 - 0.01, norm(to_t)))
        dirv = unit(to_t)
        a = (l1 * l1 - l2 * l2 + d * d) / (2 * d)
        h = math.sqrt(max(l1 * l1 - a * a, 0.0))
        pole = sub(sub(E, A), mul(dirv, dot(sub(E, A), dirv)))
        pole = unit(pole) if norm(pole) > 1e-6 else unit(cross(dirv, (0.0, 0.0, 1.0)))
        E2 = add(A, add(mul(dirv, a), mul(pole, h)))
        T2 = add(A, mul(dirv, d))
        r1 = q_between(sub(E, A), sub(E2, A))
        a_q2 = qmul(r1, a_q)
        r2 = q_between(qrot(r1, sub(H, E)), sub(T2, E2))
        f_q2 = qmul(r2, qmul(r1, f_q))
        a_loc = qmul(qinv(sh_q), a_q2)
        f_loc = qmul(qinv(a_q2), f_q2)
        h_loc = qmul(qinv(f_q2), h_q)
        for b, lq, l in ((ARM, a_loc, a_l), (FORE, f_loc, f_l), (HAND, h_loc, h_l)):
            keys[b][0].append(unreal.Vector(*l[0]))
            keys[b][1].append(unreal.Quat(*lq))
            keys[b][2].append(unreal.Vector(*l[2]))
        if k % 3 == 0:
            out.append(f"k{k:02d} w={w:.2f} hand=({H[0]:.1f},{H[1]:.1f},{H[2]:.1f}) -> ({T2[0]:.1f},{T2[1]:.1f},{T2[2]:.1f}) "
                       f"reach {norm(to_t):.1f}/{l1 + l2:.1f}")
    ctrl = seq.get_editor_property("controller")
    ctrl.open_bracket("ImmLoot raised grab", True)
    for b, (pos, rot, scl) in keys.items():
        ctrl.set_bone_track_keys(b, pos, rot, scl, True)
    ctrl.close_bracket(True)
    # HandIK notifies from the vanilla montage (left hand off the grip at the start, back on before the end)
    AL.remove_animation_notify_events_by_name(seq, "HandIK")
    mont = unreal.load_asset(MONT)
    track = "ImmLoot"
    if track not in [str(t) for t in AL.get_animation_notify_track_names(seq)]:
        AL.add_animation_notify_track(seq, track, unreal.LinearColor(0.2, 0.8, 0.2, 1.0))
    hand = None
    for e in AL.get_animation_notify_events(mont):
        if e.notify is not None and e.notify.get_class().get_name() == "AnimNotify_HandIK":
            hand = e.notify.get_editor_property("hand_to_apply")
    hik = unreal.load_class(None, "/Script/Stalker2.AnimNotify_HandIK")
    for t, end in ((0.035907, None), (1.178550, 1.0)):      # times of the vanilla montage's two HandIK notifies
        new = AL.add_animation_notify_event(seq, track, t, hik)
        new.set_editor_property("hand_to_apply", hand)
        if end is not None:
            new.set_editor_property("end_value", end)
        out.append(f"HandIK at {t}: hand {new.get_editor_property('hand_to_apply')} end {new.get_editor_property('end_value')}")
    out.append(f"notifies now: {[str(x) for x in AL.get_animation_notify_event_names(seq)]}")
    out.append(f"saved: {EAL.save_loaded_asset(seq, only_if_is_dirty=False)}")
except Exception:
    import traceback
    out.append("EXCEPTION " + traceback.format_exc())
os.makedirs(SCRATCH, exist_ok=True)
open(os.path.join(SCRATCH, "make_grab_seq.txt"), "w").write("\n".join(out))
