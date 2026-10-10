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


def slerp(a, b, t):
    d = sum(x * y for x, y in zip(a, b))
    if d < 0:
        b, d = tuple(-x for x in b), -d
    if d > 0.9995:
        r = tuple(x + (y - x) * t for x, y in zip(a, b))
    else:
        th = math.acos(d)
        sa, sb = math.sin((1 - t) * th) / math.sin(th), math.sin(t * th) / math.sin(th)
        r = tuple(sa * x + sb * y for x, y in zip(a, b))
    n = math.sqrt(sum(x * x for x in r))
    return tuple(x / n for x in r)


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


BASE_BH = "/Game/_STALKER2/Animations/Player/AnimSequences/bh/stand/fp_bh_idle_stand"
NAME_BH = "AS_ImmLoot_GrabBH"


def build_bh(src, rifle_seq, tgt_path, tgt_rot, nkeys):
    """Build 8: the same hand path for EMPTY hands. The LeftHand slot replaces the left shoulder-to-fingers local
    rotations only; the spine comes from the stance underneath, and the empty-handed spine (fp_bh_idle_stand) sits so
    differently that the rifle-solved arm put the hand 35-43 cm ABOVE the eye (build 7 probe trace) - "the hand goes up
    and left off screen". Same camera-relative targets, re-solved on the empty-handed spine; the hand starts from and
    returns to the empty-handed rest pose (frames 0-12 out, 27-39 back)."""
    base = unreal.load_asset(BASE_BH)
    sp_p, sp_q = cs(base, "jnt_spine_03", 0)
    cam_bh, _ = cs(base, "jnt_camera", 0)
    cam_ar, _ = cs(src, "jnt_camera", 0)
    ba, bf, bh = local(base, ARM, 0), local(base, FORE, 0), local(base, HAND, 0)
    bsh = local(base, SHOULDER, 0)
    # rest hand in the base pose (its own shoulder)
    rq_sh = qmul(sp_q, bsh[1]); rp_sh = add(sp_p, qrot(sp_q, bsh[0]))
    rq_a = qmul(rq_sh, ba[1]); RA = add(rp_sh, qrot(rq_sh, ba[0]))
    rq_f = qmul(rq_a, bf[1]); RE = add(RA, qrot(rq_a, bf[0]))
    RQ = qmul(rq_f, bh[1]); R = add(RE, qrot(rq_f, bh[0]))
    out.append(f"BH: cam {tuple(round(x, 1) for x in cam_bh)} (rifle {tuple(round(x, 1) for x in cam_ar)}), rest hand rel cam "
               f"{tuple(round(a - b, 1) for a, b in zip(R, cam_bh))}")
    path = f"{DIR}/{NAME_BH}"
    if not EAL.does_asset_exist(path):
        unreal.AssetToolsHelpers.get_asset_tools().duplicate_asset(NAME_BH, DIR, rifle_seq)
    seq = unreal.load_asset(path)
    keys = {b: ([], [], []) for b in (ARM, FORE, HAND)}
    for k in range(nkeys):
        if k <= 12:
            bw = smooth(k / 12)
        elif k <= 27:
            bw = 1.0
        else:
            bw = 1.0 - smooth((k - 27) / 12)
        P = add(sub(tgt_path[k], cam_ar), cam_bh)
        T = add(R, mul(sub(P, R), bw))
        hq = slerp(RQ, tgt_rot[k], bw)
        sh_l = local(src, SHOULDER, k)            # our sequence's shoulder (in the LeftHand mask) on the bh spine
        sh_q = qmul(sp_q, sh_l[1]); sh_p = add(sp_p, qrot(sp_q, sh_l[0]))
        a_l, f_l, h_l = local(src, ARM, k), local(src, FORE, k), local(src, HAND, k)
        a_q = qmul(sh_q, ba[1]); A = add(sh_p, qrot(sh_q, a_l[0]))
        f_q = qmul(a_q, bf[1]); E = add(A, qrot(a_q, f_l[0]))
        H = add(E, qrot(f_q, h_l[0]))
        l1, l2 = norm(sub(E, A)), norm(sub(H, E))
        to_t = sub(T, A)
        d = max(abs(l1 - l2) + 0.01, min(l1 + l2 - 0.01, norm(to_t)))
        dirv = unit(to_t)
        a = (l1 * l1 - l2 * l2 + d * d) / (2 * d)
        h = math.sqrt(max(l1 * l1 - a * a, 0.0))
        hint = sub(E, A)                          # elbow side: the rest pose's elbow
        pole = sub(hint, mul(dirv, dot(hint, dirv)))
        pole = unit(pole) if norm(pole) > 1e-6 else unit(cross(dirv, (0.0, 0.0, 1.0)))
        E2 = add(A, add(mul(dirv, a), mul(pole, h)))
        T2 = add(A, mul(dirv, d))
        r1 = q_between(sub(E, A), sub(E2, A))
        a_q2 = qmul(r1, a_q)
        r2 = q_between(qrot(r1, sub(H, E)), sub(T2, E2))
        f_q2 = qmul(r2, qmul(r1, f_q))
        for b, lq, l in ((ARM, qmul(qinv(sh_q), a_q2), a_l), (FORE, qmul(qinv(a_q2), f_q2), f_l), (HAND, qmul(qinv(f_q2), hq), h_l)):
            keys[b][0].append(unreal.Vector(*l[0]))
            keys[b][1].append(unreal.Quat(*lq))
            keys[b][2].append(unreal.Vector(*l[2]))
        if k % 3 == 0:
            rel = sub(T2, cam_bh)
            out.append(f"BH k{k:02d} b={bw:.2f} hand rel cam ({rel[0]:.1f},{rel[1]:.1f},{rel[2]:.1f}) reach {norm(to_t):.1f}/{l1 + l2:.1f}")
    ctrl = seq.get_editor_property("controller")
    ctrl.open_bracket("ImmLoot grab, empty hands", True)
    for b, (pos, rot, scl) in keys.items():
        ctrl.set_bone_track_keys(b, pos, rot, scl, True)
    ctrl.close_bracket(True)
    # no HandIK notifies with empty hands: the copied "left hand back on" notify switched the left-hand IK on with no
    # weapon and the hand jumped to the (invisible) grip, centre-left (build 7 report "the hand just appeared there")
    for tn in [str(t) for t in AL.get_animation_notify_track_names(seq)]:
        AL.remove_animation_notify_events_by_track(seq, tn)
    out.append(f"BH notifies left: {len(AL.get_animation_notify_events(seq))}")
    out.append(f"BH saved: {EAL.save_loaded_asset(seq, only_if_is_dirty=False)}")

PITCHES = [-75, -60, -45, -30, -15, 0, 15, 30]   # view pitch of each segment (deg, + = up)
SEG = 60                                         # frames per segment (2 s); the Blueprint stops it at +1.5 s
REACH = (40.0, -28.0, -16.0)                     # hand target in the VIEW frame: ahead, right, up (cm); build 11: "way more left, a bit lower" (b10 (42,-13,-11), b9 (48,-4,-3))


def build_bh_table(src, rifle_seq, tgt_rot, nkeys):
    """Build 9 (empty hands): a pitch table. The arm bones do not follow the view pitch (build 4 / 7 data: looking
    ~27 deg down, the reaching hand sat 53 cm above the view axis = "the hand goes too far up"), so each 2 s segment
    is the grab for one view pitch: the hand goes from the empty-handed rest pose to a point 48 cm along the VIEW
    (4 cm left, 3 cm low: it covers the item at the crosshair) by frame 12, holds to 20, goes to the pocket by 27,
    back to rest by 39. Segment i starts at i * 2 s (PITCHES[i]); the Blueprint starts the montage there."""
    base = unreal.load_asset(BASE_BH)
    sp_p, sp_q = cs(base, "jnt_spine_03", 0)
    cam, _ = cs(base, "jnt_camera", 0)
    cam_ar, _ = cs(src, "jnt_camera", 0)
    ba, bf, bh = local(base, ARM, 0), local(base, FORE, 0), local(base, HAND, 0)
    bsh = local(base, SHOULDER, 0)
    rq_sh = qmul(sp_q, bsh[1]); rp_sh = add(sp_p, qrot(sp_q, bsh[0]))
    rq_a = qmul(rq_sh, ba[1]); RA = add(rp_sh, qrot(rq_sh, ba[0]))
    rq_f = qmul(rq_a, bf[1]); RE = add(RA, qrot(rq_a, bf[0]))
    RQ = qmul(rq_f, bh[1]); R = add(RE, qrot(rq_f, bh[0]))
    POCKET = add(sub((12.4, -8.2, 121.0), cam_ar), cam)        # vanilla pocket point (frame 27), body-relative
    GQ = tgt_rot[13]
    path = f"{DIR}/{NAME_BH}"
    if not EAL.does_asset_exist(path):
        unreal.AssetToolsHelpers.get_asset_tools().duplicate_asset(NAME_BH, DIR, rifle_seq)
    seq = unreal.load_asset(path)
    tracks = [str(t) for t in AL.get_animation_track_names(src)]
    total = len(PITCHES) * SEG
    keys = {b: ([], [], []) for b in tracks}
    for i, pitch in enumerate(PITCHES):
        pr = math.radians(pitch)
        fwd = (math.cos(pr), 0.0, math.sin(pr))
        up = (-math.sin(pr), 0.0, math.cos(pr))
        G = add(cam, add(mul(fwd, REACH[0]), add(mul((0.0, 1.0, 0.0), REACH[1]), mul(up, REACH[2]))))
        qp = (0.0, -math.sin(pr / 2), 0.0, math.cos(pr / 2))       # rotation about +Y by -pitch (nose up = +pitch)
        GQp = qmul(qp, GQ)
        for f in range(SEG):
            k = min(f, nkeys - 1)
            if f <= 12:
                bw, T0, Q0, T1, Q1 = smooth(f / 12), R, RQ, G, GQp
            elif f <= 20:
                bw, T0, Q0, T1, Q1 = 1.0, G, GQp, G, GQp
            elif f <= 27:
                bw, T0, Q0, T1, Q1 = smooth((f - 20) / 7), G, GQp, POCKET, tgt_rot[min(27, nkeys - 1)]
            elif f <= 39:
                bw, T0, Q0, T1, Q1 = smooth((f - 27) / 12), POCKET, tgt_rot[min(27, nkeys - 1)], R, RQ
            else:
                bw, T0, Q0, T1, Q1 = 1.0, R, RQ, R, RQ
            T = add(T0, mul(sub(T1, T0), bw))
            hq = slerp(Q0, Q1, bw)
            sh_l = local(src, SHOULDER, k)
            sh_q = qmul(sp_q, sh_l[1]); sh_p = add(sp_p, qrot(sp_q, sh_l[0]))
            a_l, f_l, h_l = local(src, ARM, k), local(src, FORE, k), local(src, HAND, k)
            a_q = qmul(sh_q, ba[1]); A = add(sh_p, qrot(sh_q, a_l[0]))
            f_q = qmul(a_q, bf[1]); E = add(A, qrot(a_q, f_l[0]))
            H = add(E, qrot(f_q, h_l[0]))
            l1, l2 = norm(sub(E, A)), norm(sub(H, E))
            to_t = sub(T, A)
            d = max(abs(l1 - l2) + 0.01, min(l1 + l2 - 0.01, norm(to_t)))
            dirv = unit(to_t)
            a = (l1 * l1 - l2 * l2 + d * d) / (2 * d)
            h = math.sqrt(max(l1 * l1 - a * a, 0.0))
            hint = sub(E, A)
            pole = sub(hint, mul(dirv, dot(hint, dirv)))
            pole = unit(pole) if norm(pole) > 1e-6 else unit(cross(dirv, (0.0, 0.0, 1.0)))
            E2 = add(A, add(mul(dirv, a), mul(pole, h)))
            T2 = add(A, mul(dirv, d))
            r1 = q_between(sub(E, A), sub(E2, A))
            a_q2 = qmul(r1, a_q)
            r2 = q_between(qrot(r1, sub(H, E)), sub(T2, E2))
            f_q2 = qmul(r2, qmul(r1, f_q))
            solved = {ARM: qmul(qinv(sh_q), a_q2), FORE: qmul(qinv(a_q2), f_q2), HAND: qmul(qinv(f_q2), hq)}
            for b in tracks:
                l = local(src, b, k) if b not in solved else (a_l if b == ARM else f_l if b == FORE else h_l)
                keys[b][0].append(unreal.Vector(*l[0]))
                keys[b][1].append(unreal.Quat(*(solved[b] if b in solved else l[1])))
                keys[b][2].append(unreal.Vector(*l[2]))
            if f in (0, 12, 16, 27, 39):
                rel = sub(T2, cam)
                vf, vu = dot(rel, fwd), dot(rel, up)
                out.append(f"BH pitch {pitch:+3d} f{f:02d} hand rel cam mesh ({rel[0]:.1f},{rel[1]:.1f},{rel[2]:.1f}) "
                           f"view (ahead {vf:.1f}, up {vu:.1f}) reach {norm(to_t):.1f}/{l1 + l2:.1f}")
    ctrl = seq.get_editor_property("controller")
    ctrl.open_bracket("ImmLoot grab table, empty hands", True)
    ctrl.set_frame_rate(unreal.FrameRate(30, 1), True)
    ctrl.set_number_of_frames(unreal.FrameNumber(total - 1), True)
    for b, (pos, rot, scl) in keys.items():
        ctrl.set_bone_track_keys(b, pos, rot, scl, True)
    ctrl.close_bracket(True)
    for tn in [str(t) for t in AL.get_animation_notify_track_names(seq)]:
        AL.remove_animation_notify_events_by_track(seq, tn)
    # build 11: the hand ended ~(55, +4, -8) in view axes in build 10 whatever the target (planned (39, -13, -11)), as if
    # pulled to a fixed point: suspected the left-hand IK to jnt_weapon. Switch it off at the start of every segment
    # (no "back on": with empty hands that made the hand jump centre-left, build 7).
    track = "ImmLoot"
    if track not in [str(t) for t in AL.get_animation_notify_track_names(seq)]:
        AL.add_animation_notify_track(seq, track, unreal.LinearColor(0.2, 0.8, 0.2, 1.0))
    hik = unreal.load_class(None, "/Script/Stalker2.AnimNotify_HandIK")
    hand_enum = None
    for e in AL.get_animation_notify_events(unreal.load_asset(MONT)):
        if e.notify is not None and e.notify.get_class().get_name() == "AnimNotify_HandIK":
            hand_enum = e.notify.get_editor_property("hand_to_apply")
    for i in range(len(PITCHES)):
        n = AL.add_animation_notify_event(seq, track, i * SEG / 30.0 + 0.02, hik)
        n.set_editor_property("hand_to_apply", hand_enum)
        n.set_editor_property("blend_time", 0.05)
    out.append(f"BH table: {len(PITCHES)} segments x {SEG} frames, len {seq.get_play_length():.2f} s, keys {AL.get_num_keys(seq)}, "
               f"notifies {len(AL.get_animation_notify_events(seq))}, saved {EAL.save_loaded_asset(seq, only_if_is_dirty=False)}")


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
    # build 7: the vanilla grab first dips the hand to the lower left (frames 3-9: 33 cm below the eye) and only then
    # reaches; seen as "the animation plays twice". Now the hand goes straight from the grip to the raised grab
    # point (frames 0-12, eased, the hand rotation blended between the two), holds the vanilla grab (raised) to
    # frame 20, then eases back into the vanilla move to the pocket (frame 27 on unchanged).
    path_h, path_q = [], []
    for k in range(nkeys):
        sh_p, sh_q = cs(src, SHOULDER, k)
        a_l, f_l, h_l = local(src, ARM, k), local(src, FORE, k), local(src, HAND, k)
        a_q = qmul(sh_q, a_l[1]); A = add(sh_p, qrot(sh_q, a_l[0]))
        f_q = qmul(a_q, f_l[1]); E = add(A, qrot(a_q, f_l[0]))
        h_q = qmul(f_q, h_l[1]); H = add(E, qrot(f_q, h_l[0]))
        path_h.append(H); path_q.append(h_q)
    tgt_path, tgt_rot = [], []
    G = add(path_h[W_FULL + 1], OFFSET)
    GQ = path_q[W_FULL + 1]
    for k in range(nkeys):
        sh_p, sh_q = cs(src, SHOULDER, k)
        a_l, f_l, h_l = local(src, ARM, k), local(src, FORE, k), local(src, HAND, k)
        a_q = qmul(sh_q, a_l[1]); A = add(sh_p, qrot(sh_q, a_l[0]))
        f_q = qmul(a_q, f_l[1]); E = add(A, qrot(a_q, f_l[0]))
        h_q = qmul(f_q, h_l[1]); H = add(E, qrot(f_q, h_l[0]))
        w = weight(k)
        if k <= W_FULL + 1:
            u = smooth(k / (W_FULL + 1))
            T = add(path_h[0], mul(sub(G, path_h[0]), u))
            h_q = slerp(path_q[0], GQ, u)
        else:
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
        tgt_path.append(T2)
        tgt_rot.append(h_q)
        if k % 3 == 0:
            out.append(f"k{k:02d} w={w:.2f} hand=({H[0]:.1f},{H[1]:.1f},{H[2]:.1f}) -> ({T2[0]:.1f},{T2[1]:.1f},{T2[2]:.1f}) "
                       f"reach {norm(to_t):.1f}/{l1 + l2:.1f}")
    ctrl = seq.get_editor_property("controller")
    ctrl.open_bracket("ImmLoot raised grab", True)
    for b, (pos, rot, scl) in keys.items():
        ctrl.set_bone_track_keys(b, pos, rot, scl, True)
    ctrl.close_bracket(True)
    # HandIK notifies from the vanilla montage (left hand off the grip at the start, back on before the end)
    for tn in [str(t) for t in AL.get_animation_notify_track_names(seq)]:   # start clean (by name does not match class notifies)
        AL.remove_animation_notify_events_by_track(seq, tn)
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
    if ARGS.get("BH", "1") == "1":
        build_bh_table(src, seq, tgt_rot, nkeys)
except Exception:
    import traceback
    out.append("EXCEPTION " + traceback.format_exc())
os.makedirs(SCRATCH, exist_ok=True)
open(os.path.join(SCRATCH, "make_grab_seq.txt"), "w").write("\n".join(out))
