from agrid import *
exec(open("r5.py").read().split("TR, TE = specs")[0].split("import time, random")[1].replace("random.seed(1)\nt0 = time.time()\nprint(\"bones\", len(B))", ""))
TE = R5["TE"]
gdelta = local_delta(full("grab", 44 * 45 + 15), g0)
ld = ms_delta(sk, full("look", 15), full("idle", 0))
Cs, cams = finish(copy(base), gdelta, None, ld); still = handcam(Cs, cams)
def q(v, st): return round(v / st) * st
def mk(fn):
    def f(s3c):
        y, p, r_, x, yy, z = feats6(s3c); th = math.degrees(math.atan2(yy, -x)); r = math.hypot(x, yy)
        a = fn(y, p, r_, th, r, z)
        y2, p2, ro2, th2, r2, z2 = a
        return X_of(s3c_from(y2, p2, ro2, -r2 * math.cos(math.radians(th2)), r2 * math.sin(math.radians(th2)), z2))
    return f
V = {
 "roll0 only": mk(lambda y,p,ro,th,r,z: (y,p,0,th,r,z)),
 "th q10": mk(lambda y,p,ro,th,r,z: (y,p,ro,q(th,10),r,z)),
 "pit q5": mk(lambda y,p,ro,th,r,z: (y,q(p,5),ro,th,r,z)),
 "r q4": mk(lambda y,p,ro,th,r,z: (y,p,ro,th,q(r,4),z)),
 "z q3": mk(lambda y,p,ro,th,r,z: (y,p,ro,th,r,q(z,3))),
 "z=-33": mk(lambda y,p,ro,th,r,z: (y,p,ro,th,r,-33)),
 "roll0 th10 pit5 r4 z3": mk(lambda y,p,ro,th,r,z: (y,q(p,5),0,q(th,10),q(r,4),q(z,3))),
}
res = {k: [] for k in V}
for name, spec in TE[::2]:
    if "L/R" in name: continue
    lp = pose_from(spec); s3c = s3_in_cam(comp(sk, lp))
    for k, fn in V.items():
        C, cam = finish(lp, gdelta, slot_X(fn(s3c)), ld); res[k].append((vlen(vsub(handcam(C, cam), still)), name))
for k, v in res.items():
    v.sort(); print(f"{k:24s} max {v[-1][0]:5.1f} ({v[-1][1]}) p95 {v[int(.95*len(v))][0]:4.1f}")
