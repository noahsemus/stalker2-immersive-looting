"""Candidate f refined: LeftHand-slot re-root of jnt_l_shoulder, CAMERA-relative (shoulder comp = cam_now * cam_rest^-1 * shoulder_rest).
Lookup variants: exact; 1-D yaw table (mean of samples per 5 deg bin); nearest-neighbour table over sampled spine_03-in-camera
transforms (samples: every 2nd frame of the 4 strafe anims at blend weights .2/.4/.6/.8/1; tested on other weights).
Also: where the stretched clavicle lies in camera space (x = forward; x<0 is behind the eye = never on screen).
Usage: sim3.py [lookframe]"""
import json, sys, os, math, itertools, re
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from simcore import *
D = json.load(open(os.path.join(HERE, "simdump.json")))
sk = Skel(D); B = sk.bones; I = sk.idx
VBP = {"VB jnt_r_knee_target": "jnt_r_foot", "VB jnt_l_knee_target": "jnt_l_foot", "VB jnt_camera": "jnt_spine_03",
       "VB jnt_weapon": "jnt_spine_03", "VB jnt_item": "jnt_spine_03", "VB jnt_r_hand_jnt_weapon": "jnt_r_hand"}
for v, p in VBP.items(): sk.parents[I[v]] = I[p]
sk.order = sk._order()
S = D["seqs"]
def full(key, k): s = S[key]; return to_pose(s["full"][s["frames"].index(k)])
LEFT = set(re.findall(r'BoneName="([^"]*)"', open(os.path.join(HERE, "masks", "left_hand_blend_mask.t3d"), encoding="utf-8", errors="replace").read()))
LOOKF = int(sys.argv[1]) if len(sys.argv) > 1 else 15
STRIDE = int(sys.argv[2]) if len(sys.argv) > 2 else 2
TW = tuple(float(x) for x in sys.argv[3].split(",")) if len(sys.argv) > 3 else (0.2, 0.4, 0.6, 0.8, 1.0)
SEGONLY = len(sys.argv) > 4
H, VCAM, SH, S3, ARMB = I["jnt_l_hand"], I["VB jnt_camera"], I["jnt_l_shoulder"], I["jnt_spine_03"], I["jnt_l_arm"]
def tmul(a, b):   # a then... component composition: parent a, child local b
    return (qmul(a[0], b[0]), vadd(a[1], qrot(a[0], b[1])))
def tinv(a): qi = qinv(a[0]); return (qi, qrot(qi, vmul(a[1], -1)))
base = full("idle", 0); Cb = comp(sk, base)
CAMR = Cb[VCAM]; SHR_in_cam = tmul(tinv(CAMR), Cb[SH])
look_delta = ms_delta(sk, full("look", LOOKF), full("idle", 0))
g0 = full("grab", 0)
MOVES = [("walk_left", "idle"), ("walk_right", "idle"), ("run_left", "idle"), ("run_right", "idle")]
DELTAS = {mv: [ms_delta(sk, full(mv, k), full(mb, 0)) for k in S[mv]["frames"]] for mv, mb in MOVES}
def loco(mv, i, w=1.0): return apply_ms(sk, base, DELTAS[mv][i], w=w)
def s3_in_cam(C): return tmul(tinv(C[VCAM]), C[S3])
def slot_from_s3cam(s3c):
    """shoulder local so that shoulder-in-camera = rest shoulder-in-camera, given spine_03-in-camera"""
    X = tmul(tinv(s3c), SHR_in_cam)
    pose = copy(base); pose[SH] = [qnorm(X[0]), X[1]]; return pose
def finish(pose, gdelta, slot=None):
    if slot is not None: pose = [list(slot[i]) if B[i] in LEFT else list(pose[i]) for i in range(len(B))]
    pose = apply_ms(sk, pose, look_delta)
    C0 = comp(sk, pose); cam = C0[VCAM]
    C = comp(sk, apply_local(pose, gdelta))
    return C, cam
def yaw_s3(s3c): v = qrot(s3c[0], qrot(qinv(tmul(tinv(CAMR), Cb[S3])[0]), (1, 0, 0))); return math.degrees(math.atan2(v[1], v[0]))
# samples
TRAIN_W, TEST_W = TW, (0.1, 0.3, 0.5, 0.7, 0.9, 1.0)
samples = []
for mv, _ in MOVES:
    for i in range(0, len(DELTAS[mv]), STRIDE):
        for w in TRAIN_W:
            samples.append(s3_in_cam(comp(sk, loco(mv, i, w))))
samples.append(s3_in_cam(Cb))
def feat_dist(a, b): return vlen(vsub(a[1], b[1])) + 0.5 * qangle(a[0], b[0])
def nn(s3c): return min(samples, key=lambda s: feat_dist(s, s3c))
BIN = 5.0; yb = {}
for s in samples: yb.setdefault(round(yaw_s3(s) / BIN) * BIN, []).append(s)
def mean_tf(lst):
    q0 = lst[0][0]; acc = [0, 0, 0, 0]; t = [0, 0, 0]
    for q, p in lst:
        if sum(a*b for a, b in zip(q, q0)) < 0: q = tuple(-x for x in q)
        acc = [a + b for a, b in zip(acc, q)]; t = [a + b for a, b in zip(t, p)]
    return qnorm(tuple(acc)), tuple(x / len(lst) for x in t)
YT = {b: mean_tf(v) for b, v in yb.items()}
def ylook(s3c):
    b = round(yaw_s3(s3c) / BIN) * BIN
    return YT[b] if b in YT else YT[min(YT, key=lambda x: abs(x - b))]
out = []
def P(s): out.append(s); print(s)
P(f"samples {len(samples)}, yaw bins {len(YT)}; look frame {LOOKF}")
# stretch visibility: natural vs re-rooted clavicle root / shoulder joint, camera space
for mv, _ in MOVES:
    xs = []
    for i in range(len(DELTAS[mv])):
        C = comp(sk, loco(mv, i)); cam = C[VCAM]
        nat_sh = qrot(qinv(cam[0]), vsub(C[SH][1], cam[1])); nat_arm = qrot(qinv(cam[0]), vsub(C[ARMB][1], cam[1]))
        xs.append((nat_sh[0], nat_arm[0], vlen(vsub(nat_sh, SHR_in_cam[1]))))
    P(f"{mv}: natural clavicle root x(fwd) {min(a for a,_,_ in xs):.0f}..{max(a for a,_,_ in xs):.0f} cm, natural shoulder joint x {min(b for _,b,_ in xs):.0f}..{max(b for _,b,_ in xs):.0f}; re-rooted clavicle root fixed at {tuple(round(v) for v in SHR_in_cam[1])}; gap {min(c for *_,c in xs):.0f}-{max(c for *_,c in xs):.0f} cm")
SEGS = {44: "elev-50 az0", 66: "elev-35 az+15", 120: "elev+10 az0"}
if SEGONLY: SEGS = {44: "elev-50 az0"}
for seg, segname in SEGS.items():
    gdelta = local_delta(full("grab", seg * 45 + 15), g0)
    Cs, cams = finish(copy(base), gdelta); still = vsub(Cs[H][1], cams[1])
    P(f"\nseg {seg} ({segname}) t=0.50 s: still hand rel cam {tuple(round(x,1) for x in still)}  [max hand displacement over all frames, per test blend weight]")
    for var in (("f_nn_table", "f_nn_table_lag1") if SEGONLY else ("none", "f_exact_cam", "f_yaw_table", "f_nn_table", "f_nn_table_lag1")):
        cells = []
        for mv, _ in MOVES:
            worst = []
            for w in TEST_W:
                m = 0; prev = None
                for i in range(0, len(DELTAS[mv]), 1 if w == 1.0 else 3):
                    lp = loco(mv, i, w); C0 = comp(sk, lp); s3c = s3_in_cam(C0)
                    if var == "none": slot = None
                    elif var == "f_exact_cam": slot = slot_from_s3cam(s3c)
                    elif var == "f_yaw_table": slot = slot_from_s3cam(ylook(s3c))
                    elif var == "f_nn_table": slot = slot_from_s3cam(nn(s3c))
                    else: slot = slot_from_s3cam(nn(prev if prev is not None else s3c))
                    prev = s3c
                    C, cam = finish(lp, gdelta, slot)
                    m = max(m, vlen(vsub(vsub(C[H][1], cam[1]), still)))
                worst.append(m)
            cells.append(f"{mv} " + "/".join(f"{x:.0f}" for x in worst))
        P(f"  {var:16s} " + " | ".join(cells))
open(os.path.join(HERE, f"sim3_out_look{LOOKF}" + (f"_stride{STRIDE}" if SEGONLY else "") + ".txt"), "w").write("\n".join(out))
