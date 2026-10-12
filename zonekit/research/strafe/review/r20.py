exec(open("r16.py").read().split("gdelta = local_delta")[0])
# idle band: one row, column = spine pitch (-10..+4, 1 deg, interpolated); other features regressed on breathing samples
ID = []
for k in S["idle_long"]["frames"][::2]:
    ID.append(s3_in_cam(comp(sk, apply_ms(sk, base, ms_delta(sk, full("idle_long", k), base)))))
IDF = [dict(zip(("yaw","pit","roll","x","y","z"), feats6(s))) for s in ID]
PLO, PST, PN = -10.0, 1.0, 15
idle_cells = []
for j in range(PN):
    p = PLO + j * PST
    ws = [math.exp(-((f["pit"] - p) / 1.5) ** 2) for f in IDF]; tw = sum(ws) or 1
    est = {k: sum(w * f[k] for w, f in zip(ws, IDF)) / tw for k in ("yaw", "x", "y", "z")}
    idle_cells.append(X_of(s3c_from(est["yaw"], p, 0.0, est["x"], est["y"], est["z"])))
idle_cells[int(round(-PLO / PST))] = X_REST
def idle_lookup(s3c):
    p = feats6(s3c)[1]; u = max(0.0, min(PN - 1.0, (p - PLO) / PST)); i = min(int(u), PN - 2)
    return tf_lerp(idle_cells[i], idle_cells[i + 1], u - i)
gdelta = local_delta(full("grab", 44 * 45 + 15), g0)
for look in (15, 23):
    ld = ms_delta(sk, full("look", look), full("idle", 0))
    Cs, cams = finish(copy(base), gdelta, None, ld); still = handcam(Cs, cams)
    dv, dt_ = [], []
    for k in S["idle_long"]["frames"][1::2]:
        lp = apply_ms(sk, base, ms_delta(sk, full("idle_long", k), base)); s3c = s3_in_cam(comp(sk, lp))
        C, cam = finish(lp, gdelta, None, ld); dv.append(vlen(vsub(handcam(C, cam), still)))
        C, cam = finish(lp, gdelta, slot_X(idle_lookup(s3c)), ld); dt_.append(vlen(vsub(handcam(C, cam), still)))
    print(f"look{look} standing breathing (test frames): vanilla {max(dv):.1f} cm | idle band (pitch-keyed row, {PN} frames) {max(dt_):.1f} cm")
