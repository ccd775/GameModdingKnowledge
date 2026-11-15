# blender --background <run>/build.blend --python pleat_gap.py -- <run>
# Firefly round 3 measurements on a build (left side; report.json's new_joints lists the left joints):
#   PLEAT  how far the skirt's render pleats sit inside the simulation tube MI_FF_SkirtSim (the tube radius is the
#          outermost render vertex, so the inner folds are below it; a collider must reach that deep to stop the leg)
#   THIGH / CALF  radius of the skin / stocking verts (weight > 0.6) about the bone axis in three bands along the bone
#   TUBE   nearest tube particle to the thigh axis per tenth of the thigh: where a full-size thigh capsule fits at rest
import bpy, sys, os, json
import numpy as np
from mathutils.bvhtree import BVHTree
from mathutils import Vector
argv = sys.argv[sys.argv.index("--") + 1:]
RUN = argv[0]
rep = json.load(open(os.path.join(RUN, "report.json"), encoding="utf-8"))
NJ = {k: np.array([v[0], -v[1], v[2]]) for k, v in rep["new_joints"].items()}   # UE -> Blender (Y negated)
body = bpy.data.objects["SK_Karin_Body"]
me = body.data
mi = {s.material.name: i for i, s in enumerate(body.material_slots) if s.material}
co = np.array([list(v.co) for v in me.vertices])
def faces_of(slot): return [p for p in me.polygons if p.material_index == mi[slot]]
tube_f = faces_of("MI_FF_SkirtSim")
tv = sorted({v for p in tube_f for v in p.vertices}); tix = {v: i for i, v in enumerate(tv)}
bvh = BVHTree.FromPolygons([tuple(co[v]) for v in tv], [[tix[v] for v in p.vertices] for p in tube_f])
sk_v = sorted({v for p in faces_of("MI_FF_SkirtCloth") for v in p.vertices})
axis = np.array([0.0, co[tv, 1].mean()])
d_in = []
for v in sk_v:
    loc, _, _, _ = bvh.find_nearest(Vector(co[v]))
    if loc is None: continue
    r_v = np.hypot(co[v, 0] - axis[0], co[v, 1] - axis[1]); r_t = np.hypot(loc.x - axis[0], loc.y - axis[1])
    d_in.append(r_t - r_v)
d_in = np.array(d_in)
print("PLEAT inside depth cm pct50/75/90/95/max", [round(float(np.percentile(d_in, q)), 2) for q in (50, 75, 90, 95, 100)])
gi = {g.name: g.index for g in body.vertex_groups}
def seg_dist(p, a, b):
    d = b - a; t = ((p - a) @ d) / max(np.dot(d, d), 1e-9)
    return np.linalg.norm(p - (a + np.outer(np.clip(t, 0, 1), d)), axis=1), t
skip = {mi[s] for s in mi if "Skirt" in s or "Sim" in s}
vok = np.ones(len(co), bool)
for p in me.polygons:
    if p.material_index in skip:
        for v in p.vertices: vok[v] = False
for bone, a, b in (("thigh_l", "thigh_l", "calf_l"), ("calf_l", "calf_l", "foot_l")):
    g = gi.get(bone)
    ids = [v.index for v in me.vertices if vok[v.index] and any(x.group == g and x.weight > 0.6 for x in v.groups)]
    d, t = seg_dist(co[ids], NJ[a], NJ[b])
    for lo, hi in ((0.0, 0.3), (0.3, 0.6), (0.6, 0.9)):
        m = (t >= lo) & (t < hi)
        if m.sum(): print(f"{bone.upper()} t{lo}-{hi} n={m.sum()} r pct50/85/95/max", [round(float(np.percentile(d[m], q)), 2) for q in (50, 85, 95, 100)])
d, t = seg_dist(co[tv], NJ["thigh_l"], NJ["calf_l"])
for k in range(10):
    m = (t >= k / 10) & (t < (k + 1) / 10)
    if m.sum(): print(f"TUBE to thigh_l axis t{k / 10:.1f}: min {d[m].min():.2f}")
print("PLEAT_OK")
