import json, sys, os, math, re
SIM = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sim"); sys.path.insert(0, SIM)
from simcore import *
D = json.load(open(os.path.join(SIM, "simdump.json")))
sk = Skel(D); B = sk.bones; I = sk.idx
VBP = {"VB jnt_r_knee_target": "jnt_r_foot", "VB jnt_l_knee_target": "jnt_l_foot", "VB jnt_camera": "jnt_spine_03", "VB jnt_weapon": "jnt_spine_03", "VB jnt_item": "jnt_spine_03", "VB jnt_r_hand_jnt_weapon": "jnt_r_hand"}
for v, p in VBP.items(): sk.parents[I[v]] = I[p]
sk.order = sk._order()
S = D["seqs"]
def full(key, k): s = S[key]; return to_pose(s["full"][s["frames"].index(k)])
LEFT = set(re.findall(r'BoneName="([^"]*)"', open(os.path.join(SIM, "masks", "left_hand_blend_mask.t3d"), encoding="utf-8", errors="replace").read()))
H, VCAM, SH, S3, ARMB = I["jnt_l_hand"], I["VB jnt_camera"], I["jnt_l_shoulder"], I["jnt_spine_03"], I["jnt_l_arm"]
def tmul(a, b): return (qmul(a[0], b[0]), vadd(a[1], qrot(a[0], b[1])))
def tinv(a): qi = qinv(a[0]); return (qi, qrot(qi, vmul(a[1], -1)))
base = full("idle", 0); Cb = comp(sk, base)
CAMR = Cb[VCAM]; SHR_in_cam = tmul(tinv(CAMR), Cb[SH]); S3R_in_cam = tmul(tinv(CAMR), Cb[S3])
g0 = full("grab", 0)
def look(f): return ms_delta(sk, full("look", f), full("idle", 0))
def s3_in_cam(C): return tmul(tinv(C[VCAM]), C[S3])
def slot_from_s3cam(s3c):
    X = tmul(tinv(s3c), SHR_in_cam); pose = copy(base); pose[SH] = [qnorm(X[0]), X[1]]; return pose
def apply_slot(pose, slot, alpha=1.0):
    out = []
    for i in range(len(B)):
        if B[i] in LEFT and slot is not None:
            if alpha >= 1: out.append(list(slot[i]))
            else: out.append(lbb_local(sk, [pose[i]], [slot[i]], [alpha])[0])
        else: out.append(list(pose[i]))
    return out
def finish(pose, gdelta, slot=None, ld=None, alpha=1.0):
    pose = apply_slot(pose, slot, alpha) if slot is not None else pose
    if ld is not None: pose = apply_ms(sk, pose, ld)
    C0 = comp(sk, pose); cam = C0[VCAM]
    C = comp(sk, apply_local(pose, gdelta))
    return C, cam
def handcam(C, cam): return qrot(qinv(cam[0]), vsub(C[H][1], cam[1]))
def rel_feats(s3c):
    """yaw/pitch/roll of s3c rotation relative to rest s3c rotation, expressed in camera axes; translation relative to rest"""
    dq = qmul(s3c[0], qinv(S3R_in_cam[0]))     # rotation taking rest -> now, in camera frame
    f = qrot(dq, (1,0,0)); l = qrot(dq, (0,1,0)); u = qrot(dq,(0,0,1))
    yaw = math.degrees(math.atan2(f[1], f[0])); pit = math.degrees(math.asin(max(-1,min(1,f[2]))))
    roll = math.degrees(math.atan2(l[2], u[2]))
    return yaw, pit, roll, s3c[1]
MOVES = ["walk_left", "walk_right", "run_left", "run_right", "walk_fwd"]
DELTAS = {mv: [ms_delta(sk, full(mv, k), base) for k in S[mv]["frames"]] for mv in MOVES}
D2 = json.load(open(r"C:/Users/noahs/AppData/Local/Temp/stalker2-harness/rev_dump2.json"))
for k, v in D2["seqs"].items(): S[k] = {"frames": v["frames"], "full": [[r + [1,1,1] for r in fr] for fr in v["full"]]}
ALLMV = ["walk_left","walk_right","walk_fwd","walk_fl","walk_fr","walk_bl","walk_br","walk_bwd",
         "run_left","run_right","run_fwd","run_fl","run_fr","run_bl","run_br","run_bwd",
         "jog_fwd","jog_fl","jog_fr","sprint_fwd","sprint_fl","sprint_fr","turn90r"]
_dc = {}
def deltas(mv):
    if mv not in _dc: _dc[mv] = [ms_delta(sk, full(mv, k), base) for k in S[mv]["frames"]]
    return _dc[mv]
def blend_deltas(ds, ws):
    """BlendPosesTogether of additive deltas: weighted quat sum (aligned to first) normalized, translations summed"""
    out = []
    for b in range(len(B)):
        q0 = ds[0][b][0]; acc = [0,0,0,0]; t = [0,0,0]
        for d, w in zip(ds, ws):
            q, tt = d[b]
            if sum(x*y for x, y in zip(q, q0)) < 0: q = tuple(-x for x in q)
            acc = [a + w*x for a, x in zip(acc, q)]; t = [a + w*x for a, x in zip(t, tt)]
        out.append([qnorm(tuple(acc)), tuple(t)])
    return out
def phase_delta(mv, ph):
    ds = deltas(mv); return ds[int(ph * len(ds)) % len(ds)]
