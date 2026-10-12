-- live chain tuning on the player (dev only): set per-group runtime rates by the group's setting id, return tip drops.
-- SET = { [settingId] = { grav=, damp=, elastic=, motion=, angle= } } (a global set by the caller's chunk)
local ch, go = K.player()
local chain = K.comp(go, 'via.motion.Chain')
local out = {}
for i = 0, chain:call('getGroupCount') - 1 do
    local g = chain:call('getGroup', i)
    local s = SET and SET[g:call('get_ResourceSettingID')]
    if s then
        if s.grav then g:call('set_GravityRate', s.grav) end
        if s.damp then g:call('set_DampingRate', s.damp) end
        if s.elastic then g:call('set_ElasticRate', s.elastic) end
        if s.motion then g:call('set_MotionForceCoef', s.motion) end
        if s.angle then g:call('set_AngleLimitCoef', s.angle) end
    end
    local n = g:call('get_NodeCount')
    local a, b = g:call('getNodePosition', 0), g:call('getNodePosition', n - 1)
    out[#out + 1] = string.format('%d sid %d rates g%.2f d%.2f e%.2f m%.2f | root->tip dz %.3f dh %.3f', i,
        g:call('get_ResourceSettingID'), g:call('get_GravityRate'), g:call('get_DampingRate'), g:call('get_ElasticRate'),
        g:call('get_MotionForceCoef'), b.y - a.y, math.sqrt((b.x - a.x) ^ 2 + (b.z - a.z) ^ 2))
end
return out
