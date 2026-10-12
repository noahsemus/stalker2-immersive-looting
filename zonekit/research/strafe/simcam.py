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
for name, idlep, adds in [("stand", "/Game/_STALKER2/Animations/Player/AnimSequences/bh/stand/fp_bh_idle_stand",
          ["bh/stand/walk/Additive/AS_fp_bh_walk_left_add", "bh/stand/walk/Additive/AS_fp_bh_walk_right_add", "bh/stand/run/Additive/fp_bh_run_left_add", "bh/stand/walk/Additive/AS_fp_bh_walk_fwd_add"]),
         ("crouch", "/Game/_STALKER2/Animations/Player/AnimSequences/bh/crouch/fp_bh_idle_crouch", ["bh/crouch/move/Additive/fp_bh_crouch_left_add"])]:
    idle = unreal.load_asset(idlep); I = raw(idle, 0)
    c0, q0, P0, M0 = camera(I)
    out.append(f"#### {name} idle: VB camera pos {tuple(round(v,1) for v in c0)} (jnt_camera {tuple(round(v,1) for v in P0['jnt_camera'])}) yaw {yaw(q0):.1f}")
    if name == "crouch":
        st = raw(unreal.load_asset("/Game/_STALKER2/Animations/Player/AnimSequences/bh/stand/fp_bh_idle_stand"), 0)
        Cx = lb(I, st, set(BONES) - LEGS)   # stand frame held in MainActionSlot while crouched, standing still
        c, q, P, M = camera(Cx)
        out.append(f"   crouched, standing still, stand idle frame 0 in MainActionSlot: camera moves {tuple(round(a-b,1) for a,b in zip(c,c0))} yaw {yaw(q)-yaw(q0):+.1f}")
    for a in adds:
        s = unreal.load_asset("/Game/_STALKER2/Animations/Player/AnimSequences/" + a); n = AL.get_num_frames(s)
        res = {m: [] for m in "ABCDF"}
        for k in range(0, n, max(1, n // 10)):
            A = raw(s, k)
            LA = msadd(I, A, I); LB = msadd(I, A, I, LOWER)
            modes = {"A": LA, "B": LB, "C": lb(LA, I, set(BONES) - LEGS), "D": lb(LA, I, LHAND), "F": lb(LA, I, set(BONES) - UNDERHIPS)}
            for m, L in modes.items():
                c, q, P, M = camera(L)
                res[m].append((math.dist(c, c0), abs(yaw(q) - yaw(q0)), c[2] - c0[2]))
        out.append(f"== {s.get_name()}: camera change vs idle (max over cycle): " + " | ".join(f"{m}: pos {max(r[0] for r in v):.1f} cm (height {min(r[2] for r in v):+.1f}..{max(r[2] for r in v):+.1f}), yaw {max(r[1] for r in v):.0f} deg" for m, v in res.items()))
out.append("A=vanilla/FullBody additive now, B=AdditiveMovingUpperBody=1, C=MainActionSlot idle hold, D=LeftHand idle-arm hold, F=UpperBody slot idle hold")
open(os.path.join(SCRATCH, "simcam.txt"), "w").write("\n".join(out))
