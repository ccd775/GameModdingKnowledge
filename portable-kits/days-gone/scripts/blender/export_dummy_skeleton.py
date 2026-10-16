# Export Deacon's head mesh + skeleton as FBX for the UE 4.11 dummy deacon_master_Skeleton (Blender 4.2 background).
# usage: blender --background --factory-startup --python export_dummy_skeleton.py -- <deacon .uemodel> <out.fbx>
import bpy, sys, os
argv = sys.argv[sys.argv.index("--") + 1:]
SRC, OUT = argv[0], argv[1]
import addon_utils
bpy.ops.wm.read_factory_settings(use_empty=True)
addon_utils.enable("io_scene_ueformat", default_set=True)
s = bpy.context.scene.uf_settings
s.scale_factor = 1.0; s.import_sockets = False; s.import_morph_targets = False
bpy.ops.uf.import_uemodel(filepath=SRC, files=[{"name": os.path.basename(SRC)}], directory=os.path.dirname(SRC))
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
mesh = next(o for o in bpy.data.objects if o.type == "MESH" and o.parent == arm)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fbx_common import export_for_ue411
export_for_ue411(arm, [mesh], OUT, "deacon_head_standard")
print("DUMMY_OK", OUT)
