# Fit Karin-sized collision capsules for the player PhysicsAsset (Blender 4.2 background).
#
# usage: blender -b <run>/build.blend --python fit_colliders.py -- <cooked mesh.uasset> <out colliders.json>
#
# Deacon's bodies are far bigger than Karin (his head capsule pokes 4 cm out of her face, his thigh capsules are 3 cm
# fatter than her thighs), so the chains that collide (pytools/physchain.py "collide") would rest inside them. Output:
# {bone: [a, b, r]} capsules in UE component space (cm) for physchain's "refit":
# - head: vertical capsule as large as possible while every head-colliding chain capsule stays clear by MARGIN;
# - LeftUpLeg/RightUpLeg: along the thigh bone, radius = 75th percentile distance of the thigh skin;
# - hips: horizontal capsule inside the hip/belly skin.
import bpy, sys, json, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # the kit's scripts/
import refskel, physchain

MARGIN = 0.6
mesh, out = sys.argv[sys.argv.index("--") + 1:]
rs = refskel.read(mesh)
names, parents, C = rs["names"], rs["parents"], rs["component"]
bone = {n.lower(): i for i, n in enumerate(names)}
ob = bpy.data.objects["deacon_head_standard"]; me = ob.data
co = np.array([v.co for v in me.vertices]) * np.array([1.0, -1.0, 1.0])   # UE space
mat = np.zeros(len(co), int)
for p in me.polygons:
    mat[list(p.vertices)] = p.material_index
slots = [s.material.name if s.material else "" for s in ob.material_slots]
SKIN = slots.index("MI_Karin_Body")
gname = {g.index: g.name for g in ob.vertex_groups}
dom = np.array([gname[max(v.groups, key=lambda g: g.weight).group] if len(v.groups) else "" for v in me.vertices])

def pt_seg(p, a, b):
    ab = b - a; t = np.clip(((p - a) @ ab) / max(ab @ ab, 1e-9), 0, 1)
    return np.linalg.norm(p - (a + np.outer(t, ab)), axis=1)

caps = physchain.chain_capsules(rs)
def clear_of(prefixes):
    segs = [cap for i, _, cap, _ in caps if any(names[i].startswith(p) for p in prefixes)]
    return lambda a, b, r: min(physchain.seg_dist(a, b, A, B) - r - R for A, B, R in segs)

res = {}
# head: around the skull centre (between the eyes' height and the crown), clear of bangs / side locks / tail roots
head_clear = clear_of([p for p, c in physchain.DEFAULT["chains"].items() if "head" in c.get("collide", [])])
H = C[bone["head"]][:3, 3]
top = float(np.percentile(co[dom == "Head"][:, 2], 99))   # crown (hair) height
best = None
for y in np.arange(-6.0, 6.01, 0.5):
    for z0 in np.arange(H[2] + 4.0, H[2] + 16.01, 1.0):
        for h in np.arange(0.0, 10.01, 1.0):
            a, b = np.array([0.0, H[1] + y, z0]), np.array([0.0, H[1] + y, z0 + h])
            r = min(head_clear(a, b, 0.0) - MARGIN, 11.0, top - 2.0 - b[2])
            vol = np.pi * r * r * h + 4 / 3 * np.pi * r ** 3 if r > 0 else 0
            if best is None or vol > best[0]:
                best = (vol, a, b, r)
res["head"] = best[1:]
# thighs: along the bone from just below the hip joint to above the knee
for s in ("Left", "Right"):
    p0, p1 = C[bone[(s + "UpLeg").lower()]][:3, 3], C[bone[(s + "Leg").lower()]][:3, 3]
    ax = (p1 - p0) / np.linalg.norm(p1 - p0)
    v = co[(mat == SKIN) & (dom == s + "UpLeg")]; t = (v - p0) @ ax
    m = (t > 6) & (t < 30)
    r = float(np.percentile(np.linalg.norm((v[m] - p0) - np.outer(t[m], ax), axis=1), 75))   # covers the skin (t15: skin poked through)
    res[s + "UpLeg"] = (p0 + ax * (2.0 + r), p0 + ax * (34.0 - r), r)
# hips: horizontal capsule inside the hip / lower belly skin
hs = co[(mat == SKIN) & np.isin(dom, ["Hips", "spine"])]
P = C[bone["hips"]][:3, 3]
best = None
for y in np.arange(-4.0, 6.01, 0.5):
    for z in np.arange(P[2] - 8, P[2] + 8.01, 0.5):
        for w in np.arange(0.0, 12.01, 1.0):
            a, b = np.array([-w, P[1] + y, z]), np.array([w, P[1] + y, z])
            r = float(np.percentile(pt_seg(hs, a, b), 1)) - 0.3
            vol = np.pi * r * r * 2 * w + 4 / 3 * np.pi * r ** 3
            if best is None or vol > best[0]:
                best = (vol, a, b, r)
res["hips"] = best[1:]
for k, (a, b, r) in res.items():
    print("FIT", k, np.round(a, 1).tolist(), np.round(b, 1).tolist(), round(float(r), 2))
json.dump({k: [np.asarray(a).tolist(), np.asarray(b).tolist(), float(r)] for k, (a, b, r) in res.items()},
          open(out, "w"), indent=1)
print("FIT_OK", out)
