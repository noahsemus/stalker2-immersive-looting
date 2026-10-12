exec(open("r16.py").read().split("gdelta = local_delta")[0])
def featk(s3c):
    y, p, ro, x, yy, z = feats6(s3c); return dict(yaw=y, pit=p, th=math.degrees(math.atan2(yy, -x)), r=math.hypot(x, yy))
def lookup_feats(k):
    fam = "jog" if k["pit"] < PIT_JOG else ("run" if k["pit"] < PIT_RUN else "walk")
    g = G[fam]; ri = g.row_of(k); u = max(0.0, min(g.ny - 1.0, (k["yaw"] - g.ylo) / g.ystep)); i = min(int(u), g.ny - 2)
    return tf_lerp(g.cells[(ri, i)], g.cells[(ri, i + 1)], u - i)
gdelta = local_delta(full("grab", 44 * 45 + 15), g0)
SCEN = {
  "walk_left steady": lambda t: [("walk_left", (t / 2.467) % 1, 1.0)],
  "run_left steady": lambda t: [("run_left", (t / 4.667) % 1, 1.0)],
  "run_fr steady": lambda t: [("run_fr", (t / 4.667) % 1, 1.0)],
  "walk_left start (0->1 in 0.25 s)": lambda t: [("walk_left", (t / 2.467) % 1, min(1.0, t / 0.25))],
  "run_right start (0->1 in 0.2 s)": lambda t: [("run_right", (t / 4.667) % 1, min(1.0, t / 0.2))],
  "walk L->R reversal (0.3 s)": lambda t: [("walk_left", (t / 2.467) % 1, max(0.0, 1 - t / 0.3) + 1e-6), ("walk_right", (t / 2.467) % 1, min(1.0, t / 0.3) + 1e-6)],
}
for look in LOOKS:
    ld = ms_delta(sk, full("look", look), full("idle", 0))
    Cs, cams = finish(copy(base), gdelta, None, ld); still = handcam(Cs, cams)
    print(f"look {look} ({(15-look)*6:+d} deg): max hand displacement over 0.6 s (cm)")
    for sn, sc in SCEN.items():
        row = []
        for fps in (30, 60):
            dt = 1.0 / fps; T = [k * dt for k in range(int(0.6 / dt) + 3)]
            S3 = [s3_in_cam(comp(sk, pose_from(sc(t)))) for t in T]
            K = [featk(s) for s in S3]
            errs = {"nolag": 0, "lag1": 0, "lag1+pred": 0, "exact lag1": 0}
            for n in range(2, len(T)):
                lp = pose_from(sc(T[n]))
                kp = {k: 2 * K[n-1][k] - K[n-2][k] for k in K[n-1]}
                for nm, X in (("nolag", lookup_feats(K[n])), ("lag1", lookup_feats(K[n-1])), ("lag1+pred", lookup_feats(kp)), ("exact lag1", X_of(S3[n-1]))):
                    C, cam = finish(lp, gdelta, slot_X(X), ld); errs[nm] = max(errs[nm], vlen(vsub(handcam(C, cam), still)))
            row.append(f"{fps}fps " + " ".join(f"{k} {v:.1f}" for k, v in errs.items()))
        print(f"  {sn:34s} | " + " | ".join(row), flush=True)
