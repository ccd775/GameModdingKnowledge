# clav_test.py -- <out.png>: rotate both clavicles down (HL idle-like) and render a neck/shoulder close-up
import bpy, sys, math
out = sys.argv[sys.argv.index('--') + 1]
arm = bpy.data.objects['HLArmature']
for o in bpy.data.objects:
    if o.type == 'MESH': o.hide_render = not o.name.startswith('Karin')
bpy.context.view_layer.objects.active = arm; bpy.ops.object.mode_set(mode='POSE')
for s, sg in (('Left', 1), ('Right', -1)):
    pb = arm.pose.bones[s + 'Shoulder']; pb.rotation_mode = 'XYZ'
    # rotate about the world forward axis so the outer end drops
    import mathutils
    m = (arm.matrix_world @ pb.bone.matrix_local).to_3x3().inverted()
    ax = m @ mathutils.Vector((0, 1, 0)) * sg
    pb.rotation_mode = 'AXIS_ANGLE'; pb.rotation_axis_angle = (math.radians(12), ax.x, ax.y, ax.z)
bpy.ops.object.mode_set(mode='OBJECT')
scn = bpy.context.scene; scn.render.engine = 'BLENDER_WORKBENCH'; scn.display.shading.light = 'STUDIO'
scn.render.resolution_x = 800; scn.render.resolution_y = 600
neck = arm.matrix_world @ arm.data.bones['Neck'].head_local
c = bpy.data.cameras.new('c'); c.type = 'ORTHO'; c.ortho_scale = 0.45
co = bpy.data.objects.new('c', c); scn.collection.objects.link(co); scn.camera = co
co.location = (0.25, -1.5, neck.z + 0.02); co.rotation_euler = (math.radians(88), 0, math.radians(10))
scn.render.filepath = out; bpy.ops.render.render(write_still=True); print('CLAV OK')
