exec(open("r11.py").read().split("grids = {}")[0])
import pickle
ID = [s3_in_cam(comp(sk, apply_ms(sk, base, ms_delta(sk, full("idle_long", k), base)))) for k in S["idle_long"]["frames"][::2]]
MOV = fam_train["walk"] + fam_train["run"] + fam_train["jog"]
TT = pickle.load(open("TT.pkl", "rb")); T = TT["T (theta/pitch grid)"]
IDLE = T["idle"]
U = {
 "U1 th10 x pit6": AGrid(MOV, 10.0, ylo=-100, yhi=100, rows=(("th", -100, 100, 10), ("pit", -24, 12, 6))),
 "U2 th10 x pit6 x r4": AGrid(MOV, 10.0, ylo=-100, yhi=100, rows=(("th", -100, 100, 10), ("pit", -24, 12, 6), ("r", 18, 38, 4))),
}
for k, g in U.items(): print(k, "frames", g.nframes + IDLE.nframes, flush=True)
pickle.dump(U, open("U.pkl", "wb"))
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
        fns = [(k, g.lookup) for k, g in U.items()] + [("T (bands by state)", T[band(spec)].lookup)]
        for dn, fn in fns:
            C, cam = finish(lp, gdelta, slot_X(fn(s3c)), ld)
            res.setdefault(dn, {}).setdefault(cat, []).append((vlen(vsub(handcam(C, cam), still)), name))
    print(f"look {look} ({(15-look)*6:+d} deg): max [p95] cm (moving poses; idle row as before)")
    for dn, r in res.items():
        allv = sorted(v for c in r for v in r[c] if c != "L/R")
        print(f"  {dn:22s} " + " | ".join(f"{c} {max(r[c])[0]:.1f} [{sorted(r[c])[int(.95*len(r[c]))][0]:.1f}]" for c in r) + f" | ALL(excl L/R) {allv[-1][0]:.1f} [{allv[int(.95*len(allv))][0]:.1f}] worst {allv[-1][1]}", flush=True)
