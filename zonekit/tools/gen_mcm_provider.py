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
# 1.3.1 (tester: "there must be a way to remove dead settings"): MCM keeps every setting ever registered in the game
# save (MWS_MCM save data -> BP_MCM_Manager.AllSettings) and its menu lists all of a mod's saved settings
# (WBP_MCM_ModContainer: AllSettings filtered by ModID); there is no remove call. But it only lists mods added this
# session (ActiveModIDs, AddUniqueModID). So retiring settings = a new mod id: the old id's entries stay in the save,
# unlisted. The new id looks the same on screen (a trailing space). Next time: "Immersive Looting  " (two), etc.
MOD_ID = "Immersive Looting "
# 1.3.1 (tester: "consolidate some of the toggles in a dropdown"): two dropdowns and two toggles. MCM setting types
# (E_MCM_SettingType, from MCM_ModExample1): NewEnumerator0 = Bool, NewEnumerator7 = Combo Box (ComboBoxOptions =
# the labels, ComboBoxSelectedOption = the index, read back by GetModSetting's ComboBoxSelectedOption).
# (setting id, hover text, kind, provider / actor variable, combo labels, default). The combo ids are new names: a
# first build registered "Body looting" / "Stash looting" as Bool (the Type default lost on paste), and MCM keeps a
# saved setting's value.
# (setting id, hover text, kind, provider / actor variable, combo labels, default)
SETTINGS = [
    ("Looting bodies", "What Skif does when you loot a body. Hand: his left hand reaches out and touches it. Both hands: he pats it "
                     "down with both hands (a weapon in hand is put out of sight and drawn again after). Backpack: he swings his "
                     "backpack round, as when opening the inventory. Off: the loot window opens at once, as in vanilla.",
     "combo", "BodyMode", ["Hand", "Both hands", "Backpack", "Off"], 0),
    ("Looting stashes", "What Skif does when you open a stash, crate or bag. Hand: his left hand reaches out and touches it. "
                      "Backpack: he swings his backpack round, as when opening the inventory. Off: it opens at once, as in vanilla.",
     "combo", "StashMode", ["Hand", "Backpack", "Off"], 0),
    ("Door animation", "Skif's hand reaches for the door when you open, close or peek through it. Off: doors behave as in vanilla.",
     "bool", "TouchDoors", None, True),
    ("Hide items in the hand", "Skif's hand still reaches for loose items, but the item itself is not shown flying into his hand: "
                               "it goes straight into the inventory, as in vanilla.",
     "bool", "HideItem", None, False),
]
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
            # 1.3.1: the value goes where the editor writes it (after the pin type): placed right after PinName, an enum
            # pin's default (Type = NewEnumerator7, the combo box) was reset to NewEnumerator0 on paste (strings kept)
            v = values[m.group(1)]
            if re.search(r'(?<![A-Za-z])DefaultValue="[^"]*",', line):   # not AutogeneratedDefaultValue
                line = re.sub(r'(?<![A-Za-z])DefaultValue="[^"]*",', f'DefaultValue="{v}",', line, count=1)
            elif "bSerializeAsSinglePrecisionFloat=False," in line:
                line = line.replace("bSerializeAsSinglePrecisionFloat=False,", f'bSerializeAsSinglePrecisionFloat=False,DefaultValue="{v}",', 1)
            else:
                line = line.replace(f'PinName="{m.group(1)}",', f'PinName="{m.group(1)}",DefaultValue="{v}",', 1)
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


common = {"ModID": MOD_ID, "AuthorName": "geoffjeffrey", "Category": "General"}
TYPES = {"bool": "NewEnumerator0", "combo": "NewEnumerator7"}


def make_opts(x, y, labels):
    n = Node(g, BG + "K2Node_MakeArray", nm("K2Node_MakeArray"), x, y, "MCM: the dropdown's labels", [f"NumInputs={len(labels)}"])
    for k_, lab in enumerate(labels):
        n.pin(f"[{k_}]", "string", extra=f'DefaultValue="{lab}",')
    a = n.pin("Array", "string", out=True)
    a.container = "Array"
    return n


def opts_for(s, x, y):
    return (make_opts(x, y, s[4]) if s[2] == "combo" else make_str_array(x, y))["Array"]


lifted = []
# RegisterMCMSettings: each setting with its current value, then AddUniqueModID, Registered = true
ev_r = Lifted(EX, P + "K2Node_Event_6", "K2Node_Event_901", 0, 0)
lifted.append(ev_r)
prev, prev_pin = ev_r, "then"
for k, s in enumerate(SETTINGS):
    r = Lifted(EX, P + "K2Node_Message_55", f"K2Node_Message_{920 + k}", 700 + 300 * k, 0,
               defaults(dict(common, SettingID=s[0], SettingHoverText=s[1], Type=TYPES[s[2]])))
    lifted.append(r)
    link(prev, prev_pin, r, "execute")
    link(ev_r, "BPI MCM API", r, "self")
    if s[2] == "combo":
        xlink(r, "ComboBoxSelectedOption", self_get(s[3], "int", 650 + 300 * k, 500)[s[3]])
    else:
        xlink(r, "BoolValue", self_get(s[3], "bool", 650 + 300 * k, 500)[s[3]])
    xlink(r, "ComboBoxOptions", opts_for(s, 650 + 300 * k, 650))
    prev, prev_pin = r, "then"
add = Lifted(EX, P + "K2Node_Message_0", "K2Node_Message_902", 700 + 300 * len(SETTINGS), 0, defaults({"ModID": MOD_ID}))
lifted.append(add)
link(prev, prev_pin, add, "execute")
link(ev_r, "BPI MCM API", add, "self")
sr = self_set("Registered", "bool", 1000 + 300 * len(SETTINGS), 0, "registered (Apply may write now)", default="true")
xlink(add, "then", sr["execute"])

# RegisterMCMDefaultSettings
ev_d = Lifted(EX, P + "K2Node_Event_9", "K2Node_Event_902", 0, 1300)
lifted.append(ev_d)
prev, prev_pin = ev_d, "then"
for k, s in enumerate(SETTINGS):
    vals = dict(common, SettingID=s[0], SettingHoverText=s[1], Type=TYPES[s[2]])
    if s[2] == "combo":
        vals["ComboBoxSelectedOption"] = str(s[5])
    else:
        vals["BoolValue"] = "true" if s[5] else "false"
    d = Lifted(EX, P + "K2Node_Message_31", f"K2Node_Message_{930 + k}", 700 + 400 * k, 1300, defaults(vals))
    lifted.append(d)
    link(prev, prev_pin, d, "execute")
    link(ev_d, "BPI MCM API", d, "self")
    xlink(d, "ComboBoxOptions", opts_for(s, 350 + 400 * k, 1950))
    prev, prev_pin = d, "then"

# ApplyMCMSettings: (only once registered) read each setting, then write them into the running loot actor
ev_a = Lifted(EX, P + "K2Node_Event_7", "K2Node_Event_903", 0, 2600)
lifted.append(ev_a)
br = branch(350, 2600, "registered? (else an unknown setting reads false)")
xlink(ev_a, "then", br["execute"])
g.link(self_get("Registered", "bool", 150, 2800)["Registered"], br["Condition"])
prev_exec = br["then"]
for k, s in enumerate(SETTINGS):
    gt = Lifted(EX, P + "K2Node_Message_66", f"K2Node_Message_{940 + k}", 700, 2600 + 300 * k, defaults({"ModID": MOD_ID, "SettingID": s[0]}))
    lifted.append(gt)
    xlink(gt, "execute", prev_exec)
    link(ev_a, "BPI MCM API", gt, "self")
    st = self_set(s[3], "int" if s[2] == "combo" else "bool", 1250, 2600 + 300 * k, f"the setting {s[0]!r}")
    xlink(gt, "then", st["execute"])
    xlink(gt, "ComboBoxSelectedOption" if s[2] == "combo" else "BoolValue", st[s[3]])
    prev_exec = st["then"]
gaoc = exec_pins(Node(g, BG + "K2Node_CallFunction", nm("K2Node_CallFunction"), 1600, 2600, "the running loot actor (an exec node in UE5)",
            [f'FunctionReference=(MemberParent={GS},MemberName="GetActorOfClass")']))
gaoc.pin("self", "object", sub=GS, hidden=True, extra='DefaultObject="/Script/Engine.Default__GameplayStatics",' + TGT)
gaoc.pin("WorldContextObject", "object", sub=OBJ, hidden=True)
gaoc.pin("ActorClass", "class", sub=cls("/Script/Engine.Actor"), extra=f'DefaultObject="/ImmersiveLooting/Runtime/BP_ImmLootActor.BP_ImmLootActor_C",')
gaoc.pin("ReturnValue", "object", sub=ACT, out=True)
g.link(prev_exec, gaoc["execute"])
cast = exec_pins(Node(g, BG + "K2Node_DynamicCast", nm("K2Node_DynamicCast"), 2000, 2600, "", ["TargetType=" + ACT]))
cast.pin("CastFailed", "exec", out=True)
cast.pin("Object", "object", sub=OBJ)
cast.pin("AsBP Imm Loot Actor", "object", sub=ACT, out=True)
cast.pin("bSuccess", "bool", out=True)
g.link(gaoc["ReturnValue"], cast["Object"])
g.link(gaoc["then"], cast["execute"])
prev_exec = cast["then"]
for k, s in enumerate(SETTINGS):
    cat = "int" if s[2] == "combo" else "bool"
    sa = exec_pins(Node(g, BG + "K2Node_VariableSet", nm("K2Node_VariableSet"), 2400 + 300 * k, 2600, "into the loot actor" if k == 0 else "",
                        [f'VariableReference=(MemberParent={ACT},MemberName="{s[3]}")']))
    sa.pin(s[3], cat)
    sa.pin("Output_Get", cat, out=True)
    sa.pin("self", "object", sub=ACT, extra=TGT)
    g.link(prev_exec, sa["execute"])
    g.link(cast["AsBP Imm Loot Actor"], sa["self"])
    g.link(self_get(s[3], cat, 2200 + 300 * k, 2900)[s[3]], sa[s[3]])
    prev_exec = sa["then"]

out = []
for l_ in lifted:
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
