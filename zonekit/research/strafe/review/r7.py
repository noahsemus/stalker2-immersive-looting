from grid import *
exec(open("r5.py").read().split("TR, TE = specs")[0].split("import time, random")[1].replace("random.seed(1)\nt0 = time.time()\nprint(\"bones\", len(B))", ""))
TE = R5["TE"]
# check reconstruction
errs = []
for name, spec in TE[::7]:
    s3c = s3_in_cam(comp(sk, pose_from(spec)))
    r = s3c_from(*feats6(s3c)); errs.append((qangle(r[0], s3c[0]), vlen(vsub(r[1], s3c[1]))))
print("reconstruction max rot err", max(e[0] for e in errs), "pos", max(e[1] for e in errs))
gdelta = local_delta(full("grab", 44 * 45 + 15), g0)
ld = ms_delta(sk, full("look", 15), full("idle", 0))
Cs, cams = finish(copy(base), gdelta, None, ld); still = handcam(Cs, cams)
yaw0, pit0, roll0, x0, y0, z0 = feats6(S3R_in_cam)
print("rest feats", [round(v, 2) for v in feats6(S3R_in_cam)])
SUBS = {"roll->0": lambda f: (f[0], f[1], 0, f[3], f[4], f[5]),
        "pitch->0": lambda f: (f[0], 0, f[2], f[3], f[4], f[5]),
        "z->rest": lambda f: (f[0], f[1], f[2], f[3], f[4], z0),
        "radius->rest": lambda f: (f[0], f[1], f[2], *(lambda th: (-26.8*math.cos(th), 26.8*math.sin(th)))(math.atan2(f[4], -f[3])), f[5]),
        "roll,z->rest": lambda f: (f[0], f[1], 0, f[3], f[4], z0),
        "roll,z,pitch->rest": lambda f: (f[0], 0, 0, f[3], f[4], z0)}
res = {k: [] for k in SUBS}
for name, spec in TE[::3]:
    lp = pose_from(spec); s3c = s3_in_cam(comp(sk, lp)); f = feats6(s3c)
    for k, fn in SUBS.items():
        X = X_of(s3c_from(*fn(f))); C, cam = finish(lp, gdelta, slot_X(X), ld)
        res[k].append((vlen(vsub(handcam(C, cam), still)), name))
for k, v in res.items():
    v.sort(); print(f"{k:22s} max {v[-1][0]:5.1f} ({v[-1][1]})  p95 {v[int(.95*len(v))][0]:5.1f}  median {v[len(v)//2][0]:5.1f}")
