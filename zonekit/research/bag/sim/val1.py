from bagsim import *
for st in ("stand", "lowcrouch"):
    for pitch in (0, -30, -60):
        C, cam, _ = compose(st, pitch)
        f = qrot(cam[0], (1, 0, 0))
        print(f"{st} pitch {pitch}: cam bone X elev {math.degrees(math.asin(f[2])):.1f}, cam pos {tuple(round(x,1) for x in cam[1])}, l_hand view {view(C, cam, pitch, LH)}")
cases = [("stand", -59, "bag_idle", 0.0, ("pitchfix", 59), "(45,-28,+17)"),
         ("stand", -32, "bag_in", 1.5, ("pitchfix", 32), "(29,-27,+9)"),
         ("lowcrouch", -25, "bag_idle", 0.0, ("pitchfix", 0), "(41,-16,-26)"),
         ("lowcrouch", -25, "bag_idle", 0.0, ("pitchfix", 25), "(41,-16,-26)?")]
for st, pitch, bk, t, (tk, tf), exp in cases:
    bag = raw_t(bk, t)
    C, cam, _ = compose(st, pitch, bag, table_delta(tk, tf))
    C2, cam2, _ = compose(st, pitch, bag, None)
    print(f"{st} {pitch} {bk}@{t} {tk}[{tf}]: l_weapon view {view(C, cam, pitch)} (no table {view(C2, cam2, pitch)})  probe {exp}")
for k, t in (("bag_idle", 0.0), ("bag_in", 0.0), ("bag_in", 0.5), ("bag_out", 0.6)):
    print(f"vanilla {k}@{t}: l_weapon in anim camera axes {anim_view(k, t)}")
