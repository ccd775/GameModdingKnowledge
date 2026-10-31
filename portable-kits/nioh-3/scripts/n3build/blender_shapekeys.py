"""Blender (background): dump every shape key of the Karin_Original FBX meshes as world-space vertex deltas.

usage: blender --factory-startup --background --python blender_shapekeys.py -- <fbx> <out_dir>
Writes <out_dir>/shapekeys.npz ("<mesh>__<index>" -> (n, 3) float32 delta, Blender world space, metres) and
<out_dir>/shapekeys.json ({mesh: [{index, name, moved (vertices with |delta| > 1e-5), max (metres)}]}).
Deltas are taken from the key blocks relative to Basis, so the prefab's applied key mix does not matter.
"""
import json
import os
import sys

import bpy
import numpy as np

argv = sys.argv[sys.argv.index('--') + 1:]
fbx, out = argv[0], argv[1]
os.makedirs(out, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=fbx)

arrays, info = {}, {}
for ob in sorted((o for o in bpy.context.scene.objects if o.type == 'MESH'), key=lambda o: o.name):
    keys = ob.data.shape_keys
    if not keys:
        continue
    basis = keys.reference_key
    n = len(ob.data.vertices)
    b = np.empty(n * 3, np.float32); basis.data.foreach_get('co', b); b = b.reshape(-1, 3)
    R = np.array(ob.matrix_world)[:3, :3]
    rows = []
    for i, k in enumerate(keys.key_blocks):
        if k == basis:
            continue
        c = np.empty(n * 3, np.float32); k.data.foreach_get('co', c); c = c.reshape(-1, 3)
        d = ((c - b) @ R.T).astype(np.float32)
        mag = np.linalg.norm(d, axis=1)
        moved = int((mag > 1e-5).sum())
        rows.append({'index': i, 'name': k.name, 'moved': moved, 'max': float(mag.max())})
        if moved:
            arrays[f'{ob.name}__{i}'] = d
    info[ob.name] = rows
np.savez_compressed(os.path.join(out, 'shapekeys.npz'), **arrays)
with open(os.path.join(out, 'shapekeys.json'), 'w', encoding='utf-8') as f:
    json.dump(info, f, ensure_ascii=False, indent=1)
print('meshes with keys:', {k: len(v) for k, v in info.items()})
