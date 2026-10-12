local ch, go = K.player()
local m = K.comp(go, 'via.render.Mesh')
local function p(h) return h and h:call('get_ResourcePath') end
local tr = go:call('get_Transform')
return { status = KarinReplacer.status(), mesh = p(m:call('getMesh')), mdf = p(m:call('get_Material')),
  chain = p(K.comp(go, 'via.motion.Chain'):call('get_ChainAsset')),
  hide = ch:call('get_HumanPartSwapper'):get_field('_HideSwapObjects'),
  head = K.comp(K.child(go, 'head'), 'via.render.Mesh'):call('get_Enabled'),
  root = tr:call('getJointByName', 'root') ~= nil, kjoint = tr:call('getJointByName', 'K_Hair_Front_0') ~= nil }
