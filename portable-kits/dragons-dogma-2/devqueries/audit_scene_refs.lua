-- Dev-only (slow: blocks the game for seconds). Every via.Behavior in the scene that is not part of the player's
-- hierarchy is walked like karin_replacer walks the player's caches (depth 4, containers included); reports the
-- components holding joints owned by the player's root Transform, and how many of those are dangling right now.
local ch, pgo = K.player()
local my = pgo:call("get_Transform"):get_address()
local mine_go = {}
local function mark(go)
  mine_go[go:get_address()] = true
  local c = go:call("get_Transform"):call("get_Child")
  while c do mark(c:call("get_GameObject")); c = c:call("get_Next") end
end
mark(pgo)
local fcache = {}
local function fields_of(td)
  local key = td:get_full_name()
  if fcache[key] then return fcache[key] end
  local l, t = {}, td
  while t do
    local tn = t:get_full_name()
    if tn == "via.Component" or tn == "System.Object" then break end
    for _, f in ipairs(t:get_fields()) do
      if not f:is_static() then l[#l + 1] = { f, f:get_type():get_full_name(), f:get_type():is_value_type() } end
    end
    t = t:get_parent_type()
  end
  fcache[key] = l
  return l
end
local hits = {}
local seen = {}
local function audit(comp, label)
  local st = { player = 0, dangling = 0, paths = {} }
  local function joint(j, path)
    if j == nil then return end
    local ok, o = pcall(j.call, j, "get_Owner")
    if ok and o and o:get_address() == my then
      st.player = st.player + 1
      if #st.paths < 4 then st.paths[#st.paths + 1] = path end
    end
  end
  local scan
  local function coll(c, is_list, path, depth, joints)
    local okn, n = pcall(function() if is_list then return c:call("get_Count") end return c:get_size() end)
    if not okn or n == nil then return end
    for i = 0, math.min(n, 512) - 1 do
      local ok, e = pcall(function() if is_list then return c:call("get_Item", i) end return c:get_element(i) end)
      if ok and e ~= nil then
        if joints then joint(e, path .. "[" .. i .. "]")
        elseif type(e) == "userdata" then scan(e, depth + 1, path .. "[" .. i .. "]") end
      end
    end
  end
  scan = function(obj, depth, path)
    if obj == nil or depth > 4 then return end
    local okd, td = pcall(obj.get_type_definition, obj)
    if not okd or td == nil then return end
    if not td:is_value_type() then
      local ok, a = pcall(obj.get_address, obj)
      if not ok or seen[a] then return end
      seen[a] = true
      if depth > 0 and (td:is_a("via.Component") or td:is_a("via.UserData")) then return end
    end
    for _, fi in ipairs(fields_of(td)) do
      local f, ft, fv = fi[1], fi[2], fi[3]
      local p = path .. "." .. f:get_name()
      if ft == "via.Joint" then local ok, v = pcall(obj.get_field, obj, f:get_name()); if ok then joint(v, p) end
      elseif ft == "System.Collections.Generic.List`1<via.Joint>" or ft == "via.Joint[]" then
        local ok, v = pcall(obj.get_field, obj, f:get_name()); if ok and v then coll(v, ft:sub(-2) ~= "[]", p, depth, true) end
      elseif not fv and ft:find("^System%.Collections%.Generic%.List`1<app%.") then
        local ok, v = pcall(obj.get_field, obj, f:get_name()); if ok and v then coll(v, true, p, depth, false) end
      elseif not fv and ft:sub(1, 4) == "app." then
        local ok, v = pcall(obj.get_field, obj, f:get_name())
        if ok and v and type(v) == "userdata" then
          if ft:sub(-2) == "[]" then coll(v, false, p, depth, false) else scan(v, depth + 1, p) end
        end
      end
    end
  end
  scan(comp, 0, label)
  return st
end
local t0 = os.clock()
local sm = sdk.get_native_singleton("via.SceneManager")
local scene = sdk.call_native_func(sm, sdk.find_type_definition("via.SceneManager"), "get_CurrentScene()")
local all = scene:call("findComponents(System.Type)", sdk.typeof("via.Behavior"))
local list = all and all:get_elements() or {}
local n, skipped = 0, 0
for _, c in ipairs(list) do
  local okg, g = pcall(c.call, c, "get_GameObject")
  if okg and g and not mine_go[g:get_address()] then
    n = n + 1
    local okt, tn = pcall(function() return c:get_type_definition():get_full_name() end)
    local label = (okt and tn or "?") .. "@" .. tostring(g:call("get_Name"))
    local ok, st = pcall(audit, c, label)
    if ok and st.player > 0 then hits[#hits + 1] = string.format("%s player=%d %s", label, st.player, table.concat(st.paths, " ")) end
  else
    skipped = skipped + 1
  end
  if os.clock() - t0 > 90 then hits[#hits + 1] = "TIME BUDGET HIT"; break end
end
hits[#hits + 1] = string.format("behaviors scanned: %d (player's own skipped: %d) in %.1f s", n, skipped, os.clock() - t0)
return hits
