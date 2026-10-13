# Build Karin_Original for Palworld (Blender 4.2 background).
#
# Usage:
#   blender --background --factory-startup --python build_pal.py -- <run_dir> [--scale 1.30]
#
# Output in <run_dir>:
#   Karin_Body.fbx  -> SK_Player_Female_Outfit_OldCloth001 (body, costume, hair, ears, tail; physics chains)
#   Karin_Head.fbx  -> SK_Player_Female_HeadXXX (face, eyes, brows; PalFacialComponent morph targets)
#   textures/*.png, report.json, build.blend
#
# Skeleton contract (SK_PalHuman_Skeleton, translation retargeting = Skeleton for all but root/pelvis):
#   * Bind-pose bone orientations = vanilla (animations set absolute local rotations).
#   * Limb segments keep the vanilla direction with Karin's length; branch offsets (pelvis->thigh, spine_03->clavicle,
#     hand->finger roots, head->eyes) are Karin's own. The mesh is re-posed onto that skeleton by a per-bone rigid
#     transform (swing of Karin's segment onto the vanilla direction).
#   * Physics chains are renamed onto existing linear NPC accessory chains of the game skeleton, because the game's
#     KawaiiPhysics (1.17.x) walks the skeleton asset's hierarchy, not the mesh's (same finding as the SB project).
import bpy, sys, os, json, math, collections
import numpy as np
from mathutils import Matrix, Vector, Quaternion

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from palcommon import enable_ueformat, import_uemodel, CACHE_UE, KARIN_VRM

argv = sys.argv[sys.argv.index("--") + 1:]
RUN = os.path.abspath(argv[0])
SCALE = float(argv[argv.index("--scale") + 1]) if "--scale" in argv else 1.30
os.makedirs(RUN, exist_ok=True)
REPORT = {"scale": SCALE, "warnings": []}

bpy.ops.wm.read_factory_settings(use_empty=True)
enable_ueformat()
import addon_utils
addon_utils.enable("io_scene_fbx", default_set=True)

# ---------------------------------------------------------------- vanilla skeleton (UE frames, Blender = UE with Y flipped)
v_objs = import_uemodel(os.path.join(CACHE_UE, r"Outfit\SK_Player_Female_Outfit_OldCloth001\SK_Player_Female_Outfit_OldCloth001.uemodel"))
v_arm = next(o for o in v_objs if o.type == "ARMATURE")
for o in v_objs:
    if o.type == "MESH":
        bpy.data.objects.remove(o, do_unlink=True)
VM = {b.name: (v_arm.matrix_world @ b.matrix_local) for b in v_arm.data.bones}
VPAR = {b.name: (b.parent.name if b.parent else None) for b in v_arm.data.bones}
BASE = [b.name for b in v_arm.data.bones if not b.name.startswith("F_OldCloth001")]
def vp(n): return np.array(VM[n].translation)

# ---------------------------------------------------------------- Karin
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=KARIN_VRM)
k_objs = [o for o in bpy.data.objects if o not in before]
k_arm = next(o for o in k_objs if o.type == "ARMATURE")
k_arm.name = "KarinArmature"; k_arm.data.name = "KarinArmature"
BODY_MESHES = ["body_2", "hair", "kemomimi", "tail", "pullover", "skirt", "underwear", "knee-socks", "shoes"]
HEAD_MESHES = ["Body"]   # the VRM's "Body" object is the face (Karin_Face + Karin_Alpha), it carries the 237 face keys
k_meshes = {o.name: o for o in k_objs if o.type == "MESH" and o.name in BODY_MESHES + HEAD_MESHES}
for o in k_objs:
    if o.type != "ARMATURE" and o.name not in k_meshes:
        bpy.data.objects.remove(o, do_unlink=True)
G = Matrix.Scale(100.0 * SCALE, 4)   # both face -Y in Blender; metres -> cm
Gn = np.array(G)
KB = {b.name: b for b in k_arm.data.bones}
def kp(n): return np.array(G @ (k_arm.matrix_world @ KB[n].head_local))

def norm(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-9 else v

# ---------------------------------------------------------------- joint correspondence
KMAP = {"pelvis": "Hips", "spine_01": "Spine", "neck_01": "Neck", "head": "Head", "eyes_l": "LeftEye", "eyes_r": "RightEye"}
for s, S in (("l", "Left"), ("r", "Right")):
    KMAP.update({f"clavicle_{s}": f"{S}Shoulder", f"upperarm_{s}": f"{S}UpperArm", f"lowerarm_{s}": f"{S}LowerArm",
                 f"hand_{s}": f"{S}Hand", f"thigh_{s}": f"{S}UpperLeg", f"calf_{s}": f"{S}LowerLeg", f"foot_{s}": f"{S}Foot",
                 f"ball_{s}": f"{S}ToeBase"})
    for pf, kf in (("thumb", "Thumb"), ("index", "Index"), ("middle", "Middle"), ("ring", "Ring"), ("pinky", "Little")):
        for i, seg in enumerate(("Proximal", "Intermediate", "Distal")):
            KMAP[f"{pf}_0{i + 1}_{s}"] = f"{S}{kf}{seg}"
# continuation segments: (parent, child) whose direction animations rely on -> vanilla direction, Karin length
CHAIN = {"spine_01": "spine_02", "spine_02": "spine_03", "spine_03": "neck_01", "neck_01": "head"}
for s in "lr":
    CHAIN.update({f"clavicle_{s}": f"upperarm_{s}", f"upperarm_{s}": f"lowerarm_{s}", f"lowerarm_{s}": f"hand_{s}",
                  f"thigh_{s}": f"calf_{s}", f"calf_{s}": f"foot_{s}", f"foot_{s}": f"ball_{s}"})
    for pf in ("thumb", "index", "middle", "ring", "pinky"):
        CHAIN[f"{pf}_01_{s}"] = f"{pf}_02_{s}"; CHAIN[f"{pf}_02_{s}"] = f"{pf}_03_{s}"
CHILD_OF = {c: p for p, c in CHAIN.items()}

# Karin has no spine_02/spine_03: the run Spine->Neck is shared by spine_01..neck_01 in vanilla proportions, scaled so
# the chord spine_01->neck_01 equals Karin's Spine->Neck (the torso then re-poses as one rigid piece onto it).
k_spine = np.linalg.norm(kp("Neck") - kp("Spine"))
v_chord = np.linalg.norm(vp("neck_01") - vp("spine_01"))
def seg_len(p, c):
    if p in ("spine_01", "spine_02", "spine_03"):
        return np.linalg.norm(vp(c) - vp(p)) * k_spine / v_chord
    if KMAP.get(p) and KMAP.get(c):
        return np.linalg.norm(kp(KMAP[c]) - kp(KMAP[p]))
    return np.linalg.norm(vp(c) - vp(p))

# length ratio per bone (used for unmapped children such as twist / weapon bones)
RATIO = {}
for p, c in CHAIN.items():
    RATIO[p] = seg_len(p, c) / max(np.linalg.norm(vp(c) - vp(p)), 1e-6)
for s in "lr":
    RATIO[f"hand_{s}"] = np.linalg.norm(kp(KMAP[f"middle_01_{s}"]) - kp(KMAP[f"hand_{s}"])) /                          np.linalg.norm(vp(f"middle_01_{s}") - vp(f"hand_{s}"))
    RATIO[f"ball_{s}"] = RATIO[f"foot_{s}"]
    for pf in ("thumb", "index", "middle", "ring", "pinky"):
        RATIO[f"{pf}_03_{s}"] = RATIO[f"{pf}_02_{s}"]
RATIO["head"] = RATIO["neck_01"]
RATIO["pelvis"] = RATIO["spine_01"]

def swing(a, b):
    q = Vector(norm(a)).rotation_difference(Vector(norm(b)))
    return np.array(q.to_matrix())
def rigid(R, src, dst):
    M = np.eye(4); M[:3, :3] = R; M[:3, 3] = dst - R @ src
    return M
def apply(M, p): return M[:3, :3] @ p + M[:3, 3]
INV = {v: k for k, v in KMAP.items()}
TORSO = ("Spine", "Chest")

NEW, KMC = {}, {}
def newpos(n):
    """Bind-pose position of vanilla bone n."""
    if n in NEW: return NEW[n]
    p = VPAR[n]
    if p is None:
        r = vp(n)
    elif n == "pelvis":
        r = kp("Hips")
    elif n in CHILD_OF:                       # continuation: vanilla direction, Karin length
        r = newpos(p) + norm(vp(n) - vp(p)) * seg_len(p, n)
    elif n in KMAP:                           # branch joint: Karin's joint carried by its re-posed Karin parent
        k = KMAP[n]
        r = apply(kmat(KB[k].parent.name), kp(k))
    else:                                     # unmapped helper: vanilla offset scaled like its parent
        r = newpos(p) + (vp(n) - vp(p)) * RATIO.get(p, 1.0)
    NEW[n] = r
    return r
def kmat(k):
    """Rigid transform that re-poses Karin bone k's region (Karin cm frame -> new bind pose)."""
    if k in KMC: return KMC[k]
    kb = KB[k]
    pal = INV.get(k)
    if k in TORSO:
        R = swing(kp("Neck") - kp("Spine"), newpos("neck_01") - newpos("spine_01"))
        M = rigid(R, kp("Spine"), newpos("spine_01"))
    elif pal is not None:
        child = CHAIN.get(pal)
        if child is not None and KMAP.get(child):
            R = swing(kp(KMAP[child]) - kp(k), newpos(child) - newpos(pal))
        elif kb.parent is not None:
            R = kmat(kb.parent.name)[:3, :3]
        else:
            R = np.eye(3)
        M = rigid(R, kp(k), newpos(pal))
    elif kb.parent is not None:               # secondary / helper bones ride rigidly on their parent
        M = kmat(kb.parent.name)
    else:
        M = np.eye(4)
    KMC[k] = M
    return M
for n in BASE:
    newpos(n)
KM = {kb.name: kmat(kb.name) for kb in k_arm.data.bones}
REPORT["joints"] = {n: [round(float(x), 2) for x in NEW[n]] for n in BASE}
REPORT["ratio"] = {n: round(float(r), 3) for n, r in RATIO.items()}
# how far Karin's own joints land from the new skeleton joints after the re-pose (seams at the segment ends)
REPORT["joint_mismatch_cm"] = {pal: round(float(np.linalg.norm(apply(KM[KB[k].parent.name], kp(k)) - NEW[pal])), 2)
                               for k, pal in INV.items() if KB[k].parent is not None and pal in NEW}

# ---------------------------------------------------------------- mesh re-pose (LBS of the rigid transforms)
def vgroups(obj):
    names = {g.index: g.name for g in obj.vertex_groups}
    return [[(names[g.group], g.weight) for g in v.groups if g.weight > 1e-6] for v in obj.data.vertices]

BAKE_KEYS = {"body_2": {"kisekae_Shoulder", "kisekae_UpperArm", "kisekae_Elbow", "kisekae_LowerArm", "kisekae_Chest 2",
                        "kisekae_Knee", "kisekae_LowerLeg 1", "kisekae_LowerLeg 2", "kisekae_Ankle", "kisekae_Foot",
                        "kisekae_Toe"}}

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
    """Re-pose obj. keep_keys: set of key names kept as deltas (re-posed with the same weights), others baked/dropped."""
    me = obj.data
    W = np.array(obj.matrix_world)
    T = Gn @ W
    rows = vgroups(obj)
    def to_cm(a): return (np.c_[a, np.ones(len(a))] @ T.T)[:, :3]
    kept = {}
    if me.shape_keys:
        kb = me.shape_keys.key_blocks
        basis = np.array([list(p.co) for p in kb[0].data])
        mix = basis.copy()
        for key in kb[1:]:
            arr = np.array([list(p.co) for p in key.data])
            if key.name in BAKE_KEYS.get(obj.name, ()):
                mix += arr - basis
                REPORT.setdefault("baked_keys", []).append(f"{obj.name}:{key.name}")
            elif key.name in keep_keys:
                kept[key.name] = arr - basis
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
    # kept keys: deform basis+delta with the same LBS, store the difference
    deltas = {}
    for name, d in kept.items():
        moved = lbs(rows, to_cm(base + d))
        deltas[name] = moved - out
    return rows, deltas

# ---------------------------------------------------------------- face morphs for PalFacialComponent
# morph names the game's facial component drives (strings next to each other in Palworld-Win64-Shipping.exe)
FACE_MORPHS = {
    "eye_close":     {"blink": 1.0},
    "eye_halfclose": {"blink": 0.55},
    "eye_smile":     {"smile": 1.0},
    "eye_anger":     {"jitome": 0.45, "mayu_angry_1": 1.0},
    "eye_pain":      {"><": 1.0, "mayu_sad_1": 0.8},
    "eye_trouble":   {"mayu_sad_2": 1.0, "LowerEyelid_up": 0.3},
    "eye_guruguru":  {"guruguru_1": 1.0},
    "mouth_open":    {"kuchi_A": 1.0},
    "mouth_smile":   {"wa": 0.75},
    "mouth_pain":    {"hawa": 1.0},
    "mouth_anger":   {"Λ_1": 1.0},
}
need_keys = set(k for m in FACE_MORPHS.values() for k in m)

face = k_meshes["Body"]
face_keys = set(k.name for k in face.data.shape_keys.key_blocks) if face.data.shape_keys else set()
missing = sorted(need_keys - face_keys)
if missing:
    REPORT["warnings"].append(f"missing face keys {missing}")
ROWS, DELTAS = {}, {}
for name, obj in k_meshes.items():
    rows, deltas = deform(obj, need_keys if name == "Body" else set())
    ROWS[name] = rows
    if deltas: DELTAS[name] = deltas

# ---------------------------------------------------------------- weights -> PalHuman bones
SPINE_ST = None
def tparam(p, a, b):
    d = b - a
    return float(np.clip(np.dot(p - a, d) / max(np.dot(d, d), 1e-9), 0.0, 1.0))
def smooth(x, a, b):
    t = min(max((x - a) / (b - a), 0.0), 1.0)
    return t * t * (3 - 2 * t)

DIRECT = dict(INV)       # Karin humanoid bone -> PalHuman bone
def spine_split(kname, p):
    """Karin Spine/Chest weight -> spine_01/02/03 by height along the new spine (smooth ramps at the joints)."""
    z = p[2]
    z1, z2, z3 = NEW["spine_02"][2], NEW["spine_03"][2], NEW["neck_01"][2]
    w2 = smooth(z, z1 - 3.0, z1 + 3.0)
    w3 = smooth(z, z2 - 3.0, z2 + 3.0)
    return {"spine_01": 1 - w2, "spine_02": w2 - w3, "spine_03": w3}

# physics chains: Karin chain head -> (skeleton parent, game skeleton chain from the head down). The listed chains
# are linear NPC accessory chains (no player animation tracks; checked idle/jog/dance/damage/jump: 65 base tracks).
def seq(prefix, n, start=1, fmt="%02d", suffix=""):
    return [prefix + (fmt % i) + suffix for i in range(start, start + n)]
SKEL_CHAINS = {
    "Skirt_0":   ("pelvis", seq("NPC_SakurajimaBoss_skirtA_", 5)),
    "Skirt_8":   ("pelvis", seq("NPC_SakurajimaBoss_skirtB_", 5)),
    "Tail":      ("pelvis", seq("NPC_Female_Kunoichi01_cloth_A_", 8)),
    "Hair_tail_L": ("head", seq("NPC_Female_Kunoichi01_hair_", 8, suffix="_l")),
    "Hair_tail_R": ("head", seq("NPC_Female_Kunoichi01_hair_", 8, suffix="_r")),
    "Hair_side_L": ("head", seq("NPC_SakurajimaBoss_hairE_", 5, suffix="_l")),
    "Hair_side_R": ("head", seq("NPC_SakurajimaBoss_hairE_", 5, suffix="_r")),
    "Ear_L":     ("head", seq("NPC_SakurajimaBoss_hairF_", 5, suffix="_l")),
    "Ear_R":     ("head", seq("NPC_SakurajimaBoss_hairF_", 5, suffix="_r")),
    "Ribbon_L":  ("head", seq("NPC_GrassBoss001_hair_", 4, suffix="_l")),
    "Ribbon_R":  ("head", seq("NPC_GrassBoss001_hair_", 4, suffix="_r")),
    "Hair_front": ("head", seq("NPC_SakurajimaBoss_hairA_", 4)),
    "Hair_front_L": ("head", seq("NPC_Female_Farmer01_hairB_", 4, suffix="_l")),
    "Hair_front_R": ("head", seq("NPC_Female_Farmer01_hairB_", 4, suffix="_r")),
    "Cheek_Root_L": ("head", seq("NPC_WorldTreeBoss001_sidehair_", 4, suffix="_l")),
    "Cheek_Root_R": ("head", seq("NPC_WorldTreeBoss001_sidehair_", 4, suffix="_r")),
    "Ribbon_camisole": ("spine_03", seq("NPC_SorajimaBoss001_chesthimoA_", 2)),
    "Ribbon_tops_L": ("spine_03", seq("NPC_WorldTreeBoss001_collarB_", 2, suffix="_l")),
    "Ribbon_tops_R": ("spine_03", seq("NPC_WorldTreeBoss001_collarB_", 2, suffix="_r")),
}
for i, (a, b) in enumerate((("A", "SnowBoss001_skirtA"), ("B", "SnowBoss001_skirtB"), ("C", "SnowBoss001_skirtC"),
                            ("D", "SnowBoss001_skirtD"), ("E", "GrassBoss001_Skin001_skirtB"),
                            ("F", "GrassBoss001_Skin001_skirtC"), ("G", "GrassBoss001_Skin001_skirtD"))):
    for s in "LR":
        SKEL_CHAINS[f"Skirt_{i + 1}_{s}"] = ("pelvis", seq(f"NPC_{b}_", 4, suffix="_" + s.lower()))
RENAME, CHAIN_PARENT = {}, {}
for head, (sparent, sq) in SKEL_CHAINS.items():
    names = [head]
    while KB[names[-1]].children:
        assert len(KB[names[-1]].children) == 1, f"{names[-1]} branches"
        names.append(KB[names[-1]].children[0].name)
    assert len(names) <= len(sq), f"{head}: {len(names)} bones, skeleton chain has {len(sq)}"
    RENAME.update(zip(names, sq))
    CHAIN_PARENT[sq[0]] = sparent
REPORT["physics_chains"] = {sq[0]: [RENAME[n] for n in RENAME if RENAME[n].startswith(sq[0][:-3])] for _, sq in SKEL_CHAINS.values()}

def target_of(kname):
    """Final group for a Karin bone (renamed chain bone, PalHuman bone or merged ancestor)."""
    b = KB[kname]
    while b is not None:
        if b.name in RENAME: return RENAME[b.name]
        if b.name in DIRECT: return DIRECT[b.name]
        if b.name in ("Spine", "Chest"): return b.name
        b = b.parent
    return "pelvis"

def remap(obj, rows):
    pos = np.array([list(v.co) for v in obj.data.vertices])
    acc_all = []
    for i, row in enumerate(rows):
        acc = collections.defaultdict(float)
        for n, w in row:
            t = target_of(n)
            if t in ("Spine", "Chest"):
                for b, f in spine_split(n, pos[i]).items():
                    if f > 0: acc[b] += w * f
            else:
                acc[t] += w
        items = sorted(acc.items(), key=lambda kv: -kv[1])[:8]
        tot = sum(w for _, w in items) or 1.0
        acc_all.append([(n, w / tot) for n, w in items])
    for g in list(obj.vertex_groups):
        obj.vertex_groups.remove(g)
    groups = {}
    for i, row in enumerate(acc_all):
        for n, w in row:
            g = groups.get(n) or obj.vertex_groups.new(name=n)
            groups[n] = g
            g.add([i], w, "REPLACE")
    return acc_all

for name, obj in k_meshes.items():
    remap(obj, ROWS[name])

# ---------------------------------------------------------------- export armature (vanilla orientations, new joints)
bpy.ops.object.select_all(action="DESELECT")
v_arm.select_set(True); bpy.context.view_layer.objects.active = v_arm
bpy.ops.object.mode_set(mode="EDIT")
eb = v_arm.data.edit_bones
for b in list(eb):
    if b.name not in BASE:
        eb.remove(b)
to_arm = v_arm.matrix_world.inverted()
for b in eb:
    d = Vector(NEW[b.name]) - Vector(VM[b.name].translation)
    d = to_arm.to_3x3() @ d
    b.head = b.head + d; b.tail = b.tail + d
# chain bones: head at Karin joint (re-posed rigidly with the parent), X axis along the bone (UE convention)
CHAIN_INFO = {}
for kname, sname in RENAME.items():
    kb = KB[kname]
    Mi = KM[kname]
    h = Mi[:3, :3] @ kp(kname) + Mi[:3, 3]
    if kb.children:
        c = kb.children[0].name
        t = KM[c][:3, :3] @ kp(c) + KM[c][:3, 3]
    else:
        t = Mi[:3, :3] @ np.array(G @ (k_arm.matrix_world @ kb.tail_local)) + Mi[:3, 3]
    CHAIN_INFO[sname] = (h, t)
for kname, sname in RENAME.items():
    h, t = CHAIN_INFO[sname]
    e = eb.new(sname)
    xdir = norm(t - h)
    if np.linalg.norm(t - h) < 1e-3: xdir = np.array([0.0, 0.0, -1.0])
    # Blender bone Y = UE bone Y; the UE X axis (along the chain) is the Blender bone's X axis -> build roll so that
    # the bone's X axis points along the chain: tail along an arbitrary perpendicular, then align roll.
    up = np.array([0.0, 0.0, 1.0]) if abs(xdir[2]) < 0.9 else np.array([0.0, 1.0, 0.0])
    ydir = norm(np.cross(up, xdir))
    e.head = Vector(h); e.tail = Vector(h + ydir * 4.0)
    e.align_roll(Vector(np.cross(xdir, ydir)))   # bone Z axis
    kp_ = KB[kname].parent.name
    e.parent = eb[RENAME[kp_]] if kp_ in RENAME else eb[CHAIN_PARENT[sname]]
    e.use_connect = False
bpy.ops.object.mode_set(mode="OBJECT")
# verify the X axes of chain bones
xerr = 0.0
for sname, (h, t) in CHAIN_INFO.items():
    m = v_arm.matrix_world @ v_arm.data.bones[sname].matrix_local
    if np.linalg.norm(t - h) > 1e-3:
        xerr = max(xerr, float(np.degrees(np.arccos(np.clip(np.dot(np.array(m.to_3x3().col[0]), norm(t - h)), -1, 1)))))
REPORT["chain_x_axis_err_deg"] = round(xerr, 3)
v_arm.name = "Armature"; v_arm.data.name = "Armature"

# ---------------------------------------------------------------- two-sided skirt
# The VRM is single-sided (glTF doubleSided false); the skirt must also be seen from below / inside. A reversed copy of
# its faces (same UVs and weights, inward corner normals) gives it an inner side without a TwoSided MI (SB r12).
import bmesh
def two_sided(obj):
    me = obj.data
    nl = np.empty(len(me.loops) * 3, np.float32); me.corner_normals.foreach_get("vector", nl)
    me.attributes.new("ks_n", "FLOAT_VECTOR", "CORNER").data.foreach_set("vector", nl)
    bm = bmesh.new(); bm.from_mesh(me)
    dl = bm.faces.layers.int.new("ks_dup")
    out_ = bmesh.ops.duplicate(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces))["geom"]
    new_faces = [e for e in out_ if isinstance(e, bmesh.types.BMFace)]
    for f_ in new_faces: f_[dl] = 1
    bmesh.ops.reverse_faces(bm, faces=new_faces)
    bm.to_mesh(me); bm.free()
    nl = np.empty(len(me.loops) * 3, np.float32); me.attributes["ks_n"].data.foreach_get("vector", nl)
    dup = np.empty(len(me.polygons), np.int32); me.attributes["ks_dup"].data.foreach_get("value", dup)
    tot = np.empty(len(me.polygons), np.int32); me.polygons.foreach_get("loop_total", tot)
    nl = nl.reshape(-1, 3); nl[np.repeat(dup, tot) == 1] *= -1.0
    me.normals_split_custom_set(nl.tolist())
    for a_ in ("ks_n", "ks_dup"): me.attributes.remove(me.attributes[a_])
    return len(new_faces)
REPORT["two_sided"] = {"skirt": two_sided(k_meshes["skirt"])}

# ---------------------------------------------------------------- assemble body and head objects
def join(names, newname):
    bpy.ops.object.select_all(action="DESELECT")
    objs = [k_meshes[n] for n in names]
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1: bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active
    o.name = newname; o.data.name = newname
    for m in list(o.modifiers): o.modifiers.remove(m)
    o.parent = v_arm
    mod = o.modifiers.new("Armature", "ARMATURE"); mod.object = v_arm
    return o
body = join(BODY_MESHES, "SK_Karin_Body")
head = join(HEAD_MESHES, "SK_Karin_Head")
bpy.data.objects.remove(k_arm, do_unlink=True)

# face morph targets on the head
if "Body" in DELTAS:
    d = DELTAS["Body"]
    head.shape_key_add(name="Basis", from_mix=False)
    base = np.array([list(v.co) for v in head.data.vertices])
    REPORT["face_morphs"] = {}
    for mname, recipe in FACE_MORPHS.items():
        delta = np.zeros_like(base)
        for k, w in recipe.items():
            if k in d: delta += w * d[k]
        sk = head.shape_key_add(name=mname, from_mix=False)
        sk.data.foreach_set("co", (base + delta).ravel())
        REPORT["face_morphs"][mname] = {"recipe": recipe, "max_cm": round(float(np.linalg.norm(delta, axis=1).max()), 3)}

# ---------------------------------------------------------------- materials
MAT_RENAME = {"Karin_Face": "MI_Karin_Face", "Karin_Alpha": "MI_Karin_FaceAlpha", "Karin_Body": "MI_Karin_Skin",
              "Karin_Hair": "MI_Karin_Hair", "Karin_Hair_Transparent": "MI_Karin_HairTrans", "Karin_Costume": "MI_Karin_Costume"}
for m in bpy.data.materials:
    if m.name in MAT_RENAME: m.name = MAT_RENAME[m.name]
import bmesh
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
REPORT["dropped_alpha_faces"] = drop_slots(head, ("MI_Karin_FaceAlpha",))   # blush overlay: needs a translucent MI (later)
drop_slots(body, (), {"MI_Karin_HairTrans": "MI_Karin_Hair"})
REPORT["materials"] = {"body": [s.material.name for s in body.material_slots], "head": [s.material.name for s in head.material_slots]}


# ---------------------------------------------------------------- textures
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

# ---------------------------------------------------------------- physics groups for ue_build_abp.py
# Roots and derived capsules are the geometry; the dynamics below are only defaults. The shipped values come from
# scripts/physics_tune.json (merged and simulated by kawaii_sim.py, which exports the file ue_build_abp.py builds from).
# Positions are written in UE component space (cm): UE = Blender with Y negated.
def ue(p): return [round(float(p[0]), 3), round(float(-p[1]), 3), round(float(p[2]), 3)]
def bpos(n):
    m = v_arm.matrix_world @ v_arm.data.bones[n].matrix_local
    return np.array(m.translation)
SEQ = {head_: sq for head_, (_, sq) in SKEL_CHAINS.items()}
def used(head_):   # skeleton chain names actually present in the mesh
    return [n for n in SEQ[head_] if n in v_arm.data.bones]

# VRM colliders (capsules in collider-node space) -> re-posed with their Karin bone -> UE component space
import struct as _st
_b = open(KARIN_VRM, "rb").read(); _cl, = _st.unpack_from("<I", _b, 12)
_j = json.loads(_b[20:20 + _cl])
_nodes = _j["nodes"]
_par = {c: i for i, nd in enumerate(_nodes) for c in nd.get("children", [])}
def _local(nd):
    if "matrix" in nd:
        m = nd["matrix"]
        return Matrix([[m[0], m[4], m[8], m[12]], [m[1], m[5], m[9], m[13]], [m[2], m[6], m[10], m[14]], [m[3], m[7], m[11], m[15]]])
    t = nd.get("translation", [0, 0, 0]); r = nd.get("rotation", [0, 0, 0, 1]); sc = nd.get("scale", [1, 1, 1])
    return Matrix.Translation(t) @ Quaternion((r[3], r[0], r[1], r[2])).to_matrix().to_4x4() @ Matrix.Diagonal((sc[0], sc[1], sc[2], 1))
def _world(i):
    M = _local(_nodes[i])
    while i in _par:
        i = _par[i]; M = _local(_nodes[i]) @ M
    return M
GLTF2B = Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))   # glTF Y-up -> Blender Z-up
COLL = {}
for c in _j["extensions"]["VRMC_springBone"]["colliders"]:
    nd = _nodes[c["node"]]; name = nd["name"]
    i = c["node"]
    while _nodes[i]["name"] not in KB and i in _par:   # nearest Karin bone ancestor
        i = _par[i]
    kbone = _nodes[i]["name"]
    cap = c["shape"].get("capsule") or c["shape"].get("sphere")
    W = GLTF2B @ _world(c["node"])
    a = np.array(G @ (W @ Vector(cap["offset"])))
    b = np.array(G @ (W @ Vector(cap.get("tail", cap["offset"]))))
    a = apply(KM[kbone], a); b = apply(KM[kbone], b)
    COLL[name] = {"karin_bone": kbone, "a": a, "b": b, "radius": cap["radius"] * 100.0 * SCALE}
DRIVE = {"PBCollider_Head": "head", "PBCollider_UpperArm_L": "upperarm_l", "PBCollider_UpperArm_R": "upperarm_r",
         "PBCollider_Chest": "spine_03", "PBCollider_UpperLeg_L": "thigh_l", "PBCollider_UpperLeg_R": "thigh_r",
         "PBCollider_Hips": "pelvis"}
REPORT["vrm_colliders"] = {k: {"bone": v["karin_bone"], "a": ue(v["a"]), "b": ue(v["b"]), "r": round(v["radius"], 2)} for k, v in COLL.items()}

def seg_dist(p, a, b):
    d = b - a; t = np.clip(np.dot(p - a, d) / max(np.dot(d, d), 1e-9), 0, 1)
    return float(np.linalg.norm(p - (a + t * d)))
CAP_MARGIN = 0.5
def capsules(names, sim_joints, bone_r):
    """Capsules from VRM colliders; radius shrunk so every simulated joint is clear in the bind pose (SB r14 lesson)."""
    out = []
    for nm in names:
        c = COLL[nm]
        clear = min(seg_dist(p, c["a"], c["b"]) for p in sim_joints) - bone_r - CAP_MARGIN
        r = min(c["radius"], clear)
        if r < 2.0:
            REPORT["warnings"].append(f"capsule {nm} dropped (clearance {clear:.2f})"); continue
        out.append({"bone": DRIVE[nm], "a": ue(c["a"]), "b": ue(c["b"]), "radius": round(r, 2), "vrm_radius": round(c["radius"], 2)})
    return out

def group(name, heads, root_index, settings, colliders, **extra):
    roots, sim = [], []
    for h_ in heads:
        u = used(h_)
        roots.append(u[root_index])
        sim += [bpos(n) for n in u[root_index + 1:]]
    g_ = {"name": name, "roots": roots, "settings": settings,
          "capsules": capsules(colliders, sim, settings["radius"]) if sim else []}
    g_.update(extra)
    return g_
SKIRTS = ["Skirt_0", "Skirt_8"] + [f"Skirt_{i}_{s}" for i in range(1, 8) for s in "LR"]
HAIR_S = dict(damping=0.3, stiffness=0.15, world_loc=0.8, world_rot=0.8, radius=1.5, limit_angle=35)
PHYSICS = {"groups": [
    # waistband (first skirt joint) stays rigid with the pelvis; hip and hem joints simulate (SB r15)
    group("skirt", SKIRTS, 1, dict(damping=0.25, stiffness=0.12, world_loc=0.8, world_rot=0.8, radius=2.5, limit_angle=40),
          ["PBCollider_UpperLeg_L", "PBCollider_UpperLeg_R", "PBCollider_Hips"], gravity=[0, 0, -60]),
    group("tail", ["Tail"], 0, dict(damping=0.15, stiffness=0.06, world_loc=0.7, world_rot=0.7, radius=4.0, limit_angle=60),
          ["PBCollider_UpperLeg_L", "PBCollider_UpperLeg_R", "PBCollider_Hips"], gravity=[0, 0, -40]),
    group("twintails", ["Hair_tail_L", "Hair_tail_R"], 0, dict(damping=0.12, stiffness=0.08, world_loc=0.75, world_rot=0.75, radius=3.0, limit_angle=50),
          ["PBCollider_Chest", "PBCollider_Head", "PBCollider_UpperArm_L", "PBCollider_UpperArm_R"], gravity=[0, 0, -50]),
    group("sidehair", ["Hair_side_L", "Hair_side_R", "Cheek_Root_L", "Cheek_Root_R"], 0, dict(HAIR_S),
          ["PBCollider_Head", "PBCollider_Chest"]),
    group("fronthair", ["Hair_front", "Hair_front_L", "Hair_front_R"], 0, dict(HAIR_S, stiffness=0.2, limit_angle=25),
          ["PBCollider_Head"]),
    group("ears", ["Ear_L", "Ear_R"], 0, dict(damping=0.3, stiffness=0.3, world_loc=0.8, world_rot=0.8, radius=1.0, limit_angle=20), []),
    group("ribbons", ["Ribbon_L", "Ribbon_R", "Ribbon_camisole", "Ribbon_tops_L", "Ribbon_tops_R"], 0,
          dict(damping=0.3, stiffness=0.15, world_loc=0.8, world_rot=0.8, radius=1.0, limit_angle=45), [], gravity=[0, 0, -30]),
]}
with open(os.path.join(RUN, "physics.json"), "w", encoding="utf-8") as f:
    json.dump(PHYSICS, f, indent=1)
REPORT["physics_groups"] = {g_["name"]: {"roots": g_["roots"], "capsules": [(c["bone"], c["radius"], c["vrm_radius"]) for c in g_["capsules"]]}
                            for g_ in PHYSICS["groups"]}

# ---------------------------------------------------------------- hidden mesh (replaces every hair mesh)
hp = bpos("head")
hm = bpy.data.meshes.new("SK_Hidden")
hm.from_pydata([tuple(hp + np.array([0, 0, 1.0])), tuple(hp + np.array([0.01, 0, 1.0])), tuple(hp + np.array([0, 0.01, 1.0]))], [], [(0, 1, 2)])
hm.update()
hidden = bpy.data.objects.new("SK_Hidden", hm); bpy.context.scene.collection.objects.link(hidden)
hidden.data.materials.append(bpy.data.materials.get("MI_Karin_Skin"))
hidden.vertex_groups.new(name="head").add([0, 1, 2], 1.0, "REPLACE")
hidden.parent = v_arm
hidden.modifiers.new("Armature", "ARMATURE").object = v_arm

# ---------------------------------------------------------------- checks
bones = set(b.name for b in v_arm.data.bones)
for o in (body, head):
    REPORT.setdefault("groups_not_bones", {})[o.name] = [g.name for g in o.vertex_groups if g.name not in bones]
    REPORT.setdefault("verts", {})[o.name] = len(o.data.vertices)
REPORT["bones"] = len(bones)

# ---------------------------------------------------------------- export (stock FBX, cm via unit scale 0.01)
bpy.context.scene.unit_settings.scale_length = 0.01
kw = dict(use_selection=True, add_leaf_bones=False, bake_anim=False, use_mesh_modifiers=False,
          mesh_smooth_type="FACE", use_tspace=False, object_types={"ARMATURE", "MESH"})
for o, fn in ((body, "Karin_Body.fbx"), (head, "Karin_Head.fbx"), (hidden, "Hidden.fbx")):
    bpy.ops.object.select_all(action="DESELECT")
    v_arm.select_set(True); o.select_set(True)
    bpy.context.view_layer.objects.active = v_arm
    bpy.ops.export_scene.fbx(filepath=os.path.join(RUN, fn), **kw)
REPORT["fbx_kwargs"] = {k: (sorted(v) if isinstance(v, set) else v) for k, v in kw.items()}
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(RUN, "build.blend"))
with open(os.path.join(RUN, "report.json"), "w", encoding="utf-8") as f:
    json.dump(REPORT, f, indent=1, ensure_ascii=False)
print("BUILD_OK", RUN)
