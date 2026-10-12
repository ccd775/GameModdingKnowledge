-- Which native via.* objects (not components, not joints) do the player's scripts cache? Walks the same graph as
-- karin_replacer (components of the root and its descendants, depth 5, containers included) and counts field types
-- via.* that are neither components nor via.Joint, with an example path each.
local ch, go = K.player()
local counts, example = {}, {}
local seen = {}
local fc = {}
local function fields_of(td)
  local key = td:get_full_name()
  if fc[key] then return fc[key] end
  local l, t = {}, td
  while t do
    local tn = t:get_full_name()
    if tn == "via.Component" or tn == "System.Object" then break end
    for _, f in ipairs(t:get_fields()) do
      if not f:is_static() then l[#l + 1] = { f, f:get_type():get_full_name(), f:get_type():is_value_type() } end
    end
    t = t:get_parent_type()
  end
  fc[key] = l
  return l
end
local scan
local FILTER = KARIN_NATIVE_FILTER   -- optional: only this type, list every path
local function note(tn, path)
  if FILTER and tn ~= FILTER then return end
  counts[tn] = (counts[tn] or 0) + 1
  example[tn] = example[tn] or path
  if FILTER then counts[path] = 1 end
end
local function coll(c, is_list, path, depth)
  local okn, n = pcall(function() if is_list then return c:call("get_Count") end return c:get_size() end)
  if not okn or n == nil then return end
  for i = 0, math.min(n, 256) - 1 do
    local ok, e = pcall(function() if is_list then return c:call("get_Item", i) end return c:get_element(i) end)
    if ok and e ~= nil and type(e) == "userdata" then scan(e, depth + 1, path .. "[" .. i .. "]") end
  end
end
scan = function(obj, depth, path)
  if obj == nil or depth > 5 then return end
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
    if not fv and ft:sub(1, 4) == "via." and ft ~= "via.Joint" and ft ~= "via.GameObject" and ft ~= "via.Transform" then
      local ok, v = pcall(obj.get_field, obj, f:get_name())
      if ok and v ~= nil and type(v) == "userdata" then
        local okc, isc = pcall(function() return v:get_type_definition():is_a("via.Component") end)
        if okc and not isc then note(ft, p) end
      end
    elseif not fv and ft:find("^System%.Collections%.Generic%.List`1<app%.") then
      local ok, v = pcall(obj.get_field, obj, f:get_name()); if ok and v then coll(v, true, p, depth) end
    elseif not fv and ft:sub(1, 4) == "app." then
      local ok, v = pcall(obj.get_field, obj, f:get_name())
      if ok and v and type(v) == "userdata" then
        if ft:sub(-2) == "[]" then coll(v, false, p, depth) else scan(v, depth + 1, p) end
      end
    end
  end
end
local function all(g, prefix)
  for _, c in ipairs(g:call("get_Components"):get_elements()) do scan(c, 0, prefix .. c:get_type_definition():get_name()) end
  local c = g:call("get_Transform"):call("get_Child")
  while c do
    local cg = c:call("get_GameObject")
    pcall(all, cg, prefix .. cg:call("get_Name") .. "/")
    c = c:call("get_Next")
  end
end
all(go, "")
local out = {}
for tn, n in pairs(counts) do out[#out + 1] = string.format("%4d %s  e.g. %s", n, tn, example[tn]) end
table.sort(out, function(a, b) return a > b end)
return out
