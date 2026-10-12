from agrid import *
import sys, time
exec(open("r5.py").read().split("TR, TE = specs")[0].split("import time, random")[1].replace("random.seed(1)\nt0 = time.time()\nprint(\"bones\", len(B))", ""))
TR = R5["TR"]; TRS = R5["TRS"]; TE = R5["TE"]
def family(spec):
    w = {}
    for mv, ph, ww in spec:
        f = "walk" if mv.startswith("walk") else "run" if mv.startswith("run") else "jog" if mv.startswith(("jog", "sprint")) else "idle"
        w[f] = w.get(f, 0) + ww
    return max(w, key=w.get)
fam_train = {}
for (n, sp), (_, s) in zip(TR, TRS): fam_train.setdefault(family(sp), []).append(s)
print({k: len(v) for k, v in fam_train.items()})
LOOKS = [int(x) for x in (sys.argv[1].split(",") if len(sys.argv) > 1 else ["15"])]
THS = float(sys.argv[2]) if len(sys.argv) > 2 else 10.0
YS = float(sys.argv[3]) if len(sys.argv) > 3 else 5.0
TH_LO = float(sys.argv[4]) if len(sys.argv) > 4 else -100.0
grids = {}
for f, tr in fam_train.items():
    if f == "idle": continue
    grids[f] = AGrid(tr, YS, ylo=-100, yhi=100, rows=(("th", TH_LO, -TH_LO, THS),))
grids["idle"] = grids["walk"]
nfr = sum(g.nframes for k, g in grids.items() if k != "idle")
gdelta = local_delta(full("grab", 44 * 45 + 15), g0)
def nn(s3c): return X_of(min([s for _, s in TRS], key=lambda s: vlen(vsub(s[1], s3c[1])) + 0.5 * qangle(s[0], s3c[0])))
for look in LOOKS:
    ld = ms_delta(sk, full("look", look), full("idle", 0))
    Cs, cams = finish(copy(base), gdelta, None, ld); still = handcam(Cs, cams)
    res = {"fam_grid": {}, "plan_nn6d": {}}
    for name, spec in TE:
        cat = "L/R" if "L/R" in name else ("mix" if ("+" in name or "/" in name.split(" ")[0]) else name.split("_")[0])
        lp = pose_from(spec); s3c = s3_in_cam(comp(sk, lp))
        for nm, fn in (("fam_grid", grids[family(spec)].lookup), ("plan_nn6d", nn)):
            C, cam = finish(lp, gdelta, slot_X(fn(s3c)), ld)
            res[nm].setdefault(cat, []).append((vlen(vsub(handcam(C, cam), still)), name))
    print(f"look {look} ({(15-look)*6:+d} deg); family grid: 3 families x yaw {YS} deg (interp) x theta {THS} deg rows = {nfr} frames")
    for nm, r in res.items():
        allv = sorted(v for c in r for v in r[c])
        print(f"  {nm:10s} " + " | ".join(f"{c} {max(r[c])[0]:.1f} [{sorted(r[c])[int(.95*len(r[c]))][0]:.1f}]" for c in r) + f" | ALL {allv[-1][0]:.1f} [{allv[int(.95*len(allv))][0]:.1f}] worst {allv[-1][1]}")
    # still
    C, cam = finish(copy(base), gdelta, slot_X(grids["idle"].lookup(S3R_in_cam)), ld); print("  standing still error", round(vlen(vsub(handcam(C, cam), still)), 2))
