# cmp_upper.py -- <out.png> <face_object> [fbx]: front ortho render of the upper body, framed by the face height
import bpy, sys, math
from mathutils import Vector
a = sys.argv[sys.argv.index('--') + 1:]
out, face = a[0], a[1]
if len(a) > 2:
    bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.fbx(filepath=a[2], use_anim=False)
scn = bpy.context.scene; scn.render.engine = 'BLENDER_WORKBENCH'; scn.display.shading.light = 'STUDIO'
scn.render.resolution_x = 700; scn.render.resolution_y = 900
fo = bpy.data.objects[face]
dg = bpy.context.evaluated_depsgraph_get()
def wverts(o):
    e = o.evaluated_get(dg); m = e.to_mesh(); vs = [o.matrix_world @ v.co for v in m.vertices]; e.to_mesh_clear(); return vs
fv = wverts(fo); zmin = min(v.z for v in fv); zmax = max(v.z for v in fv)
h = zmax - zmin; cz = zmin - 0.6 * h
for o in bpy.data.objects:
    if o.type == 'MESH': o.hide_render = not o.name.startswith(('Karin',) if len(a) == 2 else ('Body', 'body', 'hair', 'pullover', 'underwear', 'kemomimi'))
c = bpy.data.cameras.new('c'); c.type = 'ORTHO'; c.ortho_scale = 4.2 * h
co = bpy.data.objects.new('c', c); scn.collection.objects.link(co); scn.camera = co
co.location = (0, -5, cz); co.rotation_euler = (math.radians(90), 0, 0)
scn.render.filepath = out; bpy.ops.render.render(write_still=True)
print('FACE h', round(h, 4), 'chin', round(zmin, 4))
