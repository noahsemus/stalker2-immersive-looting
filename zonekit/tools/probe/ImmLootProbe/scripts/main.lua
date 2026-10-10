-- ImmLootProbe: dev-box only (never shipped). Logs BP_ImmLootActor's counters and state to UE4SS.log whenever
-- they change, so one test run shows: was each pickup detected, did the reach play or why it was skipped
-- (SkipBits, see gen_actor_looting.py), was a copy spawned, was the hand recovered, and for loot windows:
-- open / kind (1 corpse, 2 stash) / weights and money read from the window / taken / reach after closing.
-- Install: <game>\Stalker2\Binaries\Win64\ue4ss\Mods\ImmLootProbe\scripts\main.lua + "ImmLootProbe : 1" in
-- mods.txt before UObjectCacheMod (ASCII, no BOM).

local TAG = "[ImmLootProbe] "
local FIELDS = { "NPickups", "NReaches", "NSkips", "SkipBits", "NFly", "NRecover", "Reaching", "ItemArmed",
                 "InvOpen", "LootKind", "Took", "NLootOpen", "NLootTook", "StartPW", "CurPW", "StartLW", "CurLW",
                 "StartMoney", "CurMoney", "GrabFwd", "GrabRight", "GrabUp", "FovS", "TanFOVv", "CamOff", "GrabBH", "SegStart", "ItemElev", "ItemDist", "ItemAzim", "SpX", "SpY", "SpZ", "ShX", "ShY", "ShZ", "ElX", "ElY", "ElZ", "GrabFwd", "TouchState", "TouchAdded", "Lootable", "KeysSynced", "NTouch", "LootReach", "LootPaused", "LootReverse", "TrBusy", "TrLH", "TrPos", "TouchHX", "TouchHY", "TouchHZ", "PlayRate" }
local actor = nil
local pawn = nil
local last_ticks, last_look = -1, ""
local last = {}
local ticks = 0

local function log(s) print(TAG .. s .. "\n") end

local function find_actor()
    local all = FindAllOf("BP_ImmLootActor_C")
    if not all then return nil end
    for _, a in ipairs(all) do
        if a:IsValid() and not string.find(a:GetFullName(), "Default__", 1, true) then return a end
    end
    return nil
end

local function obj_name(o)
    if o and o:IsValid() then return o:GetFName():ToString() end
    return "none"
end

LoopAsync(200, function()
    ExecuteInGameThread(function()
        ticks = ticks + 1
        if not actor or not actor:IsValid() then
            actor = nil
            if ticks % 10 == 0 then            -- object scans only every 2 s while the actor is missing
                actor = find_actor()
                if actor then
                    last = {}
                    log("actor found: " .. actor:GetFullName())
                    pawn = FindFirstOf("BP_Stalker2Character_C")
                    if pawn and pawn:IsValid() then log("pawn: " .. pawn:GetFullName()) else pawn = nil end
                end
            end
            return
        end
        local parts, changed = {}, false
        for _, f in ipairs(FIELDS) do
            local v = tostring(actor[f])
            if last[f] ~= v then changed = true; last[f] = v end
            parts[#parts + 1] = f .. "=" .. v
        end
        for _, f in ipairs({ "Item", "ItemMesh", "ItemSkel", "Fly", "LootTarget", "PWText", "LWText", "InvView", "InvIMC" }) do
            local v = obj_name(actor[f])
            if last[f] ~= v then changed = true; last[f] = v end
            parts[#parts + 1] = f .. "=" .. v
        end
        if changed then log(table.concat(parts, " ")) end
        -- once a second: is the graph ticking, and what does the game say we look at
        if ticks % 5 == 0 then
            local look = ""
            if not (pawn and pawn:IsValid()) and ticks % 25 == 0 then
                pawn = FindFirstOf("BP_Stalker2Character_C")
                if pawn and pawn:IsValid() then log("pawn: " .. pawn:GetFullName()) else pawn = nil end
            end
            if pawn and pawn:IsValid() then
                local function q(fn)
                    local ok, r = pcall(function() return pawn[fn](pawn) end)
                    if not ok then return "err" end
                    if type(r) == "userdata" then return obj_name(r) end
                    return tostring(r)
                end
                look = "target=" .. q("GetInteractionTarget") .. " actor=" .. q("GetInteractedActor") ..
                       " comp=" .. q("GetInteractedComponent") .. " inProgress=" .. q("IsInteractionInProgress") ..
                       " backpack=" .. q("IsUsingBackpack")
            end
            local t = tonumber(tostring(actor.NTicks)) or -1
            if look ~= last_look or ticks % 25 == 0 then
                log("ticks/s=" .. tostring(last_ticks >= 0 and (t - last_ticks) or "?") .. " " .. look)
                last_look = look
            end
            last_ticks = t
        end
    end)
    return false
end)

log("loaded")

-- build 7: while a reach runs, the hand bone's offset from jnt_camera (mesh frame) every 50 ms
local t0 = nil
LoopAsync(50, function()
    ExecuteInGameThread(function()
        if not actor or not actor:IsValid() then return end
        local ok, reaching = pcall(function() return actor.Reaching end)
        if ok and reaching then
            local now = os.clock()
            t0 = t0 or now
            log(string.format("trace t=%.2f x=%s y=%s z=%s grip=%s/%s/%s pitch=%s", now - t0, tostring(actor.TraceX), tostring(actor.TraceY), tostring(actor.TraceZ), tostring(actor.WeapX), tostring(actor.WeapY), tostring(actor.WeapZ), tostring(actor.CamPitch)))
        else
            t0 = nil
        end
    end)
    return false
end)
