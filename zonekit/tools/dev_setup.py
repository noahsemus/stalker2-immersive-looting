"""v1.3.2 n (tester: "can we do something like ZST's custom menu to live change the hand positioning instead of MCM?
it should still be dev only"): the DEV tuning assets, in /ImmersiveLooting/Dev/ (never in a release).

  ABP_ImmLootDevPose  post-process anim BP (parent AnimInstancePlayer, like ImmersiveDialogue's body layer): Input
                      Pose -> both shoulders and the left hand turned / moved live (Transform (Modify) Bone, world
                      space, additive) -> out. Its AnimGraph is pasted from zonekit/tools/gen_abp_devpose.py.
  W_ImmLootDev        the in-game panel (the actor builds its rows at runtime into the root Canvas Panel, which the
                      tester adds once in the designer: Python cannot edit a widget tree).
Run in the open editor with the harness ue_exec tool.
"""
import os
import unreal

EAL = unreal.EditorAssetLibrary
BEL = unreal.BlueprintEditorLibrary
DEV = f"{MOD_ROOT}/Dev"
out = []
SKEL = "/Game/_STALKER2/SkeletalMeshes/SK_stalker_Skeleton"


def add_vars(bp, path, vars_):
    BEL.compile_blueprint(bp)
    cdo = unreal.get_default_object(BEL.generated_class(bp))
    for name, kind, default in vars_:
        try:
            cdo.get_editor_property(name)
            continue
        except Exception:
            pass
        t = BEL.get_basic_type_by_name(kind) if kind in ("bool", "int", "real") else BEL.get_struct_type(
            {"rotator": unreal.Rotator, "vector": unreal.Vector}[kind].static_struct())
        out.append(f"{path}: add {name} -> {BEL.add_member_variable(bp, name, t)}")
    BEL.compile_blueprint(bp)
    cdo = unreal.get_default_object(BEL.generated_class(bp))
    for name, kind, default in vars_:
        if default is not None:
            cdo.set_editor_property(name, default)
    out.append(f"{path} saved: {EAL.save_asset(path, only_if_is_dirty=False)}")


try:
    # the anim BP
    path = f"{DEV}/ABP_ImmLootDevPose"
    if not EAL.does_asset_exist(path):
        f = unreal.AnimBlueprintFactory()
        f.set_editor_property("target_skeleton", unreal.load_asset(SKEL))
        f.set_editor_property("parent_class", unreal.load_class(None, "/Script/Stalker2.AnimInstancePlayer"))
        unreal.AssetToolsHelpers.get_asset_tools().create_asset("ABP_ImmLootDevPose", DEV, unreal.AnimBlueprint, f)
        out.append(f"created {path}")
    abp = unreal.load_asset(path)
    out.append("abp class: " + str(BEL.generated_class(abp)))
    add_vars(abp, path, [("ArmRot", "rotator", None), ("ArmPos", "vector", None), ("HandRot", "rotator", None),
                         ("ArmAlpha", "real", 0.0), ("HandAlpha", "real", 0.0)])
    # the panel
    wpath = f"{DEV}/W_ImmLootDev"
    if not EAL.does_asset_exist(wpath):
        f = unreal.WidgetBlueprintFactory()
        f.set_editor_property("parent_class", unreal.UserWidget)
        unreal.AssetToolsHelpers.get_asset_tools().create_asset("W_ImmLootDev", DEV, unreal.WidgetBlueprint, f)
        out.append(f"created {wpath}")
    tp = f"{DEV}/W_ImmLootDevTest"
    if EAL.does_asset_exist(tp):
        out.append(f"deleted test widget: {EAL.delete_asset(tp)}")
except Exception:
    import traceback
    out.append("EXCEPTION " + traceback.format_exc())
os.makedirs(SCRATCH, exist_ok=True)
open(os.path.join(SCRATCH, "dev_setup.txt"), "w").write("\n".join(out))
