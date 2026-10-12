from common import *
for mv in ALLMV:
    rows = []
    for i in range(0, len(deltas(mv)), 2):
        C = comp(sk, apply_ms(sk, base, deltas(mv)[i])); y, p, r, t = rel_feats(s3_in_cam(C))
        ang = math.degrees(math.atan2(t[1], -t[0])); rad = math.hypot(t[0], t[1])
        rows.append((y, p, r, t[0], t[1], t[2], ang, rad))
    f = lambda k: f"{min(x[k] for x in rows):6.1f}..{max(x[k] for x in rows):6.1f}"
    print(f"{mv:11s} yaw {f(0)} pitch {f(1)} roll {f(2)} | x {f(3)} y {f(4)} z {f(5)} | orbit {f(6)} radius {f(7)}")
# look_sprint invariance
for fr in (0, 8, 15, 22, 29):
    d = ms_delta(sk, full("look_sprint", fr), base)
    C = comp(sk, apply_ms(sk, apply_ms(sk, base, deltas("run_left")[10]), d)); C0 = comp(sk, apply_ms(sk, base, deltas("run_left")[10]))
    a, b = s3_in_cam(C), s3_in_cam(C0)
    print("look_sprint", fr, "s3c change rot", round(qangle(a[0], b[0]),3), "pos", round(vlen(vsub(a[1], b[1])),3), " spine/VBcam/l_sh delta", [round(qangle(d[i][0],QI),1) for i in (S3, VCAM, SH)])
