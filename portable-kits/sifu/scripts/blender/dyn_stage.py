# Bone-chain dynamics for build_karin.py: twin tails / fox tail / side hair ride existing Base_skeleton cloth bones
# (cloth_head_A_l/r_*, cloth_pelvis_A_*, accessories_head_01_*), simulated in-game by a post-process anim blueprint
# with a RigidBody node (the node is keyed by skeleton bone index, so only Base_skeleton bones may be simulated).
import math
import json
import bpy
from mathutils import Matrix, Vector
import sifu_common as sc
import dyn_tuning
import profiles
from cloth_stage import _closest_on_polyline

# Geometry only (masses, damping, limits, drives and collision filtering live in dyn_tuning.py):
# (karin chain prefix, sifu bones, parent, joint fractions along the chain, radius scale)
CHAINS = [
    ("Hair_tail_L", ["cloth_head_A_l_01", "cloth_head_A_l_02", "cloth_head_A_l_03"], "head", [0.0, 0.3, 0.62], 0.55),
    ("Hair_tail_R", ["cloth_head_A_r_01", "cloth_head_A_r_02", "cloth_head_A_r_03"], "head", [0.0, 0.3, 0.62], 0.55),
    ("Tail", ["cloth_pelvis_A_01", "cloth_pelvis_A_02", "cloth_pelvis_A_03", "cloth_pelvis_A_04", "cloth_pelvis_A_05"], "pelvis",
     [0.0, 0.2, 0.4, 0.6, 0.8], 0.55),
    ("Hair_side_L", ["accessories_head_01_l"], "head", [0.15], 0.6),
    ("Hair_side_R", ["accessories_head_01_r"], "head", [0.15], 0.6),
]


def _prefix_names(KJ, prefix):
    """Karin_Original VRM chains: bones named <prefix> / <prefix>.NNN."""
    return sorted([b for b in KJ if (b == prefix or b.startswith(prefix + ".")) and "_end" not in b and " " not in b],
                  key=lambda s: (len(s), s))


def _deepest_path(KP, root):
    kids = {}
    for b, p in KP.items():
        kids.setdefault(p, []).append(b)

    def depth(b):
        return 1 + max([depth(c) for c in kids.get(b, [])] or [0])
    path = [root]
    while kids.get(path[-1]):
        path.append(max(kids[path[-1]], key=depth))
    return path


def _subtree(KP, root):
    out = {root}
    grow = True
    while grow:
        grow = False
        for b, p in KP.items():
            if p in out and b not in out:
                out.add(b)
                grow = True
    return out


def _chain_points(KJ, KT, names, verts):
    pts = [KJ[b].copy() for b in names]
    last = (pts[-1] - pts[-2]).normalized() if len(pts) > 1 else (KT[names[-1]] - KJ[names[-1]]).normalized()
    proj = sorted((v - pts[-1]).dot(last) for v in verts)
    ext = proj[int(len(proj) * 0.97)] if proj else 1.0
    pts.append(pts[-1] + last * max(ext, 1.0))
    return pts


def _point_at(pts, f):
    seg = [(pts[i + 1] - pts[i]).length for i in range(len(pts) - 1)]
    tot = sum(seg)
    s, acc = f * tot, 0.0
    for i, L in enumerate(seg):
        if acc + L >= s or i == len(seg) - 1:
            return pts[i].lerp(pts[i + 1], 0.0 if L == 0 else min(1.0, (s - acc) / L))
        acc += L


def _ue_rot_along(d_ue):
    x = d_ue.normalized()
    ref = Vector((0, 1, 0)) if abs(x.y) < 0.9 else Vector((0, 0, 1))
    z = x.cross(ref).normalized()
    y = z.cross(x).normalized()
    return Matrix((x, y, z)).transposed()


def _hat(t, centers):
    w = [0.0] * len(centers)
    if t <= centers[0]:
        w[0] = 1.0
    elif t >= centers[-1]:
        w[-1] = 1.0
    else:
        for i in range(len(centers) - 1):
            if centers[i] <= t <= centers[i + 1]:
                a = (t - centers[i]) / (centers[i + 1] - centers[i])
                w[i], w[i + 1] = 1.0 - a, a
                break
    return w


def _seg_dist(p1, q1, p2, q2):
    """Closest distance between segments p1q1 and p2q2."""
    best = 1e18
    for i in range(11):
        a = p1.lerp(q1, i / 10)
        d = q2 - p2
        L2 = d.length_squared
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, (a - p2).dot(d) / L2))
        best = min(best, (a - (p2 + d * t)).length)
    return best


def _specs(meshes, KJ, KP, dom_groups, skel_parent):
    """Chain specs of the active profile: name, hosts, parent, fracs, rscale, centers, mode, parts [(obj, vidx)], names."""
    P = profiles.ACTIVE
    byname = {o.name: o for o in meshes}
    out = []
    if P["dyn"] == "default":
        for prefix, bones, parent, fracs, rscale in CHAINS:
            src = "tail" if prefix == "Tail" else "hair"
            dom = dom_groups[src]
            vidx = [i for i, g in enumerate(dom) if g is not None and g.startswith(prefix)]
            out.append({"name": prefix, "hosts": bones, "parent": parent, "fracs": fracs, "rscale": rscale, "mode": "parent",
                        "centers": None, "parts": [(byname[src], vidx)], "names": _prefix_names(KJ, prefix), "tune": None})
        return out
    for c in P["dyn"]:
        hosts = c["hosts"]
        parent = skel_parent[hosts[0]]
        for k in range(1, len(hosts)):
            if skel_parent[hosts[k]] != hosts[k - 1]:
                raise RuntimeError(f"{c['name']}: {hosts[k]} is not a child of {hosts[k - 1]} in Base_skeleton")
        names = c.get("path") or _deepest_path(KP, c["root"])
        bone_set = _subtree(KP, c["root"]) if c.get("subtree") else set(names)
        for r in c.get("exclude_subtrees", ()):
            bone_set -= _subtree(KP, r)
        parts = []
        for o in meshes:
            vidx = [i for i, g in enumerate(dom_groups[o.name]) if g in bone_set]
            if vidx:
                parts.append((o, vidx))
        if not parts:
            raise RuntimeError(f"{c['name']}: no vertices on {sorted(bone_set)[:6]}")
        out.append({"name": c["name"], "hosts": hosts, "parent": parent, "fracs": c["fracs"], "rscale": c["rscale"],
                    "mode": "orig", "centers": c.get("centers"), "blend": c.get("blend", 0.02), "parts": parts,
                    "names": names, "tune": c["tune"]})
    return out


def run(meshes, arm, pos, world, KJ, KT, dom_groups, collider_bodies, report, KP=None, skel_parent=None):
    """Adds the chain bones to `arm`, re-weights the chain vertices, returns (physics json, rigidbody node settings)."""
    new_bones = {}   # name -> (parent, matrix_bl)
    chain_info = []
    for spec in _specs(meshes, KJ, KP, dom_groups, skel_parent):
        bones, parent, fracs, rscale = spec["hosts"], spec["parent"], spec["fracs"], spec["rscale"]
        vco = [o.matrix_world @ o.data.vertices[i].co for o, vidx in spec["parts"] for i in vidx]
        pts = _chain_points(KJ, KT, spec["names"], vco)
        joints = [_point_at(pts, f) for f in fracs] + [_point_at(pts, 1.0)]
        # bone matrices: X along the chain (UE space), placed at the resampled joints
        prev = parent
        for k, b in enumerate(bones):
            a_ue, b_ue = sc.C3 @ joints[k], sc.C3 @ joints[k + 1]
            m_ue = _ue_rot_along(b_ue - a_ue).to_4x4()
            m_ue.translation = a_ue
            new_bones[b] = (prev, sc.ue_to_bl(m_ue))
            prev = b
        # radius per bone from the chain vertices
        samples = [_closest_on_polyline(v, pts) for v in vco]
        radii = []
        for k in range(len(bones)):
            lo, hi = fracs[k], (fracs[k + 1] if k + 1 < len(fracs) else 1.0)
            ds = sorted(d for d, s in samples if lo <= s <= hi)
            radii.append(max(0.8, (ds[int(len(ds) * 0.6)] if ds else 2.0) * rscale))
        chain_info.append((spec, pts, joints, radii))

    # --- add bones to the armature (edit mode) ---------------------------------------------------------------------------
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    for name, (parent, m) in new_bones.items():
        eb = arm.data.edit_bones.get(name) or arm.data.edit_bones.new(name)
        eb.head = (0, 0, 0)
        eb.tail = (0, 3.0, 0)
        eb.matrix = m
    for name, (parent, m) in new_bones.items():
        arm.data.edit_bones[name].parent = arm.data.edit_bones[parent]
        arm.data.edit_bones[name].use_connect = False
    bpy.ops.object.mode_set(mode="OBJECT")

    # --- weights ---------------------------------------------------------------------------------------------------------------
    for spec, pts, joints, radii in chain_info:
        bones, parent, fracs = spec["hosts"], spec["parent"], spec["fracs"]
        mids = [(fracs[k] + (fracs[k + 1] if k + 1 < len(fracs) else 1.0)) / 2 for k in range(len(bones))]
        if spec["centers"]:
            centers = spec["centers"]
        elif spec["mode"] == "parent":
            centers = [max(0.0, fracs[0] - 0.02)] + mids
            if len(bones) == 1:
                centers = [0.12, 0.75]
        else:
            centers = [max(0.0, fracs[0] - spec["blend"])] + mids
        names = [parent] + bones
        for obj, vidx in spec["parts"]:
            for n in names:
                if obj.vertex_groups.get(n) is None:
                    obj.vertex_groups.new(name=n)
            gname = {g.index: g.name for g in obj.vertex_groups}
            for vi in vidx:
                co = obj.matrix_world @ obj.data.vertices[vi].co
                _, s = _closest_on_polyline(co, pts)
                ws = _hat(s, centers)
                if spec["mode"] == "orig":       # the chain takes over from the vertex's own (folded) weights
                    own = {gname[e.group]: e.weight for e in obj.data.vertices[vi].groups}
                    tot = sum(own.values()) or 1.0
                    acc = {n: w / tot * ws[0] for n, w in own.items()}
                    for n, w in zip(bones, ws[1:]):
                        acc[n] = acc.get(n, 0.0) + w
                    items = sorted(acc.items(), key=lambda kv: -kv[1])[:8]
                else:
                    items = list(zip(names, ws))
                for g in obj.vertex_groups:
                    g.remove([vi])
                for n, w in items:
                    if w > 1e-3:
                        obj.vertex_groups[n].add([vi], w, "REPLACE")

    # --- physics asset ------------------------------------------------------------------------------------------------------
    bodies = []
    for b in collider_bodies:
        b = dict(b, kinematic=True)
        if b["type"] == "tapered":          # RBAN over PhysX has no tapered capsules: use the larger radius
            b = {k: v for k, v in b.items() if k not in ("radius0", "radius1")}
            b["type"] = "capsule"
        bodies.append(b)
    joints_json, disable = [], []
    col_segments = {}
    for b in collider_bodies:
        Mbl = world[b["bone"]]
        c_bl = sc.C3 @ (sc.bl_to_ue(Mbl).to_3x3() @ Vector(b["center"]) + sc.bl_to_ue(Mbl).translation)
        if b["type"] == "sphere":
            col_segments[b["bone"]] = (c_bl, c_bl, b["radius"])
        else:
            half = b["length"] / 2
            from mathutils import Quaternion
            q = Quaternion((b["quat"][3], b["quat"][0], b["quat"][1], b["quat"][2]))
            ax_local = q @ Vector((0, 0, 1))
            ax_bl = sc.C3 @ (sc.bl_to_ue(Mbl).to_3x3() @ ax_local)
            col_segments[b["bone"]] = (c_bl - ax_bl * half, c_bl + ax_bl * half, b["radius"])
    for spec, pts, jts, radii in chain_info:
        bones, parent = spec["hosts"], spec["parent"]
        prev = parent
        for k, b in enumerate(bones):
            L = (jts[k + 1] - jts[k]).length
            r = min(radii[k], L * 0.45)
            length = max(0.5, L - r)
            q = Vector((0, 0, 1)).rotation_difference(Vector((1, 0, 0)))
            bodies.append({"bone": b, "type": "capsule", "center": [L / 2, 0, 0], "quat": [q.x, q.y, q.z, q.w],
                           "radius": round(r, 3), "length": round(length, 3), "kinematic": False})
            joints_json.append({"child": b, "parent": prev})
            # disable collisions with colliders overlapping this body at rest
            for cb, (p2, q2, r2) in col_segments.items():
                # new-style chains keep their leg collisions even when overlapping at rest (RBAN pushes them out;
                # otherwise a kick passes straight through a hanging panel)
                if spec["mode"] == "orig" and cb.startswith(("thigh_", "calf_")):
                    continue
                if _seg_dist(jts[k], jts[k + 1], p2, q2) < r + r2 + 0.5:
                    disable.append([b, cb])
            prev = b
    physics = {"bodies": bodies, "joints": joints_json, "rest_overlap_pairs": disable,
               "chains": [dict({"name": c[0]["name"], "bones": c[0]["hosts"], "parent": c[0]["parent"]},
                               **({"tune": c[0]["tune"]} if c[0]["tune"] else {})) for c in chain_info]}
    rigidbody = {}
    report["dynamics_tuning"] = dyn_tuning.apply(physics, rigidbody)
    report["dynamics"] = {c[0]["name"]: {"bones": c[0]["hosts"], "radii": [round(x, 2) for x in c[3]],
                                         "seg_len": [round((c[2][k + 1] - c[2][k]).length, 2) for k in range(len(c[0]["hosts"]))],
                                         "verts": sum(len(v) for _, v in c[0]["parts"]),
                                         "joints_cm": [[round(x, 1) for x in j] for j in c[2]]}
                          for c in chain_info}
    report["dynamics_rest_overlaps"] = disable
    return physics, rigidbody
