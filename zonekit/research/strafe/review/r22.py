exec(open("r11.py").read().split("grids = {}")[0])
import pickle
DIRS8 = ["fwd", "fr", "right", "br", "bwd", "bl", "left", "fl"]
def dir_of(spec):
    w = {}
    for mv, ph, ww in spec:
        if "_" in mv and mv.split("_")[1] in DIRS8: w[mv.split("_")[1]] = w.get(mv.split("_")[1], 0) + ww
    return max(w, key=w.get) if w else "fwd"
def rowkey(spec):
    f = family(spec)
    if f in ("jog", "idle"): return f
    return f + "_" + dir_of(spec)
# training by row
rows_tr = {}
for (n, sp), (_, s) in zip(TR, TRS): rows_tr.setdefault(rowkey(sp), []).append(s)
ID = [s3_in_cam(comp(sk, apply_ms(sk, base, ms_delta(sk, full("idle_long", k), base)))) for k in S["idle_long"]["frames"][::2]]
YST = float(sys.argv[2]) if len(sys.argv) > 2 else 10.0
BW = float(sys.argv[3]) if len(sys.argv) > 3 else 6.0
class Row:
    def __init__(self, tr, col="yaw", lo=-100, hi=100, st=YST, bw=BW, rest=False):
        self.col, self.lo, self.st = col, lo, st; self.n = int(round((hi - lo) / st)) + 1
        F = [dict(zip(("yaw", "pit", "roll", "x", "y", "z"), feats6(s))) for s in tr]
        self.cells = []
        for j in range(self.n):
            c = lo + j * st
            ws = [math.exp(-((f[col] - c) / bw) ** 2) for f in F]; tw = sum(ws)
            if tw < 1e-4:
                jn = min(range(len(F)), key=lambda q: abs(F[q][col] - c)); est = dict(F[jn])
                # extrapolate: keep nearest sample's non-col features, set col
            else:
                est = {k: sum(w * f[k] for w, f in zip(ws, F)) / tw for k in ("yaw", "pit", "x", "y", "z")}
            est[col] = c
            self.cells.append(X_of(s3c_from(est["yaw"], est["pit"], 0.0, est["x"], est["y"], est["z"])))
        if rest:
            self.cells[int(round(-lo / st))] = X_REST
    def lookup(self, s3c):
        f = dict(zip(("yaw", "pit", "roll", "x", "y", "z"), feats6(s3c)))
        u = max(0.0, min(self.n - 1.0, (f[self.col] - self.lo) / self.st)); i = min(int(u), self.n - 2)
        return tf_lerp(self.cells[i], self.cells[i + 1], u - i)
R = {k: Row(v) for k, v in rows_tr.items() if k != "idle"}
R["idle"] = Row(ID, col="pit", lo=-10, hi=4, st=1.0, bw=1.5, rest=True)
print("rows", sorted(R), "frames", sum(r.n for r in R.values()))
gdelta = local_delta(full("grab", 44 * 45 + 15), g0)
for look in LOOKS:
    ld = ms_delta(sk, full("look", look), full("idle", 0))
    Cs, cams = finish(copy(base), gdelta, None, ld); still = handcam(Cs, cams)
    res = {}
    for name, spec in TE:
        if name.startswith("turn90r"): continue
        cat = "L/R" if "L/R" in name else ("mix" if ("+" in name or "/" in name.split(" ")[0]) else name.split("_")[0])
        if cat == "sprint": cat = "jog"
        rk = rowkey(spec)
        if rk not in R: rk = "jog" if family(spec) == "jog" else rk
        lp = pose_from(spec); s3c = s3_in_cam(comp(sk, lp))
        C, cam = finish(lp, gdelta, slot_X(R[rk].lookup(s3c)), ld)
        res.setdefault(cat, []).append((vlen(vsub(handcam(C, cam), still)), name))
    for k in S["idle_long"]["frames"][1::4]:
        lp = apply_ms(sk, base, ms_delta(sk, full("idle_long", k), base)); s3c = s3_in_cam(comp(sk, lp))
        C, cam = finish(lp, gdelta, slot_X(R["idle"].lookup(s3c)), ld); res.setdefault("idle", []).append((vlen(vsub(handcam(C, cam), still)), "idle"))
    allv = sorted(v for c in res for v in res[c] if c != "L/R")
    print(f"look {look} ({(15-look)*6:+d} deg) DIR-ROWS: " + " | ".join(f"{c} {max(res[c])[0]:.1f} [{sorted(res[c])[int(.95*len(res[c]))][0]:.1f}]" for c in res) + f" | ALL(excl L/R) {allv[-1][0]:.1f} [{allv[int(.95*len(allv))][0]:.1f}] worst {allv[-1][1]}", flush=True)
pickle.dump(R, open("R_dirrows.pkl", "wb"))
