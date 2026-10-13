# UE 4.26 editor python (commandlet): build the Karin replacement for /Game/Characters/MainChar/W/Meshes/SK_W_MainChar_01.
# Args (py_args.json): [build_json]
#   build_json: {"fbx":..., "textures": {"T_Karin_Face_C": "png", ...}, "materials": {slot: {"parent": "skin|cloth",
#                "BaseColor": tex, "ComboMap": tex, "Normal": tex, "vectors": {...}, "scalars": {...}}},
#                "cloth_json": ..., "out_json": ..., "physics_only": false}
# Game-owned assets (master materials, physics assets) are created as placeholders at the game paths and must be
# excluded from the pak.
import json
import os
import unreal

# ue_run.ps1 writes the arguments to py_args.json and passes its path in SIFU_PY_ARGS.
ARGS = json.load(open(os.environ["SIFU_PY_ARGS"], encoding="utf-8-sig"))
CFG = json.load(open(ARGS[0], encoding="utf-8"))
eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
lib = unreal.SifuModToolsLibrary
OUT = {"log": []}

MESH_DIR = "/Game/Characters/MainChar/W/Meshes"
# each model has its own folder (Karin_Original: "Karin"), so paks of different models never share asset paths
KARIN_DIR = "/Game/Characters/MainChar/W/" + CFG.get("asset_dir", "Karin")
MASTERS = {
    "skin": ("/Game/Characters/_Shared/Materials/Master", "M_CharaMaster_Skin", ["BaseColor", "ComboMap", "Normal"], ["SSS_Color"], False, False),
    "cloth": ("/Game/Characters/_Shared/Materials/Master", "M_CharaMaster_Cloth", ["BaseColor", "ComboMap", "Normal"], [], True, True),
    "skin_dyn": ("/Game/Characters/_Shared/Materials/MainChar", "M_CharaMaster_Skin_Dyn",
                 ["BaseColor", "ComboMap", "Aging_Normal_A", "Aging_Normal_B", "Color_Old", "Aging_Mask"], ["SSS_Color", "Hair_Dark", "Hair_Light"], False, False),
    "cloth_dyn": ("/Game/Characters/_Shared/Materials/MainChar", "M_CharaMaster_Cloth_Dyn",
                  ["BaseColor", "ComboMap", "Normal", "Aging | AlphaGrid"], ["Snow_Color"], True, True),
}
# The W default-outfit material instances (game-owned): parenting to them inherits their static switches
# (IsMainChar/ClothAging off etc.) so Karin renders through exactly the W material permutations.
PARENT_MI = {
    "w_head": ("/Game/Characters/MainChar/W/Materials", "MI_MainChar_W_Head_Dyn", "skin_dyn"),
    "w_body": ("/Game/Characters/MainChar/W/Materials", "MI_MainChar_W_20_Body", "skin_dyn"),
    "w_cloth": ("/Game/Characters/MainChar/W/Materials", "MI_MainChar_W_BasicOutfit", "cloth_dyn"),
}
PLACEHOLDER_PA = [("/Game/Characters/MainChar/M/Meshes/PhysicAssets", "PA_W_MainChar"),
                  ("/Game/Characters/MainChar/M/Meshes/PhysicAssets", "PA_M_MainChar_ShadowCapsules")]


def log(*a):
    s = " ".join(str(x) for x in a)
    OUT["log"].append(s)
    unreal.log("SIFU " + s)


def placeholder_master(kind):
    path, name, texs, vecs, two_sided, cloth = MASTERS[kind]
    full = path + "/" + name
    if eal.does_asset_exist(full):
        return eal.load_asset(full)
    m = tools.create_asset(name, path, unreal.Material, unreal.MaterialFactoryNew())
    y = 0
    for p in texs:
        e = mel.create_material_expression(m, unreal.MaterialExpressionTextureSampleParameter2D, -500, y)
        e.set_editor_property("parameter_name", p)
        if p == "Normal":
            e.set_editor_property("texture", unreal.load_asset("/Engine/EngineMaterials/DefaultNormal"))
            e.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
            mel.connect_material_property(e, "RGB", unreal.MaterialProperty.MP_NORMAL)
        elif p == "BaseColor":
            mel.connect_material_property(e, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
        elif p == "ComboMap":
            e.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
            mel.connect_material_property(e, "R", unreal.MaterialProperty.MP_ROUGHNESS)
        y += 260
    for p in vecs:
        e = mel.create_material_expression(m, unreal.MaterialExpressionVectorParameter, -500, y)
        e.set_editor_property("parameter_name", p)
        y += 160
    m.set_editor_property("two_sided", two_sided)
    m.set_editor_property("used_with_skeletal_mesh", True)
    if cloth:
        m.set_editor_property("used_with_clothing", True)
    mel.recompile_material(m)
    eal.save_loaded_asset(m)
    log("placeholder master", full)
    return m


def import_texture(name, png, kind, dest=None):
    dest = dest or (KARIN_DIR + "/Textures")
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", png)
    task.set_editor_property("destination_path", dest)
    task.set_editor_property("destination_name", name)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", False)
    tools.import_asset_tasks([task])
    t = eal.load_asset(dest + "/" + name)
    if kind == "color":
        t.set_editor_property("srgb", True)
        t.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_BC7)
    elif kind == "dxt":
        t.set_editor_property("srgb", True)
        t.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_DEFAULT)
    elif kind == "normal":
        t.set_editor_property("srgb", False)
        t.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
    else:  # masks / combo map
        t.set_editor_property("srgb", False)
        t.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
    t.set_editor_property("lod_group", unreal.TextureGroup.TEXTUREGROUP_CHARACTER)
    eal.save_loaded_asset(t)
    return t


def placeholder_parent(kind):
    if kind in MASTERS:
        return placeholder_master(kind)
    path, name, master = PARENT_MI[kind]
    full = path + "/" + name
    if eal.does_asset_exist(full):
        return eal.load_asset(full)
    mi = tools.create_asset(name, path, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    mel.set_material_instance_parent(mi, placeholder_master(master))
    eal.save_loaded_asset(mi)
    log("placeholder parent MI", full)
    return mi


def make_mic(slot, spec, textures):
    parent = placeholder_parent(spec["parent"])
    name = "MI_Karin_" + slot.replace("Karin_", "")
    dest = KARIN_DIR + "/Materials"
    full = dest + "/" + name
    if eal.does_asset_exist(full):
        eal.delete_asset(full)
    mic = tools.create_asset(name, dest, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    mel.set_material_instance_parent(mic, parent)
    for p, t in spec.get("textures", {}).items():
        mel.set_material_instance_texture_parameter_value(mic, p, textures[t])
    for p in ("BaseColor", "ComboMap", "Normal"):
        if spec.get(p):
            mel.set_material_instance_texture_parameter_value(mic, p, textures[spec[p]])
    for p, v in spec.get("vectors", {}).items():
        mel.set_material_instance_vector_parameter_value(mic, p, unreal.LinearColor(*v))
    for p, v in spec.get("scalars", {}).items():
        mel.set_material_instance_scalar_parameter_value(mic, p, v)
    eal.save_loaded_asset(mic)
    return mic


def build_materials():
    textures = {}
    for name, spec in CFG["textures"].items():
        png, kind = spec[0], spec[1]
        textures[name] = import_texture(name, png, kind, spec[2] if len(spec) > 2 else None)  # 3rd = game path (placeholder)
    log("textures", len(textures))
    mics = {}
    for slot, spec in CFG["materials"].items():
        if "same_as" not in spec:
            mics[slot] = make_mic(slot, spec, textures)
    for slot, spec in CFG["materials"].items():
        if "same_as" in spec:
            mics[slot] = mics[spec["same_as"]]
    log("mics", list(mics))
    return mics


def import_mesh(target, skeleton, mics, pas):
    if eal.does_asset_exist(target):
        eal.delete_asset(target)
    ui = unreal.FbxImportUI()
    ui.set_editor_property("import_mesh", True)
    ui.set_editor_property("import_as_skeletal", True)
    ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_SKELETAL_MESH)
    ui.set_editor_property("skeleton", skeleton)
    ui.set_editor_property("import_materials", False)
    ui.set_editor_property("import_textures", False)
    ui.set_editor_property("import_animations", False)
    ui.set_editor_property("create_physics_asset", False)
    sk = ui.get_editor_property("skeletal_mesh_import_data")
    sk.set_editor_property("convert_scene", True)
    sk.set_editor_property("force_front_x_axis", False)
    sk.set_editor_property("import_uniform_scale", 1.0)
    sk.set_editor_property("use_t0_as_ref_pose", False)
    sk.set_editor_property("update_skeleton_reference_pose", False)
    sk.set_editor_property("import_morph_targets", False)
    sk.set_editor_property("preserve_smoothing_groups", True)
    sk.set_editor_property("import_meshes_in_bone_hierarchy", True)
    sk.set_editor_property("normal_import_method", unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
    sk.set_editor_property("vertex_color_import_option", unreal.VertexColorImportOption.REPLACE)
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", CFG["fbx"])
    task.set_editor_property("destination_path", MESH_DIR)
    task.set_editor_property("destination_name", "SK_W_MainChar_01")
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", False)
    task.set_editor_property("options", ui)
    tools.import_asset_tasks([task])
    mesh = eal.load_asset(target)
    if mesh is None:
        raise RuntimeError("mesh import failed")

    # NB: unreal.Array returns struct copies; build a new list or the assignment is silently lost.
    new_mats = []
    for m in mesh.get_editor_property("materials"):
        slot = str(m.get_editor_property("material_slot_name"))
        key = slot if slot in mics else ("Karin_Costume" if slot.startswith("Proxy_") else None)
        if key:
            m.set_editor_property("material_interface", mics[key])
        else:
            log("WARNING slot without material", slot)
        new_mats.append(m)
    mesh.set_editor_property("materials", new_mats)
    assigned = [str(m.get_editor_property("material_interface").get_name()) if m.get_editor_property("material_interface") else None
                for m in mesh.get_editor_property("materials")]
    log("materials assigned", assigned)
    if any(a is None for a in assigned):
        raise RuntimeError("material assignment failed")
    mesh.set_editor_property("physics_asset", pas["PA_W_MainChar"])
    mesh.set_editor_property("shadow_physics_asset", pas["PA_M_MainChar_ShadowCapsules"])
    eal.save_loaded_asset(mesh)
    return mesh


def build_cloth(mesh, cloth):
    """Collision physics asset + proxy clothing."""
    pa = lib.create_physics_asset(KARIN_DIR + "/Physics", "PA_Karin_Cloth", mesh)
    log("cloth PA", lib.build_physics_asset(pa, mesh, json.dumps(cloth["physics"])))
    eal.save_loaded_asset(pa)
    for c in cloth["cloth"]:
        r = lib.create_cloth_proxy(mesh, c["proxy_slot"], c["render_slot"], c["name"], pa, c["max_distance"], False, json.dumps(c["config"]),
                                   c.get("backstop_scale", 0.0))
        log("cloth", c["name"], r)
    eal.save_loaded_asset(mesh)


def build_dynamics(mesh, skeleton, cloth):
    """Bone-chain physics asset + post-process anim blueprint with the RigidBody node."""
    dyn = lib.create_physics_asset(KARIN_DIR + "/Physics", "PA_Karin_Dynamics", mesh)
    log("dyn PA", lib.build_physics_asset(dyn, mesh, json.dumps(cloth["dynamics"])))
    eal.save_loaded_asset(dyn)
    abp_path = KARIN_DIR + "/Anim/ABP_Karin_PostProcess"
    if eal.does_asset_exist(abp_path):
        abp = eal.load_asset(abp_path)
    else:
        fac = unreal.AnimBlueprintFactory()
        fac.set_editor_property("target_skeleton", skeleton)
        fac.set_editor_property("parent_class", unreal.AnimInstance)
        abp = tools.create_asset("ABP_Karin_PostProcess", KARIN_DIR + "/Anim", unreal.AnimBlueprint, fac)
    rb = dict(cloth["rigidbody"])
    rb["OverridePhysicsAsset"] = dyn.get_path_name()
    log("abp", lib.setup_rigid_body_post_process(abp, json.dumps(rb)))
    eal.save_loaded_asset(abp)
    lib.set_post_process_anim_blueprint(mesh, eal.load_blueprint_class(abp_path))
    eal.save_loaded_asset(mesh)


# physics_only: keep the imported mesh, materials and cloth; rebuild only PA_Karin_Dynamics + the post-process ABP.
target = MESH_DIR + "/SK_W_MainChar_01"
skeleton = eal.load_asset("/Game/Characters/Skeleton/Base_skeleton")
cloth = json.load(open(CFG["cloth_json"], encoding="utf-8")) if CFG.get("cloth_json") else {}
if CFG.get("physics_only"):
    mesh = eal.load_asset(target)
    if mesh is None:
        raise RuntimeError("physics_only needs an existing " + target)
else:
    # placeholders for game-owned physics assets
    pas = {}
    for path, name in PLACEHOLDER_PA:
        pas[name] = lib.create_physics_asset(path, name, None)
        eal.save_loaded_asset(pas[name])
    mesh = import_mesh(target, skeleton, build_materials(), pas)
    if cloth.get("cloth"):
        build_cloth(mesh, cloth)
if cloth.get("dynamics"):
    build_dynamics(mesh, skeleton, cloth)

OUT["skeleton"] = mesh.get_editor_property("skeleton").get_path_name()
OUT["bones"] = json.loads(lib.dump_ref_skeleton(mesh))
OUT["sections"] = json.loads(lib.dump_sections(mesh))
OUT["slots"] = [str(m.get_editor_property("material_slot_name")) for m in mesh.get_editor_property("materials")]
open(CFG["out_json"], "w").write(json.dumps(OUT))
unreal.log("BUILD_MESH_DONE")
