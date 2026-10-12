from agrid import *
import sys, time
exec(open("r5.py").read().split("TR, TE = specs")[0].split("import time, random")[1].replace("random.seed(1)\nt0 = time.time()\nprint(\"bones\", len(B))", ""))
TRS = [s for _, s in R5["TRS"]]; TE = R5["TE"]
LOOKS = [int(x) for x in (sys.argv[1].split(",") if len(sys.argv) > 1 else ["15"])]
WHICH = sys.argv[2].split(";") if len(sys.argv) > 2 else None
gdelta = local_delta(full("grab", 44 * 45 + 15), g0)
def nn(s3c): return X_of(min(TRS, key=lambda s: vlen(vsub(s[1], s3c[1])) + 0.5 * qangle(s[0], s3c[0])))
t0 = time.time()
CANDS = {
  "plan_nn6d": lambda: nn,
  "A2 yaw5 x th10": lambda: AGrid(TRS, 5.0, rows=(("th", -100, 100, 10),)),
  "A2 yaw5 x th7.5": lambda: AGrid(TRS, 5.0, rows=(("th", -97.5, 97.5, 7.5),)),
  "A3 yaw5 x th10 x pit5": lambda: AGrid(TRS, 5.0, rows=(("th", -100, 100, 10), ("pit", -25, 15, 5))),
  "A3 yaw5 x th10 x r4": lambda: AGrid(TRS, 5.0, rows=(("th", -100, 100, 10), ("r", 16, 40, 4))),
  "A3 yaw5 x x4 x y4": lambda: AGrid(TRS, 5.0, rows=(("x", -40, 4, 4), ("y", -30, 30, 4))),
}
VAR = {"none": None, "exact": lambda s: X_of(s)}
for nm, mk in CANDS.items():
    if WHICH and nm not in WHICH: continue
    g = mk(); VAR[nm] = g if callable(g) and not isinstance(g, AGrid) else g.lookup
    print(nm, "built", getattr(g, "nframes", ""), "frames", round(time.time() - t0, 1), "s", flush=True)
for look in LOOKS:
    ld = ms_delta(sk, full("look", look), full("idle", 0))
    Cs, cams = finish(copy(base), gdelta, None, ld); still = handcam(Cs, cams)
    res = {nm: {} for nm in VAR}
    for name, spec in TE:
        grp = name.split(" ")[0]
        if "L/R" in name: grp = name.split(" ")[0] + "_L/R"
        cat = ("mix" if ("+" in grp or "/" in grp) else grp.split("_")[0])
        lp = pose_from(spec); s3c = s3_in_cam(comp(sk, lp))
        for nm, fn in VAR.items():
            slot = None if fn is None else slot_X(fn(s3c))
            C, cam = finish(lp, gdelta, slot, ld)
            res[nm].setdefault(cat, []).append((vlen(vsub(handcam(C, cam), still)), name))
    print(f"\n=== look frame {look} ({(15-look)*6:+d} deg), grab seg 44 t0.5: hand displacement vs standing still (cm): max [p95] per category")
    cats = list(res["none"].keys())
    print(f"{'variant':24s} {'STILL':>5s} " + " ".join(f"{c:>16s}" for c in cats) + "   ALL max [p95]  worst case")
    for nm, fn in VAR.items():
        slot = None if fn is None else slot_X(fn(S3R_in_cam))
        C, cam = finish(copy(base), gdelta, slot, ld); se = vlen(vsub(handcam(C, cam), still))
        allv = sorted(v for c in cats for v in res[nm][c])
        cells = []
        for c in cats:
            v = sorted(res[nm][c]); cells.append(f"{v[-1][0]:6.1f} [{v[int(.95*len(v))][0]:5.1f}]")
        print(f"{nm:24s} {se:5.1f} " + " ".join(f"{x:>16s}" for x in cells) + f"   {allv[-1][0]:5.1f} [{allv[int(.95*len(allv))][0]:4.1f}]  {allv[-1][1]}")
