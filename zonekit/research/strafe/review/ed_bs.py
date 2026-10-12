import unreal, os, json
out = {}
log = []
A = "/Game/_STALKER2/Animations/Player/AnimSequences/bh/"
BSS = {"walk": A + "stand/walk/Additive/BS_fp_bh_walk", "run": A + "stand/run/Additive/BS_fp_bh_run",
       "jog": A + "stand/Jog/BS_fp_bh_jog_01", "sprint": A + "stand/sprint/BS_fp_bh_sprint_01",
       "crouch": A + "crouch/move/Additive/BS_fp_bh_crouch", "lowcrouch": A + "lowcrouch/move/Additive/BS_fp_bh_lowcrouch"}
for k, p in BSS.items():
    bs = unreal.load_asset(p)
    if bs is None: log.append(f"missing {p}"); continue
    d = {"class": bs.get_class().get_name()}
    for prop in ("sample_data", "blend_parameters", "is_velocity", "additive_anim_type"):
        try:
            v = bs.get_editor_property(prop); d[prop] = str(v)[:3000]
        except Exception as e: d[prop] = f"ERR {e}"
    try:
        sd = bs.get_editor_property("sample_data")
        d["samples"] = []
        for s in sd:
            a = s.get_editor_property("animation"); sv = s.get_editor_property("sample_value")
            d["samples"].append([a.get_path_name() if a else None, sv.x, sv.y, s.get_editor_property("rate_scale")])
    except Exception as e: d["samples_err"] = str(e)
    try:
        bp = bs.get_editor_property("blend_parameters")
        d["params"] = [[str(x.get_editor_property("display_name")), x.get_editor_property("min"), x.get_editor_property("max"), x.get_editor_property("grid_num")] for x in bp]
    except Exception as e: d["params_err"] = str(e)
    out[k] = d
json.dump(out, open(os.path.join(SCRATCH, "rev_bs.json"), "w"), indent=1)
open(os.path.join(SCRATCH, "rev_bs_log.txt"), "w").write("\n".join(log))
