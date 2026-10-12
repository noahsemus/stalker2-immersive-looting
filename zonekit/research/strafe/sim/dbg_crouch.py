import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from simcore import *
D = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "simdump.json")))
sk = Skel(D); B = sk.bones; I = sk.idx
S = D["seqs"]
def full(key, k): s = S[key]; return to_pose(s["full"][s["frames"].index(k)])
for gk in ("grab", "grab_crouch"):
    g0 = full(gk, 0)
    for bk in ("idle", "idle_crouch", "idle_lowcrouch"):
        b0 = full(bk, 0)
        print(gk, "frame0 vs", bk, {b: (round(qangle(g0[I[b]][0], b0[I[b]][0]), 2), round(vlen(vsub(g0[I[b]][1], b0[I[b]][1])), 2)) for b in ("jnt_l_arm", "jnt_l_fore_arm", "jnt_l_hand")})
    # segment starts
    for seg in (44, 66, 120):
        gs = full(gk, seg * 45)
        print("  seg", seg, "f0 vs asset f0", {b: round(qangle(gs[I[b]][0], g0[I[b]][0]), 2) for b in ("jnt_l_arm", "jnt_l_fore_arm", "jnt_l_hand")})
