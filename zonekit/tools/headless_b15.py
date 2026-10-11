"""One headless pass for build 15 (editor closed): door assets, actor variables / input off, the unused input assets
removed, the MCM provider Blueprint created, MCM's example Blueprint exported (to lift its interface nodes)."""
import os
import traceback
import unreal

EAL = unreal.EditorAssetLibrary
here = os.path.join(REPO, "zonekit", "tools")
log = []


def run(path, args):
    g = dict(globals())
    g["ARGS"] = dict(args)
    try:
        exec(compile(open(path, encoding="utf-8").read(), path, "exec"), g)
        log.append(f"ran {os.path.basename(path)}")
    except Exception:
        log.append(f"FAILED {os.path.basename(path)}: " + traceback.format_exc())


run(os.path.join(here, "make_grab_seq.py"), {"TOUCH": "0", "BH": "0", "DOOR": "1"})
run(os.path.join(here, "setup_assets.py"), {})
for p in ("/ImmersiveLooting/Input/IA_ImmLootInteract", "/ImmersiveLooting/Input/IMC_ImmLoot"):
    if EAL.does_asset_exist(p):
        log.append(f"delete {p}: {EAL.delete_asset(p)}")
# MCM provider
try:
    path = "/ImmersiveLooting/Runtime/BP_ImmLootMCM"
    if not EAL.does_asset_exist(path):
        f = unreal.BlueprintFactory()
        f.set_editor_property("parent_class", unreal.Actor)
        bp = unreal.AssetToolsHelpers.get_asset_tools().create_asset("BP_ImmLootMCM", "/ImmersiveLooting/Runtime", unreal.Blueprint, f)
    bp = unreal.load_asset(path)
    BEL = unreal.BlueprintEditorLibrary
    log.append("BEL interface funcs: " + str([n for n in dir(BEL) if "interface" in n.lower()]))
    iface = unreal.load_asset("/ModConfigurationMenu/BPI_MCM_SettingsProvider")
    log.append(f"iface: {iface}")
    for name, kind in (("TouchBodies", "bool"), ("Registered", "bool")):
        try:
            t = BEL.get_basic_type_by_name(kind)
            log.append(f"var {name}: {BEL.add_member_variable(bp, name, t)}")
        except Exception as e:
            log.append(f"var {name} ERR {e}")
    BEL.compile_blueprint(bp)
    cdo = unreal.get_default_object(BEL.generated_class(bp))
    cdo.set_editor_property("TouchBodies", True)
    log.append(f"saved {EAL.save_asset(path, only_if_is_dirty=False)}")
except Exception:
    log.append("MCM BP: " + traceback.format_exc())
# export the example's graph (its interface events and message nodes)
try:
    for a in ("/MCM_ModExample1/BP_MCM_ModExample1", "/ModConfigurationMenu/BPI_MCM_API"):
        asset = unreal.load_asset(a)
        dst = os.path.join(SCRATCH, asset.get_name() + ".t3d")
        t = unreal.AssetExportTask()
        t.object = asset; t.filename = dst; t.automated = True; t.prompt = False; t.replace_identical = True
        log.append(f"export {a}: {unreal.Exporter.run_asset_export_task(t)} {os.path.getsize(dst) if os.path.exists(dst) else 0}")
except Exception:
    log.append("export: " + traceback.format_exc())
os.makedirs(SCRATCH, exist_ok=True)
open(os.path.join(SCRATCH, "headless_b15.txt"), "w", encoding="utf-8").write("\n".join(log))
print("\n".join(log))
