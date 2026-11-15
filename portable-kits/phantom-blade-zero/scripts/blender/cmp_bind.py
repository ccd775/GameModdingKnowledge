# blender --background --factory-startup --python cmp_bind.py -- <out_prefix> <label>=<run>/build.blend ...
# Side-by-side bind-pose renders, same scale, of the bodies of several builds (e.g. ff2=..., ff3=..., lk6=...): the
# simulation shells are removed and the shape keys zeroed. Writes <out_prefix>_front.png, _q.png (3/4 view) and one
# arm / hand close-up per build (<out_prefix>_arm_<label>.png). Used for Firefly round 3 (arm length, hand size and
# leg thickness against Lenko's accepted build).
import bpy, bmesh, sys
from mathutils import Vector
argv = sys.argv[sys.argv.index("--") + 1:]
OUT = argv[0]
items = [a.split("=", 1) for a in argv[1:]]
for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"
sc.display.shading.light = "STUDIO"; sc.display.shading.color_type = "OBJECT"
sc.display.shading.show_cavity = True; sc.display.shading.show_backface_culling = False
sc.render.image_settings.file_format = "PNG"
COLS = [(0.85, 0.75, 0.7, 1), (0.7, 0.8, 0.9, 1), (0.75, 0.9, 0.7, 1), (0.9, 0.85, 0.6, 1)]
SPACING = 95.0
for i, (lab, path) in enumerate(items):
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        names = [n for n in src.objects if n in ("SK_Karin_Body", "SK_Karin_Face")]
        if "SK_Karin_Face" not in names and "SK_Karin_Head" in src.objects: names.append("SK_Karin_Head")
        dst.objects = names
    for o in dst.objects:
        sc.collection.objects.link(o)
        for m in list(o.modifiers): o.modifiers.remove(m)
        if o.data.shape_keys:
            for kb in o.data.shape_keys.key_blocks: kb.value = 0.0
        me = o.data; bm = bmesh.new(); bm.from_mesh(me)
        # material names of the second and later files get a ".001" suffix
        sim = {j for j, s in enumerate(o.material_slots) if s.material and s.material.name.split(".")[0].endswith("Sim")}
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index in sim], context="FACES")
        bm.to_mesh(me); bm.free()
        o.parent = None; o.location = (i * SPACING, 0, 0); o.color = COLS[i % len(COLS)]
        print("LOADED", lab, o.name, len(me.vertices))
cd = bpy.data.cameras.new("c"); cd.type = "ORTHO"; cam = bpy.data.objects.new("c", cd); sc.collection.objects.link(cam); sc.camera = cam
def shot(fn, d, scale, center, res):
    sc.render.resolution_x, sc.render.resolution_y = res
    cd.ortho_scale = scale
    cam.location = center + Vector(d) * 500
    cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = fn; bpy.ops.render.render(write_still=True)
n = len(items); cx = (n - 1) * SPACING / 2
shot(OUT + "_front.png", (0, -1, 0), max(185.0, n * SPACING + 10), Vector((cx, 0, 86.0)), (1400, 1000))
shot(OUT + "_q.png", (0.5, -1, 0), max(185.0, n * SPACING + 10), Vector((cx, 0, 86.0)), (1400, 1000))
for i, (lab, _) in enumerate(items):
    shot(f"{OUT}_arm_{lab}.png", (0, -1, 0), 70.0, Vector((i * SPACING + 25, 0, 100.0)), (600, 700))
print("CMP_OK")
