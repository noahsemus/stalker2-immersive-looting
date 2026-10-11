-- ImmLootProbe (dev-box only, never shipped): is BP_ImmLootActor alive and ticking, and what it sees / does.
local TAG = "[ImmLootProbe] "
local NUM = { "NTicks", "Enabled", "TouchDoors", "TouchState", "DoorTouch", "NDoor", "NPickups", "NReaches", "NSkips",
              "SkipBits", "Reaching", "LootReach", "LootPaused", "Lootable", "ItemArmed", "NTouch", "KeyDown", "KeyHeld", "InteractPressAt", "DoorPulling", "DoorYaw", "LHMarked", "NLHMark", "NLHReturn" }
local OBJS = { "LookActor", "Item", "LootObj", "LootComp" }
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
        -- option B: the game's own view of the left hand and its action slot (the use animation plays there)
        local okb, busy = pcall(function() return tostring(actor.Player:IsLeftHandBusy()) end)
        local oka, act = pcall(function()
            return tostring(actor.Player.Mesh:GetAnimInstance():IsSlotActive(FName("MainActionSlot")))
        end)
        local g = "LHBusy=" .. (okb and busy or "?") .. " ActionSlot=" .. (oka and act or "?")
        if last["_g"] ~= g then changed = true; last["_g"] = g end
        parts[#parts + 1] = g
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
