"""Candidate f: LeftHand-slot 're-root' of the left arm (non-additive, local, left_hand_blend_mask): jnt_l_shoulder's local
rotation+translation chosen so the shoulder's component transform equals the standing rest one; the rest of the left arm = rest
locals; our FullBody grab additive stays as is. Variants: exact per frame (upper bound), table binned by spine_03 yaw built from
(1) an orbit-about-camera model, (2) the mean of the real strafe frames per bin; 1-frame lag; partial blend weights.
Usage: sim2.py [lookframe] [binsize]"""
import json, sys, os, math, itertools
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
import re
LEFT = set(re.findall(r'BoneName="([^"]*)"', open(os.path.join(HERE, "masks", "left_hand_blend_mask.t3d"), encoding="utf-8", errors="replace").read()))
LOOKF = int(sys.argv[1]) if len(sys.argv) > 1 else 15
BIN = float(sys.argv[2]) if len(sys.argv) > 2 else 5.0
H, VCAM, CAM, SH, S3 = I["jnt_l_hand"], I["VB jnt_camera"], I["jnt_camera"], I["jnt_l_shoulder"], I["jnt_spine_03"]
ARMB = I["jnt_l_arm"]
def yaw_of(q, axis): v = qrot(q, axis); return math.degrees(math.atan2(v[1], v[0]))
def wrap(a): return (a + 180) % 360 - 180

out = []
def P(s): out.append(s); print(s)
cfg = dict(base="idle", look="look", lookbase="idle", grab="grab", moves=[("walk_left", "idle"), ("walk_right", "idle"), ("run_left", "idle"), ("run_right", "idle")])
base = full("idle", 0); Cb = comp(sk, base)
# spine_03 axis that points forward at rest
FWD3 = qrot(qinv(Cb[S3][0]), (1.0, 0.0, 0.0))
def th3(C): return wrap(yaw_of(C[S3][0], FWD3) - yaw_of(Cb[S3][0], FWD3))
look_delta = ms_delta(sk, full("look", LOOKF), full("idle", 0))
g0 = full("grab", 0)

def loco(mv, mb, k, w=1.0):
    return apply_ms(sk, base, ms_delta(sk, full(mv, k), full(mb, 0)), w=w)

def reroot_slot(s3q, s3t):
    """LeftHand slot pose: rest locals, except jnt_l_shoulder placed so its component transform = rest"""
    pose = copy(base)
    shq, sht = Cb[SH]
    pose[SH] = [qnorm(qmul(qinv(s3q), shq)), qrot(qinv(s3q), vsub(sht, s3t))]
    return pose

def finish(pose, gdelta, slot=None):
    if slot is not None:
        pose = [list(slot[i]) if B[i] in LEFT else list(pose[i]) for i in range(len(B))]   # LBB_4, weight 1, local
    pose = apply_ms(sk, pose, look_delta)
    C0 = comp(sk, pose); cam = C0[VCAM]
    pose = apply_local(pose, gdelta)
    C = comp(sk, pose)
    return C, cam, C0

# orbit model check + table building
rows_all = {}
P(f"rest: spine_03 to VB camera {vlen(vsub(Cb[VCAM][1], Cb[S3][1])):.1f} cm; L shoulder joint (jnt_l_arm) rel cam {tuple(round(a-b,1) for a,b in zip(Cb[ARMB][1], Cb[VCAM][1]))}")
bins = {}
for mv, mb in cfg["moves"]:
    errs, shd, ths = [], [], []
    for k in S[mv]["frames"]:
        C = comp(sk, loco(mv, mb, k)); th = th3(C); ths.append(th)
        cam = C[VCAM][1]
        Rz = qaxis((0, 0, 1), th)
        pred = vadd(cam, qrot(Rz, vsub(Cb[S3][1], Cb[VCAM][1])))
        errs.append(vlen(vsub(C[S3][1], pred)))
        shd.append(vlen(vsub(C[ARMB][1], Cb[ARMB][1])))
        b = round(th / BIN) * BIN
        bins.setdefault(b, []).append((C[S3][0], C[S3][1]))
    P(f"{mv}: spine_03 yaw {min(ths):+.1f}..{max(ths):+.1f}; orbit-about-camera model error {min(errs):.1f}-{max(errs):.1f} cm; L shoulder joint moved {min(shd):.1f}-{max(shd):.1f} cm")
def mean_tf(lst):
    q0 = lst[0][0]; acc = [0, 0, 0, 0]; t = [0, 0, 0]
    for q, p in lst:
        if sum(a*b for a, b in zip(q, q0)) < 0: q = tuple(-x for x in q)
        acc = [a + b for a, b in zip(acc, q)]; t = [a + b for a, b in zip(t, p)]
    return qnorm(tuple(acc)), tuple(x / len(lst) for x in t)
TABLE_MEAN = {b: mean_tf(v) for b, v in bins.items()}
def table_orbit(th, cam):
    Rz = qaxis((0, 0, 1), th)
    return qmul(Rz, Cb[S3][0]), vadd(cam, qrot(Rz, vsub(Cb[S3][1], Cb[VCAM][1])))
def lookup_mean(th):
    b = round(th / BIN) * BIN
    if b in TABLE_MEAN: return TABLE_MEAN[b]
    nb = min(TABLE_MEAN, key=lambda x: abs(x - b)); return TABLE_MEAN[nb]

SEGS = {44: "elev-50 az0", 66: "elev-35 az+15", 120: "elev+10 az0"}
for seg, segname in SEGS.items():
    gf = 15
    gdelta = local_delta(full("grab", seg * 45 + gf), g0)
    Cs, cams, _ = finish(copy(base), gdelta)
    still = vsub(Cs[H][1], cams[1])
    P(f"\n[stand] seg {seg} ({segname}) t=0.50 s, look frame {LOOKF}, bin {BIN} deg: still hand rel cam {tuple(round(x,1) for x in still)}")
    for var in ("none", "f_exact", "f_table_orbit", "f_table_mean", "f_table_mean_lag1"):
        txt = []
        for mv, mb in cfg["moves"]:
            fr = S[mv]["frames"]; disp, hs, camd, stretch = [], [], [], []
            prevC = None
            for k in fr:
                lp = loco(mv, mb, k); C0 = comp(sk, lp)
                if var == "none": slot = None
                elif var == "f_exact": slot = reroot_slot(C0[S3][0], C0[S3][1])
                elif var == "f_table_orbit": q, t = table_orbit(th3(C0), C0[VCAM][1]); slot = reroot_slot(q, t)
                elif var == "f_table_mean": q, t = lookup_mean(th3(C0)); slot = reroot_slot(q, t)
                else:
                    Cl = prevC if prevC is not None else C0
                    q, t = lookup_mean(th3(Cl)); slot = reroot_slot(q, t)
                prevC = C0
                C, cam, _ = finish(lp, gdelta, slot)
                Cn, camn, _ = finish(lp, gdelta, None)
                h = vsub(C[H][1], cam[1]); hs.append(h); disp.append(vlen(vsub(h, still)))
                camd.append(vlen(vsub(cam[1], camn[1])) + qangle(cam[0], camn[0]))
                if slot is not None: stretch.append(vlen(vsub(slot[SH][1], base[SH][1])))
            p2p = max(vlen(vsub(a, b)) for a, b in itertools.combinations(hs, 2))
            st = f" clavicle offset {max(stretch):.1f}cm" if stretch else ""
            txt.append(f"{mv}: disp {min(disp):.1f}-{max(disp):.1f} p2p {p2p:.1f} camD {max(camd):.2f}{st}")
        P(f"  {var:20s} " + " | ".join(txt))
# partial blend (strafe blending in), table_mean
P("\npartial strafe weight (blend-in), seg 44, f_table_mean vs none:")
gdelta = local_delta(full("grab", 44 * 45 + 15), g0)
Cs, cams, _ = finish(copy(base), gdelta); still = vsub(Cs[H][1], cams[1])
for mv, mb in cfg["moves"]:
    for w in (0.25, 0.5, 0.75):
        r = []
        for var in ("none", "f_table_mean", "f_exact"):
            dm = 0
            for k in S[mv]["frames"][::4]:
                lp = loco(mv, mb, k, w); C0 = comp(sk, lp)
                slot = None if var == "none" else (reroot_slot(*lookup_mean(th3(C0))) if var == "f_table_mean" else reroot_slot(C0[S3][0], C0[S3][1]))
                C, cam, _ = finish(lp, gdelta, slot)
                dm = max(dm, vlen(vsub(vsub(C[H][1], cam[1]), still)))
            r.append(f"{var} max {dm:.1f}")
        P(f"  {mv} w={w}: " + ", ".join(r))
open(os.path.join(HERE, f"sim2_out_look{LOOKF}_bin{int(BIN)}.txt"), "w").write("\n".join(out))
