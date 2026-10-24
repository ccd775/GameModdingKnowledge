"""Render the fitted Karin next to Arno's vanilla meshes (Blender 5.0, background, Workbench).

blender -b <ko_arno_fit.blend> --python render_compare.py -- <out_prefix> [--ref-scale 1]

The fit blend keeps the vanilla meshes from the fit GLB as hidden "NaoeHeadRef*" objects. AnvilToolkit's export-glb
writes their positions divided by the mesh Scale (2 for Arno's character meshes) but the inverse binds carry the
factor back, so the armature-deformed rest shape is already full size (--ref-scale 1; measured 2026-10-24).
Writes <prefix>_{front,side}_{karin,arno,both}.png.
Frame (fit blend): forward +X, up -Y, left +Z.
"""
import bpy, sys, mathutils

argv = sys.argv[sys.argv.index("--") + 1:]
prefix = argv[0]
ref_scale = float(argv[argv.index("--ref-scale") + 1]) if "--ref-scale" in argv else 1.0
sc = bpy.context.scene
rig = bpy.data.objects["NaoeRig"]
rig.data.pose_position = 'REST'
refs = [o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith("NaoeHeadRef")]
karin = [o for o in bpy.data.objects if o.type == 'MESH' and o.parent == rig and o not in refs]
for o in refs:
    o.hide_set(False)
    o.matrix_world = mathutils.Matrix.Scale(ref_scale, 4) @ o.matrix_world

def mat(name, rgba):
    m = bpy.data.materials.new(name)
    m.diffuse_color = rgba
    return m
mk, ma = mat("cmpKarin", (0.95, 0.75, 0.75, 1)), mat("cmpArno", (0.45, 0.6, 0.95, 1))
for objs, m in ((karin, mk), (refs, ma)):
    for o in objs:
        o.data.materials.clear()
        o.data.materials.append(m)

up = mathutils.Vector((0, -1, 0)); fwd = mathutils.Vector((1, 0, 0)); left = mathutils.Vector((0, 0, 1))
cam_data = bpy.data.cameras.new("cam"); cam_data.type = 'ORTHO'; cam_data.ortho_scale = 2.0
cam = bpy.data.objects.new("cam", cam_data); sc.collection.objects.link(cam); sc.camera = cam
sc.render.engine = 'BLENDER_WORKBENCH'
sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'MATERIAL'
sc.render.resolution_x = 600; sc.render.resolution_y = 1100
sc.render.film_transparent = False
ctr = up * 0.95
for view, d in (("front", fwd), ("side", left)):
    right = up.cross(d).normalized()
    loc = ctr + d * 6
    cam.matrix_world = mathutils.Matrix(((right.x, up.x, d.x, loc.x), (right.y, up.y, d.y, loc.y),
                                         (right.z, up.z, d.z, loc.z), (0, 0, 0, 1)))
    for tag, show in (("karin", karin), ("arno", refs), ("both", karin + refs)):
        for o in karin + refs:
            o.hide_render = o not in show
        sc.display.shading.show_xray = tag == "both"
        sc.display.shading.xray_alpha = 0.6
        sc.render.filepath = f"{prefix}_{view}_{tag}.png"
        bpy.ops.render.render(write_still=True)
print("COMPARE_OK", prefix)
