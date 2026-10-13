# Time-stepped skirt proxy simulation (PBD, NvCloth-like: gravity, damping, stretch/shear/bend edges, tethers to the
# fixed ring, max distance, backstop spheres, PA shape collision + thickness) driven through game animations
# (bone rotations slerped between the decoded frames). At every decoded frame the render skirt is rebuilt from the
# particles (bary + offset along interpolated normal) and tested against the posed skin: a render vertex counts as
# inside when the nearest skin face is behind it AND the first skin crossing along the cloth normal is an exit (the
# nearest-face test alone is fooled by thin edges such as the underwear rim). Hands/arms are ignored.
# The solver is a rough stand-in for NvCloth: compare variants under "iters" 2 and 6 and trust only what both agree on.
# Anims: SifuExport "anim" dumps, e.g. MC_man_barehands_V2/V3_north.anim.json (jog/run) and the kick/knee attacks.
# blender -b karin_sifu.blend --python skirt_sim.py -- <out.json> <cloth.json> <variant json> <anim.json> [...]
# variant keys: sub_r (ring subdivision), sub_s (segment subdivision), thick, thigh_dr, leg [front, lat, back],
#               bs_last (bool: backstop on the hem ring too), travel (backstop inward travel cm), hz (solver Hz)
import bpy, os, sys, json, math
from mathutils import Vector, Quaternion
from mathutils.bvhtree import BVHTree
SC = os.path.dirname(os.path.abspath(__file__)).replace("\\", "/")   # this folder (pose_preview.py, sifu_common.py)
sys.path.insert(0, SC)
import sifu_common as sc
ARGS = sys.argv[sys.argv.index("--") + 1:]
out_path, cloth_path, var, anims = ARGS[0], ARGS[1], json.loads(ARGS[2]), ARGS[3:]
anim_path = anims[0]
src = open(SC + "/pose_preview.py").read()
src = src.split(chr(10) + "scn = bpy.context.scene" + chr(10))[0].replace('args = sys.argv[sys.argv.index("--") + 1:]', "args = [anim_path, 'x']")
exec(src.replace("__file__", "'" + SC + "/pose_preview.py'"))
cloth = json.load(open(cloth_path))
cs = [c for c in cloth["cloth"] if "Skirt" in c["name"]][0]
cfg = cs["config"]
thick = var.get("thick", cfg["CollisionThickness"])
MAXD = cs["max_distance"]
bodies = cloth["physics"]["bodies"]
proxy = bpy.data.objects["Proxy_Skirt"]
skirt = bpy.data.objects["skirt"]
deps = bpy.context.evaluated_depsgraph_get()
assert arm.matrix_world.is_identity and proxy.matrix_world.is_identity

# ---- proxy (optionally subdivided) ---------------------------------------------------------------------------------
SEGS0 = 32
pv_orig = [v.co.copy() for v in proxy.data.vertices]
R0 = len(pv_orig) // SEGS0
sr, ss = var.get("sub_r", 1), var.get("sub_s", 1)
rings, segs = (R0 - 1) * sr + 1, SEGS0 * ss


def orig_at(ri, k):          # fractional ring / segment position -> point on the original proxy grid (bilinear)
    i0 = min(int(ri), R0 - 2)
    ti = ri - i0
    k0 = int(k) % SEGS0
    tk = k - int(k)
    k1 = (k0 + 1) % SEGS0
    p = lambda i, kk: pv_orig[i * SEGS0 + kk]
    a = p(i0, k0).lerp(p(i0, k1), tk)
    b = p(i0 + 1, k0).lerp(p(i0 + 1, k1), tk)
    return a.lerp(b, ti)


pv0 = [orig_at(i / sr, k / ss) for i in range(rings) for k in range(segs)]
nv = len(pv0)
travel = var.get("travel", 0.0)
gname = {g.index: g.name for g in proxy.vertex_groups}
w_orig = [{gname[e.group]: e.weight for e in v.groups} for v in proxy.data.vertices]


def w_at(ri, k):             # bilinear blend of the proxy's own skin weights
    i0 = min(int(ri), R0 - 2)
    ti = ri - i0
    k0 = int(k) % SEGS0
    tk = k - int(k)
    out = {}
    for i, wi in ((i0, 1 - ti), (i0 + 1, ti)):
        for kk, wk in ((k0, 1 - tk), ((k0 + 1) % SEGS0, tk)):
            for b_, w in w_orig[i * SEGS0 + kk].items():
                out[b_] = out.get(b_, 0.0) + w * wi * wk
    return [(b_, w) for b_, w in out.items() if w > 1e-4]


W, md, bs = [], [], []
for i in range(rings):
    f = i / (rings - 1)
    for k in range(segs):
        ws = w_at(i / sr, k / ss)
        lm = var.get("leg_mul", 1.0)
        if lm != 1.0 and i > 0:      # scale the thigh share, the rest (pelvis/spine) takes up the difference
            th = sum(w for b_, w in ws if b_.startswith("thigh"))
            new = min(0.98, th * lm)
            rs = (1 - new) / max(1e-6, 1 - th)
            ws = [(b_, w * (new / th if b_.startswith("thigh") else rs)) for b_, w in ws] if th > 0 else ws
        W.append(ws)
        md.append(0.0 if i == 0 else MAXD * f ** 0.8 * var.get("maxd_mul", [1.0] * 99)[min(int(f * 5 + 1e-6), 5)])
        on = 0 < i < rings - 1 or (i == rings - 1 and var.get("bs_last"))
        bs.append((15.0 + travel, 15.0) if on else (0.0, 0.0))
idx = lambda i, k: i * segs + k % segs
ptris = []
for i in range(rings - 1):
    for k in range(segs):
        a, b = idx(i, k), idx(i, k + 1)
        ptris += [(a, b + segs, b), (a, a + segs, b + segs)]
E = []   # (i, j, rest, stiffness per iteration)
hz = var.get("hz", 120.0)
sf = cfg.get("StiffnessFrequency", 60.0)
kst = lambda s: 1.0 - (1.0 - s) ** (sf / hz)
kbend = kst(cfg["BendConstraint"]["Stiffness"])
for i in range(rings):
    for k in range(segs):
        p = idx(i, k)
        E.append((p, idx(i, k + 1), 1.0))
        E.append((p, idx(i, k + 2), kbend))
        if i + 1 < rings:
            E += [(p, idx(i + 1, k), 1.0), (p, idx(i + 1, k + 1), 1.0), (idx(i, k + 1), idx(i + 1, k), 1.0)]
        if i + 2 < rings:
            E.append((p, idx(i + 2, k), kbend))
E = [(a, b, (pv0[a] - pv0[b]).length, s) for a, b, s in E]
tether = [(idx(0, k % segs), (pv0[i] - pv0[idx(0, k % segs)]).length) for i in range(nv) for k in [i % segs]]

# ---- bones ----------------------------------------------------------------------------------------------------------
LR = {}
for b in ORDER:
    LR[b.name] = rest_ue[b.parent.name].inverted() @ rest_ue[b.name] if b.parent else rest_ue[b.name].copy()
Minv = {n: arm.data.bones[n].matrix_local.inverted() for n in sorted({b_ for ws in W for b_, _ in ws})}


def frame_q(fr):
    return {b["name"]: Quaternion((b["q"][3], b["q"][0], b["q"][1], b["q"][2])) for b in fr["bones"]
            if b["keyed"] and not b["name"].startswith(SIM)}


def world_of(Q):
    world = {}
    for b in ORDER:
        q = Q.get(b.name) if b.parent else None
        if q is not None:
            local = q.to_matrix().to_4x4()
            local.translation = LR[b.name].translation
        else:
            local = LR[b.name]
        world[b.name] = world[b.parent.name] @ local if b.parent else local
    return world


def lerp_q(Q0, Q1, t):
    out = {}
    for n, q0 in Q0.items():
        q1 = Q1.get(n, q0)
        if q0.dot(q1) < 0:
            q1 = -q1
        out[n] = q0.slerp(q1, t)
    return out


def anchors(world):
    S = {n: sc.ue_to_bl(world[n]) @ Minv[n] for n in Minv}
    return [sum((S[b_] @ pv0[i] * w for b_, w in W[i]), Vector()) for i in range(nv)]


def shapes(world):
    out = []
    for b in bodies:
        Mue = world[b["bone"]]
        c_ue = Mue @ Vector(b["center"])
        if b["type"] == "sphere":
            p = sc.C3 @ c_ue
            out.append((p, p, b["radius"] + thick, b["radius"] + thick))
            continue
        x, y, z, w = b["quat"]
        ax = Mue.to_3x3() @ (Quaternion((w, x, y, z)) @ Vector((0, 0, 1)))
        A = sc.C3 @ (c_ue + ax * b["length"] / 2)
        B = sc.C3 @ (c_ue - ax * b["length"] / 2)
        rA, rB = (b["radius0"], b["radius1"]) if b["type"] == "tapered" else (b["radius"], b["radius"])
        dr = var.get("thigh_dr", 0.0) if b["bone"].startswith("thigh") else 0.0
        out.append((A, B, rA + dr + thick, rB + dr + thick))
    return out


def normals(pts):
    nrm = [Vector((0, 0, 0)) for _ in pts]
    for t in ptris:
        a, b, c = (pts[i] for i in t)
        n = (b - a).cross(c - a)
        for i in t:
            nrm[i] += n
    cen = sum(pts, Vector()) / len(pts)
    flip = sum(n.dot(p - cen) for p, n in zip(pts, nrm)) < 0
    return [(-n if flip else n).normalized() for n in nrm]


# ---- render mapping (rest) ------------------------------------------------------------------------------------------
n0 = normals(pv0)
bvh0 = BVHTree.FromPolygons(pv0, ptris)
mapping = []
for v in skirt.data.vertices:
    r = skirt.matrix_world @ v.co
    loc, _, ti, _ = bvh0.find_nearest(r)
    a, b, c = (pv0[i] for i in ptris[ti])
    v0, v1, v2 = b - a, c - a, loc - a
    d00, d01, d11, d20, d21 = v0.dot(v0), v0.dot(v1), v1.dot(v1), v2.dot(v0), v2.dot(v1)
    den = (d00 * d11 - d01 * d01) or 1e-9
    wb = (d11 * d20 - d01 * d21) / den
    wc = (d00 * d21 - d01 * d20) / den
    bc = (1 - wb - wc, wb, wc)
    n = sum((n0[i] * w for i, w in zip(ptris[ti], bc)), Vector()).normalized()
    mapping.append((ti, bc, (r - loc).dot(n), r.z))

skin = [bpy.data.objects[n] for n in ("body_2", "underwear", "knee-socks") if n in bpy.data.objects]
dom = {}
for o in skin:
    gn = {g.index: g.name for g in o.vertex_groups}
    dom[o.name] = []
    for v in o.data.vertices:
        gs = sorted(((e.weight, gn[e.group]) for e in v.groups), reverse=True)
        dom[o.name].append(gs[0][1] if gs else "-")


HANDS = ("hand", "thumb", "index", "middle", "ring", "pinky", "lowerarm", "upperarm")


def skin_check(fr, X):
    apply_frame(fr)
    deps.update()
    vs, tris, owner = [], [], []
    for o in skin:
        oe = o.evaluated_get(deps)
        base = len(vs)
        vs += [oe.matrix_world @ v.co for v in oe.data.vertices]
        for p in oe.data.polygons:
            tris.append(tuple(base + i for i in p.vertices))
            owner.append((o.name, p.vertices[0]))
    bvh = BVHTree.FromPolygons(vs, tris)
    sn = normals(X)
    hits = []
    for vi, (ti, bc, d, z0) in enumerate(mapping):
        r = sum(((X[i] + sn[i] * d) * w for i, w in zip(ptris[ti], bc)), Vector())
        loc, fn, fi, dist = bvh.find_nearest(r)
        if dist is not None and dist < 4.0 and (r - loc).dot(fn) < 0:
            on, ov = owner[fi]
            if dom[on][ov].startswith(HANDS):
                continue
            # confirm: going out along the cloth normal, the first skin crossing must be an exit
            n = sum((sn[i] * w for i, w in zip(ptris[ti], bc)), Vector()).normalized()
            hl, hn, hi, hd = bvh.ray_cast(r, n, 8.0)
            if var.get("strict", True) and (hl is None or hn.dot(n) <= 0):
                continue
            hits.append((dist if hd is None else min(dist, hd), z0, dom[on][ov], vi))
    # validation: own skinning vs Blender's evaluated proxy (only meaningful without subdivision / re-weighting)
    return hits


# ---- solver ---------------------------------------------------------------------------------------------------------
G = Vector((0, 0, -980.0))
DT = 1.0 / hz
damp = 1.0 - (1.0 - cfg["Damping"]["X"]) ** (sf / hz)


def step(X, Xp, anc, an, sh):
    Xn = []
    for i in range(nv):
        if md[i] <= 0:
            Xn.append(anc[i].copy())
            continue
        v = (X[i] - Xp[i]) * (1.0 - damp)
        Xn.append(X[i] + v + G * DT * DT)
    for _ in range(var.get("iters", 2)):
        for a, b, rest, s in E:
            d = Xn[b] - Xn[a]
            L = d.length
            if L < 1e-6:
                continue
            ia, ib = md[a] > 0, md[b] > 0
            wsum = ia + ib
            if not wsum:
                continue
            c = d * ((L - rest) / L * s / wsum)
            if ia:
                Xn[a] += c
            if ib:
                Xn[b] -= c
    for i in range(nv):
        if md[i] <= 0:
            continue
        t, L = tether[i]
        d = Xn[i] - Xn[t]
        if d.length > L:
            Xn[i] = Xn[t] + d.normalized() * L
        off = Xn[i] - anc[i]
        if off.length > md[i]:
            Xn[i] = anc[i] + off.normalized() * md[i]
        R, D = bs[i]
        if R > 0:
            c = anc[i] - an[i] * D
            if (Xn[i] - c).length < R:
                Xn[i] = c + (Xn[i] - c).normalized() * R
        p = Xn[i]
        for A, B, rA, rB in sh:
            d = B - A
            t_ = max(0.0, min(1.0, (p - A).dot(d) / d.length_squared))
            q = A + d * t_
            rr = rA + (rB - rA) * t_
            o = p - q
            if o.length < rr:
                p = q + (o.normalized() if o.length > 1e-6 else Vector((0, 0, 1))) * rr
        Xn[i] = p
    return Xn, X


res = {"var": var, "rings": rings, "segs": segs, "anims": []}
for ap in anims:
    a = json.load(open(ap))
    fps = a.get("fps", 30.0)
    frs = a["frames"]
    Qs = [frame_q(fr) for fr in frs]
    w0 = world_of(Qs[0])
    X = anchors(w0)
    Xp = [x.copy() for x in X]
    sh0 = shapes(w0)
    an0 = normals(X)
    anc0 = [x.copy() for x in X]
    for _ in range(int(hz * 0.6)):           # settle in the first pose
        X, Xp = step(X, Xp, anc0, an0, sh0)
    rows = []
    for k in range(len(frs)):
        if k > 0:
            span = (frs[k]["frame"] - frs[k - 1]["frame"]) / fps
            n = max(1, int(round(span * hz)))
            for s in range(1, n + 1):
                w = world_of(lerp_q(Qs[k - 1], Qs[k], s / n))
                anc = anchors(w)
                X, Xp = step(X, Xp, anc, normals(anc), shapes(w))
        hits = skin_check(frs[k], X)
        if var.get("diag") and var["diag"] in a["name"] and k in var.get("dframes", []):
            anc_d = anchors(world_of(Qs[k]))
            an_d = normals(anc_d)
            print("DIAG frame", frs[k]["frame"])
            seen = set()
            for h in sorted(hits, reverse=True):
                if h[0] < 1.0 or h[2].startswith("thigh"):
                    continue
                ti, bc, d, z0 = mapping[h[3]]
                key = ti
                if key in seen:
                    continue
                seen.add(key)
                info = []
                for i in ptris[ti]:
                    off = X[i] - anc_d[i]
                    info.append("r%d s%d in%.1f tan%.1f md%.1f" % (i // segs, i % segs, -off.dot(an_d[i]), (off - an_d[i] * off.dot(an_d[i])).length, md[i]))
                print("  depth %.1f z0 %.0f %s | %s" % (h[0], z0, h[2], " ; ".join(info)))
                if len(seen) >= 6:
                    break
        anc_k = anchors(world_of(Qs[k]))
        atmax = sum(1 for i in range(nv) if md[i] > 0 and (X[i] - anc_k[i]).length > md[i] - 0.05)
        if k == 0:
            pe = proxy.evaluated_get(deps)
            if sr == ss == 1:
                own = anchors(world_of(Qs[0]))
                err = max((own[i] - pe.matrix_world @ pe.data.vertices[i].co).length for i in range(nv))
                print("VALIDATE anchor vs blender proxy max err %.3f cm" % err)
        st = max((X[a_] - X[b_]).length / rest for a_, b_, rest, s in E if s == 1.0)
        doms = {}
        for h in hits:
            kk = h[2].split("_twist")[0]
            doms[kk] = round(max(doms.get(kk, 0.0), h[0]), 1)
        rows.append({"frame": frs[k]["frame"], "n": len(hits), "depth": round(max([h[0] for h in hits] or [0.0]), 2),
                     "doms": doms, "stretch": round(st, 2), "atmax": atmax, "z": [round(min([h[1] for h in hits] or [0])), round(max([h[1] for h in hits] or [0]))]})
    res["anims"].append({"name": a["name"], "rows": rows})
    worst = max(rows, key=lambda r: r["depth"] * (r["n"] > 0) + 0.001 * r["n"])
    tot = sum(r["n"] * r["depth"] for r in rows)
    print("ANIM %-45s bad %2d/%2d  score %6.1f | worst f%s n=%d depth=%.1f doms=%s z=%s stretch=%.2f" % (
        a["name"].replace("MainChar_Attack_", "").replace("Man_Barehands_", ""), sum(r["n"] > 0 for r in rows), len(rows), tot,
        worst["frame"], worst["n"], worst["depth"], worst["doms"], worst["z"], worst["stretch"]) + " atmax=%d" % worst["atmax"])
json.dump(res, open(out_path, "w"))
print("SIM_DONE total score %.1f" % sum(r["n"] * r["depth"] for a in res["anims"] for r in a["rows"]))
