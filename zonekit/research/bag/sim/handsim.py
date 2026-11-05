"""Knife / bolt study: the left hand of the knife / bolt stances (rifle stand idle + the item's mesh-space idle additive +
the rifle look) against the bare-hands rest, in view axes. Data: handdump.json (dump_hand.py)."""
import json, os, sys, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bagsim as bs
from simcore import *
H = json.load(open(os.path.join(HERE, "handdump.json")))
S2 = H["seqs"]
sk = bs.sk; B = bs.B; I = bs.I
def raw2(key, k=0):
    s = S2[key]; rows = s["raw"][s["frames"].index(k)]
    return bs.vb_fix([[tuple(r[0:4]), tuple(r[4:7])] if r is not None else list(bs.REF[i]) for i, r in enumerate(rows)])
def ar_look_delta(p):
    f = (90.0 - p) / 6.0; k0 = max(0, min(int(math.floor(f)), 29)); a = f - k0
    q = lbb_local(sk, raw2("ar_look", k0), raw2("ar_look", k0 + 1), [a] * len(B)) if a > 1e-6 else raw2("ar_look", k0)
    return ms_delta(sk, bs.vb_fix(q), raw2("ar_idle"))
def stance(name, p):
    if name == "bh":
        pose = apply_ms(sk, bs.raw("idle", 0), bs.look_pose_delta("look", "idle", p))
    else:
        pose = raw2("ar_idle")
        if name in ("knife", "bolt"):
            pose = apply_ms(sk, pose, ms_delta(sk, raw2(name + "_idle_add"), raw2("ar_idle")) if False else to_pose(S2[name + "_idle_add"]["ue_add"]["0"]))
        if name == "pm":
            pose = raw2("pm_idle")
        pose = apply_ms(sk, pose, ar_look_delta(p))
    return pose
if __name__ == "__main__":
    for p in (0, -25, -48, -70):
        for nm in ("bh", "knife", "bolt", "ar", "pm"):
            pose = stance(nm, p); C = comp(sk, pose); cam = C[bs.VCAM]
            print(f"{p:4} {nm:6} L hand {bs.view(C, cam, p, bs.LH)}  L shoulder {bs.view(C, cam, p, I['jnt_l_shoulder'])}  L arm {bs.view(C, cam, p, I['jnt_l_arm'])}  R hand {bs.view(C, cam, p, bs.RH)}")
