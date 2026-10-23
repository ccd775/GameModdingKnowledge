"""Tiny skinned stub mesh (one 0.1 mm triangle inside the neck) used to hide a vanilla mesh.

blender --background --factory-startup --python scripts/blender/make_stub_mesh.py -- '{"out": "...w2mesh", "bone": "neck"}'
(W3_WORK set: the rig is read from <W3_WORK>\\uncook\\; "rig" in the JSON overrides it)
"""
import bpy
import json
import os
import sys
import importlib
import addon_utils

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # kit scripts/
import w3paths  # noqa: E402

ARGS = json.loads(sys.argv[sys.argv.index('--') + 1])
MOD = w3paths.addon_module()
bpy.ops.wm.read_factory_settings(use_empty=True)
addon_utils.enable(MOD, default_set=True)
irig = importlib.import_module(MOD + '.importers.import_rig')
em = importlib.import_module(MOD + '.exporters.export_mesh')
irig.import_w3_rig(ARGS.get('rig') or w3paths.work_dir('uncook') + 'characters\\base_entities\\man_base\\man_base.w2rig', ns='')
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
bone = ARGS.get('bone', 'neck')
c = arm.matrix_world @ arm.data.bones[bone].head_local
e = 0.0001
me = bpy.data.meshes.new('stub_lod0')
me.from_pydata([(c.x, c.y, c.z), (c.x + e, c.y, c.z), (c.x, c.y, c.z + e)], [], [(0, 1, 2)])
me.uv_layers.new(name='UVMap')
mat = bpy.data.materials.new('stub')
me.materials.append(mat)
o = bpy.data.objects.new('stub_lod0', me)
bpy.context.scene.collection.objects.link(o)
g = o.vertex_groups.new(name=bone)
g.add([0, 1, 2], 1.0, 'REPLACE')
o.parent = arm
o.modifiers.new('Armature', 'ARMATURE').object = arm


def patched(mesh_bl, mesh_obj=None, material_slot_indices=None):
    return [{'name': 'stub', 'material_slot_index': 0,
             'witcher_props': {'name': 'stub', 'enableMask': False, 'local': True,
                               'base_custom': r'engine\materials\graphs\pbr_std.w2mg', 'input_props': []}}]


em.get_mesh_material_info = patched
em.do_export_mesh(bpy.context, ARGS['out'], armature=arm, meshes=[o], col_tri_meshes=[], export_col_tri=False,
                  keep_intermediate_json=False, use_native_writer=True, strip_material_names=False)
print('STUB DONE', ARGS['out'])
