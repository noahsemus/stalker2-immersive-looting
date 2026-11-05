"""v1.3.2 n: the AnimGraph of Dev/ABP_ImmLootDevPose (DEV only, post-process anim BP) as paste text.

  (Input Pose, added by hand) -> Local To Component -> Transform (Modify) Bone jnt_l_shoulder (rotation ArmRot,
  translation ArmPos, alpha ArmAlpha) -> the same on jnt_r_shoulder -> jnt_l_hand (rotation HandRot, alpha HandAlpha)
  -> Component To Local -> (Output Pose, wired by hand).
Rotation and translation are ADDED in WORLD space: the actor turns the panel's view-axis values (forward / right / up
of the camera) into world space, so a slider moves the arms the same way whatever the view.
Node templates are lifted from the game's AnimBP_Player_TwoHandedItem export (its WeaponLayer graph); the property
bindings are pointed at our variables.
Usage: python gen_abp_devpose.py <AnimBP_Player_TwoHandedItem.t3d> <out.txt>
"""
import os
import re
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "harness", "tools", "t3d"))
from t3d_lift import Lifted, link
from bp_t3d import write

EX = sys.argv[1]
P = "AnimBP_Player_TwoHandedItem.AnimBP_Player_TwoHandedItem:WeaponLayer."


def no_bindings(l):
    return "" if l.strip().startswith("PropertyBindings=") else l


def modify(bone, rot_var, pos_var, alpha_var):
    def f(l):
        s = l.strip()
        if s.startswith("PropertyBindings="):
            for prop, var in (("Translation", pos_var), ("Rotation", rot_var), ("Alpha", alpha_var)):
                if var is None:
                    # drop that binding: the whole ("Prop", (...)) entry
                    l = re.sub(r'\("%s", \(.*?bIsBound=True\)\),?' % prop, "", l)
                else:
                    l = re.sub(r'(PropertyName="%s",PathAsText=")[^"]*(",PropertyPath=\()[^)]*(\))' % prop, r'\g<1>%s\g<2>"%s"\g<3>' % (var, var), l)
            l = l.replace("),)", "))").replace("(,", "(")
            return l
        if s.startswith("Node=("):
            return re.sub(r"Node=\(.*\)", f'Node=(BoneToModify=(BoneName="{bone}"),TranslationMode={"BMM_Additive" if pos_var else "BMM_Ignore"},'
                                          f'RotationMode=BMM_Additive,TranslationSpace=BCS_WorldSpace,RotationSpace=BCS_WorldSpace,Alpha=0.000000)', l)
        if s.startswith("ErrorType=") or s.startswith("ErrorMsg="):
            return ""
        return l
    return f


l2c = Lifted(EX, P + "AnimGraphNode_LocalToComponentSpace_1", "AnimGraphNode_LocalToComponentSpace_900", 0, 0, no_bindings)
ml = Lifted(EX, P + "AnimGraphNode_ModifyBone_1", "AnimGraphNode_ModifyBone_900", 300, 0, modify("jnt_l_shoulder", "ArmRot", "ArmPos", "ArmAlpha"))
mr = Lifted(EX, P + "AnimGraphNode_ModifyBone_1", "AnimGraphNode_ModifyBone_901", 700, 0, modify("jnt_r_shoulder", "ArmRot", "ArmPos", "ArmAlpha"))
mh = Lifted(EX, P + "AnimGraphNode_ModifyBone_1", "AnimGraphNode_ModifyBone_902", 1100, 0, modify("jnt_l_hand", "HandRot", None, "HandAlpha"))
c2l = Lifted(EX, P + "AnimGraphNode_ComponentToLocalSpace_1", "AnimGraphNode_ComponentToLocalSpace_900", 1500, 0, no_bindings)
link(l2c, "ComponentPose", ml, "ComponentPose")
link(ml, "Pose", mr, "ComponentPose")
link(mr, "Pose", mh, "ComponentPose")
link(mh, "Pose", c2l, "ComponentPose")
out = []
for n in (l2c, ml, mr, mh, c2l):
    out += [l for l in n.text() if l != ""]
out += ['Begin Object Class=/Script/UnrealEd.EdGraphNode_Comment Name="EdGraphNode_Comment_900"',
        "   NodePosX=-100", "   NodePosY=-150", "   NodeWidth=1900", "   NodeHeight=500",
        '   NodeComment="DEV: arms and left hand turned / moved live (world space; the actor sets the values from the panel)"', "End Object"]
write(sys.argv[2], out)
print("ok", sorted(ml.pin_ids))
