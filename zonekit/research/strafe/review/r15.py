exec(open("r11.py").read().split("grids = {}")[0])
import pickle
DES = {
 "C1": {"walk": (("th", -100, 100, 10),), "run": (("th", -60, 60, 10), ("r", 26, 38, 4)), "jog": ()},
 "C2": {"walk": (("th", -100, 100, 10), ("pit", 0, 12, 4)), "run": (("th", -60, 60, 10), ("r", 26, 38, 4)), "jog": ()},
 "C3": {"walk": (("th", -100, 100, 10), ("pit", 0, 12, 4)), "run": (("th", -60, 60, 10), ("r", 26, 38, 4), ("pit", -12, 0, 6)), "jog": ()},
}
G = {}
for d, cfg in DES.items():
    gr = {f: AGrid(fam_train[f], 5.0, ylo=-100, yhi=100, rows=cfg[f]) for f in cfg}; gr["idle"] = gr["walk"]
    G[d] = gr; print(d, "frames", sum(gr[f].nframes for f in cfg), {f: gr[f].nframes for f in cfg}, flush=True)
pickle.dump(G, open("grids.pkl", "wb"))
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
        fns = [("plan_nn6d", nn)] + [(d, G[d][family(spec)].lookup) for d in G]
        for nm, fn in fns:
            C, cam = finish(lp, gdelta, slot_X(fn(s3c)), ld)
            res.setdefault(nm, {}).setdefault(cat, []).append((vlen(vsub(handcam(C, cam), still)), name))
    print(f"look {look} ({(15-look)*6:+d} deg): max [p95] cm")
    for nm, r in res.items():
        allv = sorted(v for c in r for v in r[c] if c != "L/R")
        print(f"  {nm:10s} " + " | ".join(f"{c} {max(r[c])[0]:.1f} [{sorted(r[c])[int(.95*len(r[c]))][0]:.1f}]" for c in r) + f" | ALL(excl L/R) {allv[-1][0]:.1f} [{allv[int(.95*len(allv))][0]:.1f}] worst {allv[-1][1]}", flush=True)
