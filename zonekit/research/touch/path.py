import os, math, unreal
AL = unreal.AnimationLibrary
out = []
def qmul(a, b):
    ax, ay, az, aw = a; bx, by, bz, bw = b
    return (aw*bx+ax*bw+ay*bz-az*by, aw*by-ax*bz+ay*bw+az*bx, aw*bz+ax*by-ay*bx+az*bw, aw*bw-ax*bx-ay*by-az*bz)
def qinv(a): return (-a[0], -a[1], -a[2], a[3])
def qrot(a, p):
    r = qmul(qmul(a, (p[0], p[1], p[2], 0.0)), qinv(a)); return (r[0], r[1], r[2])
def cs(seq, bone, k):
    qq, p = (0.0, 0.0, 0.0, 1.0), (0.0, 0.0, 0.0)
    for b in reversed([str(x) for x in AL.find_bone_path_to_root(seq, bone)]):
        t = AL.get_bone_pose_for_frame(seq, b, k, False)
        p = tuple(a + b_ for a, b_ in zip(p, qrot(qq, (t.translation.x, t.translation.y, t.translation.z))))
        qq = qmul(qq, (t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w))
    return p, qq
for pre in ("AS_ImmLoot_TouchAr12", "AS_ImmLoot_TouchPt12", "AS_ImmLoot_TouchAr20"):
    s = unreal.load_asset(f"{MOD_ROOT}/Runtime/{pre}")
    r0 = cs(s, "jnt_l_hand", 0)[0]
    out.append(pre + ": hand - rest (X fwd, Y right, Z up) " + "  ".join(f"k{k}:({p[0]:.0f},{p[1]:.0f},{p[2]:.0f})" for k in (2, 4, 6, 9, 12, 26, 30, 32, 34) for p in [tuple(a - b for a, b in zip(cs(s, 'jnt_l_hand', k)[0], r0))]))
os.makedirs(SCRATCH, exist_ok=True)
open(os.path.join(SCRATCH, "path.txt"), "w").write("\n".join(out))
