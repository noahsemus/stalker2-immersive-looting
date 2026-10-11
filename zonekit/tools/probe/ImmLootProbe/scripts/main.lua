-- ImmLootProbe (dev-box only, never shipped): is BP_ImmLootActor alive and ticking, and what it sees / does.
local TAG = "[ImmLootProbe] "
local NUM = { "NTicks", "Enabled", "TouchBodies", "TouchDoors", "TouchState", "DoorTouch", "NDoor", "NPickups", "NReaches", "NSkips",
              "SkipBits", "Reaching", "LootReach", "LootPaused", "Lootable", "ItemArmed", "NTouch", "KeyDown", "KeyHeld", "InteractPressAt", "DoorPulling", "DoorYaw", "UseHeld", "NUseHolds", "GameMontageAt", "ReachStart", "GrabBH", "PreReach", "PreReachAt", "Captured", "Handed", "NCapture", "NHandBack", "NAbort", "NHandUse", "NAbort2", "KeySeenAt", "NDoorCut", "TrPos", "InvOpen", "InjRetries", "NInjRetry", "ReenableAt", "TouchOpenAt", "OurHeldAt", "NHoldInject", "HandedAt", "UseWait", "UseWaitAt", "UseMode", "UsePausedAt", "NUsePause", "NUseResume", "NUseLate", "NUseNoTable", "NSkips", "LHOff", "LHOffAt", "NLHOff", "NLHOn", "TwinsPaused", "TwinHidden", "NTwinPause", "NTwinResume", "FBActive", "TraceX", "TraceY", "TraceZ", "GrabFwd", "GrabRight", "GrabUp", "ItemElev", "ItemDist", "ItemAzim", "SegStart", "NCand", "TwinHidden2", "UseGrabbed" }
local OBJS = { "LookActor", "Item", "LootObj", "LootComp", "GameMontage", "HeldUse", "GrabMontage", "Fly", "TouchAsset", "HideComp", "UseTap", "UseMont", "TwinComp", "TwinMont", "CandComp", "CandMont", "CandAnim", "CandComp2", "CandMont2", "TwinComp2" }
local actor, last, ticks, lastT = nil, {}, 0, -1
local function log(s) print(TAG .. s .. "\n") end
local function nm(o) if o and o:IsValid() then return o:GetFName():ToString() end return "none" end
local function find()
    local all = FindAllOf("BP_ImmLootActor_C")
    if not all then return nil end
    for _, a in ipairs(all) do
        if a:IsValid() and not string.find(a:GetFullName(), "Default__", 1, true) then return a end
    end
end
LoopAsync(50, function()
    ExecuteInGameThread(function()
        ticks = ticks + 1
        if not actor or not actor:IsValid() then
            actor = nil
            if ticks % 40 == 0 then
                actor = find()
                if actor then last = {}; log("actor found: " .. actor:GetFullName())
                elseif ticks % 200 == 0 then log("no BP_ImmLootActor in the world") end
            end
            return
        end
        local parts, changed = {}, false
        for _, f in ipairs(NUM) do
            local ok, v = pcall(function() return tostring(actor[f]) end)
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
            lastT = t
        end
    end)
    return false
end)
log("loaded")

-- (hold-to-use study 2026-10-11 removed: passive mode + state reads; a save-to-save load crashed with it on)
