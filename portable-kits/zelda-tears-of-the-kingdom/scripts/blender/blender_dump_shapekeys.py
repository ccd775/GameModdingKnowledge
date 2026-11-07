"""Blender (5.0): dump shape-key deltas of Karin's meshes, indexed exactly like blender_dump_karin.py's unique vertices.

usage: blender -b --factory-startup -P blender_dump_shapekeys.py -- <in.fbx> <out.npz> [object ...]
Writes: names (json), idx (unique-vertex indices of the listed objects), deltas [K, n, 3] in game space (Karin's own scale).
"""
import bpy, sys, json
import numpy as np
from mathutils import Matrix

argv = sys.argv[sys.argv.index('--') + 1:]
src, out, wanted = argv[0], argv[1], set(argv[2:]) or {'Body'}
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=src)
C = Matrix(((1, 0, 0, 0), (0, 0, 1, 0), (0, -1, 0, 0), (0, 0, 0, 1)))

n_unique = 0
keys_out = {}   # key name -> list of (unique idx, delta)
idx_all = []
for ob in [o for o in bpy.data.objects if o.type == 'MESH']:
    me = ob.data
    M3 = np.array((C @ ob.matrix_world).to_3x3())
    me.calc_loop_triangles()
    cn = np.array([n.vector for n in me.corner_normals]) if hasattr(me, 'corner_normals') else np.array([l.normal for l in me.loops])
    R = np.array((C @ ob.matrix_world).to_3x3().inverted().transposed())
    cn = cn @ R.T
    cn /= np.maximum(np.linalg.norm(cn, axis=1, keepdims=True), 1e-9)
    uvl = me.uv_layers.active
    uv = np.array([d.uv for d in uvl.data]) if uvl else np.zeros((len(me.loops), 2))
    loop_vert = np.array([l.vertex_index for l in me.loops])
    key2idx = {}; uvert = []   # unique idx -> source vertex index (same dedup as blender_dump_karin.py)
    for t in me.loop_triangles:
        for li in t.loops:
            vi = int(loop_vert[li])
            key = (vi, tuple(np.round(cn[li], 4)), tuple(np.round(uv[li], 5)))
            if key not in key2idx:
                key2idx[key] = n_unique + len(uvert); uvert.append(vi)
    if ob.name in wanted and me.shape_keys:
        basis = np.array([v.co for v in me.shape_keys.reference_key.data])
        src_idx = np.array(uvert)
        idx_all.append(np.arange(n_unique, n_unique + len(uvert)))
        for kb in me.shape_keys.key_blocks:
            if kb == me.shape_keys.reference_key: continue
            d = (np.array([v.co for v in kb.data]) - basis) @ M3.T
            keys_out.setdefault(kb.name, []).append(d[src_idx])
        print('object', ob.name, 'unique verts', len(uvert), 'keys', len(me.shape_keys.key_blocks) - 1)
    n_unique += len(uvert)

names = list(keys_out)
deltas = np.stack([np.concatenate(keys_out[k]) for k in names]).astype(np.float32)
np.savez_compressed(out, idx=np.concatenate(idx_all).astype(np.int32), deltas=deltas, names=json.dumps(names, ensure_ascii=True))
print('DUMPED', out, 'total unique', n_unique, 'keys', len(names), deltas.shape)
