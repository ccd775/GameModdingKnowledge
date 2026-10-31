# blender -b <run>/build.blend --python render_pt.py -- <run> <out_prefix> [sfx]
# Renders the built body + face: textured (materials.json) and with every cloth section in its own colour.
import bpy, sys, os, json, math
from mathutils import Vector
argv = sys.argv[sys.argv.index("--") + 1:]
RUN, OUT = argv[0], argv[1]
SFX = argv[2] if len(argv) > 2 else ""
spec = json.load(open(os.path.join(RUN, f"materials{SFX}.json"), encoding="utf-8"))
sc = bpy.context.scene
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = 16; sc.cycles.use_denoising = False
sc.render.image_settings.file_format = "PNG"
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
bg.inputs[0].default_value = (0.55, 0.55, 0.6, 1); bg.inputs[1].default_value = 1.3
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sun.data.energy = 2.5
sun.rotation_euler = (math.radians(50), 0, math.radians(-30)); sc.collection.objects.link(sun)
show = [o for o in bpy.data.objects if o.type == "MESH" and o.name in ("SK_Karin_Body", f"SK_Karin_Face")]
for o in bpy.data.objects:
    if o.type == "MESH": o.hide_render = o not in show
imgs = {}
def tex_mat(name, tex):
    m = bpy.data.materials.new("R_" + name); m.use_nodes = True
    nt = m.node_tree; bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    if tex not in imgs: imgs[tex] = bpy.data.images.load(os.path.join(RUN, "textures", tex + ".png"))
    t = nt.nodes.new("ShaderNodeTexImage"); t.image = imgs[tex]
    nt.links.new(t.outputs["Color"], bsdf.inputs["Base Color"]); bsdf.inputs["Roughness"].default_value = 0.8
    return m
def flat(name, col):
    m = bpy.data.materials.new("C_" + name); m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"); b.inputs["Base Color"].default_value = (*col, 1); b.inputs["Roughness"].default_value = 0.9
    return m
mats = spec["materials"]; alias = spec["alias"]
COL = {"MI_Karin_HairTail": (0.9, 0.1, 0.1), "MI_Karin_HairFront": (0.1, 0.8, 0.1), "MI_Karin_Ear": (0.1, 0.2, 0.9),
       "MI_Karin_Tail": (0.9, 0.6, 0.0), "MI_Karin_Jacket": (0.7, 0.1, 0.8), "MI_Karin_Cord": (0.0, 0.8, 0.8), "MI_Karin_Strap": (0.9, 0.9, 0.0)}
orig = {o.name: [s.material.name for s in o.material_slots] for o in show}
def setmode(textured):
    for o in show:
        for i, n in enumerate(orig[o.name]):
            if textured:
                base = alias.get(n, n)
                o.material_slots[i].material = tex_mat(n, mats[base]["texture"]) if base in mats else flat(n, (1, 0, 1))
            else:
                o.material_slots[i].material = flat(n, COL.get(n, (0.75, 0.75, 0.75)))
body = bpy.data.objects["SK_Karin_Body"]
pts = [body.matrix_world @ Vector(c) for c in body.bound_box]
lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))); hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
cd = bpy.data.cameras.new("c"); cd.type = "ORTHO"; cam = bpy.data.objects.new("c", cd); sc.collection.objects.link(cam); sc.camera = cam
tgt = (lo + hi) / 2
def shot(fn, d, scale, center, res=(600, 900)):
    sc.render.resolution_x, sc.render.resolution_y = res
    cd.ortho_scale = scale
    cam.location = center + Vector(d) * 500
    cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = fn; bpy.ops.render.render(write_still=True)
H = (hi.z - lo.z) * 1.05
for textured, tag in ((True, "tex"), (False, "sec")):
    setmode(textured)
    for name, d in (("front", (0, -1, 0)), ("back", (0, 1, 0)), ("side", (1, 0, 0))):
        shot(f"{OUT}_{tag}_{name}.png", d, H, tgt)
setmode(True)
hd = Vector((0, 0, hi.z - (hi.z - lo.z) * 0.12))
shot(f"{OUT}_tex_face.png", (0, -1, 0), (hi.z - lo.z) * 0.2, hd, (600, 600))
print("RENDER_OK")
