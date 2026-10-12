import pickle, sys
exec(open("vis.py").read().split("gdelta = ")[0])
gdelta = local_delta(full("grab", 44 * 45 + 15), g0)
worst = (999, None)
nvis_tot = 0
for mv in ("walk_left", "walk_right", "run_left", "run_right", "walk_fl", "walk_fr", "walk_bl", "walk_br", "run_bl", "run_br", "jog_fwd"):
    for look in (12, 15, 18, 21, 24, 27, 29):
        ld = ms_delta(sk, full("look", look), full("idle", 0))
        for i in range(0, len(deltas(mv)), max(1, len(deltas(mv)) // 5)):
            lp = apply_ms(sk, base, deltas(mv)[i])
            C, cam = finish(lp, gdelta, slot_X(X_of(s3_in_cam(comp(sk, lp)))), ld)
            for v in mixed[::3]:
                c = incam(cam, skin(C, v))
                if c[0] > 0:
                    m = max(abs(math.degrees(math.atan2(c[1], c[0]))) - HF, abs(math.degrees(math.atan2(c[2], c[0]))) - VF)
                    if m < worst[0]: worst = (m, (mv, look, i, tuple(round(x) for x in c)))
                    if m < 0: nvis_tot += 1
print(NAME, "mixed verts", len(mixed), "| visible count", nvis_tot, "| closest approach to a 110x72 deg frustum (deg outside):", round(worst[0], 1), worst[1])
