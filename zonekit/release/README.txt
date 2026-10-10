Immersive Looting v0.1.0 (BETA) for S.T.A.L.K.E.R. 2: Heart of Chornobyl
When you pick something up, Skif reaches out with his left hand, takes it and pockets it,
instead of the item just vanishing. No UE4SS required.

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
  Delete the six files. Safe to remove at any time; nothing is written to your save.

WHAT IT DOES
  - Items lying in the world: press the interact key as usual. Skif's left hand reaches
    toward the item, takes it at its real size and carries it to his pocket. The item goes
    into your inventory immediately, exactly as in vanilla; only the look changes.
  - With empty hands the hand reaches to where the item is (far items slide the last bit
    into the hand, the arm only reaches so far). With a weapon in hand the left hand leaves
    the weapon, grabs, and goes back to it.
  - Corpses and stashes: after you close the loot window, if you took something, Skif does
    the same grab once.
  - No reach (vanilla pickup) while sprinting, aiming, reloading, in dialogue or cutscenes,
    or with a detector or binoculars in hand.
  - Artifacts and mutant parts keep their own vanilla animations.

BETA
  Tested with empty hands and with a pistol. Rifles and other weapons, the corpse / stash
  grab and gamepad have had little or no testing yet. Reports welcome.

COMPATIBILITY
  Overrides no game assets and changes no config files: everything is new content, so it
  should work alongside other mods. Mods that change the player's left-hand animations may
  look odd together with it.

Source and build instructions: https://github.com/noahsemus/stalker2-immersive-looting
