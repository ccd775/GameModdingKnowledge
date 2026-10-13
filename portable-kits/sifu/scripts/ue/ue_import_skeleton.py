# UE 4.26 editor python (commandlet): import the Base_skeleton reference FBX, name the skeleton asset
# /Game/Characters/Skeleton/Base_skeleton and dump the imported ref skeleton for verification.
# Usage: ue_run.ps1 ue_import_skeleton.py <fbx> <out.json>   (arguments arrive via py_args.json, path in SIFU_PY_ARGS)
import os, sys, json
import unreal

fbx, out_json = json.load(open(os.environ["SIFU_PY_ARGS"], encoding="utf-8-sig"))[:2]
DEST = "/Game/Characters/Skeleton"
eal = unreal.EditorAssetLibrary

for p in (DEST + "/SK_BaseSkeletonRef", DEST + "/Base_skeleton", DEST + "/SK_BaseSkeletonRef_Skeleton"):
    if eal.does_asset_exist(p):
        eal.delete_asset(p)

ui = unreal.FbxImportUI()
ui.set_editor_property("import_mesh", True)
ui.set_editor_property("import_as_skeletal", True)
ui.set_editor_property("import_materials", False)
ui.set_editor_property("import_textures", False)
ui.set_editor_property("import_animations", False)
ui.set_editor_property("create_physics_asset", False)
ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_SKELETAL_MESH)
sk = ui.get_editor_property("skeletal_mesh_import_data")
sk.set_editor_property("convert_scene", True)
sk.set_editor_property("force_front_x_axis", False)
sk.set_editor_property("import_uniform_scale", 1.0)
sk.set_editor_property("use_t0_as_ref_pose", False)
sk.set_editor_property("import_morph_targets", False)

task = unreal.AssetImportTask()
task.set_editor_property("filename", fbx)
task.set_editor_property("destination_path", DEST)
task.set_editor_property("destination_name", "SK_BaseSkeletonRef")
task.set_editor_property("automated", True)
task.set_editor_property("replace_existing", True)
task.set_editor_property("save", False)
task.set_editor_property("options", ui)
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

mesh = eal.load_asset(DEST + "/SK_BaseSkeletonRef")
skel = mesh.get_editor_property("skeleton")
src = skel.get_path_name().split(".")[0]
if src != DEST + "/Base_skeleton":
    eal.rename_asset(src, DEST + "/Base_skeleton")
eal.save_directory(DEST, only_if_is_dirty=False, recursive=True)

mesh = eal.load_asset(DEST + "/SK_BaseSkeletonRef")
res = {"skeleton": mesh.get_editor_property("skeleton").get_path_name(),
       "bones": json.loads(unreal.SifuModToolsLibrary.dump_ref_skeleton(mesh))}
open(out_json, "w").write(json.dumps(res))
unreal.log("IMPORT_SKELETON_DONE %d bones" % len(res["bones"]))
