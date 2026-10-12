-- Who else holds the player's joints? Walks (like audit_joints.lua) the components of
--   * every child GameObject of the player (head, hair, weapons, lantern, ...), and
--   * every other app.Character in the scene (NPCs, pawns, enemies),
-- and counts references to joints owned by the player's root Transform, plus dangling joints (get_Owner fails).
local ch, pgo = K.player()
local my = pgo:call("get_Transform"):get_address()
local function fields_of(td)
  local l, t = {}, td
  while t do
    local tn = t:get_full_name()
    if tn == "via.Component" or tn == "System.Object" then break end
    for _, f in ipairs(t:get_fields()) do
      if not f:is_static() then l[#l + 1] = { f, f:get_type():get_full_name(), f:get_type():is_value_type() } end
    end
    t = t:get_parent_type()
  end
  return l
end
local function audit(go)
  local st = { player = 0, dangling = 0, where = {} }
  local seen = {}
  local function joint(j, path)
    if j == nil then return end
    local ok, o = pcall(j.call, j, "get_Owner")
    if not ok or o == nil then st.dangling = st.dangling + 1; if #st.where < 6 then st.where[#st.where + 1] = "D:" .. path end
    elseif o:get_address() == my then st.player = st.player + 1; if #st.where < 6 then st.where[#st.where + 1] = "P:" .. path end end
  end
  local function read(obj, f)
    local ok, v = pcall(obj.get_field, obj, f:get_name())
    return ok and v or nil
  end
  local scan
  local function coll(c, is_list, path, depth, joints)
    local okn, n = pcall(function() if is_list then return c:call("get_Count") end return c:get_size() end)
    if not okn or n == nil then return end
    for i = 0, math.min(n, 4096) - 1 do
      local ok, e = pcall(function() if is_list then return c:call("get_Item", i) end return c:get_element(i) end)
      if ok and e ~= nil then
        if joints then joint(e, path .. "[" .. i .. "]")
        elseif type(e) == "userdata" then scan(e, depth + 1, path .. "[" .. i .. "]") end
      end
    end
  end
  scan = function(obj, depth, path)
    if obj == nil or depth > 5 then return end
    local isv = obj:get_type_definition():is_value_type()
    if not isv then
      local ok, a = pcall(obj.get_address, obj)
      if not ok or seen[a] then return end
      seen[a] = true
      local okt, skip = pcall(function() local vt = obj:get_type_definition(); return depth > 0 and (vt:is_a("via.Component") or vt:is_a("via.UserData")) end)
      if okt and skip then return end
    end
    for _, fi in ipairs(fields_of(obj:get_type_definition())) do
      local f, ft, fv = fi[1], fi[2], fi[3]
      local p = path .. "." .. f:get_name()
      if ft == "via.Joint" then joint(read(obj, f), p)
      elseif ft == "System.Collections.Generic.List`1<via.Joint>" then local v = read(obj, f); if v then coll(v, true, p, depth, true) end
      elseif ft == "via.Joint[]" then local v = read(obj, f); if v then coll(v, false, p, depth, true) end
      elseif not fv and ft:find("^System%.Collections%.Generic%.List`1<app%.") then local v = read(obj, f); if v then coll(v, true, p, depth, false) end
      elseif not fv and ft:sub(1, 4) == "app." then
        local v = read(obj, f)
        if v and type(v) == "userdata" then
          if ft:sub(-2) == "[]" then coll(v, false, p, depth, false) else scan(v, depth + 1, p) end
        end
      end
    end
  end
  local comps = go:call("get_Components")
  if comps == nil then return st end
  for _, c in ipairs(comps:get_elements()) do scan(c, 0, c:get_type_definition():get_name()) end
  return st
end
local out = {}
local function report(label, go)
  local ok, st = pcall(audit, go)
  if not ok then out[#out + 1] = label .. ": error " .. tostring(st); return end
  if st.player > 0 or st.dangling > 0 then
    out[#out + 1] = string.format("%s: player=%d dangling=%d %s", label, st.player, st.dangling, table.concat(st.where, " "))
  end
end
-- children of the player (recursive)
local function children(go, prefix)
  local c = go:call("get_Transform"):call("get_Child")
  while c do
    local g = c:call("get_GameObject")
    local name = prefix .. "/" .. g:call("get_Name")
    report("child " .. name, g)
    children(g, name)
    c = c:call("get_Next")
  end
end
local t0 = os.clock()
children(pgo, "")
local t1 = os.clock()
local sm = sdk.get_native_singleton("via.SceneManager")
local scene = sdk.call_native_func(sm, sdk.find_type_definition("via.SceneManager"), "get_CurrentScene()")
local n = 0
for _, c in ipairs(scene:call("findComponents(System.Type)", sdk.typeof("app.Character")):get_elements()) do
  local g = c:call("get_GameObject")
  if g ~= pgo then n = n + 1; report("chara " .. g:call("get_Name"), g) end
end
out[#out + 1] = string.format("characters scanned: %d; children %.0f ms, characters %.0f ms", n, (t1 - t0) * 1000, (os.clock() - t1) * 1000)
return out
