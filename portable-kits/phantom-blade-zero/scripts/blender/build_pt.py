# Build Karin_PicodraTech for Phantom Blade Zero (Blender 4.2 background). Fork of build_pbz.py (Karin_Original): same
# skeleton contract, face morphs, two-face setup and exports; the source is Karin_PT_Unified_Atlas.blend (10 meshes
# merged per material on 4 x 4096 atlases, one 237-bone rig) and the cloth sections are this outfit's.
#
# Usage:
#   blender --background --factory-startup --python build_pt.py -- <run_dir> [--scale 1.37] [--variant adult|young]
#
# The rig's bones are renamed to Karin_Original's (VRM 1.0 humanoid names: LeftUpperLeg, ...) so the joint fitting is
# shared; shape keys the blend has switched on (Hair_tail_volume_up, Ahoge_big, Foot_OFF, Toe_OFF) are baked.
# Scale 1.37 = 1.30 (Karin_Original) x the eye height ratio (Original 1.0994 m / PicodraTech 1.0415 m).
#
# Output in <run_dir>:
#   Karin_Leader.fbx  -> Hun_Invs        (invisible leader mesh, every skeleton bone; sets the proportions animations retarget to)
#   Karin_Body.fbx    -> Hun_Body_Simple (body, outfit, hair, ears, tail; cloth sections for the physics)
#   Karin_Head.fbx    -> Hun_Head_New    (face; morph targets named after MetaHuman CTRL_expressions_* curves; adult:
#                                         a hidden first section, see face_slot0, and shown only by KarinFaceShow)
#   Karin_Face.fbx    -> Hun_BrowLashCard (adult: the same face, plain; see face_show)
#   Empty.fbx         -> Hun_Cloth / Hun_Scarf / Hun_Hair_Band / Hun_BrowLashCard (one hidden triangle)
#   Hat_Empty.fbx     -> Hats/Hun_Hat_00 (one hidden triangle on Hun_Hat_Skeleton)
#   cloth.json, cloth_collision.json -> Chaos cloth sections and their collision capsules (ue_cloth.py)
#   materials.json    -> material slot -> base color texture and kind (ue_import_pt.py)
#   textures/*.png, report.json, build.blend
#
# Skeleton contract (Hun_Skin_Skeleton): translation retargeting is AnimationScaled for the body and the chain bones
# (direction from the animation, length from the mesh), Animation for hands/fingers/IK (vanilla offsets), Skeleton for
# the balls. So every bind joint is parent + vanilla direction * length, with Karin's length where a Karin joint maps,
# the vanilla offset for Animation bones and a scaled vanilla offset for helpers. Bind orientations stay vanilla
# (animations carry absolute local rotations); the mesh is re-posed onto that skeleton by per-region rigid transforms.
# The game animates every chain bone, so chain roots stay on their vanilla ray; the RigidBody node simulates the rest.
import bpy, sys, os, json, math, collections
import numpy as np
from mathutils import Matrix, Vector, Quaternion

argv = sys.argv[sys.argv.index("--") + 1:]
RUN = os.path.abspath(argv[0])
SCALE = float(argv[argv.index("--scale") + 1]) if "--scale" in argv else 1.37
VARIANT = argv[argv.index("--variant") + 1] if "--variant" in argv else "adult"
# adult = Hun (BP_Renewal_Hun, leader Hun_Body_Simple, AnimationScaled; its chain bones stay unused, see chains);
# young = Young Hun of the prologue (BP_Renewal_Hun_Young, leader Hun_Young_Body, every bone Animation-retargeted, no chain bones)
VCFG = {
    "adult": dict(uemodel="ue/Hun_Invs.uemodel", skel="c/Hun_Skin_Skeleton.Hun_Skin_Skeleton.skel.json",
                  ref="g/Hun_Invs.Hun_Invs.skel.json", body="c/Hun_Body_Simple.Hun_Body_Simple.skel.json",
                  chains=False, leader=True, cloth=True, face_in_body=False, face_fbx="Karin_Head", face_slot0=True, face_show=True, suffix=""),
    "young": dict(uemodel="ue/Hun_Young_Skeleton.uemodel", skel="y/Hun_Young_Skeleton.Hun_Young_Skeleton.skel.json",
                  ref="y/Hun_Young_Body.Hun_Young_Body.skel.json", body="y/Hun_Young_Body.Hun_Young_Body.skel.json",
                  chains=False, leader=False, cloth=True, face_in_body=False, face_fbx="Karin_Head", face_slot0=False, face_show=False, suffix="_Young"),
}[VARIANT]
def _need(name, what):
    v = os.environ.get(name)
    if not v: raise SystemExit(f"set {name}: {what}")
    return v
WORK = _need("PBZ_WORK", "folder with the vanilla dumps (ue/*.uemodel, c/ g/ y/ *.skel.json), see BUILD_PIPELINE.md")
KARIN_BLEND = _need("PBZ_SOURCE_BLEND", "Karin_PT_Unified_Atlas.blend (its textures/ folder next to it)")
UF_ADDONS = os.environ.get("PBZ_BLENDER_ADDONS", "")   # folder holding io_scene_ueformat when the addon is not installed
os.makedirs(RUN, exist_ok=True)
REPORT = {"scale": SCALE, "variant": VARIANT, "warnings": []}

bpy.ops.wm.read_factory_settings(use_empty=True)
import addon_utils
if not addon_utils.enable("io_scene_ueformat", default_set=True):
    sys.path.insert(0, UF_ADDONS)
    import io_scene_ueformat
    io_scene_ueformat.register()
addon_utils.enable("io_scene_fbx", default_set=True)

def import_uemodel(path):
    s = bpy.context.scene.uf_settings
    s.scale_factor = 1.0; s.import_sockets = False; s.import_morph_targets = False
    before = set(bpy.data.objects)
    bpy.ops.uf.import_uemodel(filepath=path, files=[{"name": os.path.basename(path)}], directory=os.path.dirname(path))
    return [o for o in bpy.data.objects if o not in before]

def norm(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-9 else v

# ---------------------------------------------------------------- vanilla skeleton (Blender = UE with Y negated)
v_objs = import_uemodel(os.path.join(WORK, VCFG["uemodel"]))
v_arm = next(o for o in v_objs if o.type == "ARMATURE")
for o in v_objs:
    if o.type == "MESH": bpy.data.objects.remove(o, do_unlink=True)
# Bones of the vanilla body that the vanilla leader model lacks: weapon_l/r_child and ik_weapon_l/r_child (identity
# children of the weapon bones). The body is the gameplay leader, and without them the 醉剑 weapon lost its model and
# its hits. Added on their parents so the body keeps every vanilla bone; the leader mesh keeps the vanilla set.
_vbody = json.load(open(os.path.join(WORK, VCFG["body"]), encoding="utf-8"))["bones"]
_have = {b.name.lower() for b in v_arm.data.bones}
EXTRA = []
for b in _vbody:
    if b["name"].lower() in _have or b["parent"] < 0: continue
    assert np.abs(b["t"]).max() < 1e-3 and abs(abs(b["q"][3]) - 1.0) < 1e-6, "non-identity extra bone " + b["name"]
    EXTRA.append((b["name"], _vbody[b["parent"]]["name"]))
if EXTRA:
    bpy.ops.object.select_all(action="DESELECT")
    v_arm.select_set(True); bpy.context.view_layer.objects.active = v_arm
    bpy.ops.object.mode_set(mode="EDIT")
    eb = {e.name.lower(): e for e in v_arm.data.edit_bones}
    for n, p in EXTRA:
        pe = eb[p.lower()]
        e = v_arm.data.edit_bones.new(n)
        e.head = pe.head.copy(); e.tail = pe.tail.copy(); e.roll = pe.roll; e.parent = pe
        eb[n.lower()] = e
    bpy.ops.object.mode_set(mode="OBJECT")
EXTRA = [n for n, _ in EXTRA]
REPORT["body_bones_added"] = EXTRA
VM = {b.name: (v_arm.matrix_world @ b.matrix_local) for b in v_arm.data.bones}
VPAR = {b.name: (b.parent.name if b.parent else None) for b in v_arm.data.bones}
ORDER = [b.name for b in v_arm.data.bones]                      # parents first
LOW = {n.lower(): n for n in ORDER}
def V(n): return LOW[n.lower()]                                  # exact vanilla spelling
def vp(n): return np.array(VM[V(n)].translation)
SK = json.load(open(os.path.join(WORK, VCFG["skel"]), encoding="utf-8"))
RT = {b["name"].lower(): b["retarget"] for b in SK["bones"]}
INVS = json.load(open(os.path.join(WORK, VCFG["ref"]), encoding="utf-8"))["bones"]
SKQ = {b["name"].lower(): b["q"] for b in INVS}
SKP = {b["name"].lower(): (INVS[b["parent"]]["name"].lower() if b["parent"] >= 0 else None) for b in INVS}
BODY_SET = [b["name"] for b in json.load(open(os.path.join(WORK, VCFG["body"]), encoding="utf-8"))["bones"]]
BODY_BONES = [V(n) for n in BODY_SET if n.lower() in LOW]
REPORT["body_bones"] = len(BODY_BONES)

# ---------------------------------------------------------------- Karin
# The blend's meshes are merged per material and get their role as name; "Body" stays the face (the face code's name).
# Body.010 (Karin_Alpha, the face overlay) is not loaded: build_pbz.py drops those faces too.
ROLE = {"Body": "hair",          # Hair + Karin_Hair_Transparent: hair, twin tails, bangs, ears, tail
        "Body.001": "clothB",    # ClothB_Blue: jacket, shoes, headphones and cords, halo, leg ring, tail ribbons, ear covers
        "Body.002": "costume", "Body.003": "skin", "Body.005": "kcostume",   # hair ribbons
        "Body.006": "clothA",    # ClothA_Blue: inner, shorts, socks, arm covers, belt strap, leg ribbon
        "Body.007": "metal", "Body.008": "costume1", "Body.009": "Body"}
with bpy.data.libraries.load(KARIN_BLEND, link=False) as (src, dst):
    dst.objects = [n for n in src.objects if n == "Karin_PT_Armature" or n in ROLE]
k_objs = [o for o in dst.objects if o]
for o in k_objs:
    bpy.context.scene.collection.objects.link(o)
    o.name = "_pt_" + o.name
for o in k_objs:
    if o.type == "MESH": o.name = ROLE[o.name[4:]]
k_arm = next(o for o in k_objs if o.type == "ARMATURE")
k_arm.name = "KarinArmature"; k_arm.data.name = "KarinArmature"
# rig -> Karin_Original (VRM 1.0) names; renaming a bone renames the vertex groups of the meshes deformed by it
BONE_RENAME = {"Eye.L": "LeftEye", "Eye.R": "RightEye", "Toes.L": "LeftToeBase", "Toes.R": "RightToeBase"}
for s, S in ((".L", "Left"), (".R", "Right")):
    for n in ("Shoulder", "UpperArm", "LowerArm", "Hand", "UpperLeg", "LowerLeg", "Foot"):
        BONE_RENAME[n + s] = S + n
    for f in ("Thumb", "Index", "Middle", "Ring", "Little"):
        for seg in ("Proximal", "Intermediate", "Distal"):
            BONE_RENAME[f + seg + s] = S + f + seg
for b in k_arm.data.bones:
    if b.name in BONE_RENAME: b.name = BONE_RENAME[b.name]
BODY_MESHES = ["skin", "hair", "clothA", "clothB", "costume", "kcostume", "metal", "costume1"]
HEAD_MESHES = ["Body"]
k_meshes = {o.name: o for o in k_objs if o.type == "MESH"}
REPORT["uv_maps"] = {n: [u.name for u in o.data.uv_layers] for n, o in k_meshes.items()}
for o in k_meshes.values():   # one UV map, one name: the join merges maps by name and UE samples channel 0
    uvs = o.data.uv_layers
    while len(uvs) > 1: uvs.remove(uvs[-1])
    uvs[0].name = "UVMap"
assert sorted(k_meshes) == sorted(BODY_MESHES + HEAD_MESHES), sorted(k_meshes)
_bones = set(b.name for b in k_arm.data.bones)
REPORT["groups_not_rig_bones"] = {n: [g.name for g in o.vertex_groups if g.name not in _bones] for n, o in k_meshes.items()}
G = Matrix.Scale(100.0 * SCALE, 4)   # both face -Y in Blender; metres -> cm
Gn = np.array(G)
KB = {b.name: b for b in k_arm.data.bones}
def kp(n): return np.array(G @ (k_arm.matrix_world @ KB[n].head_local))
def ktail(n): return np.array(G @ (k_arm.matrix_world @ KB[n].tail_local))

def swing(a, b):
    q = Vector(norm(a)).rotation_difference(Vector(norm(b)))
    return np.array(q.to_matrix())
def rigid(R, src, dst):
    M = np.eye(4); M[:3, :3] = R; M[:3, 3] = dst - R @ src
    return M
def apply(M, p): return M[:3, :3] @ p + M[:3, 3]
def ue(p): return np.array([p[0], -p[1], p[2]])   # UE component space = Blender with Y negated

# ---------------------------------------------------------------- joint correspondence (vanilla name -> Karin bone)
KMAP = {"neck_01": "Neck", "head": "Head", "eye_l_root": "LeftEye", "eye_r_root": "RightEye"}
for s, S in (("l", "Left"), ("r", "Right")):
    KMAP.update({f"clavicle_{s}": f"{S}Shoulder", f"upperarm_{s}": f"{S}UpperArm", f"lowerarm_{s}": f"{S}LowerArm",
                 f"hand_{s}": f"{S}Hand", f"thigh_{s}": f"{S}UpperLeg", f"calf_{s}": f"{S}LowerLeg", f"foot_{s}": f"{S}Foot",
                 f"ball_{s}": f"{S}ToeBase"})
    for pf, kf in (("thumb", "Thumb"), ("index", "Index"), ("middle", "Middle"), ("ring", "Ring"), ("pinky", "Little")):
        for i, seg in enumerate(("Proximal", "Intermediate", "Distal")):
            KMAP[f"{pf}_0{i + 1}_{s}"] = f"{S}{kf}{seg}"
KMAP = {V(k): v for k, v in KMAP.items()}
INV = {v: k for k, v in KMAP.items()}
# main child of each mapped segment (direction the mesh region is swung onto)
SEGCHILD = {"neck_01": "head"}
for s in "lr":
    SEGCHILD.update({f"clavicle_{s}": f"upperarm_{s}", f"upperarm_{s}": f"lowerarm_{s}", f"lowerarm_{s}": f"hand_{s}",
                     f"hand_{s}": f"middle_01_{s}", f"thigh_{s}": f"calf_{s}", f"calf_{s}": f"foot_{s}", f"foot_{s}": f"ball_{s}"})
    for pf in ("thumb", "index", "middle", "ring", "pinky"):
        SEGCHILD[f"{pf}_01_{s}"] = f"{pf}_02_{s}"; SEGCHILD[f"{pf}_02_{s}"] = f"{pf}_03_{s}"
SEGCHILD = {V(a): V(b) for a, b in SEGCHILD.items()}

# ---------------------------------------------------------------- new bind joints
P0 = (kp("LeftUpperLeg") + kp("RightUpperLeg")) / 2.0      # pelvis at the hip joints (vanilla thighs are lateral)
P0[0] = 0.0
TORSO = [V(n) for n in ("spine_01", "spine_02", "spine_03", "spine_04", "spine_05", "neck_01")]
r_torso = np.linalg.norm(kp("Neck") - P0) / max(np.linalg.norm(vp("neck_01") - vp("pelvis")), 1e-6)
r_neck = np.linalg.norm(kp("Head") - kp("Neck")) / max(np.linalg.norm(vp("head") - vp("neck_01")), 1e-6)
NEW, RATIO, LEN = {}, {}, {}
KM = {}   # Karin bone -> 4x4 region transform (filled lazily while joints are placed)

def offset(n):
    p = VPAR[n]
    return vp(n) - vp(p)

def place(n):
    p = VPAR[n]
    if p is None:
        NEW[n] = vp(n); RATIO[n] = 1.0; return
    off = offset(n); vlen = np.linalg.norm(off); vdir = norm(off)
    mode = RT.get(n.lower(), "AnimationScaled")
    if mode == "Animation":
        NEW[n] = NEW[p] + off
    elif n == V("pelvis"):
        NEW[n] = P0.copy()
    elif n in TORSO:
        NEW[n] = NEW[p] + vdir * vlen * r_torso
    elif n in (V("neck_02"), V("head")):
        NEW[n] = NEW[p] + vdir * vlen * r_neck
    elif n in LEN:
        NEW[n] = NEW[p] + vdir * LEN[n]
    else:
        NEW[n] = NEW[p] + vdir * vlen * RATIO.get(p, 1.0)
    # length ratio inherited by helper children: the bone's own mapped segment if it has one, else the parent's
    RATIO[n] = RATIO.get(p, 1.0)
    if n == V("pelvis"): RATIO[n] = r_torso
    if n in TORSO: RATIO[n] = r_torso
    if n in (V("neck_01"), V("neck_02"), V("head")): RATIO[n] = r_neck

def region(kname):
    """Rigid transform taking Karin bone kname's region into the new bind pose."""
    if kname in KM: return KM[kname]
    kb = KB[kname]
    if kname == "Hips":
        M = rigid(np.eye(3), P0, NEW[V("pelvis")])
    elif kname in ("Spine", "Chest"):
        # swing onto the new spine and stretch along it to its length (1 when the spine is AnimationScaled; the
        # Animation-retargeted young spine keeps the vanilla length, which would otherwise all end up in the neck)
        a, b = kp("Neck") - P0, NEW[V("neck_01")] - NEW[V("pelvis")]
        R = swing(a, b)
        S = np.eye(3) + (np.linalg.norm(b) / np.linalg.norm(a) - 1.0) * np.outer(norm(a), norm(a))
        M = np.eye(4); M[:3, :3] = R @ S; M[:3, 3] = NEW[V("pelvis")] - R @ S @ P0
    elif kname in ("LeftEye", "RightEye"):
        M = region(kb.parent.name)   # the eyes stay in Karin's face (the vanilla eye roots sit elsewhere in the head)
    elif kname == "Head" and RT.get(V("head").lower()) == "Animation":
        M = region(kb.parent.name)   # vanilla neck length is fixed: keep Karin's, the head pivots a little above it
    elif kname in INV and INV[kname] in NEW:
        n = INV[kname]
        c = SEGCHILD.get(n)
        if c is not None and c in KMAP and c in NEW:
            R = swing(kp(KMAP[c]) - kp(kname), NEW[c] - NEW[n])
        elif kb.parent is not None:
            R = region(kb.parent.name)[:3, :3]
        else:
            R = np.eye(3)
        M = rigid(R, kp(kname), NEW[n])
    elif kb.parent is not None:
        M = region(kb.parent.name)
    else:
        M = np.eye(4)
    KM[kname] = M
    return M

def proj_len(n, target):
    """Length along n's vanilla direction from its new parent that comes closest to target."""
    p = VPAR[n]
    return max(float(np.dot(target - NEW[p], norm(offset(n)))), 0.5)

# place in hierarchy order; branch joints that map to Karin get their length from Karin's joint carried by the
# already-placed parent region (projection onto the vanilla ray), segment joints get Karin's segment length.
for n in ORDER:
    p = VPAR[n]
    if p is not None and n in KMAP and RT.get(n.lower()) != "Animation" and n not in TORSO and n not in (V("neck_01"), V("head")):
        k = KMAP[n]
        kparent = KB[k].parent.name
        pn = INV.get(kparent)
        if pn is not None and pn == p and SEGCHILD.get(p) == n:
            LEN[n] = float(np.linalg.norm(kp(k) - kp(kparent)))          # segment continuation: Karin length
        else:
            # branch (clavicle from spine_05, thigh from pelvis, eye roots from head): Karin joint through its region
            KM.clear()
            LEN[n] = proj_len(n, apply(region(kparent), kp(k)))
    place(n)
KM.clear()
# bones whose own segment is mapped carry that segment's ratio for their helper children
for n, c in SEGCHILD.items():
    if n in NEW and c in NEW:
        vl = np.linalg.norm(vp(c) - vp(n))
        if vl > 1e-6: RATIO[n] = np.linalg.norm(NEW[c] - NEW[n]) / vl
for n in ORDER:   # second pass so helpers pick up the segment ratios
    if n not in KMAP and n not in TORSO and VPAR[n] is not None and RT.get(n.lower()) != "Animation" and n != V("pelvis") \
            and n not in (V("neck_02"), V("head")) and n not in LEN:
        p = VPAR[n]
        NEW[n] = NEW[p] + norm(offset(n)) * np.linalg.norm(offset(n)) * RATIO.get(p, 1.0)
    elif VPAR[n] is not None and RT.get(n.lower()) == "Animation":
        NEW[n] = NEW[VPAR[n]] + offset(n)
KM.clear()
for kb in k_arm.data.bones:
    region(kb.name)
REPORT["ratios"] = {"torso": round(float(r_torso), 3), "neck": round(float(r_neck), 3)}
REPORT["joint_mismatch_cm"] = {n: round(float(np.linalg.norm(apply(region(KB[k].parent.name), kp(k)) - NEW[n])), 2)
                               for n, k in KMAP.items() if KB[k].parent is not None}

# ---------------------------------------------------------------- chains
# No Karin bone maps to a game chain bone (build_pbz.py: the game poses them and stretched the hair and skirt): the
# chains are Chaos cloth on mesh sections or follow their parent region / the nearest skin (see the cloth sections).
def chain_of(head):
    names = [head]
    while KB[names[-1]].children:
        kids = [c for c in KB[names[-1]].children if "_end" not in c.name]
        if not kids: break
        names.append(kids[0].name)
    return names
RENAME = {}        # Karin bone -> [(game bone, factor)]

# ---------------------------------------------------------------- mesh re-pose (LBS of the rigid region transforms)
def vgroups(obj):
    names = {g.index: g.name for g in obj.vertex_groups}
    return [[(names[g.group], g.weight) for g in v.groups if g.weight > 1e-6] for v in obj.data.vertices]

# shape keys the blend has switched on are baked at their value (keys of the merged meshes are not muted; 336 each)

def lbs(rows, co):
    out = np.zeros_like(co)
    for i, row in enumerate(rows):
        tot = sum(w for _, w in row)
        if tot <= 0:
            out[i] = co[i]; continue
        acc = np.zeros(3)
        for n, w in row:
            Mi = KM.get(n, np.eye(4))
            acc += (w / tot) * (Mi[:3, :3] @ co[i] + Mi[:3, 3])
        out[i] = acc
    return out

def deform(obj, keep_keys):
    me = obj.data
    W = np.array(obj.matrix_world)
    T = Gn @ W
    rows = vgroups(obj)
    def to_cm(a): return (np.c_[a, np.ones(len(a))] @ T.T)[:, :3]
    kept = {}
    if me.shape_keys:
        kb = me.shape_keys.key_blocks
        def kco(key):
            a = np.zeros(len(me.vertices) * 3); key.data.foreach_get("co", a)
            return a.reshape(-1, 3)
        basis = kco(kb[0])
        mix = basis.copy()
        for key in kb[1:]:
            if key.name in keep_keys:
                kept[key.name] = kco(key) - basis
            elif abs(key.value) > 1e-4 and not key.mute:
                assert key.relative_key == kb[0], key.name
                mix += (kco(key) - basis) * key.value
                REPORT.setdefault("baked_keys", []).append(f"{obj.name}:{key.name}={key.value:.2f}")
        base = mix
        obj.shape_key_clear()
    else:
        base = np.array([list(v.co) for v in me.vertices])
    co = to_cm(base)
    out = lbs(rows, co)
    obj.matrix_world = Matrix.Identity(4)
    for v, p in zip(me.vertices, out):
        v.co = Vector(p)
    me.update()
    deltas = {}
    for name, d in kept.items():
        moved = lbs(rows, to_cm(base + d))
        deltas[name] = moved - out
    return rows, deltas

# ---------------------------------------------------------------- face morphs named after MetaHuman control curves
# curve -> {Karin key: weight}. "|L" / "|R" restrict the key to the character's left (+X) / right (-X) half;
# "|UL" etc. also split upper/lower lip at the mouth centre.
FACE = {
    "CTRL_expressions_eyeBlinkL": {"blink_L": 1.0},
    "CTRL_expressions_eyeBlinkR": {"blink_R": 1.0},
    "CTRL_expressions_eyeSquintInnerL": {"LowerEyelid_up_L": 0.6},
    "CTRL_expressions_eyeSquintInnerR": {"LowerEyelid_up_R": 0.6},
    "CTRL_expressions_eyeCheekRaiseL": {"smile|L": 0.5},
    "CTRL_expressions_eyeCheekRaiseR": {"smile|R": 0.5},
    "CTRL_expressions_eyeWidenL": {"surprise_L": 0.7},
    "CTRL_expressions_eyeWidenR": {"surprise_R": 0.7},
    "CTRL_expressions_eyeLookUpL": {"LookUp|L": 1.0}, "CTRL_expressions_eyeLookUpR": {"LookUp|R": 1.0},
    "CTRL_expressions_eyeLookDownL": {"LookDown|L": 1.0}, "CTRL_expressions_eyeLookDownR": {"LookDown|R": 1.0},
    "CTRL_expressions_eyeLookLeftL": {"LookLeft|L": 1.0}, "CTRL_expressions_eyeLookLeftR": {"LookLeft|R": 1.0},
    "CTRL_expressions_eyeLookRightL": {"LookRight|L": 1.0}, "CTRL_expressions_eyeLookRightR": {"LookRight|R": 1.0},
    "CTRL_expressions_browDownL": {"mayu_angry_1_L": 0.6, "mayu_down_L": 0.4},
    "CTRL_expressions_browDownR": {"mayu_angry_1_R": 0.6, "mayu_down_R": 0.4},
    "CTRL_expressions_browLateralL": {"mayu_serious_L": 0.6},
    "CTRL_expressions_browLateralR": {"mayu_serious_R": 0.6},
    "CTRL_expressions_browRaiseInL": {"mayu_sad_1_L": 1.0},
    "CTRL_expressions_browRaiseInR": {"mayu_sad_1_R": 1.0},
    "CTRL_expressions_browRaiseOuterL": {"mayu_up_L": 1.0},
    "CTRL_expressions_browRaiseOuterR": {"mayu_up_R": 1.0},
    "CTRL_expressions_jawOpen": {"kuchi_A": 1.0},
    "CTRL_expressions_mouthCornerPullL": {"kuchi_smile_1_L": 1.0},
    "CTRL_expressions_mouthCornerPullR": {"kuchi_smile_1_R": 1.0},
    "CTRL_expressions_mouthCornerDepressL": {"kuchi_angry_1_L": 0.7},
    "CTRL_expressions_mouthCornerDepressR": {"kuchi_angry_1_R": 0.7},
    "CTRL_expressions_mouthStretchL": {"kuchi_I|L": 0.6},
    "CTRL_expressions_mouthStretchR": {"kuchi_I|R": 0.6},
    "CTRL_expressions_mouthFunnelUL": {"kuchi_O|L": 0.25}, "CTRL_expressions_mouthFunnelUR": {"kuchi_O|R": 0.25},
    "CTRL_expressions_mouthFunnelDL": {"kuchi_O|L": 0.25}, "CTRL_expressions_mouthFunnelDR": {"kuchi_O|R": 0.25},
    "CTRL_expressions_mouthLipsPurseUL": {"kuchi_U|L": 0.25}, "CTRL_expressions_mouthLipsPurseUR": {"kuchi_U|R": 0.25},
    "CTRL_expressions_mouthLipsPurseDL": {"kuchi_U|L": 0.25}, "CTRL_expressions_mouthLipsPurseDR": {"kuchi_U|R": 0.25},
    "CTRL_expressions_mouthUpperLipRaiseL": {"kuchi_E|L": 0.4}, "CTRL_expressions_mouthUpperLipRaiseR": {"kuchi_E|R": 0.4},
    "CTRL_expressions_mouthLowerLipDepressL": {"kuchi_E|L": 0.3}, "CTRL_expressions_mouthLowerLipDepressR": {"kuchi_E|R": 0.3},
}
# The game's lip-sync and gameplay emotion poses (Animation/SoundLip: dialogue lines, Pain, Outofbreath, Fear, ...) use
# ARKit blendshape curves per head part instead (head_jawopen, eyelashes_eyeblinkleft, ...), so the face also carries
# the head_* ARKit shapes Karin's keys can make (left = the character's left, as the CTRL curves).
ARKIT = {
    "head_eyeblinkleft": FACE["CTRL_expressions_eyeBlinkL"], "head_eyeblinkright": FACE["CTRL_expressions_eyeBlinkR"],
    "head_eyesquintleft": FACE["CTRL_expressions_eyeSquintInnerL"], "head_eyesquintright": FACE["CTRL_expressions_eyeSquintInnerR"],
    "head_eyewideleft": FACE["CTRL_expressions_eyeWidenL"], "head_eyewideright": FACE["CTRL_expressions_eyeWidenR"],
    "head_eyelookupleft": FACE["CTRL_expressions_eyeLookUpL"], "head_eyelookupright": FACE["CTRL_expressions_eyeLookUpR"],
    "head_eyelookdownleft": FACE["CTRL_expressions_eyeLookDownL"], "head_eyelookdownright": FACE["CTRL_expressions_eyeLookDownR"],
    "head_eyelookoutleft": FACE["CTRL_expressions_eyeLookLeftL"], "head_eyelookinleft": FACE["CTRL_expressions_eyeLookRightL"],
    "head_eyelookoutright": FACE["CTRL_expressions_eyeLookRightR"], "head_eyelookinright": FACE["CTRL_expressions_eyeLookLeftR"],
    "head_browdownleft": FACE["CTRL_expressions_browDownL"], "head_browdownright": FACE["CTRL_expressions_browDownR"],
    "head_browinnerup": {"mayu_sad_1_L": 1.0, "mayu_sad_1_R": 1.0},
    "head_browouterupleft": FACE["CTRL_expressions_browRaiseOuterL"], "head_browouterupright": FACE["CTRL_expressions_browRaiseOuterR"],
    "head_cheeksquintleft": FACE["CTRL_expressions_eyeCheekRaiseL"], "head_cheeksquintright": FACE["CTRL_expressions_eyeCheekRaiseR"],
    "head_jawopen": FACE["CTRL_expressions_jawOpen"],
    "head_mouthsmileleft": FACE["CTRL_expressions_mouthCornerPullL"], "head_mouthsmileright": FACE["CTRL_expressions_mouthCornerPullR"],
    "head_mouthfrownleft": FACE["CTRL_expressions_mouthCornerDepressL"], "head_mouthfrownright": FACE["CTRL_expressions_mouthCornerDepressR"],
    "head_mouthstretchleft": FACE["CTRL_expressions_mouthStretchL"], "head_mouthstretchright": FACE["CTRL_expressions_mouthStretchR"],
    "head_mouthfunnel": {"kuchi_O": 0.7}, "head_mouthpucker": {"kuchi_U": 0.7},
    "head_mouthupperupleft": FACE["CTRL_expressions_mouthUpperLipRaiseL"], "head_mouthupperupright": FACE["CTRL_expressions_mouthUpperLipRaiseR"],
    "head_mouthlowerdownleft": FACE["CTRL_expressions_mouthLowerLipDepressL"], "head_mouthlowerdownright": FACE["CTRL_expressions_mouthLowerLipDepressR"],
}
FACE.update(ARKIT)
need_keys = set(k.split("|")[0] for m in FACE.values() for k in m)
face = k_meshes["Body"]
face_keys = set(k.name for k in face.data.shape_keys.key_blocks) if face.data.shape_keys else set()
REPORT["missing_face_keys"] = sorted(need_keys - face_keys)
ROWS, DELTAS = {}, {}
for name, obj in k_meshes.items():
    rows, deltas = deform(obj, need_keys if name == "Body" else set())
    ROWS[name] = rows
    if deltas: DELTAS[name] = deltas

# ---------------------------------------------------------------- weights -> Hun bones
def smooth(x, a, b):
    t = np.clip((np.asarray(x, dtype=float) - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)
SPINE = [V(n) for n in ("spine_01", "spine_02", "spine_03", "spine_04", "spine_05")]
def spine_split(p):
    z = p[2]
    zs = [NEW[n][2] for n in SPINE[1:]]
    w = [1.0]
    for zz in zs:
        w.append(smooth(z, zz - 3.0, zz + 3.0))
    out = {}
    for i, n in enumerate(SPINE):
        nxt = w[i + 1] if i + 1 < len(w) else 0.0
        out[n] = w[i] - nxt
    return out
def neck_split(p):
    z = p[2]; zm = NEW[V("neck_02")][2]
    t = smooth(z, zm - 2.0, zm + 2.0)
    return {V("neck_01"): 1 - t, V("neck_02"): t}

DIRECT = {k: v for k, v in INV.items() if not v.startswith(("eye_",))}
DIRECT["Hips"] = V("pelvis")
DIRECT["LeftEye"] = V("head"); DIRECT["RightEye"] = V("head")
def target_of(kname):
    b = KB[kname]
    while b is not None:
        if b.name in RENAME: return RENAME[b.name]
        if b.name in ("Spine", "Chest"): return [("SPINE", 1.0)]
        if b.name == "Neck": return [("NECK", 1.0)]
        if b.name in DIRECT: return [(DIRECT[b.name], 1.0)]
        b = b.parent
    return [(V("pelvis"), 1.0)]

def remap(obj, rows):
    pos = np.array([list(v.co) for v in obj.data.vertices])
    acc_all = []
    for i, row in enumerate(rows):
        acc = collections.defaultdict(float)
        for n, w in row:
            for t, f in target_of(n):
                if t == "SPINE":
                    for b, ff in spine_split(pos[i]).items():
                        if ff > 0: acc[b] += w * f * ff
                elif t == "NECK":
                    for b, ff in neck_split(pos[i]).items():
                        if ff > 0: acc[b] += w * f * ff
                else:
                    acc[t] += w * f
        acc_all.append(top8(acc))
    write_groups(obj, acc_all)
    return acc_all
def top8(acc):
    items = sorted(acc.items(), key=lambda kv: -kv[1])[:8]
    tot = sum(w for _, w in items) or 1.0
    return [(n, w / tot) for n, w in items if w / tot > 1e-4]
def write_groups(obj, rows):
    for g in list(obj.vertex_groups):
        obj.vertex_groups.remove(g)
    groups = {}
    for i, row in enumerate(rows):
        for n, w in row:
            g = groups.get(n) or obj.vertex_groups.new(name=n)
            groups[n] = g
            g.add([i], w, "REPLACE")
WROWS = {}
for name, obj in k_meshes.items():
    WROWS[name] = remap(obj, ROWS[name])

# Accessories on chains that are not simulated and wrap a limb (the ribbon round the right calf, the left thigh ring,
# the belt strings) take the weights of the nearest skin verts (inverse-distance mean of 8) in proportion to their
# chain weight: by the chain's parent bone alone the ribbon round the calf would stay with the thigh when the knee bends.
FOLLOW = ("Leg_Ribbon", "Leg_Ring", "Belt_String", "Right_Belt")
def chain_frac(name, prefixes):
    return np.array([sum(w for n, w in row if n.startswith(prefixes)) / max(sum(w for _, w in row), 1e-9) for row in ROWS[name]])
def follow_skin(name, prefixes, src="skin"):
    obj = k_meshes[name]
    f = chain_frac(name, prefixes)
    ids = np.where(f > 0.01)[0]
    if len(ids) == 0: return 0
    sp = np.array([list(v.co) for v in obj.data.vertices])
    bp = np.array([list(v.co) for v in k_meshes[src].data.vertices])
    for i in ids:
        d = np.linalg.norm(bp - sp[i], axis=1)
        nn = np.argpartition(d, 8)[:8]
        iw = 1.0 / np.maximum(d[nn], 0.05); iw /= iw.sum()
        acc = collections.defaultdict(float)
        for n, w in WROWS[name][i]: acc[n] += (1.0 - f[i]) * w
        for j, wj in zip(nn, iw):
            for n, w in WROWS[src][j]: acc[n] += f[i] * wj * w
        WROWS[name][i] = top8(acc)
    write_groups(obj, WROWS[name])
    return int(len(ids))
REPORT["skin_follow"] = {n: follow_skin(n, FOLLOW) for n in ("clothA", "clothB")}

# ---------------------------------------------------------------- armatures (vanilla orientations, new joints)
def make_armature(name, keep):
    """Copy of the vanilla armature with only `keep` bones (parents first), heads moved to NEW."""
    a = v_arm.copy(); a.data = v_arm.data.copy(); a.name = name; a.data.name = name
    bpy.context.scene.collection.objects.link(a)
    bpy.ops.object.select_all(action="DESELECT")
    a.select_set(True); bpy.context.view_layer.objects.active = a
    bpy.ops.object.mode_set(mode="EDIT")
    eb = a.data.edit_bones
    keepset = set(keep)
    for b in list(eb):
        if b.name not in keepset:
            eb.remove(b)
    to_arm = a.matrix_world.inverted().to_3x3()
    for b in eb:
        d = Vector(NEW[b.name]) - Vector(VM[b.name].translation)
        d = to_arm @ d
        b.head = b.head + d; b.tail = b.tail + d
    bpy.ops.object.mode_set(mode="OBJECT")
    return a
def with_ancestors(names):
    out = set()
    for n in names:
        while n is not None and n not in out:
            out.add(n); n = VPAR[n]
    return [n for n in ORDER if n in out]

body_bones = with_ancestors(BODY_BONES + [b for b, _ in [x for r in RENAME.values() for x in r]])
head_bones = with_ancestors([V("head"), V("eye_l"), V("eye_r"), V("jaw")])
arm_body = make_armature("Armature", body_bones)
arm_head = make_armature("ArmatureHead", head_bones)
arm_lead = make_armature("ArmatureLeader", [n for n in ORDER if n not in EXTRA]) if VCFG["leader"] else None
arm_empty = make_armature("ArmatureEmpty", head_bones)
REPORT["bones"] = {"body": len(body_bones), "head": len(head_bones), "leader": len(ORDER) - len(EXTRA)}

import bmesh

# ---------------------------------------------------------------- cloth sections
# Chaos cloth on mesh sections (ue_cloth.py) as in build_pbz.py: every simulated part gets its own material slot and a
# geometric max-distance mask (radial from anchors), written to cloth.json. Sections are picked by the source rig's
# weights (a face is in when the mean of its verts' weight fraction on the chain bones is over one half):
#   MI_Karin_HairTail   twin tails (Hair_Tail chains)        MI_Karin_HairFront  bangs and side locks
#   MI_Karin_Ear        fox ears; the ear covers (Accessory_Ear, clothing atlas) are rigid with the head, so the ears
#                       are fixed up to just above them
#   MI_Karin_Tail       tail and the ribbons tied on it (Back_Ribbon, Tail_Ribbon; clothing atlas) on one texture of
#                       their own (combine_texture): UE binds one render section per clothing asset
#                       (UClothingAssetCommon::BindToSkeletalMesh refuses a second LOD mapping), and a ribbon section
#                       with a simulation of its own would not stay on the tail
#   MI_Karin_Jacket     jacket below the waist (Outer chains, pocket strings), from the border with the skinned jacket
#   MI_Karin_Cord       headphone cords (Code chains)        MI_Karin_Strap  belt strap on the left hip (Belt_Ribbon)
CLOTH = []
TEX_SRC = {"Karin_SkinFace": "Karin_PT_Atlas_Skin_Face_ColorAlpha_4096.png", "Karin_Hair": "Karin_PT_Atlas_Hair_Head_ColorAlpha_4096.png",
           "Karin_ClothA": "Karin_PT_Atlas_Clothing_A_ColorAlpha_4096.png", "Karin_ClothB": "Karin_PT_Atlas_Clothing_B_Accessories_ColorAlpha_4096.png"}
texdir = os.path.join(RUN, "textures"); os.makedirs(texdir, exist_ok=True)
def bones_with(prefixes, exclude=()):
    return {b.name for b in k_arm.data.bones if b.name.startswith(prefixes) and b.name not in exclude}
def vfrac(name, bones):
    return np.array([sum(w for n, w in row if n in bones) / max(sum(w for _, w in row), 1e-9) for row in ROWS[name]])
def fmask(name, bones, thr=0.5):
    f = vfrac(name, bones)
    return [float(np.mean(f[list(p.vertices)])) > thr for p in k_meshes[name].data.polygons]
def new_mat(src, name):
    m = src.copy() if src else bpy.data.materials.new(name)
    m.name = name
    return m
def set_slot(obj, mat, face_mask):
    me = obj.data
    me.materials.append(mat)
    idx = len(me.materials) - 1
    n = 0
    for f in me.polygons:
        if face_mask[f.index]: f.material_index = idx; n += 1
    return n
def image_px(fn):
    img = bpy.data.images.load(os.path.join(os.path.dirname(KARIN_BLEND), "textures", fn))
    w, h = img.size
    a = np.zeros(w * h * 4, dtype=np.float32); img.pixels.foreach_get(a)
    bpy.data.images.remove(img)
    return a.reshape(h, w, 4)
def uv_islands(obj, mask):
    """Masked faces grouped into UV islands (faces sharing a vertex with the same UV): [(loop indices)]."""
    me = obj.data; uv = me.uv_layers[0].data
    faces = [p for p in me.polygons if mask[p.index]]
    par = {p.index: p.index for p in faces}
    def find(a):
        while par[a] != a: par[a] = par[par[a]]; a = par[a]
        return a
    seen = {}
    for p in faces:
        for l in p.loop_indices:
            k = (me.loops[l].vertex_index, round(uv[l].uv[0], 5), round(uv[l].uv[1], 5))
            if k in seen: par[find(p.index)] = find(seen[k])
            else: seen[k] = p.index
    out = collections.defaultdict(list)
    for p in faces: out[find(p.index)].extend(p.loop_indices)
    return list(out.values())
def combine_texture(name, parts, pad=6, limit=4096):
    """parts: [(object, face mask, source texture file)]. Crops every UV island of the masked faces from its texture,
    packs the crops in shelves on a new power-of-two texture and moves the islands' UVs onto it."""
    rects = []   # (crop pixels, object, loops, W, H, x0, y0)
    for obj, mask, fn in parts:
        px = image_px(fn); H, W = px.shape[:2]
        uv = obj.data.uv_layers[0].data
        for loops in uv_islands(obj, mask):
            a = np.array([uv[l].uv for l in loops])
            x0, y0 = np.floor(a.min(0) * (W, H)).astype(int) - pad
            x1, y1 = np.ceil(a.max(0) * (W, H)).astype(int) + pad
            x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, W), min(y1, H)
            rects.append((px[y0:y1, x0:x1], obj, loops, W, H, x0, y0))
        del px
    area = sum(r[0].shape[0] * r[0].shape[1] for r in rects)
    for s in (1, 2, 4):
        cw = 1 << int(math.ceil(math.log2(max(math.sqrt(area) / s * 1.15, max(r[0].shape[1] for r in rects) / s))))
        x = y = rowh = 0; place = []
        for r in sorted(rects, key=lambda r: -r[0].shape[0]):
            h, w = r[0].shape[0] // s, r[0].shape[1] // s
            if x + w > cw: x, y, rowh = 0, y + rowh, 0
            place.append((r, x, y)); x += w; rowh = max(rowh, h)
        ch = 1 << int(math.ceil(math.log2(max(y + rowh, 1))))
        if cw <= limit and ch <= limit: break
    canvas = np.zeros((ch, cw, 4), dtype=np.float32)
    canvas[:] = np.concatenate([r[0].reshape(-1, 4) for r in rects]).mean(0)
    for (c, obj, loops, W, H, x0, y0), x, y in place:
        cs = c[:c.shape[0] // s * s, :c.shape[1] // s * s].reshape(c.shape[0] // s, s, c.shape[1] // s, s, 4).mean((1, 3))
        canvas[y:y + cs.shape[0], x:x + cs.shape[1]] = cs
        uv = obj.data.uv_layers[0].data
        for l in loops:
            u, v = uv[l].uv
            uv[l].uv = ((x + (u * W - x0) / s) / cw, (y + (v * H - y0) / s) / ch)
    img = bpy.data.images.new(name, cw, ch, alpha=True)
    img.pixels.foreach_set(canvas.ravel())
    img.filepath_raw = os.path.join(texdir, name + ".png"); img.file_format = "PNG"; img.save()
    return {"size": [cw, ch], "downscale": s, "islands": len(rects), "fill": round(area / s / s / (cw * ch), 2)}
if VCFG["cloth"]:
    hr, cb, ca = k_meshes["hair"], k_meshes["clothB"], k_meshes["clothA"]
    hair_mat = next((m for m in hr.data.materials if m and m.name == "Hair"), hr.data.materials[0])
    cb_mat, ca_mat = cb.data.materials[0], ca.data.materials[0]
    TAILS = bones_with(("Hair_Tail",))
    m_tail = fmask("hair", TAILS)
    REPORT["cloth_faces"] = {"hairtail": set_slot(hr, new_mat(hair_mat, "MI_Karin_HairTail"), m_tail)}
    # bangs and side locks: every hair face touching their chains; their root bone is the scalp
    FRONTS = bones_with(("Hair_Front", "Hair_Side"), ("Hair_Front_Root",))
    vf = vfrac("hair", FRONTS)
    hair_idx = {i for i, m in enumerate(hr.data.materials) if m and m.name in ("Hair", "Karin_Hair_Transparent")}
    m_front = [f.material_index in hair_idx and not m_tail[f.index] and float(vf[list(f.vertices)].max()) > 0.02 for f in hr.data.polygons]
    REPORT["cloth_faces"]["hairfront"] = set_slot(hr, new_mat(hair_mat, "MI_Karin_HairFront"), m_front)
    hco = np.array([list(v.co) for v in hr.data.vertices])
    vin, vout = set(), set()
    for f in hr.data.polygons:
        (vin if m_front[f.index] else vout).update(f.vertices)
    seam = sorted(vin & vout)
    # closed strand shells lose their inner sheet (build_pbz.py: welded edge particles got cancelling normals)
    hcen = hco.mean(axis=0)
    hf_i = len(hr.data.materials) - 1
    inner = [f.index for f in hr.data.polygons if f.material_index == hf_i
             and float(np.dot(np.array(f.normal), norm(np.array(f.center) - hcen))) < -0.3]
    EARS = bones_with(("Ear_",))
    m_ear = fmask("hair", EARS)
    REPORT["cloth_faces"]["ears"] = set_slot(hr, new_mat(hair_mat, "MI_Karin_Ear"), [m and not t for m, t in zip(m_ear, m_tail)])
    TAILB = bones_with(("Tail_",), bones_with(("Tail_Ribbon",)))
    RIBB = bones_with(("Back_Ribbon", "Tail_Ribbon"))
    m_tl = fmask("hair", TAILB); m_rb = fmask("clothB", RIBB | TAILB)
    REPORT["tail_texture"] = combine_texture("Karin_TailComb", [(hr, m_tl, TEX_SRC["Karin_Hair"]), (cb, m_rb, TEX_SRC["Karin_ClothB"])])
    tail_mat = new_mat(hair_mat, "MI_Karin_Tail")
    REPORT["cloth_faces"]["tail"] = set_slot(hr, tail_mat, m_tl)
    REPORT["cloth_faces"]["tail_ribbons"] = set_slot(cb, tail_mat, m_rb)
    JACKET = bones_with(("Outer", "Pocket_String"))
    m_jk = [m and not r for m, r in zip(fmask("clothB", JACKET), m_rb)]
    REPORT["cloth_faces"]["jacket"] = set_slot(cb, new_mat(cb_mat, "MI_Karin_Jacket"), m_jk)
    CORDS = bones_with(("Code",))
    REPORT["cloth_faces"]["cords"] = set_slot(cb, new_mat(cb_mat, "MI_Karin_Cord"), fmask("clothB", CORDS))
    STRAP = bones_with(("Belt_Ribbon",))
    m_st = fmask("clothA", STRAP)
    REPORT["cloth_faces"]["strap"] = set_slot(ca, new_mat(ca_mat, "MI_Karin_Strap"), m_st)
    bm = bmesh.new(); bm.from_mesh(hr.data); bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.faces[i] for i in inner], context="FACES_ONLY")   # verts kept: indices stay valid
    bm.to_mesh(hr.data); bm.free()
    REPORT["cloth_faces"]["hairfront_inner_removed"] = len(inner)

    def rootp(k): return apply(region(k), kp(k))
    def chain_len(h):
        kn = chain_of(h)
        pts = [apply(region(k), kp(k)) for k in kn] + [apply(region(kn[-1]), ktail(kn[-1]))]
        return float(sum(np.linalg.norm(pts[i + 1] - pts[i]) for i in range(len(pts) - 1)))
    def border(obj, mask):
        """Verts shared by masked and unmasked faces (where a section meets the skinned rest), and all masked verts."""
        a, b = set(), set()
        for f in obj.data.polygons:
            (a if mask[f.index] else b).update(f.vertices)
        co = np.array([list(v.co) for v in obj.data.vertices])
        return co[sorted(a & b)], co[sorted(a)]
    def far(anchors, pts):
        return float(max(np.linalg.norm(anchors - p, axis=1).min() for p in pts)) if len(anchors) and len(pts) else 0.0
    def lr(h): return (chain_len(h + ".L") + chain_len(h + ".R")) / 2.0
    lt, le, ls = lr("Hair_Tail"), lr("Ear_1"), lr("Hair_Side_1")
    fa = hco[seam] if seam else np.array([rootp(k) for k in FRONTS])
    fd1 = max(0.85 * far(fa, hco[sorted(vin)]), 3.0)
    # ears fixed up to 1 cm above the ear covers
    ear_roots = np.array([rootp(k) for k in ("Ear_1.L", "Ear_1.R")])
    cov = np.array([list(v.co) for v in cb.data.vertices])[vfrac("clothB", bones_with(("Accessory_Ear",))) > 0.5]
    ed0 = max(0.3 * le, far(ear_roots, cov) + 1.0) if len(cov) else 0.3 * le
    tail_root = rootp("Tail_1")
    ltail = chain_len("Tail_1")
    jb, jall = border(cb, m_jk)
    jd = far(jb, jall)
    cord_roots = np.array([rootp(k) for k in ("Code.L", "Code.R")])
    lc = lr("Code")
    sb, sall = border(ca, m_st)
    if not len(sb): sb = np.array([rootp("Belt_Ribbon_Root")])
    sd = far(sb, sall)
    REPORT["cloth_fixed"] = {"hairfront_anchors": len(fa), "hairfront_d1": round(fd1, 2), "ear_d0": round(ed0, 2), "ear_len": round(le, 2),
                             "tail_len": round(ltail, 2), "jacket_border": len(jb), "jacket_reach": round(jd, 2),
                             "cord_len": round(lc, 2), "strap_border": len(sb), "strap_reach": round(sd, 2), "hairtail_len": round(lt, 2)}
    # drive, damping and inertia as build_pbz.py (anim drive keeps the modelled shape; weak drive, full inertia)
    def drive(k): return {"AnimDriveStiffness": {"Low": k, "High": k}, "AnimDriveDamping": {"Low": 0.6, "High": 0.6}}
    def inertia(s): return {"LinearVelocityScale": {"X": s, "Y": s, "Z": s}, "AngularVelocityScale": s}
    def pts(a): return [[round(float(x), 3) for x in ue(p)] for p in a]
    CLOTH = [
        {"slot": "MI_Karin_HairTail", "name": "Karin_HairTails", "max_distance": round(0.45 * lt, 2),
         "mask": {"type": "radial", "anchors": pts([rootp("Hair_Tail.L"), rootp("Hair_Tail.R")]), "d0": 4.0, "d1": round(0.9 * lt, 2)},
         "config": {"DampingCoefficient": 0.03, "FrictionCoefficient": 0.1, "CollisionThickness": 1.5, "GravityScale": 0.5}
                   | inertia(1.0) | drive(0.12)},
        {"slot": "MI_Karin_Tail", "name": "Karin_Tail", "max_distance": round(0.45 * ltail, 2),
         "mask": {"type": "radial", "anchors": pts([tail_root]), "d0": 3.0, "d1": round(max(8.0, 0.9 * ltail), 2)},
         "config": {"DampingCoefficient": 0.03, "FrictionCoefficient": 0.1, "CollisionThickness": 1.5, "GravityScale": 0.4}
                   | inertia(1.0) | drive(0.12)},
        {"slot": "MI_Karin_HairFront", "name": "Karin_HairFront", "max_distance": round(0.4 * ls, 2), "collide": False,
         "mask": {"type": "radial", "anchors": pts(fa), "d0": 0.5, "d1": round(fd1, 2)},
         "config": {"DampingCoefficient": 0.05, "FrictionCoefficient": 0.1, "CollisionThickness": 0.5, "GravityScale": 0.3}
                   | inertia(1.0) | drive(0.2)},
        {"slot": "MI_Karin_Ear", "name": "Karin_Ears", "max_distance": round(0.22 * le, 2), "collide": False,
         "mask": {"type": "radial", "anchors": pts(ear_roots), "d0": round(ed0, 2), "d1": round(max(1.0 * le, ed0 + 3.0), 2)},
         "config": {"DampingCoefficient": 0.1, "FrictionCoefficient": 0.1, "CollisionThickness": 0.5, "GravityScale": 0.0}
                   | inertia(1.0) | drive(0.5)},
        # jacket hem: free range grows from the border with the skinned jacket; legs push it through the colliders
        {"slot": "MI_Karin_Jacket", "name": "Karin_Jacket", "max_distance": round(0.4 * jd, 2),
         "mask": {"type": "radial", "anchors": pts(jb), "d0": 1.0, "d1": round(max(0.8 * jd, 3.0), 2)},
         "config": {"DampingCoefficient": 0.08, "FrictionCoefficient": 0.2, "CollisionThickness": 2.0, "GravityScale": 0.5,
                    "bUseCCD": True} | inertia(0.8) | drive(0.3)},
        {"slot": "MI_Karin_Cord", "name": "Karin_Cords", "max_distance": round(0.3 * lc, 2),
         "mask": {"type": "radial", "anchors": pts(cord_roots), "d0": 2.0, "d1": round(0.9 * lc, 2)},
         "config": {"DampingCoefficient": 0.1, "FrictionCoefficient": 0.1, "CollisionThickness": 0.8, "GravityScale": 0.6}
                   | inertia(1.0) | drive(0.15)},
        {"slot": "MI_Karin_Strap", "name": "Karin_Strap", "max_distance": round(0.35 * sd, 2),
         "mask": {"type": "radial", "anchors": pts(sb), "d0": 1.0, "d1": round(max(0.9 * sd, 3.0), 2)},
         "config": {"DampingCoefficient": 0.08, "FrictionCoefficient": 0.1, "CollisionThickness": 1.0, "GravityScale": 0.6}
                   | inertia(1.0) | drive(0.2)},
    ]
    json.dump(CLOTH, open(os.path.join(RUN, f"cloth{VCFG['suffix']}.json"), "w", encoding="utf-8"), indent=1)
    REPORT["cloth"] = [{k: c[k] for k in ("slot", "max_distance")} | {"mask": {k: v for k, v in c["mask"].items() if k != "anchors"}} for c in CLOTH]

# ---------------------------------------------------------------- assemble objects
def join(names, newname, arm):
    bpy.ops.object.select_all(action="DESELECT")
    objs = [k_meshes[n] for n in names]
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1: bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active
    o.name = newname; o.data.name = newname
    for m in list(o.modifiers): o.modifiers.remove(m)
    o.parent = arm
    o.modifiers.new("Armature", "ARMATURE").object = arm
    return o
# collider radii: skin and the tight clothes (ClothA without the strap and the ribbons; the jacket and shoes are on ClothB)
k_meshes["skin"].vertex_groups.new(name="_coll").add(list(range(len(k_meshes["skin"].data.vertices))), 1.0, "REPLACE")
k_meshes["clothA"].vertex_groups.new(name="_coll").add(
    np.where(vfrac("clothA", bones_with(FOLLOW + ("Belt_Ribbon",))) < 0.1)[0].tolist(), 1.0, "REPLACE")
body = join(BODY_MESHES, "SK_Karin_Body", arm_body)
head = join(HEAD_MESHES, "SK_Karin_Head", arm_head)
bpy.data.objects.remove(k_arm, do_unlink=True)

# face morph targets
if "Body" in DELTAS:
    d = DELTAS["Body"]
    head.shape_key_add(name="Basis", from_mix=False)
    base = np.array([list(v.co) for v in head.data.vertices])
    xs = base[:, 0]
    REPORT["face_morphs"] = {}
    for mname, recipe in FACE.items():
        delta = np.zeros_like(base)
        for key, w in recipe.items():
            k, _, part = key.partition("|")
            if k not in d: continue
            dk = d[k] * w
            if part == "L": dk = dk * smooth(xs, -0.3, 0.3)[:, None]
            elif part == "R": dk = dk * (1.0 - smooth(xs, -0.3, 0.3))[:, None]
            delta += dk
        sk = head.shape_key_add(name=mname, from_mix=False)
        sk.data.foreach_set("co", (base + delta).ravel())
        REPORT["face_morphs"][mname] = round(float(np.linalg.norm(delta, axis=1).max()), 3)
    # side sanity: the character's left eye is +X
    if "blink_L" in d:
        mv = np.linalg.norm(d["blink_L"], axis=1)
        REPORT["blink_L_center_x"] = round(float((xs * mv).sum() / max(mv.sum(), 1e-9)), 2)

# ---------------------------------------------------------------- materials
MAT_RENAME = {"Karin_Face": "MI_Karin_Face", "Body": "MI_Karin_Skin", "Hair": "MI_Karin_Hair", "Karin_Hair_Transparent": "MI_Karin_HairTrans",
              "ClothA_Blue": "MI_Karin_ClothA", "Costume": "MI_Karin_Costume", "Karin_Costume": "MI_Karin_KCostume",
              "ClothB_Blue": "MI_Karin_ClothB", "Costume_1": "MI_Karin_Costume1", "Costume_Metalic": "MI_Karin_Metal"}
for m in list(bpy.data.materials):
    if m.name in MAT_RENAME: m.name = MAT_RENAME[m.name]
def drop_slots(obj, drop_faces_of=(), merge=None):
    merge = merge or {}
    idx = {s.material.name: i for i, s in enumerate(obj.material_slots) if s.material}
    bm = bmesh.new(); bm.from_mesh(obj.data)
    dels = [f for f in bm.faces if any(f.material_index == idx.get(n, -1) for n in drop_faces_of)]
    bmesh.ops.delete(bm, geom=dels, context="FACES")
    for f in bm.faces:
        for src, dst in merge.items():
            if f.material_index == idx.get(src, -1): f.material_index = idx[dst]
    bm.to_mesh(obj.data); bm.free()
    bpy.context.view_layer.objects.active = obj
    for name in list(drop_faces_of) + list(merge):
        for i, s in enumerate(obj.material_slots):
            if s.material and s.material.name == name:
                obj.active_material_index = i
                bpy.ops.object.material_slot_remove(); break
    return len(dels)
# the small materials share an atlas with a big one: one slot per atlas (hair ribbons and costume pieces on ClothA,
# metal and the other costume pieces on ClothB)
drop_slots(body, (), {"MI_Karin_HairTrans": "MI_Karin_Hair", "MI_Karin_Costume": "MI_Karin_ClothA", "MI_Karin_KCostume": "MI_Karin_ClothA",
                      "MI_Karin_Costume1": "MI_Karin_ClothB", "MI_Karin_Metal": "MI_Karin_ClothB"})
if VCFG["face_in_body"]:
    # The adult head component (meshhead: Hun_CopyPose plus the game's head logic) rendered the face dark brown, while
    # the same face mesh and material are fine on the young head and on the body's neck right next to it. So the face
    # and its morph targets join the body mesh and Hun_Head_New becomes a hidden stand-in (Empty.fbx).
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True); head.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.join()
    head = None
REPORT["materials"] = {"body": [s.material.name for s in body.material_slots], "head": [s.material.name for s in head.material_slots] if head else []}

# ---------------------------------------------------------------- textures and materials.json
# base color atlases as they are (alpha unused: only the dropped Karin_Alpha overlay is cut out); the tail texture is
# written by combine_texture. Normal and emission atlases are not used yet (flat normals as build_pbz.py).
import shutil
for t, fn in TEX_SRC.items():
    shutil.copyfile(os.path.join(os.path.dirname(KARIN_BLEND), "textures", fn), os.path.join(texdir, t + ".png"))
MATS = {"MI_Karin_Skin": ("Karin_SkinFace", "skin"), "MI_Karin_Face": ("Karin_SkinFace", "face"), "MI_Karin_Hair": ("Karin_Hair", "hair"),
        "MI_Karin_Tail": ("Karin_TailComb", "hair"), "MI_Karin_ClothA": ("Karin_ClothA", "costume"), "MI_Karin_ClothB": ("Karin_ClothB", "costume")}
ALIAS = {"MI_Karin_HairTail": "MI_Karin_Hair", "MI_Karin_HairFront": "MI_Karin_Hair", "MI_Karin_Ear": "MI_Karin_Hair",
         "MI_Karin_Jacket": "MI_Karin_ClothB", "MI_Karin_Cord": "MI_Karin_ClothB", "MI_Karin_Strap": "MI_Karin_ClothA"}
json.dump({"materials": {k: {"texture": t, "kind": c} for k, (t, c) in MATS.items()}, "alias": ALIAS},
          open(os.path.join(RUN, f"materials{VCFG['suffix']}.json"), "w", encoding="utf-8"), indent=1)
REPORT["slots_unmapped"] = sorted({s.material.name for o in (body, head) if o for s in o.material_slots} - set(MATS) - set(ALIAS))

# ---------------------------------------------------------------- hidden triangles
def tri(name, arm, bone, at, mat):
    m = bpy.data.meshes.new(name)
    m.from_pydata([tuple(at), tuple(at + np.array([0.01, 0, 0])), tuple(at + np.array([0, 0, 0.01]))], [], [(0, 1, 2)])
    m.update()
    o = bpy.data.objects.new(name, m); bpy.context.scene.collection.objects.link(o)
    o.data.materials.append(mat)
    o.vertex_groups.new(name=bone).add([0, 1, 2], 1.0, "REPLACE")
    o.parent = arm
    o.modifiers.new("Armature", "ARMATURE").object = arm
    return o
skin = bpy.data.materials.get("MI_Karin_Skin")
leader_tri = tri("SK_Karin_Leader", arm_lead, V("root"), np.array([0.0, 0.0, 0.0]), skin) if arm_lead else None
empty_tri = tri("SK_Hidden", arm_empty, V("head"), NEW[V("head")] + np.array([0, 0, 1.0]), skin)
hat_arm = hat_tri = None
if VARIANT == "adult":
    h_objs = import_uemodel(os.path.join(WORK, "ue", "Hun_Hat_Skeleton.uemodel"))
    hat_arm = next(o for o in h_objs if o.type == "ARMATURE")
    hat_arm.name = "ArmatureHat"; hat_arm.data.name = "ArmatureHat"
    for o in h_objs:
        if o.type == "MESH": bpy.data.objects.remove(o, do_unlink=True)
    hat_tri = tri("SK_HatHidden", hat_arm, hat_arm.data.bones[0].name, np.array([0.0, 0.0, 0.0]), skin)
if head and VCFG["face_slot0"]:
    # The game gives the adult head component a dynamic instance of its first material (BP_Renewal_Hun
    # RefreshMaterialParamByHead: GetMaterial(0) -> CreateDynamicMaterialInstance(0) -> HealthPercentage), and with it the
    # face rendered dark brown with grey eyes. The young player (no override) and the lash card render the same face and
    # material fine. So the head's first section is a hidden triangle inside the head and the face is the second.
    t = tri("SK_HeadSlot0", arm_head, V("head"), NEW[V("head")], bpy.data.materials["MI_Karin_Skin"])
    bpy.ops.object.select_all(action="DESELECT")
    t.select_set(True); head.select_set(True)
    bpy.context.view_layer.objects.active = head
    bpy.ops.object.join()
    me = head.data
    order = [m.name for m in me.materials]
    new = ["MI_Karin_Skin"] + [n for n in order if n != "MI_Karin_Skin"]
    idx = np.zeros(len(me.polygons), dtype=np.int32); me.polygons.foreach_get("material_index", idx)
    remap = np.array([new.index(n) for n in order], dtype=np.int32)
    mats = [bpy.data.materials[n] for n in new]
    me.materials.clear()
    for m in mats: me.materials.append(m)
    me.polygons.foreach_set("material_index", remap[idx]); me.update()
lash_face = None
if head and VCFG["face_show"]:
    # Gameplay: the head component's own anim blueprint does not drive its morphs (blinks added there never showed, the
    # same overlay on the lash card did), while the cutscene actors (BP_Seq_*) run it and hide the lash card. So the face
    # is on both: plain on the lash card, and on the head scaled to 90% around the head joint with a morph target
    # KarinFaceShow that restores it; the mod's Hun_CopyPose(_Head) always outputs that curve at 1. In gameplay the
    # scaled copy sits inside the lash card's face (eyes about 1.3 cm deeper; probe_face3.py: nothing of it in front of
    # the closed lids). Not smaller: the importer computes each expression's normals on the scaled base plus the
    # unscaled delta (5%: blink normals off by up to 2.0; 90%: about 1.3 degrees mean, 6 at the 95th percentile).
    lash_face = head.copy(); lash_face.data = head.data.copy(); lash_face.name = "SK_Karin_Face"
    bpy.context.scene.collection.objects.link(lash_face)
    keys = head.data.shape_keys.key_blocks
    n = len(head.data.vertices)
    base = np.zeros(n * 3); keys["Basis"].data.foreach_get("co", base); base = base.reshape(-1, 3)
    c = np.array(NEW[V("head")])
    small = c + (base - c) * 0.9
    for kb in keys[1:]:
        a = np.zeros(n * 3); kb.data.foreach_get("co", a)
        kb.data.foreach_set("co", (a.reshape(-1, 3) - base + small).ravel())
    show = head.shape_key_add(name="KarinFaceShow", from_mix=False)
    show.data.foreach_set("co", base.ravel())
    keys["Basis"].data.foreach_set("co", small.ravel())
    head.data.vertices.foreach_set("co", small.ravel()); head.data.update()
    REPORT["face_show"] = {"verts": n, "collapsed_extent": round(float(np.abs(small - c).max()), 3)}

# ---------------------------------------------------------------- degenerate cloth triangles
# UE's cloth builder welds coincident verts and refuses the whole section when a triangle then has two equal corners
# (LogClothingAssetFactory "degenerate triangle": the twin tails, at a collapsed edge near the root). The cloth sections
# are triangulated here and triangles with an edge under 0.01 mm or no area are dropped.
def drop_degenerate(obj, slots, tol=1e-3):
    idx = {s.material.name: i for i, s in enumerate(obj.material_slots) if s.material}
    want = {idx[n] for n in slots if n in idx}
    bm = bmesh.new(); bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if f.material_index in want])
    bad = [f for f in bm.faces if f.material_index in want
           and (min(e.calc_length() for e in f.edges) < tol or f.calc_area() < tol * tol)]
    bmesh.ops.delete(bm, geom=bad, context="FACES_ONLY")
    bm.to_mesh(obj.data); bm.free()
    return len(bad)
if CLOTH:
    REPORT["degenerate_cloth_tris"] = drop_degenerate(body, [c["slot"] for c in CLOTH])

# ---------------------------------------------------------------- physics asset (UE bone-local shapes)
if True:
    # UE component space = Blender with Y negated. Bind rotations are the vanilla ones (skel json local quats).
    def qmul(a, b):
        ax, ay, az, aw = a; bx, by, bz, bw = b
        return (aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx,
                aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz)
    CROT = {}
    def crot(n):
        l = n.lower()
        if l in CROT: return CROT[l]
        p = SKP.get(l)
        q = tuple(SKQ[l])
        CROT[l] = q if p is None else qmul(crot(p), q)
        return CROT[l]
    def qmat(q):
        x, y, z, w = q
        return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                         [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                         [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
    def ue(p): return np.array([p[0], -p[1], p[2]])
    def to_local(n, p_blender):
        R = qmat(crot(n))
        return R.T @ (ue(p_blender) - ue(NEW[n]))
    def dir_local(n, d_blender):
        return qmat(crot(n)).T @ ue(d_blender)
    def quat_z_to(d):
        d = norm(d); z = np.array([0.0, 0.0, 1.0])
        c = float(np.dot(z, d))
        if c > 0.99999: return [0.0, 0.0, 0.0, 1.0]
        if c < -0.99999: return [1.0, 0.0, 0.0, 0.0]
        ax = norm(np.cross(z, d)); s = math.sqrt((1 - c) / 2.0); hc = math.sqrt((1 + c) / 2.0)
        return [float(ax[0] * s), float(ax[1] * s), float(ax[2] * s), hc]
    def capsule(n, a, b, r, kinematic, **extra):
        """Capsule from Blender points a->b on bone n (radius r, cylinder length |b-a|)."""
        la, lb = to_local(n, a), to_local(n, b)
        L = float(np.linalg.norm(lb - la))
        body = {"bone": n, "type": "capsule", "center": [round(float(x), 3) for x in (la + lb) / 2.0],
                "quat": quat_z_to(lb - la), "radius": round(float(r), 3), "length": round(max(L, 0.1), 3), "kinematic": kinematic}
        body.update(extra)
        return body

    # collider radii from the re-posed mesh: median distance of strongly weighted body verts to the segment
    bpos = np.array([list(v.co) for v in body.data.vertices])
    def seg_dist(p, a, b):
        d = b - a; t = np.clip(((p - a) @ d) / max(np.dot(d, d), 1e-9), 0, 1)
        return np.linalg.norm(p - (a + np.outer(t, d)), axis=1)
    gidx = {g.index: g.name for g in body.vertex_groups}
    cg = body.vertex_groups["_coll"].index
    vbone = collections.defaultdict(list)
    for i, v in enumerate(body.data.vertices):
        if not any(g.group == cg for g in v.groups): continue   # skirt, hair, tail and ears would inflate the radii
        best = max((g for g in v.groups if g.group != cg), key=lambda g: g.weight, default=None)
        if best is not None and best.weight > 0.6:
            vbone[gidx[best.group]].append(i)
    body.vertex_groups.remove(body.vertex_groups["_coll"])
    def radius_for(bone, a, b, default, pct=40):
        ids = vbone.get(bone, [])
        if len(ids) < 20: return default
        d = seg_dist(bpos[ids], a, b)
        return float(np.clip(np.percentile(d, pct), 2.0, 14.0))
    COLL = []
    def coll(bone, a, b, default, shrink=0.9, pct=40):
        r = radius_for(bone, a, b, default, pct) * shrink
        COLL.append(capsule(bone, a, b, r, True))
    pel, s2, s4, nk, hd = (V(n) for n in ("pelvis", "spine_02", "spine_04", "neck_01", "head"))
    coll(pel, NEW[V("thigh_l")], NEW[V("thigh_r")], 10.0)
    coll(s2, NEW[s2], NEW[V("spine_03")], 10.0)
    coll(s4, NEW[s4], NEW[V("spine_05")], 10.0)
    coll(nk, NEW[nk], NEW[V("head")], 4.0)
    COLL.append({"bone": hd, "type": "sphere", "center": [round(float(x), 3) for x in to_local(hd, NEW[hd] + np.array([0, 0, 8.0 * SCALE]))],
                 "radius": round(float(9.0 * SCALE), 2), "kinematic": True})
    for s in "lr":
        th, ca, ft, ua, la = (V(f"{n}_{s}") for n in ("thigh", "calf", "foot", "upperarm", "lowerarm"))
        coll(th, NEW[th], NEW[ca], 7.0, shrink=1.0, pct=85)
        coll(ca, NEW[ca], NEW[ft], 5.0)
        coll(ua, NEW[ua], NEW[la], 4.0)
    # buttocks: a sphere per side on the thigh, fitted to the pelvis / thigh skin behind the hip joint (the skirt sank
    # into them between the pelvis and thigh capsules)
    for s, sx in (("l", 1.0), ("r", -1.0)):
        th, ca = V(f"thigh_{s}"), V(f"calf_{s}")
        L_ = float(np.linalg.norm(NEW[ca] - NEW[th]))
        ids = np.array(vbone.get(pel, []) + vbone.get(th, []), dtype=int)
        if len(ids) < 20: continue
        p = bpos[ids]
        m = (p[:, 0] * sx > 1.0) & (p[:, 1] > NEW[th][1] + 1.0) & (p[:, 2] > NEW[th][2] - 0.35 * L_) & (p[:, 2] < NEW[th][2] + 0.15 * L_)
        p = p[m]
        if len(p) < 20: continue
        c = np.array([p[:, 0].mean(), NEW[th][1], p[:, 2].mean()])
        r0 = float(np.percentile(np.linalg.norm(p - c, axis=1), 75))
        c[1] += 0.25 * r0
        r = float(np.percentile(np.linalg.norm(p - c, axis=1), 85))
        COLL.append({"bone": th, "type": "sphere", "center": [round(float(x), 3) for x in to_local(th, c)], "radius": round(r, 2), "kinematic": True})
        REPORT.setdefault("buttock_spheres", {})[s] = {"center": [round(float(x), 2) for x in ue(c)], "radius": round(r, 2), "verts": int(len(p))}
    KIN = [c["bone"] for c in COLL]
    if VCFG["cloth"]:
        # cloth collision PA: the kinematic capsules only
        json.dump({"bodies": COLL, "joints": [], "disable_pairs": []}, open(os.path.join(RUN, f"cloth_collision{VCFG['suffix']}.json"), "w", encoding="utf-8"), indent=1)

# ---------------------------------------------------------------- checks
def ue(p): return np.array([p[0], -p[1], p[2]])   # UE component space = Blender with Y negated
for o, a in [(body, arm_body)] + ([(head, arm_head)] if head else []):
    bones = set(b.name for b in a.data.bones)
    REPORT.setdefault("groups_not_bones", {})[o.name] = [g.name for g in o.vertex_groups if g.name not in bones]
    REPORT.setdefault("verts", {})[o.name] = len(o.data.vertices)
REPORT["new_joints"] = {n: [round(float(x), 2) for x in ue(NEW[n])] for n in
                        [V(x) for x in ("pelvis", "spine_01", "neck_01", "head", "clavicle_l", "upperarm_l", "lowerarm_l",
                                        "hand_l", "thigh_l", "calf_l", "foot_l", "ball_l")]}

# ---------------------------------------------------------------- export (stock FBX, cm via unit scale 0.01)
bpy.context.scene.unit_settings.scale_length = 0.01
kw = dict(use_selection=True, add_leaf_bones=False, bake_anim=False, use_mesh_modifiers=False,
          mesh_smooth_type="FACE", use_tspace=False, object_types={"ARMATURE", "MESH"})
SFX = VCFG["suffix"]
EXPORTS = [(arm_body, body, f"Karin_Body{SFX}.fbx"), (arm_empty, empty_tri, f"Empty{SFX}.fbx")]
# Adult face on the head component (meshhead), behind a hidden first section (face_slot0). On the body (the leader) it
# never blinked in gameplay; on the lash card (meshBrowLashCard) the cutscene actors (BP_Seq_Hun*, lash card flagged
# bInfluencedByMainHairMode) hid it.
for fn in ("Karin_Head", "Karin_Face"):   # the UE import picks the face meshes by which FBX exists; none = face in the body
    if (not head or fn != VCFG["face_fbx"]) and not (fn == "Karin_Face" and VCFG["face_show"]) and os.path.exists(os.path.join(RUN, f"{fn}{SFX}.fbx")):
        os.remove(os.path.join(RUN, f"{fn}{SFX}.fbx"))
if head:
    EXPORTS.append((arm_head, head, f"{VCFG['face_fbx']}{SFX}.fbx"))
if lash_face:
    EXPORTS.append((arm_head, lash_face, f"Karin_Face{SFX}.fbx"))
if arm_lead: EXPORTS.append((arm_lead, leader_tri, "Karin_Leader.fbx"))
if hat_arm: EXPORTS.append((hat_arm, hat_tri, "Hat_Empty.fbx"))
for arm, o, fn in EXPORTS:
    # the exporter drops the armature node only when the object is named "Armature" (else UE adds an extra root bone)
    for a_ in [e[0] for e in EXPORTS]:
        if a_ is not arm and a_.name == "Armature": a_.name = "ArmatureTmp"
    arm.name = "Armature"
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True); o.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.export_scene.fbx(filepath=os.path.join(RUN, fn), **kw)
    arm.name = "Exported_" + fn
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(RUN, f"build{VCFG['suffix']}.blend"))
with open(os.path.join(RUN, f"report{VCFG['suffix']}.json"), "w", encoding="utf-8") as f:
    json.dump(REPORT, f, indent=1, ensure_ascii=False)
print("BUILD_OK", RUN)
