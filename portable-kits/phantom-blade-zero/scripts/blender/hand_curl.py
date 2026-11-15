# blender --background <run>/build.blend --python hand_curl.py -- <out_prefix>
# Left hand close-ups of a build: open (bind pose) and with the index / middle / ring / little fingers curled 75 / 80 /
# 55 deg per joint about the knuckle line (fist-like), front and side, single colour. Firefly round 4 moved the finger
# meshes sideways along the knuckle line (FINGER_LAT in build_ff.py); this checks the fist still holds together.
# Writes <out_prefix>_{open,fist}_{front,side}.png.
import bpy, sys, math
from mathutils import Vector, Quaternion
argv = sys.argv[sys.argv.index("--") + 1:]
OUT = argv[0]
sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"
sc.display.shading.light = "STUDIO"; sc.display.shading.color_type = "SINGLE"
sc.display.shading.single_color = (0.85, 0.78, 0.72); sc.display.shading.show_cavity = True
sc.display.shading.show_backface_culling = False
sc.render.image_settings.file_format = "PNG"
body = bpy.data.objects["SK_Karin_Body"]
arm = next(m.object for m in body.modifiers if m.type == "ARMATURE")
for o in bpy.data.objects:
    if o.type == "MESH": o.hide_render = o is not body
me = body.data   # simulation shells moved out of view
sim = {i for i, s in enumerate(body.material_slots) if s.material and s.material.name.split(".")[0].endswith("Sim")}
for p in me.polygons:
    if p.material_index in sim:
        for v in p.vertices: me.vertices[v].co.z -= 1000.0
pb = arm.pose.bones
def head(n): return arm.matrix_world @ arm.data.bones[n].head_local
lat = (head("index_01_l") - head("pinky_01_l")); fd = (head("middle_02_l") - head("middle_01_l")).normalized()
lat = (lat - lat.dot(fd) * fd).normalized()
inward = Vector((-1.0, 0.0, -0.3)); inward = (inward - inward.dot(fd) * fd - inward.dot(lat) * lat).normalized()
# sign: rotating the finger direction about the knuckle line by +angle must move it toward the palm side
s_ = 1.0 if (Quaternion(lat, 0.3) @ fd).dot(inward) > fd.dot(inward) else -1.0
cd = bpy.data.cameras.new("c"); cd.type = "ORTHO"; cam = bpy.data.objects.new("c", cd); sc.collection.objects.link(cam); sc.camera = cam
def shot(fn, d, scale, center):
    sc.render.resolution_x, sc.render.resolution_y = 600, 600
    cd.ortho_scale = scale
    cam.location = center + Vector(d) * 300
    cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = fn; bpy.ops.render.render(write_still=True)
ctr = (head("hand_l") + head("middle_01_l")) / 2
front = Vector((0, -1, 0)); side = lat if lat.y < 0 else -lat
shot(OUT + "_open_front.png", front, 26.0, ctr)
shot(OUT + "_open_side.png", side, 26.0, ctr)
ANG = {"01": 75, "02": 80, "03": 55}
for f in ("index", "middle", "ring", "pinky"):
    for g, a in ANG.items():
        b = pb[f"{f}_{g}_l"]; b.rotation_mode = "QUATERNION"
        ax = (arm.matrix_world.to_3x3() @ arm.data.bones[b.name].matrix_local.to_3x3()).inverted() @ lat
        b.rotation_quaternion = Quaternion(ax, math.radians(a) * s_)
bpy.context.view_layer.update()
shot(OUT + "_fist_front.png", front, 26.0, ctr)
shot(OUT + "_fist_side.png", side, 26.0, ctr)
print("HAND_OK sign", s_)
