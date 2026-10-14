import os, math, unreal
AL = unreal.AnimationLibrary
out = []
def qmul(a, b):
    ax, ay, az, aw = a; bx, by, bz, bw = b
    return (aw*bx+ax*bw+ay*bz-az*by, aw*by-ax*bz+ay*bw+az*bx, aw*bz+ax*by-ay*bx+az*bw, aw*bw-ax*bx-ay*by-az*bz)
def qinv(a): return (-a[0], -a[1], -a[2], a[3])
def qrot(a, p):
    r = qmul(qmul(a, (p[0], p[1], p[2], 0.0)), qinv(a)); return (r[0], r[1], r[2])
def ang(a, b):
    d = qmul(a, qinv(b)); return math.degrees(2 * math.acos(min(1.0, abs(d[3]))))
def cs(seq, bone, k):
    qq, p = (0.0, 0.0, 0.0, 1.0), (0.0, 0.0, 0.0)
    for b in reversed([str(x) for x in AL.find_bone_path_to_root(seq, bone)]):
        t = AL.get_bone_pose_for_frame(seq, b, k, False)
        p = tuple(a + b_ for a, b_ in zip(p, qrot(qq, (t.translation.x, t.translation.y, t.translation.z))))
        qq = qmul(qq, (t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w))
    return p, qq
def rel(s, b):
    hp, hq = cs(s, b, 0); sp, sq = cs(s, "jnt_spine_03", 0)
    return qrot(qinv(sq), tuple(a - c for a, c in zip(hp, sp))), qmul(qinv(sq), hq)
ar_ = unreal.AssetRegistryHelpers.get_asset_registry()
P = '/Game/_STALKER2/Animations/Player/AnimSequences/'
f = unreal.ARFilter(package_paths=[P + 'pt'], recursive_paths=True, class_paths=[unreal.TopLevelAssetPath('/Script/Engine','AnimSequence')])
ids = sorted(str(a.package_name) for a in ar_.get_assets(f) if str(a.asset_name).lower().endswith("_idle") and "aim" not in str(a.asset_name).lower())
ref = None
for p in ids + [P + "ar/ak74/Idle/AS_fp_ak74_idle", f"{MOD_ROOT}/Runtime/AS_ImmLoot_Touch12"]:
    s = unreal.load_asset(p)
    hp, hq = rel(s, "jnt_l_hand")
    if ref is None: ref = (hp, hq)
    out.append(f"{p.split('/')[-1]:28s} frames {AL.get_num_frames(s):4d} l_hand in spine {tuple(round(x,1) for x in hp)}  vs first {math.dist(hp, ref[0]):5.1f} cm {ang(hq, ref[1]):5.0f} deg")
os.makedirs(SCRATCH, exist_ok=True)
open(os.path.join(SCRATCH, "ptidle.txt"), "w").write("\n".join(out))
