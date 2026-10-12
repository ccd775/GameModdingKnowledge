-- chain state of the player: per joint, world position and how far the chain turned it from its base (rest) rotation
local ch, go = K.player()
local tr = go:call('get_Transform')
local chain = K.comp(go, 'via.motion.Chain')
local out = {}
pcall(function() out.asset = chain:call('get_ChainAsset'):call('get_ResourcePath') end)
pcall(function() out.enabled = chain:call('get_Enabled') end)
local function ang(a, b)
    local d = math.abs(a.x * b.x + a.y * b.y + a.z * b.z + a.w * b.w)
    return math.deg(2 * math.acos(math.min(1, d)))
end
for _, n in ipairs(NAMES or { 'K_Hair_tail_L', 'K_Hair_tail_L_003', 'K_Hair_tail_L_005', 'K_Hair_side_L', 'K_Hair_side_L_002',
    'K_Tail', 'K_Tail_003', 'K_Tail_005', 'K_Skirt_4_L', 'K_Skirt_4_L_002', 'K_Skirt_0', 'K_Skirt_0_002', 'K_Ear_L' }) do
    local j = tr:call('getJointByName', n)
    if j then
        local p = j:call('get_Position')
        local r = { pos = { p.x, p.y, p.z } }
        pcall(function() r.turn = ang(j:call('get_LocalRotation'), j:call('get_BaseLocalRotation')) end)
        out[n] = r
    else
        out[n] = 'missing'
    end
end
return out
