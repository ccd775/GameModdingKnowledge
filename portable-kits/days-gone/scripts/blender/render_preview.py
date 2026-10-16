# Workbench previews of a build (front / side / back), optionally next to a reference .uemodel or .glb.
# Usage: blender --background --factory-startup <run>/build.blend --python render_preview.py -- <run> [ref_model]
import bpy, sys, os, math
from mathutils import Vector, Euler
argv = sys.argv[sys.argv.index("--") + 1:]
RUN = argv[0]
REF = argv[1] if len(argv) > 1 else ""
if REF:
    before = set(bpy.data.objects)
    if REF.endswith(".uemodel"):
        import addon_utils
        addon_utils.enable("io_scene_ueformat", default_set=True)
        s = bpy.context.scene.uf_settings
        s.scale_factor = 1.0; s.import_sockets = False; s.import_morph_targets = False
        bpy.ops.uf.import_uemodel(filepath=REF, files=[{"name": os.path.basename(REF)}], directory=os.path.dirname(REF))
    else:
        bpy.ops.import_scene.gltf(filepath=REF)
    for o in set(bpy.data.objects) - before:
        if o.parent is None:
            o.location.x += 80.0 if not REF.endswith(".glb") else 0.8
            if REF.endswith(".glb"): o.scale = (100, 100, 100); o.location.x = 80.0
scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "TEXTURE"
scene.render.resolution_x = 1000 if REF else 700; scene.render.resolution_y = 1200
cam_data = bpy.data.cameras.new("cam"); cam_data.type = "ORTHO"; cam_data.ortho_scale = 230
cam = bpy.data.objects.new("cam", cam_data); scene.collection.objects.link(cam); scene.camera = cam
cx = 40.0 if REF else 0.0
views = {"front": (Vector((cx, -400, 100)), Euler((math.radians(90), 0, 0))),
         "side": (Vector((400, 0, 100)), Euler((math.radians(90), 0, math.radians(90)))),
         "back": (Vector((cx, 400, 100)), Euler((math.radians(90), 0, math.radians(180))))}
for name, (loc, r) in views.items():
    cam.location = loc; cam.rotation_euler = r
    scene.render.filepath = os.path.join(RUN, f"preview_{name}.png")
    bpy.ops.render.render(write_still=True)
print("PREVIEW_OK")
