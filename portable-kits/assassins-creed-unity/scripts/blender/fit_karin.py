"""ACU copy of ACOd/scripts/fit_karin.py (2026-10-24): Unity has no Neck1 (Neck -> Head), so the Neck weight split
only runs when the target rig has Neck1. Otherwise identical to the Odyssey copy (KP bones +X down the chain).
ACOd copy of ACShadow/scripts/fit_karin.py (2026-10-19): KP bones oriented +X down the chain (Odyssey).

Fit the Karin model onto Naoe's skeleton (Blender 5.0, background).

blender -b --factory-startup --python fit_karin.py -- <naoe_fit_skeleton.glb> <karin.blend> <out.blend>
        [--scale auto|<s>] [--head-scale 1.0] [--max-influences 4]

Result: Karin meshes (shape-key mix baked) skinned to Naoe's armature ("NaoeRig") by Naoe bone names.
v2 policy (2026-09-27, after in-game proportion review):
- joint positions are driven by Naoe's animations (skeleton rest edits have no effect, diag5/6), so the mesh
  is fitted to Naoe's joints, but
- global scale = least-squares fit of Karin's torso joints (thighs, chest, neck, shoulders, head) onto Naoe's
  (≈1.684; v1 used 1.48 from the Hips joint, which sits 8.6 cm above the thighs in VRoid rigs and made every
  segment stretch 15–19 %),
- RIGID bones (torso + head and everything parented to them: jacket, breasts, hair, tail) keep Karin's exact
  shape: no stretch, no joint move; they only follow Naoe's joints with a few cm pivot offset,
- limb joints (clavicle→hand, thigh→toes, fingers) snap onto Naoe's joints so hands/feet stay exact; the limb
  stretch uses Karin's joint-to-joint distance (not VRoid bone length),
- inherit_scale = NONE on every bone (v1 let jacket/breast bones inherit the Spine/Chest stretch).
Frames: Naoe (as imported from AnvilToolkit GLB): forward +X, up -Y, left +Z.
        Karin source (VRoid-like): forward -Y, up +Z, left +X.
"""
import bpy, sys, json, math
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1:]
naoe_glb, karin_blend, out_blend = argv[0], argv[1], argv[2]
def opt(name, default):
    return float(argv[argv.index(name) + 1]) if name in argv else default
SCALE = argv[argv.index("--scale") + 1] if "--scale" in argv else "auto"
HEAD_SCALE = opt("--head-scale", 1.0)
MAX_INF = int(opt("--max-influences", 4))
# feet (v3, 2026-09-27): at the torso LSQ scale Karin's ankle sits 17-20 cm above her platform soles, Naoe's/Yasuke's
# ankle joint only 8 cm above the ground, so snapped feet sank 9-11 cm. --ground <h> keeps the foot flat (Karin's
# orientation, uniform --foot-scale about the ankle, toes rigid with the foot) and lifts the sole to height h
# (vanilla Naoe shoes bottom out at -0.014); the lift ramps over the shin (0 at the knee) so the knee pivot stays exact.
FOOT_SCALE = opt("--foot-scale", 1.0)
GROUND = opt("--ground", None)
# --foot-squash <s> (2026-10-07): squash only the height of the foot below the ankle by s (about the ankle) instead of
# shrinking the whole shoe — with --foot-scale 1 --foot-squash 0.8 the sole needs the same lift as --foot-scale 0.8,
# but the shoes keep Karin's length and width (user: the 0.8 shoes looked smaller than on the original model)
FOOT_SQUASH = opt("--foot-squash", None)
# --leg-girth <thigh>,<shin>: radial scale of everything skinned to the thigh / shin toward the leg axis (Yasuke: the
# UnendingFlame strap harness + side cloak read as fat thighs in game next to PicodraTech, user 2026-09-27; dropped
# again 2026-10-13 — that impression came mostly from Yasuke's 1.1 entity scale, fixed in the same version)
LEG_GIRTH = [float(v) for v in argv[argv.index("--leg-girth") + 1].split(",")] if "--leg-girth" in argv else None
# --shoulder-narrow <d> [--shoulder-hang <deg>] (2026-10-13): Yasuke's shoulder joints sit 18.7 cm off the centre line
# (Naoe 15.3, Karin's own 11.3 at the fit scale), so snapping the arms there stretched the bare shoulder line into a
# man's shoulders (user). The animations keep the arm pivot there; instead the shoulder end of the upper arm and the
# outer end of the clavicle are moved d toward the body AS SEEN WITH THE ARM HANGING (upper arm <deg> off vertical),
# and that offset is un-posed to the bind pose (rest = (blended deform)^-1 (posed + offset)). Exact for the hanging and
# forward/back-swinging arm (flexion keeps a medial offset medial); raised sideways the offset turns down (T-pose) and
# outward (overhead). Elbow, forearm and hand stay on the joints (weapons are held in the hand).
SHOULDER_NARROW = opt("--shoulder-narrow", None)
SHOULDER_HANG = opt("--shoulder-hang", 10.0)
# physics chains: Karin secondary-bone roots kept as their own bones ("KP_<name>") under the mapped Naoe bone,
# so an add-on skeleton with Reflex3 Physics constraints can drive them (make_phys_skel.py)
PHYS_ROOTS = argv[argv.index("--phys") + 1].split(",") if "--phys" in argv else []
def kp_name(n):
    return "KP_" + n.replace(".", "_")

# Karin bone -> (Naoe bone, Naoe bone whose head is the stretch target or None)
RIGID = {"Hips", "Spine", "Chest", "Neck", "Head"}
LSQ_PAIRS = [("UpperLeg.L", "LeftUpLeg"), ("UpperLeg.R", "RightUpLeg"), ("Neck", "Neck"), ("Chest", "Spine2"),
             ("UpperArm.L", "LeftArm"), ("UpperArm.R", "RightArm"), ("Head", "Head")]
MAP = {
    "Hips": ("Hips", "Spine"),
    "Spine": ("Spine", "Spine2"),
    "Chest": ("Spine2", "Neck"),
    "Neck": ("Neck", "Head"),
    "Head": ("Head", None),
}
for s, S in (("L", "Left"), ("R", "Right")):
    MAP.update({
        f"Shoulder.{s}": (f"{S}Clavicle", f"{S}Arm"),
        f"UpperArm.{s}": (f"{S}Arm", f"{S}ForeArm"),
        f"LowerArm.{s}": (f"{S}ForeArm", f"{S}Hand"),
        f"Hand.{s}": (f"{S}Hand", f"{S}HandMiddle1"),
        f"UpperLeg.{s}": (f"{S}UpLeg", f"{S}Leg"),
        f"LowerLeg.{s}": (f"{S}Leg", f"{S}Foot"),
        f"Foot.{s}": (f"{S}Foot", f"{S}FootThumb1"),
        f"Toes.{s}": (f"{S}FootThumb1", None),
    })
    for kf, nf in (("Index", "Index"), ("Middle", "Middle"), ("Ring", "Ring"), ("Little", "Pinky")):
        MAP[f"{kf}Proximal.{s}"] = (f"{S}Hand{nf}1", f"{S}Hand{nf}2")
        MAP[f"{kf}Intermediate.{s}"] = (f"{S}Hand{nf}2", f"{S}Hand{nf}3")
        MAP[f"{kf}Distal.{s}"] = (f"{S}Hand{nf}3", None)
    MAP[f"ThumbProximal.{s}"] = (f"{S}HandThumb1", f"{S}HandThumb2")
    MAP[f"ThumbIntermediate.{s}"] = (f"{S}HandThumb2", f"{S}HandThumb3")
    MAP[f"ThumbDistal.{s}"] = (f"{S}HandThumb3", None)

def ctx_for(obj, mode=None):
    bpy.ops.object.mode_set(mode='OBJECT') if bpy.context.object and bpy.context.object.mode != 'OBJECT' else None
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    if mode:
        bpy.ops.object.mode_set(mode=mode)

# --- 1. Naoe rig -------------------------------------------------------------------------
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=naoe_glb, merge_vertices=False, import_shading='NORMALS',
                          guess_original_bind_pose=True, bone_heuristic='BLENDER')
naoe = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
naoe.name = "NaoeRig"
for o in list(bpy.data.objects):
    if o.type == 'MESH':
        if o.vertex_groups:
            o.name = "NaoeHeadRef"; o.hide_render = True; o.hide_set(True)
        else:
            bpy.data.objects.remove(o)
nb = naoe.data.bones
missing = [v[0] for v in MAP.values() if v[0] not in nb] + [v[1] for v in MAP.values() if v[1] and v[1] not in nb]
if missing:
    raise SystemExit(f"Naoe bones missing: {missing}")

# --- 2. Karin ----------------------------------------------------------------------------
with bpy.data.libraries.load(karin_blend, link=False) as (src, dst):
    dst.objects = [n for n in src.objects]
for o in dst.objects:
    if o is not None:
        bpy.context.scene.collection.objects.link(o)
karm = [o for o in dst.objects if o and o.type == 'ARMATURE'][0]
kmeshes = [o for o in dst.objects if o and o.type == 'MESH']
# rig naming: PicodraTech uses "UpperArm.L"/"Toes.L", UnendingFlame uses "UpperArm_L"/"Toe_L",
# Karin_Original (Unity FBX) uses "LeftUpperArm"/"LeftToeBase"
_kb = karm.data.bones
def adapt(n):
    if n in _kb:
        return n
    m = n.replace(".L", "_L").replace(".R", "_R")
    if m not in _kb:
        m = m.replace("Toes", "Toe")
    if m not in _kb and n[-2:] in (".L", ".R"):
        u = ("Left" if n[-1] == "L" else "Right") + n[:-2]
        m = u if u in _kb else u.replace("Toes", "ToeBase")
    return m
MAP = {adapt(k): v for k, v in MAP.items() if adapt(k) in _kb}
RIGID = {adapt(k) for k in RIGID}
LSQ_PAIRS = [(adapt(a), b) for a, b in LSQ_PAIRS]
PHYS_ROOTS = [adapt(r) for r in PHYS_ROOTS]
print("FIT rig bones", len(_kb), "mapped", len(MAP))
for o in [o for o in dst.objects if o and o.type not in ('ARMATURE', 'MESH')]:
    bpy.data.objects.remove(o)

# bake shape-key mix
for o in kmeshes:
    if o.data.shape_keys:
        ctx_for(o)
        bpy.ops.object.shape_key_remove(all=True, apply_mix=True)

# --fix-bones a,b,c (2026-10-07): a chain collapsed to a point in the source (PicodraTech's hairpin tassel Ornaments_1..4
# all sit at the head centre with zero length, so physics has no lever) is rebuilt along the centroids of the vertices
# skinned to each bone: head_1 = centroid_1, head_k = midpoint of centroids k-1 and k, last tail extrapolated.
FIX_BONES = [adapt(n) for n in argv[argv.index("--fix-bones") + 1].split(",")] if "--fix-bones" in argv else []
if FIX_BONES:
    cent = {}
    for n in FIX_BONES:
        acc, wsum = Vector(), 0.0
        for o in kmeshes:
            g = o.vertex_groups.get(n)
            if g is None:
                continue
            for v in o.data.vertices:
                for e in v.groups:
                    if e.group == g.index and e.weight > 0.05:
                        acc += (o.matrix_world @ v.co) * e.weight; wsum += e.weight
        if not wsum:
            raise SystemExit(f"--fix-bones: no vertices skinned to {n}")
        cent[n] = acc / wsum
    heads = [cent[FIX_BONES[0]]] + [(cent[a] + cent[b]) / 2 for a, b in zip(FIX_BONES, FIX_BONES[1:])]
    tails = heads[1:] + [cent[FIX_BONES[-1]] * 2 - heads[-1]]
    inv = karm.matrix_world.inverted()
    ctx_for(karm, 'EDIT')
    for n, h, t in zip(FIX_BONES, heads, tails):
        e = karm.data.edit_bones[n]
        e.use_connect = False
        e.head, e.tail = inv @ h, inv @ t
    bpy.ops.object.mode_set(mode='OBJECT')
    print("FIT fixed bones", [(n, tuple(round(c, 3) for c in h)) for n, h in zip(FIX_BONES, heads)])

# --- 3. frame + uniform scale (+ translation) --------------------------------------------
R = Matrix(((0, -1, 0, 0), (0, 0, -1, 0), (1, 0, 0, 0), (0, 0, 0, 1)))
def nhead(n):
    return naoe.matrix_world @ nb[n].head_local
kf = R @ karm.matrix_world
ks = [kf @ karm.data.bones[a].head_local for a, _ in LSQ_PAIRS]
ns = [nhead(b) for _, b in LSQ_PAIRS]
kc = sum(ks, Vector()) / len(ks); nc = sum(ns, Vector()) / len(ns)
if SCALE == "auto":
    SCALE = sum((k - kc).dot(n - nc) for k, n in zip(ks, ns)) / sum((k - kc).length_squared for k in ks)
else:
    SCALE = float(SCALE)
T = nc - SCALE * kc
print(f"FIT scale={SCALE:.4f} translate=({T.x:.4f},{T.y:.4f},{T.z:.4f})")
karm.matrix_world = Matrix.Translation(T) @ Matrix.Scale(SCALE, 4) @ kf
bpy.ops.object.select_all(action='DESELECT')
for o in [karm] + kmeshes:
    o.select_set(True)
bpy.context.view_layer.objects.active = karm
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# --- 4. pose fit (direct pose matrices) ----------------------------------------------------
ctx_for(karm, 'POSE')
pre = [(pb.name, c.type) for pb in karm.pose.bones for c in pb.constraints]
print("FIT removed source constraints", pre)
for pb in karm.pose.bones:
    for c in list(pb.constraints):
        pb.constraints.remove(c)
    pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.rotation_euler = (0, 0, 0); pb.scale = (1, 1, 1)
if karm.animation_data:
    karm.animation_data_clear()
for b in karm.data.bones:
    b.inherit_scale = 'NONE'
bpy.context.view_layer.update()
KINV = {v[0]: k for k, v in MAP.items()}  # Naoe bone -> Karin bone
order = sorted(karm.pose.bones, key=lambda pb: len(pb.parent_recursive))
flat_foot = {}  # Karin foot bone -> its fitted pose matrix (flat-foot mode)
for pb in order:
    if pb.name not in MAP or pb.name in RIGID:
        continue
    nbone, tail = MAP[pb.name]
    bone = karm.data.bones[pb.name]
    rest = bone.matrix_local
    rest_rot = rest.to_quaternion()
    head_t = nhead(nbone)
    sc = Vector((1, 1, 1))
    kchild = KINV.get(tail) if tail else None
    if GROUND is not None and nbone.endswith("Foot"):
        # flat foot: Karin's orientation, uniform scale about Naoe's ankle joint
        pb.matrix = Matrix.LocRotScale(head_t, rest_rot, Vector((FOOT_SCALE,) * 3))
        flat_foot[pb.name] = (rest, pb.matrix.copy())
        bpy.context.view_layer.update()
        continue
    if GROUND is not None and nbone.endswith("FootThumb1") and pb.parent and pb.parent.name in flat_foot:
        # toes rigid with the flat foot (the toe pivot is Naoe's; Karin's toe joint lands where the foot puts it)
        frest, fpose = flat_foot[pb.parent.name]
        h = fpose.to_translation() + FOOT_SCALE * (rest.to_translation() - frest.to_translation())
        pb.matrix = Matrix.LocRotScale(h, rest_rot, Vector((FOOT_SCALE,) * 3))
        bpy.context.view_layer.update()
        continue
    if kchild and kchild in karm.data.bones:
        d = nhead(tail) - head_t
        vk = karm.data.bones[kchild].head_local - bone.head_local   # Karin joint-to-joint, rest
        rot = vk.rotation_difference(d) @ rest_rot
        yk = (rest.to_3x3() @ Vector((0, 1, 0))).normalized()
        along = abs(vk.normalized().dot(yk))
        sc = Vector((1, 1 + (d.length / vk.length - 1) * along, 1))
    else:
        par = pb.parent
        delta = par.matrix.to_quaternion() @ par.bone.matrix_local.to_quaternion().inverted()
        rot = delta @ rest_rot
    pb.matrix = Matrix.LocRotScale(head_t, rot, sc)
    bpy.context.view_layer.update()
if HEAD_SCALE != 1.0:
    hb = karm.pose.bones["Head"]
    hb.matrix = Matrix.LocRotScale(hb.matrix.to_translation(), hb.matrix.to_quaternion(), Vector((HEAD_SCALE,) * 3))
    for c in hb.children_recursive:
        c.bone.inherit_scale = 'FULL'
    bpy.context.view_layer.update()
# report residual joint error
err = []
for kname, (nname, _) in MAP.items():
    kh = karm.matrix_world @ karm.pose.bones[kname].head
    nh = naoe.matrix_world @ nb[nname].head_local
    err.append((round((kh - nh).length, 4), kname))
print("FIT errs (cm, rigid bones keep Karin position)", [(round(e * 100, 1), n) for e, n in sorted(err, reverse=True) if e > 0.005])

# --- 5. bake deformation + new rest ------------------------------------------------------
bpy.ops.object.mode_set(mode='OBJECT')
for o in kmeshes:
    ctx_for(o)
    for m in list(o.modifiers):
        if m.type == 'ARMATURE':
            bpy.ops.object.modifier_apply(modifier=m.name)
ctx_for(karm, 'POSE')
bpy.ops.pose.select_all(action='SELECT')
bpy.ops.pose.armature_apply(selected=False)
for pb in karm.pose.bones:
    for c in list(pb.constraints):
        pb.constraints.remove(c)
bpy.ops.object.mode_set(mode='OBJECT')

def target_of(kname):
    b = karm.data.bones[kname]
    while b is not None:
        if b.name in MAP:
            return MAP[b.name][0]
        b = b.parent
    return "Hips"

# --- 5a. leg girth (radial slimming toward the hip-knee / knee-ankle axes) ------------------------
def seg_closest(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared))
    return a + ab * t
def girth_delta(p, weights):  # weights: {naoe bone: w}, normalised; returns the world offset
    d = Vector()
    for S in ("Left", "Right"):
        hip_, knee_, ank_ = nhead(f"{S}UpLeg"), nhead(f"{S}Leg"), nhead(f"{S}Foot")
        for bone, (a, b), f in ((f"{S}UpLeg", (hip_, knee_), LEG_GIRTH[0]), (f"{S}Leg", (knee_, ank_), LEG_GIRTH[1])):
            w = weights.get(bone, 0.0)
            if w > 0:
                d += (seg_closest(p, a, b) - p) * (w * (1.0 - f))
    return d
if LEG_GIRTH:
    for o in kmeshes:
        gname = {g.index: g.name for g in o.vertex_groups}
        inv = o.matrix_world.inverted().to_3x3()
        for v in o.data.vertices:
            tot = sum(g.weight for g in v.groups) or 1.0
            ws = {}
            for g in v.groups:
                t = target_of(gname[g.group]); ws[t] = ws.get(t, 0.0) + g.weight / tot
            if any(k.endswith("UpLeg") or k.endswith("Leg") for k in ws):
                v.co += inv @ girth_delta(o.matrix_world @ v.co, ws)
    print("FIT leg girth", LEG_GIRTH)

# --- 5b. feet onto the ground (flat-foot mode) ----------------------------------------------
def height(v):  # Naoe frame: up = -Y
    return -v.y
UP = Vector((0, -1, 0))
lift = {}
if GROUND is not None:
    for S in ("Left", "Right"):
        knee_h, ankle_h = height(nhead(f"{S}Leg")), height(nhead(f"{S}Foot"))
        feet = {f"{S}Foot", f"{S}FootThumb1"}
        if FOOT_SQUASH is not None:  # vertical squash of the foot-weighted part below the ankle joint
            for o in kmeshes:
                gname = {g.index: g.name for g in o.vertex_groups}
                inv = o.matrix_world.inverted().to_3x3()
                for v in o.data.vertices:
                    tot = sum(g.weight for g in v.groups) or 1.0
                    f = sum(g.weight for g in v.groups if target_of(gname[g.group]) in feet) / tot
                    h = height(o.matrix_world @ v.co)
                    if f > 0 and h < ankle_h:
                        v.co += inv @ (UP * ((ankle_h - h) * (1.0 - FOOT_SQUASH) * f))
        lo = None
        for o in kmeshes:
            gname = {g.index: g.name for g in o.vertex_groups}
            for v in o.data.vertices:
                tot = sum(g.weight for g in v.groups) or 1.0
                if sum(g.weight for g in v.groups if target_of(gname[g.group]) in feet) / tot >= 0.5:
                    h = height(o.matrix_world @ v.co)
                    lo = h if lo is None else min(lo, h)
        d = max(0.0, GROUND - lo) if lo is not None else 0.0
        lift[S] = {"sole_before": lo, "lift": d, "knee_h": knee_h, "ankle_h": ankle_h}
        if d <= 0:
            continue
        for o in kmeshes:
            gname = {g.index: g.name for g in o.vertex_groups}
            inv = o.matrix_world.inverted().to_3x3()
            for v in o.data.vertices:
                tot = sum(g.weight for g in v.groups) or 1.0
                s = 0.0
                for g in v.groups:
                    t = target_of(gname[g.group])
                    if t in feet:
                        s += g.weight
                    elif t == f"{S}Leg":  # shin: ramp 0 at the knee -> 1 at the ankle
                        h = height(o.matrix_world @ v.co)
                        s += g.weight * min(1.0, max(0.0, (knee_h - h) / (knee_h - ankle_h)))
                if s > 0:
                    v.co += inv @ (UP * (d * s / tot))
    print("FIT feet", {k: {kk: round(vv, 4) for kk, vv in v.items()} for k, v in lift.items()})

# --- 5c. narrower shoulders (see --shoulder-narrow) ------------------------------------------
def smooth(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)
shoulder = {}
if SHOULDER_NARROW:
    X = Vector((1, 0, 0))                                   # Naoe frame: forward +X, rotate the arm about it
    for S, lat in (("Left", 1.0), ("Right", -1.0)):
        J, E, C = nhead(f"{S}Arm"), nhead(f"{S}ForeArm"), nhead(f"{S}Clavicle")
        a = E - J; a.x = 0
        h_ = math.radians(SHOULDER_HANG)
        hang = Vector((0, math.cos(h_), lat * math.sin(h_)))  # down = +Y
        phi = math.atan2(a.cross(hang).dot(X), a.dot(hang))
        Rm = Matrix.Rotation(phi, 3, X)
        sub = {f"{S}Arm"} | {b.name for b in nb[f"{S}Arm"].children_recursive}
        Ep = J + Rm @ (E - J)
        delta = Vector((0, 0, -lat * SHOULDER_NARROW))     # toward the body, horizontal, in the hanging pose
        moved, worst = 0, 0.0
        for o in kmeshes:
            gname = {g.index: g.name for g in o.vertex_groups}
            inv = o.matrix_world.inverted().to_3x3()
            for v in o.data.vertices:
                tot = sum(g.weight for g in v.groups) or 1.0
                w_sub = w_arm = w_clav = 0.0
                for g in v.groups:
                    t = target_of(gname[g.group])
                    if t in sub:
                        w_sub += g.weight / tot
                        if t == f"{S}Arm":
                            w_arm += g.weight / tot
                    elif t == f"{S}Clavicle":
                        w_clav += g.weight / tot
                if not (w_arm or w_clav):
                    continue
                p = o.matrix_world @ v.co
                pp = J + Rm @ (p - J)                          # the upper arm in the hanging pose
                f_arm = 1.0 - smooth((pp - J).dot(Ep - J) / (Ep - J).length_squared)
                f_clav = smooth((p - C).dot(J - C) / (J - C).length_squared)
                g_ = w_arm * f_arm + w_clav * f_clav
                if g_ <= 1e-4:
                    continue
                L = Matrix.Identity(3) * (1.0 - w_sub) + Rm * w_sub   # linear part of the blended deform
                d_rest = L.inverted() @ (delta * g_)
                v.co += inv @ d_rest
                moved += 1; worst = max(worst, d_rest.length)
        shoulder[S] = {"phi_deg": round(math.degrees(phi), 2), "verts": moved, "max_rest_offset": round(worst, 4)}
    print("FIT shoulders", SHOULDER_NARROW, shoulder)

# --- 6. weight remap ---------------------------------------------------------------------
remap = {b.name: target_of(b.name) for b in karm.data.bones}
phys_bones = {}  # karin bone -> (KP name, parent name in NaoeRig)
for root in PHYS_ROOTS:
    rb = karm.data.bones[root]
    phys_bones[root] = (kp_name(root), target_of(rb.parent.name))
    for c in rb.children_recursive:
        phys_bones[c.name] = (kp_name(c.name), kp_name(c.parent.name))
for kname, (kp, _) in phys_bones.items():
    remap[kname] = kp
if phys_bones:
    def lifted(n, p):  # the 5a/5b girth + foot lift at a KP bone point (leg ribbons/cloak follow the leg geometry)
        t = target_of(n)
        if LEG_GIRTH:
            p = p + girth_delta(p, {t: 1.0})
        for S, L in lift.items():
            if t in (f"{S}Foot", f"{S}FootThumb1"):
                return p + UP * L["lift"]
            if t == f"{S}Leg":
                return p + UP * (L["lift"] * min(1.0, max(0.0, (L["knee_h"] - height(p)) / (L["knee_h"] - L["ankle_h"]))))
        return p
    kpos = {n: (lifted(n, karm.matrix_world @ karm.data.bones[n].head_local), lifted(n, karm.matrix_world @ karm.data.bones[n].tail_local))
            for n in phys_bones}
    ctx_for(naoe, 'EDIT')
    ninv = naoe.matrix_world.inverted()
    for kname in sorted(phys_bones, key=lambda n: len(karm.data.bones[n].parent_recursive)):
        kp, par = phys_bones[kname]
        eb = naoe.data.edit_bones.new(kp)
        # Odyssey Physics bones run along local +X (vanilla hair/ponytail/skirt chains; Shadows used -Z): point the
        # bone's Y (head->tail) forward, perpendicular to the chain, and roll its Z to X x Y so that X = the chain.
        h = ninv @ kpos[kname][0]
        chain = (ninv.to_3x3() @ (kpos[kname][1] - kpos[kname][0])).normalized()
        fwd = ninv.to_3x3() @ Vector((1, 0, 0))            # Naoe frame: forward +X
        perp = (fwd - chain * fwd.dot(chain))
        if perp.length < 1e-4:
            perp = ninv.to_3x3() @ Vector((0, 0, 1))
        perp.normalize()
        eb.head = h; eb.tail = h + perp * 0.03
        eb.align_roll(chain.cross(perp))
        eb.parent = naoe.data.edit_bones[par]
        eb.use_connect = False
    bpy.ops.object.mode_set(mode='OBJECT')
    print("FIT phys bones", len(phys_bones), sorted(v[0] for v in phys_bones.values())[:6], "...")
def seg_frac(p, a, b):
    ha, hb = height(naoe.matrix_world @ nb[a].head_local), height(naoe.matrix_world @ nb[b].head_local)
    return min(1.0, max(0.0, (height(p) - ha) / (hb - ha)))
SPLITS = {"Spine": ("Spine", "Spine1", "Spine2"), "Neck": ("Neck", "Neck1", "Head")}
SPLITS = {k: v for k, v in SPLITS.items() if all(b in nb for b in v)}  # Unity: no Neck1

report = {"scale": SCALE, "head_scale": HEAD_SCALE, "foot_scale": FOOT_SCALE, "foot_squash": FOOT_SQUASH, "ground": GROUND, "feet": lift, "leg_girth": LEG_GIRTH,
          "shoulder_narrow": SHOULDER_NARROW, "shoulder_hang": SHOULDER_HANG, "shoulders": shoulder, "meshes": {},
          "phys": {v[0]: {"karin": k, "parent": v[1], "len": round((kpos[k][1] - kpos[k][0]).length, 4),
                          "dir": [round(c, 3) for c in (kpos[k][1] - kpos[k][0]).normalized()]}  # Naoe frame, up = -Y
                   for k, v in phys_bones.items()}}
for o in kmeshes:
    me = o.data
    groups = {g.index: g.name for g in o.vertex_groups}
    neww = []
    for v in me.vertices:
        acc = {}
        p = o.matrix_world @ v.co
        for g in v.groups:
            if g.weight <= 0:
                continue
            t = remap.get(groups[g.group], "Hips")
            if t in SPLITS:
                lo, mid, hi = SPLITS[t]
                f = seg_frac(p, lo, hi) * 2.0  # 0..1 across lower half -> mid, clamp
                f = min(1.0, f)
                acc[lo] = acc.get(lo, 0) + g.weight * (1 - f)
                acc[mid] = acc.get(mid, 0) + g.weight * f
            else:
                acc[t] = acc.get(t, 0) + g.weight
        items = sorted(acc.items(), key=lambda kv: -kv[1])[:MAX_INF]
        tot = sum(w for _, w in items) or 1.0
        neww.append([(n, w / tot) for n, w in items if w / tot > 1e-4])
    for g in list(o.vertex_groups):
        o.vertex_groups.remove(g)
    vg = {}
    for i, lst in enumerate(neww):
        for n, w in lst:
            if n not in vg:
                vg[n] = o.vertex_groups.new(name=n)
            vg[n].add([i], w, 'REPLACE')
    for m in list(o.modifiers):
        o.modifiers.remove(m)
    o.parent = naoe
    o.matrix_parent_inverse = naoe.matrix_world.inverted()
    am = o.modifiers.new("Armature", 'ARMATURE'); am.object = naoe
    report["meshes"][o.name] = {"verts": len(me.vertices), "groups": sorted(vg)}
bpy.data.objects.remove(karm)
used = sorted({g for m in report["meshes"].values() for g in m["groups"]})
report["used_bones"] = used
print("FIT used bones", len(used))
json.dump(report, open(out_blend.replace(".blend", "_fit.json"), "w"), indent=1)
bpy.ops.wm.save_as_mainfile(filepath=out_blend)
print("FIT_OK", out_blend)
