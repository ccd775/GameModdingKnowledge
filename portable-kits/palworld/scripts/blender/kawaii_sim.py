# Offline KawaiiPhysics 1.17.1 test bench: drives a run's build.blend with a game animation (rotation-only retarget,
# like the game's "Skeleton" translation mode) while the component moves forward, simulates the chosen physics groups
# with the same per-frame algorithm as FAnimNode_KawaiiPhysics, and measures how deep skirt vertices sink into the
# thighs. Use it to tune physics_tune.json without a cook/game round trip.
#   blender --background <run>/build.blend --python kawaii_sim.py -- <run_dir> <anim.ueanim> <tag> [key=value ...]
# keys: speed=cm/s (700)  tune=<physics_tune.json> (scripts/physics_tune.json)  groups=skirt,tail  loops=3
#       render=0|1  fps=60  set.<group>.<key>=<value> (override a tune value, e.g. set.skirt.limit_angle=60)
import bpy, sys, os, math, json
sys.path.insert(0, os.path.dirname(__file__))
from palcommon import *
from mathutils import Matrix, Vector, Quaternion
from mathutils.bvhtree import BVHTree

argv = sys.argv[sys.argv.index("--") + 1:]
RUN, ANIM, TAG = os.path.abspath(argv[0]), argv[1], argv[2]
OPT = dict(a.split("=", 1) for a in argv[3:])
SPEED = float(OPT.get("speed", 700)); FPS = float(OPT.get("fps", 60)); LOOPS = int(OPT.get("loops", 3))
TUNE_PATH = OPT.get("tune", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "physics_tune.json"))  # kit: scripts/
GROUPS = OPT.get("groups", "skirt").split(",")
OUT = os.path.join(RUN, "sim"); os.makedirs(OUT, exist_ok=True)

PHYS = json.load(open(os.path.join(RUN, "physics.json"), encoding="utf-8"))
TUNE = json.load(open(TUNE_PATH, encoding="utf-8"))["groups"]
for k, v in OPT.items():
    if k.startswith("set."):
        _, g, key = k.split(".", 2)
        TUNE.setdefault(g, {})[key] = json.loads(v)

def merged(group):
    """physics.json group (geometry) + physics_tune.json dynamics; same merge as ue_build_abp.py."""
    g = json.loads(json.dumps(group))
    t = TUNE[g["name"]]
    for k in ("damping", "stiffness", "world_loc", "world_rot", "radius", "limit_angle"):
        if k in t: g["settings"][k] = t[k]
    for k in ("gravity", "stiffness_curve", "damping_curve", "limit_angle_curve", "dummy",
              "ring_levels", "compliance", "constraint_iterations"):
        if k in t: g[k] = t[k]
    if "capsules" in t:   # explicit capsule list (UE bind-pose component space) replaces the derived one
        g["capsules"] = json.loads(json.dumps(t["capsules"]))
    for c in g.get("capsules", []):
        c["radius"] = t.get("capsule_radius", {}).get(c["bone"], c["radius"])
    g["capsules"] = g.get("capsules", []) + t.get("extra_capsules", [])
    return g

# ---------------------------------------------------------------- animation (same retarget as probe_run_pose.py)
enable_ueformat()
from io_scene_ueformat.importer.import_context import UEFormatImport
from io_scene_ueformat.options import UEAnimOptions
K = bpy.data.objects["Armature"]
objs = import_uemodel(os.path.join(CACHE_UE, r"Outfit\SK_Player_Female_Outfit_OldCloth001\SK_Player_Female_Outfit_OldCloth001.uemodel"))
V = next(o for o in objs if o.type == "ARMATURE")
for o in objs:
    if o.type == "MESH":
        o.hide_render = True
action, dto = UEFormatImport(UEAnimOptions(rotation_only=True, override_skeleton=V, scale_factor=1.0)).import_file_with_dto(ANIM)
NF, AFPS = dto.metadata.num_frames, dto.metadata.frames_per_second
def rot(m):
    return m.to_quaternion().to_matrix().to_4x4()
KR = {b.name: K.matrix_world @ b.matrix_local for b in K.data.bones}
VR = {b.name: V.matrix_world @ b.matrix_local for b in V.data.bones}
C = {n: rot(VR[n]).inverted() @ rot(KR[n]) for n in KR if n in VR}

def anim_pose(t):
    """Component-space (armature) matrices of every K bone at time t, K bone frames."""
    if OPT.get("bind") == "1":
        return dict(KR)
    f = (t * AFPS) % (NF - 1)
    bpy.context.scene.frame_set(int(f), subframe=f - int(f))
    VP = {b.name: V.matrix_world @ b.matrix for b in V.pose.bones}
    Q = {}
    for b in K.data.bones:
        n = b.name; p = b.parent.name if b.parent else None
        if n in C:
            Lr = rot(VP[n]) if not p else rot(VP[p]).inverted() @ rot(VP[n])
            if p:
                Mp = KR[p] @ (C[p].inverted() if p in C else Matrix())
                t_ = (Mp.inverted() @ (KR[n] @ C[n].inverted())).translation
                P = Q[p] @ (C[p].inverted() if p in C else Matrix()) @ Matrix.Translation(t_) @ Lr
            else:
                P = Matrix.Translation(KR[n].translation) @ Lr
            Q[n] = P @ C[n]
        else:
            Q[n] = (Q[p] @ (KR[p].inverted() @ KR[n])) if p else KR[n]
    return Q

def apply_pose(Q):
    for b in K.data.bones:
        n = b.name; p = b.parent.name if b.parent else None
        rest_rel = (KR[p].inverted() @ KR[n]) if p else KR[n]
        cur_rel = (Q[p].inverted() @ Q[n]) if p else Q[n]
        pb = K.pose.bones[n]; pb.rotation_mode = "QUATERNION"
        pb.matrix_basis = rest_rel.inverted() @ cur_rel
    bpy.context.view_layer.update()

# ---------------------------------------------------------------- Kawaii node model
def curve(keys, x):
    if not keys: return 1.0
    if x <= keys[0][0]: return keys[0][1]
    for (x0, y0), (x1, y1) in zip(keys, keys[1:]):
        if x <= x1: return y0 + (y1 - y0) * (x - x0) / max(x1 - x0, 1e-9)
    return keys[-1][1]

class Node:
    def __init__(self, g):
        self.g = g; s = g["settings"]
        self.grav = Vector(g.get("gravity", [0, 0, 0]))
        self.bones = []   # dicts: name, parent (index), children
        for r in g["roots"]:
            base = len(self.bones)
            def add(name, parent):
                i = len(self.bones)
                self.bones.append({"name": name, "parent": parent, "children": []})
                if parent is not None: self.bones[parent]["children"].append(i)
                for c in K.data.bones[name].children:
                    add(c.name, i)
            add(r, None)
            chain = self.bones[base:]
            for b in chain:   # LengthFromRoot over the mesh ref pose
                b["len"] = 0.0 if b["parent"] is None else self.bones[b["parent"]]["len"] + (KR[self.bones[b["parent"]]["name"]].inverted() @ KR[b["name"]]).translation.length
            total = max(b["len"] for b in chain) or 1.0
            for b in chain:
                rate = b["len"] / total
                b["damping"] = min(max(s["damping"] * curve(g.get("damping_curve"), rate), 0), 1)
                b["stiffness"] = min(max(s["stiffness"] * curve(g.get("stiffness_curve"), rate), 0), 1)
                b["wl"], b["wr"] = s["world_loc"], s["world_rot"]
                b["radius"] = s["radius"]
                b["limit"] = s["limit_angle"] * curve(g.get("limit_angle_curve"), rate)
        # capsules: bind-pose endpoints (UE -> Blender: negate Y), carried by the driving bone
        self.caps = [(c["bone"], Vector((c["a"][0], -c["a"][1], c["a"][2])), Vector((c["b"][0], -c["b"][1], c["b"][2])), c["radius"])
                     for c in g.get("capsules", [])]
        # ring constraints (cloth-like): joints at the same depth of neighbouring chains, ordered around the pelvis
        self.cons = []; pairs = []
        if g.get("ring_levels"):
            idx = {b["name"]: i for i, b in enumerate(self.bones)}
            roots = [i for i, b in enumerate(self.bones) if b["parent"] is None]
            cen = KR["pelvis"].translation
            for lv in g["ring_levels"]:
                ring = []
                for r in roots:
                    i = r
                    for _ in range(lv):
                        i = self.bones[i]["children"][0] if self.bones[i]["children"] else None
                        if i is None: break
                    if i is not None: ring.append(i)
                ring.sort(key=lambda i: math.atan2(KR[self.bones[i]["name"]].translation.y - cen.y, KR[self.bones[i]["name"]].translation.x - cen.x))
                for a_, b_ in zip(ring, ring[1:] + ring[:1]):
                    pairs.append([self.bones[a_]["name"], self.bones[b_]["name"]]); self.cons.append([a_, b_, None, 0.0])
        g["bone_constraints"] = pairs
        self.compliance = [0.00000000004, 0.00000000016, 0.000000001, 0.000000002, 0.0000001, 0.00002, 0.0001][
            ["Concrete", "Wood", "Leather", "Tendon", "Rubber", "Muscle", "Fat"].index(g.get("compliance", "Leather"))]
        self.iters = int(g.get("constraint_iterations", 1))
        self.init = False

    def step(self, Q, dt, move):
        for b in self.bones:
            b["pl"] = Q[b["name"]].translation.copy(); b["pr"] = Q[b["name"]].to_quaternion()
        if not self.init:
            for b in self.bones:
                b["loc"] = b["pl"].copy(); b["prev"] = b["pl"].copy()
            for c in self.cons:
                c[2] = (self.bones[c[0]]["loc"] - self.bones[c[1]]["loc"]).length
            self.init = True; self.dt_old = dt
        caps = []
        for bone, a, bb, r in self.caps:
            M = Q[bone] @ KR[bone].inverted()
            caps.append((M @ a, M @ bb, r))
        for b in self.bones:
            if b["parent"] is None:
                b["prev"] = b["loc"]; b["loc"] = b["pl"].copy(); continue
            p = self.bones[b["parent"]]
            vel = (b["loc"] - b["prev"]) / self.dt_old
            b["prev"] = b["loc"].copy()
            vel *= (1.0 - b["damping"])
            loc = b["loc"] + vel * dt
            loc += move * (1.0 - b["wl"])
            loc += 0.5 * self.grav * dt * dt
            base = p["loc"] + (b["pl"] - p["pl"])
            loc += (base - loc) * (1.0 - (1.0 - b["stiffness"]) ** (FPS * dt))
            b["loc"] = loc
        for b in self.bones:
            if b["parent"] is None: continue
            for a, bb, r in caps:
                d = bb - a; t = max(0.0, min(1.0, (b["loc"] - a).dot(d) / d.dot(d)))
                cp = a + d * t; lim = b["radius"] + r
                if (b["loc"] - cp).length < lim:
                    b["loc"] = cp + (b["loc"] - cp).normalized() * lim
        if self.cons and self.iters > 0:   # XPBD, after collision (1.17.1 order)
            for c in self.cons: c[3] = 0.0
            alpha = self.compliance / (dt * dt)
            for _ in range(self.iters):
                for c in self.cons:
                    b1, b2 = self.bones[c[0]], self.bones[c[1]]
                    d = b2["loc"] - b1["loc"]; dl = d.length
                    if dl <= 0: continue
                    dlam = ((dl - c[2]) - alpha * c[3]) / (2 + alpha)
                    d = d / dl * dlam
                    b1["loc"] = b1["loc"] + d; b2["loc"] = b2["loc"] - d; c[3] += dlam
        for b in self.bones:
            if b["parent"] is None: continue
            p = self.bones[b["parent"]]
            if b["limit"] != 0:
                bd = (b["loc"] - p["loc"]).normalized(); pd = (b["pl"] - p["pl"]).normalized()
                ax = pd.cross(bd); ang = math.degrees(math.atan2(ax.length, pd.dot(bd)))
                over = ang - b["limit"]
                if over > 0:
                    bd = Quaternion(ax.normalized(), -math.radians(over)) @ bd
                    b["loc"] = bd * (b["loc"] - p["loc"]).length + p["loc"]
            L = (b["pl"] - p["pl"]).length
            b["loc"] = (b["loc"] - p["loc"]).normalized() * L + p["loc"]
        self.dt_old = dt

    def write(self, Q):
        out = {b["name"]: (b["pr"].copy(), b["pl"].copy()) for b in self.bones}
        for b in self.bones:
            if b["parent"] is None: continue
            p = self.bones[b["parent"]]
            if len(p["children"]) <= 1:
                pv = b["pl"] - p["pl"]; sv = b["loc"] - p["loc"]
                q = pv.rotation_difference(sv) @ p["pr"]
                out[p["name"]] = (q, out[p["name"]][1])
            out[b["name"]] = (out[b["name"]][0], b["loc"].copy())
        for n, (q, l) in out.items():
            Q[n] = Matrix.Translation(l) @ q.to_matrix().to_4x4()

    def flare(self):
        """max angle (deg) between simulated and pose direction, split by side (front = -Y in bind pose)"""
        m = {"front": 0.0, "back": 0.0}
        for b in self.bones:
            if b["parent"] is None: continue
            p = self.bones[b["parent"]]
            side = "front" if KR[b["name"]].translation.y < 0 else "back"
            m[side] = max(m[side], math.degrees((b["loc"] - p["loc"]).angle(b["pl"] - p["pl"], 0)))
        return m

all_nodes = [Node(merged(g)) for g in PHYS["groups"]]
nodes = [n for n in all_nodes if n.g["name"] in GROUPS]
for n in nodes:
    print("NODE", n.g["name"], n.g["settings"], "grav", list(n.grav), "caps", [(c[0], c[3]) for c in n.caps],
          "curve", n.g.get("stiffness_curve"), "constraints", len(n.cons))
if OPT.get("export"):   # resolved groups = exactly what was simulated; ue_build_abp.py builds the ABP from this
    json.dump({"tune": TUNE_PATH, "groups": [n.g for n in all_nodes]}, open(OPT["export"], "w", encoding="utf-8"), indent=1)
    print("EXPORTED", OPT["export"])

# ---------------------------------------------------------------- penetration metric
B = bpy.data.objects["SK_Karin_Body"]
gidx = {g.index: g.name for g in B.vertex_groups}
SKIRT_V, FLESH_V = [], set()
for v in B.data.vertices:
    ws = {gidx[g.group]: g.weight for g in v.groups}
    if sum(w for k, w in ws.items() if "skirt" in k.lower()) > 0.5:
        SKIRT_V.append(v.index)
    if ws.get("thigh_l", 0) + ws.get("thigh_r", 0) > 0.3:
        FLESH_V.add(v.index)
FLESH_P = [list(p.vertices) for p in B.data.polygons if all(i in FLESH_V for i in p.vertices)]
print("skirt verts", len(SKIRT_V), "flesh polys", len(FLESH_P))

DOM = {}
for v in B.data.vertices:
    if v.groups:
        g = max(v.groups, key=lambda g: g.weight); DOM[v.index] = (gidx[g.group], round(g.weight, 2))
def penetration(dump=False):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = B.evaluated_get(dg); me = ev.to_mesh()
    co = [B.matrix_world @ v.co for v in me.vertices]
    ev.to_mesh_clear()
    tree = BVHTree.FromPolygons(co, FLESH_P)
    n, depth, deep = 0, 0.0, 0
    for i in SKIRT_V:
        hit = tree.find_nearest(co[i], 6.0)
        if hit[0] is None: continue
        loc, nor, _, dist = hit
        if (co[i] - loc).dot(nor) < 0:
            n += 1; depth = max(depth, dist); deep += dist > 1.0
            if dump and dist > 1.0: print("  INSIDE", i, DOM[i], "z %.1f" % co[i].z, "depth %.2f" % dist)
    return n, depth, deep

# ---------------------------------------------------------------- run
dt = 1.0 / FPS
cycle = (NF - 1) / AFPS
steps = int(round(LOOPS * cycle / dt))
move = Vector((0, SPEED * dt, 0))   # previous component location seen from the current one (character runs toward -Y)
worst = (0, 0.0, -1); total_n = 0; total_deep = 0; samples = 0; flare_max = {"front": 0.0, "back": 0.0}
group_flare = {n.g["name"]: 0.0 for n in nodes}; group_mean = {n.g["name"]: 0.0 for n in nodes}
for s in range(steps):
    t = s * dt
    Q = anim_pose(t)
    for n in nodes: n.step(Q, dt, move)
    for n in nodes: n.write(Q)
    if OPT.get("dbg") and s % 15 == 0:
        for n in nodes:
            if n.g["name"] != OPT["dbg"]: continue
            for b in n.bones[:9]:
                if b["parent"] is None: print("DBG", s, b["name"], "root pl", tuple(round(x, 1) for x in b["pl"])); continue
                p = n.bones[b["parent"]]
                print("DBG", s, b["name"][-10:], "ang %.1f" % math.degrees((b["loc"] - p["loc"]).angle(b["pl"] - p["pl"], 0)),
                      "pl", tuple(round(x, 1) for x in b["pl"]), "loc", tuple(round(x, 1) for x in b["loc"]), "seg %.2f" % (b["pl"] - p["pl"]).length)
    if t >= (LOOPS - 1) * cycle:   # measure the last loop
        apply_pose(Q)
        pn, pd, pdeep = penetration() if OPT.get("nopen") != "1" else (0, 0.0, 0)
        total_n += pn; total_deep += pdeep; samples += 1
        for n in nodes:
            fl = n.flare()
            group_flare[n.g["name"]] = max(group_flare[n.g["name"]], fl["front"], fl["back"])
            group_mean[n.g["name"]] += max(fl["front"], fl["back"])
            if n.g["name"] == "skirt":
                for k, v in fl.items(): flare_max[k] = max(flare_max[k], v)
        if pd > worst[1] or (pd == worst[1] and pn > worst[0]): worst = (pn, pd, s)
print("RESULT %s speed %.0f: mean skirt verts inside thigh %.1f (>1cm %.1f), worst %d verts depth %.2f cm at step %d, max flare front %.1f back %.1f deg"
      % (TAG, SPEED, total_n / max(samples, 1), total_deep / max(samples, 1), worst[0], worst[1], worst[2], flare_max["front"], flare_max["back"]))

if OPT.get("render", "0") == "1":
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"; sc.display.shading.light = "STUDIO"; sc.display.shading.color_type = "TEXTURE"
    sc.render.resolution_x, sc.render.resolution_y = 600, 600
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); sc.collection.objects.link(cam); sc.camera = cam
    cam.data.type = "ORTHO"; cam.data.ortho_scale = 60
    # re-run to the worst step and render it (simulation is deterministic)
    for n in nodes: n.init = False
    for s in range(worst[2] + 1):
        Q = anim_pose(s * dt)
        for n in nodes: n.step(Q, dt, move)
        for n in nodes: n.write(Q)
    apply_pose(Q)
    penetration(dump=True)
    for n in nodes:
        caps = [(bone, (Q[bone] @ KR[bone].inverted()) @ a, (Q[bone] @ KR[bone].inverted()) @ bb, r) for bone, a, bb, r in n.caps]
        for b in n.bones:
            if any(k in b["name"] for k in OPT.get("dumpbones", "skirtA_0,skirtB_0").split(",")) and b["name"].endswith("_r"):
                ds = []
                for bone, a, bb, r in caps:
                    d = bb - a; t = max(0.0, min(1.0, (b["loc"] - a).dot(d) / d.dot(d)))
                    ds.append("%s %.2f(t%.2f)" % (bone, (b["loc"] - (a + d * t)).length, t))
                print("  JOINT %-34s loc %s pose %s  %s" % (b["name"], tuple(round(x, 1) for x in b["loc"]), tuple(round(x, 1) for x in b["pl"]), ds))
        for bone, a, bb, r in caps: print("  CAP", bone, tuple(round(x, 1) for x in a), tuple(round(x, 1) for x in bb), r)
    c = K.matrix_world @ K.pose.bones["pelvis"].head
    for name, off, r in [("front", (0, -150, -10), (90, 0, 0)), ("q_l", (106, -106, -10), (90, 0, 45)),
                         ("q_r", (-106, -106, -10), (90, 0, -45)), ("back", (0, 150, -10), (90, 0, 180))]:
        cam.location = c + Vector(off); cam.rotation_euler = [math.radians(x) for x in r]
        sc.render.filepath = os.path.join(OUT, f"{TAG}_{name}.png"); bpy.ops.render.render(write_still=True)
print("FLARE", TAG, "max", {k: round(v, 1) for k, v in group_flare.items()})
print("FLARE", TAG, "mean", {k: round(v / max(samples, 1), 1) for k, v in group_mean.items()})
print("SIM_OK")
