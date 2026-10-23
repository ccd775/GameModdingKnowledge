"""Thigh / hip skin poking through the skirt in vanilla walk/run frames. Per frame, three modes: dyng nodes rigid on
their anchors ('none'), the simulated skirt nodes pushed inward to their current collision limits ('current'), and the
same with the hip-level ring kept at 98 % of its rest distance ('snug', the snug_depth rule of karin_build.py); the
pinned _002 and _001 segments turn with their look-ats. Skin vertices covered at rest are ray cast along their
normals against the skirt (nearest-face signed distances are useless on pleats).
blender -b <W3_WORK>/blend/karin_fit.blend --python scripts/checks/blender/skirt_walk_sink.py -- <spec> <out_prefix> <anim>[,<anim>...] [nframes]
(W3_WORK set; anims from man_geralt_movement.w2anims, e.g. the walk / run / sprint cycles). Skirt bone names
(Skirt*, *_001, *_002, *_end) are Karin's."""
import bpy, sys, json, math, importlib, addon_utils, os
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))   # kit scripts/
import w3paths  # noqa: E402
argv = sys.argv[sys.argv.index('--') + 1:]
spec = json.load(open(argv[0])); out = argv[1]; anims = argv[2].split(','); NF = int(argv[3]) if len(argv) > 3 else 8
MOD = w3paths.addon_module()
addon_utils.enable(MOD, default_set=True)
U = w3paths.work_dir('uncook')
bpy.context.preferences.addons[MOD].preferences.uncook_path = U
dca = importlib.import_module(MOD + '.CR2W.dc_anims')
ia = importlib.import_module(MOD + '.importers.import_anims')
RIG = U + r'characters\base_entities\man_base\man_base.w2rig'
PATH = U + r'animations\man\movement\man_geralt_movement.w2anims'
body = bpy.data.objects['karin_body_lod0']
arm = body.modifiers['Armature'].object
mw = arm.matrix_world
gi = {g.index: g.name for g in body.vertex_groups}
dyng_roots = {n['name'] for n in spec['nodes']}
def wsum(v, pred):
    return sum(g.weight for g in v.groups if pred(gi[g.group]))
me = body.data
skirt = set(); legs = set()
LEGB = ('l_thigh', 'r_thigh', 'l_legRoll', 'r_legRoll', 'l_legRoll2', 'r_legRoll2', 'l_kneeRoll', 'r_kneeRoll', 'pelvis')
for v in me.vertices:
    s = wsum(v, lambda n: n.startswith('Skirt'))
    if s > 0:
        skirt.add(v.index)
    elif wsum(v, lambda n: n in LEGB) > 0.5 and wsum(v, lambda n: n not in LEGB and n in arm.data.bones and arm.data.bones[n].parent is None and n != 'pelvis') == 0:
        legs.add(v.index)
sfaces = [p for p in me.polygons if all(i in skirt for i in p.vertices)]
# boundary faces (hem / waist edges): skip them as nearest hits
from collections import Counter
ec = Counter()
for p in sfaces:
    for e in p.edge_keys:
        ec[e] += 1
bnd = {k for k, p in enumerate(sfaces) if any(ec[e] == 1 for e in p.edge_keys)}
print('SKIRT verts', len(skirt), 'faces', len(sfaces), 'boundary faces', len(bnd), 'leg verts', len(legs))
dg = bpy.context.evaluated_depsgraph_get()
def snapshot():
    dg.update()
    ev = body.evaluated_get(dg)
    m = ev.to_mesh()
    co = [body.matrix_world @ v.co for v in m.vertices]
    nr = [(body.matrix_world.to_3x3() @ v.normal).normalized() for v in m.vertices]
    ev.to_mesh_clear()
    return co, nr
def measure(cn, ref=None):
    # ray along the skin normal: hits the skirt -> covered (negative = gap); misses outward but hits the skirt
    # inward -> the skin is outside the skirt by that distance (pleat-proof, unlike nearest-face normals)
    co, nr = cn
    tree = BVHTree.FromPolygons(co, [tuple(p.vertices) for p in sfaces], all_triangles=False)
    res = {}
    for i in legs:
        h = tree.ray_cast(co[i] + nr[i] * 1e-4, nr[i], 0.2)
        if h[0] is not None:
            res[i] = (-h[3], h[2])
            continue
        h = tree.ray_cast(co[i] - nr[i] * 1e-4, -nr[i], 0.2)
        if h[0] is not None:
            res[i] = (h[3], h[2])
    return res
def delta(nm):
    pb = arm.pose.bones[nm]
    return (mw @ pb.matrix) @ (mw @ pb.bone.matrix_local).inverted()
def pose_dyng():
    # every dyng node rigid with its anchor: delta(node) = delta(dyng parent), also through nodes that are not
    # mesh bones (e.g. Skirt_root)
    D = {}
    for n in spec['nodes']:
        b = arm.data.bones.get(n['name'])
        if b is not None and b.parent is None and n['parent'] in D:
            D[n['name']] = D[n['parent']]
            arm.pose.bones[n['name']].matrix = mw.inverted() @ D[n['name']] @ mw @ b.matrix_local
        elif b is not None and not (b.parent is None and n['name'] != 'pelvis' and n['parent'] != 'Root'):
            D[n['name']] = delta(n['name'])
        elif n['parent'] in D:
            D[n['name']] = D[n['parent']]
    bpy.context.view_layer.update()
    return D
rest = measure(snapshot())
covered = {i for i, (s, f) in rest.items() if s < 0 and s > -0.15}
print('REST covered', len(covered), 'outside(rest)', sum(1 for s, f in rest.values() if s > 0))
import numpy as np
SN = spec['nodes']; sidx = {n['name']: k for k, n in enumerate(SN)}
Wd = {}
def wspec(k):
    if k in Wd: return Wd[k]
    n = SN[k]; L = Matrix(((n['local'][0][0], n['local'][1][0], n['local'][2][0], n['local'][3][0]),
                           (n['local'][0][1], n['local'][1][1], n['local'][2][1], n['local'][3][1]),
                           (n['local'][0][2], n['local'][1][2], n['local'][2][2], n['local'][3][2]), (0, 0, 0, 1)))
    p = n['parent_index']; M = L if p < 0 else wspec(p) @ L; Wd[k] = M; return M
colls = {}
for l in spec['links']:
    if l['type'] == 1:
        colls.setdefault(l['b'], []).append((l['a'], l['length']))
axis = wspec(sidx['pelvis']).translation
RZ90 = Matrix.Rotation(math.radians(90), 4, 'Z')
def sink_posed(D, sel='both', margin_override=None):
    """skirt sim nodes pushed horizontally toward the posed pelvis axis until a collision link (posed proxies) or the
    cap stops them; _002 bones then aim at their _end node. margin_override(name, proxy, bind_len, rest) -> length"""
    W = lambda k: D[SN[k]['name']] @ wspec(k)
    ax = W(sidx['pelvis']).translation
    moved = {}
    for k, n in enumerate(SN):
        if not n['name'].startswith('Skirt') or n['distance'] <= 0:
            continue
        hip = not n['name'].endswith('_end')
        if (sel == 'hip' and not hip) or (sel == 'hem' and hip):
            continue
        p = W(k).translation
        d = Vector((ax.x - p.x, ax.y - p.y, 0)).normalized()
        cl = []
        for a, L in colls.get(k, []):
            if margin_override:
                L = margin_override(n['name'], SN[a]['name'], L, (wspec(k).translation - wspec(a).translation).length)
            cl.append((W(a).translation, L))
        t = 0.0
        while t < n['distance']:
            q = p + d * (t + 0.001)
            if any((q - c).length < L for c, L in cl):
                break
            t += 0.001
        moved[n['name']] = (t, d * t)
    for name, (t, off) in moved.items():
        if name.endswith('_end'):
            continue
        b = arm.data.bones[name]
        k = sidx[name]; ke = sidx[name + '_end']
        p0 = W(k).translation; e0 = W(ke).translation
        p1 = p0 + off; e1 = e0 + moved.get(name + '_end', (0, Vector()))[1]
        R = (e0 - p0).rotation_difference(e1 - p1).to_matrix().to_4x4()
        Dm = Matrix.Translation(p1) @ R @ Matrix.Translation(-p0)
        arm.pose.bones[name].matrix = mw.inverted() @ Dm @ D[name] @ mw @ b.matrix_local
        # the pinned _001 node looks at _002: it turns about its own position toward the moved _002
        up = name[:-4] + '_001'
        if LOOKAT_001 and up in arm.data.bones:
            ku = sidx[up]; u0 = W(ku).translation
            Ru = (p0 - u0).rotation_difference(p1 - u0).to_matrix().to_4x4()
            Du = Matrix.Translation(u0) @ Ru @ Matrix.Translation(-u0)
            arm.pose.bones[up].matrix = mw.inverted() @ Du @ D[up] @ mw @ arm.data.bones[up].matrix_local
    bpy.context.view_layer.update()
    return {k: v[0] for k, v in moved.items()}
LOOKAT_001 = True
def snug(name, proxy, L, rest):
    return rest * 0.98 if not name.endswith('_end') else L
res = {}
for an in anims:
    s_ = dca.load_bin_anims_single(PATH, an, rigPath=RIG)
    ia.import_anim(bpy.context, PATH, [e for e in s_.animations if e.animation.name == an][0], override_select=arm)
    f0, f1 = arm.animation_data.action.frame_range
    for k in range(NF):
        fr = int(round(f0 + (f1 - f0) * k / NF))
        bpy.context.scene.frame_set(fr)
        D = pose_dyng()
        for mode in ('none', 'current', 'snug'):
            D = pose_dyng()
            if mode != 'none':
                sink_posed(D, 'both', snug if mode == 'snug' else None)
            m = measure(snapshot())
            poke = [(i, m[i][0]) for i in covered if i in m and 0.002 < m[i][0] < 0.12]   # > 12 cm: ray reached the far side
            r = res.setdefault(mode, [0, 0.0, set()])
            r[0] = max(r[0], len(poke)); r[1] = max([r[1]] + [x for i, x in poke]); r[2] |= {i for i, x in poke}
            print('FRAME %-36s %3d %-7s poke=%3d max=%.3f' % (an, fr, mode, len(poke), max([0] + [x for i, x in poke])))
    arm.animation_data_clear()
    for pb in arm.pose.bones:
        pb.matrix_basis.identity()
    bpy.context.view_layer.update()
for mode, (c, mx, vs) in res.items():
    print('SUMMARY %-8s max_verts=%d max_depth=%.3f distinct=%d' % (mode, c, mx, len(vs)))
json.dump({m: sorted(v[2]) for m, v in res.items()}, open(out + '_ws.json', 'w'))
