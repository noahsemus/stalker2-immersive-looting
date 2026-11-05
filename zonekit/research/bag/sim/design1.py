from bagsim import *
LSH, RSH = I["jnt_l_shoulder"], I["jnt_r_shoulder"]
print("parents:", B[sk.parents[LSH]], B[sk.parents[RSH]], B[sk.parents[I['jnt_l_arm']]])
# 1. anim camera relative to its spine_03 over time
ref = None
for key, ts in (("bag_in", [0.0, 0.3, 0.6, 1.0, 1.5]), ("bag_idle", [0.0, 1.0, 2.0]), ("bag_out", [0.0, 0.3, 0.5, 0.66])):
    for t in ts:
        C = comp(sk, raw_t(key, t))
        rel = qmul(qinv(C[SP3][0]), C[CAM][0])
        if ref is None: ref = rel
        print(f"{key}@{t}: cam-vs-spine3 change {qangle(rel, ref):.2f} deg; l_shoulder in cam axes {anim_view(key, t, LSH)[0]} r_shoulder {anim_view(key, t, RSH)[0]}")
for st in ("stand", "lowcrouch"):
    for p in (0, -30, -60):
        C, cam, _ = compose(st, p)
        print(f"live {st} {p}: l_shoulder view {view(C, cam, p, LSH)} r_shoulder {view(C, cam, p, RSH)}")
