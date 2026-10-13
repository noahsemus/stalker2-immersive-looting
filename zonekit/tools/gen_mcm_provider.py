"""Generates the event graph of BP_ImmLootMCM, the MCM (Mod Configuration Menu 2.0) settings provider.

BP_ImmLootMCM implements /ModConfigurationMenu/BPI_MCM_SettingsProvider (Class Settings -> Interfaces; the stub plugin
from MCM's modder package must be in <kit>/Stalker2/Mods). MCM's manager finds it (GetAllActorsWithInterface) and calls:
  RegisterMCMSettings(api)        -> RegisterModSetting "Immersive Looting" / "Body and stash animation" and / "Door
                                     animation" (Bool, the current values; a value MCM already saved wins),
                                     AddUniqueModID, Registered = true
  RegisterMCMDefaultSettings(api) -> RegisterDefaultModSetting (Bool, true) for both
  ApplyMCMSettings(api)           -> (only once registered: another mod's click would read an unknown setting as false)
                                     GetModSetting x2 -> TouchBodies / TouchDoors -> into the running BP_ImmLootActor
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
SETTING2 = "Door animation"
HOVER2 = "Skif's hand reaches for the door when you open, close or peek through it. Off: doors behave as in vanilla."
SETTING3 = "Bag for bodies and stashes"
HOVER3 = "Skif swings his backpack round, as when opening the inventory, before the loot window of a body or stash opens. Off: his hand reaches out to it instead."
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
reg2 = Lifted(EX, P + "K2Node_Message_55", "K2Node_Message_905", 1000, 0, defaults(dict(common, SettingID=SETTING2, SettingHoverText=HOVER2)))
link(ev_r, "then", reg, "execute")
link(ev_r, "BPI MCM API", reg, "self")
link(reg, "then", reg2, "execute")
link(ev_r, "BPI MCM API", reg2, "self")
reg3 = Lifted(EX, P + "K2Node_Message_55", "K2Node_Message_908", 1150, 0, defaults(dict(common, SettingID=SETTING3, SettingHoverText=HOVER3)))
link(reg2, "then", reg3, "execute")
link(ev_r, "BPI MCM API", reg3, "self")
link(reg3, "then", add, "execute")
xlink(reg3, "BoolValue", self_get("BagLoot", "bool", 950, 500)["BagLoot"])
xlink(reg3, "ComboBoxOptions", make_str_array(950, 650)["Array"])
xlink(reg2, "BoolValue", self_get("TouchDoors", "bool", 650, 500)["TouchDoors"])
xlink(reg2, "ComboBoxOptions", make_str_array(650, 650)["Array"])
link(ev_r, "BPI MCM API", add, "self")
xlink(reg, "BoolValue", self_get("TouchBodies", "bool", 350, 500)["TouchBodies"])
xlink(reg, "ComboBoxOptions", make_str_array(350, 650)["Array"])
sr = self_set("Registered", "bool", 1750, 0, "registered (Apply may write now)", default="true")
xlink(add, "then", sr["execute"])

# RegisterMCMDefaultSettings
ev_d = Lifted(EX, P + "K2Node_Event_9", "K2Node_Event_902", 0, 1300)
dft = Lifted(EX, P + "K2Node_Message_31", "K2Node_Message_903", 700, 1300, defaults(dict(common, BoolValue="true")))
dft2 = Lifted(EX, P + "K2Node_Message_31", "K2Node_Message_906", 1100, 1300, defaults(dict(common, SettingID=SETTING2, SettingHoverText=HOVER2, BoolValue="true")))
link(ev_d, "then", dft, "execute")
link(ev_d, "BPI MCM API", dft, "self")
link(dft, "then", dft2, "execute")
link(ev_d, "BPI MCM API", dft2, "self")
xlink(dft2, "ComboBoxOptions", make_str_array(750, 1950)["Array"])
dft3 = Lifted(EX, P + "K2Node_Message_31", "K2Node_Message_909", 1500, 1300, defaults(dict(common, SettingID=SETTING3, SettingHoverText=HOVER3, BoolValue="false")))   # off by default (tester)
link(dft2, "then", dft3, "execute")
link(ev_d, "BPI MCM API", dft3, "self")
xlink(dft3, "ComboBoxOptions", make_str_array(1150, 1950)["Array"])
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
get2 = Lifted(EX, P + "K2Node_Message_66", "K2Node_Message_907", 1300, 2900, defaults({"ModID": MOD_ID, "SettingID": SETTING2}))
xlink(get2, "execute", st["then"])
link(ev_a, "BPI MCM API", get2, "self")
st2 = self_set("TouchDoors", "bool", 1700, 2900, "the door setting")
xlink(get2, "then", st2["execute"])
xlink(get2, "BoolValue", st2["TouchDoors"])
get3 = Lifted(EX, P + "K2Node_Message_66", "K2Node_Message_910", 1300, 3200, defaults({"ModID": MOD_ID, "SettingID": SETTING3}))
xlink(get3, "execute", st2["then"])
link(ev_a, "BPI MCM API", get3, "self")
st3 = self_set("BagLoot", "bool", 1700, 3200, "the bag setting")
xlink(get3, "then", st3["execute"])
xlink(get3, "BoolValue", st3["BagLoot"])
g.link(st3["then"], gaoc["execute"])
g.link(gaoc["then"], cast["execute"])
sa = exec_pins(Node(g, BG + "K2Node_VariableSet", nm("K2Node_VariableSet"), 2400, 2600, "into the loot actor",
                    [f'VariableReference=(MemberParent={ACT},MemberName="TouchBodies")']))
sa.pin("TouchBodies", "bool")
sa.pin("Output_Get", "bool", out=True)
sa.pin("self", "object", sub=ACT, extra=TGT)
g.link(cast["then"], sa["execute"])
g.link(cast["AsBP Imm Loot Actor"], sa["self"])
g.link(self_get("TouchBodies", "bool", 2200, 2900)["TouchBodies"], sa["TouchBodies"])
sa2 = exec_pins(Node(g, BG + "K2Node_VariableSet", nm("K2Node_VariableSet"), 2700, 2600, "",
                     [f'VariableReference=(MemberParent={ACT},MemberName="TouchDoors")']))
sa2.pin("TouchDoors", "bool")
sa2.pin("Output_Get", "bool", out=True)
sa2.pin("self", "object", sub=ACT, extra=TGT)
g.link(sa["then"], sa2["execute"])
g.link(cast["AsBP Imm Loot Actor"], sa2["self"])
g.link(self_get("TouchDoors", "bool", 2500, 2900)["TouchDoors"], sa2["TouchDoors"])
sa3 = exec_pins(Node(g, BG + "K2Node_VariableSet", nm("K2Node_VariableSet"), 3000, 2600, "",
                     [f'VariableReference=(MemberParent={ACT},MemberName="BagLoot")']))
sa3.pin("BagLoot", "bool")
sa3.pin("Output_Get", "bool", out=True)
sa3.pin("self", "object", sub=ACT, extra=TGT)
g.link(sa2["then"], sa3["execute"])
g.link(cast["AsBP Imm Loot Actor"], sa3["self"])
g.link(self_get("BagLoot", "bool", 2800, 2900)["BagLoot"], sa3["BagLoot"])

out = []
for l_ in (ev_r, reg, reg2, reg3, add, ev_d, dft, dft2, dft3, ev_a, get, get2, get3):
    out += l_.text()
out += g.text()
# the example's header pictures are not shipped (MCM showed white behind its white text): our own copies
# (duplicated from MCM_ModExample1, in the main plugin: harmless without MCM)
HEADERS = {"/MCM_ModExample1/MCM_Header09.MCM_Header09": "/ImmersiveLooting/Runtime/T_ImmLoot_MCMHeader.T_ImmLoot_MCMHeader",
           "/MCM_ModExample1/MCM_CatHeader12.MCM_CatHeader12": "/ImmersiveLooting/Runtime/T_ImmLoot_MCMCatHeader.T_ImmLoot_MCMCatHeader"}
for a_, b_ in HEADERS.items():
    out = [l_.replace(a_, b_) for l_ in out]
assert not any("/MCM_ModExample1/" in l_ for l_ in out)
write(sys.argv[2], out)
print("ok", len(g.nodes) + 13, "nodes")
