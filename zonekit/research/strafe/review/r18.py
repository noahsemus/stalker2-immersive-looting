from agrid import *
gdelta = local_delta(full("grab", 44 * 45 + 15), g0)
g_rest = local_delta(full("grab", 44 * 45 + 0), g0)   # segment start = rest arm
for look in (15, 23):
    ld = ms_delta(sk, full("look", look), full("idle", 0))
    for gd, gname in ((gdelta, "reach t0.5"), (g_rest, "pickup start (arm at rest)")):
        Cs, cams = finish(copy(base), gd, None, ld); still = handcam(Cs, cams)
        for mv, i in (("walk_left", 20), ("walk_right", 20), ("run_left", 10)):
            lp = apply_ms(sk, base, deltas(mv)[i]); X = X_of(s3_in_cam(comp(sk, lp)))
            out = []
            for a in (0.0, 0.25, 0.5, 0.75, 1.0):
                C, cam = finish(lp, gd, slot_X(X), ld, alpha=a) if a > 0 else finish(lp, gd, None, ld)
                hc = handcam(C, cam); out.append(f"a{a}: {vlen(vsub(hc, still)):.0f} ({hc[0]:.0f},{hc[1]:.0f},{hc[2]:.0f})")
            print(f"look{look} {gname:26s} {mv:10s} " + " | ".join(out))
