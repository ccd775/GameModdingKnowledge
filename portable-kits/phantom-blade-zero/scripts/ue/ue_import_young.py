# UE 5.7 editor Python (headless): import the young variant of a build_pbz.py run (run after ue_import_pbz.py,
# which creates the Karin textures and material instances reused here).
#   UnrealEditor-Cmd ProjectPBZ.uproject -run=pythonscript -script="ue_import_young.py <run_dir>"
#
# Real assets (packaged): Young_Hun/SkinParts/{Hun_Young_Body (leader), Hun_Young_Head (face), Hun_young_Hair,
#   Hun_Young_BrowLashCard (hidden)}, Young_Hun/SkinParts/Cloth/CA_Hun_{YOung_Cloth02,Young_Hair01,Young_Cloth01}
#   (hidden mesh under the cloth asset names).
# Dummies (never packaged): Young_Hun/Hun_Young_Skeleton, Young_Hun/PA_Hun_Young, Young_Hun/AnimBP/ABP_Hun_PostProcess_Young.
import unreal, sys

args = [a for a in sys.argv[1:] if not a.startswith("-")]
RUN = args[0].replace("\\", "/")
L = lambda *a: unreal.log("[PBZ] " + " ".join(str(x) for x in a))
eal = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
lib = unreal.PBZModToolsLibrary
unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")

YH = "/HuaShira/Characters/Hero/Young_Hun"
SKEL = YH + "/Hun_Young_Skeleton"
MOD = "/HuaShira/Mods/KarinPBZ"

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
    L("imported", full)
    return m

def move(src, dst):
    if src == dst: return
    if eal.does_asset_exist(dst): eal.delete_asset(dst)
    L("rename", src, "->", dst, eal.rename_asset(src, dst))

# ---------------------------------------------------------------- body (creates the dummy skeleton on the first run)
skel = unreal.load_asset(SKEL) if eal.does_asset_exist(SKEL) else None
body = import_mesh(RUN + "/Karin_Body_Young.fbx", YH + "/SkinParts", "Hun_Young_Body", skeleton=skel)
if skel is None:
    for p in eal.list_assets(YH + "/SkinParts", recursive=False):
        p = p.split(".")[0]
        if p.endswith("_Skeleton"):
            move(p, SKEL)
    skel = unreal.load_asset(SKEL)
    body = unreal.load_asset(YH + "/SkinParts/Hun_Young_Body")
assert skel, "no skeleton"
head = import_mesh(RUN + "/Karin_Head_Young.fbx", YH + "/SkinParts", "Hun_Young_Head", skeleton=skel, morphs=True)
empty = import_mesh(RUN + "/Empty_Young.fbx", YH + "/SkinParts", "Hun_young_Hair", skeleton=skel)
L("bones body", len(eval(lib.dump_ref_skeleton(body))), "head", len(eval(lib.dump_ref_skeleton(head))))

# ---------------------------------------------------------------- dummies for game-owned assets
pa = lib.create_physics_asset(YH, "PA_Hun_Young", None)
eal.save_loaded_asset(pa)
abp_path = YH + "/AnimBP/ABP_Hun_PostProcess_Young"
if not eal.does_asset_exist(abp_path):
    fac = unreal.AnimBlueprintFactory()
    fac.set_editor_property("target_skeleton", skel)
    fac.set_editor_property("parent_class", unreal.AnimInstance)
    tools.create_asset("ABP_Hun_PostProcess_Young", YH + "/AnimBP", unreal.AnimBlueprint, fac)
    eal.save_asset(abp_path)
abp_class = eal.load_blueprint_class(abp_path)
L("dummy abp class", abp_class.get_path_name() if abp_class else None)

# ---------------------------------------------------------------- materials (the MIs from ue_import_pbz.py)
MIS = {n: unreal.load_asset(MOD + "/Materials/" + n) for n in ("MI_Karin_Skin", "MI_Karin_Face", "MI_Karin_Hair", "MI_Karin_Costume")}
assert all(MIS.values()), "run ue_import_pbz.py first"
def assign(mesh, default=None):
    out = []
    for m in mesh.get_editor_property("materials"):
        slot = str(m.get_editor_property("material_slot_name"))
        mi = MIS.get(slot) or (MIS.get(default) if default else None)
        if mi is None: L("WARN no MI for slot", slot)
        else: m.set_editor_property("material_interface", mi)
        out.append(m)
    mesh.set_editor_property("materials", out)
assign(body); assign(head); assign(empty, "MI_Karin_Skin")
lib.set_mesh_physics_asset(body, pa); lib.set_post_process_anim_blueprint(body, abp_class)
for m in (head, empty):
    lib.set_mesh_physics_asset(m, None); lib.set_post_process_anim_blueprint(m, None)
morphs = list(lib.get_morph_target_names(head))
L("head morphs", len(morphs), "curve meta", lib.set_morph_curve_meta_data(head, morphs))
for a in (body, head, empty):
    eal.save_loaded_asset(a)

# ---------------------------------------------------------------- hidden copies
for p in (YH + "/SkinParts/Hun_Young_BrowLashCard", YH + "/SkinParts/Cloth/CA_Hun_YOung_Cloth02",
          YH + "/SkinParts/Cloth/CA_Hun_Young_Hair01", YH + "/SkinParts/Cloth/CA_Hun_Young_Cloth01"):
    if eal.does_asset_exist(p): eal.delete_asset(p)
    eal.duplicate_asset(YH + "/SkinParts/Hun_young_Hair", p)
unreal.EditorAssetLibrary.save_directory("/HuaShira", only_if_is_dirty=True, recursive=True)
L("IMPORT_YOUNG_OK")
