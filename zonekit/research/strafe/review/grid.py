from common import *
import pickle
R5 = pickle.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "r5_sets.pkl"), "rb"))
FWD_LOCAL = (0.0, -1.0, 0.0)
F_REST = qrot(S3R_in_cam[0], FWD_LOCAL)
YAW0 = math.degrees(math.atan2(F_REST[1], F_REST[0])); PIT0 = math.degrees(math.asin(F_REST[2]))
def key(s3c):
    F = qrot(s3c[0], FWD_LOCAL); P = s3c[1]
    yaw = math.degrees(math.atan2(F[1], F[0])) - YAW0; pit = math.degrees(math.asin(max(-1, min(1, F[2])))) - PIT0
    th = math.degrees(math.atan2(P[1], -P[0])); r = math.hypot(P[0], P[1])
    return dict(yaw=yaw, pit=pit, th=th, r=r, x=P[0], y=P[1], z=P[2])
def X_of(s3c): X = tmul(tinv(s3c), SHR_in_cam); return (qnorm(X[0]), X[1])
X_REST = X_of(S3R_in_cam)
def tf_lerp(a, b, f):
    qb = b[0]
    if sum(x*y for x, y in zip(a[0], qb)) < 0: qb = tuple(-x for x in qb)
    return (qnorm(tuple((1-f)*x + f*y for x, y in zip(a[0], qb))), tuple((1-f)*x + f*y for x, y in zip(a[1], b[1])))
def mean_tf(lst):
    q0 = lst[0][0]; acc = [0,0,0,0]; t = [0,0,0]
    for q, p in lst:
        if sum(a*b for a, b in zip(q, q0)) < 0: q = tuple(-x for x in q)
        acc = [a+b for a, b in zip(acc, q)]; t = [a+b for a, b in zip(t, p)]
    return qnorm(tuple(acc)), tuple(x/len(lst) for x in t)
class Grid:
    """frame layout: row-major; yaw is the interpolated (column) axis. rows: tuple of (feature, lo, hi, step)"""
    def __init__(self, train, ystep=5.0, ylo=-100.0, yhi=100.0, rows=(), force_rest=True):
        self.ystep, self.ylo, self.ny = ystep, ylo, int(round((yhi - ylo) / ystep)) + 1
        self.rows = rows
        self.nr = [int(round((hi - lo) / st)) + 1 for _, lo, hi, st in rows]
        nrows = 1
        for n in self.nr: nrows *= n
        self.nrows = nrows
        buckets = {}
        for s3c in train:
            k = key(s3c); ri = self.row_of(k)
            yi = int(round((k["yaw"] - ylo) / ystep)); yi = max(0, min(self.ny - 1, yi))
            buckets.setdefault((ri, yi), []).append(s3c)
        self.cells = {}
        for ri in range(nrows):
            for yi in range(self.ny):
                if (ri, yi) in buckets: self.cells[(ri, yi)] = X_of(mean_tf(buckets[(ri, yi)]))
        filled = dict(self.cells)
        # fill: nearest yaw in row, else nearest row (by row index distance in each dim)
        for ri in range(nrows):
            have = [yi for yi in range(self.ny) if (ri, yi) in filled]
            for yi in range(self.ny):
                if (ri, yi) in self.cells: continue
                if have: self.cells[(ri, yi)] = filled[(ri, min(have, key=lambda h: abs(h - yi)))]
        for ri in range(nrows):
            for yi in range(self.ny):
                if (ri, yi) in self.cells: continue
                cands = [(self.rowdist(ri, rj), abs(yj - yi), (rj, yj)) for (rj, yj) in filled]
                self.cells[(ri, yi)] = filled[min(cands)[2]]
        if force_rest:
            kr = key(S3R_in_cam); ri = self.row_of(kr); yi = int(round((0 - ylo) / ystep))
            self.cells[(ri, yi)] = X_REST
        self.nframes = nrows * self.ny
    def row_idx(self, k):
        idx = []
        for (f, lo, hi, st), n in zip(self.rows, self.nr):
            idx.append(max(0, min(n - 1, int(round((k[f] - lo) / st)))))
        return idx
    def row_of(self, k):
        ri = 0
        for i, n in zip(self.row_idx(k), self.nr): ri = ri * n + i
        return ri
    def unrow(self, ri):
        out = []
        for n in reversed(self.nr): out.append(ri % n); ri //= n
        return list(reversed(out))
    def rowdist(self, a, b): return sum(abs(x - y) for x, y in zip(self.unrow(a), self.unrow(b)))
    def lookup(self, s3c):
        k = key(s3c); ri = self.row_of(k)
        u = (k["yaw"] - self.ylo) / self.ystep; u = max(0.0, min(self.ny - 1.0, u))
        i = min(int(u), self.ny - 2); f = u - i
        return tf_lerp(self.cells[(ri, i)], self.cells[(ri, i + 1)], f)
def slot_X(X):
    pose = copy(base); pose[SH] = [X[0], X[1]]; return pose
# ---- analytic s3c from features ----
def s3c_from(yaw, pit, roll, x, y, z):
    """rotation: rest s3 rotation, then (in camera axes) roll about the spine's forward, pitch, yaw; position given"""
    Fh = (math.cos(math.radians(YAW0)), math.sin(math.radians(YAW0)), 0.0)
    # build delta: first roll about F_REST, then pitch about horizontal axis perpendicular to F_REST, then yaw about Z
    qr = qaxis(F_REST, roll)
    side = (-Fh[1], Fh[0], 0.0)    # horizontal axis perpendicular (left-handed issues handled by sign check below)
    qp = qaxis(side, -pit)
    qy = qaxis((0, 0, 1), yaw)
    q = qnorm(qmul(qy, qmul(qp, qmul(qr, S3R_in_cam[0]))))
    return (q, (x, y, z))
def roll_of(s3c):
    """roll: angle about F of the spine's up axis vs the vertical plane"""
    q = s3c[0]
    F = qrot(q, FWD_LOCAL); U = qrot(q, (1.0, 0.0, 0.0))     # spine local X = up at rest
    # remove yaw and pitch: express U in frame (F, side, up') and compare to rest
    k = key(s3c)
    qy = qaxis((0,0,1), -k["yaw"]); Fh = (math.cos(math.radians(YAW0)), math.sin(math.radians(YAW0)), 0.0)
    side = (-Fh[1], Fh[0], 0.0); qp = qaxis(side, k["pit"])
    U2 = qrot(qp, qrot(qy, U)); U0 = qrot(S3R_in_cam[0], (1.0, 0.0, 0.0))
    c = qrot(qinv(qaxis(F_REST, 0)), U2)
    # signed angle about F_REST from U0 to U2
    cr = (U0[1]*U2[2]-U0[2]*U2[1], U0[2]*U2[0]-U0[0]*U2[2], U0[0]*U2[1]-U0[1]*U2[0])
    s = sum(a*b for a, b in zip(cr, F_REST)); cc = sum(a*b for a, b in zip(U0, U2))
    return math.degrees(math.atan2(s, cc))
def feats6(s3c):
    k = key(s3c); return k["yaw"], k["pit"], roll_of(s3c), k["x"], k["y"], k["z"]
