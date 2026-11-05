"""v1.3.2 n: builds the DEV panel's widget tree in Python (transient objects) and exports it as Widget Designer paste
text: zonekit/paste/W_ImmLootDev.txt. The tester pastes it into Dev/W_ImmLootDev's Hierarchy (empty tree: the pasted
Canvas Panel becomes the root). Python cannot edit a widget tree, but the designer's clipboard format is the widgets'
T3D export, which an AssetExportTask with ObjectExporterT3D writes for a transient widget.
  Canvas Panel "Root" -> Border "Panel" (dark, top left, auto size) -> Size Box (560 wide) -> Vertical Box ->
  Text "T_Help", then per parameter (dev_params.PARAMS): Text "T_<i>" (the actor writes label, range, default, value)
  and Slider "S_<i>" (min / max / step / default).
Run in the open editor with the harness ue_exec tool.
"""
import os
import re
import sys
import unreal

sys.path.insert(0, os.path.join(REPO, "zonekit", "tools"))
import importlib
import dev_params
importlib.reload(dev_params)

out = []
pkg = None   # (no outer: the transient package)
objs = []


def mk(cls, name):
    o = unreal.new_object(cls, name=name)
    objs.append(o)
    return o


def small_font(tb, size):
    f = tb.get_editor_property("font")
    f.set_editor_property("size", size)
    tb.set_editor_property("font", f)


root = mk(unreal.CanvasPanel, "Root")
panel = mk(unreal.Border, "Panel")
panel.set_editor_property("brush_color", unreal.LinearColor(0.0, 0.0, 0.0, 0.72))
panel.set_editor_property("padding", unreal.Margin(12.0, 10.0, 12.0, 10.0))
cs = root.add_child_to_canvas(panel)
cs.set_auto_size(True)
cs.set_position(unreal.Vector2D(24.0, 24.0))
box = mk(unreal.SizeBox, "PanelWidth")
box.set_editor_property("width_override", 560.0)
box.set_editor_property("override_width_override", True)
panel.add_child(box)
vb = mk(unreal.VerticalBox, "Rows")
box.add_child(vb)
helpt = mk(unreal.TextBlock, "T_Help")
helpt.set_text(dev_params.HELP)
small_font(helpt, 10)
helpt.set_editor_property("auto_wrap_text", True)
vb.add_child_to_vertical_box(helpt).set_padding(unreal.Margin(0.0, 0.0, 0.0, 8.0))
for i, (label, unit, lo, hi, step, d) in enumerate(dev_params.PARAMS):
    t = mk(unreal.TextBlock, f"T_{i}")
    t.set_text(f"{label}   [{lo:g} .. {hi:g} {unit}, default {d:g}]")
    small_font(t, 9)
    vb.add_child_to_vertical_box(t)
    s = mk(unreal.Slider, f"S_{i}")
    s.set_editor_property("min_value", lo)
    s.set_editor_property("max_value", hi)
    s.set_editor_property("step_size", step)
    s.set_editor_property("value", d)
    s.set_editor_property("mouse_uses_step", True)
    vb.add_child_to_vertical_box(s).set_padding(unreal.Margin(0.0, 0.0, 0.0, 4.0))

text = []
for o in objs:
    dst = os.path.join(SCRATCH, f"dev_w_{o.get_name()}.t3d")
    t = unreal.AssetExportTask()
    t.object = o
    t.filename = dst
    t.automated = True
    t.prompt = False
    t.replace_identical = True
    t.exporter = unreal.ObjectExporterT3D()
    unreal.Exporter.run_asset_export_task(t)
    s_ = open(dst, encoding="utf-8", errors="replace").read()
    # paste wants names, not transient paths
    s_ = re.sub(r" ExportPath=\"[^\"]*\"", "", s_)
    if re.match(r"[TS]_\d+$", o.get_name()):   # the actor reads these by name: Blueprint variables of the panel
        s_ = s_.rstrip("\n")
        s_ = s_[: s_.rindex("End Object")] + "   bIsVariable=True\nEnd Object\n"
    text.append(s_.rstrip("\n"))
dst = os.path.join(REPO, "zonekit", "paste", "W_ImmLootDev.txt")
open(dst, "w", encoding="utf-8", newline="\n").write("\n".join(text) + "\n")
out.append(f"{len(objs)} widgets -> {dst}")
os.makedirs(SCRATCH, exist_ok=True)
open(os.path.join(SCRATCH, "dev_panel.txt"), "w").write("\n".join(out))
