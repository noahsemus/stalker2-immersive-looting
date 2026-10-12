exec(open("r11.py").read().split("grids = {}")[0])
import itertools
CFG = {
 "walk": (("th", -100, 100, 10),),
 "run":  (("th", -60, 60, 10), ("r", 26, 38, 4)),
 "jog":  (),
}
grids = {f: AGrid(fam_train[f], YS, ylo=-100, yhi=100, rows=CFG[f]) for f in CFG}
grids["idle"] = grids["walk"]
nfr = sum(grids[f].nframes for f in CFG)
print("frames", {f: grids[f].nframes for f in CFG}, "total", nfr)
exec("gdelta = local_delta" + open("r11.py").read().split("gdelta = local_delta")[1])
