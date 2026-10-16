# Skin Karin's face to Deacon's joint-driven face rig (Blender 4.2 background, on a build_body.py build.blend).
#
# usage: blender -b <run>/build.blend --python face_rig.py -- <out_run_dir> [--check]
#
# Days Gone animates faces with ~280 face_* joints (retarget mode Animation: their local translations come straight
# from the animation, i.e. Deacon's face layout around the Head joint), plus Jaw, tongue*_jnt and the eye joints.
# The joints keep Deacon's rest positions; Karin's face only takes their weights, so every animated joint delta is
# applied to her face as is. The weights come from Deacon's head mesh: it is moved onto Karin's Head joint, warped
# onto her face with a thin-plate RBF through landmarks (eyes, nose tip, mouth, chin) and sampled at the closest
# surface point of every Karin face vertex. Eye surfaces follow LeftEye/RightEye, mouth interior follows Deacon's
# teeth/tongue weights, and the face skin blends back to its old weights near its open border (neck seam).
# Output: <out>/build.blend and <out>/deacon_head_standard.fbx (+ face_rig.json); --check also renders a jaw-open test.
import bpy, bmesh, sys, os, json, math, addon_utils
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # the kit's scripts/
import dgpaths

argv = sys.argv[sys.argv.index("--") + 1:]
OUT = os.path.abspath(argv[0]); os.makedirs(OUT, exist_ok=True)
CHECK = "--check" in argv
MAX_INF = 4
DEACON_HEAD = dgpaths.head_uemodel()   # <DG_CACHE>/ue/BendGame/Content/Characters/Deacon/parts/head/deacon_head_standard.uemodel
REPORT = {}

body = bpy.data.objects["deacon_head_standard"]
arm = body.parent
me = body.data
B = {b.name: np.array(arm.matrix_world @ b.head_local) for b in arm.data.bones}
slot = {s.material.name: i for i, s in enumerate(body.material_slots) if s.material}
co = np.array([v.co for v in me.vertices])

# ---------------------------------------------------------------- Karin face regions
face_polys = [p for p in me.polygons if p.material_index == slot["MI_Karin_Face"]]
adj = {}
ecount = {}
for p in face_polys:
    for a in p.vertices: adj.setdefault(a, set()).update(p.vertices)
    for ek in p.edge_keys: ecount[ek] = ecount.get(ek, 0) + 1
comps, seen = [], set()
for v in adj:
    if v in seen: continue
    st, c = [v], []; seen.add(v)
    while st:
        x = st.pop(); c.append(x)
        for y in adj[x]:
            if y not in seen: seen.add(y); st.append(y)
    comps.append(np.array(c))
comps.sort(key=len, reverse=True)
skin = comps[0]                                   # face skin island (whole head skin)
others = comps[1:]
def center(c): return co[c].mean(0)
def size(c): return co[c].max(0) - co[c].min(0)
# eye surfaces: components left/right of the centre at eye height in front of the eye joints
eyes = {"L": [], "R": []}
mouth_parts = []
for c in others:
    ctr, sz = center(c), size(c)
    if abs(ctr[0]) > 2.0 and ctr[2] > B["Jaw"][2] + 2.5:
        eyes["L" if ctr[0] > 0 else "R"].append(c)
    elif abs(ctr[0]) < 2.5 and ctr[2] < B["LeftEye"][2] - 1.0:
        mouth_parts.append(c)
border = {v for ek, n in ecount.items() if n == 1 for v in ek} & set(skin.tolist())
REPORT["karin"] = {"skin": len(skin), "eye_parts": {k: len(v) for k, v in eyes.items()}, "mouth_parts": len(mouth_parts),
                   "border": len(border)}

# ---------------------------------------------------------------- Deacon head, moved onto Karin's Head joint
addon_utils.enable("io_scene_ueformat", default_set=True)
s = bpy.context.scene.uf_settings; s.scale_factor = 1.0; s.import_sockets = False; s.import_morph_targets = False
before = set(bpy.data.objects)
bpy.ops.uf.import_uemodel(filepath=DEACON_HEAD, files=[{"name": os.path.basename(DEACON_HEAD)}],
                          directory=os.path.dirname(DEACON_HEAD))
new = [o for o in bpy.data.objects if o not in before]
darm = next(o for o in new if o.type == "ARMATURE"); dm = next(o for o in new if o.type == "MESH")
DB = {b.name: np.array(darm.matrix_world @ b.head_local) for b in darm.data.bones}
shift = B["Head"] - DB["Head"]
dco = np.array([dm.matrix_world @ v.co for v in dm.data.vertices]) + shift
dmats = [s.material.name if s.material else "" for s in dm.material_slots]
def dpolys(pred): return [p for p in dm.data.polygons if pred(dmats[p.material_index])]
skin_d = dpolys(lambda n: n in ("", "None") or "head" in n)
teeth_d = dpolys(lambda n: "teeth" in n)
dskin_v = sorted({v for p in skin_d for v in p.vertices})
gname = {g.index: g.name for g in dm.vertex_groups}
dw = [{gname[g.group]: g.weight for g in v.groups if g.weight > 1e-4 and gname[g.group] in B} for v in dm.data.vertices]

# ---------------------------------------------------------------- landmarks (Deacon -> Karin)
def centre_line(vs, pts, half=0.6): return [v for v in vs if abs(pts[v][0]) < half]
def k_nose():
    cl = [v for v in centre_line(skin, co) if B["Jaw"][2] < co[v][2] < B["LeftEye"][2] + 3]
    return co[min(cl, key=lambda v: co[v][1])]
def d_nose():
    cl = [v for v in centre_line(dskin_v, dco) if DB["Jaw"][2] + shift[2] < dco[v][2] < DB["LeftEye"][2] + shift[2] + 3]
    return dco[min(cl, key=lambda v: dco[v][1])]
k_mouth = co[np.concatenate(mouth_parts)].mean(0) if mouth_parts else None
mouth_front = min((co[c][:, 1].min() for c in mouth_parts), default=None)
tv = sorted({v for p in teeth_d for v in p.vertices})
tco = dco[tv]
d_mouth = np.array([0.0, tco[:, 1].min() - 0.8, (tco[:, 2].min() + tco[:, 2].max()) / 2])
def chin(vs, pts, mouth_z):
    cl = [v for v in centre_line(vs, pts, 1.0) if pts[v][2] < mouth_z - 1.0]
    front = min(pts[v][1] for v in cl)
    cl = [v for v in cl if pts[v][1] < front + 1.5]       # the chin's front surface
    return pts[min(cl, key=lambda v: pts[v][2])]
k_eye = {k: co[np.concatenate(v)].mean(0) for k, v in eyes.items()}
d_eye = {"L": DB["LeftEye"] + shift, "R": DB["RightEye"] + shift}
# Deacon's eye joints sit in the eyeball centre; move them to the front of the eye like Karin's surfaces
d_eye = {k: v + np.array([0, -1.0, 0]) for k, v in d_eye.items()}
src = [d_eye["L"], d_eye["R"], d_nose(), d_mouth, chin(dskin_v, dco, d_mouth[2])]
dst = [k_eye["L"], k_eye["R"], k_nose(), k_mouth, chin(skin, co, k_mouth[2])]
# far anchors keep the rest of the head in place (identity outside the face)
for off in ((0, 14, 4), (12, 2, 4), (-12, 2, 4), (0, 0, 20), (0, 4, -12), (14, -4, -6), (-14, -4, -6)):
    p = B["Head"] + np.array(off, float) + np.array([0, 0, 6]); src.append(p); dst.append(p)
src, dst = np.array(src), np.array(dst)
REPORT["landmarks"] = {"names": ["eyeL", "eyeR", "nose", "mouth", "chin"],
                       "deacon": src[:5].round(2).tolist(), "karin": dst[:5].round(2).tolist()}

# ---------------------------------------------------------------- thin-plate RBF (phi = r) with affine part
def rbf_fit(a, b):
    n = len(a)
    K = np.linalg.norm(a[:, None] - a[None], axis=2)
    P = np.c_[a, np.ones(n)]
    M = np.zeros((n + 4, n + 4)); M[:n, :n] = K; M[:n, n:] = P; M[n:, :n] = P.T
    rhs = np.zeros((n + 4, 3)); rhs[:n] = b
    return a, np.linalg.solve(M, rhs)
def rbf_apply(f, x):
    a, W = f
    K = np.linalg.norm(x[:, None] - a[None], axis=2)
    return K @ W[:len(a)] + np.c_[x, np.ones(len(x))] @ W[len(a):]
warp = rbf_fit(src, dst)
wco = rbf_apply(warp, dco)

# ---------------------------------------------------------------- weight sampling on the warped Deacon surface
def bvh_of(polys):
    vs = sorted({v for p in polys for v in p.vertices}); idx = {v: i for i, v in enumerate(vs)}
    tris = []
    for p in polys:
        t = [idx[v] for v in p.vertices]
        for k in range(1, len(t) - 1): tris.append((t[0], t[k], t[k + 1]))
    pts = [Vector(wco[v]) for v in vs]
    return BVHTree.FromPolygons(pts, tris), vs, tris
def sample(bvh, vs, tris, p):
    loc, nrm, fi, dist = bvh.find_nearest(Vector(p))
    a, b, c = (np.array(wco[vs[i]]) for i in tris[fi])
    v0, v1, v2 = b - a, c - a, np.array(loc) - a
    d00, d01, d11, d20, d21 = v0 @ v0, v0 @ v1, v1 @ v1, v2 @ v0, v2 @ v1
    den = d00 * d11 - d01 * d01 or 1e-12
    bv = (d11 * d20 - d01 * d21) / den; bw = (d00 * d21 - d01 * d20) / den; bu = 1 - bv - bw
    out = {}
    for wgt, i in ((bu, tris[fi][0]), (bv, tris[fi][1]), (bw, tris[fi][2])):
        for g, x in dw[vs[i]].items(): out[g] = out.get(g, 0.0) + max(wgt, 0.0) * x
    return out, dist
def top(wd, n=MAX_INF):
    it = [kv for kv in sorted(wd.items(), key=lambda kv: -kv[1])[:n] if kv[1] > 0.01] or [("Head", 1.0)]
    t = sum(x for _, x in it) or 1.0
    return {g: x / t for g, x in it}
bvh_skin = bvh_of(skin_d)
bvh_teeth = bvh_of(teeth_d) if teeth_d else None

# Karin's current weights
groups = {g.name: g for g in body.vertex_groups}
def get_w(v):
    v = int(v); return {body.vertex_groups[g.group].name: g.weight for g in me.vertices[v].groups if g.weight > 1e-6}
def set_w(v, wd):
    v = int(v)
    for g in list(me.vertices[v].groups):
        body.vertex_groups[g.group].remove([v])
    for name, x in wd.items():
        if name not in groups: groups[name] = body.vertex_groups.new(name=name)
        groups[name].add([v], x, "REPLACE")

kd = KDTree(len(border))
for i, v in enumerate(border): kd.insert(Vector(co[v]), v)
kd.balance()
# the skin island takes the sampled weights as is (no fade at its border: Deacon's lower face joints move the chin, the
# seam would tear); instead the neck vertices of the body mesh near the seam blend into the sampled weights, seam
# vertices (same position as the face border) get exactly the face side's weights
SEAM_FADE = 4.0
stats = {"skin": 0, "skin_face_joints": 0, "eyes": 0, "mouth": 0, "neck": 0, "max_dist": 0.0}
face_joint = lambda g: g.startswith("face_") or g in ("Jaw",) or g.startswith("tongue")
for v in skin:
    wd, dist = sample(*bvh_skin, co[v])
    stats["max_dist"] = max(stats["max_dist"], dist)
    nw = top(wd)
    set_w(v, nw); stats["skin"] += 1
    if any(face_joint(g) for g in nw): stats["skin_face_joints"] += 1
neck = sorted({v for p in me.polygons if p.material_index == slot["MI_Karin_Body"] for v in p.vertices
               if co[v][2] > B["Neck"][2] - 2})
for v in neck:
    _, _, bd = kd.find(Vector(co[v]))
    t = 1.0 - min(bd / SEAM_FADE, 1.0); t = t * t * (3 - 2 * t)
    if t <= 0: continue
    wd, _ = sample(*bvh_skin, co[v]); wd = top(wd)
    old = get_w(v)
    set_w(v, top({g: (1 - t) * old.get(g, 0) + t * wd.get(g, 0) for g in set(old) | set(wd)})); stats["neck"] += 1
for side, parts in eyes.items():
    bone = "LeftEye" if side == "L" else "RightEye"
    for c in parts:
        for v in c:
            set_w(v, {bone: 1.0}); stats["eyes"] += 1
for c in mouth_parts:
    for v in c:
        wd, _ = sample(*(bvh_teeth or bvh_skin), co[v])
        set_w(v, top(wd)); stats["mouth"] += 1
# other face-material bits (eyebrow/eye lines) and the Alpha material (lashes): follow the nearest skin sample
alpha = sorted({v for p in me.polygons if p.material_index == slot["MI_Karin_Alpha"] for v in p.vertices})
done = set(skin.tolist()) | {v for c in mouth_parts for v in c} | {v for cs in eyes.values() for c in cs for v in c}
rest = [v for c in others for v in c if v not in done] + [v for v in alpha if v not in done]
for v in rest:
    wd, _ = sample(*bvh_skin, co[v]); set_w(v, top(wd))
stats["lines_and_lashes"] = len(rest)
REPORT["stats"] = stats
REPORT["face_joints_used"] = sorted({g.name for g in body.vertex_groups if face_joint(g.name)})[:400]

bpy.data.objects.remove(dm, do_unlink=True); bpy.data.objects.remove(darm, do_unlink=True)

# face joints onto Karin's face: the same warp moves every face_* rest position (orientation kept), so a joint pivots
# where its skin is. Needs the game Skeleton's face_* bones in AnimationRelative mode (pytools/skel_retarget.py):
# the animation then adds Deacon's deltas to these rest positions instead of placing the joints at Deacon's layout.
if "--keep-joints" not in argv:
    W = np.array(arm.matrix_world); Wi = np.linalg.inv(W)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    moved = []
    for eb in arm.data.edit_bones:
        if not eb.name.startswith("face_"): continue
        h = np.array(B[eb.name])
        nh = rbf_apply(warp, h[None])[0]
        dl = (Wi[:3, :3] @ (nh - h))
        eb.head = eb.head + Vector(dl); eb.tail = eb.tail + Vector(dl)
        moved.append(float(np.linalg.norm(nh - h)))
    bpy.ops.object.mode_set(mode="OBJECT")
    REPORT["joints_moved"] = {"count": len(moved), "mean_cm": round(float(np.mean(moved)), 2), "max_cm": round(float(np.max(moved)), 2)}
    B.update({b.name: np.array(arm.matrix_world @ b.head_local) for b in arm.data.bones if b.name.startswith("face_")})

# VRM expression props (tears, sweat, alternative eyes...) wait hidden behind the face skin until a shape key moves
# them out. The game has no shape keys, and when face joints squeeze the cheeks the skin passes over them (dark spots
# on the cheeks in game) -> delete every face-material part that sits more than 0.5 cm behind the skin, except the
# mouth interior, which the lips uncover when they open.
sk_tris = []
for p in face_polys:
    if p.vertices[0] in set(skin.tolist()):
        t = list(p.vertices)
        for k in range(1, len(t) - 1): sk_tris.append((t[0], t[k], t[k + 1]))
skin_bvh = BVHTree.FromPolygons([Vector(c) for c in co], sk_tris)
hc = B["Head"] + np.array([0, 0, 6.0])
mouth_set = {v for c in mouth_parts for v in c}
hidden = []
for c in others:
    if c[0] in mouth_set: continue
    ctr = co[c].mean(0); d = (ctr - hc) / np.linalg.norm(ctr - hc)
    h1 = skin_bvh.ray_cast(Vector(ctr), Vector(d)); h2 = skin_bvh.ray_cast(Vector(ctr), Vector((0, -1, 0)))
    if h1[0] is not None and h2[0] is not None and h1[3] > 0.5:
        hidden.append(c)
dele = sorted({int(v) for c in hidden for v in c})
bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
bmesh.ops.delete(bm, geom=[bm.verts[i] for i in dele], context="VERTS")
bm.to_mesh(me); bm.free(); me.update()
REPORT["hidden_parts_deleted"] = {"parts": len(hidden), "verts": len(dele)}

if CHECK:   # mouth open: face joints below Deacon's mouth (rest) move 1 cm down, as a jaw-open pose would
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"; sc.display.shading.light = "STUDIO"; sc.display.shading.color_type = "SINGLE"
    sc.render.resolution_x = 500; sc.render.resolution_y = 500
    cam_d = bpy.data.cameras.new("cam"); cam_d.type = "ORTHO"; cam_d.ortho_scale = 22
    cam = bpy.data.objects.new("cam", cam_d); sc.collection.objects.link(cam); sc.camera = cam
    for o in bpy.data.objects: o.hide_render = o is not body
    low = [b for b in arm.pose.bones if b.name.startswith("face_") and B[b.name][2] < src[3][2] - 0.3 + 0 * shift[2]]
    for tag, dz in (("rest", 0.0), ("open", -1.0)):
        for b in low:
            b.location = (0, 0, 0)
            if dz:   # bone-local offset that moves the joint dz along world Z
                b.location = Vector((arm.matrix_world @ b.bone.matrix_local).to_3x3().inverted() @ Vector((0, 0, dz)))
        for view, loc, rot in (("front", (0, -80, B["LeftEye"][2] - 3), (math.radians(90), 0, 0)),
                               ("side", (80, -6, B["LeftEye"][2] - 3), (math.radians(90), 0, math.radians(90)))):
            cam.location = loc; cam.rotation_euler = rot
            sc.render.filepath = os.path.join(OUT, "mouth_%s_%s.png" % (tag, view)); bpy.ops.render.render(write_still=True)
    for b in low: b.location = (0, 0, 0)
    REPORT["check_joints"] = len(low)

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "build.blend"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fbx_common import export_for_ue411
export_for_ue411(arm, [body], os.path.join(OUT, "deacon_head_standard.fbx"), "deacon_head_standard")
json.dump(REPORT, open(os.path.join(OUT, "face_rig.json"), "w"), indent=1)
print("FACE_RIG_OK", json.dumps(REPORT["stats"]), json.dumps(REPORT["landmarks"]))
