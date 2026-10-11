"""Generates the event graph of BP_ImmLootMCM, the MCM (Mod Configuration Menu 2.0) settings provider.

BP_ImmLootMCM implements /ModConfigurationMenu/BPI_MCM_SettingsProvider (Class Settings -> Interfaces; the stub plugin
from MCM's modder package must be in <kit>/Stalker2/Mods). MCM's manager finds it (GetAllActorsWithInterface) and calls:
  RegisterMCMSettings(api)        -> RegisterModSetting "Immersive Looting" / "Body and stash animation" (Bool, the
                                     current value; a value MCM already saved wins), AddUniqueModID, Registered = true
  RegisterMCMDefaultSettings(api) -> RegisterDefaultModSetting (Bool, true)
  ApplyMCMSettings(api)           -> (only once registered: another mod's click would read an unknown setting as false)
                                     GetModSetting -> TouchBodies -> into the running BP_ImmLootActor
The MCM nodes (interface events, the (Message) calls) are lifted from MCM's own example (MCM_ModExample1, exported with
harness/tools/editor/export_t3d.py): their pin formats must match the interface exactly.
The provider is spawned by BP_ImmLootActor through a soft class path, so the main mod never imports MCM and loads
without it.
Usage: python gen_mcm_provider.py <example.t3d> <out.txt>
"""
import os
import re
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "harness", "tools", "t3d"))
from bp_t3d import cls, TGT, write
from bp_graph import Graph, Node
from t3d_lift import Lifted, link

EX = sys.argv[1]
BG = "/Script/BlueprintGraph."
SELF = "\"/Script/Engine.BlueprintGeneratedClass'/ImmersiveLooting/Runtime/BP_ImmLootMCM.BP_ImmLootMCM_C'\""
ACT = "\"/Script/Engine.BlueprintGeneratedClass'/ImmersiveLooting/Runtime/BP_ImmLootActor.BP_ImmLootActor_C'\""
OBJ = cls("/Script/CoreUObject.Object")
GS = cls("/Script/Engine.GameplayStatics")
KSL = cls("/Script/Engine.KismetSystemLibrary")
MOD_ID = "Immersive Looting"
SETTING = "Body and stash animation"
HOVER = "Skif's hand touches bodies, crates and bags before the loot window opens. Off: they open at once, as in vanilla. Loose items keep their animation."
P = "BP_MCM_ModExample1.BP_MCM_ModExample1:EventGraph."

g = Graph()
seq = [0]


def nm(kind):
    seq[0] += 1
    return f"{kind}_{900 + seq[0]}"


def defaults(values):
    def f(line):
        m = re.search(r'PinName="([^"]+)"', line) if "CustomProperties Pin" in line else None
        if m and m.group(1) in values:
            line = re.sub(r'DefaultValue="[^"]*",', "", line)
            line = line.replace(f'PinName="{m.group(1)}",', f'PinName="{m.group(1)}",DefaultValue="{values[m.group(1)]}",', 1)
        return line
    return f


class _N:
    def __init__(self, name, pin_ids):
        self.name, self.pin_ids = name, pin_ids


class _P:
    def __init__(self, node_name, pid):
        self.node, self.id = _N(node_name, {}), pid


def xlink(lifted, lpin, gpin):
    """Link a lifted node's pin with a generated (bp_graph) pin, written on both ends."""
    gpin.links.append(_P(lifted.name, lifted.pin_ids[lpin]))
    lifted.links.setdefault(lpin, []).append((_N(gpin.node.name, {gpin.name: gpin.id}), gpin.name))


def exec_pins(n):
    n.pin("execute", "exec")
    n.pin("then", "exec", out=True)
    return n


def self_get(var, cat, x, y):
    n = Node(g, BG + "K2Node_VariableGet", nm("K2Node_VariableGet"), x, y, "", [f'VariableReference=(MemberName="{var}",bSelfContext=True)'])
    n.pin(var, cat, out=True)
    n.pin("self", "object", sub=SELF, hidden=True, extra=TGT)
    return n


def self_set(var, cat, x, y, comment="", default=None):
    n = exec_pins(Node(g, BG + "K2Node_VariableSet", nm("K2Node_VariableSet"), x, y, comment, [f'VariableReference=(MemberName="{var}",bSelfContext=True)']))
    n.pin(var, cat, extra=f'DefaultValue="{default}",' if default is not None else "")
    n.pin("Output_Get", cat, out=True)
    n.pin("self", "object", sub=SELF, hidden=True, extra=TGT)
    return n


def branch(x, y, comment):
    n = exec_pins(Node(g, BG + "K2Node_IfThenElse", nm("K2Node_IfThenElse"), x, y, comment))
    n.pin("Condition", "bool", extra='DefaultValue="true",')
    n.pin("else", "exec", out=True)
    return n


def make_str_array(x, y):
    n = Node(g, BG + "K2Node_MakeArray", nm("K2Node_MakeArray"), x, y, "MCM: always one empty string", ["NumInputs=1"])
    n.pin("[0]", "string", extra='DefaultValue="",')
    a = n.pin("Array", "string", out=True)
    a.container = "Array"
    return n


common = {"ModID": MOD_ID, "SettingID": SETTING, "SettingHoverText": HOVER, "AuthorName": "geoffjeffrey",
          "Category": "General", "Type": "NewEnumerator0"}

# RegisterMCMSettings
ev_r = Lifted(EX, P + "K2Node_Event_6", "K2Node_Event_901", 0, 0)
reg = Lifted(EX, P + "K2Node_Message_55", "K2Node_Message_901", 700, 0, defaults(common))
add = Lifted(EX, P + "K2Node_Message_0", "K2Node_Message_902", 1300, 0, defaults({"ModID": MOD_ID}))
link(ev_r, "then", reg, "execute")
link(ev_r, "BPI MCM API", reg, "self")
link(reg, "then", add, "execute")
link(ev_r, "BPI MCM API", add, "self")
xlink(reg, "BoolValue", self_get("TouchBodies", "bool", 350, 500)["TouchBodies"])
xlink(reg, "ComboBoxOptions", make_str_array(350, 650)["Array"])
sr = self_set("Registered", "bool", 1750, 0, "registered (Apply may write now)", default="true")
xlink(add, "then", sr["execute"])

# RegisterMCMDefaultSettings
ev_d = Lifted(EX, P + "K2Node_Event_9", "K2Node_Event_902", 0, 1300)
dft = Lifted(EX, P + "K2Node_Message_31", "K2Node_Message_903", 700, 1300, defaults(dict(common, BoolValue="true")))
link(ev_d, "then", dft, "execute")
link(ev_d, "BPI MCM API", dft, "self")
for l_ in list(dft.lines):
    pass
xlink(dft, "ComboBoxOptions", make_str_array(350, 1950)["Array"])

# ApplyMCMSettings
ev_a = Lifted(EX, P + "K2Node_Event_7", "K2Node_Event_903", 0, 2600)
br = branch(350, 2600, "registered? (else an unknown setting reads false)")
xlink(ev_a, "then", br["execute"])
g.link(self_get("Registered", "bool", 150, 2800)["Registered"], br["Condition"])
get = Lifted(EX, P + "K2Node_Message_66", "K2Node_Message_904", 700, 2600, defaults({"ModID": MOD_ID, "SettingID": SETTING}))
xlink(get, "execute", br["then"])
link(ev_a, "BPI MCM API", get, "self")
st = self_set("TouchBodies", "bool", 1250, 2600, "the setting")
xlink(get, "then", st["execute"])
xlink(get, "BoolValue", st["TouchBodies"])
gaoc = exec_pins(Node(g, BG + "K2Node_CallFunction", nm("K2Node_CallFunction"), 1600, 2600, "the running loot actor (an exec node in UE5)",
            [f'FunctionReference=(MemberParent={GS},MemberName="GetActorOfClass")']))
gaoc.pin("self", "object", sub=GS, hidden=True, extra='DefaultObject="/Script/Engine.Default__GameplayStatics",' + TGT)
gaoc.pin("WorldContextObject", "object", sub=OBJ, hidden=True)
gaoc.pin("ActorClass", "class", sub=cls("/Script/Engine.Actor"), extra=f'DefaultObject="/ImmersiveLooting/Runtime/BP_ImmLootActor.BP_ImmLootActor_C",')
gaoc.pin("ReturnValue", "object", sub=ACT, out=True)
cast = exec_pins(Node(g, BG + "K2Node_DynamicCast", nm("K2Node_DynamicCast"), 2000, 2600, "", ["TargetType=" + ACT]))
cast.pin("CastFailed", "exec", out=True)
cast.pin("Object", "object", sub=OBJ)
cast.pin("AsBP Imm Loot Actor", "object", sub=ACT, out=True)
cast.pin("bSuccess", "bool", out=True)
g.link(gaoc["ReturnValue"], cast["Object"])
g.link(st["then"], gaoc["execute"])
g.link(gaoc["then"], cast["execute"])
sa = exec_pins(Node(g, BG + "K2Node_VariableSet", nm("K2Node_VariableSet"), 2400, 2600, "into the loot actor",
                    [f'VariableReference=(MemberParent={ACT},MemberName="TouchBodies")']))
sa.pin("TouchBodies", "bool")
sa.pin("Output_Get", "bool", out=True)
sa.pin("self", "object", sub=ACT, extra=TGT)
g.link(cast["then"], sa["execute"])
g.link(cast["AsBP Imm Loot Actor"], sa["self"])
g.link(self_get("TouchBodies", "bool", 2200, 2900)["TouchBodies"], sa["TouchBodies"])

out = []
for l_ in (ev_r, reg, add, ev_d, dft, ev_a, get):
    out += l_.text()
out += g.text()
write(sys.argv[2], out)
print("ok", len(g.nodes) + 7, "nodes")
