-- ImmLootProbe (dev-box only, never shipped): is BP_ImmLootActor alive and ticking, and what it sees / does.
local TAG = "[ImmLootProbe] "
local NUM = { "NTicks", "Enabled", "TouchDoors", "TouchState", "DoorTouch", "NDoor", "NPickups", "NReaches", "NSkips",
              "SkipBits", "Reaching", "LootReach", "LootPaused", "Lootable", "ItemArmed", "NTouch", "KeyDown", "KeyHeld", "InteractPressAt", "DoorPulling", "DoorYaw", "GameMontageAt", "ReachStart", "GrabBH", "PreReach", "PreReachAt", "Captured", "Handed", "NCapture", "NHandBack", "NAbort", "NHandUse", "NAbort2", "KeySeenAt", "NDoorCut", "TrPos", "TrLH", "TrBusy", "InvOpen", "InjRetries", "NInjRetry", "ReenableAt", "TouchOpenAt", "HandedAt", "UseWait", "UseWaitAt", "UseMode", "UsePausedAt", "NUsePause", "NUseResume", "NUseLate", "NUseNoTable", "NSkips", "LHOff", "LHOffAt", "NLHOff", "NLHOn", "TwinsPaused", "TwinHidden", "NTwinPause", "NTwinResume", "FBActive", "TraceX", "TraceY", "TraceZ", "GrabFwd", "GrabRight", "GrabUp", "ItemElev", "ItemDist", "ItemAzim", "SegStart", "TwinHidden2", "UseGrabbed", "NGhost", "GhostAt", "FlyStart", "PickUse", "NPickUse", "CamPitch", "GrabPitch", "AimCX", "AimCZ", "AimAX", "AimAY", "AimAZ", "AimT", "AimL", "AimShYaw0", "NYield", "NRecover", "BagMode", "NBag", "BagAt", "BackAt", "RetAt", "LootUse", "NLootUse", "LootWait", "LootFromGrab", "GameMontageKind", "GameMontageLen", "TouchStopped", "BagWeapon", "BagShowTick", "WeaponShowTick", "DoorWaiting", "PatMode", "NPat", "NPatCut", "TouchIsBody", "BodyMode", "StashMode", "EquipReplayAt", "NPressEdge", "PitchFixPos", "PitchFixAlive", "NPitchHeal", "BagVX", "BagVY", "BagVZ", "RHandVX", "RHandVY", "RHandVZ", "LHandVX", "LHandVY", "LHandVZ", "CamBoneVX", "CamBoneVY", "CamBoneVZ", "PitchFixReal", "BagIdleOn", "BagOutOn", "BagInOn", "BagAlive", "PickFix", "BagMode", "NBag", "InvOpen", "LootKind", "CamPitch", "GrabBH", "NPickView", "NPickViewCr", "NPatCancel", "NoteItem", "PullElong", "PullLongZ", "PullGripZ", "PullTurn", "FlyAttached", "FlyHeld", "IEFound", "NNotePDA", "TouchHandElev", "TouchHandAzim", "ViewPitch", "RigPitch", "RigRoll", "ItemElev", "ItemAzim", "TouchBin", "HoldStale", "NStaleHold", "NBodyNoInject", "TapCarry", "NTapCarry", "NTapCarryPick", "OpenAt", "LootWait", "HideItem", "DoorRadial", "DoorDecideT", "BagUsing", "BagServo", "BagLowerS", "BagLowerC", "BagServoSign", "BagBlock", "StanceBlk", "BagCamZ", "EquipType", "GrabPos", "NPickKn", "HasItemMH" }
local OBJS = {}   -- 2026-10-11: no object reads (a stale object read crashed loading a save inside UE4SS)
local actor, last, ticks, lastT = nil, {}, 0, -1
-- 2026-10-30 (two save loads crashed inside UE4SS right after a burst: during the load hitch the 50 ms loop queued dozens
-- of ExecuteInGameThread reads that ran back to back): no reads for 20 s after the actor is found, and a queued
-- callback that runs less than 40 ms after the previous one is dropped
local foundAt, lastRun = -1, -1
local function log(s) print(TAG .. s .. "\n") end
local function nm(o) if o and o:IsValid() then return o:GetFName():ToString() end return "none" end
local function find()
    local all = FindAllOf("BP_ImmLootActor_C")
    if not all then return nil end
    -- 2026-10-18: prefer an actor outside the main menu map (the menu's one stays valid after loading a save and
    -- never ticks: the whole run logged nothing)
    local fallback = nil
    for _, a in ipairs(all) do
        if a:IsValid() and not string.find(a:GetFullName(), "Default__", 1, true) then
            if not string.find(a:GetFullName(), "MainMenuMap", 1, true) then return a end
            fallback = fallback or a
        end
    end
    return fallback
end
LoopAsync(50, function()
    ExecuteInGameThread(function()
        ticks = ticks + 1
        local now = os.time()
        local wall = os.clock()
        if lastRun >= 0 and wall - lastRun < 0.04 then return end
        lastRun = wall
        if not actor or not actor:IsValid() then
            actor = nil
            if ticks % 40 == 0 then
                actor = find()
                if actor then last = {}; foundAt = now; log("actor found: " .. actor:GetFullName())
                elseif ticks % 200 == 0 then log("no BP_ImmLootActor in the world") end
            end
            return
        end
        if now - foundAt < 20 then return end
        local parts, changed = {}, false
        for _, f in ipairs(NUM) do
            local ok, v = pcall(function() return tostring(actor[f]) end)   -- (2026-10-12: reading an FString variable crashed the game on a save load)
            v = ok and v or "?"
            if f ~= "NTicks" and last[f] ~= v then changed = true; last[f] = v end
            parts[#parts + 1] = f .. "=" .. v
        end
        for _, f in ipairs(OBJS) do
            local ok, v = pcall(function() return nm(actor[f]) end)
            v = ok and v or "?"
            if last[f] ~= v then changed = true; last[f] = v end
            parts[#parts + 1] = f .. "=" .. v
        end
        -- (2026-10-11: the game-function calls here (IsLeftHandBusy, GetAnimInstance, IsVisible, FindFirstOf every 50 ms)
        --  crashed loading a save, inside UE4SS: removed; the probe only reads our actor's own variables)
        parts[#parts + 1] = string.format("t=%.2f", os.clock())
        if changed then log(table.concat(parts, " ")) end
        if ticks % 40 == 0 then
            local t = tonumber(tostring(actor.NTicks)) or -1
            log("ticks in 2 s: " .. tostring(lastT >= 0 and (t - lastT) or "?"))
            if lastT >= 0 and t == lastT then actor = nil; lastT = -1; return end   -- not ticking (the menu's): look again
            lastT = t
        end
    end)
    return false
end)
log("loaded")

-- (hold-to-use study 2026-10-11 removed: passive mode + state reads; a save-to-save load crashed with it on)
