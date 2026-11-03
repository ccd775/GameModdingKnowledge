# blender -b <run>/build.blend --python render_lk.py -- <run> <out_prefix> [sfx]
# Renders the built body + face: textured (materials.json) and with every cloth section in its own colour (the sim
# shells drawn as wireframe-ish dark overlays in the section view). Fork of render_pt.py.
import bpy, sys, os, json, math
from mathutils import Vector
argv = sys.argv[sys.argv.index("--") + 1:]
RUN, OUT = argv[0], argv[1]
SFX = argv[2] if len(argv) > 2 else ""
VIEWS = argv[3].split(",") if len(argv) > 3 else ["front", "back", "side", "q"]
spec = json.load(open(os.path.join(RUN, f"materials{SFX}.json"), encoding="utf-8"))
sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"
sc.display.shading.light = "STUDIO"; sc.display.shading.show_backface_culling = False
sc.render.image_settings.file_format = "PNG"
# the adult face renders on the lash card (SK_Karin_Face; the head copy is collapsed inside it), the young one on the head
FACE_OBJ = "SK_Karin_Face" if "SK_Karin_Face" in bpy.data.objects else "SK_Karin_Head"
show = [o for o in bpy.data.objects if o.type == "MESH" and o.name in ("SK_Karin_Body", FACE_OBJ)]
for o in bpy.data.objects:
    if o.type == "MESH": o.hide_render = o not in show
imgs = {}
def tex_mat(name, tex):
    m = bpy.data.materials.new("R_" + name); m.use_nodes = True
    nt = m.node_tree; bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    if tex not in imgs: imgs[tex] = bpy.data.images.load(os.path.join(RUN, "textures", tex + ".png"))
    t = nt.nodes.new("ShaderNodeTexImage"); t.image = imgs[tex]
    nt.links.new(t.outputs["Color"], bsdf.inputs["Base Color"])
    return m
def flat(name, col, alpha=1.0):
    m = bpy.data.materials.new("C_" + name); m.diffuse_color = (*col, alpha)
    return m
mats = spec["materials"]; alias = spec["alias"]
COL = {"MI_Lenko_HairTail": (0.9, 0.1, 0.1), "MI_Lenko_HairFront": (0.1, 0.8, 0.1), "MI_Lenko_HairBack": (0.1, 0.2, 0.9),
       "MI_Lenko_SkirtCloth": (0.9, 0.6, 0.0), "MI_Lenko_Jacket": (0.7, 0.1, 0.8), "MI_Lenko_Ribbon": (0.0, 0.8, 0.8),
       "MI_Lenko_SkirtSim": (0.2, 0.1, 0.0), "MI_Lenko_JacketSim": (0.1, 0.0, 0.2), "MI_Lenko_Chest": (1.0, 0.45, 0.65)}
SIM = tuple(n for o in show for n in [s.material.name for s in o.material_slots] if n.endswith("Sim"))
orig = {o.name: [s.material.name for s in o.material_slots] for o in show}
def setmode(mode):
    sc.display.shading.color_type = "TEXTURE" if mode == "tex" else "MATERIAL"
    for o in show:
        for i, n in enumerate(orig[o.name]):
            if mode == "tex":
                base = alias.get(n, n)
                m = tex_mat(n, mats[base]["texture"]) if base in mats and n not in SIM else flat(n, (1, 0, 1), 0.0)
                if n in SIM: m.diffuse_color = (0, 0, 0, 0)
            else:
                m = flat(n, COL.get(n, (0.75, 0.75, 0.75)))
            o.material_slots[i].material = m
    sc.display.shading.show_xray = False
def hide_sim(hide):
    # the sim shells overlap the render sections: drop their faces from the view by moving them far away
    for o in show:
        me = o.data
        for i, n in enumerate(orig[o.name]):
            if n in SIM:
                for p in me.polygons:
                    if p.material_index == i:
                        for v in p.vertices: me.vertices[v].co.z += (-1000.0 if hide else 1000.0)
hide_sim(True)
body = bpy.data.objects["SK_Karin_Body"]
pts = [body.matrix_world @ Vector(c) for c in body.bound_box]
lo = Vector((min(p.x for p in pts), min(p.y for p in pts), max(min(p.z for p in pts), -5))); hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
cd = bpy.data.cameras.new("c"); cd.type = "ORTHO"; cam = bpy.data.objects.new("c", cd); sc.collection.objects.link(cam); sc.camera = cam
def shot(fn, d, scale, center, res=(700, 1000)):
    sc.render.resolution_x, sc.render.resolution_y = res
    cd.ortho_scale = scale
    cam.location = center + Vector(d) * 500
    cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = fn; bpy.ops.render.render(write_still=True)
DIRS = {"front": (0, -1, 0), "back": (0, 1, 0), "side": (1, 0, 0), "q": (0.7, -0.7, 0), "rside": (-1, 0, 0)}
tgt = Vector((0, 0, 86.0))
for mode in ("tex", "sec"):
    setmode(mode)
    for name in VIEWS:
        shot(f"{OUT}_{mode}_{name}.png", DIRS[name], 180.0, tgt)
setmode("tex")
shot(f"{OUT}_tex_face.png", (0, -1, 0), 32.0, Vector((0, 0, 146.0)), (700, 700))
shot(f"{OUT}_tex_waist.png", (0.5, -1, 0), 75.0, Vector((0, 0, 93.0)), (700, 700))
shot(f"{OUT}_tex_hand.png", (0, -1, 0), 40.0, Vector((40, 0, 92.0)), (700, 700))
setmode("sec")
shot(f"{OUT}_sec_waist.png", (0.5, -1, 0), 75.0, Vector((0, 0, 93.0)), (700, 700))
shot(f"{OUT}_sec_waistback.png", (-0.5, 1, 0), 75.0, Vector((0, 0, 93.0)), (700, 700))
hide_sim(False)
print("RENDER_OK")
