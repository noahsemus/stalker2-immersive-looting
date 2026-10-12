exec(open("r22.py").read().split("gdelta = local_delta")[0].replace('print("rows"', '#'))
T = pickle.load(open("T_y10.pkl", "rb"))
TRL = [s for _, s in TRS]
def nn(s3c): return X_of(min(TRL, key=lambda s: vlen(vsub(s[1], s3c[1])) + 0.5 * qangle(s[0], s3c[0])))
gdelta = local_delta(full("grab", 44 * 45 + 15), g0)
ld = ms_delta(sk, full("look", 23), full("idle", 0))
SC = {  # (spec(t), T band, dir row)
 "walk_left steady": (lambda t: [("walk_left", (t/2.467) % 1, 1.0)], "walk", "walk_left"),
 "walk_bl steady": (lambda t: [("walk_bl", (t/7.03) % 1, 1.0)], "walk", "walk_bl"),
 "walk_bwd steady": (lambda t: [("walk_bwd", (t/2.467) % 1, 1.0)], "walk", "walk_bwd"),
 "run_left steady": (lambda t: [("run_left", (t/4.667) % 1, 1.0)], "run", "run_left"),
 "run_fwd steady": (lambda t: [("run_fwd", (t/4.667) % 1, 1.0)], "run", "run_fwd"),
 "run_fl steady": (lambda t: [("run_fl", (t/4.667) % 1, 1.0)], "run", "run_fl"),
 "walk_left start": (lambda t: [("walk_left", (t/2.467) % 1, min(1.0, t/0.25))], "walk", "walk_left"),
 "run_right start": (lambda t: [("run_right", (t/4.667) % 1, min(1.0, t/0.2))], "run", "run_right"),
}
print("per-frame hand jump (cm) at 30 fps over 1.4 s, look -48 deg: max step [and max abs error]")
for sn, (sc, b, dr) in SC.items():
    out = []
    for nm, fn in (("vanilla", None), ("plan_nn6d", nn), ("T", T[b].lookup), ("DIRROWS", R[dr].lookup), ("exact", lambda s: X_of(s))):
        prev = None; mx = 0; me = 0
        Cs, cams = finish(copy(base), gdelta, None, ld); still = handcam(Cs, cams)
        for k in range(42):
            t = k / 30.0; lp = pose_from(sc(t)); s3c = s3_in_cam(comp(sk, lp))
            C, cam = finish(lp, gdelta, None if fn is None else slot_X(fn(s3c)), ld); h = handcam(C, cam)
            if prev is not None: mx = max(mx, vlen(vsub(h, prev)))
            me = max(me, vlen(vsub(h, still))); prev = h
        out.append(f"{nm} {mx:.1f} [{me:.0f}]")
    print(f"  {sn:18s} " + " | ".join(out), flush=True)
