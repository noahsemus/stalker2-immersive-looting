"""Pose math matching UE 5.5 FAnimationRuntime conventions (FQuat A*B = apply B first, then A).
Pose = list of [q(x,y,z,w), t(x,y,z)] in LOCAL space, one per bone (indices of dump['bones'])."""
import json, math

def qmul(a, b):
    ax, ay, az, aw = a; bx, by, bz, bw = b
    return (aw*bx+ax*bw+ay*bz-az*by, aw*by-ax*bz+ay*bw+az*bx, aw*bz+ax*by-ay*bx+az*bw, aw*bw-ax*bx-ay*by-az*bz)
def qinv(a): return (-a[0], -a[1], -a[2], a[3])
def qnorm(a):
    n = math.sqrt(sum(x*x for x in a)); return tuple(x/n for x in a)
def qrot(a, p):
    r = qmul(qmul(a, (p[0], p[1], p[2], 0.0)), qinv(a)); return r[:3]
def vadd(a, b): return (a[0]+b[0], a[1]+b[1], a[2]+b[2])
def vsub(a, b): return (a[0]-b[0], a[1]-b[1], a[2]-b[2])
def vmul(a, s): return (a[0]*s, a[1]*s, a[2]*s)
def vlen(a): return math.sqrt(a[0]*a[0]+a[1]*a[1]+a[2]*a[2])
def qangle(a, b):
    d = abs(sum(x*y for x, y in zip(a, b))); return math.degrees(2*math.acos(min(1.0, d)))
def qaxis(axis, deg):
    h = math.radians(deg)/2; s = math.sin(h); return (axis[0]*s, axis[1]*s, axis[2]*s, math.cos(h))
QI = (0.0, 0.0, 0.0, 1.0)

def qslerp_id(q, w):
    """UE FTransform::Blend(Identity, q, w) for rotations: FQuat::FastLerp + normalize (shortest path)."""
    if q[3] < 0: q = tuple(-x for x in q)
    r = tuple((1-w)*i + w*x for i, x in zip(QI, q)); return qnorm(r)

class Skel:
    def __init__(self, dump):
        self.bones = dump["bones"]; self.idx = {b: i for i, b in enumerate(self.bones)}
        self.parents = list(dump["parents"])
        self.order = self._order()
    def _order(self):
        done, order = set(), []
        while len(order) < len(self.bones):
            for i, p in enumerate(self.parents):
                if i not in done and (p < 0 or p in done):
                    done.add(i); order.append(i)
        return order

def to_pose(rows):
    return [[tuple(r[0:4]), tuple(r[4:7])] for r in rows]

def copy(p): return [[q, t] for q, t in p]

def comp(sk, pose):
    """component-space (q, t) per bone"""
    C = [None]*len(pose)
    for i in sk.order:
        q, t = pose[i]; p = sk.parents[i]
        if p < 0: C[i] = (q, t)
        else:
            pq, pt = C[p]; C[i] = (qmul(pq, q), vadd(pt, qrot(pq, t)))
    return C

def ms_rot(sk, pose):
    """ConvertPoseToMeshRotation: rotations to mesh space, translations stay local"""
    R = [None]*len(pose)
    for i in sk.order:
        p = sk.parents[i]
        R[i] = pose[i][0] if p < 0 else qmul(R[p], pose[i][0])
    return R

def from_ms_rot(sk, R, trans):
    """ConvertMeshRotationPoseToLocalSpace"""
    out = []
    for i in range(len(R)):
        p = sk.parents[i]
        out.append([R[i] if p < 0 else qmul(qinv(R[p]), R[i]), trans[i]])
    return out

def local_delta(target, base):
    return [[qnorm(qmul(tq, qinv(bq))), vsub(tt, bt)] for (tq, tt), (bq, bt) in zip(target, base)]

def ms_delta(sk, target, base):
    RT, RB = ms_rot(sk, target), ms_rot(sk, base)
    return [[qnorm(qmul(rt, qinv(rb))), vsub(target[i][1], base[i][1])] for i, (rt, rb) in enumerate(zip(RT, RB))]

def _acc(q, d, w):
    dq = d if w >= 1 - 1e-5 else qslerp_id(d, w)
    return qnorm(qmul(dq, q))

def apply_local(base, delta, w=1.0, weights=None):
    out = []
    for i, ((q, t), (dq, dt)) in enumerate(zip(base, delta)):
        ww = w * (1.0 if weights is None else weights[i])
        if ww <= 0: out.append([q, t]); continue
        out.append([_acc(q, dq, ww), vadd(t, vmul(dt, ww))])
    return out

def apply_ms(sk, base, delta, w=1.0, weights=None):
    """AccumulateMeshSpaceRotationAdditiveToLocalPose"""
    R = ms_rot(sk, base); T = [t for _, t in base]
    for i, (dq, dt) in enumerate(delta):
        ww = w * (1.0 if weights is None else weights[i])
        if ww <= 0: continue
        R[i] = _acc(R[i], dq, ww); T[i] = vadd(T[i], vmul(dt, ww))
    return from_ms_rot(sk, R, T)

def lbb_local(sk, base, blend, weights):
    """LayeredBoneBlend, local space (bMeshSpaceRotationBlend false): per bone lerp base->blend by weight"""
    out = []
    for i, ((bq, bt), (lq, lt)) in enumerate(zip(base, blend)):
        w = weights[i]
        if w <= 0: out.append([bq, bt])
        elif w >= 1: out.append([lq, lt])
        else:
            if sum(x*y for x, y in zip(bq, lq)) < 0: lq = tuple(-x for x in lq)
            out.append([qnorm(tuple((1-w)*a + w*b for a, b in zip(bq, lq))), vadd(vmul(bt, 1-w), vmul(lt, w))])
    return out

def lbb_meshrot(sk, base, blend, weights):
    """LayeredBoneBlend with bMeshSpaceRotationBlend: rotations blended in mesh space, translations local"""
    RB, RL = ms_rot(sk, base), ms_rot(sk, blend)
    R, T = [], []
    for i in range(len(base)):
        w = weights[i]; bq, lq = RB[i], RL[i]
        if w <= 0: R.append(bq); T.append(base[i][1])
        elif w >= 1: R.append(lq); T.append(blend[i][1])
        else:
            if sum(x*y for x, y in zip(bq, lq)) < 0: lq = tuple(-x for x in lq)
            R.append(qnorm(tuple((1-w)*a + w*b for a, b in zip(bq, lq)))); T.append(vadd(vmul(base[i][1], 1-w), vmul(blend[i][1], w)))
    return from_ms_rot(sk, R, T)
