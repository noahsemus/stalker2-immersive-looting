-- ImmLootProbe: dev-box only (never shipped). Logs BP_ImmLootActor's counters and state to UE4SS.log whenever
-- they change, so one test run shows: was each pickup detected, did the reach play or why it was skipped
-- (SkipBits, see gen_actor_looting.py), was a copy spawned, was the hand recovered, and for loot windows:
-- open / kind (1 corpse, 2 stash) / weights and money read from the window / taken / reach after closing.
-- 1.0.1e: the probe no longer calls the player's interaction getters itself (the Blueprint stopped too); once a
-- second it dumps the plain properties of the looked-at body's DeadBody (search) and DeadBodyHoldComponent
-- (carry) components, to see why the carry is unavailable.
-- Install: <game>\Stalker2\Binaries\Win64\ue4ss\Mods\ImmLootProbe\scripts\main.lua + "ImmLootProbe : 1" in
-- mods.txt before UObjectCacheMod (ASCII, no BOM).

local TAG = "[ImmLootProbe] "
local FIELDS = { "NPickups", "NReaches", "NSkips", "SkipBits", "NFly", "NRecover", "Reaching", "ItemArmed",
                 "InvOpen", "LootKind", "Took", "NLootOpen", "NLootTook", "StartPW", "CurPW", "StartLW", "CurLW",
                 "StartMoney", "CurMoney", "GrabFwd", "GrabRight", "GrabUp", "FovS", "TanFOVv", "CamOff", "GrabBH", "SegStart", "ItemElev", "ItemDist", "ItemAzim", "SpX", "SpY", "SpZ", "ShX", "ShY", "ShZ", "ElX", "ElY", "ElZ", "GrabFwd", "TouchState", "TouchAdded", "Lootable", "KeysSynced", "NTouch", "LootReach", "LootPaused", "LootReverse", "TrBusy", "TrLH", "TrPos", "TouchHX", "TouchHY", "TouchHZ", "CamPitch", "TouchBin", "TapOff", "KeyDown", "KeyUp", "PlayRate" }
local actor = nil
local pawn = nil
local last_ticks, last_look = -1, ""
local last = {}
local ticks = 0
local last_dump = {}

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

-- UE4SS here has no property enumeration on classes (ForEachProperty is nil): read a list of likely names and
-- zero-argument functions instead; whatever answers is printed
local PROP_NAMES = { "bIsActive", "bAutoActivate", "bInteractionActive", "bActive", "bEnabled", "bInteractionEnabled",
    "bInteractable", "bCanInteract", "bShowInactive", "bForceShowInactive", "bSelfActivating", "bIsFocused", "bFocused",
    "bHovered", "bInRange", "bIsInRange", "bVisible", "bHidden", "bLocked", "bIsLocked", "bBlocked", "bIsBlocked",
    "InteractionDistance", "MinInteractionDistance", "MaxInteractionDistance", "MinDistance", "MaxDistance",
    "InteractionHeight", "InteractionPointHeightOffset", "InteractionSocketName", "InteractionType", "InteractType",
    "InteractLengthType", "Priority", "InteractionPriority", "HoldTime", "HoldDuration", "HoldProgress", "CurrentHoldTime",
    "HoldTimer", "bHoldStarted", "bIsHoldStarted", "bHoldInProgress", "bHoldEnabled", "bCanHold", "HoldPercent",
    "bRequiresEmptyHands", "bRequireEmptyHands", "bRequiresFreeHands", "bAllowWithWeapon", "bDisabledByWeapon",
    "InteractionTarget", "CurrentInteraction", "CurrentInteractable", "FocusedInteraction", "HoldTarget", "HoldComponent",
    "CurrentHold", "bInteractionsEnabled", "bInteractionsDisabled", "bInteractionInProgress", "TraceDistance",
    "InteractRadius", "InteractionRadius", "bIsHolding", "bHolding", "Interactables", "TargetComponent",
    "InteractableAnimCollection", "DeadBody", "Owner", "bWantsInitializeComponent", "bIsEditorOnly" }
local FUNC_NAMES = { "IsHoldStarted", "IsInteractionActive", "HasItemRequirement", "HasRelatedQuest", "IsActive",
    "CanInteract", "IsInteractable", "IsEnabled", "GetInteractLengthType", "IsInteractionInProgress", "IsHoldInProgress" }

local function dump_props(o)
    local parts = {}
    for _, n in ipairs(PROP_NAMES) do
        local ok, v = pcall(function() return o[n] end)
        if ok and v ~= nil then
            local t = type(v)
            if t == "boolean" or t == "number" or t == "string" then
                parts[#parts + 1] = n .. "=" .. tostring(v)
            elseif t == "userdata" then
                local ok3, s2 = pcall(function()
                    if v.IsValid and v:IsValid() and v.GetFName then return v:GetFName():ToString() end
                    if v.ToString then return v:ToString() end
                    return nil
                end)
                if ok3 and s2 and #s2 < 60 then parts[#parts + 1] = n .. "=" .. s2 end
            end
        end
    end
    for _, n in ipairs(FUNC_NAMES) do
        local ok, v = pcall(function() return o[n](o) end)
        if ok and v ~= nil and type(v) ~= "userdata" then parts[#parts + 1] = n .. "()=" .. tostring(v) end
    end
    if #parts == 0 then return "props: none answered" end
    return table.concat(parts, " ")
end

local function dump_component(label, owner, class_path)
    local ok, comp = pcall(function()
        local cls = StaticFindObject(class_path)
        if not cls or not cls:IsValid() then return nil end
        return owner:GetComponentByClass(cls)
    end)
    if not ok or not comp or not comp:IsValid() then
        log(label .. ": none (" .. tostring(ok) .. ")")
        return
    end
    local s = dump_props(comp)
    if last_dump[label] ~= s then
        last_dump[label] = s
        log(label .. " " .. obj_name(comp) .. ": " .. s)
    end
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
        for _, f in ipairs({ "Item", "ItemMesh", "ItemSkel", "Fly", "LootTarget", "LootComp", "LookActor", "LookComp", "TapComp", "PWText", "LWText", "InvView", "InvIMC" }) do
            local v = obj_name(actor[f])
            if last[f] ~= v then changed = true; last[f] = v end
            parts[#parts + 1] = f .. "=" .. v
        end
        if changed then log(table.concat(parts, " ")) end
        -- once a second: is the graph ticking, what we look at (our own trace), and the body's two interaction components
        if ticks % 5 == 0 then
            local look = "look=" .. obj_name(actor.LookActor) .. " comp=" .. obj_name(actor.LookComp)
            local t = tonumber(tostring(actor.NTicks)) or -1
            if look ~= last_look or ticks % 25 == 0 then
                log("ticks/s=" .. tostring(last_ticks >= 0 and (t - last_ticks) or "?") .. " " .. look)
                last_look = look
            end
            last_ticks = t
            local la = actor.LookActor
            if la and la:IsValid() and string.find(la:GetFullName(), "BP_AI_", 1, true) then
                dump_component("search", la, "/Script/Stalker2.DeadBody")
                dump_component("carry", la, "/Script/Stalker2.DeadBodyHoldComponent")
                if pawn and pawn:IsValid() then
                    local okp, pic = pcall(function() return pawn.PlayerInteractionComponent end)
                    if okp and pic and pic:IsValid() then
                        local sp = dump_props(pic)
                        if last_dump["pic"] ~= sp then last_dump["pic"] = sp; log("player interaction " .. sp) end
                    end
                end
            end
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
