-- Dev-only probe (never shipped): does the game's own body-swap pipeline run for the player while a save loads, and
-- what does it hand over? Logs every app.PartSwapper body-mesh / body-skin loaded callback with the swapper's object
-- and, per instantiated part, the part object's name, its mesh resource and its material resource.
local TAG = "[karin_pipeline] "
local function log_info(s) log.info(TAG .. s) end

local function part_info(go)
    if go == nil then return "nil" end
    local ok, s = pcall(function()
        local name = go:call("get_Name")
        local m = go:call("getComponent(System.Type)", sdk.typeof("via.render.Mesh"))
        local mp = m and m:call("getMesh") and m:call("getMesh"):call("get_ResourcePath") or "-"
        local mt = m and m:call("get_Material") and m:call("get_Material"):call("get_ResourcePath") or "-"
        return string.format("%s mesh=%s mdf=%s", name, mp, mt)
    end)
    return ok and s or ("?" .. tostring(s))
end

local function obj_fields(o)
    if o == nil then return "nil" end
    local out = {}
    local ok = pcall(function()
        local t = o:get_type_definition()
        out[#out + 1] = t:get_full_name() .. "{"
        while t and t:get_full_name() ~= "System.Object" and t:get_full_name() ~= "via.Component" do
            for _, f in ipairs(t:get_fields()) do
                if not f:is_static() then
                    local okv, v = pcall(o.get_field, o, f:get_name())
                    local vs = tostring(v)
                    if okv and type(v) == "userdata" then
                        local okp, pth = pcall(function() return v:call("get_ResourcePath") end)
                        vs = (okp and pth) and ("res:" .. pth) or v:get_type_definition():get_full_name()
                    end
                    out[#out + 1] = f:get_name() .. "=" .. vs
                end
            end
            t = t:get_parent_type()
        end
        out[#out + 1] = "}"
    end)
    return table.concat(out, " ")
end

local function go_tree(go, depth)
    if go == nil or depth > 3 then return "" end
    local out = {}
    pcall(function()
        local comps = {}
        for _, c in ipairs(go:call("get_Components"):get_elements()) do
            local tn = c:get_type_definition():get_full_name()
            local extra = ""
            if tn == "via.render.Mesh" then
                local m = c:call("getMesh"); local mt = c:call("get_Material")
                extra = "(" .. tostring(m and m:call("get_ResourcePath")) .. "," .. tostring(mt and mt:call("get_ResourcePath")) .. ")"
            end
            comps[#comps + 1] = tn .. extra
        end
        out[#out + 1] = string.rep(">", depth) .. go:call("get_Name") .. "[" .. table.concat(comps, ",") .. "]"
        local c = go:call("get_Transform"):call("get_Child")
        while c do
            out[#out + 1] = go_tree(c:call("get_GameObject"), depth + 1)
            c = c:call("get_Next")
        end
    end)
    return table.concat(out, " ")
end

local function dump_dict(dict)
    local out = {}
    pcall(function()
        local e = dict:call("GetEnumerator")
        while e:call("MoveNext") do
            local kv = e:call("get_Current")
            local k = kv:get_field("key")
            local v = kv:get_field("value")
            local parts = v and v:get_field("<Parts>k__BackingField")
            out[#out + 1] = tostring(k) .. "=>" .. part_info(parts)
            if DEEP then
                out[#out + 1] = "TREE " .. go_tree(parts, 0)
                out[#out + 1] = "ITEM " .. obj_fields(v:get_field("<SwapItem>k__BackingField"))
                pcall(function()
                    for _, c in ipairs(parts:call("get_Components"):get_elements()) do
                        local tn = c:get_type_definition():get_full_name()
                        if tn:find("Holder") then
                            out[#out + 1] = "HOLDER " .. obj_fields(c)
                            local ms = {}
                            for _, m in ipairs(c:get_type_definition():get_methods()) do ms[#ms + 1] = m:get_name() end
                            out[#out + 1] = "METHODS " .. table.concat(ms, " ")
                        end
                    end
                end)
            end
        end
    end)
    return table.concat(out, " | ")
end

local ps_td = sdk.find_type_definition("app.PartSwapper")
for _, m in ipairs(ps_td:get_methods()) do
    local n = m:get_name()
    if n == "<swapBodyMesh>b__198_0" or n == "<swapBodySkin>b__199_0" or n == "swapBodyMesh" or n == "swapBodySkin" then
        sdk.hook(m, function(args)
            local ok, info = pcall(function()
                local ps = sdk.to_managed_object(args[2])
                local owner = ps and ps:call("get_GameObject"):call("get_Name") or "?"
                local extra = ""
                DEEP = owner == "ch000000_00"
                if n:find("b__") then extra = dump_dict(sdk.to_managed_object(args[3])) end
                return owner .. " " .. extra
            end)
            log_info(n .. " on " .. tostring(ok and info or info))
        end, function(r) return r end)
    end
end
log_info("hooks installed")

-- skin bake: BodyDetailEditor.bakingProcessing(step) -> bool, MaterialBakerController.build(b, b, string[], string[])
local bake_td = sdk.find_type_definition("app.BodyDetailEditor")
local bp = bake_td:get_method("bakingProcessing")
local cur_owner = {}
sdk.hook(bp, function(args)
    local ok, owner = pcall(function() return sdk.to_managed_object(args[2]):call("get_GameObject"):call("get_Name") end)
    cur_owner[1] = ok and owner or "?"
    cur_owner[2] = sdk.to_int64(args[3]) & 0xffffffff
end, function(retval)
    if cur_owner[1] == "ch000000_00" then
        log_info(string.format("bakingProcessing(%d) on %s -> %s", cur_owner[2], cur_owner[1], tostring((sdk.to_int64(retval) & 1) == 1)))
    end
    return retval
end)
local mbc_td = sdk.find_type_definition("app.MaterialBakerController")
sdk.hook(mbc_td:get_method("build"), function(args)
    local ok, info = pcall(function()
        local function strs(p)
            local a = sdk.to_managed_object(p)
            if a == nil then return "nil" end
            local out = {}
            for _, s in ipairs(a:get_elements()) do out[#out + 1] = tostring(s) end
            return "[" .. table.concat(out, ",") .. "]"
        end
        return string.format("b1=%d b2=%d s1=%s s2=%s", sdk.to_int64(args[3]) & 0xff, sdk.to_int64(args[4]) & 0xff, strs(args[5]), strs(args[6]))
    end)
    log_info("MaterialBakerController.build " .. tostring(ok and info or info))
end, function(r) return r end)
log_info("bake hooks installed")
