"""Add simulated chain bodies (hair, tail, skirt, ears, ribbons) to the game's player PhysicsAsset (game format).

Every KO_* bone of the cooked Karin mesh (except *_end tips) gets
- a BodySetup cloned from the game's LeftHand body: one capsule from the bone to its child, PhysType_Simulated, light
  mass, angular damping, no linear damping (it acts like wind while running);
- a PhysicsConstraintTemplate cloned from the game's spine4<-spine2 constraint between the bone and its nearest
  ancestor that has a body, joint frames on the bone's origin with the twist axis along the bone, hard limits (the
  template's are soft by default).
The constraint drives do not hold anything on the player mesh in game (t12-t15: flat springs up to 5879, then springs
sized from the chain inertia, I * omega^2, still left the tails a floaty pendulum and let bangs/skirt droop), so the
shape is held by hard limits and gravity:
- gravity tilt of the limit cone ("bias" > 0): the cone is tilted by bias degrees away from the direction gravity turns
  the segment, half angle bias + "slack", so the ref pose sits on the cone's lower edge and gravity presses the segment
  onto its authored pose (bangs cannot fall into the face, skirt plates cannot fall onto the legs); motion swings it out
  by up to 2 * bias + slack. Near-vertical segments (gravity torque < 5%) get a plain cone of half angle "swing".
- small cones: large ones let the chain swing far (pendulum) and, with the head tipped (t13 crouch), hold it far
  from hanging.
The drives stay sized from the inertia ("omega", "zeta"; force mode assumed, unlimited force, swing/twist drives on) in
case they run in some states; they pull towards the cone centre, i.e. at most "bias" off the ref pose.
Old (Deacon-sized) bodies can be refitted to Karin-sized capsules ("refit": bone -> [a, b, r] in component space).
CollisionDisableTable: new bodies never collide with each other; with an old body only when the chain lists it in
"collide" and the pair is clear by "margin" (2 cm) in the ref pose. Chains must not collide with a body of the bone they
hang from: a contact there fights the joint to the same kinematic bone and throws the chain out (t16/t17: twin tails
1.3 cm from the head collider stood out sideways like wings even with locked joints; t14: on the arm colliders).

usage (numpy): physchain.py <cooked mesh.uasset> <game PhysicsAsset.uasset> <out.uasset> [config.json]
config: {"refit": {...}, "margin": cm, "chains": {"<bone prefix>": {"radius": cm, "mass": kg, "bias": deg, "slack": deg,
         "swing": deg, "twist": deg, "omega": rad/s, "zeta": .., "spring": .., "damping": .., "root_exp": ..,
         "lin_damp": .., "ang_damp": .., "motion": Limited|Locked|Free, "drive_mult": ..,
         "gravity": bool, "collide": [old body bone, ...]}}}   (longest matching prefix wins)
"""
import argparse, json, re, struct, sys, uuid
import numpy as np
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import upkg, refskel

HEAD = ["head"]
DEFAULT = {"margin": 2.0, "refit": {}, "chains": {
    "KO_": {"radius": 1.2, "mass": 0.05, "bias": 3, "slack": 1, "swing": 4, "twist": 2, "omega": 15, "zeta": 0.7,
            "spring": 0, "damping": 0, "root_exp": 0.0, "lin_damp": 0.0, "ang_damp": 2.0, "gravity": True, "collide": []},
    "KO_Ear": {"radius": 2.5, "mass": 0.08, "bias": 3, "slack": 0.5, "swing": 3, "omega": 30, "zeta": 0.8},
    "KO_Hair_front": {"radius": 1.0, "mass": 0.03, "bias": 2, "slack": 0.5, "swing": 2, "omega": 25, "zeta": 0.8},
    "KO_Hair_side": {"radius": 1.0, "mass": 0.03, "bias": 3, "slack": 0.5, "swing": 3, "omega": 20, "zeta": 0.7},
    "KO_Hair_tail": {"radius": 2.2, "mass": 0.08, "bias": 3, "slack": 1.5, "swing": 5, "omega": 12, "zeta": 0.7,
                     "collide": ["spine4", "spine2"]},
    "KO_Ribbon": {"radius": 1.0, "mass": 0.02, "bias": 6, "slack": 2, "swing": 8, "omega": 12, "zeta": 0.5},
    "KO_Tail": {"radius": 3.0, "mass": 0.1, "bias": 4, "slack": 1.5, "swing": 5, "omega": 12, "zeta": 0.7,
                "collide": ["LeftUpLeg", "RightUpLeg"]},
    "KO_Skirt": {"radius": 1.5, "mass": 0.05, "bias": 6, "slack": 0.5, "swing": 4, "omega": 25, "zeta": 0.7,
                 "collide": ["LeftUpLeg", "RightUpLeg"]},
}}
BODY_TEMPLATE_BONE = "LeftHand"
CONSTRAINT_TEMPLATE = ("spine4", "spine2")
END = re.compile(r"_end(-\d+)?$")

def cfg_for(cfg, name):
    chains = {**DEFAULT["chains"], **cfg.get("chains", {})}
    out = dict(DEFAULT["chains"]["KO_"]); out.update(chains["KO_"])
    best = max((p for p in chains if name.startswith(p)), key=len)
    out.update(chains[best])
    return out

def quat_from_z(u):
    """unit quaternion (x, y, z, w) rotating +Z onto unit vector u"""
    z = np.array([0.0, 0.0, 1.0]); c = float(z @ u)
    if c < -0.999999:
        return (1.0, 0.0, 0.0, 0.0)
    v = np.cross(z, u); w = 1.0 + c
    q = np.array([v[0], v[1], v[2], w]); q /= np.linalg.norm(q)
    return tuple(float(x) for x in q)

def seg_dist(p1, q1, p2, q2):
    """closest distance between segments p1q1 and p2q2"""
    d1, d2, r = q1 - p1, q2 - p2, p1 - p2
    a, e, f = d1 @ d1, d2 @ d2, d2 @ r
    if a < 1e-9 and e < 1e-9: return float(np.linalg.norm(r))
    if a < 1e-9: s, t = 0.0, np.clip(f / e, 0, 1)
    else:
        c = d1 @ r
        if e < 1e-9: t, s = 0.0, np.clip(-c / a, 0, 1)
        else:
            b = d1 @ d2; den = a * e - b * b
            s = np.clip((b * f - c * e) / den, 0, 1) if den > 1e-9 else 0.0
            t = (b * s + f) / e
            if t < 0: t, s = 0.0, np.clip(-c / a, 0, 1)
            elif t > 1: t, s = 1.0, np.clip((b - c) / a, 0, 1)
    return float(np.linalg.norm((p1 + d1 * s) - (p2 + d2 * t)))

def props_of(pkg, data):
    return {p.name: p for p in upkg.parse_props(pkg, data)}

def capsule_world(bone_m, center, quat, radius, length):
    R = refskel.quat_mat(*quat)
    axis = R @ np.array([0.0, 0.0, 1.0])
    c = bone_m[:3, :3] @ np.array(center) + bone_m[:3, 3]
    ax = bone_m[:3, :3] @ axis
    h = length / 2.0
    return c - ax * h, c + ax * h, radius

def chain_capsules(rs, cfg=DEFAULT):
    """[(bone index, child index, capsule (a, b, r), segment length)] for every simulated KO_* bone, in bone order"""
    names, parents, C, L = rs["names"], rs["parents"], rs["component"], rs["local"]
    children = {}
    for i, p in enumerate(parents):
        children.setdefault(p, []).append(i)
    out = []
    for i, n in enumerate(names):
        if not n.startswith("KO_") or END.search(n) or not children.get(i):
            continue
        t = L[children[i][0]][:3, 3]; ln = float(np.linalg.norm(t))
        if ln < 0.2:
            continue
        r = min(cfg_for(cfg, n)["radius"], 0.45 * ln)
        p0 = C[i][:3, 3]; p1 = C[i][:3, :3] @ t + p0
        out.append((i, children[i][0], (p0 + (p1 - p0) * (r / ln), p1 - (p1 - p0) * (r / ln), r), ln))
    return out

def bool_tag(pkg, name, value):
    return (struct.pack("<ii", pkg.name_index(name), 0) + struct.pack("<ii", pkg.name_index("BoolProperty"), 0)
            + struct.pack("<ii", 0, 0) + bytes([1 if value else 0]))

def insert_in_struct(d, sp, blob):
    """insert tags before the None that ends struct property sp (Prop of d) and grow its tag size"""
    d = bytearray(d)
    struct.pack_into("<i", d, sp.start + 16, sp.size + len(blob))
    return bytes(d[:sp.vend - 8]) + blob + bytes(d[sp.vend - 8:])

def build(mesh_path, pa_path, out_path, cfg=DEFAULT):
    rs = refskel.read(mesh_path)
    names, parents, C, L = rs["names"], rs["parents"], rs["component"], rs["local"]
    bone = {n.lower(): i for i, n in enumerate(names)}
    pkg = upkg.Package(open(pa_path, "rb").read())
    datas = [pkg.export_data(i) for i in range(len(pkg.exports))]
    cls = [pkg.ref(e["Class"]).rsplit(".", 1)[-1] for e in pkg.exports]
    pa = cls.index("PhysicsAsset")
    PP = props_of(pkg, datas[pa])
    def arr(p):
        n = struct.unpack_from("<i", datas[pa], p.vstart)[0]
        return list(struct.unpack_from("<%di" % n, datas[pa], p.vstart + 4))
    body_exports, cons_exports = arr(PP["BodySetup"]), arr(PP["ConstraintSetup"])
    refit = {k.lower(): v for k, v in cfg.get("refit", {}).items()}
    # existing bodies: bone name and capsule (refitted ones rewritten to the Karin-sized capsule)
    old, refitted = [], {}
    for ex in body_exports:
        d = bytearray(datas[ex - 1]); P = props_of(pkg, bytes(d))
        bn = pkg.name(struct.unpack_from("<ii", d, P["BoneName"].vstart))
        cap = None
        for kind in (P["AggGeom"].children or []):
            if not kind.children or bn.lower() not in bone:
                continue
            E = {c.name: c for c in kind.children[0]}
            f = lambda k: struct.unpack_from("<f", d, E[k].vstart)[0]
            ctr = struct.unpack_from("<3f", d, E["Center"].vstart); q = struct.unpack_from("<4f", d, E["Orientation"].vstart)
            M = C[bone[bn.lower()]]
            if kind.name == "SphylElems" and bn.lower() in refit:
                a, b, r = (np.array(refit[bn.lower()][0]), np.array(refit[bn.lower()][1]), float(refit[bn.lower()][2]))
                refitted[bn] = {"radius": [round(f("Radius"), 2), round(r, 2)]}
                Ri = M[:3, :3].T
                ax = b - a; ln = float(np.linalg.norm(ax)); u = Ri @ (ax / ln) if ln > 1e-6 else np.array([0.0, 0.0, 1.0])
                struct.pack_into("<3f", d, E["Center"].vstart, *(Ri @ ((a + b) / 2 - M[:3, 3])))
                struct.pack_into("<4f", d, E["Orientation"].vstart, *quat_from_z(u))
                struct.pack_into("<f", d, E["Radius"].vstart, r)
                struct.pack_into("<f", d, E["Length"].vstart, max(ln, 0.01))
                datas[ex - 1] = bytes(d)
                cap = (a, b, r)
            elif kind.name == "SphylElems":
                cap = capsule_world(M, ctr, q, f("Radius"), f("Length"))
            elif kind.name == "BoxElems":   # box (full extents X, Y, Z) -> capsule along its longest local axis
                ext = np.array([f("X"), f("Y"), f("Z")]); a = int(ext.argmax())
                rad = float(np.delete(ext, a).mean()) / 2
                R = refskel.quat_mat(*q)
                c0 = M[:3, :3] @ np.array(ctr) + M[:3, 3]; ax = M[:3, :3] @ R[:, a]
                h = max(ext[a] / 2 - rad, 0.0)
                cap = (c0 - ax * h, c0 + ax * h, rad)
            break
        old.append((bn, cap))
    missing = set(refit) - {bn.lower() for bn in refitted}
    if missing:
        raise SystemExit("refit bodies not found / not capsules: %s" % sorted(missing))
    has_body = {bn.lower(): i for i, (bn, _) in enumerate(old)}
    tb = next(ex for ex in body_exports if old[body_exports.index(ex)][0].lower() == BODY_TEMPLATE_BONE.lower())
    def cons_bones(ex):
        d = datas[ex - 1]; I = {c.name: c for c in props_of(pkg, d)["DefaultInstance"].children}
        return tuple(pkg.name(struct.unpack_from("<ii", d, I[f].vstart)).lower() for f in ("ConstraintBone1", "ConstraintBone2"))
    tc = next(ex for ex in cons_exports if cons_bones(ex) == CONSTRAINT_TEMPLATE)
    TB, TC = datas[tb - 1], datas[tc - 1]
    TBP, TCP = props_of(pkg, TB), props_of(pkg, TC)
    tb_el = {c.name: c for c in TBP["AggGeom"].children[0].children[0]}
    tb_di = {c.name: c for c in TBP["DefaultInstance"].children}
    tc_di = {c.name: c for c in TCP["DefaultInstance"].children}
    assert not {"bSwingLimitSoft", "bTwistLimitSoft", "bEnableGravity", "bEnableSwingDrive", "bEnableTwistDrive",
                "AngularDriveForceLimit"} & (set(tc_di) | set(tb_di))
    nm = lambda s: struct.pack("<ii", pkg.name_index(s), 0)
    def fname(s):
        m = re.match(r"^(.*)_(\d+)$", s)
        if m and not m.group(2).startswith("0") or (m and m.group(2) == "0"):
            return struct.pack("<ii", pkg.name_index(m.group(1)), int(m.group(2)) + 1)
        return nm(s)
    ptype_tag = nm("PhysicsType") + nm("ByteProperty") + struct.pack("<ii", 8, 0) + nm("EPhysicsType") + nm("PhysType_Simulated")
    caps = chain_capsules(rs, cfg)
    # segments from each chain bone to its tip (drive strength grows towards the root)
    seg_of = {i: k for k, (i, _, _, _) in enumerate(caps)}
    down = {}
    for i, _, _, _ in reversed(caps):
        kids = [k for k in seg_of if parents[k] == i]
        down[i] = 1 + max((down[k] for k in kids), default=0)
    # inertia (kg cm^2) of each joint's sub-chain about the joint origin, ref pose
    com = {i: ((cap[0] + cap[1]) / 2, cfg_for(cfg, names[i])["mass"], ln) for i, _, cap, ln in caps}
    def under(i, j):
        while j >= 0:
            if j == i: return True
            j = parents[j]
        return False
    inertia = {i: sum(m * (float(np.sum((p - C[i][:3, 3]) ** 2)) + l * l / 12) for j, (p, m, l) in com.items() if under(i, j))
               for i in com}
    new_bodies, new_caps, report = [], [], []
    body_index = dict(has_body)
    for i, kid, cap, ln in caps:
        c = cfg_for(cfg, names[i])
        r = cap[2]
        t = L[kid][:3, 3]; u = t / ln
        d = bytearray(TB)
        struct.pack_into("<3f", d, tb_el["Center"].vstart, *(t / 2))
        struct.pack_into("<4f", d, tb_el["Orientation"].vstart, *quat_from_z(u))
        struct.pack_into("<f", d, tb_el["Radius"].vstart, r)
        struct.pack_into("<f", d, tb_el["Length"].vstart, max(ln - 2 * r, 0.01))
        d[TBP["BoneName"].vstart:TBP["BoneName"].vstart + 8] = fname(names[i])
        struct.pack_into("<f", d, tb_di["MassInKg"].vstart, c["mass"])
        struct.pack_into("<f", d, tb_di["LinearDamping"].vstart, c["lin_damp"])
        struct.pack_into("<f", d, tb_di["AngularDamping"].vstart, c["ang_damp"])
        d = bytes(d)
        if not c["gravity"]:
            d = insert_in_struct(d, props_of(pkg, d)["DefaultInstance"], bool_tag(pkg, "bEnableGravity", False))
        end = upkg.parse_props(pkg, d).end   # props end - 8 is the None; guid-bool + BodySetupGuid follow the props
        d = bytearray(d); d[end + 4:end + 20] = uuid.uuid4().bytes
        d = bytes(d[:end - 8]) + ptype_tag + bytes(d[end - 8:])
        ex = pkg.add_export(tb - 1, (pkg.name_index("BodySetup"), 5001 + len(new_bodies)), pa + 1)
        datas.append(d)
        body_index[names[i].lower()] = len(old) + len(new_bodies)
        new_bodies.append(ex)
        new_caps.append((names[i], cap))
    # constraints: child body -> nearest ancestor with a body
    new_cons = []
    for (bn, _), (i, kid, cap, ln) in zip(new_caps, caps):
        a = parents[i]
        while a >= 0 and names[a].lower() not in body_index:
            a = parents[a]
        if a < 0:
            raise SystemExit("no ancestor body for " + bn)
        c = cfg_for(cfg, bn)
        if c.get("omega"):
            spring, damping = inertia[i] * c["omega"] ** 2, 2 * c["zeta"] * inertia[i] * c["omega"]
        else:
            scale = down[i] ** c["root_exp"]
            spring, damping = c["spring"] * scale, c["damping"] * scale
        spring, damping = spring * c.get("drive_mult", 1.0), damping * c.get("drive_mult", 1.0)
        u = C[i][:3, :3] @ L[kid][:3, 3]; u /= np.linalg.norm(u)
        y = C[i][:3, :3] @ np.array([0.0, 1.0, 0.0]); y -= u * (y @ u)
        if np.linalg.norm(y) < 1e-4:
            y = C[i][:3, :3] @ np.array([0.0, 0.0, 1.0]); y -= u * (y @ u)
        y /= np.linalg.norm(y)
        # gravity tilt of the limit cone: rotate the parent frame by "bias" away from the way gravity turns the segment
        g = np.array([0.0, 0.0, -1.0]); gt = g - u * (g @ u)
        if c["bias"] > 0 and np.linalg.norm(gt) > 0.05:
            b = -gt / np.linalg.norm(gt); ax = np.cross(u, b); ax /= np.linalg.norm(ax)
            th = np.radians(c["bias"]); K = np.array([[0, -ax[2], ax[1]], [ax[2], 0, -ax[0]], [-ax[1], ax[0], 0]])
            Rb = np.eye(3) + np.sin(th) * K + (1 - np.cos(th)) * K @ K
            cone, mode = c["bias"] + c["slack"], "bias"
        else:
            Rb, cone, mode = np.eye(3), c["swing"], "plain"
        o = C[i][:3, 3]
        d = bytearray(TC)
        for f, b in (("JointName", bn), ("ConstraintBone1", bn), ("ConstraintBone2", names[a])):
            d[tc_di[f].vstart:tc_di[f].vstart + 8] = fname(b)
        for suffix, M, R in (("1", C[i], np.eye(3)), ("2", C[a], Rb)):
            Ri = M[:3, :3].T
            struct.pack_into("<3f", d, tc_di["Pos" + suffix].vstart, *(Ri @ (o - M[:3, 3])))
            struct.pack_into("<3f", d, tc_di["PriAxis" + suffix].vstart, *(Ri @ (R @ u)))
            struct.pack_into("<3f", d, tc_di["SecAxis" + suffix].vstart, *(Ri @ (R @ y)))
        for f in ("AngularSwing1Motion", "AngularSwing2Motion", "AngularTwistMotion"):
            d[tc_di[f].vstart:tc_di[f].vstart + 8] = nm("ACM_" + c.get("motion", "Limited"))
        struct.pack_into("<f", d, tc_di["Swing1LimitAngle"].vstart, cone)
        struct.pack_into("<f", d, tc_di["Swing2LimitAngle"].vstart, cone)
        struct.pack_into("<f", d, tc_di["TwistLimitAngle"].vstart, c["twist"])
        struct.pack_into("<f", d, tc_di["AngularDriveSpring"].vstart, spring)
        struct.pack_into("<f", d, tc_di["AngularDriveDamping"].vstart, damping)
        d = bytes(d)
        force = (struct.pack("<ii", pkg.name_index("AngularDriveForceLimit"), 0) + struct.pack("<ii", pkg.name_index("FloatProperty"), 0)
                 + struct.pack("<iif", 4, 0, 1e10))
        d = insert_in_struct(d, props_of(pkg, d)["DefaultInstance"],
                             bool_tag(pkg, "bSwingLimitSoft", False) + bool_tag(pkg, "bTwistLimitSoft", False)
                             + bool_tag(pkg, "bEnableSwingDrive", True) + bool_tag(pkg, "bEnableTwistDrive", True) + force)
        new_cons.append(pkg.add_export(tc - 1, (pkg.name_index("PhysicsConstraintTemplate"), 5001 + len(new_cons)), pa + 1))
        datas.append(d)
        report.append({"bone": bn, "parent": names[a], "len": round(ln, 2), "radius": round(cap[2], 2), "mass": c["mass"],
                       "cone": cone, "mode": mode, "inertia": round(inertia[i], 1), "spring": round(spring), "damping": round(damping)})
    # collision disable table: everything new is disabled except listed, clear chain-vs-old pairs
    allc = [cap for _, cap in old] + [cap for _, cap in new_caps]
    n_old = len(old)
    old_index = {bn.lower(): k for k, (bn, _) in enumerate(old)}
    pairs, enabled, blocked = set(), [], []
    for j in range(n_old, len(allc)):
        bn = new_caps[j - n_old][0]
        allow = {old_index[b.lower()] for b in cfg_for(cfg, bn)["collide"] if b.lower() in old_index}
        for k in range(len(allc)):
            if k == j or allc[k] is None:
                continue
            if k in allow:
                gap = seg_dist(allc[j][0], allc[j][1], allc[k][0], allc[k][1]) - allc[j][2] - allc[k][2]
                if gap >= cfg.get("margin", 0.3):
                    enabled.append((bn, old[k][0], round(gap, 1)))
                    continue
                blocked.append((bn, old[k][0], round(gap, 1)))
            pairs.add((min(j, k), max(j, k)))
    # PhysicsAsset export: arrays + native CollisionDisableTable
    d = datas[pa]
    def set_array(d, p, vals):
        val = struct.pack("<i", len(vals)) + struct.pack("<%di" % len(vals), *vals)
        tag = bytearray(d[p.start:p.vstart]); struct.pack_into("<i", tag, 16, len(val))
        return d[:p.start] + bytes(tag) + val + d[p.vend:]
    # later fields first so earlier offsets stay valid
    P2 = props_of(pkg, d)
    d = set_array(d, P2["ConstraintSetup"], cons_exports + new_cons)
    d = set_array(d, P2["BodySetup"], body_exports + new_bodies)
    end = upkg.parse_props(pkg, d).end
    n = struct.unpack_from("<i", d, end + 4)[0]
    table = {struct.unpack_from("<ii", d, end + 8 + 12 * q): d[end + 16 + 12 * q:end + 20 + 12 * q] for q in range(n)}
    for pr in sorted(pairs):
        table.setdefault(pr, b"\0\0\0\0")
    rest = d[end + 8 + 12 * n:]
    d = d[:end + 4] + struct.pack("<i", len(table)) + b"".join(struct.pack("<ii", *k) + v for k, v in table.items()) + rest
    datas[pa] = d
    out = pkg.write(datas)
    open(out_path, "wb").write(out)
    return {"bodies_old": n_old, "bodies_new": len(new_bodies), "constraints_new": len(new_cons),
            "refitted": sorted(refitted), "disabled_pairs": len(table), "enabled_pairs": enabled, "blocked_pairs": blocked,
            "size": len(out), "chain": report}

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mesh"); ap.add_argument("physics_asset"); ap.add_argument("out")
    ap.add_argument("config", nargs="?", help="chain config JSON (default: DEFAULT)")
    args = ap.parse_args()
    cfg = json.load(open(args.config)) if args.config else DEFAULT
    r = build(args.mesh, args.physics_asset, args.out, cfg)
    print(json.dumps({k: v for k, v in r.items() if k not in ("chain", "enabled_pairs", "blocked_pairs")}, indent=1))
    print("enabled", len(r["enabled_pairs"]), r["enabled_pairs"])
    print("blocked (overlap in ref pose)", r["blocked_pairs"])
    for c in r["chain"]:
        print(c)
