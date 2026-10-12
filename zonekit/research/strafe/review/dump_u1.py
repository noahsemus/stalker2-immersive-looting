import pickle, json
from agrid import *
U = pickle.load(open("U.pkl", "rb"))["U1 th10 x pit6"]
T = pickle.load(open("TT.pkl", "rb"))["T (theta/pitch grid)"]; IDLE = T["idle"]
frames = []
for ri in range(U.nrows):
    for yi in range(U.ny): frames.append(U.cells[(ri, yi)])
for ri in range(IDLE.nrows):
    for yi in range(IDLE.ny): frames.append(IDLE.cells[(ri, yi)])
out = {"bone": "jnt_l_shoulder (local to jnt_spine_03); every other left_hand_blend_mask bone = fp_bh_idle_stand frame 0 local",
       "fps": 30, "layout": "moving block: frame = (ith*7 + ipit)*21 + u, ith = clamp(round((theta+100)/10),0,20), ipit = clamp(round((pitch+24)/6),0,6), u = clamp((yaw+100)/10,0,20) (fractional = interpolation); idle block (speed < 10 cm/s): frame = 3087 + ipi*21 + u, ipi = clamp(round((pitch+10)/2),0,7)",
       "key": "Ts=GetSocketTransform(jnt_spine_03,RTS_Component), Tc=GetSocketTransform(jnt_camera,RTS_Component); P=InverseTransformLocation(Tc,Ts.Location); F=InverseTransformDirection(Tc, -RightVector(Ts.Rotation)); yaw=atan2d(F.Y,F.X); pitch=asind(F.Z)+6.873; theta=atan2d(P.Y,-P.X)",
       "frames": [[list(q), list(t)] for q, t in frames]}
json.dump(out, open("U1_table.json", "w"))
print(len(frames), "frames written; rest frame check:", [round(x, 4) for x in frames[(10*7+4)*21 + 10][0]], X_REST[0])
