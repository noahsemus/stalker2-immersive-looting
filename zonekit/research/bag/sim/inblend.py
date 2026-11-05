"""v1.3.2 ac: the bag In's first frames standing, with the table at full weight from frame 0 vs blended in over 0.15 s
(the In comes in at once): left weapon bone in view axes, against the anim's own framing"""
from whichpose import tdelta, frame
from bagsim import *
p = -40.0
for k in (0, 1, 2, 3, 4, 5, 6, 9, 12, 15, 21, 30, 45):
    bag = raw("bag_in", k)
    for w, nm in ((1.0, "full"), (min(1.0, k / 4.5), "0.15s")):
        C, cam, _ = compose("stand", p, bag, tdelta(0, p), tw=w)
        print(f"In frame {k:2} table {nm:5} w {w:.2f}: bag {view(C, cam, p)}  anim {anim_view('bag_in', k / 30.0)[0]}")
