-- Karin PicodraTech player replacer for Dragon's Dogma 2 (REFramework, TU3.2) -- v1.3.0
--
-- How it works (see SOP.md 6.0):
--  * The game builds a character's body through its own part-swap pipeline: body part objects carrying an
--    app.PartSwapMeshHolder (mesh) and an app.PartSwapMaterialHolder (material) are instantiated, their swap(Mesh) puts
--    the resources on the character's body, the body chain comes in through app.PartSwapper.setBodyChainAsset, and the
--    game then sets everything up on the resulting skeleton.
--  * For the player and the player's menu model, this script hands Karin's mesh, material and chain to those calls, so
--    the character is *built* as Karin (resources in pak_mods/KarinPicodraTech.pak). Nothing is swapped at runtime:
--    swapping the body of a live character leaves engine systems on freed joints (see SOP 6.3; v1.1 did that).
--    The Karin mesh carries the native 192-joint skeleton first (same names and order, Karin proportions) plus her
--    secondary joints. The game's skin bake (native body textures) is routed past on her body; the per-character
--    detail steps around it still run on copies of the native body materials kept in her MDF.
--  * At runtime only cheap things are kept up on a body that is Karin: her mesh parts visible, the original head
--    hidden, every swap object (hair, brows, beard, all equipment, underwear) hidden.
--  * Her face follows the hidden native head's facial rig (blinks, mouth, eye direction): see "facial expressions".
--  * Turning the mod (or the menu option) on or off takes effect the next time the character is built: load a save.
-- Pawns and NPCs are untouched: targets are identified by the player's object names, never by looks. Only the female
-- human body is replaced (male bodies have joints Karin's skeleton lacks, Beastren bodies carry fur); others keep
-- their look.

local MOD = "Karin Replacer"
local VERSION = "1.3.0"
local MESH_PATH = "Character/_karin/karin_body.mesh"
local MDF_PATH = "Character/_karin/karin_body.mdf2"
local CHAIN_PATH = "Character/_karin/karin_body.chain"
local PLAYER_GO = "ch000000_00"                  -- the player's root object
local MOCKUP_GO = "MockupModel_ch000000_00"      -- the player's model in menus (equipment screen, portrait)
local ANY_BODY_MESH = "^Character/_kit/body/"                               -- body meshes the game builds with
local ANY_BODY_MDF = "^AppSystem/CharaEdit/ch000/Material/Runtime/body_"     -- body materials the game builds with
local HUMAN_F_MESH = "^Character/_kit/body/body_000_f/"                      -- the female body mesh
local HUMAN_MDF = "^AppSystem/CharaEdit/ch000/Material/Runtime/body_runtime_human"   -- the human skin
local NATIVE_BODY_CHAIN = "^Character/_kit/body/_common/secondary/body_chain%.chain"
local HIDE_ALL = 8191         -- app.charaedit.ch000.Define.SwapObjects.Newborn (hair, beard, brows, all gear, underwear)
local PARTS = 8               -- Karin mesh visibility groups 0..7
local LOAD_WAIT_SEC = 5.0     -- resources are handed out only this long after creation (an unloaded one crashes)
local CHECK_EVERY = 5         -- frames between maintenance passes
local SCAN_SEC = 2.0          -- mockup discovery interval
local CHAIN_REST_POSE = false -- put her K_* (chain) joints back to their rest rotation every frame (see rest_sets)
-- facial expressions: how much native motion moves her face all the way (see "facial expressions")
local FACE_EYE_FULL_DEG = 20  -- eye turn that moves her irises as far as her look shape keys go
local FACE_JAW_FULL_DEG = 12  -- jaw opening that opens her mouth fully (her "aa" shape key)
local FACE_BLINK_FULL = 0.75  -- lid closing, as a share of the open eye's lid gap, that closes her eye
local FACE_BLINK_DEAD = 0.15  -- share of that below which her eye stays open (the native lids drift a little at rest)

local cfg = { enabled = true, physics = true, mockups = true, face = true }
local CFG_FILE = "karin_replacer/config.json"
pcall(function()
    local c = json.load_file(CFG_FILE)
    if type(c) == "table" then
        for k, v in pairs(c) do
            if type(v) == "boolean" and cfg[k] ~= nil then cfg[k] = v end
        end
    end
end)
local function save_cfg() pcall(json.dump_file, CFG_FILE, cfg) end

local R = nil                 -- resource holders { mesh, mdf, chain, created }
local next_resource_try = 0
local live_ps = {}            -- [PartSwapper address] = true: bodies that are Karin (hide-mask hook filter)
local wanted_mask = {}        -- [PartSwapper address] = { ps, mask }: the hide mask the game last asked for on a Karin body
local touched = {}            -- [GameObject address] = the object: head hidden / mask forced here while it was Karin
local guard_ok = false        -- every hook and field this relies on exists in this game version (else: never Karin)
local own_mask_write = false  -- this script's own set_HideSwapObjects call is in progress
local unsupported_note = nil  -- why the player keeps the original look, when it is the body type
local proportion_noted = {}   -- [BodyEditor address] = true once the body-shape skip was logged
local mockup_list, mockup_face = nil, nil
local last_scan = -100
local frame = 0
local status = "waiting for player"
local portrait_done = {}      -- [mockup object address] = true once the portrait was re-captured with Karin
local rest_sets = {}          -- [GameObject address] = her K_* joints and their rest rotations (CHAIN_REST_POSE)
local face_sets = {}          -- [GameObject address] = her expression joints and the native head's
local face_retry = {}         -- [GameObject address] = when to look for them again (none found last time)
local face_noted = {}         -- [GameObject address] = true once her expressions were logged for it
local face_err_noted = {}     -- [GameObject address] = true once a failure of her expressions was logged for it
local rest_retry = {}         -- [GameObject address] = when to look for her K_* joints again (none found last time)

local function log_info(msg) log.info("[" .. MOD .. "] " .. msg) end
local hook_storage = type(thread) == "table" and thread.get_hook_storage or nil   -- per-call pre/post data
local function now() return os.clock() end

local mesh_t = sdk.typeof("via.render.Mesh")
local ps_t = sdk.typeof("app.PartSwapper")

local function get_comp(go, t)
    if go == nil then return nil end
    local ok, c = pcall(go.call, go, "getComponent(System.Type)", t)
    return ok and c or nil
end

local function find_child(go, name)
    local ok, res = pcall(function()
        local c = go:call("get_Transform"):call("get_Child")
        while c do
            local g = c:call("get_GameObject")
            if g and g:call("get_Name") == name then return g end
            c = c:call("get_Next")
        end
        return nil
    end)
    return ok and res or nil
end

local function holder_path(h)
    if h == nil then return nil end
    local ok, p = pcall(h.call, h, "get_ResourcePath")
    return ok and p or nil
end

----------------------------------------------------------------------------------------------------------------------
-- resources
----------------------------------------------------------------------------------------------------------------------
local function make_holder(rtype, htype, path, acquired)
    local r = sdk.create_resource(rtype, path)
    if r == nil then return nil end
    r:add_ref(); acquired[#acquired + 1] = r
    local h = r:create_holder(htype)
    if h then h:add_ref(); acquired[#acquired + 1] = h end
    return h
end

local function create_resources()
    if R ~= nil then return true end
    if now() < next_resource_try then return false end
    next_resource_try = now() + 10.0
    local acquired = {}
    local ok, res = pcall(function()
        local r = {
            mesh = make_holder("via.render.MeshResource", "via.render.MeshResourceHolder", MESH_PATH, acquired),
            mdf = make_holder("via.render.MeshMaterialResource", "via.render.MeshMaterialResourceHolder", MDF_PATH, acquired),
            chain = make_holder("via.motion.ChainResource", "via.motion.ChainResourceHolder", CHAIN_PATH, acquired),
        }
        if r.mesh == nil or r.mdf == nil then return nil end
        r.created = now()
        return r
    end)
    if ok and res then
        R = res
        log_info("resources created")
        return true
    end
    for _, x in ipairs(acquired) do pcall(x.release, x) end
    status = "resources missing (is pak_mods/KarinPicodraTech.pak installed?)"
    return false
end

local function resources_ready() return R ~= nil and now() - R.created >= LOAD_WAIT_SEC end

-- her holders are still live managed objects (a freed one handed to a build would crash it); if not, they are made
-- again (this build keeps the original look)
local function resources_valid()
    local ok, valid = pcall(function()
        for k, path in pairs({ mesh = MESH_PATH, mdf = MDF_PATH, chain = CHAIN_PATH }) do
            if R[k] ~= nil and not (sdk.is_managed_object(R[k]:get_address()) and holder_path(R[k]) == path) then
                return false
            end
        end
        return true
    end)
    if ok and valid then return true end
    log_info("Karin's resources are no longer valid; creating them again")
    R, next_resource_try = nil, 0
    return false
end

----------------------------------------------------------------------------------------------------------------------
-- build-time hand-over (hooks into the game's part-swap pipeline)
----------------------------------------------------------------------------------------------------------------------
-- the name of the character whose body `mesh` (a via.render.Mesh) is, when this script turns it into Karin
local function karin_target_of(mesh)
    local ok, name = pcall(function() return mesh:call("get_GameObject"):call("get_Name") end)
    if not ok then return nil end
    if name == PLAYER_GO then return name end
    if name == MOCKUP_GO and cfg.mockups then return name end
    return nil
end

-- sdk.hook with pcall-guarded pre(args) and optional post() (per-call data: thread.get_hook_storage()); true if hooked
local function hook(tname, mname, pre, post)
    local td = sdk.find_type_definition(tname)
    local m = td and td:get_method(mname)
    if m == nil then log_info("hook target missing: " .. tname .. "." .. mname); return false end
    sdk.hook(m, function(args)
        local ok, err = xpcall(pre, debug.traceback, args)
        if not ok then log_info(tname .. "." .. mname .. " hook error: " .. tostring(err)) end
    end, function(retval)
        if post then
            local ok, err = xpcall(post, debug.traceback)
            if not ok then log_info(tname .. "." .. mname .. " post-hook error: " .. tostring(err)) end
        end
        return retval
    end)
    return true
end

-- Body type from the character's PartSwapper MetaData (app.Gender / app.Species), the same for both hooks of a build
-- whatever their order: only female humans are replaced (male bodies have joints Karin's skeleton lacks, Beastren
-- bodies carry fur). A body mesh path only tells the gender and a skin path only the species, so neither will do.
local function enum_value(tn, name)
    local t = sdk.find_type_definition(tn)
    local f = t and t:get_field(name)
    local ok, v = pcall(function() return f:get_data(nil) end)
    return ok and type(v) == "number" and v or nil
end
local GENDER_FEMALE = enum_value("app.Gender", "Female")
local SPECIES_HUMAN = enum_value("app.Species", "Human")
local function female_human(go)
    local ok, res = pcall(function()
        local ps = get_comp(go, ps_t)
        local meta = ps and ps:call("get_Meta")
        return meta ~= nil and meta:get_field("_Gender") == GENDER_FEMALE and meta:get_field("_Species") == SPECIES_HUMAN
    end)
    if not ok then log_info("body type unreadable (" .. tostring(res) .. "); keeping the original look") end
    return ok and res == true
end
-- The menu model is the player's own character (its MetaData cannot be read through REFramework): it gets Karin
-- exactly when the player's body is hers, which the player's build (always first) decided from the player's MetaData.
local function player_is_karin()
    local cm = sdk.get_managed_singleton("app.CharacterManager")
    local ch = cm and cm:call("get_ManualPlayer")
    if ch == nil or not ch:call("get_Valid") then return false end
    local m = get_comp(ch:call("get_GameObject"), mesh_t)
    return m ~= nil and holder_path(m:call("getMesh")) == MESH_PATH
end

-- One decision per character build, shared by its body-mesh and body-material hand-overs (milliseconds apart, in either
-- order), so a build never gets Karin's mesh without her materials or the other way round, even when the options or
-- resource readiness change in between. A decision serves one hand-over of each kind: the next one of a kind starts a
-- new decision (a new build), so nothing carries over from one build to the next; 2 s is only a backstop. Returns the
-- target's name when it is built as Karin. Only the player and the player's menu model get a decision.
-- `female_path`: this hand-over's native resource is the female human one (a veto next to the body-type rule, taken
-- when the decision is made; the second hand-over of a build follows the decision, so the pair never splits).
-- Also returns the resources the decision was validated with, which both hand-overs of the build use.
local BUILD_WINDOW_SEC = 2.0
local build_decision = {}     -- [target GameObject address] = { who = name or false, res, t, used = { [kind] = true } }
local function decide(target, kind, female_path)
    local ok, go = pcall(target.call, target, "get_GameObject")
    if not ok or go == nil then return nil end
    local name = go:call("get_Name")
    if name ~= PLAYER_GO and name ~= MOCKUP_GO then return nil end
    local key = go:get_address()
    local d = build_decision[key]
    if d ~= nil and not d.used[kind] and now() - d.t <= BUILD_WINDOW_SEC then
        d.used[kind] = true
        if d.who and not female_path then log_info(name .. ": " .. kind .. " path is not the female human one; following the build's decision") end
        if not d.who then return nil end
        return d.who, d.res
    end
    for k, old in pairs(build_decision) do
        if now() - old.t > BUILD_WINDOW_SEC then build_decision[k] = nil end
    end
    d = { who = false, t = now(), used = { [kind] = true } }
    build_decision[key] = d
    if name == MOCKUP_GO then portrait_done[key] = nil end   -- a new build of the menu model: new portrait
    local who = karin_target_of(target)
    if who == nil or not cfg.enabled then
        if name == PLAYER_GO then unsupported_note = nil end
        return nil
    end
    if not guard_ok then
        if name == PLAYER_GO then unsupported_note = "this game version is not supported (see re2_framework_log.txt)" end
        log_info(who .. " keeps the original look: this game version is not supported (see the log above)")
        return nil
    end
    local supported = female_path
    if supported then
        if name == PLAYER_GO then supported = female_human(go) else supported = player_is_karin() end
    end
    if name == PLAYER_GO then
        unsupported_note = not supported and "not supported for this body type (female human only)" or nil
    end
    if not supported then
        log_info(who .. " keeps the original look: only female human characters are replaced")
    elseif not resources_ready() then
        log_info("Karin not ready yet when " .. who .. " was built; she appears after the next load")
    elseif resources_valid() then
        d.who, d.res = who, R
    end
    if not d.who then return nil end
    return d.who, d.res
end

-- The holders belong to the game's temporary body-part objects. Karin's resource is in the holder only for the
-- duration of swap() (which puts it on the character), then the part's own resource goes back, so the part releases
-- exactly what it holds. (No add_ref / release around this: REFramework's release() on her holder freed it at the
-- next build -- measured.)
local function hand_over(field, native_prefix, female_prefix, resource, what)
    return function(args)
        if hook_storage == nil then return end
        local st = hook_storage()
        st.holder = nil
        local holder, target = sdk.to_managed_object(args[2]), sdk.to_managed_object(args[3])
        if holder == nil or target == nil then return end
        if resource == "mesh" and (next(rest_sets) ~= nil or next(face_sets) ~= nil) then
            local ok, go = pcall(target.call, target, "get_GameObject")
            if ok and go ~= nil then   -- the body (and its joints) is rebuilt
                rest_sets[go:get_address()], face_sets[go:get_address()] = nil, nil
            end
        end
        local orig = holder:get_field(field)
        local cur = holder_path(orig)
        if cur == nil or not cur:find(native_prefix) then return end   -- not the body part
        local who, res = decide(target, resource, cur:find(female_prefix) ~= nil)
        local mine = who and res and res[resource]
        if not mine then return end
        holder:set_field(field, mine)
        st.holder, st.orig, st.mine = holder, orig, mine
        log_info("built " .. who .. " with Karin's " .. what .. " (instead of " .. cur .. ")")
    end, function()
        if hook_storage == nil then return end
        local st = hook_storage()
        local holder, mine = st.holder, st.mine
        if holder == nil then return end
        st.holder, st.mine = nil, nil
        local cur = holder:get_field(field)
        if cur ~= nil and cur:get_address() == mine:get_address() then holder:set_field(field, st.orig) end
        st.orig = nil
    end
end

-- the body mesh: app.PartSwapMeshHolder.swap(via.render.Mesh target)
local mesh_hooked = hook("app.PartSwapMeshHolder", "swap", hand_over("_Mesh", ANY_BODY_MESH, HUMAN_F_MESH, "mesh", "body"))
-- the body material: app.PartSwapMaterialHolder.swap(via.render.Mesh target). Karin's MDF carries her materials plus
-- copies of the native body materials, which the game's skin-detail steps set parameters on.
local mdf_hooked = hook("app.PartSwapMaterialHolder", "swap", hand_over("_Material", ANY_BODY_MDF, HUMAN_MDF, "mdf", "materials"))

-- the body chain (physics): app.PartSwapper.setBodyChainAsset(via.motion.ChainResourceHolder); only the native body
-- chain is replaced, and only on a body that is Karin's (her chain needs her joints)
hook("app.PartSwapper", "setBodyChainAsset", function(args)
    if not (cfg.enabled and cfg.physics and R and R.chain) then return end
    local ps = sdk.to_managed_object(args[2])
    local body = ps and ps:call("get_BodyMesh")
    if body == nil or karin_target_of(body) == nil then return end
    if holder_path(body:call("getMesh")) ~= MESH_PATH then return end
    local cur = holder_path(sdk.to_managed_object(args[3]))
    if cur == nil or not cur:find(NATIVE_BODY_CHAIN) then return end
    args[3] = sdk.to_ptr(R.chain)
    log_info("body chain of " .. tostring(ps:call("get_GameObject"):call("get_Name")) .. " set to Karin's")
end)

-- The skin bake: BodyDetailEditor.bakingProcessing is a state machine on <Baking>k__BackingField
-- (app.BodyDetailEditor.BakingProcess). Its MaterialBake step (MaterialBakerController.build, which renders the native
-- body's skin textures) crashes on Karin's mesh, and she does not use the result (her own textures are complete). The
-- game's own non-baking modes (MaterialBake None / PreBake) go from ApplyParamWaiting straight to FinishingProcess; on a
-- Karin body the state machine takes that route at MaterialBake, so finishing, Completed and the baker's discard run
-- as usual. (Skipping build alone is not enough: the step after it reads the baked resource ids that build creates.)
-- One call can run several steps: ApplyPrepareWaiting falls through into ApplyParam, and ApplyParam (once its
-- parameters are done) through ApplyParamWaiting into MaterialBake. So a Karin body in ApplyPrepareWaiting /
-- ApplyParam keeps those steps (the detail parameters still get applied) and only build is skipped for its baker; the
-- waiting step after it is re-routed on the next call.
local BAKING = "<Baking>k__BackingField"
local BAKE = {}   -- BakingProcess values by name
local bake_names_ok = true
do
    local et = sdk.find_type_definition("app.BodyDetailEditor.BakingProcess")
    for name, fallback in pairs({ None = 0, ApplyPrepareWaiting = 3, ApplyParamWaiting = 5, MaterialBakeWaiting = 7,
                                  FinishingProcess = 12, Completed = 14, Failed = 15 }) do
        local f = et and et:get_field(name)
        local ok, v = pcall(function() return f:get_data(nil) end)
        if not (ok and type(v) == "number") then bake_names_ok = false end
        BAKE[name] = ok and type(v) == "number" and v or fallback
    end
end
-- [MaterialBakerController address] = { obj, n }: n bakingProcessing calls of a Karin body that may reach build are
-- running for that baker (counted up in the pre-hook, down in the post-hook of the same call). The entry holds the
-- baker itself, so its address cannot be reused by another baker while the entry exists (e.g. after a missed
-- post-hook).
local karin_bakers = {}
local bake_hooked = hook("app.BodyDetailEditor", "bakingProcessing", function(args)
    local bde = sdk.to_managed_object(args[2])
    if bde == nil then return end
    local b = bde:get_field(BAKING)
    if b < BAKE.ApplyPrepareWaiting or b > BAKE.MaterialBakeWaiting then return end   -- steps that can reach build
    local mesh = bde:get_field("<BodyMesh>k__BackingField")
    if mesh == nil or holder_path(mesh:call("getMesh")) ~= MESH_PATH then
        if next(karin_bakers) ~= nil then
            local mbc = bde:get_field("_MaterialBakerController")
            if mbc ~= nil then karin_bakers[mbc:get_address()] = nil end
        end
        return
    end
    if b >= BAKE.ApplyParamWaiting then
        bde:set_field(BAKING, BAKE.FinishingProcess)   -- this call runs the finishing step; build is not reached
        log_info("skin bake skipped on " .. tostring(bde:call("get_GameObject"):call("get_Name")))
        return
    end
    local mbc = bde:get_field("_MaterialBakerController")
    if mbc ~= nil and hook_storage ~= nil then
        local a = mbc:get_address()
        local e = karin_bakers[a] or { obj = mbc, n = 0 }
        e.n = e.n + 1
        karin_bakers[a] = e
        hook_storage().baker = a
    end
end, function()
    if hook_storage == nil or next(karin_bakers) == nil then return end
    local st = hook_storage()
    local a = st.baker
    if a == nil then return end
    st.baker = nil
    local e = karin_bakers[a]
    if e ~= nil then
        e.n = e.n - 1
        if e.n <= 0 then karin_bakers[a] = nil end
    end
end)
local build_hooked = false
do
    local mbc_td = sdk.find_type_definition("app.MaterialBakerController")
    local build = mbc_td and mbc_td:get_method("build")
    if build == nil then
        log_info("hook target missing: app.MaterialBakerController.build")
    else
        sdk.hook(build, function(args)
            local ok, a = pcall(sdk.to_int64, args[2])
            if not (ok and karin_bakers[a]) then return end
            return sdk.PreHookResult.SKIP_ORIGINAL
        end, function(retval) return retval end)
        build_hooked = true
    end
end

-- Body shape: every body is built with the save's character-creation proportions. BodyEditor.setupApplyEditScales
-- fetches the game's edit table (per slider, per joint scale data; CharacterEditManager.getBodyEditJointScale) into
-- _ApplyEditScales, and BodyEditorRoot.applyEdit combines it with the sliders into a local position / rotation / scale
-- per joint, which ends up baked into the joints' base pose (the scales compound down the hierarchy; the pelvis height
-- follows the body height). The native skeleton is authored for that; Karin's is not (her upper body and the joints of
-- her hair and ears came out at about half size). On her body the table is taken away right after it is fetched:
-- applyEdit then has nothing to apply and reports done (its own path for a missing table), and she keeps the rest pose
-- of her mesh, her own proportions and size.
local function body_is_karin(be)
    local mesh = be:get_field("<Mesh>k__BackingField")
    return mesh ~= nil and holder_path(mesh:call("getMesh")) == MESH_PATH
end
local shape_hooked = hook("app.BodyEditor", "setupApplyEditScales", function(args)
    if hook_storage == nil then return end
    local st = hook_storage()
    st.editor = nil
    local be = sdk.to_managed_object(args[2])
    if be ~= nil and body_is_karin(be) then st.editor = be end
end, function()
    if hook_storage == nil then return end
    local st = hook_storage()
    local be = st.editor
    st.editor = nil
    if be == nil then return end
    be:set_field("_ApplyEditScales", nil)
    local a = be:get_address()
    if not proportion_noted[a] then
        proportion_noted[a] = true
        log_info("Karin keeps her own proportions on " .. tostring(be:call("get_GameObject"):call("get_Name")))
    end
end)


-- keep the game's own hide-mask writes on Karin bodies at "hide everything" (live_ps is only a cheap pre-filter from
-- the last maintenance pass: the body is checked at the time of the write, so a character rebuilt without Karin keeps
-- the mask the game gives it)
hook("app.PartSwapper", "set_HideSwapObjects", function(args)
    if own_mask_write then return end
    local ok, a = pcall(sdk.to_int64, args[2])
    if not (ok and live_ps[a]) then return end
    local body = sdk.to_managed_object(args[2]):call("get_BodyMesh")
    if body == nil or holder_path(body:call("getMesh")) ~= MESH_PATH then return end
    -- every game request; given back on a rebuild without Karin
    wanted_mask[a] = { ps = sdk.to_managed_object(args[2]), mask = sdk.to_int64(args[3]) & 0xffffffff }
    args[3] = sdk.to_ptr(HIDE_ALL)
end)

----------------------------------------------------------------------------------------------------------------------
-- runtime upkeep (cheap, no mesh changes)
----------------------------------------------------------------------------------------------------------------------
-- the game's skin-detail state machine for this character is not running
local function bake_idle(go)
    local ok, idle = pcall(function()
        local bde = get_comp(go, sdk.typeof("app.BodyDetailEditor"))
        if bde == nil then return true end
        local b = bde:get_field(BAKING)
        return b == BAKE.None or b == BAKE.Completed or b == BAKE.Failed
    end)
    return ok and idle == true
end

-- Her K_* joints (hair, tail, skirt, ribbons: the ones her chain moves) are not driven by the game's motion system (it
-- drives the core skeleton only), so nothing puts them back to their rest pose between frames: the chain's spring then
-- has no rest shape to return to and gravity drags the tails and the skirt down for good (measured: the tail hung
-- straight down with spring x10 and no gravity). With CHAIN_REST_POSE they are set back to their base (rest) rotation
-- every frame before the scene update, like the motion system does for animated joints; the chain then swings them
-- around her rest shape. The joint list is dropped whenever the object's body is rebuilt (mesh hook), when it is no
-- longer Karin, on a load, and when a joint lookup no longer finds the same joint.
local joint_td, tr_td = sdk.find_type_definition("via.Joint"), sdk.find_type_definition("via.Transform")
local joint_set_rot = joint_td and joint_td:get_method("set_LocalRotation")
local tr_joint_by_hash = tr_td and tr_td:get_method("getJointByHash")
local rest_pose_ok = CHAIN_REST_POSE and joint_set_rot ~= nil and tr_joint_by_hash ~= nil   -- (else: left off)

local function collect_rest(go)
    local ok, set = pcall(function()
        local tr = go:call("get_Transform")
        local arr = tr:call("get_Joints")
        local list = {}
        for i = 0, arr:get_size() - 1 do
            local j = arr:get_element(i)
            if j ~= nil and j:call("get_Name"):sub(1, 2) == "K_" then
                list[#list + 1] = { j, j:call("get_BaseLocalRotation") }
            end
        end
        if #list == 0 then return nil end
        return { go = go, tr = tr, list = list, h0 = list[1][1]:call("get_NameHash"), a0 = list[1][1]:get_address() }
    end)
    return ok and set or nil
end

re.on_pre_application_entry("UpdateScene", function()
    if next(rest_sets) == nil then return end
    for a, set in pairs(rest_sets) do
        local ok = pcall(function()
            if not set.go:call("get_Valid") then error("gone") end
            local j0 = tr_joint_by_hash:call(set.tr, set.h0)
            if j0 == nil or j0:get_address() ~= set.a0 then error("joints rebuilt") end
            local list = set.list
            for i = 1, #list do joint_set_rot:call(list[i][1], list[i][2]) end
        end)
        if not ok then rest_sets[a] = nil end
    end
end)

----------------------------------------------------------------------------------------------------------------------
-- facial expressions
----------------------------------------------------------------------------------------------------------------------
-- The game animates faces with the joints of the head object (eyes, lids, jaw...: blinks, looks, talking, cutscenes),
-- and keeps doing so while that head's mesh is hidden. Her face moves with shape keys, which her mesh carries as
-- translation joints instead (SOP 6.4): "KF_<channel>_<k>" under Head_0, each with an unweighted child
-- "KF_<channel>_<k>_End" whose offset is how far the joint moves for the full shape; "KF_Iris" with children
-- "KF_Iris_<Left|Right|Up|Down>" at its full look offsets. Every frame before the scene update (her face then shows the
-- previous frame's native expression) the native lids, jaw and eyes are read and her joints set to match:
--   Blink / BlinkL / BlinkR: native upper lid down + lower lid up, against the open eye's gap (FACE_BLINK_FULL);
--   Mouth: native jaw opening angle (FACE_JAW_FULL_DEG);   iris: native eye yaw / pitch (FACE_EYE_FULL_DEG).
-- Her expression joints are not driven by the motion system, so they stay where they are set. The joint lists are
-- dropped on the same occasions as rest_sets, and when the native head's joints change.
local joint_set_pos = joint_td and joint_td:get_method("set_LocalPosition")
local face_ok = joint_set_pos ~= nil and tr_joint_by_hash ~= nil   -- (else: no expressions)
local NATIVE_FACE = { "L_Eye", "R_Eye", "C_Jaw", "L_UpperLid_03", "L_LowerLid_02", "R_UpperLid_03", "R_LowerLid_02" }
local FACE_CHANNELS = { "Blink", "BlinkL", "BlinkR", "Mouth" }
local IRIS_DIRS = { "Left", "Right", "Up", "Down" }

local function qrot(q, x, y, z)   -- (x, y, z) rotated by quaternion q
    local qx, qy, qz, qw = q.x, q.y, q.z, q.w
    local tx, ty, tz = 2 * (qy * z - qz * y), 2 * (qz * x - qx * z), 2 * (qx * y - qy * x)
    return x + qw * tx + qy * tz - qz * ty, y + qw * ty + qz * tx - qx * tz, z + qw * tz + qx * ty - qy * tx
end
local function clamp01(v) return v < 0 and 0 or (v > 1 and 1 or v) end

local function collect_face(go)
    local ok, set = pcall(function()
        local tr = go:call("get_Transform")
        local head = find_child(go, "head")
        if head == nil then return false end
        local htr = head:call("get_Transform")
        local nat = {}
        for _, n in ipairs(NATIVE_FACE) do
            nat[n] = htr:call("getJointByName", n)
            if nat[n] == nil then return false end
        end
        local function offset(j, e)   -- e's base position in j's parent space, relative to j
            local p = e:call("get_BaseLocalPosition")
            local x, y, z = qrot(j:call("get_BaseLocalRotation"), p.x, p.y, p.z)
            return { x, y, z }
        end
        local chans, first = {}, nil
        for _, c in ipairs(FACE_CHANNELS) do
            for k = 0, 7 do
                local j = tr:call("getJointByName", "KF_" .. c .. "_" .. k)
                if j == nil then break end
                local e = tr:call("getJointByName", "KF_" .. c .. "_" .. k .. "_End")
                if e == nil then return false end
                chans[c] = chans[c] or {}
                table.insert(chans[c], { j = j, base = j:call("get_BaseLocalPosition"), off = offset(j, e) })
                first = first or j
            end
        end
        local iris = nil
        local ij = tr:call("getJointByName", "KF_Iris")
        if ij ~= nil then
            iris = { j = ij, base = ij:call("get_BaseLocalPosition") }
            for _, s in ipairs(IRIS_DIRS) do
                local e = tr:call("getJointByName", "KF_Iris_" .. s)
                if e == nil then return false end
                iris[s] = offset(ij, e)
            end
            first = first or ij
        end
        if first == nil then return false end
        local base_y = {}
        for _, n in ipairs({ "L_UpperLid_03", "L_LowerLid_02", "R_UpperLid_03", "R_LowerLid_02" }) do
            base_y[n] = nat[n]:call("get_BaseLocalPosition").y
        end
        for _, s in ipairs({ "L", "R" }) do   -- an open eye's lid gap (a degenerate head would divide by ~0)
            if base_y[s .. "_UpperLid_03"] - base_y[s .. "_LowerLid_02"] < 0.002 then return false end
        end
        return { go = go, name = go:call("get_Name"), tr = tr, head = head, htr = htr, nat = nat, chans = chans,
                 iris = iris, base_y = base_y,
                 h0 = first:call("get_NameHash"), a0 = first:get_address(),
                 nh = nat.L_Eye:call("get_NameHash"), na = nat.L_Eye:get_address() }
    end)
    return ok and set or false
end

-- her expression joints back to rest (option turned off)
local function face_rest(set)
    pcall(function()
        for _, list in pairs(set.chans) do
            for _, e in ipairs(list) do joint_set_pos:call(e.j, e.base) end
        end
        if set.iris then joint_set_pos:call(set.iris.j, set.iris.base) end
    end)
end

local function eye_turn(q)   -- yaw (towards her left) and pitch (up) of the native eye, degrees; face space x left, y up, z ahead
    local x, y, z = qrot(q, 0, 0, 1)
    return math.deg(math.atan(x, z)), math.deg(math.atan(y, math.sqrt(x * x + z * z)))
end

local function drive_face(set)
    local nat, by = set.nat, set.base_y
    local function closing(up, lo)
        local gap = by[up] - by[lo]
        local c = (by[up] - nat[up]:call("get_LocalPosition").y) + (nat[lo]:call("get_LocalPosition").y - by[lo])
        return clamp01((c / (FACE_BLINK_FULL * gap) - FACE_BLINK_DEAD) / (1 - FACE_BLINK_DEAD))
    end
    local bl, br = closing("L_UpperLid_03", "L_LowerLid_02"), closing("R_UpperLid_03", "R_LowerLid_02")
    local _, jy, jz = qrot(nat.C_Jaw:call("get_LocalRotation"), 0, 0, 1)
    local amount = { Blink = (bl + br) / 2, BlinkL = bl, BlinkR = br,
                     Mouth = clamp01(math.deg(math.atan(-jy, jz)) / FACE_JAW_FULL_DEG) }
    for c, list in pairs(set.chans) do
        local a = amount[c]
        for i = 1, #list do
            local e = list[i]
            joint_set_pos:call(e.j, Vector3f.new(e.base.x + a * e.off[1], e.base.y + a * e.off[2], e.base.z + a * e.off[3]))
        end
    end
    local iris = set.iris
    if iris then
        local yl, pl = eye_turn(nat.L_Eye:call("get_LocalRotation"))
        local yr, pr = eye_turn(nat.R_Eye:call("get_LocalRotation"))
        local yaw = math.max(-1, math.min(1, (yl + yr) / (2 * FACE_EYE_FULL_DEG)))
        local pitch = math.max(-1, math.min(1, (pl + pr) / (2 * FACE_EYE_FULL_DEG)))
        local h, v = yaw >= 0 and iris.Left or iris.Right, pitch >= 0 and iris.Up or iris.Down
        local ay, ap, b = math.abs(yaw), math.abs(pitch), iris.base
        joint_set_pos:call(iris.j, Vector3f.new(b.x + ay * h[1] + ap * v[1], b.y + ay * h[2] + ap * v[2], b.z + ay * h[3] + ap * v[3]))
    end
end

re.on_pre_application_entry("UpdateScene", function()
    if next(face_sets) == nil then return end
    for a, set in pairs(face_sets) do
        local body_ok, stage = false, "body"
        local ok, err = pcall(function()
            if not set.go:call("get_Valid") then error("gone") end
            local j0 = tr_joint_by_hash:call(set.tr, set.h0)
            if j0 == nil or j0:get_address() ~= set.a0 then error("joints rebuilt") end
            body_ok = true
            if not cfg.face then error("option off") end   -- (set_face: put back to rest here, after the checks above)
            if not set.head:call("get_Valid") then error("head gone") end
            local n0 = tr_joint_by_hash:call(set.htr, set.nh)
            if n0 == nil or n0:get_address() ~= set.na then error("head joints rebuilt") end
            stage = "drive"
            drive_face(set)
        end)
        if not ok then
            if body_ok then face_rest(set) end   -- her joints are still there: back to rest until the head is found again
            face_sets[a], face_retry[a] = nil, now() + 3.0
            if stage == "drive" and not face_err_noted[a] then
                face_err_noted[a] = true
                log_info("expressions paused on " .. tostring(set.name) .. " (retrying): " .. tostring(err))
            end
        end
    end
end)

-- Returns is_karin, ready: the body is Karin's mesh; and her look is complete (materials, parts, head, hide mask)
local function upkeep(go, ps)
    local mesh = get_comp(go, mesh_t)
    if mesh == nil or holder_path(mesh:call("getMesh")) ~= MESH_PATH then return false, false end
    if holder_path(mesh:call("get_Material")) ~= MDF_PATH then
        -- her material goes on once the skin-detail steps are done and her resources are usable
        if not (bake_idle(go) and resources_ready()) then return true, false end
        mesh:call("set_Material", R.mdf)
        log_info("Karin's materials on " .. tostring(go:call("get_Name")))
    end
    for i = 0, PARTS - 1 do
        if not mesh:call("getPartsEnable", i) then mesh:call("setPartsEnable", i, true) end
    end
    local hm = get_comp(find_child(go, "head"), mesh_t)
    if hm ~= nil and hm:call("get_Enabled") then hm:call("set_Enabled", false) end
    local masked = false
    if ps ~= nil then
        local pa = ps:get_address()
        live_ps[pa] = true
        local cur = ps:get_field("_HideSwapObjects")
        if cur ~= HIDE_ALL then
            wanted_mask[pa] = { ps = ps, mask = cur }   -- a write the hook did not see: the newest request
            own_mask_write = true
            local ok = pcall(ps.call, ps, "set_HideSwapObjects", HIDE_ALL)
            own_mask_write = false
            masked = ok and pcall(ps.call, ps, "forceUpdateStatusOfSwapObjects")
        else
            masked = true
        end
    end
    local a = go:get_address()
    if touched[a] == nil then
        touched[a] = go
        log_info("Karin on " .. tostring(go:call("get_Name")))
    end
    if rest_pose_ok and rest_sets[a] == nil and now() >= (rest_retry[a] or 0) then
        rest_sets[a] = collect_rest(go)
        if rest_sets[a] ~= nil then
            rest_retry[a] = nil
            log_info(#rest_sets[a].list .. " chain joints held to her rest pose on " .. tostring(go:call("get_Name")))
        else
            rest_retry[a] = now() + 3.0   -- no K_* joints found: look again later
        end
    end
    if face_ok and cfg.face and face_sets[a] == nil and now() >= (face_retry[a] or 0) then
        local set = collect_face(go)
        if not set then
            face_retry[a] = now() + 3.0   -- no expression joints / native head not ready: look again later
        else
            face_sets[a], face_retry[a] = set, nil
            if not face_noted[a] then   -- (a menu model's head is rebuilt a few times while it is built)
                face_noted[a] = true
                local n = {}
                for c, list in pairs(set.chans) do n[#n + 1] = c .. "(" .. #list .. ")" end
                if set.iris then n[#n + 1] = "Iris" end
                table.sort(n)
                log_info("expressions on " .. tostring(go:call("get_Name")) .. ": " .. table.concat(n, " "))
            end
        end
    end
    return true, hm ~= nil and masked and bake_idle(go)
end

-- A character this script had hidden the head / forced the mask of, rebuilt in place without Karin (option turned
-- off, then a rebuild of the same object): give the head and the game's mask back.
local function restore_native(go, ps)
    local a = go:get_address()
    if touched[a] == nil then return end
    local ok = pcall(function()
        local hm = get_comp(find_child(go, "head"), mesh_t)
        if hm == nil or ps == nil then error("head / PartSwapper not there yet") end
        if not hm:call("get_Enabled") then hm:call("set_Enabled", true) end
        local pa = ps:get_address()
        if ps:get_field("_HideSwapObjects") == HIDE_ALL then
            local w = wanted_mask[pa]
            ps:call("set_HideSwapObjects", w and w.mask or 0)
        end
        ps:call("forceUpdateStatusOfSwapObjects")
        wanted_mask[pa] = nil
    end)
    if not ok then return end   -- mid-rebuild: tried again on the next pass
    touched[a] = nil
    log_info("original look back on " .. tostring(go:call("get_Name")))
end

local function scan()
    last_scan = now()
    mockup_list, mockup_face = nil, nil
    pcall(function()
        local sm = sdk.get_native_singleton("via.SceneManager")
        local scene = sdk.call_native_func(sm, sdk.find_type_definition("via.SceneManager"), "get_CurrentScene()")
        mockup_list = scene:call("findComponents(System.Type)", sdk.typeof("app.GUIMenuMockupList")):get_elements()[1]
        mockup_face = scene:call("findComponents(System.Type)", sdk.typeof("app.MockupFace")):get_elements()[1]
    end)
end

local function player_mockups(chara_id)
    local out = {}
    if mockup_list == nil then return out, false end
    local ok = pcall(function()
        if not mockup_list:call("get_Valid") then error("menu model list gone") end
        local list = mockup_list:get_field("ModelList")
        for i = 0, list:call("get_Count") - 1 do
            local md = list:call("get_Item", i)
            if md and md:get_field("CharaId") == chara_id then
                local obj = md:get_field("Obj")
                if obj ~= nil then out[#out + 1] = obj end
            end
        end
    end)
    return out, ok
end

local function pass()
    live_ps = {}
    if not create_resources() then return end
    local cm = sdk.get_managed_singleton("app.CharacterManager")
    local ch = cm and cm:call("get_ManualPlayer")
    -- (while a save unloads the player component is being destroyed; touching it throws inside the game)
    if ch == nil or not ch:call("get_Valid") then
        -- a save is loading: everything keyed by object address belongs to objects that are going away
        status = "waiting for player"
        touched, wanted_mask, portrait_done, proportion_noted = {}, {}, {}, {}
        rest_sets, rest_retry, face_sets, face_retry, face_noted, face_err_noted = {}, {}, {}, {}, {}, {}
        for k in pairs(karin_bakers) do karin_bakers[k] = nil end
        return
    end
    local go = ch:call("get_GameObject")
    local ps = ch:call("get_HumanPartSwapper")
    if upkeep(go, ps) then
        status = cfg.enabled and "Karin" or "Karin until the next load (disabled)"
    else
        rest_sets[go:get_address()], face_sets[go:get_address()] = nil, nil
        restore_native(go, ps)
        status = not cfg.enabled and "disabled"
            or unsupported_note or "original look: Karin appears after loading a save"
    end
    if now() - last_scan > SCAN_SEC then scan() end
    local cid = ch:call("get_CharaID")
    local present = {}
    local models, complete = player_mockups(cid)
    for _, obj in ipairs(models) do
        if not obj:call("get_Valid") then goto next_mockup end
        local a = obj:get_address()
        present[a] = true
        local mps = get_comp(obj, ps_t)
        local karin, ready = upkeep(obj, mps)
        if not karin then
            rest_sets[a], face_sets[a] = nil, nil
            restore_native(obj, mps)
            portrait_done[a] = nil   -- rebuilt as Karin later: take the portrait again
        end
        if ready and not portrait_done[a] and mockup_face and mockup_face:call("get_Valid") then
            -- re-take the portrait once her look is complete (without the old head)
            portrait_done[a] = pcall(mockup_face.call, mockup_face, "reqCapture", cid) or nil
        end
        ::next_mockup::
    end
    if complete then
        for a in pairs(portrait_done) do
            if not present[a] then portrait_done[a] = nil end   -- a later model at the same address is a new one
        end
    end
    local function gone(o)
        local ok, v = pcall(o.call, o, "get_Valid")
        return not (ok and v)
    end
    for a, o in pairs(touched) do
        if gone(o) then touched[a] = nil end
    end
    for a, set in pairs(rest_sets) do
        if gone(set.go) then rest_sets[a] = nil end
    end
    for a, set in pairs(face_sets) do
        if gone(set.go) then face_sets[a] = nil end
    end
    for a, w in pairs(wanted_mask) do
        if gone(w.ps) then wanted_mask[a] = nil end
    end
end

re.on_pre_application_entry("UpdateBehavior", function()
    frame = frame + 1
    if frame % CHECK_EVERY ~= 0 then return end
    local ok, err = pcall(pass)
    if not ok then status = "error: " .. tostring(err) end
end)

-- expressions on / off: unlike the other options this one applies at once. Off: the scene-update callback puts her face
-- back to rest (after its joint checks, in the game's update) and drops the sets; on: upkeep collects them again.
local function set_face(v)
    cfg.face = v
    save_cfg()
    if v then face_retry = {} end
end

re.on_draw_ui(function()
    if imgui.tree_node(MOD .. " " .. VERSION) then
        local changed, v = imgui.checkbox("Enable Karin", cfg.enabled)
        if changed then cfg.enabled = v; save_cfg() end
        local c2, v2 = imgui.checkbox("Hair / cloth physics", cfg.physics)
        if c2 then cfg.physics = v2; save_cfg() end
        local c3, v3 = imgui.checkbox("Also in menus (equipment preview, portrait)", cfg.mockups)
        if c3 then cfg.mockups = v3; save_cfg() end
        imgui.text("Changes take effect when the character is built: load a save.")
        local c4, v4 = imgui.checkbox("Facial expressions (blinks, mouth, eyes; applies at once)", cfg.face)
        if c4 then set_face(v4) end
        imgui.text("status: " .. tostring(status))
        imgui.tree_pop()
    end
end)

-- for other scripts (and testing): KarinReplacer.set_enabled(bool), KarinReplacer.set_option(name, bool),
-- KarinReplacer.status(); like the UI, changes apply at the next character build
KarinReplacer = {
    set_enabled = function(v) cfg.enabled = v == true; save_cfg() end,
    set_option = function(k, v)
        if k == "face" and type(v) == "boolean" then set_face(v); return end
        if k ~= "enabled" and type(cfg[k]) == "boolean" and type(v) == "boolean" then cfg[k] = v; save_cfg() end
    end,
    status = function() return status end,
    debug_refs = function()
        if R == nil then return nil end
        local out = {}
        for _, k in ipairs({ "mesh", "mdf", "chain" }) do
            local ok, n = pcall(function() return R[k]:get_reference_count() end)
            out[k] = ok and n or tostring(n)
        end
        return out
    end,
}

-- last: everything the hand-over relies on must exist in this game version, or Karin is not handed out at all
do
    local function has_field(tn, fname)
        local t = sdk.find_type_definition(tn)
        while t ~= nil do
            if t:get_field(fname) ~= nil then return true end
            t = t:get_parent_type()
        end
        return false
    end
    local ps_td = sdk.find_type_definition("app.PartSwapper")
    local checks = {
        { "PartSwapMeshHolder.swap hook", mesh_hooked }, { "PartSwapMaterialHolder.swap hook", mdf_hooked },
        { "bakingProcessing hook", bake_hooked }, { "MaterialBakerController.build hook", build_hooked },
        { "setupApplyEditScales hook", shape_hooked }, { "BakingProcess names", bake_names_ok },
        { "thread.get_hook_storage", hook_storage ~= nil },
        { "app.Gender.Female / app.Species.Human", GENDER_FEMALE ~= nil and SPECIES_HUMAN ~= nil },
        { "PartSwapper.get_Meta", ps_td ~= nil and ps_td:get_method("get_Meta") ~= nil },
        { "PartSwapMeshHolder._Mesh", has_field("app.PartSwapMeshHolder", "_Mesh") },
        { "PartSwapMaterialHolder._Material", has_field("app.PartSwapMaterialHolder", "_Material") },
        { "BodyDetailEditor fields", has_field("app.BodyDetailEditor", BAKING)
            and has_field("app.BodyDetailEditor", "<BodyMesh>k__BackingField")
            and has_field("app.BodyDetailEditor", "_MaterialBakerController") },
        { "BodyEditor fields", has_field("app.BodyEditor", "_ApplyEditScales")
            and has_field("app.BodyEditor", "<Mesh>k__BackingField") },
        { "MetaData fields", has_field("app.CharacterEditDefine.MetaData", "_Gender")
            and has_field("app.CharacterEditDefine.MetaData", "_Species") },
    }
    local all_ok = true
    for _, c in ipairs(checks) do
        if not c[2] then
            all_ok = false
            log_info("missing in this game version: " .. c[1] .. " -- Karin will not be applied")
        end
    end
    guard_ok = all_ok
end

create_resources()
log_info("loaded " .. VERSION)
