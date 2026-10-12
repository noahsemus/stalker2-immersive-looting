exec(open("r11.py").read().split("grids = {}")[0])
import pickle
ID = [s3_in_cam(comp(sk, apply_ms(sk, base, ms_delta(sk, full("idle_long", k), base)))) for k in S["idle_long"]["frames"][::2]]
DESIGNS = {
 "K (clusters)": {"idle": (ID, (("pit", -10, 4, 2),)), "walk": (fam_train["walk"], (("dev", -30, 30, 30),)),
                  "run": (fam_train["run"], (("th", -45, 45, 45),)), "jog": (fam_train["jog"] + [s for s in fam_train["run"] if feats6(s)[1] < -8], (("pit", -24, -8, 8),))},
 "K2 (clusters+pitch)": {"idle": (ID, (("pit", -10, 4, 2),)), "walk": (fam_train["walk"], (("dev", -30, 30, 30), ("pit", 0, 10, 5))),
                  "run": (fam_train["run"], (("th", -45, 45, 45), ("pit", -12, 0, 6))), "jog": (fam_train["jog"] + [s for s in fam_train["run"] if feats6(s)[1] < -8], (("pit", -24, -8, 8),))},
}
TT = {}
for dn, bands in DESIGNS.items():
    TT[dn] = {b: AGrid(tr, 10.0, ylo=-100, yhi=100, rows=rows, force_rest=(b in ("idle", "walk"))) for b, (tr, rows) in bands.items()}
    print(dn, "frames", {b: g.nframes for b, g in TT[dn].items()}, sum(g.nframes for g in TT[dn].values()), flush=True)
TT["T (theta/pitch grid)"] = pickle.load(open("T_y10.pkl", "rb"))
pickle.dump({k: v for k, v in TT.items()}, open("TT.pkl", "wb"))
def band(spec):
    f = family(spec); return "walk" if f == "idle" else f
gdelta = local_delta(full("grab", 44 * 45 + 15), g0)
for look in LOOKS:
    ld = ms_delta(sk, full("look", look), full("idle", 0))
    Cs, cams = finish(copy(base), gdelta, None, ld); still = handcam(Cs, cams)
    res = {}
    for name, spec in TE:
        if name.startswith("turn90r"): continue
        cat = "L/R" if "L/R" in name else ("mix" if ("+" in name or "/" in name.split(" ")[0]) else name.split("_")[0])
        if cat == "sprint": cat = "jog"
        lp = pose_from(spec); s3c = s3_in_cam(comp(sk, lp))
        for dn, T in TT.items():
            C, cam = finish(lp, gdelta, slot_X(T[band(spec)].lookup(s3c)), ld)
            res.setdefault(dn, {}).setdefault(cat, []).append((vlen(vsub(handcam(C, cam), still)), name))
    for k in S["idle_long"]["frames"][1::4]:
        lp = apply_ms(sk, base, ms_delta(sk, full("idle_long", k), base)); s3c = s3_in_cam(comp(sk, lp))
        for dn, T in TT.items():
            C, cam = finish(lp, gdelta, slot_X(T["idle"].lookup(s3c)), ld); res[dn].setdefault("idle", []).append((vlen(vsub(handcam(C, cam), still)), "idle"))
    print(f"look {look} ({(15-look)*6:+d} deg): max [p95] cm")
    for dn, r in res.items():
        allv = sorted(v for c in r for v in r[c] if c != "L/R")
        print(f"  {dn:22s} " + " | ".join(f"{c} {max(r[c])[0]:.1f} [{sorted(r[c])[int(.95*len(r[c]))][0]:.1f}]" for c in r) + f" | ALL(excl L/R) {allv[-1][0]:.1f} [{allv[int(.95*len(allv))][0]:.1f}] worst {allv[-1][1]}", flush=True)
