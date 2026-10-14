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
def dot4(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2] + a[3] * b[3]
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


def slerp_raw(a, b, t):
    """Slerp along the path from a to b as given (no shortest-way flip)."""
    d = max(-1.0, min(1.0, sum(x * y for x, y in zip(a, b))))
    th = math.acos(d)
    if math.sin(th) < 1e-6:
        r = tuple(x + (y - x) * t for x, y in zip(a, b))
    else:
        sa, sb = math.sin((1 - t) * th) / math.sin(th), math.sin(t * th) / math.sin(th)
        r = tuple(sa * x + sb * y for x, y in zip(a, b))
    n = math.sqrt(sum(x * x for x in r))
    return tuple(x / n for x in r)


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


def palm_q(src, facing, up_vec=(0.0, 0.0, 1.0)):
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
    up0 = unit(add(unit(up_vec), mul(unit(facing), 0.8)))             # build 11: fingers up AND forward (less tall on screen)
    up = unit(sub(up0, mul(unit(facing), dot(up0, unit(facing)))))
    f1p = unit(sub(f1, mul(unit(facing), dot(f1, unit(facing)))))
    return qmul(q_between(f1p, up), q1)


def hand_axes(src):
    """palm_q's hand-local finger direction and palm normal (the palm toward the item)."""
    hp, hq0 = cs(src, HAND, FIST_K)
    f_l = qrot(qinv(hq0), unit(sub(cs(src, "jnt_l_hand_middle_01", FIST_K)[0], hp)))
    lat = qrot(qinv(hq0), unit(sub(cs(src, "jnt_l_hand_index_01", FIST_K)[0], cs(src, "jnt_l_hand_pinky_01", FIST_K)[0])))
    palm_l = unit(cross(f_l, lat))
    if dot(qrot(hq0, palm_l), (1.0, 0.0, 0.0)) < 0:
        palm_l = mul(palm_l, -1.0)
    return f_l, palm_l


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
    # (1.3.0: the armed AS_ImmLoot_DoorPush / DoorPull are replaced by build_door_family's ...Ar / ...Pt)
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


TOUCH_HOLD_K = 18   # the Blueprint holds the touch at 0.6 s (frame 18) while the loot window is open
# build t (tester after build s, mirrored return: "no change"; r and s changed everything before frame 36 but nothing
# after it): the left-hand IK came on at 1.2 s over the default 0.2 s with the hand in the vanilla AK grab's grip pose,
# 35-98 deg (local) from the held weapon's own grip (pistols most): a quick wrist twist at the very end. Now the IK
# comes on as the hand starts back (0.8 s = frame 24, the mirror of the reach's frame 12) over 0.5 s, so the hand
# settles onto the real grip while it travels.
TOUCH_IK_ON = (1.0, 0.35)   # build y: was (1.2, 0.25)
# build v (build u = a left-arm additive in FullBody over the IK: "way worse, the hand is jelly / alien", reverted).
# Probe build t: the flips are inside the IK's blends, where the IK's grip and our keyed hand are ~180 deg apart. The
# reach-out turns the hand ~170 deg by frame 7 while the IK still held it (off at 0.036 s over 0.2 s): off now over
# 0.06 s (the hand has turned ~25 deg by then); on at 1.2 s (frame 36, the start pose again) over 0.25 s.
TOUCH_IK_OFF_BLEND = 0.06
# build y (tester: "on the way back the hand goes too far right and clips through the gun, then moves left into place"):
# the touch ends on the rifle stand idle's grip, the IK then slid it to the held weapon's own grip. The IK comes on at
# frame 30 (the palm already back, <= 60 deg from the grip) over 0.35 s, so the hand converges on the real grip while
# it travels in.


def mirror_touch_return(seq):
    """2026-10-13 build s (tester, armed, bag off: "when the hand returns to the weapon it twists awkwardly", also the
    session's first report and Tim0st's on Nexus). The way back (frames 20-36) re-solved only the upper arm, forearm and
    hand, with the elbow pole and the shoulder taken from the vanilla grab's own frames, where the vanilla hand goes to
    the chest and flips back onto the grip (frames 23-34): the solved elbow swung over (upper arm 55-64 deg in one frame)
    and the untouched roll / shoulder / finger tracks twisted with the vanilla motion. Now every left-arm track (the
    LeftHand slot's mask: the shoulder down) plays the reach back in reverse after the hold: frame 18 + i = frame 18 - i,
    the start pose (the grip, = the vanilla grab's frames 41-50) from 36 on, where the "left hand back on" IK notify is."""
    n = AL.get_num_frames(seq)
    tracks = [str(t) for t in AL.get_animation_track_names(seq)]
    arm = [b for b in tracks if "jnt_l_shoulder" in [str(x) for x in AL.find_bone_path_to_root(seq, b)]]
    H = TOUCH_HOLD_K
    src_k = lambda k: k if k <= H else (2 * H - k if k <= 2 * H else 0)
    keys = {}
    for b in arm:
        poses = [AL.get_bone_pose_for_frame(seq, b, k, False) for k in range(n + 1)]
        sel = [poses[src_k(k)] for k in range(n + 1)]
        keys[b] = ([t.translation for t in sel], [t.rotation for t in sel], [t.scale3d for t in sel])
    ctrl = seq.get_editor_property("controller")
    ctrl.open_bracket("ImmLoot touch return mirrored", True)
    for b, (pos, rot, scl) in keys.items():
        ctrl.set_bone_track_keys(b, pos, rot, scl, True)
    ctrl.close_bracket(True)
    return len(arm)


NAME_TOUCH_PT = "AS_ImmLoot_TouchPt"
PISTOL_BASE = "/Game/_STALKER2/Animations/Player/AnimSequences/pt/pm/Idle/AS_fp_pm_idle"
ELBOW_REF = (-0.25, -0.82, -0.5)   # component space: back a little, left, down


NAME_TOUCH_AR = "AS_ImmLoot_TouchAr"
SPREAD_SEQ = "/Game/_STALKER2/Animations/Player/AnimSequences/Dialog_animations/AS_fp_dialogue_bothhands_statement"
SPREAD_K = 70
TOUCH_PALM_DOWN = (0.0, 0.0, -0.6)
TOUCH_FINGERS_UP = (0.0, 0.1, 1.0)    # build z (tester: "twisted counter clockwise too much, like breaking the wrist"): was (0, -0.35, 1)
TOUCH_EXIT = (2.0, -8.0, -6.0)          # build z / za: component space, cm, from the path's end: a little forward, left, down
TOUCH_END_OFF = (1.0, -5.0, -4.0)       # build za: the path's end from the stand idle's grip: left and down
RIFLE_BASE = "/Game/_STALKER2/Animations/Player/AnimSequences/ar/common/stand/fp_ar_idle_stand"
TOUCH_FAMILIES = {"pt": (NAME_TOUCH_PT, PISTOL_BASE), "ar": (NAME_TOUCH_AR, RIFLE_BASE)}


def build_touch_pistol(i, family="pt"):
    """2026-10-13 build w (tester, pistol: "very obviously twisting when coming back"; probe build v: the hand turns up
    to 116 deg in one tick at the start (the LeftHand slot's 0.2 s blend-in) and 23-30 deg a tick for ~0.3 s on the way
    back). The touches start and end in the vanilla AK grab's grip, 9.7 cm and 88 deg from every pistol's support grip
    (kora / apb / pm / udp / rhino agree within 2.6 cm and 24 deg), and their wrist turns ~170 deg with the vanilla
    reach: blending them over a pistol pose flips, and the way back is a long wrist roll. With a pistol: these, built on
    the pistol idle (AS_fp_pm_idle frame 0) for every left-arm track: the shoulder, fingers and roll bones stay at the
    pistol grip; only the upper arm / forearm are solved toward the same point as AS_ImmLoot_Touch<i>, and the hand
    keeps its pistol-grip wrist (no roll). Out by frame 12, held to 18 (the Blueprint's pause), back by 36 (reverse)."""
    # build x (tester: pistol "no more twisting, but the hand still looks like it's holding a grip instead of a high
    # five facing away from the player"; rifles still twist): the hand turns, the short way, from the grip to the palm
    # facing the target (palm_q: fingers up) while the fingers open (the dialogue gesture's open hand), over the reach
    # (frames 0-12) and back over the return; the same build on the rifle stand idle (fp_ar_idle_stand, within 0-64 deg
    # of every rifle / SMG / sniper / shotgun idle's left hand) for every long gun: AS_ImmLoot_TouchAr<bin>
    prefix, base_path = TOUCH_FAMILIES[family]
    name = f"{prefix}{i}"
    path = f"{DIR}/{name}"
    tmpl = unreal.load_asset(f"{DIR}/{NAME}")   # release cleanup: the grab (same tracks / frames); the old AS_ImmLoot_Touch* are gone
    if not EAL.does_asset_exist(path):
        unreal.AssetToolsHelpers.get_asset_tools().duplicate_asset(name, DIR, tmpl)
    seq = unreal.load_asset(path)
    base = unreal.load_asset(base_path)
    grab_src = unreal.load_asset(SRC)
    # build y (tester: "the fingers need to be spread out"): the most spread vanilla left hand with straight fingers
    # (searched: dialogue / interactables / items / deaths; index-pinky 49 deg, curl 20 deg; the door hand's ~20)
    sp_seq = unreal.load_asset(SPREAD_SEQ)
    opens = {b: local(sp_seq, b, SPREAD_K)[1] for b in FINGERS}
    n = AL.get_num_frames(tmpl)
    ie, ia = divmod(i, len(TOUCH_AZIMS))
    elev, azim = float(TOUCH_ELEVS[ie]), float(TOUCH_AZIMS[ia])
    cam, _ = cs(base, "jnt_camera", 0)
    er, ar = math.radians(elev), math.radians(azim)
    dirv_e = (math.cos(er) * math.cos(ar), math.cos(er) * math.sin(ar), math.sin(er))
    sh_p, sh_q = cs(base, SHOULDER, 0)
    a_l, f_l, h_l = local(base, ARM, 0), local(base, FORE, 0), local(base, HAND, 0)
    a_q = qmul(sh_q, a_l[1]); A = add(sh_p, qrot(sh_q, a_l[0]))
    f_q = qmul(a_q, f_l[1]); E = add(A, qrot(a_q, f_l[0]))
    R = add(E, qrot(f_q, h_l[0]))
    RQ = qmul(f_q, h_l[1])
    l1, l2 = norm(sub(E, A)), norm(sub(R, E))
    reach = (l1 + l2) * TOUCH_REACH
    inv = lambda v: tuple((v[j] - TOUCH_MAP[j][1]) / TOUCH_MAP[j][0] for j in range(3))
    u = tuple(dirv_e[j] / TOUCH_MAP[j][0] for j in range(3))
    c_ = sub(add(cam, inv((0.0, 0.0, 0.0))), A)
    qa, qb, qc = dot(u, u), 2 * dot(c_, u), dot(c_, c_) - reach * reach
    disc = qb * qb - 4 * qa * qc
    t = (-qb + math.sqrt(disc)) / (2 * qa) if disc > 0 else max(10.0, -qb / (2 * qa))
    G = add(cam, inv(mul(dirv_e, t)))
    hint = sub(E, A)
    sched = ((0, 12, R, G), (12, 18, G, G), (18, 36, G, R))
    tracks = [str(x) for x in AL.get_animation_track_names(tmpl)]
    arm = [b for b in tracks if "jnt_l_shoulder" in [str(x) for x in AL.find_bone_path_to_root(tmpl, b)]]
    keys = {}
    for b in arm:
        l = local(base, b, 0)
        keys[b] = ([unreal.Vector(*l[0])] * (n + 1), [unreal.Quat(*l[1])] * (n + 1), [unreal.Vector(*l[2])] * (n + 1))
    # build y (tester: "angled down and away from the player a bit, too robotic and upright"): the palm faces the target
    # tilted ~30 deg down, the fingers lean out to the left ~20 deg
    PQ = palm_q(grab_src, unit(add(dirv_e, TOUCH_PALM_DOWN)), TOUCH_FINGERS_UP)
    if dot4(PQ, RQ) < 0:
        PQ = tuple(-x for x in PQ)
    out_w, kr, prev_tq = [], [], None
    ROLL = "jnt_l_fore_arm_roll"
    roll_l = local(base, ROLL, 0)[1]
    ka, kf, kh = ([], []), ([], []), ([], [])
    for k in range(n + 1):
        bw, T0, T1 = 1.0, R, R
        for f0, f1, P0, P1 in sched:
            if f0 <= k <= f1:
                bw, T0, T1 = smooth((k - f0) / max(f1 - f0, 1)), P0, P1
                break
        # build z (tester: "on the return the hand clips through the barrel to go back to the grip", pistols and
        # rifles; probe: it came back from above the grip and passed it 3.5 cm to the right, 3-5 cm above): the hand
        # leaves and rejoins the grip from the left and below (a quadratic curve through TOUCH_EXIT off the grip)
        u_ = bw if T1 is G and T0 is R else (1.0 - bw if T0 is G and T1 is R else (1.0 if T0 is G else 0.0))
        # build za (tester: still clips on the return, then "goes left and right slightly before it settles"; probe:
        # the stand idle's grip R is ~3-4 cm right of / ~2.5 cm above the held weapon's own grip, so the hand came in
        # past the real grip to R while the IK took over and pulled it back): the path ends left of and below R
        # (TOUCH_END_OFF), the IK (on from frame 30) takes the hand from there to the real grip, from the left / below
        Re_ = add(R, TOUCH_END_OFF)
        P1_ = add(Re_, TOUCH_EXIT)
        T = add(add(mul(Re_, (1 - u_) ** 2), mul(P1_, 2 * u_ * (1 - u_))), mul(G, u_ * u_))
        to_t = sub(T, A)
        d = max(abs(l1 - l2) + 0.01, min(reach, norm(to_t)))
        dv = unit(to_t)
        a = (l1 * l1 - l2 * l2 + d * d) / (2 * d)
        h = math.sqrt(max(l1 * l1 - a * a, 0.0))
        # the elbow: the pistol pose's own at rest, turning toward out-left-and-down as the hand goes out (the rest
        # elbow's direction lines up with the reach to the low left bins: the solve flipped the elbow 30-35 deg a frame)
        s_ = min(1.0, norm(sub(T, R)) / max(norm(sub(G, R)), 1e-6))
        ref = unit(add(mul(unit(hint), 1.0 - s_), mul(ELBOW_REF, s_)))
        pole = sub(ref, mul(dv, dot(ref, dv)))
        pole = unit(pole) if norm(pole) > 1e-6 else unit(cross(dv, (0.0, 0.0, 1.0)))
        E2 = add(A, add(mul(dv, a), mul(pole, h)))
        T2 = add(A, mul(dv, d))
        r1 = q_between(sub(E, A), sub(E2, A))
        a_q2 = qmul(r1, a_q)
        r2 = q_between(qrot(r1, sub(R, E)), sub(T2, E2))
        f_q2 = qmul(r2, qmul(r1, f_q))
        ka[1].append(unreal.Quat(*qmul(qinv(sh_q), a_q2)))
        kf[1].append(unreal.Quat(*qmul(qinv(a_q2), f_q2)))
        # the palm turn and the open fingers: frames 5-17 (after the LeftHand slot's 0.2 s blend-in, so the blend only
        # ever spans the grip-to-grip gap), back over 19-31 (mirror), none from 36 on. The hand follows the swung
        # forearm, then turns toward PQ; half of its turn about the forearm goes to the forearm roll bone (skin twist)
        kk = k if k <= 18 else (36 - k if k <= 36 else 0)
        wv = smooth(min(1.0, max(0.0, (kk - 5) / 12.0)))
        tq = qmul(qinv(f_q2), PQ)
        # one way round for the whole touch (some bins' palm target is ~180 deg from the grip: a per-frame shortest path
        # switched sides between frames, 177 deg in one frame)
        if prev_tq is None:
            if dot4(tq, h_l[1]) < 0:
                tq = tuple(-x for x in tq)
        elif dot4(tq, prev_tq) < 0:
            tq = tuple(-x for x in tq)
        prev_tq = tq
        hl = slerp_raw(h_l[1], tq, wv)
        kh[1].append(unreal.Quat(*hl))
        dlt = qmul(hl, qinv(h_l[1]))
        ax_ = unit(h_l[0])
        pr = dot(ax_, dlt[:3])
        tw = (ax_[0] * pr, ax_[1] * pr, ax_[2] * pr, dlt[3])
        tn = math.sqrt(sum(x * x for x in tw))
        tw = tuple(x / tn for x in tw) if tn > 1e-9 else (0.0, 0.0, 0.0, 1.0)
        kr.append(unreal.Quat(*qmul(slerp((0.0, 0.0, 0.0, 1.0), tw, 0.5), roll_l)))
        out_w.append(wv)
    keys[ARM] = (keys[ARM][0], ka[1], keys[ARM][2])
    keys[FORE] = (keys[FORE][0], kf[1], keys[FORE][2])
    keys[HAND] = (keys[HAND][0], kh[1], keys[HAND][2])
    if ROLL in keys:
        keys[ROLL] = (keys[ROLL][0], kr, keys[ROLL][2])
    for b in FINGERS:
        if b in keys:
            rest = local(base, b, 0)[1]
            keys[b] = (keys[b][0], [unreal.Quat(*finger_q(rest, opens, opens, b, wv, 0.0)) for wv in out_w], keys[b][2])
    ctrl = seq.get_editor_property("controller")
    ctrl.open_bracket("ImmLoot pistol touch", True)
    for b, (pos, rot, scl) in keys.items():
        ctrl.set_bone_track_keys(b, list(pos), list(rot), list(scl), True)
    ctrl.close_bracket(True)
    touch_notifies(seq, "touch")
    cname = "left_hand_curve"
    if cname in [str(x) for x in AL.get_animation_curve_names(seq, unreal.RawCurveTrackTypes.RCT_FLOAT)]:
        AL.remove_curve(seq, cname, False)
    AL.add_curve(seq, cname, unreal.RawCurveTrackTypes.RCT_FLOAT, False)
    AL.add_float_curve_keys(seq, cname, [0.0, 0.17, 1.1, 1.3, seq.get_play_length()], [0.0, 1.0, 1.0, 0.0, 0.0])
    rel = sub(G, cam)
    out.append(f"{name}: elev {elev:+.0f} az {azim:+.0f}, hand to ({rel[0]:.1f},{rel[1]:.1f},{rel[2]:.1f}) from the eye, "
               f"{len(arm)} left-arm tracks, saved {EAL.save_loaded_asset(seq, only_if_is_dirty=False)}")



GRAB_FAMILY_NAMES = {"ar": "AS_ImmLoot_GrabAr", "pt": "AS_ImmLoot_GrabPt"}
GRAB_POCKET_K = 26     # the armed grab's pocket frame (Blueprint PocketTime 0.87 s): the item is gone there
GRAB_BACK_K = 38       # the way back to the grip ends here (12 frames, the touch's return speed)
GRAB_IK_ON = (32 / 30.0, 0.35)


def build_grab_family(family):
    """n2j (tester, armed loose-item pickup: "once the item has been grabbed and the hand goes back, then it starts to
    return to the weapon, it goes a little too far right and then recorrects; the stash hand return looks good, copy
    that exact return"): AS_ImmLoot_Grab's way back is the vanilla AK grab's (to the AK stand grip; the IK then slid the
    hand to the held weapon's grip, past it and back, as the touches did before build za). AS_ImmLoot_GrabAr / ...Pt:
    AS_ImmLoot_Grab unchanged to the pocket frame (reach, grab, pocket), then the touch's return on the family stance
    (fp_ar_idle_stand / AS_fp_pm_idle): the hand's path from the pocket to TOUCH_END_OFF off the stance grip through
    TOUCH_EXIT (it comes in from the left and below), upper arm / forearm solved (the elbow from the pocket's toward the
    stance's), the hand's turn, the shoulder / roll / fingers eased to the stance, the IK on from frame 32 over 0.35 s
    (it takes the hand to the real grip from the left / below)."""
    name = GRAB_FAMILY_NAMES[family]
    path = f"{DIR}/{name}"
    tmpl = unreal.load_asset(f"{DIR}/{NAME}")
    if not EAL.does_asset_exist(path):
        unreal.AssetToolsHelpers.get_asset_tools().duplicate_asset(name, DIR, tmpl)
    seq = unreal.load_asset(path)
    base = unreal.load_asset(TOUCH_FAMILIES[family][1])
    n = AL.get_num_frames(tmpl)
    tracks = [str(x) for x in AL.get_animation_track_names(tmpl)]
    arm = [b for b in tracks if SHOULDER in [str(x) for x in AL.find_bone_path_to_root(tmpl, b)]]
    sh_parent = [str(x) for x in AL.find_bone_path_to_root(base, SHOULDER)][1]
    pp_p, pp_q = cs(base, sh_parent, 0)
    Pk, Ek = GRAB_POCKET_K, GRAB_BACK_K
    gl = {b: local(tmpl, b, Pk) for b in arm}        # the pocket frame's left arm
    st = {b: local(base, b, 0) for b in arm}         # the family stance's

    def chain(L):
        sh_q = qmul(pp_q, L[SHOULDER][1]); sh_p = add(pp_p, qrot(pp_q, L[SHOULDER][0]))
        a_q = qmul(sh_q, L[ARM][1]); A = add(sh_p, qrot(sh_q, L[ARM][0]))
        f_q = qmul(a_q, L[FORE][1]); E = add(A, qrot(a_q, L[FORE][0]))
        h_q = qmul(f_q, L[HAND][1]); R = add(E, qrot(f_q, L[HAND][0]))
        return sh_q, A, E, R, a_q, f_q, h_q
    _, A_P, E_P, H_P, _, _, HQ_P = chain(gl)
    _, A_S, E_S, R_S, _, _, RQ_S = chain(st)
    if dot4(HQ_P, RQ_S) < 0:
        RQ_S = tuple(-x for x in RQ_S)
    Re_ = add(R_S, TOUCH_END_OFF)
    P1_ = add(Re_, TOUCH_EXIT)
    l1, l2 = norm(sub(E_P, A_P)), norm(sub(H_P, E_P))
    pole_P, pole_S = unit(sub(E_P, A_P)), unit(sub(E_S, A_S))
    keys = {b: ([], [], []) for b in arm}
    for k in range(n + 1):
        if k <= Pk:
            for b in arm:
                l = local(tmpl, b, k)
                keys[b][0].append(unreal.Vector(*l[0])); keys[b][1].append(unreal.Quat(*l[1])); keys[b][2].append(unreal.Vector(*l[2]))
            continue
        w = smooth(min(1.0, (k - Pk) / float(Ek - Pk)))
        L = {b: (gl[b][0], slerp(gl[b][1], st[b][1], w), gl[b][2]) for b in arm}
        sh_q, A, E_ref, R_ref, a_ref, f_ref0, _ = chain(L)
        T = add(add(mul(H_P, (1 - w) ** 2), mul(P1_, 2 * w * (1 - w))), mul(Re_, w * w))
        to_t = sub(T, A)
        d = max(abs(l1 - l2) + 0.01, min((l1 + l2) * 0.999, norm(to_t)))
        dv = unit(to_t)
        a = (l1 * l1 - l2 * l2 + d * d) / (2 * d)
        h = math.sqrt(max(l1 * l1 - a * a, 0.0))
        ref = unit(add(mul(pole_P, 1.0 - w), mul(pole_S, w)))
        pole = sub(ref, mul(dv, dot(ref, dv)))
        pole = unit(pole) if norm(pole) > 1e-6 else unit(cross(dv, (0.0, 0.0, 1.0)))
        E2 = add(A, add(mul(dv, a), mul(pole, h)))
        T2 = add(A, mul(dv, d))
        r1 = q_between(sub(E_ref, A), sub(E2, A))
        a_q2 = qmul(r1, a_ref)
        f_ref = qmul(a_q2, L[FORE][1])
        R2 = add(E2, qrot(f_ref, L[HAND][0]))
        r2 = q_between(sub(R2, E2), sub(T2, E2))
        f_q2 = qmul(r2, f_ref)
        HQ = slerp(HQ_P, RQ_S, w)
        solved = {ARM: qmul(qinv(sh_q), a_q2), FORE: qmul(qinv(a_q2), f_q2), HAND: qmul(qinv(f_q2), HQ)}
        for b in arm:
            rq = solved.get(b, L[b][1])
            keys[b][0].append(unreal.Vector(*L[b][0])); keys[b][1].append(unreal.Quat(*rq)); keys[b][2].append(unreal.Vector(*L[b][2]))
    ctrl = seq.get_editor_property("controller")
    ctrl.open_bracket("ImmLoot family grab", True)
    for b, (pos, rot, scl) in keys.items():
        ctrl.set_bone_track_keys(b, pos, rot, scl, True)
    ctrl.close_bracket(True)
    touch_notifies(seq, "grab")
    cname = "left_hand_curve"
    if cname in [str(x) for x in AL.get_animation_curve_names(seq, unreal.RawCurveTrackTypes.RCT_FLOAT)]:
        AL.remove_curve(seq, cname, False)
    AL.add_curve(seq, cname, unreal.RawCurveTrackTypes.RCT_FLOAT, False)
    AL.add_float_curve_keys(seq, cname, [0.0, 0.17, 1.1, 1.3, seq.get_play_length()], [0.0, 1.0, 1.0, 0.0, 0.0])
    ev_ = [(round(AL.get_anim_notify_event_trigger_time(e), 3), round(e.notify.get_editor_property("blend_time"), 2))
           for e in AL.get_animation_notify_events(seq) if e.notify]
    out.append(f"{name}: pocket {Pk} -> grip-side end {Ek}, end off the stance grip {tuple(round(x, 1) for x in TOUCH_END_OFF)}, "
               f"IK {ev_}, saved {EAL.save_loaded_asset(seq, only_if_is_dirty=False)}")


DOOR_FAMILY_NAMES = {("ar", "push"): "AS_ImmLoot_DoorPushAr", ("ar", "pull"): "AS_ImmLoot_DoorPullAr",
                     ("pt", "push"): "AS_ImmLoot_DoorPushPt", ("pt", "pull"): "AS_ImmLoot_DoorPullPt"}
DOOR_ARC = (3.0, -4.0, -14.0)      # door build B: the curve's control point from the path's end (component cm): the hand
                                   # leaves / rejoins the grip in a downward arc under the weapon (tester)
DOOR_IK_ON = {"push": (1.0, 0.35), "pull": (1.13, 0.35)}
DOOR_PUSH_STROKE_FAM = 24.0        # door build C: cm of forward drive in the push (was 14)   # frame 30 / 34: the hand back near the grip


def build_door_family(family, mode):
    """2026-10-13 door build B (tester: "the animation still looks bad. the hand clips through the gun and the fingers
    look weird as they settle into the resting pose. the return should go in a downward arc under the pistol or
    rifle"): the door push / pull with a weapon, built like the v1.2.0 touches (zonekit/research/touch/README.md):
    every left-arm track at the family's stance (rifle stand idle / pistol idle), only the upper arm / forearm solved,
    the elbow pole turning out-left-down, the hand following the forearm and turning one way round (half the turn in the
    forearm roll), the path starting / ending left of and below the stance grip and leaving / rejoining it in a
    downward arc under the weapon (DOOR_ARC). Push: an open spread palm toward the door, out by 8, a forward stroke
    8-14 (the Blueprint holds at 14 = 0.467 s), back 18-36. Pull: out to the handle by 8, the hand closes 8-12 (held
    at 12 = 0.4 s), drawn back and down 12-26, the hand opens and comes back 26-40. IK off at 0.036 s over 0.06 s, on
    near the grip (push 1.0 s, pull 1.13 s) over 0.35 s."""
    _prefix, base_path = TOUCH_FAMILIES[family]
    name = DOOR_FAMILY_NAMES[(family, mode)]
    path = f"{DIR}/{name}"
    tmpl = unreal.load_asset(f"{DIR}/{NAME}")
    if not EAL.does_asset_exist(path):
        unreal.AssetToolsHelpers.get_asset_tools().duplicate_asset(name, DIR, tmpl)
    seq = unreal.load_asset(path)
    base = unreal.load_asset(base_path)
    grab_src = unreal.load_asset(SRC)
    sp_seq = unreal.load_asset(SPREAD_SEQ)
    opens = {b: local(sp_seq, b, SPREAD_K)[1] for b in FINGERS}
    _o, fists = door_fingers(grab_src)
    n = AL.get_num_frames(tmpl)
    cam, _ = cs(base, "jnt_camera", 0)
    er, ar = math.radians(DOOR_ELEV), math.radians(DOOR_AZIM)
    dirv_e = (math.cos(er) * math.cos(ar), math.cos(er) * math.sin(ar), math.sin(er))
    sh_p, sh_q = cs(base, SHOULDER, 0)
    a_l, f_l, h_l = local(base, ARM, 0), local(base, FORE, 0), local(base, HAND, 0)
    a_q = qmul(sh_q, a_l[1]); A = add(sh_p, qrot(sh_q, a_l[0]))
    f_q = qmul(a_q, f_l[1]); E = add(A, qrot(a_q, f_l[0]))
    R = add(E, qrot(f_q, h_l[0]))
    RQ = qmul(f_q, h_l[1])
    l1, l2 = norm(sub(E, A)), norm(sub(R, E))
    reach = (l1 + l2) * TOUCH_REACH
    inv = lambda v: tuple((v[j] - TOUCH_MAP[j][1]) / TOUCH_MAP[j][0] for j in range(3))
    u = tuple(dirv_e[j] / TOUCH_MAP[j][0] for j in range(3))
    c_ = sub(add(cam, inv((0.0, 0.0, 0.0))), A)
    qa, qb, qc = dot(u, u), 2 * dot(c_, u), dot(c_, c_) - reach * reach
    disc = qb * qb - 4 * qa * qc
    t = (-qb + math.sqrt(disc)) / (2 * qa) if disc > 0 else max(10.0, -qb / (2 * qa))
    G = add(cam, inv(mul(dirv_e, t)))
    back = unit(sub(G, cam))
    Re = add(R, TOUCH_END_OFF)
    C = add(Re, DOOR_ARC)
    if mode == "push":
        # door build C (tester: "the push could use more of a push, the hand just kinda stays static"): the hand comes up
        # nearer the body (DOOR_PUSH_STROKE_FAM back from the door) and drives forward accelerating into it (ease-in)
        N = sub(G, mul(back, DOOR_PUSH_STROKE_FAM))
        legs = ((0, 8, "curve", Re, N), (8, 14, "push", N, G), (14, 18, "line", G, G), (18, 36, "curve", G, Re))
        turn = lambda k: smooth(min(1.0, max(0.0, (k - 6) / 8.0))) if k <= 18 else smooth(min(1.0, max(0.0, (27 - k) / 9.0)))
        fist = lambda k: 0.0
        PQ = palm_q(grab_src, unit(add(dirv_e, TOUCH_PALM_DOWN)), TOUCH_FINGERS_UP)
    else:
        PB = sub(sub(G, mul(back, DOOR_PULL_STROKE)), (0.0, 0.0, DOOR_PULL_DROP))
        legs = ((0, 8, "curve", Re, G), (8, 12, "line", G, G), (12, 26, "line", G, PB), (26, 40, "curve", PB, Re))
        turn = lambda k: smooth(min(1.0, max(0.0, (k - 3) / 5.0))) if k <= 26 else smooth(min(1.0, max(0.0, (34 - k) / 8.0)))
        fist = lambda k: smooth(min(1.0, max(0.0, (k - 8) / 4.0))) if k <= 26 else smooth(min(1.0, max(0.0, (32 - k) / 6.0)))
        # the hand around a handle: palm facing right (inward), fingers along the reach
        PQ = palm_q(grab_src, unit(add((0.0, 1.0, 0.0), mul(dirv_e, 0.3))), dirv_e)
    if dot4(PQ, RQ) < 0:
        PQ = tuple(-x for x in PQ)
    hint = sub(E, A)
    tracks = [str(x) for x in AL.get_animation_track_names(tmpl)]
    arm = [b for b in tracks if "jnt_l_shoulder" in [str(x) for x in AL.find_bone_path_to_root(tmpl, b)]]
    keys = {}
    for b in arm:
        l = local(base, b, 0)
        keys[b] = ([unreal.Vector(*l[0])] * (n + 1), [unreal.Quat(*l[1])] * (n + 1), [unreal.Vector(*l[2])] * (n + 1))
    ROLL = "jnt_l_fore_arm_roll"
    roll_l = local(base, ROLL, 0)[1]
    ka, kf, kh, kr, ww, wf, prev_tq = [], [], [], [], [], [], None
    for k in range(n + 1):
        T = Re
        for f0, f1, kind, P0, P1 in legs:
            if f0 <= k <= f1:
                w_ = smooth((k - f0) / max(f1 - f0, 1))
                if kind == "push":
                    x_ = (k - f0) / max(f1 - f0, 1)
                    T = add(P0, mul(sub(P1, P0), x_ * x_))
                elif kind == "line":
                    T = add(P0, mul(sub(P1, P0), w_))
                else:
                    T = add(add(mul(P0, (1 - w_) ** 2), mul(C, 2 * w_ * (1 - w_))), mul(P1, w_ * w_))
                break
        to_t = sub(T, A)
        d = max(abs(l1 - l2) + 0.01, min(reach, norm(to_t)))
        dv = unit(to_t)
        a = (l1 * l1 - l2 * l2 + d * d) / (2 * d)
        h = math.sqrt(max(l1 * l1 - a * a, 0.0))
        s_ = min(1.0, norm(sub(T, Re)) / max(norm(sub(G, Re)), 1e-6))
        ref = unit(add(mul(unit(hint), 1.0 - s_), mul(ELBOW_REF, s_)))
        pole = sub(ref, mul(dv, dot(ref, dv)))
        pole = unit(pole) if norm(pole) > 1e-6 else unit(cross(dv, (0.0, 0.0, 1.0)))
        E2 = add(A, add(mul(dv, a), mul(pole, h)))
        T2 = add(A, mul(dv, d))
        r1 = q_between(sub(E, A), sub(E2, A))
        a_q2 = qmul(r1, a_q)
        r2 = q_between(qrot(r1, sub(R, E)), sub(T2, E2))
        f_q2 = qmul(r2, qmul(r1, f_q))
        ka.append(unreal.Quat(*qmul(qinv(sh_q), a_q2)))
        kf.append(unreal.Quat(*qmul(qinv(a_q2), f_q2)))
        wv = turn(k)
        tq = qmul(qinv(f_q2), PQ)
        if prev_tq is None:
            if dot4(tq, h_l[1]) < 0:
                tq = tuple(-x for x in tq)
        elif dot4(tq, prev_tq) < 0:
            tq = tuple(-x for x in tq)
        prev_tq = tq
        hl = slerp_raw(h_l[1], tq, wv)
        kh.append(unreal.Quat(*hl))
        dlt = qmul(hl, qinv(h_l[1]))
        ax_ = unit(h_l[0])
        pr = dot(ax_, dlt[:3])
        tw = (ax_[0] * pr, ax_[1] * pr, ax_[2] * pr, dlt[3])
        tn = math.sqrt(sum(x * x for x in tw))
        tw = tuple(x / tn for x in tw) if tn > 1e-9 else (0.0, 0.0, 0.0, 1.0)
        kr.append(unreal.Quat(*qmul(slerp((0.0, 0.0, 0.0, 1.0), tw, 0.5), roll_l)))
        ww.append(wv)
        wf.append(fist(k))
    keys[ARM] = (keys[ARM][0], ka, keys[ARM][2])
    keys[FORE] = (keys[FORE][0], kf, keys[FORE][2])
    keys[HAND] = (keys[HAND][0], kh, keys[HAND][2])
    if ROLL in keys:
        keys[ROLL] = (keys[ROLL][0], kr, keys[ROLL][2])
    for b in FINGERS:
        if b in keys:
            rest = local(base, b, 0)[1]
            keys[b] = (keys[b][0], [unreal.Quat(*finger_q(rest, opens, fists, b, wo_, wf_)) for wo_, wf_ in zip(ww, wf)], keys[b][2])
    ctrl = seq.get_editor_property("controller")
    ctrl.open_bracket("ImmLoot door (family)", True)
    for b, (pos, rot, scl) in keys.items():
        ctrl.set_bone_track_keys(b, list(pos), list(rot), list(scl), True)
    ctrl.close_bracket(True)
    for tn_ in [str(x) for x in AL.get_animation_notify_track_names(seq)]:
        AL.remove_animation_notify_events_by_track(seq, tn_)
    track = "ImmLoot"
    if track not in [str(x) for x in AL.get_animation_notify_track_names(seq)]:
        AL.add_animation_notify_track(seq, track, unreal.LinearColor(0.2, 0.8, 0.2, 1.0))
    hand = None
    for e in AL.get_animation_notify_events(unreal.load_asset(MONT)):
        if e.notify is not None and e.notify.get_class().get_name() == "AnimNotify_HandIK":
            hand = e.notify.get_editor_property("hand_to_apply")
    hik = unreal.load_class(None, "/Script/Stalker2.AnimNotify_HandIK")
    for t_, end, bl in ((0.035907, None, TOUCH_IK_OFF_BLEND), (DOOR_IK_ON[mode][0], 1.0, DOOR_IK_ON[mode][1])):
        ev = AL.add_animation_notify_event(seq, track, t_, hik)
        ev.set_editor_property("hand_to_apply", hand)
        ev.set_editor_property("blend_time", bl)
        if end is not None:
            ev.set_editor_property("end_value", end)
    cname = "left_hand_curve"
    if cname in [str(x) for x in AL.get_animation_curve_names(seq, unreal.RawCurveTrackTypes.RCT_FLOAT)]:
        AL.remove_curve(seq, cname, False)
    AL.add_curve(seq, cname, unreal.RawCurveTrackTypes.RCT_FLOAT, False)
    AL.add_float_curve_keys(seq, cname, [0.0, 0.17, 1.1, 1.3, seq.get_play_length()], [0.0, 1.0, 1.0, 0.0, 0.0])
    rel = sub(G, cam)
    out.append(f"{name}: to ({rel[0]:.1f},{rel[1]:.1f},{rel[2]:.1f}) from the eye, {len(arm)} left-arm tracks, "
               f"saved {EAL.save_loaded_asset(seq, only_if_is_dirty=False)}")



NAME_PAT = "AS_ImmLoot_PatTable"
PAT_FAMILIES = (("ar", RIFLE_BASE), ("pt", PISTOL_BASE), ("bh", BASE_BH))   # segment = family index * 25 + bin
PAT_SEG = 51                       # frames per segment (30 fps): out 0-10, pats 10-27, held at 27 (0.9 s), back 27-45
# n2c (tester: "still too fast and it pats too many times: only 3 pats, slow and eased, but not too slow"): three
# pats in turn (left, right, left), each a smooth dip over 9 frames; the montage plays at PAT_RATE (0.78: ~0.38 s a pat,
# out ~0.43 s, back ~0.47 s), the table's length unchanged (the hand-set montage keeps working)
PAT_OUT_K = 10
PAT_HOLD_K = 37                    # the Blueprint holds here: 37 / 30 = 1.233 s of montage time
PAT_BACK_K = 48
PAT_COUNT = 3
# n2d (tester: "pat in different places, as if searching the body"; "on leaving the window the hands should go fully out
# of view before the equip brings the weapon up: now you see the weapon appear, then the equip"): each pat lands on its
# own spot (component cm from the hand's target: X forward, Y right, Z up), the hand gliding between them; with a weapon
# the hands go back DOWN out of view (PAT_DROP from the stance grip), not to the grip, and the IK stays off (the game's
# equip that follows switches it on)
PAT_SPOTS = {"l": ((7.0, -4.0, 0.0), (-6.0, 5.0, 0.0)),      # left: pat 1, pat 3
             "r": ((-5.0, 3.0, 0.0), (6.0, -3.0, 0.0))}      # right: where it waits, pat 2
PAT_DROP = (-6.0, 0.0, -42.0)
# n2e (tester: "still robotic: it moves, then goes down and up; it should be one smooth motion, an eased pat, moving,
# pat, in an arc, natural"): each hand follows one continuous path over the pat timeline (x 0..3): it arrives hovering
# PAT_HOVER above its first spot, drops onto it (eased in, so it lands with some speed), lifts in an arc of PAT_ARC to
# the next spot and lands again, and lifts off at the end; the left pats at x 0.5 and 2.5, the right at 1.5
PAT_HOVER, PAT_PRESS, PAT_ARC = 3.0, 1.5, 6.0
PAT_CONTACTS = {"l": (0.5, 2.5), "r": (1.5,)}


def pat_off(s, x):
    """The hand's offset from its target at pat time x (0..PAT_COUNT): (X fwd, Y right, Z up) cm."""
    sp = PAT_SPOTS[s]
    ct = PAT_CONTACTS[s]
    # waypoints: (time, spot, height); between two contacts an arc
    if s == "l":
        pts = [(0.0, sp[0], PAT_HOVER), (ct[0], sp[0], -PAT_PRESS), (ct[1], sp[1], -PAT_PRESS), (float(PAT_COUNT), sp[1], PAT_HOVER)]
    else:
        pts = [(0.0, sp[0], PAT_HOVER), (ct[0], sp[1], -PAT_PRESS), (float(PAT_COUNT), sp[1], PAT_HOVER)]
    for (t0, p0, z0), (t1, p1, z1) in zip(pts, pts[1:]):
        if t0 <= x <= t1:
            t = (x - t0) / max(t1 - t0, 1e-6)
            hz = smooth(t)
            h = add(p0, mul(sub(p1, p0), hz))
            if z0 < 0 and z1 < 0:                       # contact to contact: lift in an arc
                z = -PAT_PRESS + PAT_ARC * math.sin(math.pi * t)
            elif z1 < 0:                                # hover -> contact: accelerating down (lands with some speed)
                z = z0 + (z1 - z0) * (t * t)
            else:                                       # contact -> hover: decelerating up
                z = z0 + (z1 - z0) * (1 - (1 - t) * (1 - t))
            return (h[0], h[1], h[2] + z)
    return add(sp[-1], (0.0, 0.0, PAT_HOVER))
PAT_WRIST_UP = 35.0                # n2i: the hand bent up at the wrist (fingers toward the back of the hand), degrees
PAT_SPREAD = 26.0                 # cm between the hands (component Y): the right hand's target right of the left's
PAT_DIP = 4.0                      # cm each pat goes down
PAT_IK = ((0.035907, 0.0, 0.06), (1.47, 1.0, 0.3))   # both hands' IK: off at the start, on at frame 44


def _mirror_q(q):
    """A component-space rotation reflected across the XZ plane (left <-> right)."""
    return (-q[0], q[1], -q[2], q[3])


def build_pat_table():
    """2026-10-14 (Nexus, Scorpius34: "loot corpses with both hands"; tester: "the right hand goes out the same way the
    left does, as if patting down and checking the body on the ground"; not the mutant looting animation, it uses a
    knife): AS_ImmLoot_PatTable, one long sequence of 75 segments of 51 frames: family (rifle stand idle / pistol idle /
    bare-hands stand idle) x the 25 touch bins. Both arms, each from its own stance, built like the v1.2.0 touch
    (zonekit/research/touch/README.md): every arm track at the stance, upper arm / forearm solved, elbow pole turning
    out and down, a curved path out (left: through the left / below exit, right: mirrored), the hand following the
    forearm then turning one way round to palm down toward the body (right: the left's orientation mirrored), fingers
    opening (the dialogue gesture's spread hands), two pats (the hands dip in turn), held at frame 27 (the Blueprint
    pauses at 0.9 s while the loot window is open), back by 45. Both hands' IK off at the start and on at 1.4 s (the
    Blueprint hides a held weapon and draws it again after). Played through AM_ImmLoot_Pat (LeftHand + RightHand slot
    tracks, set once by hand in the montage editor), started at the segment."""
    tmpl = unreal.load_asset(f"{DIR}/{NAME}")
    path = f"{DIR}/{NAME_PAT}"
    if not EAL.does_asset_exist(path):
        unreal.AssetToolsHelpers.get_asset_tools().duplicate_asset(NAME_PAT, DIR, tmpl)
    seq = unreal.load_asset(path)
    grab_src = unreal.load_asset(SRC)
    sp_seq = unreal.load_asset(SPREAD_SEQ)
    tracks = [str(x) for x in AL.get_animation_track_names(tmpl)]
    sides = {}
    for s in ("l", "r"):
        arm = [b for b in tracks if f"jnt_{s}_shoulder" in [str(x) for x in AL.find_bone_path_to_root(tmpl, b)]]
        fingers = [b for b in arm if b.startswith(f"jnt_{s}_hand_")]
        sides[s] = dict(arm=arm, fingers=fingers, SH=f"jnt_{s}_shoulder", ARM=f"jnt_{s}_arm", FORE=f"jnt_{s}_fore_arm",
                        HAND=f"jnt_{s}_hand", ROLL=f"jnt_{s}_fore_arm_roll",
                        opens={b: local(sp_seq, b, SPREAD_K)[1] for b in fingers},
                        sign=-1.0 if s == "l" else 1.0)
    # the right hand's orientation = the left's mirrored, corrected by the two hands' reference-pose difference
    ref = tmpl.get_editor_property("skeleton").get_reference_pose()
    def ref_cs(b):
        t = ref.get_ref_bone_pose(b, unreal.AnimPoseSpaces.WORLD)
        return (t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w)
    C_hand = qmul(qinv(_mirror_q(ref_cs("jnt_l_hand"))), ref_cs("jnt_r_hand"))
    _fl, _pl = hand_axes(grab_src)
    WRIST_AX = {"l": unit(cross(_fl, mul(_pl, -1.0)))}   # n2i: hand-local axis bending the fingers toward the back of the hand
    _mv = lambda v: (v[0], -v[1], v[2])   # reflected across XZ; right pose = mirror(left) * C_hand, so v_r = C_hand^-1 M(v_l)
    _flr, _plr = qrot(qinv(C_hand), _mv(_fl)), qrot(qinv(C_hand), _mv(_pl))
    WRIST_AX["r"] = unit(cross(_flr, mul(_plr, -1.0)))
    keys = {b: ([], [], []) for s in sides.values() for b in s["arm"]}
    nseg = 0
    for fam, base_path in PAT_FAMILIES:
        base = unreal.load_asset(base_path)
        cam, _ = cs(base, "jnt_camera", 0)
        st = {}
        for s, d in sides.items():
            sh_p, sh_q = cs(base, d["SH"], 0)
            a_l, f_l, h_l = local(base, d["ARM"], 0), local(base, d["FORE"], 0), local(base, d["HAND"], 0)
            a_q = qmul(sh_q, a_l[1]); A = add(sh_p, qrot(sh_q, a_l[0]))
            f_q = qmul(a_q, f_l[1]); E = add(A, qrot(a_q, f_l[0]))
            R = add(E, qrot(f_q, h_l[0]))
            st[s] = dict(sh_q=sh_q, a_q=a_q, f_q=f_q, A=A, E=E, R=R, h_l=h_l, l1=norm(sub(E, A)), l2=norm(sub(R, E)),
                         rest={b: local(base, b, 0) for b in d["arm"]}, roll_l=local(base, d["ROLL"], 0)[1])
        for ie, elev in enumerate(TOUCH_ELEVS):
            for ia, azim in enumerate(TOUCH_AZIMS):
                er, ar = math.radians(elev), math.radians(azim)
                dirv_e = (math.cos(er) * math.cos(ar), math.cos(er) * math.sin(ar), math.sin(er))
                L = st["l"]
                reach_l = (L["l1"] + L["l2"]) * TOUCH_REACH
                inv = lambda v: tuple((v[j] - TOUCH_MAP[j][1]) / TOUCH_MAP[j][0] for j in range(3))
                u = tuple(dirv_e[j] / TOUCH_MAP[j][0] for j in range(3))
                c_ = sub(add(cam, inv((0.0, 0.0, 0.0))), L["A"])
                qa, qb, qc = dot(u, u), 2 * dot(c_, u), dot(c_, c_) - reach_l * reach_l
                disc = qb * qb - 4 * qa * qc
                t = (-qb + math.sqrt(disc)) / (2 * qa) if disc > 0 else max(10.0, -qb / (2 * qa))
                GL = add(cam, inv(mul(dirv_e, t)))
                goals = {"l": GL, "r": add(GL, (0.0, PAT_SPREAD, 0.0))}
                # n2f (tester: "rotate the hands up, toward the sky; they're a little too far rotated down, so it doesn't
                # look fully like a pat"): n2f tilted the palm normal AWAY from the body's direction (-0.25): tester "tilted
                # the wrong way, the wrists look broken, the hands way too far down". A palm normal tilted toward the
                # body's direction lifts the fingers (n2e: +0.35 * dirv_e, ~10 deg up with the view's downward part);
                # n2g: the horizontal direction only, PAT_PALM_UP 0.55. Tester: "looks like it was when I first asked; the
                # hand needs to go up, rotate it up". Scan: n2e -> n2g raised the fingers 12 deg but the wrist bend stayed
                # 30 deg (the hand turned about the forearm, not up). n2i: n2e's palm; the hand is then bent up at the
                # wrist about its own side axis by PAT_WRIST_UP, as a local rotation on top of the turn (below: bending
                # the target instead made the turn out take the long way, 214 deg in 7 frames)
                PQL = palm_q(grab_src, unit(add((0.0, 0.0, -1.0), mul(dirv_e, 0.35))), (dirv_e[0], dirv_e[1], 0.0))
                PQ = {"l": PQL, "r": qmul(_mirror_q(PQL), C_hand)}
                for s, d in sides.items():
                    S = st[s]
                    G = goals[s]
                    sg = d["sign"]
                    Re = add(S["R"], (TOUCH_END_OFF[0], -sg * TOUCH_END_OFF[1], TOUCH_END_OFF[2]))
                    Cc = add(Re, (TOUCH_EXIT[0], -sg * TOUCH_EXIT[1], TOUCH_EXIT[2]))
                    reach = (S["l1"] + S["l2"]) * TOUCH_REACH
                    eref = (ELBOW_REF[0], -sg * ELBOW_REF[1], ELBOW_REF[2])
                    hint = sub(S["E"], S["A"])
                    RQ = qmul(S["f_q"], S["h_l"][1])
                    pq = PQ[s] if dot4(PQ[s], RQ) >= 0 else tuple(-x for x in PQ[s])
                    prev_tq = None
                    mine = (0, 2) if s == "l" else (1,)   # which of the three pats this hand makes
                    spots = PAT_SPOTS[s]
                    armed = fam in ("ar", "pt")
                    Dn = add(S["R"], (PAT_DROP[0], -sg * PAT_DROP[1], PAT_DROP[2]))   # armed: the way back ends below the view
                    for k in range(PAT_SEG):
                        if k <= PAT_OUT_K:
                            u_ = smooth(k / float(PAT_OUT_K))
                        elif k <= PAT_HOLD_K:
                            u_ = 1.0
                        elif k <= PAT_BACK_K:
                            u_ = 1.0 - smooth((k - PAT_HOLD_K) / float(PAT_BACK_K - PAT_HOLD_K))
                        else:
                            u_ = 0.0
                        # n2e: one continuous path through the pat timeline (pat_off: hover, arcs between spots)
                        xs = 0.0 if k <= PAT_OUT_K else (PAT_COUNT if k >= PAT_HOLD_K else (k - PAT_OUT_K) / float(PAT_HOLD_K - PAT_OUT_K) * PAT_COUNT)
                        off = pat_off(s, xs)
                        Gk = add(G, off)
                        if armed and k > PAT_HOLD_K:
                            # with a weapon: from the last spot down out of view (a little out to the side on the way)
                            w_ = smooth(min(1.0, (k - PAT_HOLD_K) / float(PAT_BACK_K - PAT_HOLD_K)))
                            Cd = add(mul(add(Gk, Dn), 0.5), (0.0, sg * 6.0, 0.0))
                            T = add(add(mul(Gk, (1 - w_) ** 2), mul(Cd, 2 * w_ * (1 - w_))), mul(Dn, w_ * w_))
                        else:
                            T = add(add(mul(Re, (1 - u_) ** 2), mul(Cc, 2 * u_ * (1 - u_))), mul(Gk, u_ * u_))
                        to_t = sub(T, S["A"])
                        l1, l2 = S["l1"], S["l2"]
                        dd = max(abs(l1 - l2) + 0.01, min(reach, norm(to_t)))
                        dv = unit(to_t)
                        a = (l1 * l1 - l2 * l2 + dd * dd) / (2 * dd)
                        h = math.sqrt(max(l1 * l1 - a * a, 0.0))
                        s_ = min(1.0, norm(sub(T, Re)) / max(norm(sub(G, Re)), 1e-6))
                        rf = unit(add(mul(unit(hint), 1.0 - s_), mul(eref, s_)))
                        pole = sub(rf, mul(dv, dot(rf, dv)))
                        pole = unit(pole) if norm(pole) > 1e-6 else unit(cross(dv, (0.0, 0.0, 1.0)))
                        E2 = add(S["A"], add(mul(dv, a), mul(pole, h)))
                        T2 = add(S["A"], mul(dv, dd))
                        r1 = q_between(sub(S["E"], S["A"]), sub(E2, S["A"]))
                        a_q2 = qmul(r1, S["a_q"])
                        r2 = q_between(qrot(r1, sub(S["R"], S["E"])), sub(T2, E2))
                        f_q2 = qmul(r2, qmul(r1, S["f_q"]))
                        kk = k if k <= PAT_HOLD_K else (2 * PAT_HOLD_K - k if k <= 2 * PAT_HOLD_K else 0)
                        wv = smooth(min(1.0, max(0.0, (kk - 5) / 7.0))) if k <= PAT_HOLD_K else smooth(min(1.0, max(0.0, (PAT_HOLD_K + 9 - k) / 9.0)))
                        tq = qmul(qinv(f_q2), pq)
                        if prev_tq is None:
                            if dot4(tq, S["h_l"][1]) < 0:
                                tq = tuple(-x for x in tq)
                        elif dot4(tq, prev_tq) < 0:
                            tq = tuple(-x for x in tq)
                        prev_tq = tq
                        hl = slerp_raw(S["h_l"][1], tq, wv)
                        dlt = qmul(hl, qinv(S["h_l"][1]))
                        ax_ = unit(S["h_l"][0])
                        pr = dot(ax_, dlt[:3])
                        tw = (ax_[0] * pr, ax_[1] * pr, ax_[2] * pr, dlt[3])
                        tn = math.sqrt(sum(x * x for x in tw))
                        tw = tuple(x / tn for x in tw) if tn > 1e-9 else (0.0, 0.0, 0.0, 1.0)
                        _bt = math.radians(PAT_WRIST_UP) * wv / 2   # n2i: bent up at the wrist as the hand turns out
                        _ax = WRIST_AX[s]
                        hl_b = qmul(hl, (_ax[0] * math.sin(_bt), _ax[1] * math.sin(_bt), _ax[2] * math.sin(_bt), math.cos(_bt)))
                        solved = {d["ARM"]: qmul(qinv(S["sh_q"]), a_q2), d["FORE"]: qmul(qinv(a_q2), f_q2), d["HAND"]: hl_b,
                                  d["ROLL"]: qmul(slerp((0.0, 0.0, 0.0, 1.0), tw, 0.5), S["roll_l"])}
                        for b in d["arm"]:
                            l = S["rest"][b]
                            if b in solved:
                                rq = solved[b]
                            elif b in d["opens"]:
                                rq = slerp(l[1], d["opens"][b], wv)
                            else:
                                rq = l[1]
                            keys[b][0].append(unreal.Vector(*l[0]))
                            keys[b][1].append(unreal.Quat(*rq))
                            keys[b][2].append(unreal.Vector(*l[2]))
                nseg += 1
        out.append(f"{NAME_PAT}: family {fam} done ({nseg} segments)")
    ctrl = seq.get_editor_property("controller")
    ctrl.open_bracket("ImmLoot pat table", True)
    ctrl.remove_all_bone_tracks(True)
    ctrl.set_number_of_frames(unreal.FrameNumber(nseg * PAT_SEG - 1), True)
    for b, (pos, rot, scl) in keys.items():
        ctrl.add_bone_curve(b, True)
        ctrl.set_bone_track_keys(b, pos, rot, scl, True)
    ctrl.close_bracket(True)
    for tn_ in [str(x) for x in AL.get_animation_notify_track_names(seq)]:
        AL.remove_animation_notify_events_by_track(seq, tn_)
    track = "ImmLoot"
    if track not in [str(x) for x in AL.get_animation_notify_track_names(seq)]:
        AL.add_animation_notify_track(seq, track, unreal.LinearColor(0.2, 0.8, 0.2, 1.0))
    hik = unreal.load_class(None, "/Script/Stalker2.AnimNotify_HandIK")
    for i in range(nseg):
        for t_, end, bl in (PAT_IK if i >= 50 else PAT_IK[:1]):   # n2d: with a weapon (segments 0-49) no IK-on
            ev = AL.add_animation_notify_event(seq, track, i * PAT_SEG / 30.0 + t_, hik)
            ev.set_editor_property("hand_to_apply", unreal.AnimationHands.BOTH_HAND)
            ev.set_editor_property("blend_time", bl)
            ev.set_editor_property("end_value", end)
    for cn in [str(x) for x in AL.get_animation_curve_names(seq, unreal.RawCurveTrackTypes.RCT_FLOAT)]:
        AL.remove_curve(seq, cn, False)
    AL.add_curve(seq, "left_hand_curve", unreal.RawCurveTrackTypes.RCT_FLOAT, False)
    AL.add_float_curve_keys(seq, "left_hand_curve", [0.0, seq.get_play_length()], [1.0, 1.0])
    out.append(f"{NAME_PAT}: {nseg} segments x {PAT_SEG} frames, len {seq.get_play_length():.2f} s, "
               f"{len(AL.get_animation_notify_events(seq))} notifies, saved {EAL.save_loaded_asset(seq, only_if_is_dirty=False)}")
    mpath = f"{DIR}/AM_ImmLoot_Pat"
    if not EAL.does_asset_exist(mpath):
        f_ = unreal.AnimMontageFactory()
        f_.set_editor_property("source_animation", seq)
        unreal.AssetToolsHelpers.get_asset_tools().create_asset("AM_ImmLoot_Pat", DIR, unreal.AnimMontage, f_)
    m = unreal.load_asset(mpath)
    bi = m.get_editor_property("blend_in"); bi.set_editor_property("blend_time", 0.2); m.set_editor_property("blend_in", bi)
    bo = m.get_editor_property("blend_out"); bo.set_editor_property("blend_time", 0.3); m.set_editor_property("blend_out", bo)
    m.set_editor_property("enable_auto_blend_out", False) if hasattr(m, "enable_auto_blend_out") else None
    out.append(f"AM_ImmLoot_Pat: slots {[str(x) for x in AL.get_montage_slot_names(m)]} (needs LeftHand + RightHand), "
               f"saved {EAL.save_loaded_asset(m, only_if_is_dirty=False)}")


def touch_notifies(seq, mode):
    """The left-hand IK off just after the start, back on at the return (vanilla grab's HandIK notify kind)."""
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
    for t, end, bl in ((0.035907, None, None if mode != "touch" else TOUCH_IK_OFF_BLEND),
                       ({"push": 1.27, "pull": 1.4, "grab": GRAB_IK_ON[0]}.get(mode, TOUCH_IK_ON[0]), 1.0,
                        {"touch": TOUCH_IK_ON[1], "grab": GRAB_IK_ON[1]}.get(mode))):
        new = AL.add_animation_notify_event(seq, track, t, hik)
        new.set_editor_property("hand_to_apply", hand)
        if end is not None:
            new.set_editor_property("end_value", end)
        if bl is not None:
            new.set_editor_property("blend_time", bl)


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
    if mode == "touch":
        out.append(f"TOUCH {name}: return mirrored on {mirror_touch_return(seq)} left-arm tracks")
    touch_notifies(seq, mode)
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


def build_use_table(src, tgt_rot, nkeys, base, name, template, out_dir=None, lower_deg=0.0, max_dist=None, grip_seq=None, azims=None, finger_base=None, hand_roll=0.0, dists=None, follow_pitch=False):
    """follow_pitch (1.3.1, Nexus EMPERORTECH: "standing, an extremely stretched and distorted texture on the sleeve,
    starting from the shoulder, when picking up items and inspecting stashes; not when crouching"; with a wider weapon
    viewmodel FOV): standing, the bare-hands look additive leaves the arms level while the camera pitches, so looking
    down at an item the shoulder and upper arm come into the bottom-left of the view close to the camera, where the
    arms' first-person FOV squeeze stretches them; crouched, the look turns the arms with the view. With follow_pitch the
    shoulder (and the arm with it) turns about jnt_spine_03 by the row's elevation (the view pitch when looking at the
    item), eased in over the reach and out on the way back (jnt_l_shoulder keyed too), as the crouched posture does;
    the arm is solved from the turned shoulder, so the hand still lands on the item."""
    dists_ = dists or DISTS
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
    sh_parent = [str(x) for x in AL.find_bone_path_to_root(base, SHOULDER)][1]
    pp_p, pp_q = cs(base, sh_parent, 0)
    if follow_pitch:
        keys[SHOULDER] = ([], [], [])
    for ie, elev in enumerate(ELEVS):
      th_ = math.radians(-elev) if follow_pitch else 0.0
      Wfull = (0.0, math.sin(th_ / 2), 0.0, math.cos(th_ / 2))
      for dd in dists_:
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
                # follow_pitch: the shoulder rig turned by the view pitch, eased in by frame 10, out over 16-36
                wfp = smoother(min(1.0, f / 10.0)) if f <= 16 else (1.0 - smoother(min(1.0, (f - 16) / 20.0)))
                Wf = slerp((0.0, 0.0, 0.0, 1.0), Wfull, wfp)
                sh_qf = qmul(Wf, sh_q)
                sh_pf = add(sp_p, qrot(Wf, sub(sh_p, sp_p)))
                a_q0 = qmul(sh_qf, ba[1]); A = add(sh_pf, qrot(sh_qf, ba[0]))
                f_q0 = qmul(a_q0, bf[1]); E = add(A, qrot(a_q0, bf[0]))
                RQ = qmul(f_q0, bh[1]); R = add(E, qrot(f_q0, bh[0]))
                H = R
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
                    solved = {ARM: qmul(qinv(sh_qf), a_q2), FORE: qmul(qinv(a_q2), f_q2), HAND: qmul(qinv(f_q2), hq)}
                if follow_pitch:
                    keys[SHOULDER][0].append(unreal.Vector(*bsh[0]))
                    keys[SHOULDER][1].append(unreal.Quat(*(bsh[1] if (f == 0 or f >= 39) else qmul(qinv(pp_q), sh_qf))))
                    keys[SHOULDER][2].append(unreal.Vector(*bsh[2]))
                for b, l in ((ARM, ba), (FORE, bf), (HAND, bh)):
                    keys[b][0].append(unreal.Vector(*l[0]))
                    keys[b][1].append(unreal.Quat(*solved[b]))
                    keys[b][2].append(unreal.Vector(*l[2]))
                if f == 12:
                    errs.append(norm(sub(add(T2, qrot(hq, wpn)), sub(item, bias))))
    nseg = len(ELEVS) * len(dists_) * len(azims_)
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


def build_twist():
    """build 50: AS_ImmLoot_Twist, additive (local space, reference = frame 90): frame 90 + phi turns the upper body
    (jnt_spine_01 and everything above it) by phi degrees about the vertical, -90..+90. Played in DeathSlot (after
    FullBody), frame set every tick to cancel the strafe's turn of the hips."""
    base = unreal.load_asset(BASE_BH)
    hp, hq = cs(base, "jnt_hips", 0)
    sl = local(base, "jnt_spine_01", 0)
    name = "AS_ImmLoot_Twist"
    path = f"{DIR}/{name}"
    if not EAL.does_asset_exist(path):
        unreal.AssetToolsHelpers.get_asset_tools().duplicate_asset(name, DIR, unreal.load_asset(f"{DIR}/{NAME_BH}"))
    seq = unreal.load_asset(path)
    rots = []
    for i in range(181):
        ph = math.radians(i - 90) / 2
        rz = (0.0, 0.0, math.sin(ph), math.cos(ph))
        d = qmul(qmul(qinv(hq), rz), hq)              # the turn about the component vertical, in the hips' frame
        rots.append(unreal.Quat(*qmul(d, sl[1])))
    ctrl = seq.get_editor_property("controller")
    ctrl.open_bracket("ImmLoot twist", True)
    ctrl.remove_all_bone_tracks(True)
    ctrl.remove_all_curves_of_type(unreal.RawCurveTrackTypes.RCT_FLOAT, True)
    ctrl.set_frame_rate(unreal.FrameRate(30, 1), True)
    ctrl.set_number_of_frames(unreal.FrameNumber(180), True)
    if hasattr(ctrl, "add_bone_track"):
        ctrl.add_bone_track("jnt_spine_01", True)
    else:
        ctrl.add_bone_curve("jnt_spine_01", True)
    ctrl.set_bone_track_keys("jnt_spine_01", [unreal.Vector(*sl[0])] * 181, rots, [unreal.Vector(*sl[2])] * 181, True)
    ctrl.close_bracket(True)
    for tn in [str(t) for t in AL.get_animation_notify_track_names(seq)]:
        AL.remove_animation_notify_events_by_track(seq, tn)
    seq.set_editor_property("additive_anim_type", unreal.AdditiveAnimationType.AAT_LOCAL_SPACE_BASE)
    seq.set_editor_property("ref_pose_type", unreal.AdditiveBasePoseType.ABPT_LOCAL_ANIM_FRAME)
    seq.set_editor_property("ref_frame_index", 90)
    out.append(f"TWIST {name}: len {seq.get_play_length():.2f} s, ref frame {seq.get_editor_property('ref_frame_index')}, saved {EAL.save_loaded_asset(seq, only_if_is_dirty=False)}")


def build_arm_hold():
    """build 54: AS_ImmLoot_ArmHold, NOT additive, 3 s constant: the left shoulder, arm, forearm, hand and fingers of the
    empty-handed idle (fp_bh_idle_stand frame 0). Played in the LeftHand slot under our FullBody pickup: the strafe
    animation's own left-arm swing (build 53 probe: the left shoulder turned +-75 deg while the spine did not turn at all)
    is replaced by the rest pose our pickup table was built on, so the table lands as built."""
    base = unreal.load_asset(BASE_BH)
    name = "AS_ImmLoot_ArmHold"
    path = f"{DIR}/{name}"
    if not EAL.does_asset_exist(path):
        unreal.AssetToolsHelpers.get_asset_tools().duplicate_asset(name, DIR, unreal.load_asset(f"{DIR}/{NAME_BH}"))
    seq = unreal.load_asset(path)
    bones = [SHOULDER, ARM, FORE, HAND, "jnt_l_weapon"] + FINGERS + [b for b in ("jnt_l_arm_roll", "jnt_l_fore_arm_roll", "jnt_l_elbow") if True]
    tracks_b = [str(t) for t in AL.get_animation_track_names(base)]
    ctrl = seq.get_editor_property("controller")
    ctrl.open_bracket("ImmLoot arm hold", True)
    ctrl.remove_all_bone_tracks(True)
    ctrl.remove_all_curves_of_type(unreal.RawCurveTrackTypes.RCT_FLOAT, True)
    ctrl.set_frame_rate(unreal.FrameRate(30, 1), True)
    ctrl.set_number_of_frames(unreal.FrameNumber(90), True)
    n = 0
    for b in bones:
        if b not in tracks_b:
            continue
        l = local(base, b, 0)
        if hasattr(ctrl, "add_bone_curve"):
            ctrl.add_bone_curve(b, True)
        else:
            ctrl.add_bone_track(b, True)
        ctrl.set_bone_track_keys(b, [unreal.Vector(*l[0])] * 91, [unreal.Quat(*l[1])] * 91, [unreal.Vector(*l[2])] * 91, True)
        n += 1
    ctrl.close_bracket(True)
    for tn in [str(t) for t in AL.get_animation_notify_track_names(seq)]:
        AL.remove_animation_notify_events_by_track(seq, tn)
    seq.set_editor_property("additive_anim_type", unreal.AdditiveAnimationType.AAT_NONE)
    out.append(f"ARMHOLD {name}: {n} tracks, len {seq.get_play_length():.2f} s, saved {EAL.save_loaded_asset(seq, only_if_is_dirty=False)}")


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
    pick_only = ARGS.get("PART", "") == "pickstand"   # 1.3.1: only the standing empty-hands pickup table (follow_pitch)
    if ARGS.get("PART", "") == "grabfam":   # n2j: the armed pickup per family, the touch's return
        for fam in ("ar", "pt"):
            build_grab_family(fam)
        raise SystemExit
    if ARGS.get("PART", "") == "pat":   # both hands on bodies
        build_pat_table()
        raise SystemExit
    if ARGS.get("PART", "") == "doorfam":   # door build B: the doors with a weapon, per family
        for fam in ("ar", "pt"):
            for md in ("push", "pull"):
                build_door_family(fam, md)
        raise SystemExit
    if ARGS.get("PART", "") == "touchpt":   # build w: the pistol touches; build x: and the long guns'
        for fam in ("pt", "ar"):
            for i in range(len(TOUCH_ELEVS) * len(TOUCH_AZIMS)):
                build_touch_pistol(i, fam)
        raise SystemExit
    if ARGS.get("PART", "") == "touchret":   # only re-mirror the existing touch assets' return (build s)
        for i in range(len(TOUCH_ELEVS) * len(TOUCH_AZIMS)):
            s_ = unreal.load_asset(f"{DIR}/{NAME_TOUCH}{i}")
            nm_ = mirror_touch_return(s_)
            touch_notifies(s_, "touch")   # build t: the IK-on notify earlier and slower
            ev_ = [(round(AL.get_anim_notify_event_trigger_time(e), 3), e.notify.get_editor_property("end_value"), round(e.notify.get_editor_property("blend_time"), 2)) for e in AL.get_animation_notify_events(s_) if e.notify]
            out.append(f"{NAME_TOUCH}{i}: {nm_} tracks, IK notifies {ev_}, saved {EAL.save_loaded_asset(s_, only_if_is_dirty=False)}")
        raise SystemExit
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
    if pick_only:
        build_use_table(src, tgt_rot, nkeys, unreal.load_asset(BASE_BH), "AS_ImmLoot_GrabBHAdd", unreal.load_asset(f"{DIR}/{NAME_BH}"),
                        out_dir=DIR, grip_seq="src", azims=list(range(-30, 61, 5)), dists=[60], follow_pitch=True)
        raise SystemExit
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
        # (release cleanup 2026-10-13: the vanilla-grab touches AS_ImmLoot_Touch0..24 (build_touch) are no longer built:
        # every armed body / stash touch is a family touch)
        for fam in ("pt", "ar"):   # builds w, x
            for i in range(len(TOUCH_ELEVS) * len(TOUCH_AZIMS)):
                build_touch_pistol(i, fam)
    if ARGS.get("DOOR", "1") == "1":
        for fam in ("ar", "pt"):   # door build B
            for md in ("push", "pull"):
                build_door_family(fam, md)
        build_doors(src, seq, path_h, path_q, nkeys, tgt_rot)
    if ARGS.get("BH", "1") == "1":
        build_bh_reach_table(src, seq, tgt_rot, nkeys)   # build 12 (build_bh_table = checkpoint-b11)
    if ARGS.get("PICKADD", "0") == "1":    # build 38
        build_use_table(src, tgt_rot, nkeys, unreal.load_asset(BASE_BH), "AS_ImmLoot_GrabBHAdd", unreal.load_asset(f"{DIR}/{NAME_BH}"),
                        out_dir=DIR, grip_seq="src", azims=list(range(-30, 61, 5)), dists=[60], follow_pitch=True)   # build 39; build 42: the vanilla grab's fingers; 1.3.1: follow_pitch
    if ARGS.get("ARMHOLD", "0") == "1":
        build_arm_hold()
    if ARGS.get("TWIST", "0") == "1":
        build_twist()
    if ARGS.get("PICKCROUCH", "0") == "1":    # build 41: crouched, its own rest pose (the stand table's delta barely moved the
        # crouched arm: build 40 probe, the hand ended where it started)
        build_use_table(src, tgt_rot, nkeys, unreal.load_asset("/Game/_STALKER2/Animations/Player/AnimSequences/bh/crouch/fp_bh_idle_crouch"),
                        "AS_ImmLoot_GrabBHAddCrouch", unreal.load_asset(f"{DIR}/{NAME_BH}"), out_dir=DIR,
                        grip_seq="src", azims=list(range(-30, 61, 5)), dists=[60], finger_base=unreal.load_asset(BASE_BH),
                        hand_roll=-35.0)   # build 46: -35 (tester: -70 "too far", the item clipped); build 45 (tester: crouched "rotate clockwise so the back of the hand faces up, now it faces left")   # build 42/44: the vanilla grab's fingers, from the standing rest
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
except SystemExit:
    pass
except Exception:
    import traceback
    out.append("EXCEPTION " + traceback.format_exc())
os.makedirs(SCRATCH, exist_ok=True)
open(os.path.join(SCRATCH, "make_grab_seq.txt"), "w").write("\n".join(out))
