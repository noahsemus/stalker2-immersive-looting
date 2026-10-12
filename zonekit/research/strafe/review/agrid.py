from grid import *
class AGrid:
    """Analytic grid. Column axis = yaw (interpolated by the montage time). Row axes: list of (feature, lo, hi, step).
    Each node's s3c is built from the node's key values; features not in the key come from a kernel regression
    over training samples (Gaussian in the keyed features), so empty regions are filled smoothly."""
    def __init__(self, train, ystep=5.0, ylo=-100.0, yhi=100.0, rows=(), bw=None, force_rest=True):
        self.ystep, self.ylo, self.ny = ystep, ylo, int(round((yhi - ylo) / ystep)) + 1
        self.rows = rows; self.nr = [int(round((hi - lo) / st)) + 1 for _, lo, hi, st in rows]
        self.nrows = 1
        for n in self.nr: self.nrows *= n
        self.nframes = self.nrows * self.ny
        F = [dict(zip(("yaw", "pit", "roll", "x", "y", "z"), feats6(s))) for s in train]
        for f in F:
            f["th"] = math.degrees(math.atan2(f["y"], -f["x"])); f["r"] = math.hypot(f["x"], f["y"]); f["dev"] = f["th"] + f["yaw"]
        self.F = F
        keyed = ["yaw"] + [r[0] for r in rows]
        bw = bw or {"yaw": 12.0, "th": 12.0, "pit": 5.0, "r": 4.0, "x": 5.0, "y": 5.0, "z": 3.0, "dev": 12.0}
        self.cells = {}
        for ri in range(self.nrows):
            idx = self.unrow(ri); kv = {r[0]: r[1] + i * r[3] for r, i in zip(rows, idx)}
            for yi in range(self.ny):
                kv["yaw"] = ylo + yi * ystep
                # regression of non-keyed features
                ws = [math.exp(-sum(((f[k] - kv[k]) / bw[k]) ** 2 for k in keyed)) for f in F]
                tw = sum(ws)
                if tw < 1e-6:   # far from data: nearest sample's values
                    j = min(range(len(F)), key=lambda j: sum(((F[j][k] - kv[k]) / bw[k]) ** 2 for k in keyed)); ws = [1.0 if k == j else 0.0 for k in range(len(F))]; tw = 1.0
                est = {k: sum(w * f[k] for w, f in zip(ws, F)) / tw for k in ("pit", "roll", "z", "r", "th", "x", "y")}
                est.update(kv)
                if "dev" in kv:
                    th = kv["dev"] - kv["yaw"]; x, y = -est["r"] * math.cos(math.radians(th)), est["r"] * math.sin(math.radians(th))
                elif "th" in kv and "r" not in kv: x, y = -est["r"] * math.cos(math.radians(kv["th"])), est["r"] * math.sin(math.radians(kv["th"]))
                elif "th" in kv and "r" in kv: x, y = -kv["r"] * math.cos(math.radians(kv["th"])), kv["r"] * math.sin(math.radians(kv["th"]))
                elif "x" in kv and "y" in kv: x, y = kv["x"], kv["y"]
                else:
                    th = est["th"]; x, y = -est["r"] * math.cos(math.radians(th)), est["r"] * math.sin(math.radians(th))
                self.cells[(ri, yi)] = X_of(s3c_from(est["yaw"], est["pit"], 0.0, x, y, est["z"]))
        if force_rest:
            kr = self.kfeat(S3R_in_cam)
            self.cells[(self.row_of(kr), int(round(-ylo / ystep)))] = X_REST
    def unrow(self, ri):
        out = []
        for n in reversed(self.nr): out.append(ri % n); ri //= n
        return list(reversed(out))
    def row_of(self, k):
        ri = 0
        for (f, lo, hi, st), n in zip(self.rows, self.nr): ri = ri * n + max(0, min(n - 1, int(round((k[f] - lo) / st))))
        return ri
    def kfeat(self, s3c):
        f = dict(zip(("yaw", "pit", "roll", "x", "y", "z"), feats6(s3c))); f["th"] = math.degrees(math.atan2(f["y"], -f["x"])); f["r"] = math.hypot(f["x"], f["y"]); f["dev"] = f["th"] + f["yaw"]; return f
    def frame(self, s3c):
        k = self.kfeat(s3c); ri = self.row_of(k)
        u = (k["yaw"] - self.ylo) / self.ystep; u = max(0.0, min(self.ny - 1.0, u))
        return ri, u
    def lookup(self, s3c):
        ri, u = self.frame(s3c); i = min(int(u), self.ny - 2); f = u - i
        return tf_lerp(self.cells[(ri, i)], self.cells[(ri, i + 1)], f)
