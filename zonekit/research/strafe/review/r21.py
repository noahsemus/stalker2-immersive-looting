exec(open("r11.py").read().split("grids = {}")[0])
import pickle
ID = [s3_in_cam(comp(sk, apply_ms(sk, base, ms_delta(sk, full("idle_long", k), base)))) for k in S["idle_long"]["frames"][::2]]
BANDS = {
 "idle": (ID, (("pit", -10, 4, 2),)),
 "walk": (fam_train["walk"], (("th", -100, 100, 10), ("pit", 0, 12, 4))),
 "run":  (fam_train["run"], (("th", -60, 60, 10), ("r", 26, 38, 4), ("pit", -12, 0, 6))),
 "jog":  (fam_train["jog"] + [s for s in fam_train["run"] if feats6(s)[1] < -8], (("pit", -24, -8, 8),)),
}
YSTEP = float(sys.argv[2]) if len(sys.argv) > 2 else 10.0
T = {b: AGrid(tr, YSTEP, ylo=-100, yhi=100, rows=rows, force_rest=(b in ("idle", "walk"))) for b, (tr, rows) in BANDS.items()}
print("frames per band", {b: g.nframes for b, g in T.items()}, "total", sum(g.nframes for g in T.values()))
pickle.dump(T, open(f"T_y{int(YSTEP)}.pkl", "wb"))
def band(spec):
    f = family(spec); return "walk" if f == "idle" else f
gdelta = local_delta(full("grab", 44 * 45 + 15), g0)
TRL = [s for _, s in TRS]
def nn(s3c): return X_of(min(TRL, key=lambda s: vlen(vsub(s[1], s3c[1])) + 0.5 * qangle(s[0], s3c[0])))
for look in LOOKS:
    ld = ms_delta(sk, full("look", look), full("idle", 0))
    Cs, cams = finish(copy(base), gdelta, None, ld); still = handcam(Cs, cams)
    res = {}
    for name, spec in TE:
        if name.startswith("turn90r"): continue
        cat = "L/R" if "L/R" in name else ("mix" if ("+" in name or "/" in name.split(" ")[0]) else name.split("_")[0])
        if cat == "sprint": cat = "jog"
        lp = pose_from(spec); s3c = s3_in_cam(comp(sk, lp))
        for nm, fn in (("none", None), ("plan_nn6d", nn), ("T", T[band(spec)].lookup)):
            C, cam = finish(lp, gdelta, None if fn is None else slot_X(fn(s3c)), ld)
            res.setdefault(nm, {}).setdefault(cat, []).append((vlen(vsub(handcam(C, cam), still)), name))
    # idle
    for k in S["idle_long"]["frames"][1::4]:
        lp = apply_ms(sk, base, ms_delta(sk, full("idle_long", k), base)); s3c = s3_in_cam(comp(sk, lp))
        for nm, fn in (("none", None), ("plan_nn6d", nn), ("T", T["idle"].lookup)):
            C, cam = finish(lp, gdelta, None if fn is None else slot_X(fn(s3c)), ld)
            res.setdefault(nm, {}).setdefault("idle", []).append((vlen(vsub(handcam(C, cam), still)), "idle"))
    print(f"look {look} ({(15-look)*6:+d} deg): max [p95] cm")
    for nm, r in res.items():
        allv = sorted(v for c in r for v in r[c] if c != "L/R")
        print(f"  {nm:10s} " + " | ".join(f"{c} {max(r[c])[0]:.1f} [{sorted(r[c])[int(.95*len(r[c]))][0]:.1f}]" for c in r) + f" | ALL(excl L/R) {allv[-1][0]:.1f} [{allv[int(.95*len(allv))][0]:.1f}] worst {allv[-1][1]}", flush=True)
