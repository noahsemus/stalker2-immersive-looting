"""Camera = VB jnt_camera (child of spine_03, = camera relative to spine_03 in each sequence) copied onto jnt_camera (CopyBone_2, active)."""
import os, math, unreal
AL = unreal.AnimationLibrary
def qmul(a, b):
    ax, ay, az, aw = a; bx, by, bz, bw = b
    return (aw*bx+ax*bw+ay*bz-az*by, aw*by-ax*bz+ay*bw+az*bx, aw*bz+ax*by-ay*bx+az*bw, aw*bw-ax*bx-ay*by-az*bz)
def qinv(a): return (-a[0], -a[1], -a[2], a[3])
def qrot(a, p):
    r = qmul(qmul(a, (p[0], p[1], p[2], 0.0)), qinv(a)); return r[:3]
def ang(q):
    w = max(-1.0, min(1.0, abs(q[3]))); return math.degrees(2*math.acos(w))
def yaw(q):
    v = qrot(q, (1, 0, 0)); return math.degrees(math.atan2(v[1], v[0]))
CH = ["jnt_root", "jnt_hips", "jnt_spine_01", "jnt_spine_02", "jnt_spine_03", "jnt_l_shoulder", "jnt_l_arm", "jnt_l_fore_arm", "jnt_l_hand", "jnt_camera"]
PAR = {CH[i]: CH[i-1] for i in range(1, 9)}; PAR["jnt_root"] = None; PAR["jnt_camera"] = "jnt_root"; PAR["VB"] = "jnt_spine_03"
BONES = CH + ["VB"]
def raw(seq, k):
    d = {}
    for b in CH:
        t = AL.get_bone_pose_for_frame(seq, b, k, False)
        d[b] = ((t.translation.x, t.translation.y, t.translation.z), (t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w))
    # virtual bone = camera relative to spine_03 in this sequence
    P, M = csx(d, CH)
    rot = qmul(qinv(M["jnt_spine_03"]), M["jnt_camera"])
    tr = qrot(qinv(M["jnt_spine_03"]), tuple(a - b for a, b in zip(P["jnt_camera"], P["jnt_spine_03"])))
    d["VB"] = (tr, rot); return d
def csx(L, bones):
    P, M = {}, {}
    for b in bones:
        p = PAR[b]
        if p is None: P[b], M[b] = L[b][0], L[b][1]
        else: M[b] = qmul(M[p], L[b][1]); P[b] = tuple(a+c for a, c in zip(P[p], qrot(M[p], L[b][0])))
    return P, M
def meshrot(L):
    m = {}
    for b in BONES:
        p = PAR[b]; m[b] = L[b][1] if p is None else qmul(m[p], L[b][1])
    return m
def msadd(base, anim, ref, mask=None):
    Mb, Ma, Mr = meshrot(base), meshrot(anim), meshrot(ref); M, Lt = {}, {}
    for b in BONES:
        use = mask is None or b in mask
        M[b] = qmul(qmul(Ma[b], qinv(Mr[b])) if use else (0, 0, 0, 1), Mb[b])
        Lt[b] = tuple(x + ((y - z) if use else 0.0) for x, y, z in zip(base[b][0], anim[b][0], ref[b][0]))
    return {b: (Lt[b], M[b] if PAR[b] is None else qmul(qinv(M[PAR[b]]), M[b])) for b in BONES}
def lb(base, over, bones): return {b: (over[b] if b in bones else base[b]) for b in BONES}
LOWER = {"jnt_hips", "jnt_spine_01", "jnt_spine_02"}
LEGS = {"jnt_hips", "jnt_spine_01"}
UNDERHIPS = {"jnt_hips"}
LHAND = {"jnt_l_shoulder", "jnt_l_arm", "jnt_l_fore_arm", "jnt_l_hand"}
def camera(L):
    P, M = csx(L, BONES); return P["VB"], M["VB"], P, M
out = []
def qyaw(deg):
    h = math.radians(deg) / 2; return (0.0, 0.0, math.sin(h), math.cos(h))
def lhand_table(L, I, theta):
    """LeftHand slot: idle arm locals, l_shoulder local = inv(S3 predicted for yaw theta) * idle shoulder CS (rigid turn about the camera axis)."""
    Pi, Mi = csx(I, BONES)
    R = qyaw(theta)
    s3p = qrot(R, Pi["jnt_spine_03"]); s3q = qmul(R, Mi["jnt_spine_03"])     # predicted spine_03 CS (turn about z through origin = camera axis)
    shq = qmul(qinv(s3q), Mi["jnt_l_shoulder"]); sht = qrot(qinv(s3q), tuple(a - b for a, b in zip(Pi["jnt_l_shoulder"], s3p)))
    out = dict(L)
    for b in LHAND: out[b] = I[b]
    out["jnt_l_shoulder"] = (sht, shq); return out
for name, idlep, adds in [("stand", "/Game/_STALKER2/Animations/Player/AnimSequences/bh/stand/fp_bh_idle_stand",
          ["bh/stand/walk/Additive/AS_fp_bh_walk_left_add", "bh/stand/walk/Additive/AS_fp_bh_walk_right_add", "bh/stand/run/Additive/fp_bh_run_left_add", "bh/stand/run/Additive/fp_bh_run_right_add", "bh/stand/walk/Additive/AS_fp_bh_walk_fwd_add", "bh/stand/walk/Additive/AS_fp_bh_walk_fl_add"]),
         ("crouch", "/Game/_STALKER2/Animations/Player/AnimSequences/bh/crouch/fp_bh_idle_crouch", ["bh/crouch/move/Additive/fp_bh_crouch_left_add", "bh/crouch/move/Additive/fp_bh_crouch_right_add"])]:
    idle = unreal.load_asset(idlep); I = raw(idle, 0)
    c0, q0, P0, M0 = camera(I)
    rel0 = tuple(a - b for a, b in zip(P0["jnt_l_hand"], c0)); sh0 = tuple(a - b for a, b in zip(P0["jnt_l_shoulder"], c0))
    for a in adds:
        s = unreal.load_asset("/Game/_STALKER2/Animations/Player/AnimSequences/" + a); n = AL.get_num_frames(s)
        rA, rG, th = [], [], []
        for k in range(0, n, max(1, n // 16)):
            A = raw(s, k); LA = msadd(I, A, I)
            c, q, P, M = camera(LA)
            ax = qrot(qinv(M0["jnt_spine_03"]), (1, 0, 0)); v = qrot(M["jnt_spine_03"], ax); theta = math.degrees(math.atan2(v[1], v[0]))   # what the actor would read (spine_03 component yaw vs rest)
            th.append(theta)
            rA.append(math.dist(tuple(x - y for x, y in zip(P["jnt_l_hand"], c)), rel0))
            LG = lhand_table(LA, I, theta)
            cg, qg, PG, MG = camera(LG)
            rG.append((math.dist(tuple(x - y for x, y in zip(PG["jnt_l_hand"], cg)), rel0), math.dist(tuple(x - y for x, y in zip(PG["jnt_l_shoulder"], cg)), sh0), ang(qmul(MG["jnt_l_hand"], qinv(M0["jnt_l_hand"]))), math.dist(cg, c0)))
        out.append(f"{name} {s.get_name()}: spine_03 yaw {min(th):+.0f}..{max(th):+.0f} | now (FullBody additive only): hand moves {max(rA):.1f} cm vs camera | LeftHand table: hand {min(r[0] for r in rG):.1f}..{max(r[0] for r in rG):.1f} cm, shoulder {max(r[1] for r in rG):.1f} cm, hand rot {max(r[2] for r in rG):.0f} deg, camera {max(r[3] for r in rG):.1f} cm")
open(os.path.join(SCRATCH, "simtable.txt"), "w").write("\n".join(out))
