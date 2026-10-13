# Full-body textured preview of a build (rest + animation frames), one contact sheet per call.
# blender -b --factory-startup <karin_sifu.blend> --python preview_model.py -- <profile> <out.png> [<anim.json> <frame> ...]
# Views: front, side, back, 3/4. Textures: the profile's atlas pages (Karin_Original: the build's own images).
import sys, os, math
import bpy
from mathutils import Euler
sys.path.insert(0, os.path.dirname(__file__))
import profiles

args = sys.argv[sys.argv.index("--") + 1:]
P = profiles.activate(args[0])
OUT = args[1]
poses = [(None, "rest")]
rest = args[2:]
for i in range(0, len(rest), 2):
    poses.append((rest[i], int(rest[i + 1])))

# animation posing from pose_preview.py (everything before its render setup)
SC = os.path.dirname(os.path.abspath(__file__))
src = open(SC + "/pose_preview.py", encoding="utf-8").read()
src = src.split("\nscn = bpy.context.scene\n")[0].replace('args = sys.argv[sys.argv.index("--") + 1:]', "args = [None, 'x']")
src = src.replace("anim = json.load(open(args[0]))", "anim = None")
src = src.replace('which = [int(a) for a in args[2:]] or list(range(len(anim["frames"])))', "which = []")
exec(src.replace("__file__", repr(SC + "/pose_preview.py")))

# textures
if P.get("slots"):
    for slot, spec in P["slots"].items():
        m = bpy.data.materials.get(slot)
        if m is None:
            continue
        m.use_nodes = True
        nt = m.node_tree
        for n in list(nt.nodes):
            nt.nodes.remove(n)
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = bpy.data.images.load(P["tex_dir"] + "/" + P["tex_files"]["color"].format(page=spec["page"]), check_existing=True)
        nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
        nt.nodes.active = tex

scn = bpy.context.scene
scn.render.engine = "BLENDER_WORKBENCH"
scn.display.shading.light = "STUDIO"
scn.display.shading.color_type = "TEXTURE"
scn.render.resolution_x, scn.render.resolution_y = 360, 560
scn.render.film_transparent = False
for o in bpy.data.objects:
    if o.type == "MESH" and o.name.startswith("Proxy_"):
        o.hide_render = True
cam_data = bpy.data.cameras.new("cam")
cam_data.type = "ORTHO"
cam_data.ortho_scale = 200
cam_data.clip_end = 10000
cam = bpy.data.objects.new("cam", cam_data)
scn.collection.objects.link(cam)
scn.camera = cam
VIEWS = [("front", (0, -400, 95), (90, 0, 0)), ("side", (400, 0, 95), (90, 0, 90)),
         ("back", (0, 400, 95), (90, 0, 180)), ("q34", (283, -283, 95), (90, 0, 45))]
tiles = []
tmp = os.path.splitext(OUT)[0] + "_tmp"
for anim_path, fr in poses:
    if anim_path is None:
        apply_frame(None)
    else:
        import json
        a = json.load(open(anim_path))
        apply_frame(a["frames"][fr])
    for vn, loc, rot in VIEWS:
        cam.location = loc
        cam.rotation_euler = Euler([math.radians(x) for x in rot])
        f = f"{tmp}_{len(tiles)}.png"
        scn.render.filepath = f
        bpy.ops.render.render(write_still=True)
        tiles.append(f)
# contact sheet: one row per pose
W, H = scn.render.resolution_x, scn.render.resolution_y
cols = len(VIEWS)
rows = len(poses)
sheet = bpy.data.images.new("sheet", W * cols, H * rows)
import numpy as np
px = np.zeros((H * rows, W * cols, 4), np.float32)
for i, f in enumerate(tiles):
    im = bpy.data.images.load(f)
    a = np.array(im.pixels[:], np.float32).reshape(H, W, 4)
    r, c = i // cols, i % cols
    px[(rows - 1 - r) * H:(rows - r) * H, c * W:(c + 1) * W] = a
    bpy.data.images.remove(im)
    os.remove(f)
sheet.pixels[:] = px.reshape(-1)
sheet.filepath_raw = OUT
sheet.file_format = "PNG"
sheet.save()
print("PREVIEW_DONE", OUT)
