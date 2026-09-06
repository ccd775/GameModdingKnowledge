"""Create a synthetic saved Blend for the source-audit smoke test."""
import sys
from pathlib import Path
import bpy

output = Path(sys.argv[sys.argv.index('--') + 1]).resolve()
if output.exists():
    raise FileExistsError(output)
bpy.ops.wm.read_factory_settings(use_empty=True)
mesh = bpy.data.meshes.new('SyntheticTriangle')
mesh.from_pydata([(0, 0, 0), (1, 0, 0), (0, 1, 0)], [], [(0, 1, 2)])
obj = bpy.data.objects.new('SyntheticMesh', mesh)
bpy.context.scene.collection.objects.link(obj)
bpy.context.view_layer.objects.active = obj
obj.select_set(True)
obj.shape_key_add(name='Basis')
key = obj.shape_key_add(name='SyntheticOffset')
key.data[0].co.z = 0.1
key.value = 0.5
mesh.uv_layers.new(name='UVMap')
obj.data.materials.append(bpy.data.materials.new('SyntheticMaterial'))
output.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(output))
