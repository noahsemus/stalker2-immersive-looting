exec(open("r11.py").read().split("grids = {}")[0])
import pickle
TT = pickle.load(open("TT.pkl", "rb"))
gdelta = local_delta(full("grab", 44 * 45 + 15), g0)
SC = {
 "walk_left": (lambda t: [("walk_left", (t/2.467) % 1, 1.0)], "walk"),
 "walk_fl": (lambda t: [("walk_fl", (t/2.467) % 1, 1.0)], "walk"),
 "walk_bl": (lambda t: [("walk_bl", (t/7.03) % 1, 1.0)], "walk"),
 "walk_bwd": (lambda t: [("walk_bwd", (t/2.467) % 1, 1.0)], "walk"),
 "run_left": (lambda t: [("run_left", (t/4.667) % 1, 1.0)], "run"),
 "run_fwd": (lambda t: [("run_fwd", (t/4.667) % 1, 1.0)], "run"),
 "run_fl": (lambda t: [("run_fl", (t/4.667) % 1, 1.0)], "run"),
 "run_br": (lambda t: [("run_br", (t/4.167) % 1, 1.0)], "run"),
 "walk_left start": (lambda t: [("walk_left", (t/2.467) % 1, min(1.0, t/0.25))], "walk"),
 "run_right start": (lambda t: [("run_right", (t/4.667) % 1, min(1.0, t/0.2))], "run"),
}
for look in LOOKS:
    ld = ms_delta(sk, full("look", look), full("idle", 0))
    Cs, cams = finish(copy(base), gdelta, None, ld); still = handcam(Cs, cams)
    print(f"look {look}: largest frame-to-frame hand jump at 30 fps over 1.4 s (cm) [max error]")
    for sn, (sc, b) in SC.items():
        out = []
        for nm, fn in [("vanilla", None)] + [(dn, T[b].lookup) for dn, T in TT.items() if dn != "K2 (clusters+pitch)"]:
            prev = None; mx = 0; me = 0
            for k in range(42):
                lp = pose_from(sc(k / 30.0)); s3c = s3_in_cam(comp(sk, lp))
                C, cam = finish(lp, gdelta, None if fn is None else slot_X(fn(s3c)), ld); h = handcam(C, cam)
                if prev is not None: mx = max(mx, vlen(vsub(h, prev)))
                me = max(me, vlen(vsub(h, still))); prev = h
            out.append(f"{nm.split(' ')[0]} {mx:.1f} [{me:.0f}]")
        print(f"  {sn:16s} " + " | ".join(out), flush=True)
