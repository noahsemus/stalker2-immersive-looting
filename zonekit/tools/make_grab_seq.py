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



ELEVS = list(range(-80, 26, 15))       # elevation of the item seen from the eye, body frame (deg, + = up): 8 bins
DISTS = [30, 45, 60]                   # distance of the item from the eye (cm); 60 = "out of reach": arm fully out
AZIMS = [-45, -30, -15, 0, 15]         # build 13: azimuth of the item in the body frame (deg, + = right). Build 12 aimed
                                       # straight ahead of the body and landed ~15 cm right of the item: the body is
                                       # turned relative to the view, so the item is not dead ahead in the body frame
SEG2 = 45                              # frames per segment (1.5 s); the Blueprint stops it at +1.35 s
BIAS = (9.0, 15.0, 5.0)                # build 15: in game the hand lands this far from the computed point (view frame:
                                       # ahead, right, up; builds 10, 12-14 traces, cause unknown); aim this much short


def build_bh_reach_table(src, rifle_seq, tgt_rot, nkeys, base_path=None, name=None):
    """Build 12 (tester: "what if the hand actually grabs the item, moves to where it is"): segments for every
    (elevation, distance) of the item relative to the eye in the body frame. The hand's item point (jnt_l_weapon) goes
    to the item by frame 12 (as far as the arm reaches, toward it), holds to 20, pocket by 27, rest by 39.
    Segment index = (ie * len(DISTS) + id) * len(AZIMS) + ia; starts at index * 1.5 s."""
    base_path, name = base_path or BASE_BH, name or NAME_BH
    base = unreal.load_asset(base_path)
    sp_p, sp_q = cs(base, "jnt_spine_03", 0)
    cam, _ = cs(base, "jnt_camera", 0)
    cam_ar, _ = cs(src, "jnt_camera", 0)
    ba, bf, bh = local(base, ARM, 0), local(base, FORE, 0), local(base, HAND, 0)
    bsh = local(base, SHOULDER, 0)
    rq_sh = qmul(sp_q, bsh[1]); rp_sh = add(sp_p, qrot(sp_q, bsh[0]))
    rq_a = qmul(rq_sh, ba[1]); RA = add(rp_sh, qrot(rq_sh, ba[0]))
    rq_f = qmul(rq_a, bf[1]); RE = add(RA, qrot(rq_a, bf[0]))
    RQ = qmul(rq_f, bh[1]); R = add(RE, qrot(rq_f, bh[0]))
    POCKET = add(sub((12.4, -8.2, 121.0), cam_ar), cam)
    PQ = tgt_rot[min(27, nkeys - 1)]
    GQ = tgt_rot[13]
    wpn = local(src, "jnt_l_weapon", 13)[0]           # item point, in the hand's frame
    path = f"{DIR}/{name}"
    if not EAL.does_asset_exist(path):
        unreal.AssetToolsHelpers.get_asset_tools().duplicate_asset(name, DIR, rifle_seq)
    seq = unreal.load_asset(path)
    tracks = [str(t) for t in AL.get_animation_track_names(src)]
    cache = {k: {b: local(src, b, k) for b in tracks} for k in range(min(SEG2, nkeys))}
    nseg = len(ELEVS) * len(DISTS) * len(AZIMS)
    fopen, _ = door_fingers(src)                                         # build 26: the use reach's open hand
    frest = {b: local(base, b, 0)[1] for b in FINGERS}                   # the empty-handed rest
    # build 26b (tester: "the hand doesn't clasp down to actually grab the item like it does when using an item"): the
    # grip of a use animation that holds a bottle (water, frame 0: fingers curled 407 deg in all vs 250 for the vanilla
    # grab), closing as the item arrives (it is pulled in at frames 12-16)
    _gs = unreal.load_asset("/Game/_STALKER2/Animations/Player/AnimSequences/Items/Water/AS_fp_water_use")
    fgrip = {b: local(_gs, b, 0)[1] for b in FINGERS}

    def grasp(b, f):
        if f <= 12:
            return slerp(frest[b], fopen[b], finger_open(min(f, 10)))
        if f <= 15:
            return slerp(fopen[b], fgrip[b], smoother((f - 12) / 3))
        if f <= 27:
            return fgrip[b]
        if f <= 39:
            return slerp(fgrip[b], frest[b], smoother((f - 27) / 12))
        return frest[b]
    keys = {b: ([], [], []) for b in tracks}
    for ie, elev in enumerate(ELEVS):
      for dd in DISTS:
        for az in AZIMS:
            er, ar = math.radians(elev), math.radians(az)
            dirv_e = (math.cos(er) * math.cos(ar), math.cos(er) * math.sin(ar), math.sin(er))
            qp = qmul((0.0, 0.0, math.sin(ar / 2), math.cos(ar / 2)), (0.0, -math.sin(er / 2), 0.0, math.cos(er / 2)))
            GQp = qmul(qp, GQ)
            item = add(cam, mul(dirv_e, dd))
            vf = dirv_e
            vu = (-math.sin(er) * math.cos(ar), -math.sin(er) * math.sin(ar), math.cos(er))
            vr = cross(vu, vf)
            bias = add(mul(vf, BIAS[0]), add(mul(vr, BIAS[1]), mul(vu, BIAS[2])))
            G = sub(sub(item, qrot(GQp, wpn)), bias)    # wrist so that the item point sits on the item (minus the bias)
            for f in range(SEG2):
                k = min(f, nkeys - 1)
                if f <= 12:
                    bw, T0, Q0, T1, Q1 = smooth(f / 12), R, RQ, G, GQp
                elif f <= 20:
                    bw, T0, Q0, T1, Q1 = 1.0, G, GQp, G, GQp
                elif f <= 27:
                    bw, T0, Q0, T1, Q1 = smooth((f - 20) / 7), G, GQp, POCKET, PQ
                elif f <= 39:
                    bw, T0, Q0, T1, Q1 = smooth((f - 27) / 12), POCKET, PQ, R, RQ
                else:
                    bw, T0, Q0, T1, Q1 = 1.0, R, RQ, R, RQ
                T = add(T0, mul(sub(T1, T0), bw))
                hq = slerp(Q0, Q1, bw)
                c = cache[min(k, SEG2 - 1)]
                sh_l = c[SHOULDER]
                sh_q = qmul(sp_q, sh_l[1]); sh_p = add(sp_p, qrot(sp_q, sh_l[0]))
                a_l, f_l, h_l = c[ARM], c[FORE], c[HAND]
                a_q = qmul(sh_q, ba[1]); A = add(sh_p, qrot(sh_q, a_l[0]))
                f_q = qmul(a_q, bf[1]); E = add(A, qrot(a_q, f_l[0]))
                H = add(E, qrot(f_q, h_l[0]))
                l1, l2 = norm(sub(E, A)), norm(sub(H, E))
                to_t = sub(T, A)
                d = max(abs(l1 - l2) + 0.01, min(l1 + l2 - 0.01, norm(to_t)))
                dv = unit(to_t)
                a = (l1 * l1 - l2 * l2 + d * d) / (2 * d)
                h = math.sqrt(max(l1 * l1 - a * a, 0.0))
                hint = sub(E, A)
                pole = sub(hint, mul(dv, dot(hint, dv)))
                pole = unit(pole) if norm(pole) > 1e-6 else unit(cross(dv, (0.0, 0.0, 1.0)))
                E2 = add(A, add(mul(dv, a), mul(pole, h)))
                T2 = add(A, mul(dv, d))
                r1 = q_between(sub(E, A), sub(E2, A))
                a_q2 = qmul(r1, a_q)
                r2 = q_between(qrot(r1, sub(H, E)), sub(T2, E2))
                f_q2 = qmul(r2, qmul(r1, f_q))
                solved = {ARM: qmul(qinv(sh_q), a_q2), FORE: qmul(qinv(a_q2), f_q2), HAND: qmul(qinv(f_q2), hq)}
                if not name.endswith("AR"):
                    for b in FINGERS:
                        if b in c:
                            solved[b] = grasp(b, f)
                for b in tracks:
                    l = c[b]
                    keys[b][0].append(unreal.Vector(*l[0]))
                    keys[b][1].append(unreal.Quat(*(solved[b] if b in solved else l[1])))
                    keys[b][2].append(unreal.Vector(*l[2]))
                if f == 12 and dd in (30, 60) and az in (-30, 0) and elev in (-80, -35, 10):
                    got = add(T2, qrot(hq, wpn))
                    out.append(f"elev {elev:+3d} az {az:+3d} dist {dd}: item point at {norm(sub(got, item)):.1f} cm from the item "
                               f"(reach {norm(to_t):.1f}/{l1 + l2:.1f})")
    if name.endswith("AR") and ARGS.get("AR_FROM_RIFLE", "0") == "1":   # build 2026-10-10b; reverted: same result
        rk = {b: [local(rifle_seq, b, min(f, AL.get_num_keys(rifle_seq) - 1)) for f in range(SEG2)] for b in tracks}
        keys = {b: ([], [], []) for b in tracks}
        for i in range(nseg):
            for f in range(SEG2):
                for b in tracks:
                    l = rk[b][f]
                    keys[b][0].append(unreal.Vector(*l[0]))
                    keys[b][1].append(unreal.Quat(*l[1]))
                    keys[b][2].append(unreal.Vector(*l[2]))
        out.append(f"{name}: every segment = the raised rifle grab (frames 0-{SEG2 - 1})")
    total = nseg * SEG2
    ctrl = seq.get_editor_property("controller")
    ctrl.open_bracket("ImmLoot reach table, empty hands", True)
    ctrl.set_frame_rate(unreal.FrameRate(30, 1), True)
    ctrl.set_number_of_frames(unreal.FrameNumber(total - 1), True)
    for b, (pos, rot, scl) in keys.items():
        ctrl.set_bone_track_keys(b, pos, rot, scl, True)
    ctrl.close_bracket(True)
    for tn in [str(t) for t in AL.get_animation_notify_track_names(seq)]:
        AL.remove_animation_notify_events_by_track(seq, tn)
    track = "ImmLoot"
    if track not in [str(t) for t in AL.get_animation_notify_track_names(seq)]:
        AL.add_animation_notify_track(seq, track, unreal.LinearColor(0.2, 0.8, 0.2, 1.0))
    hik = unreal.load_class(None, "/Script/Stalker2.AnimNotify_HandIK")
    hand_enum = None
    for e in AL.get_animation_notify_events(unreal.load_asset(MONT)):
        if e.notify is not None and e.notify.get_class().get_name() == "AnimNotify_HandIK":
            hand_enum = e.notify.get_editor_property("hand_to_apply")
    # left-hand IK off, repeated through every segment (build 14: builds 10, 12, 13 all ended ~15 cm right of the
    # planned point whatever the target, as if still pulled to the grip; a single "off" at the start may be undone)
    for i in range(nseg):
        if not name.endswith("AR") and ARGS.get("IKREACH", "1") == "1":
            # build 36: the game's left-hand IK steers the hand onto the target (the Blueprint moves the weapon mesh's
            # hand socket there): on, blending in over 0.3 s, from frame 2; off, blending out, at frame 28 (the pocket)
            for t, end, bl in ((0.0, None, 0.05), (0.07, 1.0, 0.3), (0.93, None, 0.25)):
                n = AL.add_animation_notify_event(seq, track, i * SEG2 / 30.0 + t, hik)
                n.set_editor_property("hand_to_apply", hand_enum)
                n.set_editor_property("blend_time", bl)
                if end is not None:
                    n.set_editor_property("end_value", end)
            continue
        for t in (0.02, 0.15, 0.3, 0.45, 0.6, 0.75, 0.9, 1.05, 1.2):
            n = AL.add_animation_notify_event(seq, track, i * SEG2 / 30.0 + t, hik)
            n.set_editor_property("hand_to_apply", hand_enum)
            n.set_editor_property("blend_time", 0.05)
    if name.endswith("AR"):
        # Built like the game's own left-hand gestures over a rifle (MG_fp_ar_flashlight): the curve left_hand_curve
        # 0 -> 1 in 0.17 s, held, back to 0, and "left-hand IK off" at the start. Rifle trace (2026-10-10): during the
        # touch the hand bone did not move at all (41, 3, -13 in view axes the whole time) although our montage was
        # playing in LeftHand: without the curve the slot's pose is not used over a rifle.
        cname = "left_hand_curve"
        if cname in [str(c) for c in AL.get_animation_curve_names(seq, unreal.RawCurveTrackTypes.RCT_FLOAT)]:
            AL.remove_curve(seq, cname, False)
        AL.add_curve(seq, cname, unreal.RawCurveTrackTypes.RCT_FLOAT, False)
        times, vals = [], []
        for i in range(nseg):
            t0 = i * SEG2 / 30.0
            for f, v in ((0, 0.0), (5, 1.0), (34, 1.0), (39, 0.0), (SEG2 - 1, 0.0)):
                times.append(t0 + f / 30.0)
                vals.append(v)
        AL.add_float_curve_keys(seq, cname, times, vals)
        for tn in [str(t) for t in AL.get_animation_notify_track_names(seq)]:
            AL.remove_animation_notify_events_by_track(seq, tn)
        if track not in [str(t) for t in AL.get_animation_notify_track_names(seq)]:
            AL.add_animation_notify_track(seq, track, unreal.LinearColor(0.2, 0.8, 0.2, 1.0))
        for i in range(nseg):
            n = AL.add_animation_notify_event(seq, track, i * SEG2 / 30.0 + 0.0085, hik)
            n.set_editor_property("hand_to_apply", hand_enum)
            n.set_editor_property("blend_time", 0.3)
        out.append(f"{name}: left_hand_curve ({len(times)} keys) + IK off at each segment start (like the flashlight)")
    out.append(f"{name} reach table (base {base_path.rsplit('/', 1)[1]}): {len(ELEVS)} elevations x {len(DISTS)} distances x {len(AZIMS)} azimuths x {SEG2} frames, len {seq.get_play_length():.2f} s, "
               f"notifies {len(AL.get_animation_notify_events(seq))}, saved {EAL.save_loaded_asset(seq, only_if_is_dirty=False)}")


NAME_TOUCH = "AS_ImmLoot_Touch"
TOUCH_ELEVS = [-45, -30, -15, 0, 15]   # direction of the body's / stash's centre seen from the camera, in VIEW axes
TOUCH_AZIMS = [-30, -15, 0, 15, 30]    # (= the camera-bone frame of the sequence with a weapon in hand); asset
                                       # AS_ImmLoot_Touch<ie * 5 + ia>, nearest bin, clamped
# Where the hand bone lands in VIEW axes for a planned position relative to the camera bone (builds c, d, e: three
# points): ahead + 8.4, right x 1.14 + 4.0, up x 1.15 + 2.0 (the sideways scale ~ the arms' FOV squeeze)
TOUCH_MAP = ((1.0, 8.4), (1.14, 4.0), (1.15, 2.0))
TOUCH_REACH = 0.95                     # of the arm length: fully out, not locked straight


DOOR_ELEV, DOOR_AZIM = -20.0, -22.0   # doors (tester): the hand stays in the lower left of the screen, one fixed direction
DOOR_PUSH_STROKE, DOOR_PULL_STROKE, DOOR_PULL_DROP = 14.0, 18.0, 10.0


FINGERS = [f"jnt_l_hand_{n}" for n in ("thumb_01", "thumb_02", "thumb_03", "index_meta", "index_01", "index_02", "index_03",
                                         "middle_meta", "middle_01", "middle_02", "middle_03", "ring_meta", "ring_01", "ring_02",
                                         "ring_03", "pinky_meta", "pinky_01", "pinky_02", "pinky_03")]
OPEN_SEQ = "/Game/_STALKER2/Animations/Player/AnimSequences/Dialog_animations/AS_fp_dialogue_openhands_expressive"
OPEN_K, FIST_K = 36, 17          # an open, spread left hand (dialogue gesture); the vanilla grab's closed hand


def door_fingers(src):
    """(tester, build 10: "it looks like poking the door; the fingers should be out, spread, pushing; for closing the hand
    goes out, makes a fist as if grabbing, and pulls"): open and fist finger rotations (left hand locals)."""
    op = unreal.load_asset(OPEN_SEQ)
    opens = {b: local(op, b, OPEN_K)[1] for b in FINGERS}
    for j in ("01", "02", "03"):        # builds 11 / 16: "ring finger and pinky still not up": straight like the middle finger
        opens[f"jnt_l_hand_ring_{j}"] = opens[f"jnt_l_hand_middle_{j}"]
        opens[f"jnt_l_hand_pinky_{j}"] = opens[f"jnt_l_hand_middle_{j}"]
    return (opens, {b: local(src, b, FIST_K)[1] for b in FINGERS})


def finger_w(mode, f):
    """(open weight, fist weight) at frame f. Push: open from 10, through the stroke, relaxed by 48. Pull: open by 12,
    a fist at the door 14-20, held through the pull, relaxed by 50."""
    ramp = lambda a, b: min(1.0, max(0.0, (f - a) / float(b - a)))
    if mode == "push":      # build 23: open by 6 (the stroke starts there)
        return (smooth(ramp(0, 6)) * (1.0 - smooth(ramp(26, 40))), 0.0)
    # build 23: the pull's schedule moved (at the handle by 8, held at 12, drawn back 12-26) and the fist came at 14-20,
    # after the pull had started: open 0-5, a fist 5-9 (grabbing the handle), held through the pull, relaxed by 42
    return (smooth(ramp(0, 5)), smooth(ramp(5, 9)) * (1.0 - smooth(ramp(28, 42))))


def finger_q(rest_q, opens, fists, b, wo, wf):
    return slerp(slerp(rest_q, opens[b], wo), fists[b], wf)


def palm_q(src, facing):
    """A hand rotation (component / sequence space) with the palm toward `facing` and the fingers up: the push."""
    hp, hq0 = cs(src, HAND, FIST_K)
    loc = lambda b: qrot(qinv(hq0), unit(sub(cs(src, b, FIST_K)[0], hp)))
    f_l = loc("jnt_l_hand_middle_01")                                   # finger direction, hand-local
    lat = qrot(qinv(hq0), unit(sub(cs(src, "jnt_l_hand_index_01", FIST_K)[0], cs(src, "jnt_l_hand_pinky_01", FIST_K)[0])))
    palm_l = unit(cross(f_l, lat))
    if dot(qrot(hq0, palm_l), (1.0, 0.0, 0.0)) < 0:                    # the grab's palm faces the item (forward)
        palm_l = mul(palm_l, -1.0)
    q1 = q_between(palm_l, unit(facing))
    f1 = qrot(q1, f_l)
    up0 = unit(add((0.0, 0.0, 1.0), mul(unit(facing), 0.8)))          # build 11: fingers up AND forward (less tall on screen)
    up = unit(sub(up0, mul(unit(facing), dot(up0, unit(facing)))))
    f1p = unit(sub(f1, mul(unit(facing), dot(f1, unit(facing)))))
    return qmul(q_between(f1p, up), q1)


def door_sched(mode, R, N, G, PB):
    """(from frame, to frame, from point, to point), 30 fps. Push: out to just short of the door by 14, a 0.4 s forward
    stroke 14-26 (the Blueprint pauses at 26 = 0.867 s), held to 30, back by 48. Pull: out to the door by 16, held to 22
    (pause at 22 = 0.733 s), drawn back and down 22-36, back to rest by 50."""
    if mode == "push":      # build 15 (tester: "plays mostly after the door opened"): out by 6, stroke 6-14 (pause at 14)
        return ((0, 6, R, N), (6, 14, N, G), (14, 18, G, G), (18, 38, G, R))
    return ((0, 8, R, G), (8, 12, G, G), (12, 26, G, PB), (26, 42, PB, R))   # pull: at the door by 8 (pause at 12)   # cm along the sight line


DOOR_ROLL = 20.0                                                 # build 23: deg, the hand turned to the right
DOOR_BH_ELEV, DOOR_BH_AZIM, DOOR_BH_DIST = -30.0, -30.0, 34.0   # the shoulder is ~19 cm behind the eye: 52 cm of arm reaches ~30 cm ahead   # body frame, from the eye


def build_bh_door(src, rifle_seq, tgt_rot, nkeys, mode, name):
    """Empty hands (build 9, tester: "no difference between open and close" unarmed: the reach table segment was used):
    the reach-table solve (body frame, BH idle rest pose) with the door schedule, one 50-frame segment."""
    NF = 51
    base = unreal.load_asset(BASE_BH)
    sp_p, sp_q = cs(base, "jnt_spine_03", 0)
    cam, _ = cs(base, "jnt_camera", 0)
    ba, bf, bh = local(base, ARM, 0), local(base, FORE, 0), local(base, HAND, 0)
    bsh = local(base, SHOULDER, 0)
    rq_sh = qmul(sp_q, bsh[1]); rp_sh = add(sp_p, qrot(sp_q, bsh[0]))
    rq_a = qmul(rq_sh, ba[1]); RA = add(rp_sh, qrot(rq_sh, ba[0]))
    rq_f = qmul(rq_a, bf[1]); RE = add(RA, qrot(rq_a, bf[0]))
    RQ = qmul(rq_f, bh[1]); R = add(RE, qrot(rq_f, bh[0]))
    er, ar = math.radians(DOOR_BH_ELEV), math.radians(DOOR_BH_AZIM)
    vf = (math.cos(er) * math.cos(ar), math.cos(er) * math.sin(ar), math.sin(er))
    qp = qmul((0.0, 0.0, math.sin(ar / 2), math.cos(ar / 2)), (0.0, -math.sin(er / 2), 0.0, math.cos(er / 2)))
    GQ = slerp(qmul(qp, tgt_rot[13]), palm_q(src, vf), 0.5) if mode == "push" else qmul(qp, tgt_rot[13])
    th = math.radians(-DOOR_ROLL) / 2                    # build 23: turned clockwise (as seen from behind) about the reach
    GQ = qmul((vf[0] * math.sin(th), vf[1] * math.sin(th), vf[2] * math.sin(th), math.cos(th)), GQ)
    opens, fists = door_fingers(src)
    G = add(cam, mul(vf, DOOR_BH_DIST))
    N = sub(G, mul(vf, DOOR_PUSH_STROKE))
    PB = sub(sub(G, mul(vf, DOOR_PULL_STROKE)), (0.0, 0.0, DOOR_PULL_DROP))
    sched = door_sched(mode, R, N, G, PB)
    path = f"{DIR}/{name}"
    if not EAL.does_asset_exist(path):
        unreal.AssetToolsHelpers.get_asset_tools().duplicate_asset(name, DIR, rifle_seq)
    seq = unreal.load_asset(path)
    tracks = [str(tr) for tr in AL.get_animation_track_names(src)]
    cache = {k: {b: local(src, b, k) for b in tracks} for k in range(min(NF, nkeys))}
    keys = {b: ([], [], []) for b in tracks}
    for f in range(NF):
        k = min(f, nkeys - 1)
        bw, T0, Q0, T1, Q1 = 1.0, R, RQ, R, RQ
        for f0, f1, P0, P1 in sched:
            if f0 <= f <= f1:
                bw, T0, T1 = smooth((f - f0) / max(f1 - f0, 1)), P0, P1
                Q0, Q1 = (RQ if P0 is R else GQ), (RQ if P1 is R else GQ)
                break
        T = add(T0, mul(sub(T1, T0), bw))
        hq = slerp(Q0, Q1, bw)
        c = cache[0]          # the rest pose throughout (the vanilla grab's shoulder moves back 6 cm at frames 20-30)
        sh_l = c[SHOULDER]
        sh_q = qmul(sp_q, sh_l[1]); sh_p = add(sp_p, qrot(sp_q, sh_l[0]))
        a_l, f_l, h_l = c[ARM], c[FORE], c[HAND]
        a_q = qmul(sh_q, ba[1]); A = add(sh_p, qrot(sh_q, a_l[0]))
        f_q = qmul(a_q, bf[1]); E = add(A, qrot(a_q, f_l[0]))
        H = add(E, qrot(f_q, h_l[0]))
        l1, l2 = norm(sub(E, A)), norm(sub(H, E))
        to_t = sub(T, A)
        d = max(abs(l1 - l2) + 0.01, min((l1 + l2) * 0.97, norm(to_t)))
        dv = unit(to_t)
        a = (l1 * l1 - l2 * l2 + d * d) / (2 * d)
        h = math.sqrt(max(l1 * l1 - a * a, 0.0))
        hint = sub(E, A)
        pole = sub(hint, mul(dv, dot(hint, dv)))
        pole = unit(pole) if norm(pole) > 1e-6 else unit(cross(dv, (0.0, 0.0, 1.0)))
        E2 = add(A, add(mul(dv, a), mul(pole, h)))
        T2 = add(A, mul(dv, d))
        r1 = q_between(sub(E, A), sub(E2, A))
        a_q2 = qmul(r1, a_q)
        r2 = q_between(qrot(r1, sub(H, E)), sub(T2, E2))
        f_q2 = qmul(r2, qmul(r1, f_q))
        solved = {ARM: qmul(qinv(sh_q), a_q2), FORE: qmul(qinv(a_q2), f_q2), HAND: qmul(qinv(f_q2), hq)}
        wo, wf = finger_w(mode, f)
        for b in FINGERS:
            if b in c:
                solved[b] = finger_q(c[b][1], opens, fists, b, wo, wf)
        for b in tracks:
            l = c[b]
            keys[b][0].append(unreal.Vector(*l[0]))
            keys[b][1].append(unreal.Quat(*(solved[b] if b in solved else l[1])))
            keys[b][2].append(unreal.Vector(*l[2]))
        if f in (14, 16, 26, 36):
            out.append(f"BHDOOR {name} f{f} hand rel eye {tuple(round(x, 1) for x in sub(T2, cam))} target {tuple(round(x, 1) for x in sub(T, cam))} need {norm(to_t):.1f} reach {l1 + l2:.1f} shoulder {tuple(round(x, 1) for x in sub(A, cam))}")
    ctrl = seq.get_editor_property("controller")
    ctrl.open_bracket("ImmLoot door, empty hands", True)
    ctrl.set_frame_rate(unreal.FrameRate(30, 1), True)
    ctrl.set_number_of_frames(unreal.FrameNumber(NF - 1), True)
    for b, (pos, rot, scl) in keys.items():
        ctrl.set_bone_track_keys(b, pos, rot, scl, True)
    ctrl.close_bracket(True)
    for tn in [str(x) for x in AL.get_animation_notify_track_names(seq)]:
        AL.remove_animation_notify_events_by_track(seq, tn)
    track = "ImmLoot"
    if track not in [str(x) for x in AL.get_animation_notify_track_names(seq)]:
        AL.add_animation_notify_track(seq, track, unreal.LinearColor(0.2, 0.8, 0.2, 1.0))
    hik = unreal.load_class(None, "/Script/Stalker2.AnimNotify_HandIK")
    hand_enum = None
    for e in AL.get_animation_notify_events(unreal.load_asset(MONT)):
        if e.notify is not None and e.notify.get_class().get_name() == "AnimNotify_HandIK":
            hand_enum = e.notify.get_editor_property("hand_to_apply")
    for tt in (0.02, 0.3, 0.6, 0.9, 1.2, 1.5):
        n = AL.add_animation_notify_event(seq, track, tt, hik)
        n.set_editor_property("hand_to_apply", hand_enum)
        n.set_editor_property("blend_time", 0.05)
    for cn in [str(x) for x in AL.get_animation_curve_names(seq, unreal.RawCurveTrackTypes.RCT_FLOAT)]:
        AL.remove_curve(seq, cn, False)
    out.append(f"BHDOOR {name}: len {seq.get_play_length():.2f} s, saved {EAL.save_loaded_asset(seq, only_if_is_dirty=False)}")


def build_doors(src, grab, path_h, path_q, nkeys, tgt_rot=None):
    """1.1 doors (tester: opening = a push, closing = a pull; the hand in the lower left quadrant, not toward the
    door): AS_ImmLoot_DoorPush / AS_ImmLoot_DoorPull, the touch asset form with their own schedules."""
    build_touch_one(src, grab, path_h, path_q, nkeys, "AS_ImmLoot_DoorPush", DOOR_ELEV, DOOR_AZIM, "push")
    build_touch_one(src, grab, path_h, path_q, nkeys, "AS_ImmLoot_DoorPull", DOOR_ELEV, DOOR_AZIM, "pull")
    if tgt_rot is not None:
        build_bh_door(src, grab, tgt_rot, nkeys, "push", "AS_ImmLoot_DoorPushBH")
        build_bh_door(src, grab, tgt_rot, nkeys, "pull", "AS_ImmLoot_DoorPullBH")


def build_touch(src, grab, path_h, path_q, nkeys):
    """With a weapon in hand the whole arm rig follows the view (the weapon layer pitches jnt_spine_03 with the
    look-vertical additive), so a hand position relative to the camera bone in the sequence IS its position in view
    axes in game (builds c, d: planned (42.9,-10.4,-45.7) / (42.3,-7.5,-42.9) rel camera bone, measured
    (51.6,-7.8,-50.6) / (50.7,-5.2,-48.0) in view axes whatever the view pitch, -48.6 deg in build d). Empty hands
    differ (the bh layer leaves the arms in the body frame: the BH table bins by pitch). So: ONE asset, the hand on
    the sight line as far as the arm reaches, 8 cm left of it (TOUCH_AZIM, minus the bias)."""
    for ie, elev in enumerate(TOUCH_ELEVS):
        for ia, az in enumerate(TOUCH_AZIMS):
            build_touch_one(src, grab, path_h, path_q, nkeys, f"{NAME_TOUCH}{ie * len(TOUCH_AZIMS) + ia}", float(elev), float(az))


def build_touch_one(src, grab, path_h, path_q, nkeys, name, TOUCH_ELEV, TOUCH_AZIM, mode="touch"):
    """2026-10-10, corpse / stash touch with a weapon: the same asset form as AS_ImmLoot_Grab (a copy of the vanilla
    grab, only the left arm re-solved, played from 0), which shows over a rifle, where the 180 s reach table never did
    (tester: "reaches a little, then stuck"; trace: the hand never left the grip). The hand goes from the grip straight
    to a point TOUCH_DIST cm from the eye at TOUCH_ELEV / TOUCH_AZIM in the body frame (as far as the arm reaches) by
    frame 12, holds to 20 (the Blueprint pauses it at 0.6 s while the loot window is open), and comes straight back to
    the grip by frame 36, where the vanilla "left hand back on" IK notify takes over. Carries left_hand_curve like the
    game's own left-hand gestures (MG_fp_ar_flashlight): rifles with an underbarrel idle (WeaponUnderbarrelIdleLayer,
    weight LeftHandCurveValueInverse) replace the slot's left arm unless the curve is 1."""
    cam, _ = cs(src, "jnt_camera", 0)
    er, ar = math.radians(TOUCH_ELEV), math.radians(TOUCH_AZIM)
    dirv_e = (math.cos(er) * math.cos(ar), math.cos(er) * math.sin(ar), math.sin(er))
    # the farthest point of the sight line the arm reaches (shoulder and arm length at the reach frame)
    sh_p12, sh_q12 = cs(src, SHOULDER, 12)
    a12, f12, h12 = local(src, ARM, 12), local(src, FORE, 12), local(src, HAND, 12)
    A12 = add(sh_p12, qrot(sh_q12, a12[0]))
    aq12 = qmul(sh_q12, a12[1]); E12 = add(A12, qrot(aq12, f12[0]))
    H12 = add(E12, qrot(qmul(aq12, f12[1]), h12[0]))
    reach = (norm(sub(E12, A12)) + norm(sub(H12, E12))) * TOUCH_REACH
    # the landing point V = cam + dir * t (view axes); the plan P = cam + (V - cam - T) / S per axis (TOUCH_MAP);
    # solve t so the planned hand is `reach` from the shoulder
    inv = lambda v: tuple((v[i] - TOUCH_MAP[i][1]) / TOUCH_MAP[i][0] for i in range(3))
    u = tuple(dirv_e[i] / TOUCH_MAP[i][0] for i in range(3))
    c_ = sub(add(cam, inv((0.0, 0.0, 0.0))), A12)
    qa, qb, qc = dot(u, u), 2 * dot(c_, u), dot(c_, c_) - reach * reach
    disc = qb * qb - 4 * qa * qc
    t = (-qb + math.sqrt(disc)) / (2 * qa) if disc > 0 else max(10.0, -qb / (2 * qa))
    G = add(cam, inv(mul(dirv_e, t)))
    qp = qmul((0.0, 0.0, math.sin(ar / 2), math.cos(ar / 2)), (0.0, -math.sin(er / 2), 0.0, math.cos(er / 2)))
    GQ = qmul(qp, path_q[W_FULL + 1])
    R, RQ = path_h[0], path_q[0]
    back = unit(sub(G, cam))
    # build 7 (tester: "goes up to the left and off the top"): the stroke points stay near the door point; the old ones
    # (22 / 30 cm back along the sight line) put the hand a hand-span from the eye, high on the screen
    N = sub(G, mul(back, DOOR_PUSH_STROKE))            # push: the hand stops a little short, then strokes forward to G
    PB = sub(sub(G, mul(back, DOOR_PULL_STROKE)), (0.0, 0.0, DOOR_PULL_DROP))   # pull: back and down toward the chest
    out.append(f"TOUCH {name}: elev {TOUCH_ELEV:+.0f} az {TOUCH_AZIM:+.0f}, lands {t:.1f} cm from the eye, plan rel cam {tuple(round(x, 1) for x in sub(G, cam))}")
    path = f"{DIR}/{name}"
    if not EAL.does_asset_exist(path):
        unreal.AssetToolsHelpers.get_asset_tools().duplicate_asset(name, DIR, grab)
    seq = unreal.load_asset(path)
    keys = {b: ([], [], []) for b in (ARM, FORE, HAND)}
    # (from frame, to frame, from point, to point): the Blueprint pauses at 0.6 s (frame 18) for DoorHold / the window
    sched = door_sched(mode, R, N, G, PB) if mode in ("push", "pull") else ((0, 12, R, G), (12, 20, G, G), (20, 36, G, R))
    if mode == "push":      # build 15 (tester: "like breaking his wrist"): half way from the grab's hand to palm-forward
        GQ = slerp(GQ, palm_q(src, dirv_e), 0.5)
    if mode in ("push", "pull"):
        opens, fists = door_fingers(src)
        for b in FINGERS:
            keys[b] = ([], [], [])
    qof = lambda P: RQ if P is R else GQ
    for k in range(nkeys):
        bw, T0, Q0, T1, Q1 = 1.0, R, RQ, R, RQ
        for f0, f1, P0, P1 in sched:
            if f0 <= k <= f1:
                bw, T0, Q0, T1, Q1 = smooth((k - f0) / max(f1 - f0, 1)), P0, qof(P0), P1, qof(P1)
                break
        T = add(T0, mul(sub(T1, T0), bw))
        hq = slerp(Q0, Q1, bw)
        sh_p, sh_q = cs(src, SHOULDER, k)
        a_l, f_l, h_l = local(src, ARM, k), local(src, FORE, k), local(src, HAND, k)
        a_q = qmul(sh_q, a_l[1]); A = add(sh_p, qrot(sh_q, a_l[0]))
        f_q = qmul(a_q, f_l[1]); E = add(A, qrot(a_q, f_l[0]))
        H = add(E, qrot(f_q, h_l[0]))
        l1, l2 = norm(sub(E, A)), norm(sub(H, E))
        to_t = sub(T, A)
        d = max(abs(l1 - l2) + 0.01, min((l1 + l2) * TOUCH_REACH, norm(to_t)))
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
        for b, lq, l in ((ARM, qmul(qinv(sh_q), a_q2), a_l), (FORE, qmul(qinv(a_q2), f_q2), f_l), (HAND, qmul(qinv(f_q2), hq), h_l)):
            keys[b][0].append(unreal.Vector(*l[0]))
            keys[b][1].append(unreal.Quat(*lq))
            keys[b][2].append(unreal.Vector(*l[2]))
        if mode in ("push", "pull"):
            wo, wf = finger_w(mode, k)
            for b in FINGERS:
                l = local(src, b, k)
                keys[b][0].append(unreal.Vector(*l[0]))
                keys[b][1].append(unreal.Quat(*finger_q(l[1], opens, fists, b, wo, wf)))
                keys[b][2].append(unreal.Vector(*l[2]))
        if k in (12,):
            rel = sub(T2, cam)
            out.append(f"TOUCH {name} k{k:02d} hand rel cam ({rel[0]:.1f},{rel[1]:.1f},{rel[2]:.1f}) reach {min(norm(to_t), (l1 + l2) * TOUCH_REACH):.1f}/{l1 + l2:.1f}")
    ctrl = seq.get_editor_property("controller")
    ctrl.open_bracket("ImmLoot touch", True)
    for b, (pos, rot, scl) in keys.items():
        ctrl.set_bone_track_keys(b, pos, rot, scl, True)
    ctrl.close_bracket(True)
    for tn in [str(t) for t in AL.get_animation_notify_track_names(seq)]:
        AL.remove_animation_notify_events_by_track(seq, tn)
    track = "ImmLoot"
    if track not in [str(t) for t in AL.get_animation_notify_track_names(seq)]:
        AL.add_animation_notify_track(seq, track, unreal.LinearColor(0.2, 0.8, 0.2, 1.0))
    hand = None
    for e in AL.get_animation_notify_events(unreal.load_asset(MONT)):
        if e.notify is not None and e.notify.get_class().get_name() == "AnimNotify_HandIK":
            hand = e.notify.get_editor_property("hand_to_apply")
    hik = unreal.load_class(None, "/Script/Stalker2.AnimNotify_HandIK")
    for t, end in ((0.035907, None), ({"push": 1.27, "pull": 1.4}.get(mode, 1.2), 1.0)):
        new = AL.add_animation_notify_event(seq, track, t, hik)
        new.set_editor_property("hand_to_apply", hand)
        if end is not None:
            new.set_editor_property("end_value", end)
    cname = "left_hand_curve"
    if cname in [str(c) for c in AL.get_animation_curve_names(seq, unreal.RawCurveTrackTypes.RCT_FLOAT)]:
        AL.remove_curve(seq, cname, False)
    AL.add_curve(seq, cname, unreal.RawCurveTrackTypes.RCT_FLOAT, False)
    AL.add_float_curve_keys(seq, cname, [0.0, 0.17, 1.1, 1.3, seq.get_play_length()], [0.0, 1.0, 1.0, 0.0, 0.0])
    out.append(f"TOUCH {name}: len {seq.get_play_length():.2f} s, notifies {len(AL.get_animation_notify_events(seq))}, "
               f"curves {[str(c) for c in AL.get_animation_curve_names(seq, unreal.RawCurveTrackTypes.RCT_FLOAT)]}, "
               f"saved {EAL.save_loaded_asset(seq, only_if_is_dirty=False)}")


# 1.1 build 17, hold F to use (tester: "the prompt fills completely, our grab plays as if the item is looted, then the
# vanilla use"). The game's use animation (MainActionSlot) is paused on its first frame while our reach plays in the
# FullBody slot, which the player AnimBP evaluates after every arm layer, slot, IK and "left hand busy" switch
# (2026-10-11 slot-order study of AnimBP_Player / _player_bh / _PlayerWeaponLayer). FullBody as a full pose took the
# camera (build 10); as a LOCAL-SPACE ADDITIVE keyed only on the left upper arm, forearm and hand (every other bone has
# no track = no change; base = this asset's own frame 0) the camera and the body stay the game's. The arm is solved on
# each use animation's own first frame (spine, shoulder, rest arm: they differ per item, hand 6-31 cm ahead, 27-67 cm
# below the eye), so one table per vanilla use montage: AS_ImmLoot_<montage name>, picked by name at run time;
# AS_ImmLoot_UseAny (canned food's frame) for any other (Project Itemization Reborn's AM_fp_PIR_*).
# Same segments as AS_ImmLoot_GrabBH (elevation x distance x azimuth of the item seen from the eye, 45 frames each).
USE_DIR = f"{DIR}/Use"
USE_MONTS = ["Antirad/MG_fp_antirad_use", "Bandage/MG_fp_bandage_use", "Beer/MG_fp_beer_use", "Bread/MG_fp_bread_use",
             "CannedFood/MG_fp_canned_food_use", "CannedMilk/MG_fp_condensed_milk_use", "EnergyDrink/MG_fp_energy_drink_use",
             "Medkit/MG_fp_medkit_common_use", "Pills/MG_fp_pills_common_use", "Sausage/MG_fp_sausage_use",
             "Vodka/MG_fp_vodka_use", "Water/MG_fp_water_use"]
USE_ROOT = "/Game/_STALKER2/Animations/Player/AnimSequences/Items/"


ARC_OUT = (0.0, -3.0, 6.0)     # build 22: the hand's path bulges up (and a little left) on the way out / back (cm, view axes)
ARC_BACK = (0.0, -2.0, 3.0)


def smoother(x):
    x = max(0.0, min(1.0, x))
    return x * x * x * (x * (6 * x - 15) + 10)


def finger_open(f):
    """0 = the use animation's grip, 1 = open and spread: opening on the way out, closing on the item at the grab."""
    if f <= 2 or f >= 13:
        return 0.0
    if f <= 8:
        return smoother((f - 2) / 6)
    if f <= 10:
        return 1.0
    return 1.0 - smoother((f - 10) / 3)


def build_use_table(src, tgt_rot, nkeys, base, name, template, out_dir=None, lower_deg=0.0, max_dist=None, grip_seq=None, azims=None, finger_base=None, hand_roll=0.0):
    azims_ = azims or AZIMS
    sp_p, sp_q = cs(base, "jnt_spine_03", 0)
    cam, _ = cs(base, "jnt_camera", 0)
    cam_ar, _ = cs(src, "jnt_camera", 0)
    bsh, ba, bf, bh = local(base, SHOULDER, 0), local(base, ARM, 0), local(base, FORE, 0), local(base, HAND, 0)
    sh_q = qmul(sp_q, bsh[1]); sh_p = add(sp_p, qrot(sp_q, bsh[0]))      # the shoulder stays the paused frame's
    a_q0 = qmul(sh_q, ba[1]); A = add(sh_p, qrot(sh_q, ba[0]))
    f_q0 = qmul(a_q0, bf[1]); E = add(A, qrot(a_q0, bf[0]))
    RQ = qmul(f_q0, bh[1]); R = add(E, qrot(f_q0, bh[0]))
    H = R
    l1, l2 = norm(sub(E, A)), norm(sub(H, E))
    POCKET = add(sub((12.4, -8.2, 121.0), cam_ar), cam)
    PQ = tgt_rot[min(27, nkeys - 1)]
    GQ = tgt_rot[13]
    wpn = local(src, "jnt_l_weapon", 13)[0]
    keys = {b: ([], [], []) for b in (ARM, FORE, HAND)}
    errs = []
    fopen, _ = door_fingers(src)                        # an open, spread hand on the way out
    tracks_b = [str(t) for t in AL.get_animation_track_names(base)]
    fbase = {b: local(finger_base or base, b, 0) for b in FINGERS if b in tracks_b}   # build 44: crouched, the standing rest fingers   # the use animation's own grip (holds the item)
    fk = {b: ([], [], []) for b in fbase}
    fgrip_ = {b: local(grip_seq, b, 0)[1] for b in FINGERS} if grip_seq not in (None, "src") else None
    out.append(f"{name}: table arm root (from the eye) {tuple(round(x - c, 2) for x, c in zip(A, cam))} abs {tuple(round(x, 2) for x in A)}, reach {l1 + l2:.2f}")
    for ie, elev in enumerate(ELEVS):
      for dd in DISTS:
        for az in azims_:
            er, ar = math.radians(elev), math.radians(az)
            dirv_e = (math.cos(er) * math.cos(ar), math.cos(er) * math.sin(ar), math.sin(er))
            qp = qmul((0.0, 0.0, math.sin(ar / 2), math.cos(ar / 2)), (0.0, -math.sin(er / 2), 0.0, math.cos(er / 2)))
            GQp = qmul(qp, GQ)
            if hand_roll:                      # build 45: the hand turned about the reach direction (- = clockwise from behind)
                th = math.radians(hand_roll) / 2
                GQp = qmul((dirv_e[0] * math.sin(th), dirv_e[1] * math.sin(th), dirv_e[2] * math.sin(th), math.cos(th)), GQp)
            item = add(cam, mul(dirv_e, dd))
            if lower_deg or max_dist:          # build 30, the pickup table: where the use reach's hand ends
                el2 = er - math.radians(lower_deg)
                item = add(cam, mul((math.cos(el2) * math.cos(ar), math.cos(el2) * math.sin(ar), math.sin(el2)), min(dd, max_dist or dd)))
            vf = dirv_e
            vu = (-math.sin(er) * math.cos(ar), -math.sin(er) * math.sin(ar), math.cos(er))
            vr = cross(vu, vf)
            bias = (0.0, 0.0, 0.0)   # build 20: none (build 19 landed exactly where aimed)
            G = sub(sub(item, qrot(GQp, wpn)), bias)
            for f in range(SEG2):
                if f <= 12:                     # out: eased, arcing up and out, the wrist turning ahead of the arm
                    bw = smoother(f / 12)
                    T = add(add(R, mul(sub(G, R), bw)), mul(ARC_OUT, math.sin(math.pi * bw)))
                    hq = slerp(RQ, GQp, smoother(min(1.0, f / 9)))
                elif f <= 16:                   # the grip settles
                    T, hq = G, GQp
                elif f <= 39:                   # back with it to the use animation's pose, eased, a small arc
                    bw = smoother((f - 16) / 23)
                    T = add(add(G, mul(sub(R, G), bw)), mul(ARC_BACK, math.sin(math.pi * bw)))
                    hq = slerp(GQp, RQ, smoother(min(1.0, (f - 16) / 20)))
                else:
                    T, hq = R, RQ
                fo = finger_open(f)
                for b in FINGERS:
                    if b not in fbase:
                        continue
                    if grip_seq == "src":       # build 42 (tester: "go back to the 1.0.0 version of the hand closing"):
                        # the vanilla grab's own fingers frame by frame, blended in from / out to the rest fingers (build 43:
                        # frame 0 must BE the rest fingers - the additive's reference - or every finger twists: "spaghetti")
                        wf = smoother(f / 4) if f < 4 else (1.0 if f <= 34 else 1.0 - smoother((f - 34) / 8))
                        fq = slerp(fbase[b][1], local(src, b, min(f, nkeys - 1))[1], wf)
                    elif grip_seq is None:
                        fq = slerp(fbase[b][1], fopen[b], fo)
                    elif f <= 10:                 # build 38 pickup: rest -> open, closing onto the item at the grab,
                        fq = slerp(fbase[b][1], fopen[b], fo)          # held until the hand is down again
                    elif f <= 13:
                        fq = slerp(fopen[b], fgrip_[b], smoother((f - 10) / 3))
                    elif f <= 34:
                        fq = fgrip_[b]
                    elif f <= 42:
                        fq = slerp(fgrip_[b], fbase[b][1], smoother((f - 34) / 8))
                    else:
                        fq = fbase[b][1]
                    fk[b][1].append(unreal.Quat(*fq))
                to_t = sub(T, A)
                d = max(abs(l1 - l2) + 0.01, min(l1 + l2 - 0.01, norm(to_t)))
                dv = unit(to_t)
                a = (l1 * l1 - l2 * l2 + d * d) / (2 * d)
                h = math.sqrt(max(l1 * l1 - a * a, 0.0))
                hint = sub(E, A)
                pole = sub(hint, mul(dv, dot(hint, dv)))
                pole = unit(pole) if norm(pole) > 1e-6 else unit(cross(dv, (0.0, 0.0, 1.0)))
                E2 = add(A, add(mul(dv, a), mul(pole, h)))
                T2 = add(A, mul(dv, d))
                r1 = q_between(sub(E, A), sub(E2, A))
                a_q2 = qmul(r1, a_q0)
                r2 = q_between(qrot(r1, sub(H, E)), sub(T2, E2))
                f_q2 = qmul(r2, qmul(r1, f_q0))
                if f == 0 or f >= 39:       # exactly the paused frame's own arm (no jump when the use goes on)
                    solved = {ARM: ba[1], FORE: bf[1], HAND: bh[1]}
                else:
                    solved = {ARM: qmul(qinv(sh_q), a_q2), FORE: qmul(qinv(a_q2), f_q2), HAND: qmul(qinv(f_q2), hq)}
                for b, l in ((ARM, ba), (FORE, bf), (HAND, bh)):
                    keys[b][0].append(unreal.Vector(*l[0]))
                    keys[b][1].append(unreal.Quat(*solved[b]))
                    keys[b][2].append(unreal.Vector(*l[2]))
                if f == 12:
                    errs.append(norm(sub(add(T2, qrot(hq, wpn)), sub(item, bias))))
    nseg = len(ELEVS) * len(DISTS) * len(AZIMS)
    total = nseg * SEG2
    out_dir = out_dir or USE_DIR
    path = f"{out_dir}/{name}"
    if not EAL.does_asset_exist(path):
        unreal.AssetToolsHelpers.get_asset_tools().duplicate_asset(name, out_dir, template)
    seq = unreal.load_asset(path)
    ctrl = seq.get_editor_property("controller")
    ctrl.open_bracket("ImmLoot use reach (additive)", True)
    ctrl.remove_all_bone_tracks(True)
    ctrl.remove_all_curves_of_type(unreal.RawCurveTrackTypes.RCT_FLOAT, True)
    ctrl.set_frame_rate(unreal.FrameRate(30, 1), True)
    ctrl.set_number_of_frames(unreal.FrameNumber(total - 1), True)
    for b, (pos, rot, scl) in keys.items():
        if hasattr(ctrl, "add_bone_track"):
            ctrl.add_bone_track(b, True)
        else:
            ctrl.add_bone_curve(b, True)
        ctrl.set_bone_track_keys(b, pos, rot, scl, True)
    for b, (pos, rot, scl) in fk.items():
        n = len(rot)
        if hasattr(ctrl, "add_bone_track"):
            ctrl.add_bone_track(b, True)
        else:
            ctrl.add_bone_curve(b, True)
        ctrl.set_bone_track_keys(b, [unreal.Vector(*fbase[b][0])] * n, rot, [unreal.Vector(*fbase[b][2])] * n, True)
    ctrl.close_bracket(True)
    for tn in [str(t) for t in AL.get_animation_notify_track_names(seq)]:
        AL.remove_animation_notify_events_by_track(seq, tn)
    seq.set_editor_property("additive_anim_type", unreal.AdditiveAnimationType.AAT_LOCAL_SPACE_BASE)
    seq.set_editor_property("ref_pose_type", unreal.AdditiveBasePoseType.ABPT_LOCAL_ANIM_FRAME)
    seq.set_editor_property("ref_frame_index", 0)
    out.append(f"USE {name} (base {base.get_name()}): tracks {[str(t) for t in AL.get_animation_track_names(seq)]}, len {seq.get_play_length():.1f} s, "
               f"additive {seq.get_editor_property('additive_anim_type')}, rest hand rel eye {tuple(round(x - c, 1) for x, c in zip(R, cam))}, "
               f"grab error max {max(errs):.1f} cm (beyond reach: arm out toward it), saved {EAL.save_loaded_asset(seq, only_if_is_dirty=False)}")


def build_pick_pose():
    """build 30: the vodka use animation's first frame as a 2-frame pose, with jnt_camera and jnt_root from the
    empty-handed idle (the held use animation moved the camera: jnt_camera is a child of the root)."""
    vod = unreal.load_asset(USE_ROOT + "Vodka/AS_fp_vodka_use")
    idle = unreal.load_asset(BASE_BH)
    name = "AS_ImmLoot_PickPose"
    path = f"{DIR}/{name}"
    if not EAL.does_asset_exist(path):
        unreal.AssetToolsHelpers.get_asset_tools().duplicate_asset(name, DIR, unreal.load_asset(f"{DIR}/{NAME_BH}"))
    seq = unreal.load_asset(path)
    tracks = [str(t) for t in AL.get_animation_track_names(vod)]
    ctrl = seq.get_editor_property("controller")
    ctrl.open_bracket("ImmLoot pick pose", True)
    ctrl.remove_all_bone_tracks(True)
    ctrl.remove_all_curves_of_type(unreal.RawCurveTrackTypes.RCT_FLOAT, True)
    ctrl.set_frame_rate(unreal.FrameRate(30, 1), True)
    ctrl.set_number_of_frames(unreal.FrameNumber(90), True)    # 3 s, constant (played, not paused)
    # build 30c (tester: "the camera moves up slightly, like on tippy toes; no grab shows"; probe: our reach played but
    # the hand stayed 60-85 cm below the eye). The camera follows the head (the player AnimBP copies a virtual camera bone
    # onto jnt_camera at the end), and the use animation's torso is lower and bent (hips 4 cm lower, spine / neck / head
    # turned): the view rose and the arms sat low. Now the idle's legs, hips, spine, neck, head, camera and root with the
    # use animation's shoulders, arms, hands and fingers (and its item / IK bones).
    ARMS = ("_clavicle", "_shoulder", "_arm", "_hand", "_elbow", "_weapon", "ik_hand", "root_weapon")
    for b in tracks:
        l = local(vod if any(k in b for k in ARMS) else idle, b, 0)
        if hasattr(ctrl, "add_bone_track"):
            ctrl.add_bone_track(b, True)
        else:
            ctrl.add_bone_curve(b, True)
        ctrl.set_bone_track_keys(b, [unreal.Vector(*l[0])] * 91, [unreal.Quat(*l[1])] * 91, [unreal.Vector(*l[2])] * 91, True)
    ctrl.close_bracket(True)
    for tn in [str(t) for t in AL.get_animation_notify_track_names(seq)]:
        AL.remove_animation_notify_events_by_track(seq, tn)
    seq.set_editor_property("additive_anim_type", unreal.AdditiveAnimationType.AAT_NONE)
    out.append(f"PICKPOSE {name}: {len(tracks)} tracks, len {seq.get_play_length():.3f} s, saved {EAL.save_loaded_asset(seq, only_if_is_dirty=False)}")


def build_use_tables(src, tgt_rot, nkeys):
    template = unreal.load_asset(f"{DIR}/{NAME_BH}")
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    opt = unreal.AssetRegistryDependencyOptions(include_soft_package_references=False, include_hard_package_references=True)
    only = ARGS.get("USE_ONLY", "")
    for rel in USE_MONTS + [None]:
        mpath = USE_ROOT + (rel or "CannedFood/MG_fp_canned_food_use")
        name = "AS_ImmLoot_" + (mpath.rsplit("/", 1)[1] if rel else "UseAny")
        if only and only not in name:
            continue
        deps = [str(d) for d in ar.get_dependencies(mpath, opt)]
        seqs = [d for d in deps if "/Animations/" in d and str(EAL.find_asset_data(d).asset_class_path.asset_name) == "AnimSequence"]
        build_use_table(src, tgt_rot, nkeys, unreal.load_asset(seqs[0]), name, template)


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
    # 2026-10-10 f: left_hand_curve like the game's own left-hand gestures. On rifles with an underbarrel idle type the
    # weapon layer replaces the left arm by the GripIdle pose weighted by 1 - this curve (WeaponUnderbarrelIdleLayer),
    # so without it the grab plays but the hand stays on the grip (probe: hand at the grip through the whole montage
    # while the curve-carrying touch assets moved it; tester: "loose items broken, the hand doesn't go fully out")
    cname = "left_hand_curve"
    if cname in [str(c) for c in AL.get_animation_curve_names(seq, unreal.RawCurveTrackTypes.RCT_FLOAT)]:
        AL.remove_curve(seq, cname, False)
    AL.add_curve(seq, cname, unreal.RawCurveTrackTypes.RCT_FLOAT, False)
    AL.add_float_curve_keys(seq, cname, [0.0, 0.17, 1.15, 1.4, seq.get_play_length()], [0.0, 1.0, 1.0, 0.0, 0.0])
    out.append(f"curves: {[str(c) for c in AL.get_animation_curve_names(seq, unreal.RawCurveTrackTypes.RCT_FLOAT)]}")
    out.append(f"saved: {EAL.save_loaded_asset(seq, only_if_is_dirty=False)}")
    if ARGS.get("TOUCH", "1") == "1":
        build_touch(src, seq, path_h, path_q, nkeys)
    if ARGS.get("DOOR", "1") == "1":
        build_doors(src, seq, path_h, path_q, nkeys, tgt_rot)
    if ARGS.get("BH", "1") == "1":
        build_bh_reach_table(src, seq, tgt_rot, nkeys)   # build 12 (build_bh_table = checkpoint-b11)
    if ARGS.get("PICKADD", "0") == "1":    # build 38
        build_use_table(src, tgt_rot, nkeys, unreal.load_asset(BASE_BH), "AS_ImmLoot_GrabBHAdd", unreal.load_asset(f"{DIR}/{NAME_BH}"),
                        out_dir=DIR, grip_seq="src", azims=[-15, 0, 15, 30, 45])   # build 39; build 42: the vanilla grab's fingers
    if ARGS.get("PICKCROUCH", "0") == "1":    # build 41: crouched, its own rest pose (the stand table's delta barely moved the
        # crouched arm: build 40 probe, the hand ended where it started)
        build_use_table(src, tgt_rot, nkeys, unreal.load_asset("/Game/_STALKER2/Animations/Player/AnimSequences/bh/crouch/fp_bh_idle_crouch"),
                        "AS_ImmLoot_GrabBHAddCrouch", unreal.load_asset(f"{DIR}/{NAME_BH}"), out_dir=DIR,
                        grip_seq="src", azims=[-15, 0, 15, 30, 45], finger_base=unreal.load_asset(BASE_BH),
                        hand_roll=-70.0)   # build 45 (tester: crouched "rotate clockwise so the back of the hand faces up, now it faces left")   # build 42/44: the vanilla grab's fingers, from the standing rest
    if ARGS.get("PICKPOSE", "0") == "1":   # build 30: the pickup in our own use pose
        build_pick_pose()
        build_use_table(src, tgt_rot, nkeys, unreal.load_asset(f"{DIR}/AS_ImmLoot_PickPose"), "AS_ImmLoot_PickReach",
                        unreal.load_asset(f"{DIR}/{NAME_BH}"), out_dir=DIR, lower_deg=7.0, max_dist=45.0)
    if ARGS.get("USE", "0") == "1":
        build_use_tables(src, tgt_rot, nkeys)
    if ARGS.get("AR", "0") == "1":   # the rifle table never showed over a rifle (no left_hand_curve then); deleted for v1.0.0
        # v0.2: the same reach table on the rifle stance (weapon in hand), used to touch a corpse / stash; the rest pose
        # is the stance's own left hand on the grip
        build_bh_reach_table(src, seq, tgt_rot, nkeys, "/Game/_STALKER2/Animations/Player/AnimSequences/ar/common/stand/fp_ar_idle_stand",
                             "AS_ImmLoot_GrabAR")
except Exception:
    import traceback
    out.append("EXCEPTION " + traceback.format_exc())
os.makedirs(SCRATCH, exist_ok=True)
open(os.path.join(SCRATCH, "make_grab_seq.txt"), "w").write("\n".join(out))
