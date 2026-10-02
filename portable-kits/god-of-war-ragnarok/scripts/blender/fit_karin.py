"""Fit a VRM-humanoid FBX onto a GoWR character's bind skeleton and export baked mesh data.

Usage: blender --background --factory-startup --python fit_karin.py -- <src.fbx> <rigspec.json> <out_dir> [scale]
rigspec.json comes from gowr/rigspec.py (bone roles + bind joints in Blender space).
"""
import bpy, sys, json, os, math
import numpy as np
from mathutils import Vector, Matrix, Quaternion

argv = sys.argv[sys.argv.index('--') + 1:]
SRC, KJ, OUT = argv[0], argv[1], argv[2]
SCALE = float(argv[3]) if len(argv) > 3 else 1.6
os.makedirs(OUT, exist_ok=True)

spec = json.load(open(KJ))
J = {int(k): Vector(v) for k, v in spec['joints'].items()}

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=SRC)
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
meshes = [o for o in bpy.data.objects if o.type == 'MESH']

# --- bake object transforms and the uniform scale into data -------------------------------
for o in bpy.data.objects:
    o.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
S = Matrix.Scale(SCALE, 4)
arm.matrix_world = S @ arm.matrix_world
for o in meshes:
    if o.parent is None:
        o.matrix_world = S @ o.matrix_world
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

for o in meshes:
    if o.data.shape_keys:
        o.shape_key_clear()

# free every bone so pose translations are honoured
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT')
for eb in arm.data.edit_bones:
    eb.use_connect = False
bpy.ops.object.mode_set(mode='OBJECT')

# --- target pose ----------------------------------------------------------------------------
# GoW characters: left limbs sit at Blender +X (game -X)
side = {}
for s in ('Left', 'Right'):
    d = dict(spec[s])
    d['F'] = {f: d[f] for f in ('Index', 'Middle', 'Ring', 'Little', 'Thumb')}
    side[s] = d
def mirror_toe_tip(s):
    return J[side[s]['toe_tip']].copy()

# name -> (move_head_to | None, aim_point, child_for_rest_vector, roll_ref)
T = {}
for s, d in side.items():
    T[f'{s}Shoulder'] = (None, J[d['sh']], f'{s}UpperArm', None)
    T[f'{s}UpperArm'] = (J[d['sh']], J[d['el']], f'{s}LowerArm', None)
    T[f'{s}LowerArm'] = (J[d['el']], J[d['wr']], f'{s}Hand', None)
    T[f'{s}Hand'] = (J[d['wr']], J[d['F']['Middle'][0]], f'{s}MiddleProximal', (f'{s}IndexProximal', f'{s}LittleProximal', J[d['F']['Index'][0]], J[d['F']['Little'][0]]))
    for fname in ('Index', 'Middle', 'Ring', 'Little'):
        ch = d['F'][fname]
        T[f'{s}{fname}Proximal'] = (None, None, f'{s}{fname}Intermediate', None, (J[ch[0]], J[ch[1]]))
        T[f'{s}{fname}Intermediate'] = (None, None, f'{s}{fname}Distal', None, (J[ch[1]], J[ch[2]]))
        T[f'{s}{fname}Distal'] = (None, None, None, None, (J[ch[2]], J[ch[3]]))
    th = d['F']['Thumb']
    T[f'{s}ThumbProximal'] = (None, None, f'{s}ThumbIntermediate', None, (J[th[0]], J[th[1]]))
    T[f'{s}ThumbIntermediate'] = (None, None, f'{s}ThumbDistal', None, (J[th[1]], J[th[2]]))
    T[f'{s}ThumbDistal'] = (None, None, None, None, (J[th[2]], J[th[3]]))
    T[f'{s}UpperLeg'] = (J[d['hip']], J[d['kn']], f'{s}LowerLeg', None)
    T[f'{s}LowerLeg'] = (J[d['kn']], J[d['an']], f'{s}Foot', None)
    T[f'{s}Foot'] = (J[d['an']], J[d['toe']], f'{s}ToeBase', None)
    T[f'{s}ToeBase'] = (J[d['toe']], mirror_toe_tip(s), None, None)

bones = arm.data.bones
def rest_vec(name, child):
    b = bones[name]
    if child and child in bones:
        return bones[child].head_local - b.head_local
    return b.tail_local - b.head_local

bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='POSE')
pose = arm.pose
order = []
def walk(b):
    order.append(b.name)
    for c in b.children:
        walk(c)
for b in bones:
    if b.parent is None:
        walk(b)

report = {}
for name in order:
    if name not in T:
        continue
    spec = T[name]
    pb = pose.bones[name]
    bpy.context.view_layer.update()
    cur = pb.matrix.copy()
    move, aim, child, roll = spec[0], spec[1], spec[2], spec[3]
    dirpair = spec[4] if len(spec) > 4 else None
    head = move.copy() if move is not None else cur.translation.copy()
    rv = rest_vec(name, child)
    rest_rot = bones[name].matrix_local.to_3x3()
    d_cur = cur.to_3x3() @ (rest_rot.inverted() @ rv)
    if dirpair is not None:
        d_tgt = dirpair[1] - dirpair[0]
    else:
        d_tgt = aim - head
    q = d_cur.rotation_difference(d_tgt)
    newrot = q.to_matrix() @ cur.to_3x3()
    if roll is not None:
        a, b_, ta, tb = roll
        va = newrot @ (rest_rot.inverted() @ (bones[a].head_local - bones[b_].head_local))
        vt = ta - tb
        ax = d_tgt.normalized()
        va_p = (va - ax * va.dot(ax)).normalized()
        vt_p = (vt - ax * vt.dot(ax)).normalized()
        ang = va_p.angle(vt_p)
        if ax.dot(va_p.cross(vt_p)) < 0:
            ang = -ang
        newrot = Quaternion(ax, ang).to_matrix() @ newrot
    M = Matrix.Translation(head) @ newrot.to_4x4()
    pb.matrix = M
    report[name] = dict(head=list(head), angle=math.degrees(d_cur.angle(d_tgt)) if d_cur.length and d_tgt.length else 0)
bpy.context.view_layer.update()
bpy.ops.object.mode_set(mode='OBJECT')

# --- bake the pose into the meshes ----------------------------------------------------------
for o in meshes:
    bpy.context.view_layer.objects.active = o
    for m in list(o.modifiers):
        if m.type == 'ARMATURE':
            bpy.ops.object.modifier_apply(modifier=m.name)

# --- export ---------------------------------------------------------------------------------
summary = {'scale': SCALE, 'pose': report, 'meshes': {}}
for o in meshes:
    me = o.data
    me.calc_loop_triangles()
    V = np.array([v.co[:] for v in me.vertices], np.float32)
    nl = len(me.loops)
    lv = np.zeros(nl, np.int32); me.loops.foreach_get('vertex_index', lv)
    ln = np.zeros(nl * 3, np.float32); me.corner_normals.foreach_get('vector', ln)
    uvl = me.uv_layers.active
    uv = np.zeros(nl * 2, np.float32); uvl.data.foreach_get('uv', uv)
    nt = len(me.loop_triangles)
    tl = np.zeros(nt * 3, np.int32); me.loop_triangles.foreach_get('loops', tl)
    tm = np.zeros(nt, np.int32); me.loop_triangles.foreach_get('material_index', tm)
    groups = [g.name for g in o.vertex_groups]
    wi, ww, wv = [], [], []
    for v in me.vertices:
        for g in v.groups:
            if g.weight > 1e-5:
                wv.append(v.index); wi.append(g.group); ww.append(g.weight)
    mats = [s.material.name if s.material else '' for s in o.material_slots]
    np.savez_compressed(os.path.join(OUT, f'{o.name}.npz'), V=V, loop_v=lv, loop_n=ln.reshape(-1, 3), loop_uv=uv.reshape(-1, 2),
                        tri_loops=tl.reshape(-1, 3), tri_mat=tm, w_vert=np.array(wv, np.int32), w_group=np.array(wi, np.int32),
                        w_weight=np.array(ww, np.float32))
    summary['meshes'][o.name] = dict(groups=groups, materials=mats, verts=len(V), tris=nt)
# final bone heads (posed) for verification
summary['bones_posed'] = {}
for pb in arm.pose.bones:
    summary['bones_posed'][pb.name] = list(pb.head)
json.dump(summary, open(os.path.join(OUT, 'summary.json'), 'w'), indent=1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'karin_fitted.blend'))
print('FIT DONE', len(meshes))
