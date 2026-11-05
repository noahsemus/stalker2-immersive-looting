"""Read-only (open editor, ue_exec): knife / bolt / rifle stance poses for the knife-bolt study -> SCRATCH/handdump.json
(same format as bagdump.json)."""
import os, json, time, unreal
exec(open(os.path.join(ARGS["HERE"], "dump_bag.py")).read().split("SEQS = {")[0])
A = "/Game/_STALKER2/Animations/Player/AnimSequences/"
SEQS = {
    "idle": (A + "bh/stand/fp_bh_idle_stand", [0], []),
    "ar_idle": (A + "ar/common/stand/fp_ar_idle_stand", [0], []),
    "ar_look": (A + "ar/common/stand/fp_ar_stand_lookvertical", None, [0, 15]),
    "ar_crouch": (A + "ar/common/crouch/fp_ar_idle_crouch", [0], []),
    "ar_lowcrouch": (A + "ar/common/lowcrouch/fp_ar_idle_lowcrouch", [0], []),
    "gr_lowcrouch": (A + "grenades/common/lowcrouch/AS_fp_grenades_idle_lowcrouch", [0], []),
    "knife_idle": (A + "knifes/Idle/AS_fp_knife_idle", [0], []),
    "knife_idle_add": (A + "knifes/Additive/AS_fp_knife_idle_add", [0], [0]),
    "bolt_idle": (A + "bolt/idle/AS_fp_bolt_idle", [0], []),
    "bolt_idle_pose": (A + "bolt/idle/AS_fp_bolt_idle_pose", [0], []),
    "bolt_idle_add": (A + "bolt/idle/AS_fp_bolt_idle_add", [0], [0]),
    "pm_idle": (A + "pt/pm/Idle/AS_fp_pm_idle", [0], []),
}
src = open(os.path.join(ARGS["HERE"], "dump_bag.py")).read()
body = src.split("def opts(full, raw):")[1]
exec("def opts(full, raw):" + body.replace('"bagdump.json"', '"handdump.json"').replace('"bagdump_log.txt"', '"handdump_log.txt"'))
