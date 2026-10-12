import pickle, sys
from grid import *
NAME = sys.argv[1] if len(sys.argv) > 1 else "SK_pla_skif_01"
SK = pickle.load(open(f"skin_{NAME}.pkl", "rb"))
def _nz(v):
    t = sum(w for _, w, _ in v[1]) or 1.0
    return (v[0], [(b, w / t, l) for b, w, l in v[1]])
SK["verts"] = [_nz(v) for v in SK["verts"]]; SK["mixed"] = [_nz(v) for v in SK["mixed"]]
SUB = SK["SUB"]; mixed = [v for v in SK["mixed"] if any(b in ("jnt_spine_01","jnt_spine_02","jnt_spine_03","jnt_neck","jnt_head","jnt_r_shoulder") for b, _, _ in v[1])]
# torso verts near the left shoulder (pure non-shoulder, within 20 cm of rest l_shoulder joint)
REF = to_pose(D["refpose"]); CR = comp(sk, REF); shp = CR[I["jnt_l_shoulder"]][1]
near = [v for v in SK["verts"] if all(b not in SUB for b, _, _ in v[1]) and vlen(vsub(v[0], shp)) < 20][::4]
HF, VF = 55.0, 36.0     # half FOVs (deg): 110 x 72 (generous)
def skin(C, v): 
    p = (0, 0, 0)
    for b, w, loc in v[1]: q, t = C[I[b]]; p = vadd(p, vmul(vadd(t, qrot(q, loc)), w))
    return p
def incam(cam, p):
    c = qrot(qinv(cam[0]), vsub(p, cam[1])); return c
def visible(c): return c[0] > 2 and abs(math.degrees(math.atan2(c[1], c[0]))) < HF and abs(math.degrees(math.atan2(c[2], c[0]))) < VF
gdelta = local_delta(full("grab", 44 * 45 + 15), g0)
print(NAME, "mixed verts", len(mixed), "torso verts near L shoulder (sampled)", len(near))
print("pose | look | mixed visible vanilla / plan-f | max plan-f displacement of visible mixed verts vs vanilla | torso-near-shoulder visible")
for mv in ("walk_left", "walk_right", "run_left", "run_right", "walk_fl", "walk_br", "run_bl", "idle"):
    for look in (15, 20, 23, 26, 29):
        ld = ms_delta(sk, full("look", look), full("idle", 0))
        worst = (0, 0, 0, 0)
        frames = [None] if mv == "idle" else range(0, len(deltas(mv)), max(1, len(deltas(mv)) // 6))
        for i in frames:
            lp = copy(base) if i is None else apply_ms(sk, base, deltas(mv)[i])
            s3c = s3_in_cam(comp(sk, lp))
            # vanilla
            Cv, camv = finish(lp, gdelta, None, ld)
            Cf, camf = finish(lp, gdelta, slot_X(X_of(s3c)), ld)
            nv = nf = 0; md = 0
            for v in mixed:
                pv, pf = incam(camv, skin(Cv, v)), incam(camf, skin(Cf, v))
                if visible(pv): nv += 1
                if visible(pf): nf += 1; md = max(md, vlen(vsub(pf, pv)))
            nt = sum(1 for v in near if visible(incam(camf, skin(Cf, v))))
            worst = max(worst, (nf, nv, md, nt))
        print(f"{mv:10s} look{look:2d} ({(15-look)*6:+4d} deg) | mixed visible vanilla {worst[1]:4d} plan-f {worst[0]:4d} | max disp {worst[2]:5.1f} cm | torso-near-shoulder visible {worst[3]}")
