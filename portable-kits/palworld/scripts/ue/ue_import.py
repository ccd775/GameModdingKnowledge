# UE 5.1 editor Python (run with -run=pythonscript): import a build_pal.py run into the Pal authoring project.
#   UnrealEditor-Cmd Pal.uproject -run=pythonscript -script="<PAL_WORK_ROOT>/scripts/ue_import.py <PAL_WORK_ROOT>/builds/<run>"
#   (or tools/run_py.ps1 <PAL_WORK_ROOT>/scripts/ue_import.py <PAL_WORK_ROOT>/builds/<run> <log>)
#
# Real assets (packaged):
#   /Game/Pal/Model/Character/Player/Outfit/SK_Player_Female_Outfit_OldCloth001/SK_Player_Female_Outfit_OldCloth001  (body)
#   /Game/Pal/Model/Character/Player/Head/HeadNNN/SK_Player_Female_HeadNNN                                         (face)
#   /Game/Pal/Model/Character/Player/Hair/HairNNN/SK_Player_HairNNN                                                (hidden)
#   /Game/Mods/KarinPal/**                                                                                         (MIs, textures)
# Dummies (never packaged; the game has the real ones at the same paths):
#   /Game/Pal/Model/Character/Skeleton/Human/SK_PalHuman_Skeleton, .../Body/Female/SK_Player_Female_PhysicsAsset,
#   parent materials under /Game/Pal/Material/Character/Common, /Game/Pal/Blueprint/Character/Player/Female/ALI_HumanCloth
import unreal, sys, os, json

args = [a for a in sys.argv[1:] if not a.startswith("-")]
RUN = args[0].replace("\\", "/")
CFG = json.load(open(os.path.join(RUN, "ue_config.json"), encoding="utf-8"))
L = lambda *a: unreal.log("[KARIN] " + " ".join(str(x) for x in a))
eal = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()

SKEL = "/Game/Pal/Model/Character/Skeleton/Human/SK_PalHuman_Skeleton"
PHYS = "/Game/Pal/Model/Character/Player/Body/Female/SK_Player_Female_PhysicsAsset"
BODY_DIR = "/Game/Pal/Model/Character/Player/Outfit/SK_Player_Female_Outfit_OldCloth001"
BODY = BODY_DIR + "/SK_Player_Female_Outfit_OldCloth001"
MOD = "/Game/Mods/KarinPal"


def _set(obj, name, value):
    try:
        obj.set_editor_property(name, value)
    except Exception as ex:
        L("WARN option", name, ex)

def fbx_task(path, dest_dir, name, skeleton=None, morphs=True, physics=False):
    o = unreal.FbxImportUI()
    for k, v in (("import_mesh", True), ("import_as_skeletal", True),
                 ("mesh_type_to_import", unreal.FBXImportType.FBXIT_SKELETAL_MESH), ("import_materials", False),
                 ("import_textures", False), ("import_animations", False), ("create_physics_asset", physics),
                 ("automated_import_should_detect_type", False)):
        _set(o, k, v)
    if skeleton:
        _set(o, "skeleton", skeleton)
    sm = o.get_editor_property("skeletal_mesh_import_data")
    for k, v in (("import_morph_targets", morphs),
                 ("normal_import_method", unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS),
                 ("normal_generation_method", unreal.FBXNormalGenerationMethod.MIKK_T_SPACE),
                 ("use_t0_as_ref_pose", False), ("preserve_smoothing_groups", True), ("convert_scene", True),
                 ("force_front_x_axis", False), ("convert_scene_unit", False), ("import_uniform_scale", 1.0),
                 ("update_skeleton_reference_pose", False)):
        _set(sm, k, v)
    t = unreal.AssetImportTask()
    t.filename = path
    t.destination_path = dest_dir
    t.destination_name = name
    t.replace_existing = True
    t.automated = True
    t.save = False
    t.options = o
    return t


def import_mesh(path, dest_dir, name, skeleton=None, morphs=True, physics=False):
    full = dest_dir + "/" + name
    if eal.does_asset_exist(full):
        eal.delete_asset(full)   # stale material slots / bones otherwise survive a reimport
    t = fbx_task(path, dest_dir, name, skeleton, morphs, physics)
    tools.import_asset_tasks([t])
    m = unreal.load_asset(full)
    assert m, "import failed: " + full
    L("imported", full, "paths", list(t.imported_object_paths))
    return m, list(t.imported_object_paths)


def move(src, dst):
    if src == dst:
        return
    if eal.does_asset_exist(dst):
        eal.delete_asset(dst)
    ok = eal.rename_asset(src, dst)
    L("rename", src, "->", dst, ok)


# ---------------------------------------------------------------- body + skeleton + physics dummy
skel = unreal.load_asset(SKEL) if eal.does_asset_exist(SKEL) else None
body, paths = import_mesh(os.path.join(RUN, "Karin_Body.fbx"), BODY_DIR, "SK_Player_Female_Outfit_OldCloth001",
                          skeleton=skel, morphs=False, physics=(skel is None))
if skel is None:
    for p in eal.list_assets(BODY_DIR, recursive=False):
        p = p.split(".")[0]
        if p.endswith("_Skeleton"):
            move(p, SKEL)
        elif p.endswith("_PhysicsAsset"):
            move(p, PHYS)
    unreal.EditorAssetLibrary.save_directory("/Game/Pal", only_if_is_dirty=True, recursive=True)
    skel = unreal.load_asset(SKEL)
    body = unreal.load_asset(BODY)
assert skel, "no skeleton"
L("skeleton bones", len(unreal.PalGraphLib.get_skeleton_ref_pose(skel)), "body bones", len(unreal.PalGraphLib.get_ref_pose(body)))

# ---------------------------------------------------------------- textures + material instances
def import_texture(png, name, srgb=True, normal=False):
    dest = MOD + "/Textures"
    full = dest + "/" + name
    t = unreal.AssetImportTask()
    t.filename = png
    t.destination_path = dest
    t.destination_name = name
    t.replace_existing = True
    t.automated = True
    t.save = False
    f = unreal.TextureFactory()
    t.factory = f
    tools.import_asset_tasks([t])
    tex = unreal.load_asset(full)
    assert tex, "texture import failed: %s -> %s %s" % (png, full, list(t.imported_object_paths))
    tex.set_editor_property("srgb", srgb)
    if normal:
        tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
    elif not srgb:
        tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
    return tex

TEX = {}
for name, spec in CFG["textures"].items():
    TEX[name] = import_texture(os.path.join(RUN, "textures", spec["file"]), name, spec.get("srgb", True), spec.get("normal", False))

mel = unreal.MaterialEditingLibrary

# ---------------------------------------------------------------- dummy parents (game paths, never packaged)
# Our MIs only override texture parameters, so at runtime they reuse the shader maps of the game's real parents.
# The dummy master just has to own parameters with the same names and compile cleanly (defaults = our textures so
# sampler types match).
DUMMY_MASTER = "/Game/Pal/Material/Character/Common/M_KarinDummyPalLit"
ST = unreal.MaterialSamplerType
DUMMY_PARAMS = [("Base Texture", "T_Karin_Body", ST.SAMPLERTYPE_COLOR),
                ("Subsurface Texture", "T_Karin_SkinSSS", ST.SAMPLERTYPE_COLOR),
                ("MetallicRoughnessOcclusionSpecularTexture", "T_Karin_SkinM", ST.SAMPLERTYPE_MASKS),
                ("BaseColor Mask", "T_Karin_Black", ST.SAMPLERTYPE_MASKS),
                ("Override Normal Mask 1", "T_Karin_Black", ST.SAMPLERTYPE_MASKS),
                ("Override Normal Mask 2", "T_Karin_Black", ST.SAMPLERTYPE_MASKS),
                ("Override Normal Mask 3", "T_Karin_Black", ST.SAMPLERTYPE_MASKS),
                ("Normal Map", "T_Karin_FlatN", ST.SAMPLERTYPE_NORMAL),
                ("Override Normal Map 1", "T_Karin_FlatN", ST.SAMPLERTYPE_NORMAL),
                ("Override Normal Map 2", "T_Karin_FlatN", ST.SAMPLERTYPE_NORMAL)]
def dummy_master():
    if eal.does_asset_exist(DUMMY_MASTER):
        eal.delete_asset(DUMMY_MASTER)
    d, n = DUMMY_MASTER.rsplit("/", 1)
    mat = tools.create_asset(n, d, unreal.Material, unreal.MaterialFactoryNew())
    acc, acc_out = None, ""
    for i, (pname, tname, st) in enumerate(DUMMY_PARAMS):
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
    mel.connect_material_property(acc, acc_out, unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mel.recompile_material(mat)
    eal.save_loaded_asset(mat)
    return mat
master = dummy_master()
for spec in CFG["materials"].values():
    pp = spec["parent"]
    if eal.does_asset_exist(pp):
        continue
    d, n = pp.rsplit("/", 1)
    mic = tools.create_asset(n, d, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    mel.set_material_instance_parent(mic, master)
    eal.save_loaded_asset(mic)
    L("dummy parent", pp)

def make_mi(name, parent_path, textures, scalars, vectors=None):
    full = MOD + "/Materials/" + name
    if eal.does_asset_exist(full):
        mi = unreal.load_asset(full)
    else:
        mi = tools.create_asset(name, MOD + "/Materials", unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    parent = unreal.load_asset(parent_path)
    assert parent, "missing parent " + parent_path
    mel.set_material_instance_parent(mi, parent)
    for p, tname in textures.items():
        mel.set_material_instance_texture_parameter_value(mi, p, TEX[tname])   # UE 5.1 returns False even on success
        if mel.get_material_instance_texture_parameter_value(mi, p) != TEX[tname]: L("WARN texture param", name, p)
    for p, v in scalars.items():
        ok = mel.set_material_instance_scalar_parameter_value(mi, p, float(v))
        if not ok: L("WARN scalar param", name, p)
    for p, v in (vectors or {}).items():
        ok = mel.set_material_instance_vector_parameter_value(mi, p, unreal.LinearColor(*v))
        if not ok: L("WARN vector param", name, p)
    mel.update_material_instance(mi)
    return mi

MIS = {}
for name, spec in CFG["materials"].items():
    MIS[name] = make_mi(name, spec["parent"], spec.get("textures", {}), spec.get("scalars", {}), spec.get("vectors"))

def assign(mesh, mapping):
    mats = mesh.get_editor_property("materials")
    out = []
    for m in mats:
        slot = str(m.get_editor_property("material_slot_name"))
        mi = MIS.get(mapping.get(slot, slot))
        if mi is None:
            L("WARN no MI for slot", slot)
        else:
            m.set_editor_property("material_interface", mi)
        out.append(m)
    mesh.set_editor_property("materials", out)
    L("materials", mesh.get_name(), [(str(m.get_editor_property("material_slot_name")), m.get_editor_property("material_interface").get_name() if m.get_editor_property("material_interface") else None) for m in out])

assign(body, CFG.get("slot_map", {}))
body.set_editor_property("physics_asset", unreal.load_asset(PHYS))
for s in CFG.get("body_sockets", []):
    unreal.PalGraphLib.set_mesh_socket(body, s["name"], s["bone"], unreal.Vector(*s["loc"]), unreal.Rotator(*s["rot"]), unreal.Vector(*s["scale"]))

# ---------------------------------------------------------------- heads (same face mesh at every female head path)
heads = CFG["head_paths"]
first = None
for hp in heads:
    d, n = hp.rsplit("/", 1)
    if first is None:
        h, _ = import_mesh(os.path.join(RUN, "Karin_Head.fbx"), d, n, skeleton=skel, morphs=True)
        assign(h, CFG.get("slot_map", {}))
        h.set_editor_property("physics_asset", None)
        L("head morphs", list(unreal.PalGraphLib.get_morph_targets(h)))
        unreal.EditorAssetLibrary.save_loaded_asset(h)
        first = hp
    else:
        if eal.does_asset_exist(hp): eal.delete_asset(hp)
        eal.duplicate_asset(first, hp)

# ---------------------------------------------------------------- hidden hairs
hairs = CFG["hair_paths"]
first = None
for hp in hairs:
    d, n = hp.rsplit("/", 1)
    if first is None:
        h, _ = import_mesh(os.path.join(RUN, "Hidden.fbx"), d, n, skeleton=skel, morphs=False)
        assign(h, {"Hidden": CFG["hidden_material"]})
        unreal.EditorAssetLibrary.save_loaded_asset(h)
        first = hp
    else:
        if eal.does_asset_exist(hp): eal.delete_asset(hp)
        eal.duplicate_asset(first, hp)
for hp, socks in CFG.get("hair_sockets", {}).items():
    h = unreal.load_asset(hp)
    for s in socks:
        unreal.PalGraphLib.set_mesh_socket(h, s["name"], s["bone"], unreal.Vector(*s["loc"]), unreal.Rotator(*s["rot"]), unreal.Vector(*s["scale"]))

unreal.EditorAssetLibrary.save_directory("/Game", only_if_is_dirty=True, recursive=True)
L("IMPORT_OK")
