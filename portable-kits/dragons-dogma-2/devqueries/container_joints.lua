-- joint caches of the player that sit inside containers of script objects (List<app.X> / app.X[]),
-- i.e. the ones karin_replacer's walker does not reach. Reports path, element count and joints owned by the player.
local ch, go = K.player()
local my = go:call("get_Transform"):get_address()
local out = {}
local seen = {}
local function mine(j)
  local ok, o = pcall(j.call, j, "get_Owner")
  return ok and o and o:get_address() == my
end
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
local function joints_in(obj)
  -- direct joint holders of one element object
  local n, names = 0, {}
  for _, fi in ipairs(fields_of(obj:get_type_definition())) do
    local f, ft = fi[1], fi[2]
    if ft == "via.Joint" then
      local ok, j = pcall(f.get_data, f, obj)
      if ok and j and mine(j) then n = n + 1; names[#names + 1] = f:get_name() end
    elseif ft == "System.Collections.Generic.List`1<via.Joint>" or ft == "via.Joint[]" then
      local ok, c = pcall(f.get_data, f, obj)
      if ok and c then names[#names + 1] = f:get_name() .. "(coll)"; n = n + 1 end
    end
  end
  return n, names
end
local scan
local function container(c, path, depth)
  local okc, elems = pcall(function()
    if c:get_type_definition():get_full_name():sub(-2) == "[]" then return c:get_elements() end
    return c:call("ToArray"):get_elements()
  end)
  if not okc or elems == nil then return end
  local total, fieldnames = 0, {}
  local kind = (c:get_type_definition():get_full_name():sub(-2) == "[]") and "array" or "list"
  local vt = "?"
  for i, e in ipairs(elems) do
    if i > 64 then break end
    if e and type(e) == "userdata" then
      pcall(function() vt = e:get_type_definition():is_value_type() and "struct" or "class" end)
      local okn, n, names = pcall(joints_in, e)
      if okn and n > 0 then total = total + n; for _, x in ipairs(names) do fieldnames[x] = true end end
      pcall(scan, e, depth + 1, path .. "[" .. (i - 1) .. "]")
    end
  end
  if total > 0 then
    local fn = {}
    for k in pairs(fieldnames) do fn[#fn + 1] = k end
    out[#out + 1] = string.format("%s [%s of %s]: %d elems, %d joints", path, kind, vt, #elems, total)
  end
end
scan = function(obj, depth, path)
  if obj == nil or depth > 4 then return end
  local ok, a = pcall(obj.get_address, obj)
  if not ok or seen[a] then return end
  seen[a] = true
  for _, fi in ipairs(fields_of(obj:get_type_definition())) do
    local f, ft, isv = fi[1], fi[2], fi[3]
    if not isv and (ft:find("^System.Collections.Generic.List`1<app%.") or (ft:sub(1, 4) == "app." and ft:sub(-2) == "[]")) then
      local okv, v = pcall(f.get_data, f, obj)
      if okv and v then container(v, path .. "." .. f:get_name(), depth) end
    elseif not isv and ft:sub(1, 4) == "app." and ft:sub(-2) ~= "[]" then
      local okv, v = pcall(f.get_data, f, obj)
      if okv and v and type(v) == "userdata" then
        local okt, skip = pcall(function() local vt = v:get_type_definition(); return vt:is_a("via.Component") or vt:is_a("via.UserData") end)
        if okt and not skip then scan(v, depth + 1, path .. "." .. f:get_name()) end
      end
    end
  end
end
for _, c in ipairs(go:call("get_Components"):get_elements()) do scan(c, 0, c:get_type_definition():get_name()) end
table.sort(out)
return out
