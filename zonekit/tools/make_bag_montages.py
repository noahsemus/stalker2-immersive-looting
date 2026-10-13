"""Build k (tester: the bag animation as an arms-only layer over Skif's own posture): montages AM_ImmLoot_BagIn / Idle /
Out made from the copies AS_ImmLoot_BagIn / Idle / Out (make_bag_seq), to be played in the LeftHand AND RightHand
slots (left_hand_blend_mask / right_hand_blend_mask: shoulder to fingers, local space) at once, so the arms take the
game's bag animation relative to Skif's own upper body while the camera, the look and the legs stay the game's. A
dynamic montage has one slot, and two in the same group (DefaultGroup) stop each other, so these are montage assets with
two slot tracks, played with Montage_Play(bStopAllMontages false). Python cannot edit slot tracks: this script creates
them (DefaultSlot), the tester sets the tracks in the montage editor (zonekit/README.md, build k), then RUN AGAIN with
--arg CHECK=1 to verify the slots and set the blends. Run in the open editor with the harness ue_exec tool.
"""
import os
import unreal

EAL = unreal.EditorAssetLibrary
AL = unreal.AnimationLibrary
DIR = f"{MOD_ROOT}/Runtime"
out = []
# (montage, sequence, blend in, blend out): the game's own montage blends 0 / 0; Out blends out over 0.3 s into the
# hands-up / weapon draw that follows
SPEC = (("AM_ImmLoot_BagIn", "AS_ImmLoot_BagIn", 0.0, 0.05), ("AM_ImmLoot_BagIdle", "AS_ImmLoot_BagIdle", 0.05, 0.1),
        ("AM_ImmLoot_BagOut", "AS_ImmLoot_BagOut", 0.1, 0.25))
# build o: the Out's own blend-out starts at its end only (trigger 0; the default started it 0.3 s early and the arms
# carried the bag back up to the weapon); the actor holds it at 0.6 s and blends it out from there
TRIGGER = {"AM_ImmLoot_BagOut": 0.0}
try:
    for mname, sname, bi, bo in SPEC:
        path = f"{DIR}/{mname}"
        if not EAL.does_asset_exist(path):
            f = unreal.AnimMontageFactory()
            f.set_editor_property("source_animation", unreal.load_asset(f"{DIR}/{sname}"))
            unreal.AssetToolsHelpers.get_asset_tools().create_asset(mname, DIR, unreal.AnimMontage, f)
            out.append(f"created {path}")
        m = unreal.load_asset(path)
        a = m.get_editor_property("blend_in"); a.set_editor_property("blend_time", bi); m.set_editor_property("blend_in", a)
        b = m.get_editor_property("blend_out"); b.set_editor_property("blend_time", bo); m.set_editor_property("blend_out", b)
        if mname in TRIGGER:
            m.set_editor_property("blend_out_trigger_time", TRIGGER[mname])
        slots = [str(s) for s in AL.get_montage_slot_names(m)]
        ok = sorted(slots) == ["LeftHand", "RightHand"]
        out.append(f"{mname}: slots {slots} {'OK' if ok else '(needs LeftHand + RightHand)'}, length {m.get_play_length():.3f}, "
                   f"blend {m.get_editor_property('blend_in').get_editor_property('blend_time')} / "
                   f"{m.get_editor_property('blend_out').get_editor_property('blend_time')}, trigger {m.get_editor_property('blend_out_trigger_time')}, saved {EAL.save_loaded_asset(m, only_if_is_dirty=False)}")
except Exception:
    import traceback
    out.append("EXCEPTION " + traceback.format_exc())
os.makedirs(SCRATCH, exist_ok=True)
open(os.path.join(SCRATCH, "make_bag_montages.txt"), "w").write("\n".join(out))
