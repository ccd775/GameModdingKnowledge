-- Karin DD2 dev console (development only, never shipped).
-- Polls <game>/reframework/data/karin_dev/cmd.json = {"id": <any>, "lua": "<chunk>"}.
-- Runs each new id once on the game thread and writes karin_dev/result.json = {id, result|error}.
-- The chunk sees the global env plus K (helper table below); its return value must be JSON-serializable.

local CMD = "karin_dev/cmd.json"
local RES = "karin_dev/result.json"
local last_id = nil
local tick = 0

K = K or {}

function K.player()
    local cm = sdk.get_managed_singleton("app.CharacterManager")
    local ch = cm and cm:call("get_ManualPlayer")
    return ch, ch and ch:call("get_GameObject")
end

function K.tname(o)
    if o == nil then return nil end
    local ok, td = pcall(function() return o:get_type_definition() end)
    return ok and td and td:get_full_name() or tostring(o)
end

function K.str(v)
    local t = type(v)
    if v == nil or t == "string" or t == "number" or t == "boolean" then return v end
    local ok, s = pcall(function() return v:call("ToString()") end)
    if ok and s then return s end
    return tostring(v)
end

function K.comp(go, tn)
    return go and go:call("getComponent(System.Type)", sdk.typeof(tn))
end

function K.child(go, name)
    local tr = go:call("get_Transform")
    local c = tr:call("get_Child")
    while c do
        local g = c:call("get_GameObject")
        if g:call("get_Name") == name then return g end
        c = c:call("get_Next")
    end
    return nil
end

function K.children(go)
    local out = {}
    local c = go:call("get_Transform"):call("get_Child")
    while c do
        out[#out + 1] = c:call("get_GameObject")
        c = c:call("get_Next")
    end
    return out
end

function K.mesh_res(path)
    local r = sdk.create_resource("via.render.MeshResource", path)
    if r == nil then return nil end
    r:add_ref()
    return r:create_holder("via.render.MeshResourceHolder"):add_ref()
end

function K.mdf_res(path)
    local r = sdk.create_resource("via.render.MeshMaterialResource", path)
    if r == nil then return nil end
    r:add_ref()
    return r:create_holder("via.render.MeshMaterialResourceHolder"):add_ref()
end

local function run_cmd()
    local ok, c = pcall(json.load_file, CMD)
    if not ok or c == nil or c.id == nil or c.id == last_id then return end
    last_id = c.id
    local out = { id = c.id }
    local fn, err = load(c.lua or "", "karin_cmd", "t")
    if not fn then
        out.error = "compile: " .. tostring(err)
    else
        local ok2, r = pcall(fn)
        if ok2 then out.result = r else out.error = tostring(r) end
    end
    local ok3, e3 = pcall(json.dump_file, RES, out)
    if not ok3 then json.dump_file(RES, { id = c.id, error = "result not serializable: " .. tostring(e3) }) end
end

re.on_pre_application_entry("UpdateBehavior", function()
    tick = tick + 1
    if tick % 15 == 0 then
        local ok, e = pcall(run_cmd)
        if not ok then pcall(json.dump_file, RES, { id = last_id, error = "runner: " .. tostring(e) }) end
    end
end)

log.info("[karin_dev] console ready")
