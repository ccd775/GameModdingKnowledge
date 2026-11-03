# blender -b <run>/build.blend --python render_coll.py -- <run> <out_prefix> [sfx]
# Debug view of the hair-only colliders (report "hair_collision.world", Blender bind coords): each capsule drawn as a
# chain of red spheres on the textured body, (a) with the hair hidden: red showing means a collider stands outside
# the jacket; (b) with the hair: red showing through means it would push the hair at rest.
import bpy, sys, os, json
import numpy as np
from mathutils import Vector
argv = sys.argv[sys.argv.index("--") + 1:]
RUN, OUT = argv[0], argv[1]
SFX = argv[2] if len(argv) > 2 else ""
rep = json.load(open(os.path.join(RUN, f"report{SFX}.json"), encoding="utf-8"))
spec = json.load(open(os.path.join(RUN, f"materials{SFX}.json"), encoding="utf-8"))
sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"
sc.display.shading.light = "STUDIO"; sc.display.shading.color_type = "TEXTURE"
sc.render.image_settings.file_format = "PNG"
body = bpy.data.objects["SK_Karin_Body"]
FACE = "SK_Karin_Face" if "SK_Karin_Face" in bpy.data.objects else "SK_Karin_Head"
for o in bpy.data.objects:
    if o.type == "MESH": o.hide_render = o.name not in ("SK_Karin_Body", FACE)
mats, alias = spec["materials"], spec["alias"]
imgs = {}
def tex_mat(name, tex, alpha=1.0):
    m = bpy.data.materials.new("R_" + name); m.use_nodes = True
    nt = m.node_tree; bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    if tex not in imgs: imgs[tex] = bpy.data.images.load(os.path.join(RUN, "textures", tex + ".png"))
    t = nt.nodes.new("ShaderNodeTexImage"); t.image = imgs[tex]
    nt.links.new(t.outputs["Color"], bsdf.inputs["Base Color"])
    return m
orig = {o.name: [s.material.name for s in o.material_slots] for o in (body, bpy.data.objects[FACE])}
HAIR = ("MI_Lenko_HairB", "MI_Lenko_HairBack", "MI_Lenko_HairF", "MI_Lenko_HairTail", "MI_Lenko_HairFront")
def hide_faces(o, names, dz):
    me = o.data
    for i, n in enumerate(orig[o.name]):
        if n in names:
            for p in me.polygons:
                if p.material_index == i:
                    for v in p.vertices: me.vertices[v].co.z += dz
SIM = [n for n in orig["SK_Karin_Body"] if n.endswith("Sim")]
hide_faces(body, SIM, -1000.0)
for o in (body, bpy.data.objects[FACE]):
    for i, n in enumerate(orig[o.name]):
        base = alias.get(n, n)
        if base in mats: o.material_slots[i].material = tex_mat(n, mats[base]["texture"])
red = bpy.data.materials.new("Coll"); red.diffuse_color = (1.0, 0.05, 0.05, 1.0)
cm = bpy.data.meshes.new("coll")
import bmesh
bm = bmesh.new()
for a, b, r in rep["hair_collision"]["world"]:
    a, b = np.array(a), np.array(b)
    n = max(int(np.linalg.norm(b - a) / 1.0), 1)
    for t in np.linspace(0.0, 1.0, n + 1):
        bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=r,
                                  matrix=__import__("mathutils").Matrix.Translation(Vector(a + t * (b - a))))
bm.to_mesh(cm); bm.free()
co = bpy.data.objects.new("coll", cm); sc.collection.objects.link(co); co.data.materials.append(red)
sc.display.shading.color_type = "MATERIAL"
for o in (body, bpy.data.objects[FACE]):
    for s in o.material_slots:
        if s.material and s.material.name.startswith("R_"):
            s.material.diffuse_color = (0.8, 0.8, 0.85, 1.0)
cd = bpy.data.cameras.new("c"); cd.type = "ORTHO"; cam = bpy.data.objects.new("c", cd); sc.collection.objects.link(cam); sc.camera = cam
def shot(fn, d, scale, center, res=(800, 900)):
    sc.render.resolution_x, sc.render.resolution_y = res
    cd.ortho_scale = scale
    cam.location = center + Vector(d) * 500
    cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = fn; bpy.ops.render.render(write_still=True)
C = Vector((0, 0, 112.0))
for tag, hidden in (("nohair", True), ("hair", False)):
    if hidden: hide_faces(body, HAIR, -1000.0)
    for name, d in (("back", (0, 1, 0)), ("side", (1, 0, 0)), ("qback", (0.7, 0.7, 0.15))):
        shot(f"{OUT}_{tag}_{name}.png", d, 70.0, C)
    if hidden: hide_faces(body, HAIR, 1000.0)
print("RENDER_OK")
