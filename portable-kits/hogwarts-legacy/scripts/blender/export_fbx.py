# export_fbx.py — blender -b <fit.blend> --python export_fbx.py -- <out_dir> <fit config.json>
# Exports every Karin* part plus Empty / PhysProxy / Skeleton proxies as cm-scale FBX with the armature named "Armature"
# (UE skips that node, so the HL "Reference" bone stays the root).
# Meshes that deform none of Karin's extra bones are exported without them. Those meshes bind to the game's Biped_Skeleton,
# which lacks the extra bones, and HL then crashes in a layered per-bone blend at the first one (Ear_L, dumps of 2026-10-19).
# Skeleton.fbx keeps every bone because the Karin skeleton is built from it.
import bpy, bmesh, sys, os, json
args = sys.argv[sys.argv.index('--') + 1:]
out = args[0]
GAME = {b['name'] for b in json.load(open(json.load(open(args[1], encoding='utf-8'))['skel_json']))['bones']}  # the game skeleton's bones
arm = bpy.data.objects['HLArmature']; arm.name = 'Armature'; arm.data.name = 'Armature'
for o in list(bpy.data.objects):
    if o.type in ('MESH', 'ARMATURE') and o not in (arm,) and o.parent != arm: bpy.data.objects.remove(o)

def add_proxy(name, verts, faces, bone='Hips'):
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update(); me.materials.append(bpy.data.materials.new(name))
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    ob.vertex_groups.new(name=bone).add(list(range(len(verts))), 1.0, 'REPLACE')
    m = ob.modifiers.new('Armature', 'ARMATURE'); m.object = arm; ob.parent = arm
    return ob
add_proxy('Empty', [(0, 0, 0.95), (0.0005, 0, 0.95), (0, 0.0005, 0.95)], [(0, 1, 2)])
bm = bmesh.new(); bmesh.ops.create_cube(bm, size=0.25); cube = bpy.data.meshes.new('cube'); bm.to_mesh(cube); bm.free()
add_proxy('PhysProxy', [tuple((v.co.x, v.co.y, v.co.z + 0.98)) for v in cube.vertices], [tuple(p.vertices) for p in cube.polygons])
add_proxy('SkelProxy', [(0, 0, 0.9), (0.01, 0, 0.9), (0, 0.01, 0.9)], [(0, 1, 2)])

# metres -> centimetres, baked into the data (unparent, scale about the origin, apply, re-parent)
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
for o in meshes:
    mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw
for o in meshes + [arm]:
    o.hide_set(False)  # FBX stays in metres; UE's importer converts to cm
bpy.ops.object.select_all(action='DESELECT')
for o in meshes + [arm]: o.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
for o in meshes:
    o.parent = arm; o.matrix_parent_inverse.identity()
print('arm bone Hips head', arm.data.bones['Hips'].head_local)

def export(ob, path):
    bpy.ops.object.select_all(action='DESELECT'); arm.select_set(True); ob.select_set(True); bpy.context.view_layer.objects.active = arm
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, apply_unit_scale=False, global_scale=1.0, apply_scale_options='FBX_SCALE_NONE',
                             object_types={'ARMATURE', 'MESH'}, add_leaf_bones=False, use_armature_deform_only=False, bake_anim=False,
                             mesh_smooth_type='FACE', use_mesh_modifiers=False, axis_forward='-Y', axis_up='Z')
def extra_bones(o):  # Karin-only bones the mesh deforms
    gi = {g.index: g.name for g in o.vertex_groups if g.name not in GAME}
    return {gi[g.group] for v in o.data.vertices for g in v.groups if g.group in gi and g.weight > 0}
os.makedirs(out, exist_ok=True)
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
full = [o for o in meshes if o.name == 'SkelProxy' or extra_bones(o)]
for o in meshes:
    if o in full: export(o, os.path.join(out, ('Skeleton' if o.name == 'SkelProxy' else o.name) + '.fbx')); print('EXPORTED', o.name, 'all bones')
bpy.ops.object.select_all(action='DESELECT'); arm.select_set(True); bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT')
extra = [e for e in arm.data.edit_bones if e.name not in GAME]
for e in extra: arm.data.edit_bones.remove(e)
bpy.ops.object.mode_set(mode='OBJECT')
for o in meshes:
    if o not in full: export(o, os.path.join(out, o.name + '.fbx')); print('EXPORTED', o.name, 'game bones only,', len(extra), 'removed')
