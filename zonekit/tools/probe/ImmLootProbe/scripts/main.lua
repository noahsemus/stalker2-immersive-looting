-- ImmLootProbe: dev-box only (never shipped). Logs BP_ImmLootActor's counters and state to UE4SS.log whenever
-- they change, so one test run shows: was each pickup detected, did the reach play or why it was skipped
-- (SkipBits, see gen_actor_looting.py), was a copy spawned, was the hand recovered.
-- Install: <game>\Stalker2\Binaries\Win64\ue4ss\Mods\ImmLootProbe\scripts\main.lua + "ImmLootProbe : 1" in
-- mods.txt before UObjectCacheMod (ASCII, no BOM).

local TAG = "[ImmLootProbe] "
local FIELDS = { "NPickups", "NReaches", "NSkips", "SkipBits", "NFly", "NRecover", "Reaching", "ItemArmed" }
local actor = nil
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
        for _, f in ipairs({ "Item", "ItemMesh", "ItemSkel", "Fly" }) do
            local v = obj_name(actor[f])
            if last[f] ~= v then changed = true; last[f] = v end
            parts[#parts + 1] = f .. "=" .. v
        end
        if changed then log(table.concat(parts, " ")) end
    end)
    return false
end)

log("loaded")
