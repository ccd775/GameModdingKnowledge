"""Blender (5.0) script: dump Karin FBX mesh + skeleton into an .npz in TotK game space (Y up, +Z forward, meters).

usage: blender -b --factory-startup -P blender_dump_karin.py -- <in.fbx> <out.npz>
Per-corner data is de-duplicated into unique vertices (pos, normal, uv, object) so it can go straight to BFRES.
"""
import bpy, sys, json
import numpy as np
from mathutils import Matrix

argv = sys.argv[sys.argv.index('--') + 1:]
src, out = argv
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=src)

# Blender world (Z up, character faces -Y) -> game (Y up, faces +Z): (x, y, z) -> (x, z, -y)
C = Matrix(((1, 0, 0, 0), (0, 0, 1, 0), (0, -1, 0, 0), (0, 0, 0, 1)))
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
bone_names = [b.name for b in arm.data.bones]
bone_index = {n: i for i, n in enumerate(bone_names)}
bone_mats = []
bone_tails = []
for b in arm.data.bones:
    m = C @ arm.matrix_world @ b.matrix_local
    bone_mats.append(np.array(m))
    bone_tails.append(np.array((C @ arm.matrix_world @ b.tail_local.to_4d()))[:3] if False else np.array(C @ arm.matrix_world @ b.tail_local)[:3])
bone_parent = [bone_index[b.parent.name] if b.parent else -1 for b in arm.data.bones]

all_pos, all_nrm, all_uv, all_obj, all_mat = [], [], [], [], []
all_w = []  # list of dict bone->w
tris = []
objects, materials = [], []
for ob in [o for o in bpy.data.objects if o.type == 'MESH']:
    me = ob.data
    if me.shape_keys:  # use basis (rest) coordinates
        basis = me.shape_keys.reference_key
        co = np.array([v.co for v in basis.data])
    else:
        co = np.array([v.co for v in me.vertices])
    M = np.array(C @ ob.matrix_world)
    R = np.array((C @ ob.matrix_world).to_3x3().inverted().transposed())
    co_w = (np.c_[co, np.ones(len(co))] @ M.T)[:, :3]
    me.calc_loop_triangles()
    cn = np.array([n.vector for n in me.corner_normals]) if hasattr(me, 'corner_normals') else np.array([l.normal for l in me.loops])
    cn = cn @ R.T
    cn /= np.maximum(np.linalg.norm(cn, axis=1, keepdims=True), 1e-9)
    uvl = me.uv_layers.active
    uv = np.array([d.uv for d in uvl.data]) if uvl else np.zeros((len(me.loops), 2))
    gnames = {g.index: g.name for g in ob.vertex_groups}
    vw = []
    for v in me.vertices:
        d = {}
        for g in v.groups:
            n = gnames.get(g.group)
            if n in bone_index and g.weight > 1e-5: d[n] = d.get(n, 0) + g.weight
        vw.append(d)
    obj_id = len(objects); objects.append(ob.name)
    mat_ids = []
    for m in me.materials:
        nm = m.name if m else 'None'
        if nm not in materials: materials.append(nm)
        mat_ids.append(materials.index(nm))
    key2idx = {}
    loop_vert = np.array([l.vertex_index for l in me.loops])
    for t in me.loop_triangles:
        tri = []
        for li in t.loops:
            vi = int(loop_vert[li])
            key = (vi, tuple(np.round(cn[li], 4)), tuple(np.round(uv[li], 5)))
            idx = key2idx.get(key)
            if idx is None:
                idx = len(all_pos); key2idx[key] = idx
                all_pos.append(co_w[vi]); all_nrm.append(cn[li]); all_uv.append(uv[li])
                all_obj.append(obj_id); all_w.append(vw[vi])
            tri.append(idx)
        tris.append((tri[0], tri[1], tri[2], mat_ids[t.material_index] if mat_ids else 0, obj_id))

# weights as dense top-8
W_idx = np.full((len(all_w), 8), -1, np.int32); W_val = np.zeros((len(all_w), 8), np.float32)
for i, d in enumerate(all_w):
    items = sorted(d.items(), key=lambda kv: -kv[1])[:8]
    for j, (n, w) in enumerate(items):
        W_idx[i, j] = bone_index[n]; W_val[i, j] = w
np.savez_compressed(out, pos=np.array(all_pos, np.float32), nrm=np.array(all_nrm, np.float32), uv=np.array(all_uv, np.float32),
                    obj=np.array(all_obj, np.int32), tris=np.array(tris, np.int32), w_idx=W_idx, w_val=W_val,
                    bone_mats=np.array(bone_mats, np.float32), bone_tails=np.array(bone_tails, np.float32), bone_parent=np.array(bone_parent, np.int32),
                    meta=json.dumps({'bones': bone_names, 'objects': objects, 'materials': materials}))
print('DUMPED', out, len(all_pos), 'verts', len(tris), 'tris', len(bone_names), 'bones')
