# UE 5.7 editor Python (headless): import a build_pt.py run (Karin_PicodraTech) into its copy of the PBZ mod project.
# Fork of the Karin_Original script: textures and material instances from the run's materials.json.
#   UnrealEditor-Cmd ProjectPBZ.uproject -run=pythonscript -script="ue_import_pbz.py <run_dir>"
#
# Real assets (packaged; game paths):
#   /HuaShira/Characters/Hero/Hero_Hun/Hun_Invs                                 leader (every bone, Karin proportions)
#   /HuaShira/Characters/Hero/Hero_Hun/SkinParts/Hun_Body_Simple                 body
#   /HuaShira/Characters/Hero/Hero_Hun/SkinParts/Hun_Head_New                    face (CTRL_expressions_* morphs) from Karin_Head.fbx
#                                                                                (adult: second section, behind a hidden first one), else hidden
#   /HuaShira/Characters/Hero/Hero_Hun/SkinParts/Hun_BrowLashCard                face from Karin_Face.fbx (lash card component: child
#                                                                                of the head; the cutscene actors hide it), else hidden;
#                                                                                neither FBX: the face is part of the body. Adult: both,
#                                                                                the head's copy scaled to 90%, restored by its
#                                                                                KarinFaceShow morph
#   /HuaShira/Characters/Hero/Hero_Hun/SkinParts/{Hun_Cloth,Hun_Scarf,Hun_Hair_Band}, Hats/Hun_Hat_00   hidden
#   /HuaShira/Characters/Hero/Hero_Hun/SkinParts/Cloth/CA_Hun_{UpperCloth,Skirt,Cape,Hair01}   hidden mesh under the cloth
#   /HuaShira/Characters/Hero/Hero_Hun_Climax/SkinParts/Hun_Body_Climax   <- Karin_Body.fbx (body of BP_Renewal_Hun_Climax)
#   ... and the "10 years ago" outfit (HunBodyClimax): CA_Hun_{UpperCloth,Skirt,Cape}_Climax, Hun_Scarf_Climax, Hats/Hun_Hat_01
#       asset names (wrong class for the game's UChaosClothAsset loads, so no cloth component gets an asset)
#   /HuaShira/Characters/Hero/Hero_Hun/SkinParts/Hun_Cloth_Streamer_Physics      RigidBody override PA of ABP_Hun_PostProcess
#   /HuaShira/Mods/KarinPBZ/**                                                    textures, material instances
# Dummies (never packaged; the game has the real ones): Hun_Skin_Skeleton, Hats/Hun_Hat_Skeleton, PA_Hun,
#   Hero_Hun_PhysicsAsset, Rig/ABP_Hun_PostProcess, parent material instances under /Game/PBZContent/...
import unreal, sys, os, json

args = [a for a in sys.argv[1:] if not a.startswith("-")]
RUN = args[0].replace("\\", "/")
L = lambda *a: unreal.log("[PBZ] " + " ".join(str(x) for x in a))
eal = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
mel = unreal.MaterialEditingLibrary
lib = unreal.PBZModToolsLibrary
unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
unreal.AssetRegistryHelpers.get_asset_registry().search_all_assets(True)   # headless runs start before the scan ends

HUN = "/HuaShira/Characters/Hero/Hero_Hun"
SKEL = HUN + "/Hun_Skin_Skeleton"
HAT_SKEL = HUN + "/Hats/Hun_Hat_Skeleton"
MOD = "/HuaShira/Mods/KarinPBZ"
PARENT_SKIN = "/Game/PBZContent/Characters/Hero/Hun_New_V2b/Material/MI_ZeroHun_Head_b"
PARENT_CLOTH = "/Game/PBZContent/Characters/Hero/Hun_New_V2b/Material/MI_ZeroHun_Cloth_02_b"
# materials of the run (build_pt.py): MI -> base color texture and kind, and the cloth slots' aliases
SPEC = json.load(open(RUN + "/materials.json", encoding="utf-8"))

def _set(obj, name, value):
    try:
        obj.set_editor_property(name, value)
    except Exception as ex:
        L("WARN option", name, ex)

def import_mesh(path, dest_dir, name, skeleton=None, morphs=False):
    full = dest_dir + "/" + name
    if eal.does_asset_exist(full):
        eal.delete_asset(full)
    o = unreal.FbxImportUI()
    for k, v in (("import_mesh", True), ("import_as_skeletal", True), ("mesh_type_to_import", unreal.FBXImportType.FBXIT_SKELETAL_MESH),
                 ("import_materials", False), ("import_textures", False), ("import_animations", False),
                 ("create_physics_asset", False), ("automated_import_should_detect_type", False)):
        _set(o, k, v)
    if skeleton:
        _set(o, "skeleton", skeleton)
    sm = o.get_editor_property("skeletal_mesh_import_data")
    for k, v in (("import_morph_targets", morphs), ("normal_import_method", unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS),
                 ("use_t0_as_ref_pose", False), ("preserve_smoothing_groups", True), ("convert_scene", True),
                 ("force_front_x_axis", False), ("convert_scene_unit", False), ("import_uniform_scale", 1.0),
                 ("update_skeleton_reference_pose", False), ("import_meshes_in_bone_hierarchy", True)):
        _set(sm, k, v)
    t = unreal.AssetImportTask()
    t.filename = path; t.destination_path = dest_dir; t.destination_name = name
    t.replace_existing = True; t.automated = True; t.save = False; t.options = o
    tools.import_asset_tasks([t])
    m = unreal.load_asset(full)
    assert m, "import failed: " + full
    L("imported", full, list(t.imported_object_paths))
    return m, list(t.imported_object_paths)

def move(src, dst):
    if src == dst: return
    if eal.does_asset_exist(dst): eal.delete_asset(dst)
    L("rename", src, "->", dst, eal.rename_asset(src, dst))

def ensure_skeleton(fbx, dest_dir, mesh_name, skel_path):
    """Import the mesh; on the first run the importer creates <mesh>_Skeleton, which is moved to the game path."""
    skel = unreal.load_asset(skel_path) if eal.does_asset_exist(skel_path) else None
    mesh, paths = import_mesh(fbx, dest_dir, mesh_name, skeleton=skel)
    if skel is None:
        for p in eal.list_assets(dest_dir, recursive=False):
            p = p.split(".")[0]
            if p.endswith("_Skeleton"):
                move(p, skel_path)
        skel = unreal.load_asset(skel_path)
        mesh = unreal.load_asset(dest_dir + "/" + mesh_name)
    assert skel, "no skeleton " + skel_path
    return mesh, skel

# ---------------------------------------------------------------- skeletons + meshes
leader, skel = ensure_skeleton(RUN + "/Karin_Leader.fbx", HUN, "Hun_Invs", SKEL)
# face mesh: Karin_Head.fbx -> Hun_Head_New, Karin_Face.fbx -> Hun_BrowLashCard, neither -> part of the body (the leader:
# no blinking in gameplay)
FACE_FBX = next((n for n in ("Karin_Head", "Karin_Face") if os.path.exists(RUN + "/" + n + ".fbx")), None)
body, _ = import_mesh(RUN + "/Karin_Body.fbx", HUN + "/SkinParts", "Hun_Body_Simple", skeleton=skel, morphs=FACE_FBX is None)
head, _ = import_mesh(RUN + ("/Karin_Head.fbx" if FACE_FBX == "Karin_Head" else "/Empty.fbx"), HUN + "/SkinParts", "Hun_Head_New",
                     skeleton=skel, morphs=FACE_FBX == "Karin_Head")
lash = None
if os.path.exists(RUN + "/Karin_Face.fbx"):
    if eal.does_asset_exist(HUN + "/SkinParts/Hun_BrowLashCard"): eal.delete_asset(HUN + "/SkinParts/Hun_BrowLashCard")
    lash, _ = import_mesh(RUN + "/Karin_Face.fbx", HUN + "/SkinParts", "Hun_BrowLashCard", skeleton=skel, morphs=True)
faces = [m for m in (head if FACE_FBX == "Karin_Head" else None, lash) if m] or [body]
empty, _ = import_mesh(RUN + "/Empty.fbx", HUN + "/SkinParts", "Hun_Cloth", skeleton=skel)
hat, hat_skel = ensure_skeleton(RUN + "/Hat_Empty.fbx", HUN + "/Hats", "Hun_Hat_00", HAT_SKEL)
L("bones leader", len(json.loads(lib.dump_ref_skeleton(leader))), "body", len(json.loads(lib.dump_ref_skeleton(body))),
  "head", len(json.loads(lib.dump_ref_skeleton(head))))

# ---------------------------------------------------------------- dummies for game-owned assets
def dummy_pa(path):
    d, n = path.rsplit("/", 1)
    pa = lib.create_physics_asset(d, n, None)
    eal.save_loaded_asset(pa)
    return pa
pa_hun = dummy_pa(HUN + "/PA_Hun")
pa_hero = dummy_pa(HUN + "/Hero_Hun_PhysicsAsset")
abp_path = HUN + "/Rig/ABP_Hun_PostProcess"
if not eal.does_asset_exist(abp_path):
    fac = unreal.AnimBlueprintFactory()
    fac.set_editor_property("target_skeleton", skel)
    fac.set_editor_property("parent_class", unreal.AnimInstance)
    tools.create_asset("ABP_Hun_PostProcess", HUN + "/Rig", unreal.AnimBlueprint, fac)
    eal.save_asset(abp_path)
abp_class = eal.load_blueprint_class(abp_path)
L("dummy abp class", abp_class.get_path_name() if abp_class else None)

# ---------------------------------------------------------------- textures
def import_texture(png, name, srgb=True, normal=False):
    dest = MOD + "/Textures"
    full = dest + "/" + name
    t = unreal.AssetImportTask()
    t.filename = png; t.destination_path = dest; t.destination_name = name
    t.replace_existing = True; t.automated = True; t.save = False
    t.factory = unreal.TextureFactory()
    tools.import_asset_tasks([t])
    tex = unreal.load_asset(full)
    assert tex, "texture import failed: " + png
    tex.set_editor_property("srgb", srgb)
    if normal:
        tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
    elif not srgb:
        tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
    tex.set_editor_property("virtual_texture_streaming", False)
    eal.save_loaded_asset(tex)
    return tex

TEX = {}
for n in sorted({m["texture"] for m in SPEC["materials"].values()}):
    TEX[n] = import_texture(RUN + "/textures/" + n + ".png", "T_" + n)
for n, srgb, normal in (("Karin_FlatN", False, True), ("Karin_ARM", False, False), ("Karin_Gray", True, False),
                        ("Karin_SCMT", False, False)):
    TEX[n] = import_texture(RUN + "/textures/" + n + ".png", "T_" + n, srgb, normal)

# ---------------------------------------------------------------- dummy parents (game paths) + material instances
ST = unreal.MaterialSamplerType
DUMMY_MASTER = "/Game/PBZContent/Mods/M_KarinDummyMaster"
PARAMS = [("Albedo", "Karin_SkinFace", ST.SAMPLERTYPE_COLOR), ("Normal", "Karin_FlatN", ST.SAMPLERTYPE_NORMAL),
          ("Mix", "Karin_ARM", ST.SAMPLERTYPE_MASKS), ("SCMT_Map", "Karin_SCMT", ST.SAMPLERTYPE_MASKS),
          ("SkinNormal_MICRO", "Karin_FlatN", ST.SAMPLERTYPE_NORMAL), ("DetailColor", "Karin_Gray", ST.SAMPLERTYPE_COLOR),
          ("DetailNormal (NonVT)", "Karin_FlatN", ST.SAMPLERTYPE_NORMAL), ("DetailNormal(VT)", "Karin_FlatN", ST.SAMPLERTYPE_NORMAL)]
SCALARS = ["BaseColor Intensity", "SkinMicroNormalIntensity", "NormalIntensity", "ColorTiling", "NormalTiling"]
def dummy_master():
    if eal.does_asset_exist(DUMMY_MASTER):
        eal.delete_asset(DUMMY_MASTER)
    d, n = DUMMY_MASTER.rsplit("/", 1)
    mat = tools.create_asset(n, d, unreal.Material, unreal.MaterialFactoryNew())
    acc, acc_out = None, ""
    for i, (pname, tname, st) in enumerate(PARAMS):
        e = mel.create_material_expression(mat, unreal.MaterialExpressionTextureSampleParameter2D, -800, i * 220)
        e.set_editor_property("parameter_name", pname)
        e.set_editor_property("texture", TEX[tname])
        e.set_editor_property("sampler_type", st)
        if acc is None:
            acc = e; acc_out = "RGB"
        else:
            a = mel.create_material_expression(mat, unreal.MaterialExpressionAdd, -400, i * 220)
            mel.connect_material_expressions(acc, acc_out, a, "A")
            mel.connect_material_expressions(e, "RGB", a, "B")
            acc = a; acc_out = ""
    for j, sname in enumerate(SCALARS):
        s = mel.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, -800, (len(PARAMS) + j) * 220)
        s.set_editor_property("parameter_name", sname)
        s.set_editor_property("default_value", 1.0)
        a = mel.create_material_expression(mat, unreal.MaterialExpressionAdd, -400, (len(PARAMS) + j) * 220)
        mel.connect_material_expressions(acc, acc_out, a, "A")
        mel.connect_material_expressions(s, "", a, "B")
        acc = a; acc_out = ""
    mel.connect_material_property(acc, acc_out, unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mel.recompile_material(mat)
    eal.save_loaded_asset(mat)
    return mat
master = dummy_master()
for pp in (PARENT_SKIN, PARENT_CLOTH):
    if eal.does_asset_exist(pp):
        eal.delete_asset(pp)
    d, n = pp.rsplit("/", 1)
    mic = tools.create_asset(n, d, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    mel.set_material_instance_parent(mic, master)
    eal.save_loaded_asset(mic)

def make_mi(name, parent_path, textures, scalars):
    full = MOD + "/Materials/" + name
    mi = unreal.load_asset(full)
    if mi is None:
        mi = tools.create_asset(name, MOD + "/Materials", unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    assert mi, "MI creation failed: " + full
    mel.set_material_instance_parent(mi, unreal.load_asset(parent_path))
    for p, tname in textures.items():
        mel.set_material_instance_texture_parameter_value(mi, p, TEX[tname])
        if mel.get_material_instance_texture_parameter_value(mi, p) != TEX[tname]: L("WARN texture param", name, p)
    for p, v in scalars.items():
        if not mel.set_material_instance_scalar_parameter_value(mi, p, float(v)): L("WARN scalar param", name, p)
    mel.update_material_instance(mi)
    eal.save_loaded_asset(mi)
    return mi
SKIN_TEX = {"Normal": "Karin_FlatN", "Mix": "Karin_ARM", "SCMT_Map": "Karin_SCMT", "SkinNormal_MICRO": "Karin_FlatN"}
CLOTH_TEX = {"Normal": "Karin_FlatN", "Mix": "Karin_ARM", "DetailColor": "Karin_Gray", "DetailNormal (NonVT)": "Karin_FlatN",
             "DetailNormal(VT)": "Karin_FlatN"}
def skinlike(m): return m["kind"] in ("skin", "face")
MIS = {name: make_mi(name, PARENT_SKIN if skinlike(m) else PARENT_CLOTH, dict(SKIN_TEX if skinlike(m) else CLOTH_TEX, Albedo=m["texture"]),
                     {"SkinMicroNormalIntensity": 0.0} if skinlike(m) else {"BaseColor Intensity": 1.0, "NormalIntensity": 0.0})
       for name, m in SPEC["materials"].items()}
MIS.update({a: MIS[b] for a, b in SPEC["alias"].items()})

def assign(mesh, default=None):
    out = []
    for m in mesh.get_editor_property("materials"):
        slot = str(m.get_editor_property("material_slot_name"))
        mi = MIS.get(slot) or (MIS.get(default) if default else None)
        if mi is None: L("WARN no MI for slot", slot)
        else: m.set_editor_property("material_interface", mi)
        out.append(m)
    mesh.set_editor_property("materials", out)
    L("materials", mesh.get_name(), [(str(m.get_editor_property("material_slot_name")),
                                      m.get_editor_property("material_interface").get_name() if m.get_editor_property("material_interface") else None) for m in out])

assign(body); assign(head, "MI_Karin_Skin"); assign(leader, "MI_Karin_Skin"); assign(empty, "MI_Karin_Skin"); assign(hat, "MI_Karin_Skin")
if lash: assign(lash, "MI_Karin_Skin")
lib.set_mesh_physics_asset(leader, pa_hero); lib.set_post_process_anim_blueprint(leader, abp_class)
lib.set_mesh_physics_asset(body, pa_hun); lib.set_post_process_anim_blueprint(body, abp_class)
for m in (head, empty, hat, lash):
    if m is None: continue
    lib.set_mesh_physics_asset(m, None); lib.set_post_process_anim_blueprint(m, None)
# face morph curves: the head copies curves from the leader and plays face montages; flag the CTRL curves as morphs
for face in faces:
    morphs = list(lib.get_morph_target_names(face))
    L("face morphs on", face.get_name(), len(morphs), morphs[:6])
    L("curve meta", lib.set_morph_curve_meta_data(face, morphs))
# the "10 years ago" player (BP_Renewal_Hun_Climax, right after the prologue) has its own body mesh: the same Karin body
CLIMAX_BODY = "/HuaShira/Characters/Hero/Hero_Hun_Climax/SkinParts/Hun_Body_Climax"
if eal.does_asset_exist(CLIMAX_BODY): eal.delete_asset(CLIMAX_BODY)
climax = eal.duplicate_asset(HUN + "/SkinParts/Hun_Body_Simple", CLIMAX_BODY)
lib.set_mesh_physics_asset(climax, pa_hero)


# ---------------------------------------------------------------- hidden copies
for n in ("Hun_Scarf", "Hun_Scarf_Climax", "Hun_Hair_Band") + (() if lash else ("Hun_BrowLashCard",)):
    p = HUN + "/SkinParts/" + n
    if eal.does_asset_exist(p): eal.delete_asset(p)
    eal.duplicate_asset(HUN + "/SkinParts/Hun_Cloth", p)
for n in ("CA_Hun_UpperCloth", "CA_Hun_Skirt", "CA_Hun_Cape", "CA_Hun_Hair01",
          "CA_Hun_UpperCloth_Climax", "CA_Hun_Skirt_Climax", "CA_Hun_Cape_Climax"):
    p = HUN + "/SkinParts/Cloth/" + n
    if eal.does_asset_exist(p): eal.delete_asset(p)
    eal.duplicate_asset(HUN + "/SkinParts/Hun_Cloth", p)
if eal.does_asset_exist(HUN + "/Hats/Hun_Hat_01"): eal.delete_asset(HUN + "/Hats/Hun_Hat_01")
eal.duplicate_asset(HUN + "/Hats/Hun_Hat_00", HUN + "/Hats/Hun_Hat_01")

# ---------------------------------------------------------------- chain physics (override PA of the game's RigidBody node)
# (only for builds with chains; the cloth builds keep the game's PA and ship no replacement)
pa = None
if os.path.exists(RUN + "/physics.json"):
    phys = json.load(open(RUN + "/physics.json", encoding="utf-8"))
    pa_path = HUN + "/SkinParts/Hun_Cloth_Streamer_Physics"
    if eal.does_asset_exist(pa_path): eal.delete_asset(pa_path)
    pa = lib.create_physics_asset(HUN + "/SkinParts", "Hun_Cloth_Streamer_Physics", body)
    L("streamer PA", lib.build_physics_asset(pa, body, json.dumps(phys)))

for a in (leader, body, climax, head, empty, hat, lash, pa):
    if a is None: continue
    eal.save_loaded_asset(a)
unreal.EditorAssetLibrary.save_directory("/HuaShira", only_if_is_dirty=True, recursive=True)
unreal.EditorAssetLibrary.save_directory("/Game", only_if_is_dirty=True, recursive=True)
L("IMPORT_OK")
