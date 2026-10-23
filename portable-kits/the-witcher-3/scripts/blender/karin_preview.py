"""Offline preview: re-import the exported karin w2mesh (serialized check) next to Geralt's vanilla
body and render front/side views, rest and a test pose.

blender --background --factory-startup --python scripts/blender/karin_preview.py -- '{"out":"<dir>"}'
(W3_WORK and W3_GAME_DIR set; defaults: out <W3_WORK>\\scratch\\prev, mesh from <W3_WORK>\\build\\depot)
"""
import bpy
import json
import math
import os
import sys
import importlib
import addon_utils
from mathutils import Vector, Euler, Matrix

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # kit scripts/
import w3paths  # noqa: E402

ARGS = json.loads(sys.argv[sys.argv.index('--') + 1]) if '--' in sys.argv and len(sys.argv) > sys.argv.index('--') + 1 else {}
OUT = ARGS.get('out') or w3paths.work('scratch', 'prev')
MESH = ARGS.get('mesh') or w3paths.work('build', 'depot', 'characters', 'models', 'karin', 'karin_body.w2mesh')
TEX_ROOT = ARGS.get('tex_root') or w3paths.work_dir('build', 'depot')
os.makedirs(OUT, exist_ok=True)
MOD = w3paths.addon_module()
bpy.ops.wm.read_factory_settings(use_empty=True)
addon_utils.enable(MOD, default_set=True)
prefs = bpy.context.preferences.addons[MOD].preferences
prefs.witcher_game_path = w3paths.game()
prefs.uncook_path = w3paths.work_dir('uncook')
imesh = importlib.import_module(MOD + '.importers.import_mesh')
irig = importlib.import_module(MOD + '.importers.import_rig')

U = w3paths.work_dir('uncook')
irig.import_w3_rig(U + r'characters\base_entities\man_base\man_base.w2rig', ns='')
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]


def imp(path, offset_x):
    before = set(bpy.data.objects)
    imesh.import_mesh(path, do_import_mats=False, do_import_armature=True, target_armature=arm)
    new = [o for o in set(bpy.data.objects) - before if o.type == 'MESH']
    for o in new:
        o.location.x += offset_x
    return new


karin = imp(MESH, 0.0)
geralt = []
for m in (r'characters\models\geralt\body\model\t_01_mg__body_hires.w2mesh', r'characters\models\geralt\body\model\l_01_mg__body.w2mesh',
          r'characters\models\geralt\body\model\g_01_mg__body.w2mesh', r'characters\models\geralt\body\model\s_01_mg__body_hires.w2mesh'):
    geralt += imp(U + m, 0.0)

stats = {'karin_objects': [(o.name, len(o.data.vertices), [g.name for g in o.vertex_groups][:5]) for o in karin]}
# serialized check against the authoring blend
src = ARGS.get('blend') or w3paths.work('blend', 'karin_fit.blend')
if os.path.exists(src):
    with bpy.data.libraries.load(src) as (df, dt):
        dt.objects = ['karin_body_lod0']
    so = dt.objects[0]
    import numpy as np
    a = np.array([v.co[:] for v in so.data.vertices])
    b = np.array([(o.matrix_world @ v.co)[:] for o in karin for v in o.data.vertices])
    stats['src_bbox'] = [a.min(0).tolist(), a.max(0).tolist()]
    stats['imp_bbox'] = [b.min(0).tolist(), b.max(0).tolist()]
    stats['src_vcount'] = len(a)
    stats['imp_vcount'] = len(b)

# simple flat-colour materials
def flat(name, col):
    m = bpy.data.materials.new(name)
    m.diffuse_color = col
    return m

# textured materials for karin (load png sources)
texdir = w3paths.work('karin_src', 'textures')
for o in karin:
    for slot in o.material_slots:
        pass
mk = flat('karin', (0.9, 0.6, 0.6, 1))
mg = flat('geralt', (0.6, 0.7, 0.9, 1))
for o in karin:
    o.data.materials.clear(); o.data.materials.append(mk)
for o in geralt:
    o.data.materials.clear(); o.data.materials.append(mg)

scene = bpy.context.scene
scene.render.engine = 'BLENDER_WORKBENCH'
scene.display.shading.light = 'STUDIO'
scene.display.shading.color_type = 'MATERIAL'
scene.render.resolution_x = 900
scene.render.resolution_y = 1100
scene.render.film_transparent = False
cam_data = bpy.data.cameras.new('cam')
cam_data.type = 'ORTHO'
cam_data.ortho_scale = 2.2
cam = bpy.data.objects.new('cam', cam_data)
scene.collection.objects.link(cam)
scene.camera = cam


def shoot(name, loc, rot, ortho=2.2, target_z=0.95, objs_visible=None):
    cam.location = loc
    cam.rotation_euler = rot
    cam_data.ortho_scale = ortho
    for o in karin + geralt:
        o.hide_render = objs_visible is not None and o not in objs_visible
    scene.render.filepath = os.path.join(OUT, name + '.png')
    bpy.ops.render.render(write_still=True)


views = {
    'front': ((0, 4, 1.0), (math.radians(90), 0, math.radians(180))),
    'side': ((4, 0, 1.0), (math.radians(90), 0, math.radians(90))),
}
for vn, (loc, rot) in views.items():
    shoot('karin_' + vn, loc, rot, objs_visible=karin)
    shoot('overlay_' + vn, loc, rot, objs_visible=None)
# head close-up
shoot('karin_head_front', (0, 4, 1.62), (math.radians(90), 0, math.radians(180)), ortho=0.7, objs_visible=karin)
shoot('karin_head_side', (4, 0, 1.62), (math.radians(90), 0, math.radians(90)), ortho=0.7, objs_visible=karin)

# test pose: arms down, elbows bent, one knee raised, head turned
pb = arm.pose.bones
def rot(bone, axis, deg):
    b = pb[bone]
    b.rotation_mode = 'XYZ'
    e = list(b.rotation_euler)
    e['XYZ'.index(axis)] += math.radians(deg)
    b.rotation_euler = e
for side, sgn in (('l_', 1), ('r_', -1)):
    rot(side + 'bicep', 'Z', 0)
for name, axis, deg in ARGS.get('pose', [['l_bicep', 'X', 40], ['r_bicep', 'X', -40], ['l_forearm', 'Z', 50], ['r_thigh', 'X', 45], ['r_shin', 'X', -60], ['head', 'Y', 30], ['torso2', 'X', 15]]):
    rot(name, axis, deg)
bpy.context.view_layer.update()
shoot('pose_front', (0, 4, 1.0), (math.radians(90), 0, math.radians(180)), objs_visible=karin)
shoot('pose_side', (4, 0, 1.0), (math.radians(90), 0, math.radians(90)), objs_visible=karin)
json.dump(stats, open(os.path.join(OUT, 'stats.json'), 'w'), indent=1)
print('PREVIEW DONE', stats)
