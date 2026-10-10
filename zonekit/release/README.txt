Immersive Looting v1.0.1 for S.T.A.L.K.E.R. 2: Heart of Chornobyl
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
  1.0.1  Carrying bodies works again: holding the interact key on a body picks it up as in
         vanilla (1.0.0 turned every hold into a tap). The loot window on bodies and stashes
         opens sooner.
  1.0.0  First release.
