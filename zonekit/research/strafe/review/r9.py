from agrid import *
exec(open("r5.py").read().split("TR, TE = specs")[0].split("import time, random")[1].replace("random.seed(1)\nt0 = time.time()\nprint(\"bones\", len(B))", ""))
for r in (0.5, 0.45, 0.4, 0.3, 0.15):
    for g in ("walk", "run"):
        fs = []
        for ph in [i/12 for i in range(12)]:
            s3c = s3_in_cam(comp(sk, pose_from([(f"{g}_left", ph, r), (f"{g}_right", ph, 1-r)])))
            f = feats6(s3c); fs.append(f)
        print(g, "L", r, "R", round(1-r,2), " yaw %.0f..%.0f pitch %.0f..%.0f roll %.0f..%.0f x %.0f..%.0f y %.0f..%.0f z %.0f..%.0f" % sum(((min(f[k] for f in fs), max(f[k] for f in fs)) for k in range(6)), ()))
