from bagsim import *
for key, k in (("pitchfix", 30), ("pitchfix", 59), ("servo", 1138), ("look", 25), ("look_lowcrouch", 25)):
    ue = to_pose(S[key]["ue_add"][str(k)])
    mine = ms_delta(sk, raw(key, k), raw(key, 0)) if not key.startswith("look") else None
    print(key, k, M[key]["refseq"])
    for b in ("jnt_spine_03", "jnt_l_shoulder", "jnt_l_arm", "jnt_l_fore_arm", "jnt_l_hand", "jnt_camera", "VB jnt_camera", "jnt_r_hand"):
        i = I[b]
        print(f"   {b:16s} UE add {qangle(ue[i][0], QI):6.2f} deg t {tuple(round(x,2) for x in ue[i][1])}" + (f" | mine {qangle(mine[i][0], QI):6.2f}" if mine else ""))
