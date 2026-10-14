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
P = '/Game/_STALKER2/Animations/Player/AnimSequences/'
idles = {"ar": ["ar/ak74/Idle/AS_fp_ak74_idle", "ar/m16/Idle/AS_fp_m16_grip_idle", "smg/bucket/Idle/AS_fp_bucket_idle", "smg/m10/Idle/AS_fp_m10_idle", "shg/spsa/Idles/AS_fp_spsa_idle", "shg/toz34/Idles/AS_fp_toz34_idle", "shg/d12/Idle/AS_fp_d12_idle", "sr/svdm/Idle/AS_fp_svdm_idle"],
         "pt": ["pt/pm/Idle/AS_fp_pm_idle", "pt/rhino/Idle/AS_fp_rhino_idle"]}
B = ("jnt_l_arm", "jnt_l_fore_arm", "jnt_l_hand", "jnt_l_hand_index_01", "jnt_l_hand_thumb_01")
for fam, pre in (("pt", "AS_ImmLoot_TouchPt"), ("ar", "AS_ImmLoot_TouchAr")):
    worst = (0, "", 0, 0)
    for i in range(25):
        s = unreal.load_asset(f"{MOD_ROOT}/Runtime/{pre}{i}")
        for b in B:
            prev = None
            for k in range(0, 51):
                r = q(AL.get_bone_pose_for_frame(s, b, k, False))
                if prev is not None and ang(r, prev) > worst[0]:
                    worst = (ang(r, prev), b, i, k)
                prev = r
    out.append(f"{pre}: largest per-frame step {worst[0]:.1f} deg {worst[1]} bin {worst[2]} k{worst[3]}")
    for ip in idles[fam]:
        s0 = unreal.load_asset(P + ip)
        m = 0
        for i in (0, 4, 12, 20, 24):
            s = unreal.load_asset(f"{MOD_ROOT}/Runtime/{pre}{i}")
            for k in range(0, 9):
                for b in B[:3]:
                    m = max(m, ang(q(AL.get_bone_pose_for_frame(s, b, k, False)), q(AL.get_bone_pose_for_frame(s0, b, 0, False))))
        out.append(f"   vs {ip.split('/')[-1]}: frames 0-8 at most {m:.0f} deg from its grip (local, arm/forearm/hand)")
    s = unreal.load_asset(f"{MOD_ROOT}/Runtime/{pre}12")
    out.append(f"   bin 12 hand local turn frame 0 -> 12: {ang(q(AL.get_bone_pose_for_frame(s, 'jnt_l_hand', 12, False)), q(AL.get_bone_pose_for_frame(s, 'jnt_l_hand', 0, False))):.0f} deg")
os.makedirs(SCRATCH, exist_ok=True)
open(os.path.join(SCRATCH, "famscan.txt"), "w").write("\n".join(out))
