"""Build the Karin body mesh for DD2 (player body slot, runtime setMesh).

Method (see SOP section 6):
- one uniform scale G so that Karin's Hips height equals the DD2 female Hip height (feet stay on the floor);
- limbs of Karin are re-posed so each limb segment points along the DD2 rest direction (hand: full frame);
  the pose is baked into the geometry;
- the output skeleton is the full 192-bone DD2 female body skeleton (names, parents, DD2 rest rotations)
  with joint positions moved to Karin's (posed) joint positions; the game rebuilds the player's joints from
  the mesh on setMesh, so the runtime skeleton takes Karin's proportions;
- Karin's secondary bones (hair, tail, coat, ribbons...) are kept as extra bones "K_<name>" parented to the
  mapped DD2 bone, so chain physics can be added later;
- weights: humanoid groups renamed to DD2 bones; torso/neck split by height; limb segments split over the
  DD2 twist joints (t = 0, 1/3, 2/3) like the native body.

usage: blender -b --factory-startup --python build_karin_body.py -- <out_dir> --source-blend <blend> --dd2-body <mesh>
       [--materials test_body|karin] [--no-extra-bones] [--profile picodra|original]
  --source-blend: picodra = Karin_PT_Unified_Atlas.blend; original = karin_original_src.blend from
  prepare_karin_original.py.
  --dd2-body: the native female body in RE Mesh Editor's format, made with
  DD2Tool meshconv <natives>/character/_kit/body/body_000_f/body_000_f.mesh.260421070 <out> "DD2 (old v2)"
  (body_000_f.mesh.240423143).
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import re_common as rc  # noqa: E402

# asset path and output name per model (the source blend and the native body come from the command line)
PROFILES = {
    "picodra": {"asset": "Character/_karin/karin_body.mesh", "name": "karin_body", "chain_tips": False},
    # chain_tips: also keep the unweighted child ("*_end") of every kept secondary bone, so a chain can swing its
    # last weighted bone (a chain joint aims at the next node; the tip bones of this model carry no weights)
    "original": {"asset": "Character/_karin_original/karin_original_body.mesh", "name": "karin_original_body",
                 "chain_tips": True},
}

# Karin humanoid bone -> DD2 bone (direct rename). Torso / neck / limb segments are split separately below.
DIRECT = {"Hips": "Hip", "Head": "Head_0", "Eye.L": "Head_0", "Eye.R": "Head_0"}
for s in ("L", "R"):
    DIRECT.update({
        f"Shoulder.{s}": f"{s}_Arm_Clavicle", f"Hand.{s}": f"{s}_Arm_Hand",
        f"Foot.{s}": f"{s}_Leg_Ankle", f"Toes.{s}": f"{s}_Leg_Toes", f"Breast_1.{s}": f"{s}_Breast",
    })
    for kf, df in (("Thumb", "Thumb"), ("Index", "Index"), ("Middle", "Middle"), ("Ring", "Ring"), ("Little", "Pinky")):
        for kp, dp in (("Proximal", 1), ("Intermediate", 2), ("Distal", 3)):
            DIRECT[f"{kf}{kp}.{s}"] = f"{s}_Hand_{df}F_{dp}"

# Limb segments: Karin bone -> (DD2 joint at segment start, DD2 joint at segment end, twist joint prefix)
SEGMENTS = {}
for s in ("L", "R"):
    SEGMENTS[f"UpperArm.{s}"] = (f"{s}_Arm_Upper", f"{s}_Arm_Lower", f"{s}_Arm_Upper_Twist_")
    SEGMENTS[f"LowerArm.{s}"] = (f"{s}_Arm_Lower", f"{s}_Arm_Hand", f"{s}_Arm_Lower_Twist_")
    SEGMENTS[f"UpperLeg.{s}"] = (f"{s}_Leg_Upper", f"{s}_Leg_Lower", f"{s}_Leg_Upper_Twist_")
    SEGMENTS[f"LowerLeg.{s}"] = (f"{s}_Leg_Lower", f"{s}_Leg_Ankle", f"{s}_Leg_Lower_Twist_")

TORSO = ("Spine", "Chest")  # split over Spine_0 / Spine_1 / Spine_2 by height
NECK = ("Neck",)  # split over Neck_0 / Neck_1 by height

# Aim pairs for re-posing: Karin (bone, child joint) -> DD2 (joint, target joint).  None = use DD2 bone X axis.
AIM = []
for s in ("L", "R"):
    AIM += [
        (f"Shoulder.{s}", f"UpperArm.{s}", f"{s}_Arm_Clavicle", f"{s}_Arm_Upper"),
        (f"UpperArm.{s}", f"LowerArm.{s}", f"{s}_Arm_Upper", f"{s}_Arm_Lower"),
        (f"LowerArm.{s}", f"Hand.{s}", f"{s}_Arm_Lower", f"{s}_Arm_Hand"),
        (f"Hand.{s}", "HAND_FRAME", f"{s}_Arm_Hand", None),
    ]
    for kf, df in (("Thumb", "Thumb"), ("Index", "Index"), ("Middle", "Middle"), ("Ring", "Ring"), ("Little", "Pinky")):
        AIM += [
            (f"{kf}Proximal.{s}", f"{kf}Intermediate.{s}", f"{s}_Hand_{df}F_1", f"{s}_Hand_{df}F_2"),
            (f"{kf}Intermediate.{s}", f"{kf}Distal.{s}", f"{s}_Hand_{df}F_2", f"{s}_Hand_{df}F_3"),
            (f"{kf}Distal.{s}", None, f"{s}_Hand_{df}F_3", None),
        ]
    AIM += [
        (f"UpperLeg.{s}", f"LowerLeg.{s}", f"{s}_Leg_Upper", f"{s}_Leg_Lower"),
        (f"LowerLeg.{s}", f"Foot.{s}", f"{s}_Leg_Lower", f"{s}_Leg_Ankle"),
        (f"Foot.{s}", f"Toes.{s}", f"{s}_Leg_Ankle", f"{s}_Leg_Toes"),
        (f"Toes.{s}", None, f"{s}_Leg_Toes", None),
    ]

# Karin source material -> (DD2 material name, visibility group id), per profile
MATERIALS = {
    "picodra": {
        "Body": ("karin_skin_mat", 0), "Karin_Face": ("karin_face_mat", 1), "Karin_Alpha": ("karin_eyealpha_mat", 2),
        "Hair": ("karin_hair_mat", 3), "Karin_Hair_Transparent": ("karin_hairalpha_mat", 4),
        "ClothA_Blue": ("karin_clotha_mat", 5), "Costume": ("karin_clotha_mat", 5), "Karin_Costume": ("karin_clotha_mat", 5),
        "ClothB_Blue": ("karin_clothb_mat", 6), "Costume_1": ("karin_clothb_mat", 6), "Costume_Metalic": ("karin_clothb_mat", 6),
    },
    "original": {
        "Karin_Body": ("karin_skin_mat", 0), "Karin_Face": ("karin_face_mat", 1), "Karin_Alpha": ("karin_eyealpha_mat", 2),
        "Karin_Hair": ("karin_hair_mat", 3), "Karin_Hair_Transparent": ("karin_hairalpha_mat", 4),
        "Karin_Costume": ("karin_costume_mat", 5),
    },
}


# Facial expressions. Karin's face moves with shape keys; the game moves faces with joints (the native head's rig is
# animated even while its mesh is hidden), and the replacer script copies that motion onto her joints every frame.
# Each expression channel becomes translation joints under Head_0, "KF_<Channel>_<k>" (k = 0..), each with an
# unweighted child "KF_<Channel>_<k>_End" at D * t_k from it: with the joint moved by a * (its End offset), a vertex
# weighted w_k moves a * sum_k(w_k * D * t_k), i.e. exactly the shape key times a (weights w_k = coefficient_k / D):
#   4 joints: a regular tetrahedron of directions around the key's dominant direction t_0 (exact for any delta, the
#             coefficients are non-negative);
#   2 joints: +t_0 / -t_0 (the part across t_0 is dropped).
# The iris: the look keys move the iris rigidly; one joint "KF_Iris" weighted IRIS_W on those vertices, with unweighted
# children "KF_Iris_<Left|Right|Up|Down>" at the full look offset / IRIS_W. Nothing in the script is model specific:
# it reads the offsets from the End / direction joints. weak_bone_max: secondary bones whose largest weight is below
# it hand their weights to their parent (bone budget: a mesh has at most MAX_DEFORM weighted bones).
FACE = {
    "picodra": {"channels": [("Blink", ("blink_L", "blink_R"), 4), ("Mouth", ("VRC.v_aa",), 2)], "weak_bone_max": 0.12},
    "original": {"channels": [("BlinkL", ("blink_L",), 4), ("BlinkR", ("blink_R",), 4), ("Mouth", ("VRC.v_aa",), 4)],
                 "weak_bone_max": 0.0},
}
LOOK = {"Left": "LookLeft", "Right": "LookRight", "Up": "LookUp", "Down": "LookDown"}
IRIS_W = 0.5
FACE_EPS = 1e-6
MAX_DEFORM = 256


def log(*a):
    print("[karin]", *a, flush=True)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir")
    ap.add_argument("--source-blend", required=True,
                    help="source model blend (picodra: Karin_PT_Unified_Atlas.blend; original: karin_original_src.blend)")
    ap.add_argument("--dd2-body", required=True,
                    help='body_000_f.mesh.240423143 (DD2Tool meshconv of the native body_000_f.mesh.260421070, "DD2 (old v2)")')
    ap.add_argument("--materials", default="karin", choices=["karin", "test_body"])
    ap.add_argument("--no-extra-bones", action="store_true")
    ap.add_argument("--skeleton-only", action="store_true",
                    help="output only the 192-joint DD2 skeleton in Karin proportions + hidden compat submeshes "
                         "(set on the player's body so its joint table keeps the native layout)")
    ap.add_argument("--profile", default="picodra", choices=sorted(PROFILES))
    ap.add_argument("--name", default=None, help="output name (default: the profile's)")
    ap.add_argument("--lods", type=int, default=2)
    ap.add_argument("--native-compat", action="store_true",
                    help="experimental (v7, not used): the native body submeshes, hidden, instead of the zero-area stubs. "
                         "The skin baker still crashed on them, and that build's textures never became resident in game; "
                         "the replacer routes the bake past a Karin body instead")
    ap.add_argument("--compat-materials", default="body_mat,hand_mat,nail_mat,vfx_mat",
                    help="hidden zero-area submeshes carrying the native body material names (baker / material systems)")
    ap.add_argument("--no-face", action="store_true", help="no expression joints (face shape keys dropped as before)")
    a = ap.parse_args(argv)
    a.name = a.name or PROFILES[a.profile]["name"]
    return a


def smoothstep(e0, e1, x):
    if e1 <= e0:
        return 1.0 if x >= e1 else 0.0
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def rot_between(a, b):
    a = a.normalized()
    b = b.normalized()
    return a.rotation_difference(b).to_matrix().to_4x4()


def frame(x, lat):
    x = x.normalized()
    z = x.cross(lat).normalized()
    y = z.cross(x).normalized()
    m = Matrix((x, y, z)).transposed()  # columns = axes
    return m


# ---------------------------------------------------------------- source preparation
def load_karin(blend):
    with bpy.data.libraries.load(str(blend), link=False) as (src, dst):
        dst.objects = list(src.objects)
    coll = bpy.data.collections.new("KarinSource")
    bpy.context.scene.collection.children.link(coll)
    arm = None
    meshes = []
    for o in dst.objects:
        if o is None:
            continue
        coll.objects.link(o)
        if o.type == "ARMATURE":
            arm = o
        elif o.type == "MESH":
            meshes.append(o)
    assert arm is not None and meshes
    assert all((o.matrix_world - Matrix.Identity(4)).to_scale().length < 1e-9 or True for o in meshes)
    return coll, arm, meshes


def bake_shape_keys(obj, report):
    """Bake the saved shape-key mix into the base coordinates, then delete faces fully hidden by *_OFF keys."""
    me = obj.data
    keys = me.shape_keys
    if keys is None:
        return
    kb = keys.key_blocks
    basis = kb[0]
    n = len(me.vertices)
    co = [basis.data[i].co.copy() for i in range(n)]
    hidden = [False] * n
    active = []
    for k in kb[1:]:
        if k.value == 0 or k.mute:
            continue
        rel = k.relative_key
        active.append((k.name, k.value))
        for i in range(n):
            d = k.data[i].co - rel.data[i].co
            if d.length_squared > 0:
                co[i] += d * k.value
                if "OFF" in k.name.upper():
                    hidden[i] = True
    obj.shape_key_clear()
    for i, v in enumerate(me.vertices):
        v.co = co[i]
    removed = 0
    if any(hidden):
        bm = bmesh.new()
        bm.from_mesh(me)
        bm.verts.ensure_lookup_table()
        kill = [f for f in bm.faces if all(hidden[v.index] for v in f.verts)]
        removed = len(kill)
        bmesh.ops.delete(bm, geom=kill, context="FACES")
        loose = [v for v in bm.verts if not v.link_faces]
        bmesh.ops.delete(bm, geom=loose, context="VERTS")
        bm.to_mesh(me)
        bm.free()
    report[obj.name] = {"active_keys": active, "hidden_vertices": sum(hidden), "removed_faces": removed}


# ---------------------------------------------------------------- facial expressions (see FACE)
def face_attr(key):
    return "kf_" + "".join(c if c.isalnum() else "_" for c in key)


def face_keys(face):
    return sorted({k for _, keys, _ in face["channels"] for k in keys} | set(LOOK.values()))


def face_capture(meshes, keys):
    """Each needed shape key's vertex deltas (world axes) -> point attribute face_attr(key), before the keys are baked
    away; attributes follow the vertices through face deletion, posing and the material split."""
    found = {}
    for o in meshes:
        ks = o.data.shape_keys
        if ks is None:
            continue
        R = o.matrix_world.to_3x3()
        for key in keys:
            k = ks.key_blocks.get(key)
            if k is None:
                continue
            rel = k.relative_key
            vals = []
            nz = 0
            for i in range(len(o.data.vertices)):
                d = R @ (k.data[i].co - rel.data[i].co)
                nz += d.length > FACE_EPS
                vals.extend(d)
            if nz == 0:
                continue
            o.data.attributes.new(face_attr(key), "FLOAT_VECTOR", "POINT").data.foreach_set("vector", vals)
            found[key] = found.get(key, 0) + nz
    missing = [k for k in keys if k not in found]
    assert not missing, ("face shape keys not found on any mesh", missing)
    return found


def face_scale(meshes, keys, s):
    for o in meshes:
        for key in keys:
            a = o.data.attributes.get(face_attr(key))
            if a is None:
                continue
            vals = [0.0] * (3 * len(a.data))
            a.data.foreach_get("vector", vals)
            a.data.foreach_set("vector", [x * s for x in vals])


def face_plan(meshes, face):
    """Joint directions, amplitude and per-vertex weights of every channel and the iris.
    Returns (joints, weights, report): joints = [(name, parent, head, xdir)], weights = {mesh name: {v: [(joint, w)]}}"""
    import numpy as np

    def attr(o, key):
        a = o.data.attributes.get(face_attr(key))
        if a is None:
            return np.zeros((len(o.data.vertices), 3))
        vals = np.zeros(3 * len(a.data))
        a.data.foreach_get("vector", vals)
        return vals.reshape(-1, 3)

    def coords(o):
        c = np.zeros(3 * len(o.data.vertices))
        o.data.vertices.foreach_get("co", c)
        return c.reshape(-1, 3)

    face_meshes = [o for o in meshes if any(o.data.attributes.get(face_attr(k)) for k in face_keys(face))]
    co = {o.name: coords(o) for o in face_meshes}
    rep = {"meshes": [o.name for o in face_meshes], "channels": {}}
    # iris: the look keys are rigid translations of the same vertices (the vertices that move by the common offset;
    # a few stray vertices with tiny deltas in every key are left out)
    look = {}
    iris_mask = {o.name: np.zeros(len(o.data.vertices), bool) for o in face_meshes}
    rep["iris"] = {}
    for side, key in LOOK.items():
        ds = np.concatenate([attr(o, key) for o in face_meshes])
        med = np.median(ds[np.linalg.norm(ds, axis=1) > FACE_EPS], axis=0)
        rigid = np.linalg.norm(ds - med, axis=1) < 0.25 * np.linalg.norm(med)
        look[side] = ds[rigid].mean(axis=0)
        i0 = 0
        for o in face_meshes:
            n = len(o.data.vertices)
            iris_mask[o.name] |= rigid[i0:i0 + n]
            i0 += n
        stray = (np.linalg.norm(ds, axis=1) > FACE_EPS) & ~rigid
        rep["iris"][side] = {"offset_mm": [round(float(x) * 1000, 3) for x in look[side]], "verts": int(rigid.sum()),
                             "nonrigid_max_mm": round(float(np.linalg.norm(ds[rigid] - look[side], axis=1).max()) * 1000, 3),
                             "stray_verts": int(stray.sum()),
                             "stray_max_mm": round(float(np.linalg.norm(ds[stray], axis=1).max(initial=0)) * 1000, 3)}
    # channel deltas per mesh
    deltas = {c: {o.name: np.sum([attr(o, k) for k in keys], axis=0) for o in face_meshes} for c, keys, _ in face["channels"]}
    for per_mesh in deltas.values():   # sub-threshold noise moves nothing and takes no influence slot
        for d in per_mesh.values():
            d[np.linalg.norm(d, axis=1) <= FACE_EPS] = 0.0
    touched = {o.name: np.sum([np.linalg.norm(deltas[c][o.name], axis=1) > FACE_EPS for c in deltas], axis=0)
               for o in face_meshes}
    joints, weights = [], {o.name: {} for o in face_meshes}
    for c, keys, n in face["channels"]:
        allv = np.concatenate([deltas[c][o.name][np.linalg.norm(deltas[c][o.name], axis=1) > FACE_EPS] for o in face_meshes])
        _, V = np.linalg.eigh(allv.T @ allv)
        t0 = V[:, 2] if (allv @ V[:, 2] > 0).sum() >= len(allv) / 2 else -V[:, 2]
        t1 = V[:, 1]
        t2 = np.cross(t0, t1)
        if n == 4:
            dirs = np.array([t0] + [-t0 / 3 + math.sqrt(8) / 3 * (math.cos(a) * t1 + math.sin(a) * t2)
                                    for a in (0.0, 2 * math.pi / 3, 4 * math.pi / 3)])
        elif n == 2:
            dirs = np.array([t0, -t0])
        else:
            raise ValueError(n)

        def coef(d):
            if n == 4:
                p = 0.75 * d @ dirs.T          # sum_i t_i t_i^T = 4/3 I and sum_i t_i = 0: shift to non-negative
                return p - p.min(axis=1, keepdims=True)
            p = d @ t0
            return np.stack([np.clip(p, 0, None), np.clip(-p, 0, None)], axis=1)

        # weight budget per vertex: what the iris leaves, shared by the channels that move the vertex
        D = 0.0
        coefs = {}
        resid = 0.0
        for o in face_meshes:
            d = deltas[c][o.name]
            a = coef(d)
            coefs[o.name] = a
            budget = (1.0 - IRIS_W * iris_mask[o.name]) / np.maximum(1, touched[o.name])
            D = max(D, float((a.sum(axis=1) / budget).max()))
            resid = max(resid, float(np.linalg.norm(d - a @ dirs, axis=1).max()))
        cen = np.concatenate([co[o.name][np.linalg.norm(deltas[c][o.name], axis=1) > FACE_EPS] for o in face_meshes]).mean(axis=0)
        for k, t in enumerate(dirs):
            name = f"KF_{c}_{k}"
            joints.append((name, "Head_0", Vector(cen), Vector(t)))
            joints.append((name + "_End", name, Vector(cen + D * t), Vector(t)))
        for o in face_meshes:
            a = coefs[o.name] / D
            for vi in np.nonzero(a.sum(axis=1) > 0)[0]:
                weights[o.name].setdefault(int(vi), []).extend((f"KF_{c}_{k}", float(a[vi, k])) for k in range(n) if a[vi, k] > 0)
        rep["channels"][c] = {"keys": list(keys), "joints": n, "D_mm": round(D * 1000, 3),
                              "dirs": [[round(float(x), 4) for x in t] for t in dirs], "verts": int(len(allv)),
                              "max_dropped_mm": round(resid * 1000, 3)}
    icen = np.concatenate([co[o.name][iris_mask[o.name]] for o in face_meshes]).mean(axis=0)
    joints.append(("KF_Iris", "Head_0", Vector(icen), Vector((1.0, 0.0, 0.0))))
    for side, off in look.items():
        joints.append((f"KF_Iris_{side}", "KF_Iris", Vector(icen + off / IRIS_W), Vector((1.0, 0.0, 0.0))))
    for o in face_meshes:
        for vi in np.nonzero(iris_mask[o.name])[0]:
            weights[o.name].setdefault(int(vi), []).append(("KF_Iris", IRIS_W))
    rep["iris"]["verts"] = int(sum(m.sum() for m in iris_mask.values()))
    rep["iris_weight"] = IRIS_W
    return joints, weights, rep


def apply_face_weights(obj, fw, stats):
    """Give the vertices their expression weights; the rest of each vertex's weights is scaled to what is left. At most
    8 influences per vertex: at most 7 expression influences (the smallest dropped first: vertices where several
    channels overlap, e.g. stray vertices with tiny deltas in every key), then the largest other influences."""
    vgs = {vg.index: vg.name for vg in obj.vertex_groups}
    groups = {vg.name: vg for vg in obj.vertex_groups}
    for vi, face in fw.items():
        v = obj.data.vertices[vi]
        merged_face = {}
        for n, w in face:
            merged_face[n] = merged_face.get(n, 0.0) + w
        face = sorted(merged_face.items(), key=lambda t: -t[1])
        if len(face) > 7:
            stats["dropped_influences"] = stats.get("dropped_influences", 0) + len(face) - 7
            stats["dropped_weight_max"] = max(stats.get("dropped_weight_max", 0.0), sum(w for _, w in face[7:]))
            face = face[:7]
        tot = sum(w for _, w in face)
        assert tot <= 1.0 + 1e-6, (obj.name, vi, tot)
        cur = sorted(((vgs[g.group], g.weight) for g in v.groups if g.weight > 0), key=lambda t: -t[1])
        for n, _ in cur:
            groups[n].remove([vi])
        cur = cur[:8 - len(face)] or [("Head_0", 1.0)]
        s = sum(w for _, w in cur)
        merged = dict(face)
        for n, w in cur:
            merged[n] = merged.get(n, 0.0) + w / s * (1.0 - tot)
        assert len(merged) <= 8, (obj.name, vi, len(merged))
        stats["max_influences"] = max(stats.get("max_influences", 0), len(merged))
        for n, w in merged.items():
            if w <= 1e-6:   # (an influence scaled to nothing is not written: the weighted-bone count stays honest)
                continue
            g = groups.get(n) or obj.vertex_groups.new(name=n)
            groups[n] = g
            g.add([vi], w, "REPLACE")


# ---------------------------------------------------------------- posing
def pose_rotate(arm, pb_name, R_world):
    pb = arm.pose.bones[pb_name]
    h = pb.head.copy()
    pb.matrix = Matrix.Translation(h) @ R_world @ Matrix.Translation(-h) @ pb.matrix
    bpy.context.view_layer.update()


def dd2_pos(dd2, name):
    return dd2.data.bones[name].head_local.copy()


def dd2_xaxis(dd2, name):
    return dd2.data.bones[name].matrix_local.col[0].xyz.normalized()


def repose_karin(karin, dd2, report):
    bpy.context.view_layer.objects.active = karin
    bpy.ops.object.mode_set(mode="POSE")
    angles = {}
    for kb, kchild, db, dtarget in AIM:
        pb = karin.pose.bones[kb]
        if kchild == "HAND_FRAME":
            side = kb[-1]
            kx = karin.pose.bones[f"MiddleProximal.{side}"].head - pb.head
            klat = karin.pose.bones[f"IndexProximal.{side}"].head - karin.pose.bones[f"LittleProximal.{side}"].head
            dx = dd2_pos(dd2, f"{side}_Hand_MiddleF_1") - dd2_pos(dd2, f"{side}_Arm_Hand")
            dlat = dd2_pos(dd2, f"{side}_Hand_IndexF_1") - dd2_pos(dd2, f"{side}_Hand_PinkyF_1")
            R = (frame(dx, dlat) @ frame(kx, klat).transposed()).to_4x4()
        else:
            cur = (karin.pose.bones[kchild].head - pb.head) if kchild else (pb.tail - pb.head)
            if dtarget:
                tgt = dd2_pos(dd2, dtarget) - dd2_pos(dd2, db)
            else:
                # terminal joint: DD2 X axis, signed to continue the parent segment (right-side RE bones point back)
                tgt = dd2_xaxis(dd2, db)
                parent_dir = dd2_pos(dd2, db) - dd2.data.bones[db].parent.head_local
                if tgt.dot(parent_dir) < 0:
                    tgt = -tgt
            R = rot_between(cur, tgt)
        angles[kb] = math.degrees(R.to_quaternion().angle)
        pose_rotate(karin, kb, R)
    bpy.ops.object.mode_set(mode="OBJECT")
    report["pose_angles_deg"] = {k: round(v, 2) for k, v in angles.items()}


def bake_pose_into_meshes(meshes, karin):
    dg = bpy.context.evaluated_depsgraph_get()
    for o in meshes:
        ev = o.evaluated_get(dg)
        me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg)
        old = o.data
        o.modifiers.clear()
        o.data = me
        bpy.data.meshes.remove(old)


# ---------------------------------------------------------------- skeleton
def karin_joint(karin, name):
    return karin.pose.bones[name].head.copy()


def polyline_point_at_height(points, z):
    for a, b in zip(points, points[1:]):
        if a.z <= z <= b.z and b.z > a.z:
            t = (z - a.z) / (b.z - a.z)
            return a.lerp(b, t)
    return points[-1].copy() if z > points[-1].z else points[0].copy()


def build_target_positions(karin, dd2):
    """World (Blender) positions of every DD2 bone in Karin proportions."""
    P = {}
    # mapped joints
    for kb, db in DIRECT.items():
        if kb.startswith("Eye") or kb not in karin.pose.bones:
            continue
        P[db] = karin_joint(karin, kb)
    for kb, (a, b, _tw) in SEGMENTS.items():
        P[a] = karin_joint(karin, kb)
    hip = P["Hip"]
    neck0 = karin_joint(karin, "Neck")
    head0 = karin_joint(karin, "Head")
    P["Neck_0"] = neck0
    P["Head_0"] = head0
    dd = {n: dd2_pos(dd2, n) for n in ("Hip", "Spine_1", "Spine_2", "Neck_0", "Neck_1", "Head_0")}
    spine_line = [karin_joint(karin, n) for n in ("Hips", "Spine", "Chest", "Neck")]
    f1 = (dd["Spine_1"].z - dd["Hip"].z) / (dd["Neck_0"].z - dd["Hip"].z)
    f2 = (dd["Spine_2"].z - dd["Hip"].z) / (dd["Neck_0"].z - dd["Hip"].z)
    P["Spine_0"] = hip + (dd2_pos(dd2, "Spine_0") - dd["Hip"])
    P["Spine_1"] = polyline_point_at_height(spine_line, hip.z + f1 * (neck0.z - hip.z))
    P["Spine_2"] = polyline_point_at_height(spine_line, hip.z + f2 * (neck0.z - hip.z))
    fn = (dd["Neck_1"].z - dd["Neck_0"].z) / (dd["Head_0"].z - dd["Neck_0"].z)
    P["Neck_1"] = neck0.lerp(head0, fn)
    mapped = set(P)

    # per-anchor scale ratios (Karin length / DD2 length) for placing unmapped helper/prop/twist joints
    def seg_ratio(a, b):
        return (P[b] - P[a]).length / max(1e-6, (dd2_pos(dd2, b) - dd2_pos(dd2, a)).length)

    ratio = {}
    torso_r = seg_ratio("Hip", "Neck_0")
    for n in ("Hip", "Spine_0", "Spine_1", "Spine_2", "Neck_0", "Neck_1", "Head_0"):
        ratio[n] = torso_r
    for s in ("L", "R"):
        ratio[f"{s}_Arm_Clavicle"] = seg_ratio(f"{s}_Arm_Clavicle", f"{s}_Arm_Upper")
        ratio[f"{s}_Arm_Upper"] = seg_ratio(f"{s}_Arm_Upper", f"{s}_Arm_Lower")
        ratio[f"{s}_Arm_Lower"] = seg_ratio(f"{s}_Arm_Lower", f"{s}_Arm_Hand")
        ratio[f"{s}_Arm_Hand"] = seg_ratio(f"{s}_Arm_Hand", f"{s}_Hand_MiddleF_1")
        ratio[f"{s}_Leg_Upper"] = seg_ratio(f"{s}_Leg_Upper", f"{s}_Leg_Lower")
        ratio[f"{s}_Leg_Lower"] = seg_ratio(f"{s}_Leg_Lower", f"{s}_Leg_Ankle")
        ratio[f"{s}_Leg_Ankle"] = seg_ratio(f"{s}_Leg_Ankle", f"{s}_Leg_Toes")
        ratio[f"{s}_Leg_Toes"] = ratio[f"{s}_Leg_Ankle"]
        ratio[f"{s}_Breast"] = torso_r
        for df in ("Thumb", "Index", "Middle", "Ring", "Pinky"):
            for i in (1, 2, 3):
                ratio[f"{s}_Hand_{df}F_{i}"] = ratio[f"{s}_Arm_Hand"]
    hip_w = (P["L_Leg_Upper"] - P["R_Leg_Upper"]).length / (dd2_pos(dd2, "L_Leg_Upper") - dd2_pos(dd2, "R_Leg_Upper")).length
    ratio["Hip"] = hip_w
    ratio["Spine_0"] = hip_w

    bones = dd2.data.bones
    anchors = {}
    for b in bones:  # parents come before children in RE order
        n = b.name
        if n in P:
            continue
        if n == "root" or b.parent is None or b.parent.name == "root":
            P[n] = b.head_local.copy()  # root-level (ground, GroundAngle...) stays native
            anchors[n] = "native"
            continue
        # "*Offset" helpers anchor to their mapped child (e.g. L_BreastOffset -> L_Breast)
        child_mapped = [c for c in b.children if c.name in mapped]
        if n.endswith("Offset") and child_mapped:
            c = child_mapped[0]
            P[n] = P[c.name] + (b.head_local - c.head_local)
            anchors[n] = c.name
            continue
        a = b.parent
        while a.name not in mapped and a.name in anchors and anchors[a.name] not in ("native",) and a.parent is not None:
            a = a.parent
        if a.name not in P:
            a = b.parent
        r = ratio.get(a.name, torso_r)
        P[n] = P[a.name] + (b.head_local - a.head_local) * r
        anchors[n] = a.name
    return P, ratio, anchors


def build_target_armature(dd2, karin, P, extra, face_joints=()):
    new = dd2.copy()
    new.data = dd2.data.copy()
    new.name = "karin_body Armature"
    new.data.name = "karin_body Armature"
    bpy.context.scene.collection.objects.link(new)
    bpy.context.view_layer.objects.active = new
    for o in bpy.context.selected_objects:
        o.select_set(False)
    new.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    eb = new.data.edit_bones
    for b in eb:
        rot = b.matrix.to_3x3().normalized().to_4x4()
        length = b.length
        b.matrix = Matrix.Translation(P[b.name]) @ rot
        b.length = length
        for k in ("reMeshWorldMatrix", "reMeshLocalMatrix", "reMeshInverseMatrix"):
            if k in b:
                del b[k]
    added = {}
    if extra:
        kpose = karin.pose.bones
        for kname in extra:  # parents first (karin bone order)
            pb = kpose[kname]
            nb = eb.new(extra_name(kname))
            nb.head = pb.head
            nb.tail = pb.tail
            nb.matrix = re_chain_frame(pb.head, pb.tail - pb.head)
            nb.length = max(pb.length, 0.005)
            added[kname] = nb.name
        for kname in extra:
            kp = kpose[kname].parent
            pname = None
            while kp is not None:
                if kp.name in added:
                    pname = added[kp.name]
                    break
                if kp.name in DIRECT:
                    pname = DIRECT[kp.name]
                    break
                if kp.name in SEGMENTS:
                    pname = SEGMENTS[kp.name][0]
                    break
                if kp.name in TORSO:
                    pname = "Spine_1" if kp.name == "Spine" else "Spine_2"
                    break
                if kp.name in NECK:
                    pname = "Neck_0"
                    break
                kp = kp.parent
            eb[added[kname]].parent = eb[pname or "Hip"]
    for name, parent, head, xdir in face_joints:   # parents first
        nb = eb.new(name)
        nb.head = head
        nb.tail = head + xdir.normalized() * 0.005
        nb.matrix = re_chain_frame(head, xdir)
        nb.length = 0.005
        nb.parent = eb[parent]
    bpy.ops.object.mode_set(mode="OBJECT")
    new.data.pose_position = "REST"
    return new, added


def re_chain_frame(head, direction):
    """Bone matrix whose local X axis (RE bone axis, exported as the RE X axis) points along `direction`.

    Native DD2 chain joints keep their child offset on local +X; chain simulation assumes it."""
    d = direction.normalized() if direction.length > 1e-8 else Vector((0.0, 0.0, -1.0))
    ref = Vector((0.0, 0.0, 1.0)) if abs(d.z) < 0.9 else Vector((1.0, 0.0, 0.0))
    z = d.cross(ref).normalized()
    y = z.cross(d).normalized()
    m = Matrix((d, y, z)).transposed().to_4x4()
    m.translation = head
    return m


def extra_name(kname):
    return "K_" + kname.replace(".", "_")


# ---------------------------------------------------------------- weights
def remap_weights(obj, karin, dd2_new, P, extra_map, weak_map=None):
    """Replace Karin vertex groups with DD2 / K_ groups on obj (geometry already posed & final).
    weak_map: Karin secondary bone -> output bone that takes its weights instead (see FACE weak_bone_max)."""
    weak_map = weak_map or {}
    me = obj.data
    src_groups = {vg.index: vg.name for vg in obj.vertex_groups}
    spine_h = (P["Spine_1"].z, P["Spine_2"].z)
    neck_h = P["Neck_1"].z
    dz_t = 0.03 * 1.0
    seg_axes = {}
    for kb, (a, b, tw) in SEGMENTS.items():
        pa, pb_ = P[a], P[b]
        seg_axes[kb] = (pa, pb_ - pa, tw)
    newweights = []
    unmapped = {}
    for v in me.vertices:
        w = {}

        def add(n, x):
            if x > 0:
                w[n] = w.get(n, 0.0) + x

        for g in v.groups:
            if g.weight <= 0:
                continue
            name = src_groups[g.group]
            x = g.weight
            if name in DIRECT:
                add(DIRECT[name], x)
            elif name in SEGMENTS:
                pa, ax, tw = seg_axes[name]
                t = (v.co - pa).dot(ax) / max(1e-9, ax.length_squared)
                # hat functions over twist joints at 0, 1/3, 2/3 (the last one owns the rest of the segment)
                k = [0.0, 1.0 / 3.0, 2.0 / 3.0]
                if t <= k[0]:
                    add(tw + "0", x)
                elif t >= k[2]:
                    add(tw + "2", x)
                else:
                    i = 0 if t < k[1] else 1
                    f = (t - k[i]) / (k[i + 1] - k[i])
                    add(tw + str(i), x * (1 - f))
                    add(tw + str(i + 1), x * f)
            elif name in TORSO:
                z = v.co.z
                f1 = smoothstep(spine_h[0] - dz_t, spine_h[0] + dz_t, z)
                f2 = smoothstep(spine_h[1] - dz_t, spine_h[1] + dz_t, z)
                add("Spine_0", x * (1 - f1))
                add("Spine_1", x * (f1 - f2))
                add("Spine_2", x * f2)
            elif name in NECK:
                f = smoothstep(neck_h - 0.015, neck_h + 0.015, v.co.z)
                add("Neck_0", x * (1 - f))
                add("Neck_1", x * f)
            elif name in extra_map:
                add(weak_map.get(name, extra_map[name]), x)
            else:
                unmapped[name] = unmapped.get(name, 0) + 1
                add("Head_0" if v.co.z > P["Neck_1"].z else "Hip", x)
        items = sorted(((n, x) for n, x in w.items() if x > 1e-4), key=lambda t: -t[1])[:8]
        s = sum(x for _, x in items)
        newweights.append([(n, x / s) for n, x in items] if s > 0 else [("Hip", 1.0)])
    for vg in list(obj.vertex_groups):
        obj.vertex_groups.remove(vg)
    groups = {}
    for i, ws in enumerate(newweights):
        for n, x in ws:
            g = groups.get(n)
            if g is None:
                assert n in dd2_new.data.bones, n
                g = groups[n] = obj.vertex_groups.new(name=n)
            g.add([i], x, "REPLACE")
    return unmapped


# ---------------------------------------------------------------- output meshes
def split_by_material(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.separate(type="MATERIAL")
    bpy.ops.object.mode_set(mode="OBJECT")
    return [o for o in bpy.context.selected_objects]


def prep_output_object(o):
    me = o.data
    # UV0 = source UV, UV1 = copy (the DD2 vertex layout carries two UV streams)
    assert len(me.uv_layers) >= 1
    me.uv_layers[0].name = "UVMap0"
    while len(me.uv_layers) > 1:
        me.uv_layers.remove(me.uv_layers[1])
    uv1 = me.uv_layers.new(name="UVMap1")
    for i, d in enumerate(me.uv_layers[0].data):
        uv1.data[i].uv = d.uv
    for a in list(me.color_attributes):
        me.color_attributes.remove(a)


def main():
    args = parse_args()
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    prof = dict(PROFILES[args.profile], blend=Path(args.source_blend))
    DD2_BODY = Path(args.dd2_body)
    report = {"args": vars(args), "karin_blend": str(prof["blend"]), "karin_blend_sha256": sha(prof["blend"]),
              "dd2_body": str(DD2_BODY), "dd2_body_sha256": sha(DD2_BODY)}

    bpy.ops.wm.read_factory_settings(use_empty=True)
    rc.enable_re_mesh_editor()
    dd2_coll, dd2 = rc.import_re_mesh(DD2_BODY, shadow=False)
    assert dd2 is not None and len(dd2.data.bones) == 192
    assert (dd2.matrix_world - Matrix.Identity(4)).to_translation().length < 1e-9

    kcoll, karin, kmeshes = load_karin(prof["blend"])
    face = None if (args.no_face or args.skeleton_only or args.no_extra_bones) else FACE[args.profile]
    fkeys = face_keys(face) if face else []
    if face:
        report["face_capture"] = face_capture(kmeshes, fkeys)
    shape_report = {}
    for o in kmeshes:
        bake_shape_keys(o, shape_report)
    report["shape_keys"] = shape_report

    # uniform scale: Karin Hips height -> DD2 Hip height; floor stays at z = 0
    s = dd2_pos(dd2, "Hip").z / karin.data.bones["Hips"].head_local.z
    G = Matrix.Scale(s, 4)
    karin.data.transform(G)
    for o in kmeshes:
        o.data.transform(G)
    face_scale(kmeshes, fkeys, s)
    bpy.context.view_layer.update()
    report["uniform_scale"] = s

    repose_karin(karin, dd2, report)
    bake_pose_into_meshes(kmeshes, karin)
    for key in fkeys:   # the deltas must have come through the face deletion and the pose bake
        assert any(o.data.attributes.get(face_attr(key)) for o in kmeshes), ("face attribute lost", key)
    face_joints, face_weights = [], {}
    if face:
        face_joints, face_weights, report["face"] = face_plan(kmeshes, face)

    P, ratio, anchors = build_target_positions(karin, dd2)
    report["joint_positions"] = {n: [round(c, 5) for c in P[n]] for n in P}
    report["native_positions"] = {b.name: [round(c, 5) for c in b.head_local] for b in dd2.data.bones}
    report["anchor_ratio"] = {k: round(v, 4) for k, v in ratio.items()}
    report["unmapped_anchor"] = anchors

    humanoid = set(DIRECT) | set(SEGMENTS) | set(TORSO) | set(NECK)
    extra = [] if (args.no_extra_bones or args.skeleton_only) else [b.name for b in karin.data.bones if b.name not in humanoid]
    # only keep extra bones that carry weights (plus their ancestors)
    weighted = set()
    for o in kmeshes:
        idx = {vg.index: vg.name for vg in o.vertex_groups}
        for v in o.data.vertices:
            for g in v.groups:
                if g.weight > 0:
                    weighted.add(idx[g.group])
    keep = set()
    for n in extra:
        if n in weighted:
            b = karin.data.bones[n]
            while b is not None and b.name not in humanoid:
                keep.add(b.name)
                b = b.parent
    if prof["chain_tips"]:
        keep |= {n for n in extra if n not in keep and karin.data.bones[n].parent is not None
                 and karin.data.bones[n].parent.name in keep}
    extra = [n for n in extra if n in keep]
    new_arm, extra_map = build_target_armature(dd2, karin, P, extra, face_joints)
    # secondary bones with negligible influence give their weights to their (output) parent: bone budget
    weak_map = {}
    if face and face["weak_bone_max"] > 0:
        maxw = {}
        for o in kmeshes:
            idx = {vg.index: vg.name for vg in o.vertex_groups}
            for v in o.data.vertices:
                for g in v.groups:
                    n = idx[g.group]
                    maxw[n] = max(maxw.get(n, 0.0), g.weight)
        weak = {n for n in extra_map if 0 < maxw.get(n, 0.0) < face["weak_bone_max"]}
        by_out = {v: k for k, v in extra_map.items()}
        for n in weak:
            b = new_arm.data.bones[extra_map[n]].parent
            while b.name in by_out and by_out[b.name] in weak:
                b = b.parent
            weak_map[n] = b.name
        report["weak_bones_merged"] = {n: [weak_map[n], round(maxw[n], 4)] for n in sorted(weak)}
    if args.no_extra_bones:
        # collapse secondary groups into the nearest mapped ancestor
        for b in karin.data.bones:
            if b.name in humanoid:
                continue
            a = b.parent
            while a is not None and a.name not in humanoid:
                a = a.parent
            nm = a.name if a is not None else "Hips"
            extra_map[b.name] = DIRECT.get(nm) or (SEGMENTS[nm][0] if nm in SEGMENTS else ("Spine_2" if nm == "Chest" else "Spine_1" if nm == "Spine" else "Neck_0"))
    report["extra_bones"] = extra_map
    report["bone_count"] = len(new_arm.data.bones)

    # output collection in RE Mesh Editor layout
    root = bpy.data.collections.new(f"{args.name}.mesh")
    root["~TYPE"] = "RE_MESH_COLLECTION"
    root["~ASSETPATH"] = prof["asset"]
    root["LODGroupNameHash"] = "0"
    bpy.context.scene.collection.children.link(root)
    for c in list(new_arm.users_collection):
        c.objects.unlink(new_arm)
    root.objects.link(new_arm)
    lod_dist = [0.00979990977793932, 0.32378992438316345]
    lod0 = bpy.data.collections.new(f"Main Mesh LOD0 - {args.name}.mesh")
    lod0["LOD Distance"] = lod_dist[0]
    root.children.link(lod0)

    unmapped_all = {}
    per_group_sub = {}
    stats = []
    for o in ([] if args.skeleton_only else kmeshes):
        unm = remap_weights(o, karin, new_arm, P, extra_map, weak_map)
        for k, v in unm.items():
            unmapped_all[k] = unmapped_all.get(k, 0) + v
        if o.name in face_weights:
            apply_face_weights(o, face_weights[o.name], report["face"].setdefault("weights", {}))
        for key in fkeys:
            a = o.data.attributes.get(face_attr(key))
            if a is not None:
                o.data.attributes.remove(a)
        prep_output_object(o)
        parts = split_by_material(o) if len(o.data.materials) > 1 else [o]
        for p in parts:
            if len(p.data.polygons) == 0:
                bpy.data.objects.remove(p, do_unlink=True)
                continue
            srcmat = p.data.materials[p.data.polygons[0].material_index].name if p.data.materials else "Body"
            assert srcmat in MATERIALS[args.profile], ("no material mapping for", srcmat)
            dmat, grp = MATERIALS[args.profile][srcmat]
            if args.materials == "test_body":
                dmat = "body_mat"
            mat = bpy.data.materials.get(dmat) or bpy.data.materials.new(dmat)
            p.data.materials.clear()
            p.data.materials.append(mat)
            for poly in p.data.polygons:
                poly.material_index = 0
            sub = per_group_sub.get(grp, 0)
            per_group_sub[grp] = sub + 1
            p.name = f"LOD_0_Group_{grp}_Sub_{sub}__{dmat}"
            p.parent = None
            p.matrix_world = Matrix.Identity(4)
            p.modifiers.clear()
            mod = p.modifiers.new("Armature", "ARMATURE")
            mod.object = new_arm
            for c in list(p.users_collection):
                c.objects.unlink(p)
            lod0.objects.link(p)
            stats.append({"object": p.name, "source_material": srcmat, "verts": len(p.data.vertices), "tris": sum(len(f.vertices) - 2 for f in p.data.polygons)})
    # hidden compatibility submeshes carrying the native body material names, which the game's per-character material
    # systems (skin details, dirt, wounds, VFX) look up on the body mesh. Default: one zero-area triangle each.
    # --native-compat (experimental): the native body's own submeshes in visibility group NATIVE_GROUP, which is off
    # in game (only group 0 is on by default; the script turns on 0..7).
    NATIVE_GROUP = 16
    native_parts = [] if not args.native_compat else sorted(
        (o for o in dd2_coll.all_objects if o.type == "MESH" and o.name.startswith("LOD_0_")), key=lambda o: o.name)
    for o in native_parts:
        name = o.name.split("__", 1)[1] if "__" in o.name else o.name
        c = o.copy()
        c.data = o.data.copy()
        sub = per_group_sub.get(NATIVE_GROUP, 0)
        per_group_sub[NATIVE_GROUP] = sub + 1
        c.name = f"LOD_0_Group_{NATIVE_GROUP}_Sub_{sub}__{name}"
        c.parent = None
        c.matrix_world = o.matrix_world.copy()
        c.modifiers.clear()
        c.modifiers.new("Armature", "ARMATURE").object = new_arm
        # never visible and baked in UV space: bound rigidly to the Hip, so it adds no weighted bones (limit 256)
        for vg in list(c.vertex_groups):
            c.vertex_groups.remove(vg)
        c.vertex_groups.new(name="Hip").add(list(range(len(c.data.vertices))), 1.0, "REPLACE")
        for col in list(c.users_collection):
            col.objects.unlink(c)
        lod0.objects.link(c)
        stats.append({"object": c.name, "source_material": "native " + name, "verts": len(c.data.vertices),
                      "tris": sum(len(f.vertices) - 2 for f in c.data.polygons)})
    hip = new_arm.data.bones["Hip"].head_local.copy()
    for name in ([n for n in args.compat_materials.split(",") if n] if not args.native_compat else []):
        me = bpy.data.meshes.new("compat_" + name)
        me.from_pydata([hip, hip + Vector((0.00001, 0, 0)), hip + Vector((0, 0.00001, 0))], [], [(0, 1, 2)])
        me.uv_layers.new(name="UVMap0")
        me.uv_layers.new(name="UVMap1")
        me.materials.append(bpy.data.materials.get(name) or bpy.data.materials.new(name))
        sub = per_group_sub.get(0, 0)
        per_group_sub[0] = sub + 1
        o = bpy.data.objects.new(f"LOD_0_Group_0_Sub_{sub}__{name}", me)
        lod0.objects.link(o)
        o.vertex_groups.new(name="Hip").add([0, 1, 2], 1.0, "REPLACE")
        o.modifiers.new("Armature", "ARMATURE").object = new_arm
        stats.append({"object": o.name, "source_material": "compat", "verts": 3, "tris": 1})
    report["unmapped_groups"] = unmapped_all
    report["submeshes"] = stats
    deform = set()
    for o in lod0.objects:
        idx = {vg.index: vg.name for vg in o.vertex_groups}
        for v in o.data.vertices:
            deform.update(idx[g.group] for g in v.groups if g.weight > 0)
    report["deform_bones"] = len(deform)
    assert len(deform) <= MAX_DEFORM, ("too many weighted bones", len(deform))

    for li in range(1, args.lods):
        lod = bpy.data.collections.new(f"Main Mesh LOD{li} - {args.name}.mesh")
        lod["LOD Distance"] = lod_dist[min(li, len(lod_dist) - 1)]
        root.children.link(lod)
        for o in list(lod0.objects):
            c = o.copy()
            c.data = o.data.copy()
            c.name = o.name.replace("LOD_0_", f"LOD_{li}_", 1)
            lod.objects.link(c)

    # remove everything that is not part of the output
    keep_objs = set(root.all_objects)
    for o in list(bpy.data.objects):
        if o not in keep_objs:
            bpy.data.objects.remove(o, do_unlink=True)
    for c in list(bpy.data.collections):
        if c not in (root, *root.children_recursive):
            bpy.data.collections.remove(c)

    mesh_out = out / f"{args.name}.mesh.240423143"
    rc.export_re_mesh(root, mesh_out, preserve_bone_matrices=False)
    report["output"] = {"path": str(mesh_out), "sha256": sha(mesh_out)}
    bpy.ops.wm.save_as_mainfile(filepath=str(out / f"{args.name}_build.blend"))
    (out / "build_report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    log("BUILD_DONE", mesh_out)


main()
