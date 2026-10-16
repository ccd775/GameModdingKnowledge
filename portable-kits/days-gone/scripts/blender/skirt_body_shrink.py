# Move the body skin that the skirt covers inward a little (Blender 4.2 background), so the hips / upper thighs do not
# come out through the skirt when the legs swing (t24-t26: side-rear at panty height while running; the skirt there
# sits close to its waist pivot, so plate physics cannot move it out of the way).
#
# usage: blender -b <run>/build.blend --python skirt_body_shrink.py -- <out.npz> [max_cm]
#
# Covered = a Body-material vertex whose outward horizontal ray hits the skirt (faces weighted to KO_Skirt_*) within
# 8 cm. Shrink = max_cm (default 2.0) along the vertex normal, faded to 0 from 8 cm above the lowest hem point down to
# 2 cm above it (the thighs below the hem stay untouched) and from 93 to 98 cm (waist), then Laplacian-smoothed over the
# body so the edge of the covered area has no step. The npz holds old / new positions in UE space (x, -y, z), matched
# against the cooked vertex buffer by position (pytools/skelmesh_positions.py).
import bpy, sys
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

argv = sys.argv[sys.argv.index("--") + 1:]
out = argv[0]
max_cm = float(argv[1]) if len(argv) > 1 else 2.0
obj = bpy.data.objects["deacon_head_standard"]
me = obj.data
n = len(me.vertices)
co = np.array([v.co for v in me.vertices], dtype=np.float64)
nor = np.array([v.normal for v in me.vertices], dtype=np.float64)
names = {g.index: g.name for g in obj.vertex_groups}
skirt_w = np.zeros(n)
for v in me.vertices:
    for g in v.groups:
        if names[g.group].startswith("KO_Skirt"):
            skirt_w[v.index] += g.weight
mats = [s.material.name if s.material else "" for s in obj.material_slots]
body_m = mats.index("MI_Karin_Body")
on_body = np.zeros(n, bool); on_other = np.zeros(n, bool)
skirt_polys = []
for p in me.polygons:
    vs = list(p.vertices)
    if p.material_index == body_m:
        on_body[vs] = True
    else:
        on_other[vs] = True
    if all(skirt_w[i] > 0.5 for i in vs):
        skirt_polys.append(vs)
body = on_body & ~on_other & (skirt_w < 0.01)
skirt_v = np.unique(np.concatenate([np.array(p) for p in skirt_polys]))
hem = co[skirt_v, 2].min()
bvh = BVHTree.FromPolygons([Vector(c) for c in co], skirt_polys)

def ramp(z):
    lo = np.clip((z - (hem + 2.0)) / 6.0, 0, 1)
    hi = np.clip((98.0 - z) / 5.0, 0, 1)
    return lo * hi

s = np.zeros(n)
covered = 0
for i in np.where(body & (co[:, 2] > hem) & (co[:, 2] < 99))[0]:
    h = Vector((nor[i, 0], nor[i, 1], 0.0))
    if h.length < 0.3:
        continue
    h.normalize()
    hit = bvh.ray_cast(Vector(co[i]), h, 8.0)
    if hit[0] is not None:
        s[i] = 1.0; covered += 1
# smooth the covered mask over body edges, then fade by height
adj = [[] for _ in range(n)]
for e in me.edges:
    a, b = e.vertices
    if body[a] and body[b]:
        adj[a].append(b); adj[b].append(a)
band = body & (co[:, 2] > hem - 2) & (co[:, 2] < 100)
idx = np.where(band)[0]
for _ in range(12):
    t = s.copy()
    for i in idx:
        if adj[i]:
            t[i] = 0.5 * s[i] + 0.5 * np.mean(s[adj[i]])
    s = t
s = np.clip(s * 1.5, 0, 1) * ramp(co[:, 2]) * body
# smoothed normals for the direction
nn = nor.copy()
for _ in range(3):
    t = nn.copy()
    for i in idx:
        if adj[i]:
            t[i] = nn[i] + nn[adj[i]].sum(0)
    nn = t / np.linalg.norm(t, axis=1, keepdims=True)
moved = np.where(s * max_cm > 0.05)[0]
new = co[moved] - nn[moved] * (s[moved] * max_cm)[:, None]
flip = np.array([1.0, -1.0, 1.0])
np.savez(out, old=co[moved] * flip, new=new * flip)
print("SHRINK_OK", out, "body verts", int(body.sum()), "covered", covered, "moved", len(moved),
      "hem %.1f" % hem, "max %.2f" % (s.max() * max_cm), "z range %.1f..%.1f" % (co[moved, 2].min(), co[moved, 2].max()))
