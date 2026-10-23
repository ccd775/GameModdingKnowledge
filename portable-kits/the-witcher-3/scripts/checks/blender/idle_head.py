"""Head close-up of the idle pose (dyng nodes rigid with their anchors) at several yaws relative to the posed chest
(front, sides, three-quarter), plus the same yaws in the bind pose: the target shape of the bangs, side hair and
twin-tail roots to compare in-game screenshots against. idle_view.py is the whole-body variant.
blender -b <W3_WORK>/blend/karin_fit.blend --python scripts/checks/blender/idle_head.py -- <dyng spec> <out prefix>
(W3_WORK set: Geralt's movement animations and man_base rig are read from <W3_WORK>/uncook/)"""
import bpy, sys, json, math, importlib, addon_utils, os
from mathutils import Matrix, Vector
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))   # kit scripts/
import w3paths  # noqa: E402
argv = sys.argv[sys.argv.index('--') + 1:]
spec = json.load(open(argv[0])); out = argv[1]
nodes = spec['nodes']
MOD = w3paths.addon_module()
addon_utils.enable(MOD, default_set=True)
U = w3paths.work_dir('uncook')
bpy.context.preferences.addons[MOD].preferences.uncook_path = U
dca = importlib.import_module(MOD + '.CR2W.dc_anims')
ia = importlib.import_module(MOD + '.importers.import_anims')
body = bpy.data.objects['karin_body_lod0']
arm = body.modifiers['Armature'].object
scene = bpy.context.scene
for o in bpy.data.objects:
    if o.type == 'MESH':
        o.hide_render = o is not body
scene.render.engine = 'BLENDER_WORKBENCH'
scene.render.resolution_x, scene.render.resolution_y = 700, 700
scene.display.shading.color_type = "TEXTURE"
cam_data = bpy.data.cameras.new('c'); cam_data.lens = 50
cam = bpy.data.objects.new('c', cam_data); scene.collection.objects.link(cam); scene.camera = cam
mw = arm.matrix_world
def delta(nm):
    pb = arm.pose.bones[nm]
    return (mw @ pb.matrix) @ (mw @ pb.bone.matrix_local).inverted()
def shoot(tag, yaws):
    D = delta('torso3')
    f = D.to_3x3() @ Vector((0, 1, 0))
    y0 = math.degrees(math.atan2(f.x, f.y))
    tgt = mw @ arm.pose.bones['head'].head + Vector((0, 0, -0.08))
    for yaw in yaws:
        a = math.radians(y0 + yaw)
        d = Vector((math.sin(a), math.cos(a), 0.05)).normalized()
        cam.location = tgt + d * 1.3
        cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
        scene.render.filepath = f'{out}_{tag}_{yaw}.png'
        bpy.ops.render.render(write_still=True)
YAWS = [0, 30, 60, 90, -30, -60]
shoot('bind', YAWS)
path = U + 'animations\\man\\movement\\man_geralt_movement.w2anims'
s = dca.load_bin_anims_single(path, 'locomotion_idle', rigPath=U + 'characters\\base_entities\\man_base\\man_base.w2rig')
ia.import_anim(bpy.context, path, [e for e in s.animations if e.animation.name == 'locomotion_idle'][0], override_select=arm)
scene.frame_set(0)
bpy.context.view_layer.update()
for n in nodes:
    b = arm.data.bones.get(n['name'])
    if b is None or b.parent is not None or n['parent'] not in arm.pose.bones:
        continue
    arm.pose.bones[n['name']].matrix = mw.inverted() @ delta(n['parent']) @ mw @ b.matrix_local
    bpy.context.view_layer.update()
for nm in ('pelvis', 'torso', 'torso2', 'torso3'):
    print(nm, 'delta euler', [round(math.degrees(v), 1) for v in delta(nm).to_euler()])
shoot('idle', YAWS)
print('VIEW DONE')
