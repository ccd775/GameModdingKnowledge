local out = {}
local sm = sdk.get_native_singleton("via.SceneManager")
local scene = sdk.call_native_func(sm, sdk.find_type_definition("via.SceneManager"), "get_CurrentScene()")
local l = scene:call("findComponents(System.Type)", sdk.typeof("app.GUIMenuMockupList")):get_elements()[1]
local ch = K.player()
local list = l:get_field("ModelList")
for i = 0, list:call("get_Count") - 1 do
  local md = list:call("get_Item", i)
  if md and md:get_field("CharaId") == ch:call("get_CharaID") then
    local o = md:get_field("Obj")
    local m = K.comp(o, 'via.render.Mesh')
    local c = K.comp(o, 'via.motion.Chain')
    local hd = K.child(o, 'head')
    out[#out+1] = { name = o:call("get_Name"), mesh = m:call('getMesh'):call('get_ResourcePath'),
      chain = c and c:call('get_ChainAsset') and c:call('get_ChainAsset'):call('get_ResourcePath'),
      head = hd and K.comp(hd,'via.render.Mesh'):call('get_Enabled') }
  end
end
return { status = KarinReplacer.status(), mockups = out }
