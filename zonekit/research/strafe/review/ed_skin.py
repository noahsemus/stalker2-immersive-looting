import unreal, os, json
log = []
def L(s): log.append(str(s))
names = [n for n in dir(unreal) if "GeometryScript" in n and ("Bone" in n or "AssetUtils" in n or "Weight" in n)]
L(names[:40])
res = {}
try:
    m = unreal.load_asset("/Game/_STALKER2/SkeletalMeshes/characters/_han/SK_han_00_a")
    L(f"mesh {m}")
    dm = unreal.DynamicMesh()
    opts = unreal.GeometryScriptCopyMeshFromAssetOptions()
    lod = unreal.GeometryScriptMeshReadLOD()
    r = unreal.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(m, dm, opts, lod)
    L(f"copy result {r}")
    L(f"verts {unreal.GeometryScript_MeshQueries.get_vertex_count(dm)}")
    BW = unreal.GeometryScript_BoneWeights if hasattr(unreal, "GeometryScript_BoneWeights") else None
    L(f"BW {BW} {[x for x in dir(BW) if not x.startswith('_')] if BW else ''}")
except Exception as e:
    import traceback; L(traceback.format_exc())
open(os.path.join(SCRATCH, "rev_skin.txt"), "w").write("\n".join(log))
