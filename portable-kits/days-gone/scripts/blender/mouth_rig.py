# Mouth weights for Karin's lip sync (Blender 4.2 background, on a blink_rig.py / face_rig.py build.blend).
#
# usage: blender -b <run>/build.blend --python mouth_rig.py -- <cooked mesh.uasset> <out_run_dir> <mouth_map.json> [--render]
#
# Days Gone lip sync blends Deacon's additive viseme poses (Animation/Deacon/vo/lipsync/dcn_visemes-*, baked
# AAT_LocalSpaceBase against misc/dcn_ref_pose frame 0) on the face_* joints. face_rig.py gave Karin's face the weights of
# the closest point of Deacon's warped skin; Deacon's lip seam is only ~0.1 cm between the upper and lower lip joints and
# Karin's anime mouth line did not land on it, so both her lips took the same weights: in game the lips stayed together
# (simulated AA: 0.01 cm gap) while the chin dropped with Deacon's jaw.
# Here the lower face weights are solved instead of sampled: every Deacon viseme is paired with one of Karin's own VRM
# mouth shapes (mouth_map.json: viseme -> {shape key: factor}), and each vertex gets the non-negative weights on the face
# joints near it (plus a static part = its old non-face weights, e.g. Head / Neck) whose linear blend skinning under the
# 17 viseme poses best reproduces the paired shape displacements (least squares, sum 1, <= 4 influences). Outside the
# mouth shapes the target is zero, so the chin and jaw line no longer follow Deacon's jaw (anime mouth opens inside the
# face). A second pass pulls each vertex towards the mean of its neighbours' first-pass weights (smoothness).
# Output: <out>/build.blend, <out>/deacon_head_standard.fbx, <out>/mouth_rig.json; --render: <out>/mouth_sheet.png
# (row pairs: target shape / simulated viseme).
import bpy, sys, os, json, math
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # the kit's scripts/
import refskel, anim_pertrack, dgpaths
from blink_sim import qmat, qmul, FLIP

argv = sys.argv[sys.argv.index("--") + 1:]
COOKED, OUT, MAP = argv[0], os.path.abspath(argv[1]), json.load(open(argv[2], encoding="utf-8"))
os.makedirs(OUT, exist_ok=True)
RENDER = "--render" in argv
SKEL_JSON = dgpaths.skel_json()   # <DG_CACHE>/deacon_master_Skeleton.deacon_master_Skeleton.skel.json
ANIM = dgpaths.anim_dir()         # <DG_CACHE>/anim/raw/animj/BendGame/Content/Animation/Deacon
MAX_INF = 4
Z_LIM, FADE = MAP.get("z_lim", 140.0), MAP.get("fade", 1.0)    # Blender z: solved below Z_LIM, blended up to +FADE
CAND_R = MAP.get("cand_radius", 4.5)                            # cm: face joints this close to a vertex are candidates
RIDGE = MAP.get("ridge", 0.02)                                  # pass 1: penalty on face weights (prefer static)
SMOOTH = MAP.get("smooth", 0.3)                                 # pass 2: pull towards the neighbours' mean weights
GAIN = MAP.get("gain", 1.0)
VIS = MAP["visemes"]
REPORT = {"map": MAP}

# ---------------------------------------------------------------- skeleton, viseme poses, per-joint skinning matrices
rs = refskel.read(COOKED)
N, P, L, C = rs["names"], rs["parents"], rs["local"], rs["component"]
ix = {n: i for i, n in enumerate(N)}
iH = ix["Head"]
skel = json.load(open(SKEL_JSON))["bones"]
sk_names = [b["name"] for b in skel]
sk_mode = {b["name"]: b["retarget"] for b in skel}
def under_head(i):
    while i >= 0:
        if i == iH: return True
        i = P[i]
    return False
# face rig joints only: Head also parents the KO_* hair / ear physics bones (AnimDynamics) and the KB_* lid bones; hair
# vertices solved onto Head + KO_Hair_side bones stretched into a sheet in game (t30 first build)
JOINTS = [n for i, n in enumerate(N) if i != iH and under_head(i) and
          (n.startswith("face_") or n.startswith("tongue") or n in ("Jaw", "lowerPalette_jnt"))]
HS = {"Head": np.eye(4)}                                  # rest transforms in Head space
for n in sorted(JOINTS, key=lambda n: ix[n]):
    HS[n] = HS[N[P[ix[n]]]] @ L[ix[n]]
Hc = C[iH]; Hci = np.linalg.inv(Hc)

base = anim_pertrack.decode(os.path.join(ANIM, "misc", "dcn_ref_pose.uasset"))
Bt = {sk_names[t["bone_index"]]: t for t in base["tracks"]}
def viseme_skin(v):
    """{joint: 4x4 component-space skinning matrix} of Deacon's viseme v applied to Karin's rest pose"""
    an = anim_pertrack.decode(os.path.join(ANIM, "vo", "lipsync", "dcn_visemes-%s.uasset" % v))
    D = {}
    for t in an["tracks"]:
        n = sk_names[t["bone_index"]]
        if n not in HS or n not in Bt: continue
        b = Bt[n]
        q = qmul(t["q"][0], b["q"][0] * np.array([-1, -1, -1, 1.0])); q /= np.linalg.norm(q)
        dt = t["t"][0] - b["t"][0]
        if sk_mode.get(n) == "Skeleton": dt = np.zeros(3)      # baked additive: Skeleton-mode translation zeroed
        D[n] = (qmat(q), dt)
    PS = {"Head": np.eye(4)}
    for n in sorted(JOINTS, key=lambda n: ix[n]):
        Lr = L[ix[n]].copy()
        if n in D:
            dR, dt = D[n]
            Lr[:3, :3] = dR @ Lr[:3, :3]; Lr[:3, 3] = Lr[:3, 3] + dt
        PS[n] = PS[N[P[ix[n]]]] @ Lr
    return {n: Hc @ PS[n] @ np.linalg.inv(HS[n]) @ Hci for n in JOINTS}
SKIN = {v: viseme_skin(v) for v in VIS}

# ---------------------------------------------------------------- mesh, targets, region
ob = bpy.data.objects["deacon_head_standard"]; me = ob.data; arm = ob.parent
kb = me.shape_keys.key_blocks
co = np.array([v.co for v in kb[0].data]); cu = co * FLIP          # Blender / UE component space
gname = {g.index: g.name for g in ob.vertex_groups}
W = [{gname[g.group]: g.weight for g in v.groups if g.weight > 1e-6} for v in me.vertices]
JS = set(JOINTS)
def shape(name): return (np.array([v.co for v in kb[name].data]) - co) * FLIP
SH = {}
TGT = {}
for v in VIS:
    t = np.zeros_like(co)
    for name, f in MAP["map"][v].items():
        if name not in SH: SH[name] = shape(name)
        t += GAIN * f * SH[name]
    TGT[v] = t
sup = np.zeros(len(co), bool)
for d in SH.values(): sup |= np.linalg.norm(d, axis=1) > 0.005
blink = np.array([any(n.startswith("KB_") for n in w) for w in W])
facew = np.array([any(n in JS for n in w) for w in W])
z = co[:, 2]
slot = {s_.material.name: i for i, s_ in enumerate(ob.material_slots) if s_.material}
vmat = np.zeros(len(co), int)
for p_ in me.polygons:
    for a_ in p_.vertices: vmat[a_] = p_.material_index
okmat = np.isin(vmat, [slot["MI_Karin_Face"], slot["MI_Karin_Alpha"], slot["MI_Karin_Body"]])
region = np.where(~blink & okmat & (z < Z_LIM + FADE) & (sup | facew))[0]
fade = np.clip((z - Z_LIM) / FADE, 0, 1)                 # 0 = fully solved, 1 = old weights
jpos = {n: C[ix[n]][:3, 3] for n in JOINTS}
REPORT["region"] = {"verts": int(len(region)), "support": int(sup.sum()), "support_in_region": int(sup[region].sum()),
                    "blink_excluded": int((blink & sup).sum())}

# ---------------------------------------------------------------- per-vertex solve
def nnls(A, b, iters=200):
    """Lawson-Hanson non-negative least squares"""
    m, n = A.shape
    x = np.zeros(n); Pset = np.zeros(n, bool)
    w = A.T @ (b - A @ x)
    for _ in range(iters):
        if Pset.all() or w[~Pset].max() <= 1e-10: break
        j = np.argmax(np.where(~Pset, w, -np.inf)); Pset[j] = True
        while True:
            s = np.zeros(n)
            s[Pset] = np.linalg.lstsq(A[:, Pset], b, rcond=None)[0]
            if s[Pset].min() > 0: break
            neg = Pset & (s <= 0)
            alpha = np.min(x[neg] / (x[neg] - s[neg] + 1e-30))
            x = x + alpha * (s - x)
            Pset &= x > 1e-12
        x = s
        w = A.T @ (b - A @ x)
    return x

# row weights: per axis (UE x lateral, y depth, z up: depth is barely visible from the front) and per viseme
AXW = np.tile(np.array(MAP.get("axis_weights", [1.0, 0.4, 1.0])), len(VIS)) *     np.repeat([MAP.get("viseme_weights", {}).get(k, 1.0) for k in VIS], 3)

def system(v, allowed=None, radius=CAND_R):
    """design matrix columns: static (old non-face weights, zero motion) + candidate face joints"""
    old = W[v]
    static = {n: x for n, x in old.items() if n not in JS}
    st = sum(static.values())
    static = {n: x / st for n, x in static.items()} if st > 1e-6 else {"Head": 1.0}
    pool = JOINTS if allowed is None else allowed
    cands = sorted(n for n in pool if np.linalg.norm(jpos[n] - cu[v]) < radius)
    if allowed is None: cands = sorted(set(cands) | {n for n in old if n in JS})
    cols = []
    for n in cands:
        col = np.concatenate([SKIN[k][n][:3, :3] @ cu[v] + SKIN[k][n][:3, 3] - cu[v] for k in VIS])
        cols.append(col)
    A = np.c_[np.zeros(3 * len(VIS)), np.array(cols).T] if cols else np.zeros((3 * len(VIS), 1))
    b = np.concatenate([TGT[k][v] for k in VIS])
    return static, cands, A * AXW[:, None], b * AXW

def solve(A, b, prior=None, lam=0.0, ridge=RIDGE, max_face=3, cost=None):
    """NNLS with sum 1 (static column 0 free); keeps the largest face columns whose summed cost (influences) fits"""
    n = A.shape[1]
    cost = np.ones(n) if cost is None else np.asarray(cost)
    def run(cols):
        k = len(cols)
        rows, rhs = [A[:, cols]], [b]
        R = np.sqrt(ridge) * np.eye(k); R[0, 0] = 0; rows.append(R); rhs.append(np.zeros(k))
        if prior is not None and lam > 0:
            rows.append(np.sqrt(lam) * np.eye(k)); rhs.append(np.sqrt(lam) * prior[cols])
        rows.append(30.0 * np.ones((1, k))); rhs.append(np.array([30.0]))
        x = np.zeros(n); x[cols] = nnls(np.vstack(rows), np.concatenate(rhs))
        return x
    x = run(np.arange(n))
    keep, used = [0], 0
    for j in np.argsort(-x[1:]) + 1:
        if x[j] > 1e-3 and used + cost[j] <= max_face:
            keep.append(j); used += cost[j]
    keep = np.array(keep)
    if len(keep) < n:                                        # re-solve on the kept columns
        x = run(keep)
    return x / x.sum()

kd = KDTree(len(co))
for i, p in enumerate(co): kd.insert(Vector(p), i)
kd.balance()
EPS = 1e-4
inreg = set(int(v) for v in region)
MIRV = {}                                                 # right-side vertex -> its left-side mirror vertex
for v in region:
    if co[v][0] < -EPS:
        _, u, d_ = kd.find(Vector(co[v] * np.array([-1, 1, 1.0])))
        if d_ < 1e-3 and u in inreg and co[u][0] > EPS: MIRV[int(v)] = u

def solve_all(allowed=None, radius=CAND_R, prev=None, lam=0.0, sym=False):
    """per-vertex solve; prev = {v: {joint|__static__: w}} of the previous pass -> neighbour-mean prior.
    sym: left side and centre line are solved, right side vertices take their mirror vertex's weights (joint names
    mirrored); centre line vertices solve with mirror-pair columns (a pair = two influences, equal weights)."""
    out = {}
    for v in region:
        v = int(v)
        if sym and v in MIRV: continue
        static, cands, A, b = system(v, allowed, radius)
        groups = [(n,) for n in cands]
        if sym and abs(co[v][0]) <= EPS:
            gs = []
            for n in cands:
                g = tuple(sorted({n, MIR.get(n) or n} & set(cands)))
                if g not in gs: gs.append(g)
            groups = gs
            cols = [A[:, 0]] + [np.mean([A[:, 1 + cands.index(m)] for m in g], axis=0) for g in groups]
            A = np.array(cols).T
        pr = None
        if prev is not None:
            nb = [u for u in adj.get(v, ()) if u in prev] or [v]
            pr = np.zeros(len(groups) + 1)
            for u in nb:
                pr[0] += prev[u].get("__static__", 0) / len(nb)
                for k, g in enumerate(groups): pr[k + 1] += sum(prev[u].get(m, 0) for m in g) / len(nb)
            pr /= pr.sum() or 1
        x = solve(A, b, prior=pr, lam=lam, max_face=max(MAX_INF - len(static), 1), cost=[0] + [len(g) for g in groups])
        d = {"__static__": x[0]}
        for g, w in zip(groups, x[1:]):
            for m in g:
                if w > 0: d[m] = d.get(m, 0) + w / len(g)
        out[v] = (static, d)
    if sym:
        for v, u in MIRV.items():
            static = system(v, [], radius)[0]
            out[v] = (static, {(MIR.get(n) or n) if n != "__static__" else n: w for n, w in out[u][1].items()})
    return out

adj = {}
for e in me.edges:
    a, c = e.vertices
    adj.setdefault(a, set()).add(c); adj.setdefault(c, set()).add(a)
# pass 1: every face joint near the vertex; keep the joints that carry the most weight on the mouth shapes (plus their
# mirror partners), so neighbouring vertices pick from the same few joints
S1 = solve_all()
mass = {}
for v, (st, d) in S1.items():
    if not sup[v]: continue
    for n, w in d.items():
        if n != "__static__": mass[n] = mass.get(n, 0) + w
TOPK = MAP.get("topk", 16)
DREST = {b["name"]: np.array(b["t"]) for b in skel}       # Deacon's rest (face_* local = Head space, Y lateral)
def mirror(n):
    if n not in DREST or skel[sk_names.index(n)]["parent"] != sk_names.index("Head"): return None
    p = DREST[n] * np.array([1, -1, 1.0])
    pool = [o for o in JOINTS if o in DREST and o.startswith("face_")]
    m = min(pool, key=lambda o: np.linalg.norm(DREST[o] - p))
    return m if np.linalg.norm(DREST[m] - p) < 0.4 else None
keep = set()
for n, _ in sorted(mass.items(), key=lambda kv: -kv[1]):
    if len(keep) >= TOPK: break
    keep.add(n)
    if mirror(n): keep.add(mirror(n))
keep |= set(MAP.get("extra_joints", []))
MIR = {n: mirror(n) for n in JOINTS}
assert all(MIR[n] in keep for n in keep if MIR[n]), "kept joints must come in mirror pairs"
REPORT["kept_joints"] = {n: [round(mass.get(n, 0), 2), MIR[n]] for n in sorted(keep, key=lambda n: -mass.get(n, 0))}
# pass 2: kept joints only; passes 3..: pulled towards the neighbours' mean of the previous pass
KR = MAP.get("keep_radius", 6.0)
# sym (mirrored weights) is off by default: face_rig's warp left Karin's face joints slightly asymmetric (Deacon's chin
# landmark sat 0.7 cm off centre), so mirrored weights gave a less symmetric mouth than solving both sides
SYM = MAP.get("symmetric", False)
S = solve_all(sorted(keep), KR, sym=SYM)
for it in range(MAP.get("smooth_iters", 3)):
    S = solve_all(sorted(keep), KR, prev={v: d for v, (st, d) in S.items()}, lam=SMOOTH, sym=SYM)

# final weights: solved (static part spread over the old non-face weights), faded into the old weights near Z_LIM
newW = {}
for v in region:
    static, d = S[int(v)]
    w = {n: d["__static__"] * s for n, s in static.items()}
    for n, xx in d.items():
        if n != "__static__" and xx > 1e-4: w[n] = w.get(n, 0) + xx
    t = fade[v]
    if t > 0:
        w = {n: (1 - t) * w.get(n, 0) + t * W[v].get(n, 0) for n in set(w) | set(W[v])}
    it = sorted(w.items(), key=lambda kv: -kv[1])[:MAX_INF]
    s = sum(x for _, x in it)
    newW[int(v)] = {n: x / s for n, x in it if x / s > 1e-4}
# parts that are not face skin and not moved by the mouth shapes (Alpha cards, line bits, props just behind the skin)
# follow the closest skin vertex, as face_rig.py did; solved alone they stayed put and poked out when the skin moved
fpolys = [p_ for p_ in me.polygons if p_.material_index == slot["MI_Karin_Face"]]
fadj = {}
for p_ in fpolys:
    for a_ in p_.vertices: fadj.setdefault(a_, set()).update(p_.vertices)
seen, skin = set(), []
for v0 in fadj:
    if v0 in seen: continue
    st_, comp = [v0], []; seen.add(v0)
    while st_:
        x_ = st_.pop(); comp.append(x_)
        for y_ in fadj[x_]:
            if y_ not in seen: seen.add(y_); st_.append(y_)
    if len(comp) > len(skin): skin = comp
skin = set(skin)
skin_reg = [v for v in newW if v in skin]
kds = KDTree(len(skin_reg))
for i, v in enumerate(skin_reg): kds.insert(Vector(co[v]), i)
kds.balance()
followed = 0
for v in list(newW):
    if v in skin or sup[v] or vmat[v] not in (slot["MI_Karin_Face"], slot["MI_Karin_Alpha"]): continue
    _, i, _ = kds.find(Vector(co[v]))
    newW[v] = dict(newW[skin_reg[i]]); followed += 1
REPORT["followers"] = followed
# coincident vertices (UV / material splits, centre line, face border = body neck seam) share one weight set: the
# lowest index solved vertex of the group gives its weights to the others
shared = 0
for v in sorted(newW):
    grp = [u for (_, u, d) in kd.find_range(Vector(co[v]), 1e-4)]
    if min(u for u in grp if u in newW) != v: continue
    for u in grp:
        if u != v and newW.get(u) != newW[v]:
            newW[u] = dict(newW[v]); shared += 1
REPORT["coincident_copied"] = shared

# ---------------------------------------------------------------- fit report
def simulate(weights, v_name):
    S = SKIN[v_name]
    d = np.zeros_like(cu)
    for v, w in weights.items():
        acc = np.zeros(3)
        for n, x in w.items():
            if n in S: acc += x * (S[n][:3, :3] @ cu[v] + S[n][:3, 3] - cu[v])
        d[v] = acc
    return d
oldW = {int(v): W[v] for v in newW}
mv = np.where(np.linalg.norm(shape("kuchi_A"), axis=1) > 1e-3)[0]
KA = shape("kuchi_A")
front = co[mv, 1] < co[mv, 1].min() + 0.6
upper = mv[(KA[mv, 2] > -0.05) & front]; lower = mv[(KA[mv, 2] < -0.5) & front]
uc, lc = upper[np.abs(co[upper, 0]) < 0.6], lower[np.abs(co[lower, 0]) < 0.6]
gap = lambda d: float(d[uc, 2].mean() - d[lc, 2].mean())
fit = {}
for k in VIS:
    dn, do = simulate(newW, k), simulate(oldW, k)
    e = np.linalg.norm(dn - TGT[k], axis=1)
    m = np.linalg.norm(TGT[k], axis=1) > 0.01
    fit[k] = {"target_gap": round(gap(TGT[k]), 3), "new_gap": round(gap(dn), 3), "old_gap": round(gap(do), 3),
              "err_mean": round(float(e[m].mean()) if m.any() else 0.0, 3), "err_max": round(float(e.max()), 3),
              "static_max_move": round(float(np.linalg.norm(dn[~m], axis=1).max()), 3)}
REPORT["fit"] = fit
# left/right symmetry of the simulated visemes (mirror vertex: x -> -x)
mir = {}
for v in newW:
    if co[v][0] > 0.01:
        p_, u, d_ = kd.find(Vector(co[v] * np.array([-1, 1, 1.0])))
        if d_ < 1e-3: mir[v] = u
for k in VIS:
    dn = simulate(newW, k)
    a = [np.linalg.norm(dn[v] - dn[u] * np.array([-1, 1, 1.0])) for v, u in mir.items()]
    fit[k]["asym_max"] = round(float(max(a)), 3); fit[k]["asym_mean"] = round(float(np.mean(a)), 3)
REPORT["influences_max"] = max(len(w) for w in newW.values())
used = {}
for w in newW.values():
    for n in w:
        if n in JS: used[n] = used.get(n, 0) + 1
REPORT["joints_used"] = len(used)

# ---------------------------------------------------------------- write weights
groups = {g.name: g for g in ob.vertex_groups}
for v, w in newW.items():
    for g in list(me.vertices[v].groups):
        ob.vertex_groups[g.group].remove([v])
    for n, x in w.items():
        if n not in groups: groups[n] = ob.vertex_groups.new(name=n)
        groups[n].add([v], x, "REPLACE")

if RENDER:
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"; sc.display.shading.light = "STUDIO"; sc.display.shading.color_type = "TEXTURE"
    Rz = MAP.get("render_res", 200); sc.render.resolution_x = Rz; sc.render.resolution_y = Rz
    cam = bpy.data.objects.get("cam")
    if cam is None:
        cd = bpy.data.cameras.new("cam"); cam = bpy.data.objects.new("cam", cd); sc.collection.objects.link(cam)
    cam.data.type = "ORTHO"; cam.data.ortho_scale = MAP.get("render_scale", 9); sc.camera = cam
    cam.location = (0, -80, 137.6); cam.rotation_euler = (math.radians(90), 0, 0)
    for o in bpy.data.objects: o.hide_render = o is not ob
    tmp = os.path.join(OUT, "_tile.png")
    def tile(dsp):
        sk = ob.shape_key_add(name="_tmp", from_mix=False)
        for i in range(len(co)): sk.data[i].co = Vector(co[i] + dsp[i] * FLIP)
        for k in me.shape_keys.key_blocks: k.value = 1.0 if k.name == "_tmp" else 0.0
        sc.render.filepath = tmp; bpy.ops.render.render(write_still=True)
        ob.shape_key_remove(sk)
        img = bpy.data.images.load(tmp); px = np.array(img.pixels[:]).reshape(Rz, Rz, 4); bpy.data.images.remove(img)
        return px
    RV = MAP.get("render_visemes", VIS)
    rows_ = [[tile(TGT[k]) for k in RV], [tile(simulate(newW, k)) for k in RV], [tile(simulate(oldW, k)) for k in RV]]
    extra = MAP.get("render_moods", [])
    if extra:
        mrow = []
        for mood in extra:
            an = anim_pertrack.decode(os.path.join(ANIM, mood + ".uasset"))
            # moods: last frame against dcn_ref_pose frame 0, through the same FK
            D = {}
            for t in an["tracks"]:
                n = sk_names[t["bone_index"]]
                if n not in HS or n not in Bt: continue
                q = qmul(t["q"][-1], Bt[n]["q"][0] * np.array([-1, -1, -1, 1.0])); q /= np.linalg.norm(q)
                dt = t["t"][-1] - Bt[n]["t"][0]
                if sk_mode.get(n) == "Skeleton": dt = np.zeros(3)
                D[n] = (qmat(q), dt)
            PS = {"Head": np.eye(4)}
            for n in sorted(JOINTS, key=lambda n: ix[n]):
                Lr = L[ix[n]].copy()
                if n in D: Lr[:3, :3] = D[n][0] @ Lr[:3, :3]; Lr[:3, 3] = Lr[:3, 3] + D[n][1]
                PS[n] = PS[N[P[ix[n]]]] @ Lr
            SKIN["_m"] = {n: Hc @ PS[n] @ np.linalg.inv(HS[n]) @ Hci for n in JOINTS}
            mrow.append(tile(simulate(newW, "_m"))); mrow.append(tile(simulate(oldW, "_m")))
        rows_.append(mrow)
    os.remove(tmp)
    cols = max(len(r) for r in rows_)
    sheet = np.ones((len(rows_) * Rz, cols * Rz, 4))
    for r, row in enumerate(rows_):
        for c, t in enumerate(row):
            sheet[(len(rows_) - 1 - r) * Rz:(len(rows_) - r) * Rz, c * Rz:(c + 1) * Rz] = t
    img = bpy.data.images.new("sheet", cols * Rz, len(rows_) * Rz, alpha=True)
    img.pixels = sheet.ravel().tolist(); img.filepath_raw = os.path.join(OUT, "mouth_sheet.png"); img.file_format = "PNG"
    img.save()
    for k in me.shape_keys.key_blocks: k.value = 0.0
    REPORT["sheet"] = {"columns": RV, "rows": ["target", "new", "old"] + (["moods new/old: " + ", ".join(extra)] if extra else [])}

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "build.blend"))
from fbx_common import export_for_ue411
export_for_ue411(arm, [ob], os.path.join(OUT, "deacon_head_standard.fbx"), "deacon_head_standard")
json.dump(REPORT, open(os.path.join(OUT, "mouth_rig.json"), "w"), indent=1)
print("MOUTH_RIG_OK", json.dumps({k: REPORT[k] for k in ("region", "influences_max", "joints_used", "coincident_copied", "followers")}))
for k, f in fit.items(): print("FIT %-3s %s" % (k, f))
