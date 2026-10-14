# Left-hand reach over a held weapon: what fixed the body / stash touch (v1.2.0), and how to reuse it

Written 2026-10-13 after the body / stash touch went from "twists almost 360 on the way back" (Nexus, Tim0st; the
tester for weeks) to "perfect". Builds r to za in `zonekit/README.md` have the blow-by-blow. Use this for any other
left-hand gesture played while a weapon is held: **doors are next**. The general rules are also in
`harness/docs/animation.md` ("Left-hand gestures over a held weapon").

## 1. What was actually wrong (measured, not guessed)
1. **The gesture was keyed on the wrong grip.** The old touches were copies of the game's unused AK grab
   (`MG_fp_ak74_weapon_grab`). Their left hand starts / ends on an AK foregrip: 9.7 cm and 88 deg (local) from every
   pistol's support grip, 18-64 deg from other long guns' grips (`arid.py`, `ptidle.py`).
2. **The vanilla grab rolls the wrist ~170 deg** while reaching (hand to the chest and back). Played in reverse it is
   the same roll: "very obviously twisting".
3. **Two blends could cross 180 deg and flip** (a local / component blend takes the short way; past 180 deg the short
   way switches sides from one frame to the next = a near full spin):
   - the LeftHand slot's blend-in from the live weapon pose into the gesture;
   - the weapon layer's left-hand IK (`TwoBoneIK_GSC` to the weapon mesh's own `jnt_l_hand` socket, alpha
     `HandsIKData.LeftHand` switched by `AnimNotify_HandIK`) blending between its grip and our keyed hand.
   The probe saw 71-125 deg turns in a single tick exactly inside those blend windows, while the animation's own
   steps stayed under 15 deg a tick.
4. **A straight return crossed the weapon.** The hand came back from the touch point in a straight line, arriving from
   above the grip: through the barrel.
5. **The family stance's grip is a few cm off each real grip** (rifle: ~3-4 cm right, 2.5 cm above). The hand went to
   the stance grip and the IK then dragged it to the real grip: "left and right before it settles", and clipping.

Things that did NOT help (don't repeat): later or shorter slot blend-outs alone (r); mirroring the vanilla reach for
the return (s); turning the IK on earlier while the palm was still turned out (t: made the flip worse); a left-arm
local-space additive in FullBody over the live grip (u: "jelly / alien", reverted).

## 2. The recipe that worked (`make_grab_seq.py build_touch_pistol(i, family)`)
- **One gesture set per weapon family, built on that family's own idle stance**, like the game's own left-hand
  gestures (`MG_fp_ar_flashlight`, `MG_fp_pt_flashlight`, NVG per family):
  `Ar` = `ar/common/stand/fp_ar_idle_stand` (every rifle / SMG / sniper / shotgun within ~0-64 deg; m10 108 deg),
  `Pt` = `pt/pm/Idle/AS_fp_pm_idle` (all pistols within 2.6 cm / 24 deg). Picked at run time with
  `Obj.GetMainHandEquipType` (`EMainHandEquipmentType`: 1 = PISTOL, 2 PRIMARY, 3 SECONDARY, ...).
- **Every left-arm track (the shoulder subtree) = that stance's frame 0**; only the upper arm and forearm are
  solved (two-bone, `reach` = 0.95 of the arm). Fingers / roll bones / shoulder never inherit vanilla motion.
- **Elbow pole**: the stance's own elbow direction at rest, turning toward a fixed out-left-down reference
  (`ELBOW_REF` component (-0.25, -0.82, -0.5)) as the hand goes out (the rest pole lined up with low-left reaches and
  flipped the elbow 30-35 deg a frame).
- **Hand**: follows the swung forearm (the stance's local hand rotation), then turns **one way round** (sign kept
  continuous frame to frame, `slerp_raw`; a per-frame shortest path jumped 177 deg in one frame) to the target
  orientation: palm toward the target tilted ~30 deg down (`TOUCH_PALM_DOWN`), fingers up and very slightly
  clockwise (`TOUCH_FINGERS_UP` (0, 0.1, 1); (0, -0.35, 1) looked like "breaking the wrist").
  The turn runs only **after the slot's blend-in** (frames 5-17; back 19-31), so the blend-in only ever spans
  grip-to-grip. **Half of the turn about the forearm axis goes to `jnt_l_fore_arm_roll`** (skin twist).
- **Fingers**: open and spread from `Dialog_animations/AS_fp_dialogue_bothhands_statement` frame 70 (searched every
  vanilla left hand with straight fingers: max index-pinky spread 49-56 deg; `spread.py`).
- **Path**: a quadratic curve. It starts / ends at the stance grip + `TOUCH_END_OFF` (1 fwd, 5 left, 4 down cm,
  component space: X forward, Y right, Z up) and passes through that + `TOUCH_EXIT` (2, -8, -6): the hand leaves and
  rejoins the grip from the left / below, never over the weapon, and the IK's last stretch comes from that side.
- **Timing (30 fps keys, played at 1.15)**: out 0-12, held 12-18 (the Blueprint pauses at 0.6 s while the loot
  window is open), back 18-36 (exact reverse), rest after. **IK off at 0.036 s over 0.06 s** (before the wrist
  turns), **IK on at 1.0 s (frame 30) over 0.35 s** (palm back, hand near the grip). Slot blend in 0.2 s, out 0.35 s.
- `left_hand_curve` 1 while the arm is out (rifles with an underbarrel idle replace the left arm otherwise).

## 3. How to check a change before the tester sees it
Offline (editor open, `ue_exec.py <script>`; results in `<TEMP>/stalker2-harness/*.txt`):
- `famscan.py`: per family, the largest per-frame step of the arm / hand / fingers, and how far frames 0-8 sit from
  several real weapons' grips (must stay well under 180 deg; ours: <= 60, m10 108).
- `path.py`: the hand's path relative to the start, frame by frame (must leave / return from the left, below).
- `touchscan.py` / `touchscan2.py`: per-frame rotation steps of the arm bones of any asset set.
- `arid.py` / `ptidle.py`: grip poses of every weapon idle against a reference. `spread.py`: finger spread search.
In game (probe; patch scripts `probe_hand_turn_logger.py` (build t) and `probe_grip_offset_logger.py` (build y),
removed from the release graph, re-anchor before reuse):
- `TwStep` / `TwMax` / `TwMaxPos`: how far the left hand turns per tick (camera-bone frame) and at which montage
  position: a spike = a flip, its position says which blend.
- `TwGF` / `TwGR` / `TwGU`: the left hand minus the held weapon's own `jnt_l_hand` socket, in view axes (cm):
  overshoots and which side the hand comes back from.
These two loggers found in two runs what four blind builds had not. Add them first next time.

## 4. Applying it to doors (next job)
The door push / pull assets (`AS_ImmLoot_DoorPush` / `DoorPull` armed, `...BH` empty hands) are still built by
`build_touch_one(mode="push"/"pull")` on the vanilla AK grab, with IK on at 1.27 / 1.4 s: the same causes 1-5 apply
(tester: "you push and then when the hand turns back to the weapon it clips into the weapon and moves down").
Rebuild them with the recipe above (family stance, solved arm, one-way wrist, spread palm for a push / a fist for a
pull, curved path that rejoins the grip from the left / below, IK off fast, on near the grip), with the door's own
stroke schedule (push: out, short forward stroke; pull: out to the handle, close the hand, draw back).
Separately the choice push vs pull is wrong today: it is "door open now = closing = pull, else push", which fails
for doors that open toward the player (lockers). See `zonekit/research/2026-10-13-door-research.md`.
