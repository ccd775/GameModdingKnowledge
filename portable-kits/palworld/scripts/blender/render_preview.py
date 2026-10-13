# Workbench previews of a build_pal.py run: full body front/side next to the vanilla outfit, and face morphs.
# Usage: blender --background <run>/build.blend --python render_preview.py -- <run_dir>
import bpy, sys, os, math
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from palcommon import enable_ueformat, import_uemodel, CACHE_UE

argv = sys.argv[sys.argv.index("--") + 1:]
RUN = os.path.abspath(argv[0])
OUT = os.path.join(RUN, "preview"); os.makedirs(OUT, exist_ok=True)
sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"
sc.display.shading.light = "STUDIO"
sc.display.shading.color_type = "TEXTURE"
sc.render.resolution_x, sc.render.resolution_y = 1000, 1000
sc.render.film_transparent = False
sc.world = sc.world or bpy.data.worlds.new("W")

body = bpy.data.objects["SK_Karin_Body"]; head = bpy.data.objects["SK_Karin_Head"]
enable_ueformat()
van = [o for o in import_uemodel(os.path.join(CACHE_UE, r"Outfit\SK_Player_Female_Outfit_OldCloth001\SK_Player_Female_Outfit_OldCloth001.uemodel")) if o.type == "MESH"]
vhead = [o for o in import_uemodel(os.path.join(CACHE_UE, r"Head\Head001\SK_Player_Female_Head001.uemodel")) if o.type == "MESH"]
for o in van + vhead:
    o.location.x += 80.0

cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = "ORTHO"
def shoot(name, loc, rot, ortho):
    cam.location = loc; cam.rotation_euler = rot; cam.data.ortho_scale = ortho
    sc.render.filepath = os.path.join(OUT, name + ".png")
    bpy.ops.render.render(write_still=True)
# characters face -Y: camera at -Y looking +Y
shoot("full_front", Vector((40, -400, 85)), (math.radians(90), 0, 0), 200)
shoot("full_side", Vector((-400, 0, 85)), (math.radians(90), 0, math.radians(-90)), 200)
for o in van + vhead: o.hide_render = True
hz = 140.0
shoot("face_neutral", Vector((0, -200, hz)), (math.radians(90), 0, 0), 32)
keys = head.data.shape_keys.key_blocks if head.data.shape_keys else []
for kb in keys[1:]:
    for k2 in keys[1:]: k2.value = 0.0
    kb.value = 1.0
    shoot("face_" + kb.name, Vector((0, -200, hz)), (math.radians(90), 0, 0), 32)
for k2 in keys[1:]: k2.value = 0.0
print("PREVIEW_OK", OUT)
