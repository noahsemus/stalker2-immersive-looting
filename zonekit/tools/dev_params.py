"""v1.3.2 n / o: the DEV panel's parameters (shared by dev_panel.py, which builds the widget paste, and gen_actor_dev.py,
which reads the sliders in game). Index = the slider / label name suffix (S_<i>, T_<i>).
(label, unit, min, max, step, default)
o: the live offsets are grids played in CutsceneSlot (no post-process layer: ImmersiveDialogue owns it), one table
at a time, so the arms only TURN (about the shoulders, roughly in view axes) and the hand turns in its own axes;
the grids are fine near 0 and coarser far out (2, 4.7, 8.2, 13, 19, 27.5, 39, 53, 73, 99, 134, 180 deg)."""
PARAMS = [
    ("Backpack standing: arms turn - pitch (both arms about the shoulders)", "deg", -180.0, 180.0, 1.0, 0.0),
    ("Backpack standing: arms turn - yaw", "deg", -180.0, 180.0, 1.0, 0.0),
    ("Backpack standing: arms turn - roll", "deg", -180.0, 180.0, 1.0, 0.0),
    ("Backpack crouched: arms turn - pitch (both arms about the shoulders)", "deg", -180.0, 180.0, 1.0, 0.0),
    ("Backpack crouched: arms turn - yaw", "deg", -180.0, 180.0, 1.0, 0.0),
    ("Backpack crouched: arms turn - roll", "deg", -180.0, 180.0, 1.0, 0.0),
    ("Crouched pickup: hand turn - roll (about the hand's length)", "deg", -180.0, 180.0, 1.0, 0.0),
    ("Crouched pickup: hand turn - pitch (wrist up / down)", "deg", -180.0, 180.0, 1.0, 0.0),
    ("Crouched pickup: hand turn - yaw (wrist side to side)", "deg", -180.0, 180.0, 1.0, 0.0),
    ("Crouched pickup: reach height (+ aims higher)", "deg", -45.0, 45.0, 1.0, 0.0),
    ("Time scale (slow motion to watch an animation)", "x", 0.05, 1.0, 0.05, 1.0),
]
HELP = ("IMMERSIVE LOOTING DEV    F7 show / hide    NUMPAD: 8 / 2 select a row,  4 / 6 lower / raise (hold = faster),  "
        "5 = that row's default    F8 = all defaults.  Values apply live while the backpack is out / during a crouched pickup.")
