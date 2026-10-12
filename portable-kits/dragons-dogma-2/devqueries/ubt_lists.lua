local ch = K.player()
local ubt = ch:call("get_UpperBodyTransformer")
local o = {}
for _, n in ipairs({ "NeckToHead", "LeftArm", "RightArm", "NeckToHeadIndex", "LeftArmIndex", "RightArmIndex" }) do
  o[#o + 1] = n .. "=" .. ubt:get_field(n):call("get_Count")
end
return KarinReplacer.status() .. " | " .. table.concat(o, " ")
