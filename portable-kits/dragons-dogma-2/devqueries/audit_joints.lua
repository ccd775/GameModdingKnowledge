-- joint audit of a character's caches (fields, joint lists/arrays, and inside List<app.X>/app.X[] incl. structs):
-- own = live joints of this character, dangling = get_Owner fails, foreign = other characters' joints
local which = KARIN_AUDIT_TARGET or "player"
local ch, go = K.player()
if which == "mockup" then
  local sm = sdk.get_native_singleton("via.SceneManager")
  local scene = sdk.call_native_func(sm, sdk.find_type_definition("via.SceneManager"), "get_CurrentScene()")
  local l = scene:call("findComponents(System.Type)", sdk.typeof("app.GUIMenuMockupList")):get_elements()[1]
  local list = l:get_field("ModelList")
  for i = 0, list:call("get_Count") - 1 do
    local md = list:call("get_Item", i)
    if md and md:get_field("CharaId") == ch:call("get_CharaID") then go = md:get_field("Obj") end
  end
end
if which == "npc" then
  local sm = sdk.get_native_singleton("via.SceneManager")
  local scene = sdk.call_native_func(sm, sdk.find_type_definition("via.SceneManager"), "get_CurrentScene()")
  for _, c in ipairs(scene:call("findComponents(System.Type)", sdk.typeof("app.Character")):get_elements()) do
    local g = c:call("get_GameObject")
    if g:call("get_Name") == (KARIN_AUDIT_NPC or "ch300748") then go = g end
  end
end
local my = go:call("get_Transform"):get_address()
local st = { own = 0, dangling = 0, foreign = 0, where = {}, unreadable = 0, maxn = 0, maxpath = "", cfail = 0 }
local seen = {}
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
local function joint(j, path)
  if j == nil then return end
  local ok, o = pcall(j.call, j, "get_Owner")
  if not ok or o == nil then st.dangling = st.dangling + 1; if #st.where < 20 then st.where[#st.where + 1] = path end
  elseif o:get_address() == my then st.own = st.own + 1
  else
    st.foreign = st.foreign + 1
    if KARIN_AUDIT_FOREIGN and #st.where < 40 then
      local okg, gn = pcall(function() return o:call("get_GameObject"):call("get_Name") end)
      st.where[#st.where + 1] = "F:" .. path .. "->" .. tostring(okg and gn or "?")
    end
  end
end
local scan
local function read(obj, f)
  local ok, v = pcall(f.get_data, f, obj)
  if ok then return v end
  local ok2, v2 = pcall(obj.get_field, obj, f:get_name())
  if not ok2 then st.unreadable = st.unreadable + 1 end
  return ok2 and v2 or nil
end
local function coll(c, is_list, path, depth, joints)
  local okn, n = pcall(function() if is_list then return c:call("get_Count") end return c:get_size() end)
  if not okn then st.cfail = st.cfail + 1; return end
  if n > st.maxn then st.maxn = n; st.maxpath = path end
  for i = 0, math.min(n, 256) - 1 do
    local ok, e = pcall(function() if is_list then return c:call("get_Item", i) end return c:get_element(i) end)
    if ok and e ~= nil then
      if joints then joint(e, path .. "[" .. i .. "]")
      elseif type(e) == "userdata" then scan(e, depth + 1, path .. "[" .. i .. "]") end
    end
  end
end
scan = function(obj, depth, path)
  if obj == nil or depth > 5 then return end
  local ok, a = pcall(obj.get_address, obj)
  local isv = obj:get_type_definition():is_value_type()
  if not isv then
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
for _, c in ipairs(go:call("get_Components"):get_elements()) do scan(c, 0, c:get_type_definition():get_name()) end
return string.format("%s own=%d dangling=%d foreign=%d unreadable=%d countfail=%d maxcontainer=%d@%s %s", go:call("get_Name"), st.own, st.dangling, st.foreign, st.unreadable, st.cfail, st.maxn, st.maxpath,
  #st.where > 0 and ("e.g. " .. table.concat(st.where, " ")) or "")
