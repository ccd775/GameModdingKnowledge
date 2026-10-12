-- dev: record skirt chain node positions in her rest-pose body frame (relative to Hip) every frame, for NFRAMES frames
local ch, go = K.player()
local tr = go:call("get_Transform")
local P = { "0", "8" }
for i = 1, 7 do P[#P + 1] = i .. "_L"; P[#P + 1] = i .. "_R" end
local J = {}
for _, p in ipairs(P) do
  for _, s in ipairs({ "_001", "_002", "_002_end" }) do
    local j = tr:call("getJointByName", "K_Skirt_" .. p .. s)
    if j == nil then return "missing K_Skirt_" .. p .. s end
    J[#J + 1] = j
  end
end
for _, n in ipairs({ "L_Leg_Upper", "L_Leg_Lower", "R_Leg_Upper", "R_Leg_Lower" }) do J[#J + 1] = tr:call("getJointByName", n) end
SR = { names = P, rows = {}, on = true, n = NFRAMES or 480, hip = tr:call("getJointByName", "Hip"), tr = tr, J = J }
local function qrot(q, x, y, z)  -- rotate (x,y,z) by quaternion q
  local tx, ty, tz = 2 * (q.y * z - q.z * y), 2 * (q.z * x - q.x * z), 2 * (q.x * y - q.y * x)
  return x + q.w * tx + (q.y * tz - q.z * ty), y + q.w * ty + (q.z * tx - q.x * tz), z + q.w * tz + (q.x * ty - q.y * tx)
end
SR.qrot = qrot
if not SR_REG then
  SR_REG = true
  re.on_pre_application_entry("BeginRendering", function()
    local S = SR
    if not S or not S.on then return end
    if #S.rows >= S.n then S.on = false return end
    local ok = pcall(function()
      local hp, hq = S.hip:call("get_Position"), S.hip:call("get_Rotation")
      local iq = { x = -hq.x, y = -hq.y, z = -hq.z, w = hq.w }
      local rp = S.tr:call("get_Position")
      local row = { math.floor(rp.x * 1000 + 0.5), math.floor(rp.y * 1000 + 0.5), math.floor(rp.z * 1000 + 0.5) }
      for _, j in ipairs(S.J) do
        local p = j:call("get_Position")
        local lx, ly, lz = S.qrot(iq, p.x - hp.x, p.y - hp.y, p.z - hp.z)
        -- Hip rest axes: local X = up, local Y = -left(x), local Z = forward
        row[#row + 1] = math.floor(-ly * 1000 + 0.5); row[#row + 1] = math.floor(lx * 1000 + 0.5); row[#row + 1] = math.floor(lz * 1000 + 0.5)
      end
      S.rows[#S.rows + 1] = row
    end)
    if not ok then S.on = false end
  end)
end
return "rec " .. #J
