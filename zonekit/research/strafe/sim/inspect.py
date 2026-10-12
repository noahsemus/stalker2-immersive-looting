import json, sys
d = json.load(open(sys.argv[1]))
B = d["bones"]; P = d["parents"]
print(len(B))
print([ (i,b,B[P[i]] if P[i]>=0 else None) for i,b in enumerate(B) if not b.startswith('jnt_l_hand_') and not b.startswith('jnt_r_hand_')][:200])
for k, m in d["meta"].items():
    print(k, {x: m[x] for x in m if x != 'tracks'}, 'ntracks', len(m['tracks']))
    if k.startswith('grab'): print('  tracks', m['tracks'])
