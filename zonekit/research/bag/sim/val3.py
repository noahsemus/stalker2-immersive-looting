from bagsim import *
for key, k in (("pitchfix", 30), ("servo", 1138)):
    ue = to_pose(S[key]["ue_add"][str(k)])
    mine = ms_delta(sk, raw(key, k), raw(key, 0))
    errs = sorted(((qangle(a[0], b[0]), B[i], qangle(a[0], QI), qangle(b[0], QI)) for i, (a, b) in enumerate(zip(mine, ue))), reverse=True)[:6]
    print(key, k, [(round(e, 2), b, round(m, 1), round(u, 1)) for e, b, m, u in errs])
    print("  tracked:", len(M[key]["tracks"]), "untracked examples:", [b for b in B if b not in M[key]["tracks"]][:8])
