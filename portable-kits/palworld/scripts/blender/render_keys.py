# Render Karin's face with individual VRM shape keys: blender --background --python render_keys.py -- <outdir> key1 key2 ...
import bpy, sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from palcommon import KARIN_VRM
from mathutils import Vector
argv = sys.argv[sys.argv.index("--") + 1:]
OUT = argv[0]; os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=KARIN_VRM)
face = bpy.data.objects["Body"]
sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"; sc.display.shading.light = "STUDIO"; sc.display.shading.color_type = "TEXTURE"
sc.render.resolution_x, sc.render.resolution_y = 400, 400
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = "ORTHO"; cam.data.ortho_scale = 0.09
cam.location = Vector((0, -2, 1.06)); cam.rotation_euler = (math.radians(90), 0, 0)
kb = face.data.shape_keys.key_blocks
for i, k in enumerate(argv[1:]):
    for x in kb[1:]: x.value = 0.0
    if k in kb: kb[k].value = 1.0
    sc.render.filepath = os.path.join(OUT, "k%02d.png" % i); bpy.ops.render.render(write_still=True)
print("KEYS_OK")
