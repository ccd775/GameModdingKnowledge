# preview.py — render fitted parts (front/side) next to HL vanilla meshes, plus a posed deformation test.
# blender -b <fit.blend> --python preview.py -- <out_prefix> <ref_json...>
import bpy, sys, json, math
import numpy as np
from mathutils import Vector, Euler

args = sys.argv[sys.argv.index('--') + 1:]
out = args[0]; refs = args[1:]
scn = bpy.context.scene
scn.render.engine = 'BLENDER_WORKBENCH'
scn.display.shading.light = 'STUDIO'; scn.display.shading.color_type = 'MATERIAL'
scn.render.resolution_x = 1400; scn.render.resolution_y = 1100
scn.render.film_transparent = False
arm = bpy.data.objects['HLArmature']
parts = [o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith('Karin')]
for o in bpy.data.objects:
    if o.type == 'MESH' and o not in parts: o.hide_render = True
for o in parts: o.hide_render = False; o.hide_set(False)
cols = {'Face': (1, .85, .75, 1), 'FaceAlpha': (.3, .3, .9, 1), 'Hair': (.95, .9, .8, 1), 'HairAlpha': (.9, .7, .7, 1), 'Costume': (.55, .6, .75, 1), 'Skin': (1, .8, .7, 1)}
for m in bpy.data.materials:
    if m.name in cols: m.diffuse_color = cols[m.name]
# vanilla reference meshes, shifted +0.7 m in x
def ue2bl(p): return (p[0] * 0.01, -p[1] * 0.01, p[2] * 0.01)
for r in refs:
    d = json.load(open(r)); pos = np.array(d['pos']).reshape(-1, 3); idx = np.array(d['idx']).reshape(-1, 3)
    me = bpy.data.meshes.new(d['name']); me.from_pydata([tuple(np.add(ue2bl(p), (0.75, 0, 0))) for p in pos], [], [tuple(t[::-1]) for t in idx]); me.update()
    ob = bpy.data.objects.new(d['name'], me); scn.collection.objects.link(ob)
    mat = bpy.data.materials.new('ref'); mat.diffuse_color = (.6, .6, .6, 1); me.materials.append(mat)
def cam(name, loc, rot, scale):
    c = bpy.data.cameras.new(name); c.type = 'ORTHO'; c.ortho_scale = scale
    o = bpy.data.objects.new(name, c); scn.collection.objects.link(o); o.location = loc; o.rotation_euler = Euler(rot); return o
front = cam('front', (0.37, -4, 0.9), (math.radians(90), 0, 0), 2.1)
side = cam('side', (4, 0, 0.9), (math.radians(90), 0, math.radians(90)), 2.1)
scn.camera = front; scn.render.filepath = f'{out}_front.png'; bpy.ops.render.render(write_still=True)
for o in bpy.data.objects:
    if o.type == 'MESH' and not o.name.startswith('Karin'): o.hide_render = True
side.location.x = 4; scn.camera = side; scn.render.filepath = f'{out}_side.png'; bpy.ops.render.render(write_still=True)
# posed test: hide refs, pose arms/legs/head/spine
for o in bpy.data.objects:
    if o.type == 'MESH' and not o.name.startswith('Karin'): o.hide_render = True
bpy.context.view_layer.objects.active = arm; bpy.ops.object.mode_set(mode='POSE')
def rot(b, x=0, y=0, z=0):
    pb = arm.pose.bones.get(b)
    if pb: pb.rotation_mode = 'XYZ'; pb.rotation_euler = Euler((math.radians(x), math.radians(y), math.radians(z)))
rot('LeftArm', 0, 0, 0); rot('LeftForeArm', 50, 0, 0); rot('RightArm', 40, 0, 30); rot('LeftUpLeg', 40, 0, 0); rot('LeftLeg', -60, 0, 0)
rot('Head', 20, 0, 0); rot('Spine2', 15, 0, 0); rot('RightHand', 0, 0, 30)
bpy.ops.object.mode_set(mode='OBJECT')
front.location.x = 0; scn.camera = front; scn.render.filepath = f'{out}_posed_front.png'; bpy.ops.render.render(write_still=True)
side.location.x = 4; scn.camera = side; scn.render.filepath = f'{out}_posed_side.png'; bpy.ops.render.render(write_still=True)
