import os, math, unreal
AL = unreal.AnimationLibrary
out = []
def qmul(a, b):
    ax, ay, az, aw = a; bx, by, bz, bw = b
    return (aw*bx+ax*bw+ay*bz-az*by, aw*by-ax*bz+ay*bw+az*bx, aw*bz+ax*by-ay*bx+az*bw, aw*bw-ax*bx-ay*by-az*bz)
def qinv(a): return (-a[0], -a[1], -a[2], a[3])
def ang(a, b):
    d = qmul(a, qinv(b)); return math.degrees(2 * math.acos(min(1.0, abs(d[3]))))
def q(t): return (t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w)
for p in (f"{MOD_ROOT}/Runtime/AS_ImmLoot_Grab", f"{MOD_ROOT}/Runtime/AS_ImmLoot_Touch12", f"{MOD_ROOT}/Runtime/AS_ImmLoot_Touch20"):
    s = unreal.load_asset(p); n = AL.get_num_frames(s)
    out.append(p.rsplit("/",1)[1])
    for b in ("jnt_l_arm", "jnt_l_arm_roll", "jnt_l_fore_arm", "jnt_l_fore_arm_roll", "jnt_l_hand", "jnt_l_elbow"):
        row = []
        prev = None
        for k in range(n + 1):
            r = q(AL.get_bone_pose_for_frame(s, b, k, False))
            if prev is not None: row.append(round(ang(r, prev)))
            prev = r
        out.append(f"  {b:22s} " + " ".join(f"{x:2d}" for x in row))
os.makedirs(SCRATCH, exist_ok=True)
open(os.path.join(SCRATCH, "touchscan2.txt"), "w").write("\n".join(out))
