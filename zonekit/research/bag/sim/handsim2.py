from handsim import *
for base in ("ar_idle", "ar_crouch", "gr_lowcrouch"):
    for p in (0, -45):
        pose = apply_ms(sk, raw2(base), to_pose(S2["knife_idle_add"]["ue_add"]["0"]))
        pose = apply_ms(sk, pose, ar_look_delta(p)); C = comp(sk, pose); cam = C[bs.VCAM]
        lr = [qangle(pose[I[b]][0], stance("knife", 0)[I[b]][0]) for b in ("jnt_l_arm", "jnt_l_fore_arm", "jnt_l_hand")]
        print(f"knife on {base:12} {p:4}: L hand view {bs.view(C, cam, p, bs.LH)} L arm {bs.view(C, cam, p, I['jnt_l_arm'])} local rot diff vs stand {[round(x,1) for x in lr]} camZ {cam[1][2]:.1f}")
