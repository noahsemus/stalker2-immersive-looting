from grid import *
import sys, time
exec(open("r5.py").read().split("TR, TE = specs")[0].split("import time, random")[1].replace("random.seed(1)\nt0 = time.time()\nprint(\"bones\", len(B))", ""))
TRS = [s for _, s in R5["TRS"]]; TE = R5["TE"]
LOOKS = [int(x) for x in (sys.argv[1].split(",") if len(sys.argv) > 1 else ["15"])]
SEG = 44
gdelta = local_delta(full("grab", SEG * 45 + 15), g0)
NN = TRS
def nn(s3c): return X_of(min(NN, key=lambda s: vlen(vsub(s[1], s3c[1])) + 0.5 * qangle(s[0], s3c[0])))
VARIANTS = {
  "none": None,
  "exact": lambda s: X_of(s),
  "plan_nn6d": nn,
  "G1 yaw5": Grid(TRS, 5.0).lookup,
  "G2 yaw5 x th15": Grid(TRS, 5.0, rows=(("th", -90, 90, 15),)).lookup,
  "G2 yaw5 x th10": Grid(TRS, 5.0, rows=(("th", -90, 90, 10),)).lookup,
  "G2 yaw5 x y6": Grid(TRS, 5.0, rows=(("y", -30, 30, 6),)).lookup,
  "G3 yaw5 x th15 x pit6": Grid(TRS, 5.0, rows=(("th", -90, 90, 15), ("pit", -21, 9, 6))).lookup,
  "G3 yaw5 x th10 x pit5": Grid(TRS, 5.0, rows=(("th", -90, 90, 10), ("pit", -20, 10, 5))).lookup,
  "G3 yaw5 x th15 x r4": Grid(TRS, 5.0, rows=(("th", -90, 90, 15), ("r", 17, 37, 4))).lookup,
}
for nm, g in VARIANTS.items():
    if isinstance(g, type(None)): continue
for look in LOOKS:
    ld = look_delta = ms_delta(sk, full("look", look), full("idle", 0))
    Cs, cams = finish(copy(base), gdelta, None, ld); still = handcam(Cs, cams)
    res = {nm: {} for nm in VARIANTS}
    for name, spec in TE:
        grp = name.split(" ")[0]
        grp = grp if ("+" in grp or "/" in grp or "L/R" in name) else grp
        if "L/R" in name: grp = name.split(" ")[0] + " L/R"
        lp = pose_from(spec); C0 = comp(sk, lp); s3c = s3_in_cam(C0)
        for nm, fn in VARIANTS.items():
            slot = None if fn is None else slot_X(fn(s3c))
            C, cam = finish(lp, gdelta, slot, ld)
            e = vlen(vsub(handcam(C, cam), still))
            res[nm].setdefault(grp, []).append(e)
    # still error
    print(f"\n=== look frame {look}, seg {SEG}; max hand displacement (cm) per test group")
    groups = list(res["none"].keys())
    print(f"{'variant':24s} {'frames':>6s} {'STILL':>5s} " + " ".join(f"{g[:9]:>9s}" for g in groups) + "   WORST  p95")
    for nm, fn in VARIANTS.items():
        slot = None if fn is None else slot_X(fn(S3R_in_cam))
        C, cam = finish(copy(base), gdelta, slot, ld); se = vlen(vsub(handcam(C, cam), still))
        allv = sorted(v for g in groups for v in res[nm][g])
        nf = getattr(getattr(fn, "__self__", None), "nframes", "")
        print(f"{nm:24s} {str(nf):>6s} {se:5.1f} " + " ".join(f"{max(res[nm][g]):9.1f}" for g in groups) + f"   {allv[-1]:5.1f} {allv[int(0.95*len(allv))]:5.1f}")
