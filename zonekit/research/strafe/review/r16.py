exec(open("r11.py").read().split("grids = {}")[0])
import pickle
G = pickle.load(open("grids.pkl", "rb"))["C1"]
PIT_RUN, PIT_JOG = -1.5, -16.0
def fam_by_pitch(s3c):
    p = feats6(s3c)[1]
    return "jog" if p < PIT_JOG else ("run" if p < PIT_RUN else "walk")
gdelta = local_delta(full("grab", 44 * 45 + 15), g0)
for look in LOOKS:
    ld = ms_delta(sk, full("look", look), full("idle", 0))
    Cs, cams = finish(copy(base), gdelta, None, ld); still = handcam(Cs, cams)
    res = {}; mism = 0; n = 0
    for name, spec in TE:
        if name.startswith("turn90r"): continue
        cat = "L/R" if "L/R" in name else ("mix" if ("+" in name or "/" in name.split(" ")[0]) else name.split("_")[0])
        if cat == "sprint": cat = "jog"
        lp = pose_from(spec); s3c = s3_in_cam(comp(sk, lp))
        fp = fam_by_pitch(s3c); n += 1; mism += (fp != family(spec))
        for nm, fn in (("C1 family=state", G[family(spec)].lookup), ("C1 family=pitch", G[fp].lookup)):
            C, cam = finish(lp, gdelta, slot_X(fn(s3c)), ld)
            res.setdefault(nm, {}).setdefault(cat, []).append((vlen(vsub(handcam(C, cam), still)), name))
    print(f"look {look} ({(15-look)*6:+d} deg): family by pitch differs from state in {mism}/{n} test poses")
    for nm, r in res.items():
        allv = sorted(v for c in r for v in r[c] if c != "L/R")
        print(f"  {nm:16s} " + " | ".join(f"{c} {max(r[c])[0]:.1f} [{sorted(r[c])[int(.95*len(r[c]))][0]:.1f}]" for c in r) + f" | ALL(excl L/R) {allv[-1][0]:.1f} [{allv[int(.95*len(allv))][0]:.1f}] worst {allv[-1][1]}", flush=True)
