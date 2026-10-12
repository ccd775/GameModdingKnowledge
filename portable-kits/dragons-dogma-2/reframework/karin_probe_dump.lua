-- Karin DD2 probe: dumps the player's runtime GameObject / component / mesh hierarchy.
-- Output: <game>/reframework/data/karin_probe/player_dump_<n>.json
-- Read-only: never changes game state.

local OUT_DIR = "karin_probe/"
local dump_count = 0
local auto_dumped = false
local last_status = "waiting for player"

local function safe(f, ...)
    local ok, r = pcall(f, ...)
    if ok then return r end
    return nil
end

local function tname(obj)
    if obj == nil then return nil end
    local td = safe(function() return obj:get_type_definition() end)
    if td == nil then return tostring(obj) end
    return td:get_full_name()
end

local function tostr(v)
    if v == nil then return nil end
    local t = type(v)
    if t == "string" or t == "number" or t == "boolean" then return v end
    local ok, s = pcall(function() return v:call("ToString()") end)
    if ok and s then return s end
    return tostring(v)
end

local function vec(v)
    if v == nil then return nil end
    local ok, r = pcall(function() return { v.x, v.y, v.z, v.w } end)
    if ok then return r end
    return tostring(v)
end

local function array_elems(arr)
    local out = {}
    if arr == nil then return out end
    local n = safe(function() return arr:call("get_Count") end) or safe(function() return arr:get_size() end) or 0
    for i = 0, n - 1 do
        local e = safe(function() return arr:call("get_Item", i) end) or safe(function() return arr:get_element(i) end)
        out[#out + 1] = e
    end
    return out
end

local function resource_path(holder)
    if holder == nil then return nil end
    return safe(function() return holder:call("get_ResourcePath") end)
end

local function dump_mesh(comp)
    local m = {}
    m.enabled = safe(function() return comp:call("get_Enabled") end)
    m.draw_default = safe(function() return comp:call("get_DrawDefault") end)
    m.mesh = resource_path(safe(function() return comp:call("getMesh") end))
    m.material_resource = resource_path(safe(function() return comp:call("get_Material") end))
    local n = safe(function() return comp:call("get_MaterialNum") end) or 0
    m.material_num = n
    m.materials = {}
    for i = 0, n - 1 do
        local name = safe(function() return comp:call("getMaterialName", i) end)
        local vis = safe(function() return comp:call("getMaterialsEnable", i) end)
        m.materials[#m.materials + 1] = { name = name, enabled = vis }
    end
    m.parts_num = safe(function() return comp:call("get_PartsNum") end)
    m.parts_enable = safe(function() return tostr(comp:call("get_PartsEnable")) end)
    return m
end

local function dump_components(go)
    local list = {}
    local comps = safe(function() return go:call("get_Components") end)
    local elems = {}
    if comps ~= nil then
        local ok, r = pcall(function() return comps:get_elements() end)
        if ok and r then elems = r else elems = array_elems(comps) end
    end
    for _, c in ipairs(elems) do
        local entry = { type = tname(c) }
        if entry.type == "via.render.Mesh" then
            entry.mesh = dump_mesh(c)
        elseif entry.type == "via.Transform" then
            entry.joint_count = safe(function() return c:call("get_JointCount") end)
            entry.parent_joint = safe(function() return c:call("get_ParentJointName") end)
            entry.local_pos = vec(safe(function() return c:call("get_LocalPosition") end))
            entry.local_scale = vec(safe(function() return c:call("get_LocalScale") end))
        elseif entry.type ~= nil and entry.type:find("Chain") then
            entry.chain = resource_path(safe(function() return c:call("get_ChainAsset") end))
            entry.enabled = safe(function() return c:call("get_Enabled") end)
        elseif entry.type ~= nil and entry.type:find("GpuCloth") then
            entry.enabled = safe(function() return c:call("get_Enabled") end)
        end
        list[#list + 1] = entry
    end
    return list
end

local function dump_go(go, depth, budget)
    if go == nil or depth > 12 or budget.n <= 0 then return nil end
    budget.n = budget.n - 1
    local node = {
        name = safe(function() return go:call("get_Name") end),
        draw_self = safe(function() return go:call("get_DrawSelf") end),
        update_self = safe(function() return go:call("get_UpdateSelf") end),
        components = dump_components(go),
        children = {},
    }
    local tr = safe(function() return go:call("get_Transform") end)
    local child = tr and safe(function() return tr:call("get_Child") end)
    while child ~= nil and budget.n > 0 do
        local cgo = safe(function() return child:call("get_GameObject") end)
        node.children[#node.children + 1] = dump_go(cgo, depth + 1, budget)
        child = safe(function() return child:call("get_Next") end)
    end
    return node
end

local function dump_joints(go)
    local tr = safe(function() return go:call("get_Transform") end)
    if tr == nil then return nil end
    local joints = safe(function() return tr:call("get_Joints") end)
    local out = {}
    local elems = {}
    if joints ~= nil then
        local ok, r = pcall(function() return joints:get_elements() end)
        if ok and r then elems = r else elems = array_elems(joints) end
    end
    for _, j in ipairs(elems) do
        out[#out + 1] = {
            name = safe(function() return j:call("get_Name") end),
            parent = safe(function() local p = j:call("get_Parent"); return p and p:call("get_Name") end),
            local_pos = vec(safe(function() return j:call("get_LocalPosition") end)),
            local_rot = vec(safe(function() return j:call("get_LocalRotation") end)),
            local_scale = vec(safe(function() return j:call("get_LocalScale") end)),
            base_pos = vec(safe(function() return j:call("get_BaseLocalPosition") end)),
        }
    end
    return out
end

-- Instance fields of obj (walks base classes up to via.Component / System.Object); values stringified.
local function dump_fields(obj)
    if obj == nil then return nil end
    local out = {}
    local td = safe(function() return obj:get_type_definition() end)
    while td ~= nil do
        local tn = td:get_full_name()
        if tn == "via.Component" or tn == "System.Object" then break end
        for _, f in ipairs(safe(function() return td:get_fields() end) or {}) do
            if not f:is_static() then
                out[f:get_name()] = tostr(safe(function() return f:get_data(obj) end))
            end
        end
        td = td:get_parent_type()
    end
    return out
end

local function dump_partswapper(ch)
    local ps = safe(function() return ch:call("get_HumanPartSwapper") end)
    if ps == nil then return nil end
    return {
        type = tname(ps),
        fields = dump_fields(ps),
        meta = dump_fields(safe(function() return ps:get_field("_Meta") end)),
    }
end

local function get_player()
    local cm = sdk.get_managed_singleton("app.CharacterManager")
    if cm == nil then return nil, "no app.CharacterManager" end
    local ch = safe(function() return cm:call("get_ManualPlayer") end)
    if ch == nil then return nil, "no ManualPlayer" end
    local go = safe(function() return ch:call("get_GameObject") end)
    return ch, go
end

local function do_dump(tag)
    local ch, go = get_player()
    if ch == nil then last_status = go or "no player"; return false end
    if go == nil then last_status = "player has no GameObject"; return false end
    dump_count = dump_count + 1
    local data = {
        tag = tag,
        time = os.date("%Y-%m-%d %H:%M:%S"),
        character_type = tname(ch),
        part_swapper = dump_partswapper(ch),
        tree = dump_go(go, 0, { n = 600 }),
        joints = dump_joints(go),
    }
    local path = OUT_DIR .. "player_dump_" .. tostring(dump_count) .. ".json"
    json.dump_file(path, data)
    last_status = "dumped " .. path
    log.info("[karin_probe] " .. last_status)
    return true
end

re.on_frame(function()
    if not auto_dumped then
        local ch, go = get_player()
        if ch ~= nil and go ~= nil then
            auto_dumped = do_dump("auto")
        end
    end
end)

re.on_draw_ui(function()
    if imgui.tree_node("Karin probe") then
        imgui.text("status: " .. tostring(last_status))
        if imgui.button("Dump player now") then do_dump("manual") end
        imgui.tree_pop()
    end
end)
