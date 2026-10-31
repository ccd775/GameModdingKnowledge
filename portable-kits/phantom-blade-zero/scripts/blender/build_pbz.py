# Build Karin_Original for Phantom Blade Zero (Blender 4.2 background).
#
# Usage:
#   blender --background --factory-startup --python build_pbz.py -- <run_dir> [--scale 1.30]
#
# Output in <run_dir>:
#   Karin_Leader.fbx  -> Hun_Invs        (invisible leader mesh, every skeleton bone; sets the proportions animations retarget to)
#   Karin_Body.fbx    -> Hun_Body_Simple (body, costume, hair, ears, tail; physics chains on the game's chain bones)
#   Karin_Head.fbx    -> Hun_Head_New    (face; morph targets named after MetaHuman CTRL_expressions_* curves; adult:
#                                         a hidden first section, see face_slot0, and shown only by KarinFaceShow)
#   Karin_Face.fbx    -> Hun_BrowLashCard (adult: the same face, plain; see face_show)
#   Empty.fbx         -> Hun_Cloth / Hun_Scarf / Hun_Hair_Band / Hun_BrowLashCard (one hidden triangle)
#   Hat_Empty.fbx     -> Hats/Hun_Hat_00 (one hidden triangle on Hun_Hat_Skeleton)
#   physics.json      -> bodies + joints for SkinParts/Hun_Cloth_Streamer_Physics (RigidBody override of ABP_Hun_PostProcess)
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
SCALE = float(argv[argv.index("--scale") + 1]) if "--scale" in argv else 1.30
VARIANT = argv[argv.index("--variant") + 1] if "--variant" in argv else "adult"
# adult = Hun (BP_Renewal_Hun, leader Hun_Body_Simple, AnimationScaled). Its chain bones (Hair_*, bns_*) are also
#         posed by the game's animation and post-process nodes and stretched our hair and skirt, so physics is Chaos
#         cloth on mesh sections as for young (chains=True keeps the old RigidBody-chain path);
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
KARIN_VRM = _need("PBZ_SOURCE_VRM", "the Karin_Original VRM")
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
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=KARIN_VRM)
k_objs = [o for o in bpy.data.objects if o not in before]
k_arm = next(o for o in k_objs if o.type == "ARMATURE")
k_arm.name = "KarinArmature"; k_arm.data.name = "KarinArmature"
BODY_MESHES = ["body_2", "hair", "kemomimi", "tail", "pullover", "skirt", "underwear", "knee-socks", "shoes"]
HEAD_MESHES = ["Body"]   # the VRM's "Body" object is the face (Karin_Face + Karin_Alpha), it carries the face keys
k_meshes = {o.name: o for o in k_objs if o.type == "MESH" and o.name in BODY_MESHES + HEAD_MESHES}
for o in k_objs:
    if o.type != "ARMATURE" and o.name not in k_meshes:
        bpy.data.objects.remove(o, do_unlink=True)
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

# ---------------------------------------------------------------- physics chains on game chain bones
# Karin chain head -> game chain (root bone first; the root stays on its vanilla ray, unweighted and unsimulated),
# constraint parent body, and Karin joint index -> game bone index (0 = rigid with the parent region).
def chain_of(head):
    names = [head]
    while KB[names[-1]].children:
        kids = [c for c in KB[names[-1]].children if "_end" not in c.name]
        if not kids: break
        names.append(kids[0].name)
    return names
def seq(prefix, n, suffix=""):
    return [V(f"{prefix}{i:02d}{suffix}") for i in range(1, n + 1)]

def azim(p):     # 0 = front (-Y in Blender), +90 = character's left (+X)
    d = p - P0
    return math.degrees(math.atan2(d[0], -d[1]))
KSKIRT = ["Skirt_0", "Skirt_8"] + [f"Skirt_{i}_{s}" for i in range(1, 8) for s in "LR"]
K_ANG = {h: azim(kp(chain_of(h)[1])) for h in KSKIRT}
REPORT["karin_skirt_azimuth"] = {h: round(a, 1) for h, a in K_ANG.items()}
RENAME = {}        # Karin bone -> [(game bone, factor)]
CHAIN_POS = {}     # game bone -> new bind position (overrides the vanilla-ray placement)
SIM = []           # simulated chains: (name, [game bones in order], parent body)
if VCFG["chains"]:
    CHAINS = {
        "Hair_tail_L": dict(game=seq("Hair_1_", 4), parent="head", jmap=[0, 1, 1, 2, 2, 3]),
        "Hair_tail_R": dict(game=seq("Hair_2_", 4), parent="head", jmap=[0, 1, 1, 2, 2, 3]),
        "Hair_side_L": dict(game=seq("Hair_0_", 4), parent="head", jmap=[0, 1, 2]),
        "Hair_side_R": dict(game=seq("Hair_3_", 6), parent="head", jmap=[0, 1, 2]),
        "Tail": dict(game=seq("bns_skirt_3_", 5), parent="pelvis", jmap=[0, 1, 2, 3, 4, 4]),
    }
    # skirt: 8 game chains spread around the hips at 45 deg; Karin's 16 chains blend between the two nearest
    SKIRT_GAME = {0: seq("bns_frontSkirtArmorRibbon_", 5), 180: seq("bns_ribbon_0_", 5)}
    side = {}
    for s, sign in (("l", 1), ("r", -1)):
        roots = [V(f"bns_skirt_{i}_01_{s}") for i in range(3)]
        vpel = vp("pelvis")
        def vazim(q): return abs(math.degrees(math.atan2(q[0] - vpel[0], -(q[1] - vpel[1]))))
        tips = sorted(roots, key=lambda r: vazim(vp(r.replace("_01_", "_05_"))))
        for ang, r in zip((45, 90, 135), tips):
            SKIRT_GAME[sign * ang] = [V(r.replace("_01_", f"_{i:02d}_")) for i in range(1, 6)]
    REPORT["skirt_game_chains"] = {str(a): c[0] for a, c in SKIRT_GAME.items()}
    GANG = sorted(SKIRT_GAME)
    def bracket(a, angs=None):
        """Neighbours (lo, hi, t) of azimuth a in the sorted angle list (wraps at 180)."""
        angs = GANG if angs is None else angs
        a = ((a + 180.0) % 360.0) - 180.0
        if a < angs[0]: a += 360.0
        ext = angs + [angs[0] + 360.0]
        for i in range(len(angs)):
            if ext[i] <= a <= ext[i + 1]:
                return i, (i + 1) % len(angs), (a - ext[i]) / max(ext[i + 1] - ext[i], 1e-6)
        return 0, 0, 0.0

    for head, spec in CHAINS.items():
        kn = chain_of(head)
        g = spec["game"]
        for j, k in enumerate(kn):
            gi = spec["jmap"][min(j, len(spec["jmap"]) - 1)]
            RENAME[k] = [(V(spec["parent"]) if gi == 0 else g[gi], 1.0)]
        # positions: game bone gi sits at the first Karin joint mapped to it; trailing bones extend past the tip
        used = []
        for gi in range(1, len(g)):
            js = [j for j in range(len(kn)) if spec["jmap"][min(j, len(spec["jmap"]) - 1)] == gi]
            if js:
                CHAIN_POS[g[gi]] = apply(region(kn[js[0]]), kp(kn[js[0]])); used.append(g[gi])
        tip = apply(region(kn[-1]), ktail(kn[-1]))
        last = used[-1] if used else None
        for gi in range(1, len(g)):
            if g[gi] not in CHAIN_POS:
                step = (tip - CHAIN_POS[last]) if last else np.array([0, 0, -2.0])
                CHAIN_POS[g[gi]] = (CHAIN_POS[g[gi - 1]] if g[gi - 1] in CHAIN_POS else tip) + norm(step) * 2.0
        SIM.append((head, used, V(spec["parent"])))
    # skirt joints: game chain at azimuth A, depth d (1 = Karin .001 joint, 2 = .002, 3 = tip); Karin joint 0 -> pelvis
    KDEPTH = {h: chain_of(h) for h in KSKIRT}
    def karin_skirt_point(h, d):
        kn = KDEPTH[h]
        if d < len(kn): return apply(region(kn[d]), kp(kn[d]))
        return apply(region(kn[-1]), ktail(kn[-1]))
    for A, g in SKIRT_GAME.items():
        # interpolate Karin skirt joints at azimuth A
        order = sorted(KSKIRT, key=lambda h: K_ANG[h])
        angs = [K_ANG[h] for h in order]
        def at(d):
            i, j, t = bracket(float(A), angs)
            return (1 - t) * karin_skirt_point(order[i], d) + t * karin_skirt_point(order[j], d)
        for gi, d in ((1, 1), (2, 2), (3, 3)):
            CHAIN_POS[g[gi]] = at(d)
        CHAIN_POS[g[4]] = CHAIN_POS[g[3]] + norm(CHAIN_POS[g[3]] - CHAIN_POS[g[2]]) * 2.0
        SIM.append((f"skirt{A}", [g[1], g[2]], V("pelvis")))
    for h in KSKIRT:
        kn = KDEPTH[h]
        i, j, t = bracket(K_ANG[h]); lo, hi = GANG[i], GANG[j]
        RENAME[kn[0]] = [(V("pelvis"), 1.0)]
        for d in (1, 2):
            if d < len(kn):
                RENAME[kn[d]] = [(SKIRT_GAME[lo][d], 1.0 - t), (SKIRT_GAME[hi][d], t)]
    RENAME["Skirt_root"] = [(V("pelvis"), 1.0)]
    for n, p in CHAIN_POS.items():
        NEW[n] = p
    REPORT["sim_chains"] = {s[0]: s[1] for s in SIM}
else:
    # no chain bones on this skeleton: skirt panels blend from the pelvis toward the thighs with depth (less clipping
    # when the legs swing), tail and hair stay rigid with their parent region. The panels in front of / behind a thigh
    # follow mostly that thigh (a raised thigh went through the front panels when they split it 70/30 with the other leg).
    for h in KSKIRT:
        kn = chain_of(h)
        a = math.radians(K_ANG[h])
        t = min(max((math.sin(a) + 0.6) / 1.2, 0.0), 1.0)
        left = t * t * (3.0 - 2.0 * t)
        reach = 0.7 + 0.3 * abs(math.cos(a))
        for d, k in enumerate(kn):
            wt = (0.0, 0.45, 0.75)[min(d, 2)] * reach
            RENAME[k] = [(V("pelvis"), 1.0 - wt), (V("thigh_l"), wt * left), (V("thigh_r"), wt * (1.0 - left))]
    RENAME["Skirt_root"] = [(V("pelvis"), 1.0)]

# ---------------------------------------------------------------- mesh re-pose (LBS of the rigid region transforms)
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

# The upper skirt takes the skin weights of the body under it (inverse-distance mean of the 8 nearest body / underwear
# verts), fading to the panel weights by 1.5-5 cm of clearance and from 35% to 70% of the skirt height (a hem on skin
# weights would wrap each thigh like shorts): the pelvis-only waistband and the pelvis / thigh panel blend left the
# hip, buttock and thigh-root skin moving through the upper panels when running, where the cloth's max distance is too
# small for the colliders to push the panels out.
def skin_follow(obj, src_names, near, far):
    sp = np.array([list(v.co) for v in obj.data.vertices])
    ztop_, zbot_ = sp[:, 2].max(), sp[:, 2].min()
    hfac = 1.0 - smooth(ztop_ - sp[:, 2], 0.35 * (ztop_ - zbot_), 0.7 * (ztop_ - zbot_))
    bp = np.concatenate([np.array([list(v.co) for v in k_meshes[n].data.vertices]) for n in src_names])
    brows = [r for n in src_names for r in WROWS[n]]
    rows = []
    blend = []
    for i, p in enumerate(sp):
        d = np.linalg.norm(bp - p, axis=1)
        nn = np.argpartition(d, 8)[:8]
        b = (1.0 - float(smooth(d[nn].min(), near, far))) * float(hfac[i])
        acc = collections.defaultdict(float)
        for n, w in WROWS[obj.name][i]:
            acc[n] += (1.0 - b) * w
        iw = 1.0 / np.maximum(d[nn], 0.05)
        iw /= iw.sum()
        for j, wj in zip(nn, iw):
            for n, w in brows[j]:
                acc[n] += b * wj * w
        rows.append(top8(acc))
        blend.append(b)
    write_groups(obj, rows)
    WROWS[obj.name] = rows
    blend = np.array(blend)
    return {"verts": len(rows), "skin": int((blend > 0.99).sum()), "mixed": int(((blend > 0.01) & (blend <= 0.99)).sum())}
REPORT["skirt_skin_follow"] = skin_follow(k_meshes["skirt"], ["body_2", "underwear"], 1.5 * SCALE, 5.0 * SCALE)

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

# The skirt stays single-sided: its MI's parent (MI_ZeroHun_Cloth_02_b) is a two-sided material, and a duplicated
# reversed layer is welded onto the same particles by UE's cloth import (every triangle twice with opposite winding:
# the averaged normals cancel, the binding falls back to +X normals and the panels shaded as if wet).
import bmesh

# ---------------------------------------------------------------- cloth sections (variants without chain bones)
# The skirt, the twin tails, the bangs and side locks, the tail and the ears get their own material slots so the UE
# side can build Chaos cloth on those sections; the max-distance masks are geometric (plane / distance from the chain
# roots), written to cloth.json.
CLOTH = []
if VCFG["cloth"]:
    def new_mat(src, name):
        m = src.copy() if src else bpy.data.materials.new(name)
        m.name = name
        return m
    def chain_names(heads):
        out = set()
        for h in heads: out.update(chain_of(h))
        return out
    def set_slot(obj, mat, face_mask=None):
        me = obj.data
        if face_mask is None:
            me.materials.clear(); me.materials.append(mat)
            for f in me.polygons: f.material_index = 0
            return len(me.polygons)
        me.materials.append(mat)
        idx = len(me.materials) - 1
        n = 0
        for f in me.polygons:
            if face_mask[f.index]: f.material_index = idx; n += 1
        return n
    sk = k_meshes["skirt"]
    set_slot(sk, new_mat(sk.data.materials[0], "MI_Karin_Skirt"))
    tl = k_meshes["tail"]
    set_slot(tl, new_mat(tl.data.materials[0], "MI_Karin_Tail"))
    km = k_meshes["kemomimi"]
    set_slot(km, new_mat(km.data.materials[0], "MI_Karin_Ear"))
    hr = k_meshes["hair"]
    tails = chain_names(["Hair_tail_L", "Hair_tail_R"])
    vt = np.array([sum(w for n, w in row if n in tails) for row in ROWS["hair"]])
    fmask = [float(np.mean(vt[list(f.vertices)])) > 0.5 for f in hr.data.polygons]
    hair_mat = next((m for m in hr.data.materials if m and m.name == "Karin_Hair"), hr.data.materials[0])
    REPORT["cloth_faces"] = {"skirt": len(sk.data.polygons), "tail": len(tl.data.polygons), "ears": len(km.data.polygons),
                             "hairtail": set_slot(hr, new_mat(hair_mat, "MI_Karin_HairTail"), fmask)}
    # bangs and side locks: every hair face touching their chains; hair clips (costume faces) stay rigid with the head
    FRONT = ["Hair_front_root", "Hair_front_L", "Hair_front", "Hair_front_R", "Hair_side_L", "Hair_side_R"]
    fronts = chain_names(FRONT[1:])
    vf = np.array([sum(w for n, w in row if n in fronts) for row in ROWS["hair"]])
    hair_idx = {i for i, m in enumerate(hr.data.materials) if m and m.name in ("Karin_Hair", "Karin_Hair_Transparent")}
    fmask_f = [f.material_index in hair_idx and not fmask[f.index] and float(vf[list(f.vertices)].max()) > 0.02 for f in hr.data.polygons]
    REPORT["cloth_faces"]["hairfront"] = set_slot(hr, new_mat(hair_mat, "MI_Karin_HairFront"), fmask_f)
    hco = np.array([list(v.co) for v in hr.data.vertices])
    vin, vout = set(), set()
    for f in hr.data.polygons:
        (vin if fmask_f[f.index] else vout).update(f.vertices)
    seam = sorted(vin & vout)
    # the bang strands are closed shells (outer and inner sheet joined at the strand edges); welded into cloth particles
    # the edge verts got cancelling normals (30 particles near zero, 260 under half) and the bangs showed dark patches.
    # The inner sheet (facing the head) goes, the two-sided MI renders the outer sheet's back side in its place.
    hcen = hco.mean(axis=0)
    hf_i = next(i for i, m in enumerate(hr.data.materials) if m and m.name == "MI_Karin_HairFront")
    inner = [f.index for f in hr.data.polygons if f.material_index == hf_i
             and float(np.dot(np.array(f.normal), norm(np.array(f.center) - hcen))) < -0.3]
    bm = bmesh.new(); bm.from_mesh(hr.data); bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.faces[i] for i in inner], context="FACES_ONLY")   # verts kept: indices stay valid
    bm.to_mesh(hr.data); bm.free()
    REPORT["cloth_faces"]["hairfront_inner_removed"] = len(inner)
    zs = np.array([v.co[2] for v in sk.data.vertices]); ztop, zbot = float(zs.max()), float(zs.min())
    def root(k): return ue(apply(region(k), kp(k)))
    def chain_len(h):
        kn = chain_of(h)
        pts = [apply(region(k), kp(k)) for k in kn] + [apply(region(kn[-1]), ktail(kn[-1]))]
        return float(sum(np.linalg.norm(pts[i + 1] - pts[i]) for i in range(len(pts) - 1)))
    lt = (chain_len("Hair_tail_L") + chain_len("Hair_tail_R")) / 2.0
    le = (chain_len("Ear_L") + chain_len("Ear_R")) / 2.0
    ls = (chain_len("Hair_side_L") + chain_len("Hair_side_R")) / 2.0
    # the locks are joined to the rest of the hair: the mask measures from the border verts (anchors), so the border
    # stays fixed and the free range grows down the strands
    fa = hco[seam] if seam else np.array([apply(region(k), kp(k)) for k in FRONT])
    fsec = hco[sorted(vin)]
    fdist = np.array([np.linalg.norm(fa - p, axis=1).min() for p in fsec])
    fd1 = max(0.85 * float(fdist.max()), 3.0)
    # tail: fixed down to where it leaves the skirt (the floppy root swung up through the back panels); a tail vert is
    # under the skirt when it is above the hem and nearer the hip axis than the skirt at its height and azimuth
    tco = np.array([list(v.co) for v in tl.data.vertices])
    skc = np.array([list(v.co) for v in sk.data.vertices])
    def cyl(p):
        d = p[:, :2] - P0[:2]
        return np.hypot(d[:, 0], d[:, 1]), np.degrees(np.arctan2(d[:, 0], -d[:, 1]))
    sr, sa = cyl(skc); tr, ta = cyl(tco)
    under = np.zeros(len(tco), bool)
    for i in np.where(tco[:, 2] > zbot)[0]:
        m = (np.abs(skc[:, 2] - tco[i, 2]) < 3.0) & (np.abs((sa - ta[i] + 180.0) % 360.0 - 180.0) < 20.0)
        under[i] = bool(m.any()) and tr[i] < sr[m].max()
    ltail = chain_len("Tail")
    td0 = float(np.percentile(np.linalg.norm(tco[under] - apply(region("Tail"), kp("Tail")), axis=1), 95)) if under.sum() > 10 else 3.0
    td0 = min(max(td0, 3.0), 0.5 * ltail)
    REPORT["cloth_fixed"] = {"hairfront_anchors": len(fa), "hairfront_d1": round(fd1, 2), "hairfront_maxlen": round(float(fdist.max()), 2),
                             "tail_under_verts": int(under.sum()), "tail_d0": round(td0, 2), "tail_len": round(ltail, 2)}
    # anim drive pulls every particle toward its skinned position, so the twin tails, the tail and the flared skirt
    # keep Karin's modelled shape and only sway (without it they hang straight down under gravity). It also damps the
    # sway: at 0.4-0.7 the tails and ears barely moved, so the hair, tail and ears use a weak drive, low damping and
    # the full inertia of the reference bone (velocity scales 1); the skirt drive is weaker too, so the thigh colliders
    # can push the panels out instead of the drive pulling them back into a raised thigh. Only the waistband is fixed and
    # the free range grows fast below it (thighs and buttocks went through the upper panels while running bent over).
    # Ears: no gravity and no colliders; a weak drive (0.18-0.3) let the ear shell crumple (dented outline at rest),
    # so a firmer drive and a smaller free range. Bangs and side locks: no colliders (the head sphere would lift them
    # off the forehead), weak gravity.
    def drive(k): return {"AnimDriveStiffness": {"Low": k, "High": k}, "AnimDriveDamping": {"Low": 0.6, "High": 0.6}}
    def inertia(s): return {"LinearVelocityScale": {"X": s, "Y": s, "Z": s}, "AngularVelocityScale": s}
    hs = ztop - zbot
    # Pleat shading: the skirt is low-poly with knife pleats one face wide (16 pleats, 203 folds sharper than 150 deg).
    # UE welds the section into cloth particles, averages the unit triangle normals per particle and rebuilds every
    # render normal from those (MeshToMeshVertData); at a third of the face corners that average is 60-90 deg off the
    # face (55 corners past 90), so the rebuilt normals swung as the simulation opened and closed the pleats and the
    # folds glinted. A smooth shell over the outer folds (the skirt's own rows, 32 columns, its skin weights) is
    # simulated instead (slot MI_Karin_SkirtSim, disabled for rendering on the UE side) and the pleated skirt is bound
    # to it, so the pleats keep their modelled shape and normals.
    def skirt_shell(src, ncol=32, win=math.radians(12.0)):
        co = np.array([list(v.co) for v in src.data.vertices])
        key = {}
        pid = np.array([key.setdefault(tuple(np.float32(p).tolist()), len(key)) for p in co])
        P = np.zeros((len(key), 3)); P[pid] = co
        ecount, nbr = collections.Counter(), collections.defaultdict(set)
        for f in src.data.polygons:
            vs = [int(pid[v]) for v in f.vertices]
            for a, b in zip(vs, vs[1:] + vs[:1]):
                ecount[(min(a, b), max(a, b))] += 1; nbr[a].add(b); nbr[b].add(a)
        hem = sorted({x for e, n in ecount.items() if n == 1 for x in e})
        row = {p: 0 for p in hem}; q = collections.deque(hem)   # rows by edge steps from the hem (19 rings, top pole)
        while q:
            u = q.popleft()
            for w in nbr[u]:
                if w not in row: row[w] = row[u] + 1; q.append(w)
        c = P[:, :2].mean(axis=0)
        r = np.hypot(P[:, 0] - c[0], P[:, 1] - c[1]); th = np.arctan2(P[:, 0] - c[0], -(P[:, 1] - c[1]))
        rows = collections.defaultdict(list)
        for p, k in row.items(): rows[k].append(p)
        top = max(rows)
        pole = rows[top][0] if len(rows[top]) == 1 else None
        nring = top if pole is not None else top + 1
        cols = -math.pi + (np.arange(ncol) + 0.5) * 2.0 * math.pi / ncol
        V, depth = [], []
        for k in range(nring):
            idx = np.array(rows[k])
            rk, zk = np.zeros(ncol), np.zeros(ncol)
            for j, a in enumerate(cols):
                d = np.abs((th[idx] - a + math.pi) % (2.0 * math.pi) - math.pi)
                m = d < win   # a window of one pleat holds an outer fold
                rk[j], zk[j] = r[idx][m].max(), P[idx[m], 2].mean()
            rk = (np.roll(rk, 1) + 2.0 * rk + np.roll(rk, -1)) / 4.0
            for j, a in enumerate(cols):
                V.append([c[0] + rk[j] * math.sin(a), c[1] - rk[j] * math.cos(a), zk[j]])
            ai = np.round((th[idx] + math.pi) / (2.0 * math.pi) * ncol - 0.5).astype(int) % ncol
            depth.extend((rk[ai] - r[idx]).tolist())
        F = [(k * ncol + j, k * ncol + (j + 1) % ncol, (k + 1) * ncol + (j + 1) % ncol, (k + 1) * ncol + j)
             for k in range(nring - 1) for j in range(ncol)]
        if pole is not None:
            V.append(P[pole].tolist())
            F += [((nring - 1) * ncol + j, (nring - 1) * ncol + (j + 1) % ncol, len(V) - 1) for j in range(ncol)]
        me = bpy.data.meshes.new("skirt_sim")
        me.from_pydata(V, [], F); me.update()
        Va = np.array(V)
        out = float(np.mean([np.dot(np.array(f.normal), norm(np.array([*(np.array(f.center)[:2] - c), 0.0])))
                             for f in me.polygons[:(nring - 1) * ncol]]))
        if out < 0.0:   # side faces must face away from the hip axis (backstop and binding normals)
            me.clear_geometry(); me.from_pydata(V, [], [tuple(reversed(f)) for f in F]); me.update()
        for f in me.polygons: f.use_smooth = True
        ob = bpy.data.objects.new("skirt_sim", me)
        for col in src.users_collection: col.objects.link(ob)
        ob.matrix_world = src.matrix_world.copy()
        for uv in src.data.uv_layers: me.uv_layers.new(name=uv.name)
        me.materials.append(new_mat(None, "MI_Karin_SkirtSim"))
        W = WROWS[src.name]
        wrows = []
        for p in Va:   # inverse-distance mean of the 6 nearest skirt verts' weights
            d = np.linalg.norm(co - p, axis=1)
            nn = np.argpartition(d, 6)[:6]
            iw = 1.0 / np.maximum(d[nn], 0.05); iw /= iw.sum()
            acc = collections.defaultdict(float)
            for j, wj in zip(nn, iw):
                for n, w in W[j]: acc[n] += wj * w
            wrows.append(top8(acc))
        write_groups(ob, wrows)
        dep = np.array(depth)
        return ob, {"verts": len(V), "faces": len(F), "rings": nring, "pole": pole is not None, "flipped": out < 0.0,
                    "fold_depth_p50_p95_max": [round(float(np.percentile(dep, x)), 2) for x in (50, 95, 100)],
                    "outside_shell": int((dep < -0.05).sum())}
    k_meshes["skirt_sim"], REPORT["skirt_sim"] = skirt_shell(sk)
    # Skirt backstop: the skinned skirt stays outside the body in the test poses (abduction, running, bent running;
    # probe_r4), so the clipping came from the simulation: gravity and inertia (the panels lagging behind a running body)
    # moved the panels inward through the skin, where the free range near the waist is too small for the colliders to
    # push them back out. A plane-like sphere (radius 50) right behind each free particle's skinned position keeps the
    # panels from sinking inward; they still swing outward. CCD keeps fast thighs from passing through the panels.
    sc = ue(np.array([skc[:, 0].mean(), skc[:, 1].mean(), 0.0]))
    CLOTH = [
        {"slot": "MI_Karin_Skirt", "name": "Karin_Skirt", "max_distance": round(0.4 * hs, 2),
         "mask": {"type": "plane", "anchors": [[0.0, 0.0, round(ztop, 3)]], "dir": [0, 0, -1], "d0": round(0.08 * hs, 2), "d1": round(0.6 * hs, 2),
                  "sim_slot": "MI_Karin_SkirtSim",
                  "backstop": {"distance": 0.0, "radius": 50.0, "axis": [round(float(sc[0]), 3), round(float(sc[1]), 3), 0.0], "min_dot": 0.3}},
         "config": {"DampingCoefficient": 0.08, "FrictionCoefficient": 0.2, "CollisionThickness": 2.5, "GravityScale": 0.5,
                    "bUseCCD": True, "bUseLegacyBackstop": False} | inertia(0.8) | drive(0.3)},
        {"slot": "MI_Karin_HairTail", "name": "Karin_HairTails", "max_distance": round(0.45 * lt, 2),
         "mask": {"type": "radial", "anchors": [[round(float(x), 3) for x in root("Hair_tail_L")], [round(float(x), 3) for x in root("Hair_tail_R")]],
                  "d0": 4.0, "d1": round(0.9 * lt, 2)},
         "config": {"DampingCoefficient": 0.03, "FrictionCoefficient": 0.1, "CollisionThickness": 1.5, "GravityScale": 0.5}
                   | inertia(1.0) | drive(0.12)},
        {"slot": "MI_Karin_Tail", "name": "Karin_Tail", "max_distance": round(0.45 * chain_len("Tail"), 2),
         "mask": {"type": "radial", "anchors": [[round(float(x), 3) for x in root("Tail")]], "d0": round(td0, 2),
                  "d1": round(max(td0 + 5.0, 0.9 * ltail), 2)},
         "config": {"DampingCoefficient": 0.03, "FrictionCoefficient": 0.1, "CollisionThickness": 1.5, "GravityScale": 0.4}
                   | inertia(1.0) | drive(0.12)},
        {"slot": "MI_Karin_HairFront", "name": "Karin_HairFront", "max_distance": round(0.4 * ls, 2), "collide": False,
         "mask": {"type": "radial", "anchors": [[round(float(x), 3) for x in ue(a)] for a in fa], "d0": 0.5, "d1": round(fd1, 2)},
         "config": {"DampingCoefficient": 0.05, "FrictionCoefficient": 0.1, "CollisionThickness": 0.5, "GravityScale": 0.3}
                   | inertia(1.0) | drive(0.2)},
        {"slot": "MI_Karin_Ear", "name": "Karin_Ears", "max_distance": round(0.22 * le, 2), "collide": False,
         "mask": {"type": "radial", "anchors": [[round(float(x), 3) for x in root("Ear_L")], [round(float(x), 3) for x in root("Ear_R")]],
                  "d0": round(0.3 * le, 2), "d1": round(1.0 * le, 2)},
         "config": {"DampingCoefficient": 0.1, "FrictionCoefficient": 0.1, "CollisionThickness": 0.5, "GravityScale": 0.0}
                   | inertia(1.0) | drive(0.5)},
    ]
    json.dump(CLOTH, open(os.path.join(RUN, f"cloth{VCFG['suffix']}.json"), "w", encoding="utf-8"), indent=1)
    REPORT["cloth"] = [{k: c[k] for k in ("slot", "max_distance")} | {"mask": c["mask"]} for c in CLOTH]

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
for n in ("body_2", "pullover", "underwear", "knee-socks", "shoes"):   # collider radii: body and tight clothes only
    k_meshes[n].vertex_groups.new(name="_coll").add(list(range(len(k_meshes[n].data.vertices))), 1.0, "REPLACE")
body = join(BODY_MESHES + [n for n in ("skirt_sim",) if n in k_meshes], "SK_Karin_Body", arm_body)
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
MAT_RENAME = {"Karin_Face": "MI_Karin_Face", "Karin_Alpha": "MI_Karin_FaceAlpha", "Karin_Body": "MI_Karin_Skin",
              "Karin_Hair": "MI_Karin_Hair", "Karin_Hair_Transparent": "MI_Karin_HairTrans", "Karin_Costume": "MI_Karin_Costume"}
for m in bpy.data.materials:
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
REPORT["dropped_alpha_faces"] = drop_slots(head, ("MI_Karin_FaceAlpha",))
drop_slots(body, (), {"MI_Karin_HairTrans": "MI_Karin_Hair"})
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

if VCFG["chains"]:
    def icom(m, r, h):
        L = h + 2 * r
        return m * (L * L / 12.0 + r * r / 4.0)
    TUNE = {
        "Hair_tail": dict(mass=[0.25, 0.2, 0.15], freq=1.3, zeta=0.45, lin=8.0, ang=4.0, swing=[40, 30, 30], twist=6, r=2.5,
                          collide=[hd, nk, s4, V("upperarm_l"), V("upperarm_r")]),
        "Hair_side": dict(mass=[0.12, 0.1, 0.08], freq=2.0, zeta=0.5, lin=8.0, ang=4.0, swing=[25, 25, 25], twist=5, r=1.5,
                          collide=[hd, s4]),
        "Tail": dict(mass=[0.4, 0.3, 0.25, 0.2], freq=1.5, zeta=0.45, lin=8.0, ang=4.0, swing=[30, 25, 25, 25], twist=5, r=3.0,
                     collide=[pel, V("thigh_l"), V("thigh_r")]),
        "skirt": dict(mass=[0.15, 0.1], freq=1.6, zeta=0.5, lin=8.0, ang=4.0, swing=[35, 30], twist=5, r=2.0,
                      collide=[V("thigh_l"), V("thigh_r"), V("calf_l"), V("calf_r")]),
    }
    bodies, joints, disable = list(COLL), [], set()
    for name, bones, parent in SIM:
        t = TUNE["skirt"] if name.startswith("skirt") else TUNE["Hair_tail"] if name.startswith("Hair_tail") else \
            TUNE["Hair_side"] if name.startswith("Hair_side") else TUNE["Tail"]
        # each simulated bone: capsule from its joint to the next chain joint (or the tip)
        gchain = None
        for h, spec in CHAINS.items():
            if h == name: gchain = spec["game"]
        if gchain is None:
            gchain = next(g for A, g in SKIRT_GAME.items() if f"skirt{A}" == name)
        segs = []
        for k, b in enumerate(bones):
            nxt = gchain[gchain.index(b) + 1] if gchain.index(b) + 1 < len(gchain) else None
            a = NEW[b]; e = NEW[nxt] if nxt else a + np.array([0, 0, -3.0])
            L = float(np.linalg.norm(e - a))
            r = min(t["r"], max(0.6, 0.25 * L))
            m = t["mass"][min(k, len(t["mass"]) - 1)]
            bodies.append(capsule(b, a + (e - a) * (r / max(L, 1e-6)), e - (e - a) * (r / max(L, 1e-6)), r, False, mass=m,
                                  lin_damp=t["lin"], ang_damp=t["ang"]))
            segs.append((b, m, r, max(L - 2 * r, 0.1), L))
        w = 2 * math.pi * t["freq"]
        for k, (b, m, r, h, L) in enumerate(segs):
            isub = 0.0
            for j in range(k, len(segs)):
                dist = sum(s[4] for s in segs[k:j]) + segs[j][4] / 2.0
                isub += icom(segs[j][1], segs[j][2], segs[j][3]) + segs[j][1] * dist * dist
            scale = isub / icom(m, r, h)
            joints.append({"child": b, "parent": parent if k == 0 else segs[k - 1][0],
                           "swing1": float(t["swing"][min(k, len(t["swing"]) - 1)]), "swing2": float(t["swing"][min(k, len(t["swing"]) - 1)]),
                           "twist": float(t["twist"]), "drive_stiffness": round(w * w * scale, 1), "drive_damping": round(2 * t["zeta"] * w * scale, 2)})
            for c in KIN:
                if c not in t["collide"]: disable.add((b, c))
    sims = [s for s in SIM]
    for i, a in enumerate(sims):
        for b in sims[i + 1:]:
            for x in a[1]:
                for y in b[1]:
                    disable.add((x, y))
    for i, a in enumerate(KIN):
        for b in KIN[i + 1:]:
            disable.add((a, b))
    PHYS = {"bodies": bodies, "joints": joints, "disable_pairs": sorted([list(p) for p in disable])}
    json.dump(PHYS, open(os.path.join(RUN, "physics.json"), "w", encoding="utf-8"), indent=1)
    REPORT["physics"] = {"bodies": len(bodies), "joints": len(joints), "kinematic": KIN}

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
