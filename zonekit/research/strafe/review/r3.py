from common import *
for mv in MOVES:
    rows = []
    for w in (0.25, 0.5, 0.75, 1.0):
        for i in range(0, len(DELTAS[mv]), 4):
            C = comp(sk, apply_ms(sk, base, DELTAS[mv][i], w=w)); s3c = s3_in_cam(C)
            y, p, r, t = rel_feats(s3c)
            rows.append((w, i, y, p, r, t))
    for w in (0.25, 0.5, 0.75, 1.0):
        rr = [x for x in rows if x[0] == w]
        rng = lambda k: (round(min(x[k] for x in rr),1), round(max(x[k] for x in rr),1))
        rngt = lambda j: (round(min(x[5][j] for x in rr),1), round(max(x[5][j] for x in rr),1))
        print(mv, w, "yaw", rng(2), "pitch", rng(3), "roll", rng(4), "pos x", rngt(0), "y", rngt(1), "z", rngt(2))
print("rest pos", S3R_in_cam[1])
