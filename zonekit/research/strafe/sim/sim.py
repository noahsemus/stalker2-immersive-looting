"""Offline simulator of the bare-hands strafe + ImmLoot grab pose (see README in report). Usage: python sim.py [lookframe]"""
import json, sys, os, math, itertools
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from simcore import *
D = json.load(open(os.path.join(HERE, "simdump.json")))
sk = Skel(D); B = sk.bones; I = sk.idx
VBP = {"VB jnt_r_knee_target": "jnt_r_foot", "VB jnt_l_knee_target": "jnt_l_foot", "VB jnt_camera": "jnt_spine_03",
       "VB jnt_weapon": "jnt_spine_03", "VB jnt_item": "jnt_spine_03", "VB jnt_r_hand_jnt_weapon": "jnt_r_hand"}
for v, p in VBP.items(): sk.parents[I[v]] = I[p]
sk.order = sk._order()
S = D["seqs"]
def full(key, k):
    s = S[key]; return to_pose(s["full"][s["frames"].index(k)])
def mask(names): return [1.0 if b in names else 0.0 for b in B]
def read_mask(fn):
    import re
    t = open(os.path.join(HERE, "masks", fn + ".t3d"), encoding="utf-8", errors="replace").read()
    return set(re.findall(r'BoneName="([^"]*)"', t))
LEGS = mask(read_mask("legs_blend_mask")); LOWER = mask(read_mask("lower_body_blend_mask")); LEFT = mask(read_mask("left_hand_blend_mask"))
LOOKF = int(sys.argv[1]) if len(sys.argv) > 1 else 15     # 15 = level view (ClampedControlPitch 0.5)
SEG2 = 45
SEGS = {44: "elev-50 az0", 66: "elev-35 az+15", 120: "elev+10 az0"}
GF = [15, 20]
H, CAM, VCAM, LSH, SP1 = I["jnt_l_hand"], I["jnt_camera"], I["VB jnt_camera"], I["jnt_l_shoulder"], I["jnt_spine_01"]

def yaw_x(q):
    v = qrot(q, (1.0, 0.0, 0.0)); return math.degrees(math.atan2(v[1], v[0]))
def wrap(a): return (a + 180) % 360 - 180

STANCES = {
    "stand": dict(base="idle", look="look", lookbase="idle", grab="grab",
                  moves=[("walk_left", "idle"), ("walk_right", "idle"), ("run_left", "idle"), ("run_right", "idle")]),
    "crouch": dict(base="idle_crouch", look="look_lowcrouch", lookbase="idle_lowcrouch", grab="grab_crouch",
                   moves=[("lowcrouch_left", "idle_lowcrouch"), ("lowcrouch_right", "idle_lowcrouch"),
                          ("crouch_left", "idle_crouch"), ("crouch_right", "idle_crouch")]),
}
FIXES = ["none", "a_twist_ideal", "b_mainaction_idle_legsmask", "c_lefthand_local", "c_lefthand_meshrot",
         "d_curve_AdditiveMovingUpperBody", "d_curve_alpha0.5", "e_curve+lefthand_local"]

def compose(st, base, mdelta, gdelta, fix, look_delta):
    if fix.startswith("d_curve") or fix.startswith("e_curve"):
        a = 0.5 if "0.5" in fix else 1.0
        w = [1.0 if LOWER[i] else 1.0 - a for i in range(len(B))]
        if st == "crouch": w = None        # the LowCrouch state has no TwoWayBlend on the curve: no effect
        pose = apply_ms(sk, base, mdelta, weights=w) if mdelta else copy(base)
    else:
        pose = apply_ms(sk, base, mdelta) if mdelta else copy(base)
    if fix == "b_mainaction_idle_legsmask":
        pose = lbb_local(sk, base, pose, LEGS)            # base = MainActionSlot montage pose (rest idle), blend = locomotion on legs mask
    if fix in ("c_lefthand_local", "e_curve+lefthand_local"):
        pose = lbb_local(sk, pose, base, LEFT)            # LBB_4: blend = Slot LeftHand (rest idle, non-additive)
    if fix == "c_lefthand_meshrot":
        pose = lbb_meshrot(sk, pose, base, LEFT)          # hypothetical: same with bMeshSpaceRotationBlend
    if fix == "a_twist_ideal":                            # DefaultSlot: spine_01 turned about component Z by -theta
        Cb = comp(sk, base); Cp = comp(sk, pose)
        th = wrap(yaw_x(Cp[LSH][0]) - yaw_x(Cb[LSH][0]))
        R = ms_rot(sk, pose); T = [t for _, t in pose]
        R[SP1] = qnorm(qmul(qaxis((0, 0, 1), -th), R[SP1]))
        # keep every other bone's LOCAL rotation: rebuild children from local
        loc = [list(x) for x in pose]
        p = sk.parents[SP1]
        loc[SP1][0] = qmul(qinv(R[p]), R[SP1])
        pose = loc
    pose = apply_ms(sk, pose, look_delta)                 # MeshSpaceAdditive_20 (look pitch)
    C0 = comp(sk, pose)
    cam_vb = C0[VCAM]                                     # CopyBone_2: jnt_camera := VB jnt_camera (component)
    cam_bone = C0[CAM]
    pose = apply_local(pose, gdelta) if gdelta else pose  # Slot FullBody (AnimBP_Player), local-space additive
    C = comp(sk, pose)
    return C, cam_vb, cam_bone

def rel(C, cam):
    return vsub(C[H][1], cam[1])

def p2p(pts):
    return max(vlen(vsub(a, b)) for a, b in itertools.combinations(pts, 2)) if len(pts) > 1 else 0.0

out = []
def P(s): out.append(s); print(s)
# --- sanity: shoulder yaw
for st, cfg in STANCES.items():
    base = full(cfg["base"], 0)
    yb = yaw_x(comp(sk, base)[LSH][0])
    P(f"[{st}] rest L-shoulder X-axis component yaw {yb:.1f}")
    for mv, mb in cfg["moves"]:
        ref = full(mb, 0); fr = S[mv]["frames"]
        ys = [yaw_x(comp(sk, apply_ms(sk, base, ms_delta(sk, full(mv, k), ref)))[LSH][0]) for k in fr]
        P(f"   {mv}: L-shoulder yaw {min(ys):.1f}..{max(ys):.1f} (change {wrap(min(ys)-yb):+.1f}..{wrap(max(ys)-yb):+.1f})")
# --- main table
results = {}
for st, cfg in STANCES.items():
    base = full(cfg["base"], 0)
    look_delta = ms_delta(sk, full(cfg["look"], LOOKF), full(cfg["lookbase"], 0))
    g0 = full(cfg["grab"], 0)
    for seg, segname in SEGS.items():
        for gf in GF:
            gk = seg * SEG2 + gf
            gdelta = local_delta(full(cfg["grab"], gk), g0)
            # validation: standing still, base + grab == intended (base with the grab table's raw arm locals)
            Cs, camvb_s, cambone_s = compose(st, base, None, gdelta, "none", look_delta)
            intended = copy(base)
            for b in D["meta"][cfg["grab"]]["tracks"]:
                intended[I[b]] = full(cfg["grab"], gk)[I[b]]
            ident = [[QI, (0.0, 0.0, 0.0)] for _ in B]
            Cv, _, _ = compose(st, base, None, gdelta, "none", ident)      # validation without the look additive
            Ci = comp(sk, intended)
            verr = max(vlen(vsub(Cv[I[b]][1], Ci[I[b]][1])) for b in ('jnt_l_arm', 'jnt_l_fore_arm', 'jnt_l_hand', 'jnt_l_weapon'))
            still = rel(Cs, camvb_s)
            P(f"\n[{st}] grab seg {seg} ({segname}) t={gf/30:.2f}s: still hand rel cam (fwd,right,up) {tuple(round(x,1) for x in still)}; validation |sim - intended| (arm/forearm/hand/item point) = {verr:.4f} cm")
            for fix in FIXES:
                rows = []
                for mv, mb in cfg["moves"]:
                    ref = full(mb, 0)
                    hs, cams, camr, camb = [], [], [], []
                    for k in S[mv]["frames"]:
                        md = ms_delta(sk, full(mv, k), ref)
                        C, cvb, cbn = compose(st, base, md, gdelta, fix, look_delta)
                        Cn, cvbn, _ = compose(st, base, md, gdelta, "none", look_delta) if fix != "none" else (C, cvb, cbn)
                        hs.append(rel(C, cvb))
                        cams.append(vlen(vsub(cvb[1], cvbn[1])))
                        camr.append(qangle(cvb[0], cvbn[0]))
                        camb.append(vlen(vsub(cvb[1], camvb_s[1])))
                    disp = [vlen(vsub(h, still)) for h in hs]
                    rows.append((mv, min(disp), max(disp), p2p(hs), max(cams), max(camr), max(camb)))
                    results[(st, seg, gf, fix, mv)] = rows[-1]
                P(f"  {fix:32s} " + " | ".join(f"{mv}: disp {a:.1f}-{b:.1f} p2p {c:.1f} camD {d:.1f}cm {e:.1f}deg" for mv, a, b, c, d, e, f in rows))
json.dump({"|".join(map(str, k)): v for k, v in results.items()}, open(os.path.join(HERE, f"sim_results_look{LOOKF}.json"), "w"), indent=0)
open(os.path.join(HERE, f"sim_out_look{LOOKF}.txt"), "w").write("\n".join(out))
