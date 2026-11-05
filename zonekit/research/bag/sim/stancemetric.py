from bagsim import *
print([b for b in B if "pelvis" in b or "spine" in b or "root" in b or "hips" in b][:12])
ST = {"stand": ("idle", "look", "idle"), "crouch": ("idle_crouch", "look", "idle"), "lowcrouch": ("idle_lowcrouch", "look_lowcrouch", "idle_lowcrouch")}
for sn, (bk, lk, lb) in ST.items():
    for p in (0, -30, -60, -90):
        pose = apply_ms(sk, raw(bk, 0), look_pose_delta(lk, lb, p)); C = comp(sk, pose)
        cam = C[VCAM][1]
        row = " ".join(f"{b}={C[I[b]][1][2]:.1f}" for b in ("jnt_pelvis", "jnt_spine_01", "jnt_spine_03") if b in I)
        print(f"{sn:9} {p:4}: camZ {cam[2]:.1f}  {row}  cam-pelvis {cam[2]-C[I['jnt_pelvis']][1][2]:.1f}" if "jnt_pelvis" in I else f"{sn} {p} camZ {cam[2]:.1f} {row}")
