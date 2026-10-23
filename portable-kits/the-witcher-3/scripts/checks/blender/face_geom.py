"""Rest geometry of the face vs. the head-hair dyng nodes, in the W3 head bone frame (X up, Y forward, Z left), and a
grid search for the head collision centre: the point C where (hair vertex - C) best matches the face normal under the
bangs and side hair (karin_build.py CFG dyng_head_centre).
blender -b <W3_WORK>/blend/karin_fit.blend --python scripts/checks/blender/face_geom.py -- <dyng spec>
Needs the face build (karin_face_lod0) in the blend; bone / group names (Hair_front*, Hair_side*) are Karin's."""
import bpy, sys, json, math
from mathutils import Vector, Matrix
from mathutils.kdtree import KDTree
spec = json.load(open(sys.argv[sys.argv.index('--') + 1]))
RZ90 = Matrix.Rotation(math.radians(90), 4, 'Z')
arm = bpy.data.objects['man_base']
H = arm.matrix_world @ arm.data.bones['head'].matrix_local @ RZ90
Hi = H.inverted()
face = bpy.data.objects['karin_face_lod0']
fv = [Hi @ (face.matrix_world @ v.co) for v in face.data.vertices]
kd = KDTree(len(fv))
for i, p in enumerate(fv):
    kd.insert(p, i)
kd.balance()
xs = [p.x for p in fv]; ys = [p.y for p in fv]; zs = [p.z for p in fv]
print('FACE bbox head-frame X(up) %.3f..%.3f  Y(fwd) %.3f..%.3f  Z(left) %.3f..%.3f' % (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)))
# vertex normals for direction
fn = [(Hi.to_3x3() @ (face.matrix_world.to_3x3() @ v.normal)).normalized() for v in face.data.vertices]
body = bpy.data.objects['karin_body_lod0']
groups = {g.index: g.name for g in body.vertex_groups}
names = [n['name'] for n in spec['nodes']]
idx = {n: i for i, n in enumerate(names)}
# node rest positions from the export armature bones
def bpos(n):
    return Hi @ (arm.matrix_world @ arm.data.bones[n].matrix_local).translation
sel = [n for n in names if n.startswith(('Hair_front', 'Hair_side', 'Hair_tail', 'Ribbon_L', 'Ribbon_R'))]
for n in [n for n in sel if n in arm.data.bones]:
    p = bpos(n)
    co, i, d = kd.find(p)
    print('NODE %-22s cap=%.3f pos=(%.3f %.3f %.3f) face_d=%.3f nrm=(%.2f %.2f %.2f)' % (
        n, spec['nodes'][idx[n]]['distance'], p.x, p.y, p.z, d, fn[i].x, fn[i].y, fn[i].z))
# hair vertices dominated by front/side bones: distance to the face
mw = body.matrix_world
stats = {}
for v in body.data.vertices:
    if not v.groups:
        continue
    g = max(v.groups, key=lambda g: g.weight)
    gn = groups[g.group]
    if not gn.startswith(('Hair_front', 'Hair_side')):
        continue
    p = Hi @ (mw @ v.co)
    co, i, d = kd.find(p)
    # signed: in front of the face surface along its normal
    s = (p - co).dot(fn[i])
    stats.setdefault(gn, []).append((d, s))
for gn, l in sorted(stats.items()):
    ds = sorted(d for d, s in l)
    neg = sum(1 for d, s in l if s < 0)
    print('HAIRV %-22s n=%4d min_d=%.4f p10=%.4f p50=%.4f behind_face=%d' % (gn, len(l), ds[0], ds[len(ds) // 10], ds[len(ds) // 2], neg))
# centroid and candidate sphere centres: angle between (node - C) and the face normal at the nearest face point
import itertools
c = sum(fv, Vector()) / len(fv)
print('CENTROID %.3f %.3f %.3f' % tuple(c))
pts = []
for v in body.data.vertices:
    if not v.groups:
        continue
    g = max(v.groups, key=lambda g: g.weight)
    if groups[g.group].startswith(('Hair_front', 'Hair_side')):
        p = Hi @ (mw @ v.co)
        co, i, d = kd.find(p)
        if d < 0.03:
            pts.append((p, fn[i]))
def score(C):
    a = [math.degrees((p - C).angle(nv)) for p, nv in pts]
    a.sort()
    return sum(a) / len(a), a[int(len(a) * 0.9)]
best = []
for x in [i * 0.01 for i in range(0, 16)]:
    for y in [i * 0.01 for i in range(-6, 5)]:
        C = Vector((x, y, 0))
        m, p90 = score(C)
        best.append((m, p90, x, y))
best.sort()
for b in best[:6]:
    print('CENTER mean=%.1f p90=%.1f x=%.2f y=%.2f' % b)
for x, y in ((0.10, 0.0), (0.08, -0.02), (0.12, 0.0)):
    print('CAND x=%.2f y=%.2f' % (x, y), score(Vector((x, y, 0))))
