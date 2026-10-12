import json, struct, os, sys, math
G = r"C:/Users/noahs/AppData/Local/Temp/stalker2-harness/rev_gltf/"
g = json.load(open(G + "SK_han_00_a.gltf")); binb = open(G + "SK_han_00_a.bin", "rb").read()
print("meshes", len(g["meshes"]), [ [list(p["attributes"].keys()) for p in m["primitives"]] for m in g["meshes"]])
print("skins", len(g["skins"]), "joints", len(g["skins"][0]["joints"]))
print("asset", g.get("asset"))
print([g["nodes"][j]["name"] for j in g["skins"][0]["joints"]][:60])
