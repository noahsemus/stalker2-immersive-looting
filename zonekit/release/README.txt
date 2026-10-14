Immersive Looting v1.3.0 for S.T.A.L.K.E.R. 2: Heart of Chornobyl
When you pick something up, Skif reaches out with his left hand, takes it and pockets it,
instead of the item just vanishing. Looting a body or a stash, he reaches out and touches
it first. No UE4SS required.

WHAT IS IN THIS ZIP
  Six files, all required:
      zzz_ImmersiveLooting_20_P.pak / .ucas / .utoc
      ImmersiveLootingStalker2-Windows-NewContent.pak / .ucas / .utoc

INSTALL (Vortex)
  Drop the zip into Vortex, install, deploy. Done.

INSTALL (manual)
  Copy the six files into
      <game>\Stalker2\Content\Paks\~mods\
  (create the ~mods folder if it does not exist). Don't rename them.

UNINSTALL
  Delete the six files. Safe to remove at any time.

WHAT IT DOES
  - Items lying in the world: press the interact key as usual. Skif's left hand reaches
    toward the item, takes it at its real size and carries it to his pocket. The item goes
    into your inventory immediately, exactly as in vanilla; only the look changes.
  - With empty hands the hand reaches to where the item is (far items slide the last bit
    into the hand, the arm only reaches so far). With a weapon in hand the left hand leaves
    the weapon, grabs, and goes back to it.
  - Bodies and stashes: tap the interact key, Skif's hand reaches out toward the body or
    the stash, then the loot window opens. Close it and the hand comes back (onto the
    weapon, or to rest with empty hands). Holding the key picks up and carries a body
    exactly as in vanilla (no touch animation).
  - Holding the interact key on a food, drink or medicine item uses it as in vanilla: Skif
    first takes it with his hand, then plays the game's own use animation. Using an item
    from a body's or stash's loot window works the same way.
  - Doors: Skif pushes a door with his open hand or pulls it toward him, whichever way the door
    actually moves (open or close, from either side). Lockers, closets and cabinets too.
  - Bodies, both hands (MCM, off by default): Skif pats the body down with both hands,
    three pats in different places, while the loot window is open. A weapon in hand is
    put out of sight and drawn again after.
  - Optional Mod Configuration Menu (MCM) settings (the mod works without MCM installed):
      Looting bodies: Hand (default), Both hands, Backpack (Skif takes out his backpack,
        the game's own inventory animation), or Off (the loot window opens at once).
      Looting stashes: Hand (default), Backpack, or Off.
      Door animation: on (default) or off.
      Disable item fly animation (off by default): the item stays where it lies until
        the hand reaches it, then it is in the hand at once instead of flying into it.
  - No reach (vanilla pickup) while sprinting, aiming, reloading, in dialogue or cutscenes,
    or with a detector or binoculars in hand.
  - Artifacts and mutant parts keep their own vanilla animations.
  - Uses whatever key or gamepad button you have bound to interact.

COMPATIBILITY
  Overrides no game assets and changes no config files: everything is new content, so it
  should work alongside other mods. Tested together with Immersive Campfires, Immersive
  Dialogue and Player Gestures. Mods that change the player's left-hand animations may
  look odd together with it.

Source and build instructions: https://github.com/noahsemus/stalker2-immersive-looting

CHANGES
  1.3.0  Doors push or pull the way the door really moves: a door that swings toward you
         (lockers, closing a door opened away from you) is pulled, one that swings away is
         pushed. Closets and cabinets get the hand too. With a weapon out the door hand no
         longer goes through the gun: it leaves and comes back in an arc under the weapon,
         and the push is a real shove.
         MCM: the body and stash options are now two dropdowns (Hand, Both hands for
         bodies, Backpack, Off) instead of checkboxes; your MCM settings for this mod go
         back to their defaults once. New: "Both hands" pats the body down; "Disable item
         fly animation" (off by default).
         Picking something up with a weapon out: the hand goes straight back onto the grip
         (no more sliding past it and back), for pistols and long guns.
         Standing with empty hands, the sleeve no longer stretches at the edge of the screen
         when picking something up or touching a stash (with wide viewmodel FOV mods).
         Backpack looting: no more stuck backpack when looting quickly, the backpack shows
         on every body, and a quick tap on a body no longer picks it up.
  1.2.0  The hand no longer twists or flips when it goes back to the weapon after a body or
         stash: the reach is now made for each kind of weapon (rifles, SMGs, snipers and
         shotguns; pistols), the hand opens with the palm toward the body or stash, and it
         goes back to the grip around the weapon, not through it. Using an item from the
         loot window plays the grab-then-use, as when holding the interact key. New optional
         MCM setting "Bag for bodies and stashes" (off by default).
  1.1.1  Holding the interact key to use an item shows the hand grab again (1.1.0 sent the
         hand off screen, so the use looked vanilla).
  1.1.0  New empty-hands pickup: the hand reaches to where the item is, standing and
         crouched, closes around it and holds it in the palm. Pickups that played no
         animation now play it. Stashes (the blue boxes and others) open reliably, and
         the hand reaches toward the stash. Door push / pull. Hold the interact key to use
         an item, with the grab first. Optional MCM toggles for the body / stash touch and
         for doors.
         Known: strafing during a pickup still swings the hand (being worked on).
  1.0.1  Carrying bodies works again: holding the interact key on a body picks it up as in
         vanilla (1.0.0 turned every hold into a tap). The loot window on bodies and stashes
         opens sooner.
  1.0.0  First release.
