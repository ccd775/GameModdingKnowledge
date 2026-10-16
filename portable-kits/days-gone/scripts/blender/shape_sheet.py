# Contact sheet of shape keys (Blender 4.2 background): front close-up of each key at value v, in a grid.
# usage: blender -b <build.blend> --python shape_sheet.py -- <out.png> <centre_z> <ortho_scale> key[=value] ...
import bpy, sys, os, math
import numpy as np
argv = sys.argv[sys.argv.index("--") + 1:]
OUT, CZ, OS = argv[0], float(argv[1]), float(argv[2])
keys = [(k.split("=")[0], float(k.split("=")[1]) if "=" in k else 1.0) for k in argv[3:]]
ob = bpy.data.objects["deacon_head_standard"]; me = ob.data
sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"; sc.display.shading.light = "STUDIO"; sc.display.shading.color_type = "TEXTURE"
R = 220; sc.render.resolution_x = R; sc.render.resolution_y = R
cam = bpy.data.objects.get("cam")
if cam is None:
    cd = bpy.data.cameras.new("cam"); cam = bpy.data.objects.new("cam", cd); sc.collection.objects.link(cam)
cam.data.type = "ORTHO"; cam.data.ortho_scale = OS; sc.camera = cam
cam.location = (0, -80, CZ); cam.rotation_euler = (math.radians(90), 0, 0)
for o in bpy.data.objects: o.hide_render = o is not ob
tiles = []
tmp = os.path.join(os.path.dirname(os.path.abspath(OUT)), "_tile.png")
for name, val in [("rest", 0.0)] + keys:
    for k in me.shape_keys.key_blocks: k.value = val if k.name == name else 0.0
    sc.render.filepath = tmp; bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(tmp); px = np.array(img.pixels[:]).reshape(R, R, 4); bpy.data.images.remove(img)
    # label strip: dark bar with a crude per-tile index marker is enough; names are printed in order
    tiles.append(px)
os.remove(tmp)
cols = min(6, len(tiles)); rows = math.ceil(len(tiles) / cols)
sheet = np.ones((rows * R, cols * R, 4))
for i, t in enumerate(tiles):
    r, c = divmod(i, cols); sheet[(rows - 1 - r) * R:(rows - r) * R, c * R:(c + 1) * R] = t
img = bpy.data.images.new("sheet", cols * R, rows * R, alpha=True)
img.pixels = sheet.ravel().tolist(); img.filepath_raw = OUT; img.file_format = "PNG"; img.save()
print("SHEET", OUT, "order:", ["rest"] + [k for k, _ in keys])
