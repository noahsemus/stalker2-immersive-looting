# ImmersiveLooting — engineering log

What each kit check and each in-game test showed, newest at the bottom. Record dead ends here so they are never
retried. Plan: [../PLAN.md](../PLAN.md); reproducible edits: [../BUILD.md](../BUILD.md). Facts that hold for any
mod go to `harness/docs/` instead (promote them).

## 2026-10-09 — repo created from the harness
- `new_mod.ps1` created the repo, the kit plugin and the GitHub repo. GameFeatureData pending (tester picks the mod
  in the toolbar selector).
- Kit research (dumps, cfgs, uncooked assets read with a headless editor script, Nexus search, installed paks):
  `research/2026-10-09-pickup-and-left-hand-research.md`. Chosen route: NewContent host detects the pickup from the
  cached interaction target, plays a copy of the unused vanilla left-hand grab montage in `LeftHand`, flies a mesh
  copy of the item to `jnt_l_weapon`. See `../PLAN.md`.

## 2026-10-09 — builds 1-11 (one session)
- b1: nothing happened: `PC.GetInteractionTarget` is None while looking at a loose item. b2: `GetInteractedActor`
  first; pickups detected, reach + copy work.
- b2-b4 "item flies up-left off screen": first explained as the arms' FOV squeeze (`MF_Foreground_FOVCorrection`,
  real and in `harness/docs/animation.md`), but the main cause (b4-b7 probe traces) is that the arm bones do NOT follow
  the view pitch: looking 27 deg down, the reaching hand sat 53 cm above the view axis. b5/b6 tried the jnt_camera bone
  frame and the mesh frame (both wrong: CamOff 0, the arms do not pitch).
- "The animation plays twice" (b6): the vanilla grab dips the hand to the lower left before reaching; b7 removed the dip.
- The tester tests UNARMED: the rifle-solved arm on the empty-handed spine put the hand ~40 cm above the eye (b7 trace;
  the in-game rest hand matched `fp_bh_idle_stand` to 1 cm). b8: empty-hands grab re-solved on that spine; its copied
  "hand IK back on" notify made the hand jump centre-left (removed).
- b9: pitch table (8 segments of 2 s, -75..+30 deg) + item waits, is pulled into the hand at the grab frame. Tester:
  parent it to the hand (b9 shrank it to keep its screen size: wrong, dropped).
- b10/b11: target lower left. b10 landed at ~(55, +4, -8) view frame whatever the target: left-hand IK to the grip
  point; b11 switches it off at each segment start (HandIK notify, default = off) and aims at (40, -28, -16). Tester:
  "this is good" -> checkpoint-b11.
