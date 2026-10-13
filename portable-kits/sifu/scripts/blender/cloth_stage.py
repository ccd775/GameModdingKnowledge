# Cloth / collision / vertex-color stage for build_karin.py (Blender 4.2, cm scene).
#  * splits the simulated render pieces into their own material slots (UE sections),
#  * builds low-res proxy sim meshes (tubes along Karin spring chains, a cone ring grid for the skirt) skinned to Sifu
#    bones, with per-vertex max distance in color.R (normalised; UE multiplies by the asset's MaxDistance),
#  * fits collision capsules to Karin's body for the cloth physics asset (UE bone-local),
#  * copies the original W mesh vertex colors (material masks) onto Karin by category.
import math
import bpy, bmesh
import numpy as np
from mathutils import Matrix, Vector, Quaternion
from mathutils.kdtree import KDTree
import sifu_common as sc
import profiles

# piece: (render slot, source mesh, chain prefix, root bone, max distance cm, ring count, sides, radius scale, nvcloth?)
# Volumetric strands are simulated as bone chains (dyn_stage.py); they keep their own section only so the material slot
# layout stays stable (W outfit overrides hit slots 11-16 and 18, which must stay proxy/dummy slots).
CHAINS = [
    ("Karin_TwinTail_L", "hair", "Hair_tail_L", "head", 30.0, 10, 6, 0.55, False),
    ("Karin_TwinTail_R", "hair", "Hair_tail_R", "head", 30.0, 10, 6, 0.55, False),
    ("Karin_SideHair_L", "hair", "Hair_side_L", "head", 7.0, 5, 5, 0.6, False),
    ("Karin_SideHair_R", "hair", "Hair_side_R", "head", 7.0, 5, 5, 0.6, False),
    ("Karin_Tail", "tail", "Tail", "pelvis", 35.0, 10, 8, 0.6, False),
]
# skirt: (render slot, source mesh, max distance cm, rings, segments around). 11 rings (3.6 cm apart) and a 240 Hz
# solver: with 6 rings a fast kick swept the thigh past the coarse lower rows (NvCloth has no continuous collision in
# UE 4.26), particles were pushed out on the far side and the stretched triangles let the thigh show through the side
# panels (`skirt_sim.py` over the run + kick/knee anims: thigh frames > 1 cm 14-41 -> 0-1 of 263).
SKIRT = ("Karin_Skirt", "skirt", 16.0, 11, 32)

HAIR_CFG = {"Damping": {"X": 0.5, "Y": 0.5, "Z": 0.5}, "LinearDrag": {"X": 0.4, "Y": 0.4, "Z": 0.4},
            "AngularDrag": {"X": 0.4, "Y": 0.4, "Z": 0.4}, "LinearInertiaScale": {"X": 0.5, "Y": 0.5, "Z": 0.5},
            "AngularInertiaScale": {"X": 0.5, "Y": 0.5, "Z": 0.5}, "CentrifugalInertiaScale": {"X": 0.5, "Y": 0.5, "Z": 0.5},
            "BendConstraint": {"Stiffness": 0.8}, "StiffnessFrequency": 60.0, "CollisionThickness": 1.0}
TAIL_CFG = dict(HAIR_CFG, **{"BendConstraint": {"Stiffness": 0.9}, "Damping": {"X": 0.4, "Y": 0.4, "Z": 0.4}})
SKIRT_CFG = {"Damping": {"X": 0.4, "Y": 0.4, "Z": 0.4}, "LinearDrag": {"X": 0.3, "Y": 0.3, "Z": 0.3},
             "AngularDrag": {"X": 0.3, "Y": 0.3, "Z": 0.3}, "LinearInertiaScale": {"X": 0.6, "Y": 0.6, "Z": 0.6},
             "AngularInertiaScale": {"X": 0.6, "Y": 0.6, "Z": 0.6}, "CentrifugalInertiaScale": {"X": 0.6, "Y": 0.6, "Z": 0.6},
             "BendConstraint": {"Stiffness": 0.6}, "StiffnessFrequency": 60.0, "SolverFrequency": 240.0,
             "CollisionThickness": 1.0}
# Shapes the skirt collides with. The torso/neck/head capsules are round where the waist is not: at rest spine_01/02
# sat 4-6 cm outside the waistband and yoke and pushed the top proxy rings out (loose, gaping waist). They stay in the
# collider list for the bone chains (dyn_stage) but are left out of the skirt's physics asset.
SKIRT_COLLIDERS = ("pelvis", "thigh_", "calf_", "upperarm_", "lowerarm_")
# Skirt backstops (NvCloth separation spheres, UE BackstopDistance/Radius): each particle stays outside a sphere of radius
# BACKSTOP_R whose centre lies BACKSTOP_R + BACKSTOP_TRAVEL behind its skinned position along the proxy normal, i.e. it
# may move at most BACKSTOP_TRAVEL inward. Without them the cone sagged into the buttocks, belly and crotch, which no
# capsule fits without pushing the waist out: below the waistband the render skirt is 0-4 cm off that skin and the gap
# closes further in motion (scratchpad backstop_probe over the run frames). Rings 1..n-2 get no inward travel; the hem
# ring only ever meets the thighs (capsules) and stays free to swing in between the legs. Colour G = distance and
# B = radius, both / BACKSTOP_SCALE.
BACKSTOP_R, BACKSTOP_TRAVEL, BACKSTOP_SCALE = 15.0, 0.0, 32.0


def _mat_copy(src_name, new_name):
    if new_name in bpy.data.materials:
        return bpy.data.materials[new_name]
    src = bpy.data.materials.get(src_name)
    m = src.copy() if src else bpy.data.materials.new(new_name)
    m.name = new_name
    return m


def _assign_slot(obj, poly_mask, mat):
    if mat.name not in [m.name for m in obj.data.materials if m]:
        obj.data.materials.append(mat)
    idx = [m.name if m else "" for m in obj.data.materials].index(mat.name)
    n = 0
    for p, on in zip(obj.data.polygons, poly_mask):
        if on:
            p.material_index = idx
            n += 1
    return n


def _resample(points, n):
    seg = [(points[i + 1] - points[i]).length for i in range(len(points) - 1)]
    tot = sum(seg)
    out = []
    for k in range(n):
        s = tot * k / (n - 1)
        acc = 0.0
        for i, L in enumerate(seg):
            if acc + L >= s - 1e-9 or i == len(seg) - 1:
                a = 0.0 if L == 0 else (s - acc) / L
                out.append(points[i].lerp(points[i + 1], min(1.0, max(0.0, a))))
                break
            acc += L
    return out, tot


def _closest_on_polyline(p, pts):
    best = (1e18, 0.0)
    acc = 0.0
    tot = sum((pts[i + 1] - pts[i]).length for i in range(len(pts) - 1))
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        d = b - a
        L2 = d.length_squared
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, (p - a).dot(d) / L2))
        q = a + d * t
        dist = (p - q).length
        if dist < best[0]:
            best = (dist, (acc + t * math.sqrt(L2)) / tot)
        acc += math.sqrt(L2)
    return best


def _new_mesh_obj(name, verts, faces, arm, groups, colors, mat):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.update()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    me.materials.append(mat)
    for vi, gw in enumerate(groups):
        for b, w in gw:
            vg = obj.vertex_groups.get(b) or obj.vertex_groups.new(name=b)
            vg.add([vi], w, "REPLACE")
    attr = me.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
    for vi, c in enumerate(colors):
        attr.data[vi].color = c
    obj.parent = arm
    mod = obj.modifiers.new("Armature", "ARMATURE")
    mod.object = arm
    for p in me.polygons:
        p.use_smooth = True
    return obj


def _tube(name, centers, radii, sides, arm, root_bone, maxd_profile, mat):
    """Open tube with a fan cap at the tip; returns the object."""
    verts, faces, groups, colors = [], [], [], []
    # parallel-transport frames
    t0 = (centers[1] - centers[0]).normalized()
    ref = Vector((0, 0, 1)) if abs(t0.z) < 0.9 else Vector((1, 0, 0))
    nrm = t0.cross(ref).normalized()
    prev_t = t0
    n = len(centers)
    for i, c in enumerate(centers):
        t = (centers[min(i + 1, n - 1)] - centers[max(i - 1, 0)]).normalized()
        nrm = (nrm - t * nrm.dot(t)).normalized()
        bin_ = t.cross(nrm).normalized()
        prev_t = t
        f = i / (n - 1)
        md = maxd_profile(f)
        for k in range(sides):
            a = 2 * math.pi * k / sides
            verts.append(c + (nrm * math.cos(a) + bin_ * math.sin(a)) * radii[i])
            groups.append([(root_bone, 1.0)])
            colors.append((md, 0.0, 0.0, 1.0))
    for i in range(n - 1):
        for k in range(sides):
            a, b = i * sides + k, i * sides + (k + 1) % sides
            c, d = a + sides, b + sides
            faces.append((a, b, d))
            faces.append((a, d, c))
    tip = len(verts)
    verts.append(centers[-1] + prev_t * radii[-1] * 0.5)
    groups.append([(root_bone, 1.0)])
    colors.append((maxd_profile(1.0), 0.0, 0.0, 1.0))
    base = (n - 1) * sides
    for k in range(sides):
        faces.append((base + k, base + (k + 1) % sides, tip))
    return _new_mesh_obj(name, verts, faces, arm, groups, colors, mat)


def _weights_from_proxy(obj, proxy):
    """Skin the render piece like its proxy (barycentric on the nearest proxy triangle): the anim-only fallback (cloth
    off / blend-out) then matches the simulation's anchor."""
    from mathutils.bvhtree import BVHTree
    pv = [proxy.matrix_world @ v.co for v in proxy.data.vertices]
    tris = [tuple(p.vertices) for p in proxy.data.polygons]
    bvh = BVHTree.FromPolygons(pv, tris)
    pg = {g.index: g.name for g in proxy.vertex_groups}
    pw = [{pg[e.group]: e.weight for e in v.groups} for v in proxy.data.vertices]
    for g in list(obj.vertex_groups):
        obj.vertex_groups.remove(g)
    groups = {}
    for v in obj.data.vertices:
        loc, _, idx, _ = bvh.find_nearest(obj.matrix_world @ v.co)
        a, b, c = tris[idx]
        A, B, C = pv[a], pv[b], pv[c]
        v0, v1, v2 = B - A, C - A, loc - A
        d00, d01, d11, d20, d21 = v0.dot(v0), v0.dot(v1), v1.dot(v1), v2.dot(v0), v2.dot(v1)
        den = (d00 * d11 - d01 * d01) or 1e-9
        wb = (d11 * d20 - d01 * d21) / den
        wc = (d00 * d21 - d01 * d20) / den
        acc = {}
        for vi, f in ((a, 1.0 - wb - wc), (b, wb), (c, wc)):
            for n, w in pw[vi].items():
                acc[n] = acc.get(n, 0.0) + max(0.0, f) * w
        tot = sum(acc.values()) or 1.0
        for n, w in acc.items():
            if w / tot > 1e-3:
                if n not in groups:
                    groups[n] = obj.vertex_groups.new(name=n)
                groups[n].add([v.index], w / tot, "REPLACE")


def _offset_stats(obj, proxy):
    """Signed distance of the render vertices from the proxy surface (outward positive), percentiles in cm."""
    from mathutils.bvhtree import BVHTree
    pv = [proxy.matrix_world @ v.co for v in proxy.data.vertices]
    bvh = BVHTree.FromPolygons(pv, [tuple(p.vertices) for p in proxy.data.polygons])
    cy = sum(v.y for v in pv) / len(pv)
    d = []
    for v in obj.data.vertices:
        co = obj.matrix_world @ v.co
        loc, _, _, dist = bvh.find_nearest(co)
        out = Vector((loc.x, loc.y - cy, 0.0)).normalized()
        d.append(dist if (co - loc).dot(out) >= 0 else -dist)
    d = np.array(d)
    return {k: round(float(np.percentile(d, q)), 2) for k, q in (("p1", 1), ("p5", 5), ("p50", 50), ("p95", 95))}


def run(meshes, arm, pos, world, KJ, KT, dom_groups, w_glb, report):
    """meshes: Karin mesh objects (already re-skinned to Sifu bones). pos/world: Sifu joint positions/matrices (Blender cm).
    KJ/KT: Karin joint heads/tails (cm). dom_groups: {mesh name: [dominant Karin group per vertex]}."""
    byname = {o.name: o for o in meshes}
    cloth_specs, proxies = [], []
    P = profiles.ACTIVE
    chains = CHAINS if P["cloth_chains"] == "default" else P["cloth_chains"]
    skirt = SKIRT if P["skirt"] == "default" else P["skirt"]

    # ---- chain pieces --------------------------------------------------------------------------------------------
    for slot, src, prefix, root, maxd, rings, sides, rscale, use_cloth in chains:
        obj = byname[src]
        dom = dom_groups[src]
        mask_v = [g is not None and g.startswith(prefix) for g in dom]
        pmask = [sum(mask_v[v] for v in p.vertices) * 2 > len(p.vertices) for p in obj.data.polygons]
        if not any(pmask):
            report.setdefault("cloth_warnings", []).append(f"no polygons for {slot}")
            continue
        base_mat = obj.data.materials[obj.data.polygons[pmask.index(True)].material_index].name
        if base_mat.startswith("Karin_Hair"):
            base_mat = "Karin_Hair"
        npoly = _assign_slot(obj, pmask, _mat_copy(base_mat, slot))
        if not use_cloth:
            report.setdefault("cloth_pieces", {})[slot] = {"polys": npoly, "sim": "bone chain"}
            continue
        chain = sorted([b for b in KJ if (b == prefix or b.startswith(prefix + ".")) and "_end" not in b and " " not in b],
                       key=lambda s: (len(s), s))
        pts = [KJ[b].copy() for b in chain]
        vco = [obj.matrix_world @ obj.data.vertices[v].co for p, on in zip(obj.data.polygons, pmask) if on for v in p.vertices]
        last_dir = (pts[-1] - pts[-2]).normalized() if len(pts) > 1 else (KT[chain[-1]] - KJ[chain[-1]]).normalized()
        proj = sorted((v - pts[-1]).dot(last_dir) for v in vco)
        ext = proj[int(len(proj) * 0.97)] if proj else 1.0
        pts.append(pts[-1] + last_dir * max(ext, 1.0))
        centers, length = _resample(pts, rings)
        # radius per ring from render verts near that ring
        samples = [_closest_on_polyline(v, pts) for v in vco]
        radii = []
        for i in range(rings):
            f = i / (rings - 1)
            ds = sorted(d for d, s in samples if abs(s - f) < 0.6 / (rings - 1))
            r = ds[int(len(ds) * 0.7)] if ds else 1.0
            radii.append(max(0.6, r * rscale))
        prof = (lambda f: 0.0 if f < 0.06 else min(1.0, ((f - 0.06) / 0.94) ** 0.85))
        pname = "Proxy_" + slot.replace("Karin_", "")
        proxies.append(_tube(pname, centers, radii, sides, arm, root, prof, _mat_copy(base_mat, pname)))
        cfg = TAIL_CFG if "Tail" in slot and "Twin" not in slot else HAIR_CFG
        cloth_specs.append({"render_slot": slot, "proxy_slot": pname, "name": "Cloth_" + slot.replace("Karin_", ""),
                            "max_distance": maxd, "config": cfg})
        report.setdefault("cloth_pieces", {})[slot] = {"polys": npoly, "chain": chain, "length_cm": round(length, 2),
                                                       "radii": [round(r, 2) for r in radii]}

    # ---- skirt ----------------------------------------------------------------------------------------------------
    if skirt:
        slot, src, maxd, rings, segs = skirt
        obj = byname[src]
        _assign_slot(obj, [True] * len(obj.data.polygons), _mat_copy("Karin_Costume", slot))
        co = np.array([obj.matrix_world @ v.co for v in obj.data.vertices])
        cx, cy = 0.0, float(co[:, 1].mean())
        # top ring on the waistband's upper edge: render vertices above the proxy would be extrapolated from the first
        # simulated ring and swing opposite to it
        ztop, zbot = float(co[:, 2].max()), float(co[:, 2].min()) + 0.3
        ang = np.arctan2(co[:, 1] - cy, co[:, 0] - cx)
        rad = np.hypot(co[:, 0] - cx, co[:, 1] - cy)
        verts, groups, colors = [], [], []
        half_w = max(1.0, float(np.abs(co[:, 0]).max()))
        # The proxy sits on the inner envelope of the pleats (10th percentile radius): NvCloth collides only the proxy
        # particles and the render skirt follows at its rest offset, so render vertices inside the proxy would end up
        # inside the thighs by that offset.
        for i in range(rings):
            f = i / (rings - 1)
            z = ztop + (zbot - ztop) * f
            band = np.abs(co[:, 2] - z) < max(2.0, (ztop - zbot) / (rings - 1) * 0.6)
            for k in range(segs):
                a = -math.pi + 2 * math.pi * k / segs
                da = np.abs((ang - a + math.pi) % (2 * math.pi) - math.pi)
                sel = band & (da < 2 * math.pi / segs)
                r = float(np.percentile(rad[sel], 10)) if sel.sum() >= 3 else float(np.percentile(rad[band], 10))
                x, y = cx + r * math.cos(a), cy + r * math.sin(a)
                verts.append(Vector((x, y, z)))
                side = min(1.0, max(0.0, 0.5 + 0.5 * x / (half_w * 0.6)))
                # Karin faces -Y: front panels ride the thighs (a forward thigh pushes them), sides a bit more, back panels
                # stay on the pelvis (a forward thigh must not drag them into the buttocks; a backward thigh pushes them
                # through collision instead)
                front, back, lat = max(0.0, -math.sin(a)), max(0.0, math.sin(a)), abs(math.cos(a))
                leg = f * (0.55 * front + 0.6 * lat + 0.15 * back) / (front + lat + back)
                groups.append([("pelvis", 1.0 - leg), ("thigh_twist_02_l", leg * side), ("thigh_twist_02_r", leg * (1 - side))])
                bs = (BACKSTOP_R + BACKSTOP_TRAVEL, BACKSTOP_R) if 0 < i < rings - 1 else (0.0, 0.0)
                colors.append((0.0 if i == 0 else f ** 0.8, bs[0] / BACKSTOP_SCALE, bs[1] / BACKSTOP_SCALE, 1.0))
        faces = []
        for i in range(rings - 1):
            for k in range(segs):
                a, b = i * segs + k, i * segs + (k + 1) % segs
                faces += [(a, b + segs, b), (a, a + segs, b + segs)]   # outward normals: UE backstops push along -normal
        groups = [[(b, w) for b, w in g if w > 1e-3] for g in groups]
        pname = "Proxy_Skirt"
        proxy = _new_mesh_obj(pname, verts, faces, arm, groups, colors, _mat_copy("Karin_Costume", pname))
        proxies.append(proxy)
        _weights_from_proxy(obj, proxy)
        cloth_specs.append({"render_slot": slot, "proxy_slot": pname, "name": "Cloth_Skirt", "max_distance": maxd, "config": SKIRT_CFG,
                            "backstop_scale": BACKSTOP_SCALE})
        report.setdefault("cloth_pieces", {})[slot] = {"rings": rings, "segs": segs, "z": [round(ztop, 1), round(zbot, 1)],
                                                       "render_offset_cm": _offset_stats(obj, proxy)}

    # ---- collision capsules (UE bone-local) --------------------------------------------------------------------------
    body = byname[P["skin_mesh"]]
    vg = {g.index: g.name for g in body.vertex_groups}
    bco = [body.matrix_world @ v.co for v in body.data.vertices]
    bdom = []
    for v in body.data.vertices:
        gs = sorted(((g.weight, vg[g.group]) for g in v.groups), reverse=True)
        bdom.append(gs[0][1] if gs else None)

    def verts_of(prefixes):
        return [c for c, d in zip(bco, bdom) if d and any(d.startswith(p) for p in prefixes)]

    def capsule(bone, A, B, pts, pct=65, pad=0.5, shrink=0.0, max_r=1e9):
        d = B - A
        L = d.length
        ds = []
        for p in pts:
            t = (p - A).dot(d) / (L * L)
            if 0.15 <= t <= 0.85:
                r_ = (p - (A + d * t)).length
                if r_ <= max_r:
                    ds.append(r_)
        r = (sorted(ds)[int(len(ds) * pct / 100)] if ds else 3.0) + pad - shrink
        Mue = sc.bl_to_ue(world[bone])
        R = Mue.to_3x3()
        cen = sc.C3 @ ((A + B) / 2)
        loc = R.transposed() @ (cen - Mue.translation)
        axis = (R.transposed() @ (sc.C3 @ d)).normalized()
        q = Vector((0, 0, 1)).rotation_difference(axis)
        return {"bone": bone, "type": "capsule", "center": [round(x, 4) for x in loc], "quat": [q.x, q.y, q.z, q.w],
                "radius": round(r, 3), "length": round(L, 3)}

    def sphere(bone, center_bl, r):
        Mue = sc.bl_to_ue(world[bone])
        loc = Mue.to_3x3().transposed() @ (sc.C3 @ center_bl - Mue.translation)
        return {"bone": bone, "type": "sphere", "center": [round(x, 4) for x in loc], "radius": round(r, 3)}

    def tapered(bone, A, B, pts, pct=95, pad=0.3):
        """Tapered capsule A->B (NvCloth takes PA tapered capsules); radius0 at B (+Z end), radius1 at A."""
        d = B - A
        L = d.length
        near, far = [], []
        for p in pts:
            t = (p - A).dot(d) / (L * L)
            r_ = (p - (A + d * t)).length
            if 0.05 <= t <= 0.3:
                near.append(r_)
            elif 0.7 <= t <= 0.95:
                far.append(r_)
        cap = capsule(bone, A, B, pts)
        r1 = float(np.percentile(near, pct)) + pad if near else cap["radius"]
        r0 = float(np.percentile(far, pct)) + pad if far else cap["radius"]
        cap.update({"type": "tapered", "radius0": round(r0, 3), "radius1": round(r1, 3), "radius": round(max(r0, r1), 3)})
        return cap

    # thigh surface = skin plus the thigh-high socks (body_2 is cut away under the socks)
    sdom = []
    for socks in [byname[n] for n in P["thigh_meshes"] if n in byname]:
        sg = {g.index: g.name for g in socks.vertex_groups}
        for v in socks.data.vertices:
            gs = sorted(((g.weight, sg[g.group]) for g in v.groups), reverse=True)
            sdom.append((socks.matrix_world @ v.co, gs[0][1] if gs else None))
    bodies = []
    for s in ("l", "r"):
        thigh_pts = [c for c, d in zip(bco, bdom) if d and d.startswith("thigh_twist") and d.endswith(s)]
        thigh_pts += [c for c, d in sdom if d and d.startswith("thigh_twist") and d.endswith(s)]
        bodies.append(tapered(f"thigh_{s}", pos[f"thigh_{s}"], pos[f"calf_{s}"], thigh_pts))
        bodies.append(capsule(f"calf_{s}", pos[f"calf_{s}"], pos[f"foot_{s}"], [c for c in verts_of(["calf_twist"]) if (c.x > 0) == (s == "l")], pct=60, pad=0.5))
        bodies.append(capsule(f"upperarm_{s}", pos[f"upperarm_{s}"], pos[f"lowerarm_{s}"], [c for c in verts_of(["upperarm_twist"]) if (c.x > 0) == (s == "l")], pct=70, pad=1.5))
        bodies.append(capsule(f"lowerarm_{s}", pos[f"lowerarm_{s}"], pos[f"hand_{s}"], [c for c in verts_of(["lowerarm_twist"]) if (c.x > 0) == (s == "l")], pct=70, pad=1.5))
    # hips: horizontal capsule between the hip joints, radius from pelvis-dominant verts
    hipL, hipR = pos["thigh_l"].copy(), pos["thigh_r"].copy()
    hip_pts = verts_of(["pelvis"])
    bodies.append(capsule("pelvis", hipR, hipL, [p + Vector((0, 0, 0)) for p in hip_pts], pct=55, pad=0.5))
    torso = [c for c, d in zip(bco, bdom) if d and d.startswith(("pelvis", "spine", "clavicle", "neck"))]
    bodies.append(capsule("spine_01", pos["pelvis"], pos["spine_02"], torso, pct=55, pad=0.3, max_r=20))
    bodies.append(capsule("spine_02", pos["spine_02"], pos["spine_03"], torso, pct=55, pad=0.3, max_r=20))
    bodies.append(capsule("spine_03", pos["spine_03"], pos["neck_01"], torso, pct=50, pad=0.3, max_r=20))
    bodies.append(capsule("neck_01", pos["neck_01"], pos["head"], verts_of(["neck"]), pct=60, pad=0.3))
    face = byname["Body"]
    fco = np.array([face.matrix_world @ v.co for v in face.data.vertices])
    hc = Vector(((fco[:, 0].max() + fco[:, 0].min()) / 2, (fco[:, 1].max() + fco[:, 1].min()) / 2 + 2.0, (fco[:, 2].max() + fco[:, 2].min()) / 2 + 1.0))
    hr = float(min(fco[:, 0].max() - fco[:, 0].min(), fco[:, 2].max() - fco[:, 2].min())) * 0.45
    bodies.append(sphere("head", hc, hr))
    physics = {"bodies": [b for b in bodies if b["bone"].startswith(SKIRT_COLLIDERS)], "constraints": False}
    report["collision"] = {b["bone"]: (b["radius"], b.get("length"), b.get("radius0"), b.get("radius1")) for b in bodies}
    report["skirt_colliders"] = [b["bone"] for b in physics["bodies"]]

    # ---- vertex colors from the W mesh -------------------------------------------------------------------------------
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=w_glb)
    wobjs = [o for o in bpy.data.objects if o not in before]
    wmesh = [o for o in wobjs if o.type == "MESH" and o.name.startswith("SK_")][0]
    wme = wmesh.data
    wcol = wme.color_attributes[0]
    cats = {"skin_head": {"MI_MainChar_W_Head_Dyn"}, "skin_body": {"MI_MainChar_W_20_Body"},
            "cloth": {"MI_MainChar_W_BasicOutfit", "MI_MainChar_M_Vests"}}
    trees, vals = {}, {}
    for cat, mats in cats.items():
        pts, cols = [], []
        for p in wme.polygons:
            if wme.materials[p.material_index].name.split(".")[0] in mats:
                for li in p.loop_indices:
                    v = wme.loops[li].vertex_index
                    pts.append(wmesh.matrix_world @ wme.vertices[v].co)
                    cols.append(tuple(wcol.data[li].color) if wcol.domain == "CORNER" else tuple(wcol.data[v].color))
        kd = KDTree(len(pts))
        for i, p in enumerate(pts):
            kd.insert(p, i)
        kd.balance()
        trees[cat], vals[cat] = kd, cols
    # Karin -> W space: per-bone translation delta (rotations are identical by construction)
    w_pos = report["_w_pos"]
    stats = {}
    for o in meshes:
        me = o.data
        gname = {g.index: g.name for g in o.vertex_groups}
        attr = me.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
        mats = [m.name if m else "" for m in me.materials]
        vcat = {}
        for p in me.polygons:
            m = mats[p.material_index]
            cat = "skin_head" if m == "Karin_Face" else ("skin_body" if m == "Karin_Body" else "cloth")
            for v in p.vertices:
                vcat[v] = cat
        for v in me.vertices:
            co = o.matrix_world @ v.co
            delta = Vector()
            for g in v.groups:
                b = gname[g.group]
                if b in w_pos:
                    delta += (w_pos[b] - pos[b]) * g.weight
            cat = vcat.get(v.index, "cloth")
            _, idx, _ = trees[cat].find(co + delta)
            c = vals[cat][idx]
            attr.data[v.index].color = (c[0] + 0.5 / 255, c[1] + 0.5 / 255, c[2] + 0.5 / 255, c[3] + 0.5 / 255)
            stats.setdefault(cat, []).append(c)
    report["vcolor_mean"] = {k: [round(x, 3) for x in np.mean(np.array(v), axis=0)] for k, v in stats.items()}
    for o in wobjs:
        bpy.data.objects.remove(o, do_unlink=True)

    return proxies, cloth_specs, physics, bodies
