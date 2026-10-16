# Build Karin_Original as the Days Gone (classic) Deacon master head mesh (Blender 4.2 background).
#
# Usage:
#   blender --background --factory-startup --python build_body.py -- <run_dir> [--target <deacon .uemodel>]
#           [--scale 1.40] [--variant A|B] [--name deacon_head_standard]
#
# The fitting method is the Stellar Blade one (StellaBlade/Karin_Original_EVE09/Scripts/build_body.py): every Karin
# limb segment is rotated/stretched onto the target joints (joint translations come from the game's animations, so the
# mesh has to be bound at the target joint positions), then the vertex weights are remapped onto the target bones.
#
# Variant A: only target-skeleton bones (secondary chains merged into their parent) -> pipeline proof.
# Variant B: Karin's secondary chains kept as extra bones (EXTRA_PREFIX + Karin name) under their target parent.
#
# Output in <run_dir>: <name>.fbx, textures/*.png, report.json, build.blend
import bpy, sys, os, json, math
import numpy as np
from mathutils import Matrix, Vector
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # the kit's scripts/
import dgpaths

argv = sys.argv[sys.argv.index("--") + 1:]
RUN = os.path.abspath(argv[0])
def arg(flag, default):
    return argv[argv.index(flag) + 1] if flag in argv else default
TARGET_UE = arg("--target", None) or dgpaths.head_uemodel()   # default <DG_CACHE>/ue/.../deacon_head_standard.uemodel
SCALE = float(arg("--scale", "1.30"))
VARIANT = arg("--variant", "A")
NAME = arg("--name", "deacon_head_standard")
# cm: Karin's head sits this far below the target head joint; only useful with --prop deacon (Deacon's neck is ~2x
# Karin's scaled neck there)
HEAD_DROP = float(arg("--head-drop", "0.0"))
os.makedirs(RUN, exist_ok=True)

KARIN_VRM = dgpaths.karin_vrm()   # <DG_MODELS_DIR>/Karin_Original/Karin(Clone).vrm
MAX_INF = 4                       # UE 4.11 GPU skin: 4 influences unless the project enables 8 (not by default)
PELVIS = "Hips"                   # Deacon: Hips -> cog -> spine..spine4; legs hang off Hips
REPORT = {"variant": VARIANT, "scale": SCALE, "head_drop": HEAD_DROP, "target": TARGET_UE, "warnings": []}

import addon_utils
bpy.ops.wm.read_factory_settings(use_empty=True)
addon_utils.enable("io_scene_ueformat", default_set=True)
addon_utils.enable("io_scene_fbx", default_set=True)

# ---------------------------------------------------------------- import target (Deacon)
s = bpy.context.scene.uf_settings
s.scale_factor = 1.0
s.import_sockets = False
s.import_morph_targets = False
before = set(bpy.data.objects)
bpy.ops.uf.import_uemodel(filepath=TARGET_UE, files=[{"name": os.path.basename(TARGET_UE)}], directory=os.path.dirname(TARGET_UE))
t_objs = [o for o in bpy.data.objects if o not in before]
t_arm = next(o for o in t_objs if o.type == "ARMATURE")
E = {b.name: (t_arm.matrix_world @ b.matrix_local) for b in t_arm.data.bones}
def ej(n): return np.array(E[n].translation)

# ---------------------------------------------------------------- import Karin
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=KARIN_VRM)
k_objs = [o for o in bpy.data.objects if o not in before]
k_arm = next(o for o in k_objs if o.type == "ARMATURE")
k_arm.name = "KarinArmature"; k_arm.data.name = "KarinArmature"
K_MESHES = ["Body", "body_2", "hair", "kemomimi", "tail", "pullover", "skirt", "underwear", "knee-socks", "shoes"]
k_meshes = [o for o in k_objs if o.type == "MESH" and o.name in K_MESHES]
for o in k_objs:
    if o.type != "ARMATURE" and o not in k_meshes:
        bpy.data.objects.remove(o, do_unlink=True)

# Karin and the UEFormat import both face -Y with the character's left on +X: only metres -> cm * SCALE
G = Matrix.Scale(100.0 * SCALE, 4)
Gn = np.array(G)
KB = {b.name: b for b in k_arm.data.bones}
def kj(n): return np.array(G @ (k_arm.matrix_world @ KB[n].head_local))
def ktail(n): return np.array(G @ (k_arm.matrix_world @ KB[n].tail_local))
def norm(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-9 else v

# ---------------------------------------------------------------- re-proportion the target skeleton (--prop karin)
# deacon_master_Skeleton retargets the body bones' translations in mode "Skeleton" (Hips: "AnimationScaled"), so in game
# their bone lengths come from this mesh's reference pose and only the rotations come from the animations. The bind
# skeleton keeps Deacon's bone orientations and joint angles; each body segment takes Karin's scaled length (offset
# direction in the parent frame unchanged, so the animations bend the limbs as on Deacon). Animation-mode children
# (face joints, helpers, cloth/socket bones) keep Deacon's offsets from their moved parents.
PROP = arg("--prop", "karin")
if PROP == "karin":
    D = {b.name: np.array(t_arm.matrix_world @ b.head_local) for b in t_arm.data.bones}
    dist = lambda a, b: float(np.linalg.norm(a - b))
    def both(f): return (f("Left") + f("Right")) / 2
    k_legmid = (kj("LeftUpperLeg") + kj("RightUpperLeg")) / 2
    d_legmid = (D["LeftUpLeg"] + D["RightUpLeg"]) / 2
    K_ = {
        "torso": dist(kj("Neck"), k_legmid) / dist(D["Neck"], d_legmid),
        "neck": dist(kj("Head"), kj("Neck")) / dist(D["Head"], D["Neck"]),
        "hipw": abs(kj("LeftUpperLeg")[0] - kj("RightUpperLeg")[0]) / abs(D["LeftUpLeg"][0] - D["RightUpLeg"][0]),
        "thigh": both(lambda s: dist(kj(f"{s}LowerLeg"), kj(f"{s}UpperLeg")) / dist(D[f"{s}Leg"], D[f"{s}UpLeg"])),
        "shin": both(lambda s: dist(kj(f"{s}Foot"), kj(f"{s}LowerLeg")) / dist(D[f"{s}Foot"], D[f"{s}Leg"])),
        "foot": both(lambda s: dist(kj(f"{s}ToeBase"), kj(f"{s}Foot")) / dist(D[f"{s}ToeBase"], D[f"{s}Foot"])),
        "upper": both(lambda s: dist(kj(f"{s}LowerArm"), kj(f"{s}UpperArm")) / dist(D[f"{s}ForeArm"], D[f"{s}Arm"])),
        "lower": both(lambda s: dist(kj(f"{s}Hand"), kj(f"{s}LowerArm")) / dist(D[f"{s}Hand"], D[f"{s}ForeArm"])),
        "hand": both(lambda s: dist(kj(f"{s}MiddleProximal"), kj(f"{s}Hand")) / dist(D[f"{s}HandMiddle1"], D[f"{s}Hand"])),
    }
    # pelvis height: the legs' joints must land at Karin's hip-joint height after the hip-width scaling
    K_["hip"] = (k_legmid[2] - (d_legmid[2] - D["Hips"][2]) * K_["hipw"]) / D["Hips"][2]
    GROUP = {"Hips": "hip", "LeftUpLeg": "hipw", "RightUpLeg": "hipw", "Neck1": "neck", "Head": "neck"}
    for n in ("cog", "spine", "spine1", "spine2", "spine3", "spine4", "Neck", "LeftShoulder", "RightShoulder"):
        GROUP[n] = "torso"
    for S_ in ("Left", "Right"):
        GROUP.update({f"{S_}Leg": "thigh", f"{S_}Foot": "shin", f"{S_}Heel": "foot", f"{S_}ToeBase": "foot",
                      f"{S_}ForeArm": "upper", f"{S_}Hand": "lower"})
        for fe in ("HandThumb", "HandIndex", "HandMiddle", "HandRing", "InHandPinky"):
            for i in ("", "1", "2", "3"):
                if f"{S_}{fe}{i}" in D: GROUP[f"{S_}{fe}{i}"] = "hand"
    new = {}
    def place(b):
        if b.name in new: return new[b.name]
        if b.parent is None:
            new[b.name] = D[b.name]
        else:
            p = place(b.parent)
            off = D[b.name] - D[b.parent.name]
            g = GROUP.get(b.name)
            if b.name in ("LeftArm", "RightArm"):
                # clavicle: the shoulder joint lands at Karin's shoulder-joint width
                S_ = b.name[:-3]
                k = (abs(kj(f"{S_}UpperArm")[0]) - abs(p[0])) / max(abs(off[0]), 1e-6)
                K_[f"clav_{S_}"] = k = min(max(k, 0.2), 1.5)
                off = off * k
            elif b.name in ("LeftEye", "RightEye"):
                off = kj(b.name) - kj("Head")      # eye pivots at Karin's eye centres
            elif g:
                off = off * K_[g]
            new[b.name] = p + off
        return new[b.name]
    for b in t_arm.data.bones:
        place(b)
    # edit only Deacon's armature: Karin's (still selected after import) would join the edit session, its bones would
    # be rebuilt and the cached KB references used by kj() would go stale
    bpy.ops.object.select_all(action="DESELECT")
    t_arm.select_set(True)
    bpy.context.view_layer.objects.active = t_arm
    bpy.ops.object.mode_set(mode="EDIT")
    to_arm = t_arm.matrix_world.inverted().to_3x3()
    for e in t_arm.data.edit_bones:
        e.use_connect = False
    for e in t_arm.data.edit_bones:
        d = Vector(to_arm @ Vector(new[e.name] - D[e.name]))
        if d.length > 1e-6:
            e.head = e.head + d; e.tail = e.tail + d
    bpy.ops.object.mode_set(mode="OBJECT")
    E.clear()
    E.update({b.name: (t_arm.matrix_world @ b.matrix_local) for b in t_arm.data.bones})
    REPORT["prop"] = {k: round(float(v), 4) for k, v in K_.items()}
    REPORT["prop_joints"] = {n: [round(float(x), 2) for x in new[n]] for n in ("Hips", "LeftUpLeg", "LeftLeg", "LeftFoot",
                             "Neck", "Head", "LeftArm", "LeftForeArm", "LeftHand", "LeftEye")}
REPORT["prop_mode"] = PROP

def swing(a, b):
    """rotation matrix taking unit dir a to unit dir b (minimal)"""
    a, b = norm(a), norm(b)
    v = np.cross(a, b); c = float(np.dot(a, b))
    if np.linalg.norm(v) < 1e-9:
        return np.eye(3) if c > 0 else -np.eye(3)
    vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + vx + vx @ vx * (1.0 / (1.0 + c))
def affine(A, R, a, d=None, sigma=1.0):
    """x -> A + R @ (S @ (x - a)); S stretches by sigma along unit d (Karin space)"""
    S = np.eye(3)
    if d is not None and abs(sigma - 1.0) > 1e-6:
        d = norm(d); S = S + (sigma - 1.0) * np.outer(d, d)
    L = R @ S
    Mx = np.eye(4); Mx[:3, :3] = L; Mx[:3, 3] = A - L @ a
    return Mx

M, ROT, INFO = {}, {}, {}
def seg(kname, ka, kb, ea, eb, parent_rot):
    dk = kb - ka; de = eb - ea
    R = swing(parent_rot @ norm(dk), norm(de)) @ parent_rot
    sigma = np.linalg.norm(de) / max(np.linalg.norm(dk), 1e-9)
    M[kname] = affine(ea, R, ka, d=dk, sigma=sigma)
    ROT[kname] = R
    INFO[kname] = {"sigma": round(float(sigma), 3)}
    return R

I3 = np.eye(3)
legmid_k = (kj("LeftUpperLeg") + kj("RightUpperLeg")) / 2
legmid_e = (ej("LeftUpLeg") + ej("RightUpLeg")) / 2
# torso: Karin's chest joint lands at the same fraction of the target pelvis->neck line
f_chest = np.linalg.norm(kj("Chest") - legmid_k) / np.linalg.norm(kj("Neck") - legmid_k)
chest_e = legmid_e + f_chest * (ej("Neck") - legmid_e)
Rh = seg("Hips", legmid_k, kj("Chest"), legmid_e, chest_e, I3)
M["Spine"] = M["Hips"]; ROT["Spine"] = Rh
Rc = seg("Chest", kj("Chest"), kj("Neck"), chest_e, ej("Neck"), Rh)
head_e = ej("Head") - np.array([0.0, 0.0, HEAD_DROP])
Rn = seg("Neck", kj("Neck"), kj("Head"), ej("Neck"), head_e, Rc)
# head: upright, rigid, translated to HEAD_DROP below the target head joint (Deacon's neck is ~2x Karin's scaled neck)
M["Head"] = affine(head_e, I3, kj("Head")); ROT["Head"] = I3

FINGERS = [("Thumb", "HandThumb"), ("Index", "HandIndex"), ("Middle", "HandMiddle"), ("Ring", "HandRing"),
           ("Little", "InHandPinky")]
PARTS = ["Proximal", "Intermediate", "Distal"]
for S_ in ("Left", "Right"):
    # shoulder: keep Karin's length, end on the target upper-arm joint along the clavicle direction
    cdir = norm(ej(f"{S_}Arm") - ej(f"{S_}Shoulder"))
    klen = np.linalg.norm(kj(f"{S_}UpperArm") - kj(f"{S_}Shoulder"))
    Rs = seg(f"{S_}Shoulder", kj(f"{S_}Shoulder"), kj(f"{S_}UpperArm"), ej(f"{S_}Arm") - cdir * klen, ej(f"{S_}Arm"), Rc)
    Ru = seg(f"{S_}UpperArm", kj(f"{S_}UpperArm"), kj(f"{S_}LowerArm"), ej(f"{S_}Arm"), ej(f"{S_}ForeArm"), Rs)
    Rl = seg(f"{S_}LowerArm", kj(f"{S_}LowerArm"), kj(f"{S_}Hand"), ej(f"{S_}ForeArm"), ej(f"{S_}Hand"), Ru)
    # hand: direction to middle proximal, then roll so the palm plane matches
    Rhd = seg(f"{S_}Hand", kj(f"{S_}Hand"), kj(f"{S_}MiddleProximal"), ej(f"{S_}Hand"), ej(f"{S_}HandMiddle1"), Rl)
    nk = Rhd @ norm(np.cross(kj(f"{S_}IndexProximal") - kj(f"{S_}Hand"), kj(f"{S_}LittleProximal") - kj(f"{S_}Hand")))
    ne = norm(np.cross(ej(f"{S_}HandIndex1") - ej(f"{S_}Hand"), ej(f"{S_}InHandPinky1") - ej(f"{S_}Hand")))
    D = norm(ej(f"{S_}HandMiddle1") - ej(f"{S_}Hand"))
    pk = norm(nk - D * np.dot(nk, D)); pe = norm(ne - D * np.dot(ne, D))
    ang = math.atan2(np.dot(np.cross(pk, pe), D), np.dot(pk, pe))
    Rhd2 = np.array(Matrix.Rotation(ang, 3, Vector(D))) @ Rhd
    hk, he = kj(f"{S_}Hand"), ej(f"{S_}Hand")
    M[f"{S_}Hand"] = affine(he, Rhd2, hk, d=kj(f"{S_}MiddleProximal") - hk, sigma=INFO[f"{S_}Hand"]["sigma"])
    ROT[f"{S_}Hand"] = Rhd2
    INFO[f"{S_}Hand"]["roll_deg"] = round(math.degrees(ang), 2)
    for fk, fe in FINGERS:
        names = [f"{S_}{fk}{p}" for p in PARTS]
        enames = [f"{S_}{fe}{i}" for i in (1, 2, 3)]
        Rp, last_sig = Rhd2, 1.0
        for i, (kn, en) in enumerate(zip(names, enames)):
            if i < 2:
                Rp = seg(kn, kj(kn), kj(names[i + 1]), ej(en), ej(enames[i + 1]), Rp)
                last_sig = INFO[kn]["sigma"]
            else:   # distal: keep the previous direction relation and stretch
                M[kn] = affine(ej(en), Rp, kj(kn), d=ktail(kn) - kj(kn), sigma=last_sig); ROT[kn] = Rp
for S_ in ("Left", "Right"):
    Rt = seg(f"{S_}UpperLeg", kj(f"{S_}UpperLeg"), kj(f"{S_}LowerLeg"), ej(f"{S_}UpLeg"), ej(f"{S_}Leg"), Rh)
    Rk = seg(f"{S_}LowerLeg", kj(f"{S_}LowerLeg"), kj(f"{S_}Foot"), ej(f"{S_}Leg"), ej(f"{S_}Foot"), Rt)
    # foot: no rotation (flat sneakers); translate the ankle onto the target ankle, close the floor gap in sole_fix
    fk, fe = kj(f"{S_}Foot"), ej(f"{S_}Foot")
    M[f"{S_}Foot"] = affine(fe, I3, fk); ROT[f"{S_}Foot"] = I3
    M[f"{S_}ToeBase"] = M[f"{S_}Foot"]; ROT[f"{S_}ToeBase"] = I3
    INFO[f"{S_}Foot"] = {"gap": round(float(fe[2] - fk[2]), 3)}

MAPPED = set(M)
def resolve(bone):
    """every other Karin bone: rigid follow of its nearest mapped ancestor, attached at the mapped position"""
    if bone.name in M: return
    p = bone.parent
    if p is None:
        M[bone.name] = np.eye(4); ROT[bone.name] = I3; return
    resolve(p)
    c = kj(bone.name); Mp = M[p.name]
    M[bone.name] = affine(Mp[:3, :3] @ c + Mp[:3, 3], ROT[p.name], c); ROT[bone.name] = ROT[p.name]
for bone in k_arm.data.bones:
    resolve(bone)
REPORT["segments"] = INFO

# ---------------------------------------------------------------- deform Karin meshes (LBS with M)
def vgroups(obj):
    names = {g.index: g.name for g in obj.vertex_groups}
    return [[(names[g.group], g.weight) for g in v.groups if g.weight > 1e-6] for v in obj.data.vertices]

# author's saved state (RE4 Karin_Original SOP): these kisekae keys are 1 on body_2
BAKE_KEYS = {"body_2": {"kisekae_Shoulder", "kisekae_UpperArm", "kisekae_Elbow", "kisekae_LowerArm", "kisekae_Chest 2",
                        "kisekae_Knee", "kisekae_LowerLeg 1", "kisekae_LowerLeg 2", "kisekae_Ankle", "kisekae_Foot",
                        "kisekae_Toe"}}
KEEP_KEYS = {"Body"}   # the face keeps its shape keys (expressions, M3); everything else is baked to the basis

SOLE_BAND = 3.0
FOOT_BONES = {"LeftFoot", "RightFoot", "LeftToeBase", "RightToeBase", "Shoes_tag_L", "Shoes_tag_R",
              "Shoes_tag_L_end", "Shoes_tag_R_end"}
def sole_fix(rows, out):
    gap = INFO["LeftFoot"]["gap"]
    for i, row in enumerate(rows):
        tot = sum(w for _, w in row) or 1.0
        f = sum(w for n, w in row if n in FOOT_BONES) / tot
        if f <= 0: continue
        h = out[i][2]
        if h < gap + SOLE_BAND:
            u = min(max((h - gap) / SOLE_BAND, 0.0), 1.0)
            out[i][2] = h - f * gap * (1.0 - u)
    return out

def lbs(rows, co):
    out = np.zeros_like(co)
    for i, row in enumerate(rows):
        tot = sum(w for _, w in row)
        if tot <= 0:
            out[i] = co[i]; continue
        acc = np.zeros(3)
        for n, w in row:
            Mi = M.get(n, np.eye(4))
            acc += (w / tot) * (Mi[:3, :3] @ co[i] + Mi[:3, 3])
        out[i] = acc
    return out

def deform(obj):
    me = obj.data
    W = Gn @ np.array(obj.matrix_world)
    to_t = lambda a: (np.c_[a, np.ones(len(a))] @ W.T)[:, :3]
    rows = vgroups(obj)
    for i, row in enumerate(rows):
        if not row: REPORT["warnings"].append(f"unweighted vertex {obj.name}:{i}")
    keys = {}
    if me.shape_keys:
        kb = me.shape_keys.key_blocks
        basis = np.array([list(p.co) for p in kb[0].data])
        if obj.name in KEEP_KEYS:   # deform every key with the same skinning so the deltas stay consistent
            for key in kb[1:]:
                keys[key.name] = np.array([list(p.co) for p in key.data])
            base = basis
        else:
            base = basis.copy()
            for key in kb[1:]:
                if key.name in BAKE_KEYS.get(obj.name, ()):
                    base += np.array([list(p.co) for p in key.data]) - basis
                    REPORT.setdefault("baked_keys", []).append(f"{obj.name}:{key.name}")
        obj.shape_key_clear()
    else:
        base = np.array([list(v.co) for v in me.vertices])
    out = sole_fix(rows, lbs(rows, to_t(base)))
    obj.matrix_world = Matrix.Identity(4)
    for v, p in zip(me.vertices, out):
        v.co = Vector(p)
    if keys:
        obj.shape_key_add(name="Basis", from_mix=False)
        for kname, kco in keys.items():
            kout = lbs(rows, to_t(kco))
            sk = obj.shape_key_add(name=kname, from_mix=False)
            sk.data.foreach_set("co", kout.ravel())
        REPORT.setdefault("kept_keys", {})[obj.name] = len(keys)
    me.update()
    return rows, out

# ---------------------------------------------------------------- weight remap to target bones
EXTRA_PREFIX = "KO_"
SECONDARY_ROOTS = ["Skirt_", "Tail", "Ribbon_hand_", "Hair_", "Ribbon_L", "Ribbon_R", "Ear_", "Ribbon_tops_",
                   "Ribbon_camisole"]
NOT_SECONDARY = {"Hair_front_root", "Skirt_root", "Ribbon_hand_L_root", "Ribbon_hand_R_root"}
def is_secondary(n):
    return n not in NOT_SECONDARY and any(n.startswith(p) for p in SECONDARY_ROOTS)

BASE = {"Hips": PELVIS, "LeftEye": "Head", "RightEye": "Head", "Head": "Head"}
for S_ in ("Left", "Right"):
    BASE.update({f"{S_}Shoulder": f"{S_}Shoulder", f"{S_}Hand": f"{S_}Hand", f"{S_}Foot": f"{S_}Foot",
                 f"{S_}ToeBase": f"{S_}ToeBase"})
    for fk, fe in FINGERS:
        for p, i in zip(PARTS, (1, 2, 3)):
            BASE[f"{S_}{fk}{p}"] = f"{S_}{fe}{i}"

def tparam(p, a, b):
    d = b - a
    return float(np.dot(p - a, d) / max(np.dot(d, d), 1e-9))
def stations(t, st):
    """piecewise-linear weights along stations [(t, bone), ...] sorted by t"""
    if t <= st[0][0]: return {st[0][1]: 1.0}
    for (t0, b0), (t1, b1) in zip(st, st[1:]):
        if t <= t1:
            u = (t - t0) / max(t1 - t0, 1e-9)
            r = {}
            r[b0] = r.get(b0, 0) + 1 - u; r[b1] = r.get(b1, 0) + u
            return r
    return {st[-1][1]: 1.0}

SPINE = ["spine", "spine1", "spine2", "spine3", "spine4"]
def spine_split(p):
    a, b = ej(PELVIS), ej("Neck")
    st = [(0.0, PELVIS)] + [(tparam(ej(n), a, b), n) for n in SPINE] + [(1.0, SPINE[-1])]
    return stations(tparam(p, a, b), st)
def neck_split(p):
    a, b = ej("Neck"), ej("Head")
    return stations(tparam(p, a, b), [(0.0, "Neck"), (tparam(ej("Neck1"), a, b), "Neck1"), (1.0, "Head")])
def limb_split(kname, p):
    for S_ in ("Left", "Right"):
        if kname == f"{S_}UpperArm": return {f"{S_}Arm": 1.0}
        if kname == f"{S_}LowerArm": return {f"{S_}ForeArm": 1.0}
        if kname == f"{S_}UpperLeg": return {f"{S_}UpLeg": 1.0}
        if kname == f"{S_}LowerLeg": return {f"{S_}Leg": 1.0}
    return None

def mapped_ancestor(n):
    bone = KB[n]
    while bone is not None and bone.name not in MAPPED:
        bone = bone.parent
    return bone.name if bone else "Hips"

def target_groups(kname, p):
    if kname in ("Hips", "Spine", "Chest"):
        return spine_split(p)
    if kname == "Neck":
        return neck_split(p)
    ls = limb_split(kname, p)
    if ls: return ls
    if kname in BASE: return {BASE[kname]: 1.0}
    if is_secondary(kname) and VARIANT == "B":
        return {EXTRA_PREFIX + kname: 1.0}
    return target_groups(mapped_ancestor(kname), p)

def remap(obj, rows, pos):
    for g in list(obj.vertex_groups):
        obj.vertex_groups.remove(g)
    acc = []
    for row, p in zip(rows, pos):
        tot = sum(w for _, w in row) or 1.0
        d = {}
        for n, w in row:
            for tb, f in target_groups(n, p).items():
                d[tb] = d.get(tb, 0.0) + w / tot * f
        items = sorted(d.items(), key=lambda kv: -kv[1])[:MAX_INF]
        s_ = sum(w for _, w in items) or 1.0
        acc.append([(n, w / s_) for n, w in items if w / s_ > 1e-4])
    groups = {}
    for i, row in enumerate(acc):
        for n, w in row:
            g = groups.get(n)
            if g is None:
                g = groups[n] = obj.vertex_groups.new(name=n)
            g.add([i], w, "REPLACE")
    return acc

mesh_stats = {}
for obj in k_meshes:
    rows, pos = deform(obj)
    acc = remap(obj, rows, pos)
    mesh_stats[obj.name] = {"verts": len(pos), "max_inf": max((len(r) for r in acc), default=0),
                            "bbox": [pos.min(0).round(2).tolist(), pos.max(0).round(2).tolist()]}
REPORT["meshes"] = mesh_stats

# ---------------------------------------------------------------- extra bones (variant B)
EXTRA_BONES = {}
if VARIANT == "B":
    bpy.ops.object.select_all(action="DESELECT")
    t_arm.select_set(True)
    bpy.context.view_layer.objects.active = t_arm
    bpy.ops.object.mode_set(mode="EDIT")
    eb = t_arm.data.edit_bones
    def target_parent_of(kname):
        anc = KB[kname].parent
        while anc is not None and not is_secondary(anc.name) and anc.name not in MAPPED:
            anc = anc.parent
        if anc is None: return PELVIS
        if is_secondary(anc.name): return EXTRA_PREFIX + anc.name
        g = target_groups(anc.name, kj(anc.name))
        return max(g.items(), key=lambda kv: kv[1])[0]
    order = sorted((b for b in k_arm.data.bones if is_secondary(b.name)), key=lambda b: len(b.parent_recursive))
    for kb in order:
        Mi = M[kb.name]
        h = Mi[:3, :3] @ kj(kb.name) + Mi[:3, 3]
        t = Mi[:3, :3] @ ktail(kb.name) + Mi[:3, 3]
        if np.linalg.norm(t - h) < 0.05: t = h + np.array([0, 0, 1.0])
        e = eb.new(EXTRA_PREFIX + kb.name)
        e.head = Vector(h); e.tail = Vector(t)
        e.parent = eb[target_parent_of(kb.name)]
        e.use_connect = False
        EXTRA_BONES[e.name] = e.parent.name
    bpy.ops.object.mode_set(mode="OBJECT")
REPORT["extra_bones"] = EXTRA_BONES

# ---------------------------------------------------------------- join, bind to the target armature
for o in list(bpy.data.objects):
    if o.type == "MESH" and o not in k_meshes:
        bpy.data.objects.remove(o, do_unlink=True)
bpy.ops.object.select_all(action="DESELECT")
for o in k_meshes: o.select_set(True)
bpy.context.view_layer.objects.active = next(o for o in k_meshes if o.name == "Body")
bpy.ops.object.join()
body = bpy.context.view_layer.objects.active
body.name = NAME; body.data.name = NAME
for m in list(body.modifiers): body.modifiers.remove(m)
body.parent = t_arm
mod = body.modifiers.new("Armature", "ARMATURE"); mod.object = t_arm
bpy.data.objects.remove(k_arm, do_unlink=True)

bones = set(b.name for b in t_arm.data.bones)
REPORT["groups_not_bones"] = [g.name for g in body.vertex_groups if g.name not in bones]
REPORT["used_groups"] = sorted(g.name for g in body.vertex_groups)

# materials: final material-instance names; Hair_Transparent shares the hair texture -> merged into the hair slot
MAT_RENAME = {"Karin_Face": "MI_Karin_Face", "Karin_Alpha": "MI_Karin_Alpha", "Karin_Body": "MI_Karin_Body",
              "Karin_Hair": "MI_Karin_Hair", "Karin_Hair_Transparent": "MI_Karin_HairTrans", "Karin_Costume": "MI_Karin_Costume"}
for slot in body.material_slots:
    if slot.material and slot.material.name in MAT_RENAME:
        slot.material.name = MAT_RENAME[slot.material.name]
import bmesh
slot_index = {s_.material.name: i for i, s_ in enumerate(body.material_slots) if s_.material}
bm = bmesh.new(); bm.from_mesh(body.data)
for f in bm.faces:
    if f.material_index == slot_index.get("MI_Karin_HairTrans", -1):
        f.material_index = slot_index["MI_Karin_Hair"]
bm.to_mesh(body.data); bm.free()
bpy.context.view_layer.objects.active = body
for i, s_ in enumerate(body.material_slots):
    if s_.material and s_.material.name == "MI_Karin_HairTrans":
        body.active_material_index = i
        bpy.ops.object.material_slot_remove()
        break
REPORT["materials"] = [s_.material.name for s_ in body.material_slots]

# textures referenced by the materials
texdir = os.path.join(RUN, "textures"); os.makedirs(texdir, exist_ok=True)
tex = {}
for mat in bpy.data.materials:
    if not mat.use_nodes: continue
    for n in mat.node_tree.nodes:
        if n.type == "TEX_IMAGE" and n.image:
            img = n.image
            fn = bpy.path.clean_name(img.name) + ".png"
            path = os.path.join(texdir, fn)
            if not os.path.exists(path):
                img.filepath_raw = path; img.file_format = "PNG"
                try: img.save()
                except Exception as ex: REPORT["warnings"].append(f"texture save {img.name}: {ex}")
            links = [l.to_socket.name + "@" + l.to_node.name for l in mat.node_tree.links if l.from_node == n]
            tex.setdefault(mat.name, []).append({"image": fn, "size": list(img.size), "links": links})
REPORT["textures"] = tex

# ---------------------------------------------------------------- export FBX
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(RUN, "build.blend"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fbx_common import export_for_ue411
fbx = os.path.join(RUN, NAME + ".fbx")
export_for_ue411(t_arm, [body], fbx, NAME)
with open(os.path.join(RUN, "report.json"), "w", encoding="utf-8") as f:
    json.dump(REPORT, f, indent=1, ensure_ascii=False)
print("BUILD_OK", fbx)
