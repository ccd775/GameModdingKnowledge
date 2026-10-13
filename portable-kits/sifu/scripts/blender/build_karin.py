# Karin_Original -> Sifu SK_W_MainChar_01 body build (Blender 4.2, background).
# blender -b --factory-startup --python build_karin.py -- <config.json>
#
# Contract (see PROJECT_STATE.md):
#  * bone orientations = W mesh ref pose (A-pose) exactly; Karin is re-posed into it with her own skinning,
#  * joint positions   = Karin's (uniform scale), Sifu helper bones placed with W-relative offsets,
#  * weights           = Karin humanoid weights remapped onto Sifu deform bones, limb weights spread over the
#                        twist bones like the original W mesh (main limb bones carry no weight).
import os, sys, json, math
import bpy
import numpy as np
from mathutils import Matrix, Vector
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(1, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))   # dyn_tuning.py (plain Python)
import sifu_common as sc
import profiles
import source_prep
import cloth_stage
import dyn_stage
import torso_weights
import face_stage

CFG = json.load(open(sys.argv[sys.argv.index("--") + 1], encoding="utf-8"))
P = profiles.activate(CFG.get("profile"))
SCALE = CFG.get("scale", 1.4) * 100.0  # Karin meters -> cm, then uniform scale
REPORT = {"config": CFG, "profile": P["name"]}

# ----------------------------------------------------------------------------------------------------------------
# Humanoid map: Sifu bone -> Karin bone (joint position source) for both sides.
SIDE = {"l": "Left", "r": "Right"}
LIMB = {}
for s, S in SIDE.items():
    LIMB.update({
        f"clavicle_{s}": f"{S}Shoulder", f"upperarm_{s}": f"{S}UpperArm", f"lowerarm_{s}": f"{S}LowerArm",
        f"hand_{s}": f"{S}Hand", f"thigh_{s}": f"{S}UpperLeg", f"calf_{s}": f"{S}LowerLeg", f"foot_{s}": f"{S}Foot",
        f"ball_{s}": f"{S}ToeBase", f"eye_{s}": f"{S}Eye",
        f"thumb_01_{s}": f"{S}ThumbProximal", f"thumb_02_{s}": f"{S}ThumbIntermediate", f"thumb_03_{s}": f"{S}ThumbDistal",
    })
    for f, F in (("index", "Index"), ("middle", "Middle"), ("ring", "Ring"), ("pinky", "Little")):
        LIMB.update({f"{f}_01_{s}": f"{S}{F}Proximal", f"{f}_02_{s}": f"{S}{F}Intermediate", f"{f}_03_{s}": f"{S}{F}Distal"})
LIMB.update({"neck_01": "Neck", "head": "Head"})

# Pose alignment chains: (karin bone, karin child joint, sifu bone, sifu child bone or None (use bone axis)).
ALIGN = []
for s, S in SIDE.items():
    ALIGN += [(f"{S}Shoulder", f"{S}UpperArm", f"clavicle_{s}", f"upperarm_{s}"),
              (f"{S}UpperArm", f"{S}LowerArm", f"upperarm_{s}", f"lowerarm_{s}"),
              (f"{S}LowerArm", f"{S}Hand", f"lowerarm_{s}", f"hand_{s}"),
              (f"{S}Hand", f"{S}MiddleProximal", f"hand_{s}", f"middle_01_{s}"),
              (f"{S}UpperLeg", f"{S}LowerLeg", f"thigh_{s}", f"calf_{s}"),
              (f"{S}LowerLeg", f"{S}Foot", f"calf_{s}", f"foot_{s}"),
              (f"{S}Foot", f"{S}ToeBase", f"foot_{s}", f"ball_{s}")]
    for f, F in (("index", "Index"), ("middle", "Middle"), ("ring", "Ring"), ("pinky", "Little"), ("thumb", "Thumb")):
        k = ["Proximal", "Intermediate", "Distal"]
        ALIGN += [(f"{S}{F}{k[0]}", f"{S}{F}{k[1]}", f"{f}_01_{s}", f"{f}_02_{s}"),
                  (f"{S}{F}{k[1]}", f"{S}{F}{k[2]}", f"{f}_02_{s}", f"{f}_03_{s}"),
                  (f"{S}{F}{k[2]}", None, f"{f}_03_{s}", None)]

# Karin secondary bones whose weights fold into a Sifu bone (cloth sim handles the motion later). Profiles with
# fold_ancestor fold any other non-humanoid bone like its nearest humanoid ancestor.
FOLD_PREFIX = P["fold_prefix"]

# Twist profiles (hat functions over segment parameter t), measured from the W mesh (analyze_weights.py).
TWIST = {"upperarm": [0.08, 0.4, 0.75, 1.0], "lowerarm": [0.2, 0.5, 0.78, 1.0],
         "thigh": [0.2, 0.55, 0.85, 1.05], "calf": [0.2, 0.5, 0.75, 1.0]}

# ----------------------------------------------------------------------------------------------------------------
bpy.ops.wm.read_factory_settings(use_empty=True)
sc.setup_cm_scene()

w_bones = sc.load_skel(CFG["w_skel"])
w_world = {n: sc.ue_to_bl(m) for n, m in sc.ue_world(w_bones).items()}
w_names = [b["name"] for b in w_bones]
w_parent = {b["name"]: (w_names[b["parent"]] if b["parent"] >= 0 else None) for b in w_bones}
w_local = {b["name"]: sc.ue_local(b) for b in w_bones}


def w_dir(bone, child):
    """Unit direction of a Sifu bone in Blender world (towards child joint or along the bone's local X)."""
    if child:
        return (w_world[child].translation - w_world[bone].translation).normalized()
    ax = w_world[bone].to_3x3().col[0].normalized()
    return ax if bone.endswith("_l") else -ax


# --- import Karin -----------------------------------------------------------------------------------------------
if P["name"] == "karin_original" and CFG.get("karin_vrm"):
    P["src"] = CFG["karin_vrm"]
karm, meshes = source_prep.load(P, REPORT)
KP = {b.name: (b.parent.name if b.parent else None) for b in karm.data.bones}
face_stage.record_shape_keys([o for o in meshes if o.name == "Body"][0])
for o in meshes:
    if o.data.shape_keys:
        o.shape_key_clear()
# drop the Karin_Alpha overlay faces (hidden inside the head in the neutral state)
for o in meshes:
    names = [m.name if m else "" for m in o.data.materials]
    if P["alpha_mat"] in names:
        idx = names.index(P["alpha_mat"])
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="DESELECT")
        bpy.ops.object.mode_set(mode="OBJECT")
        for p in o.data.polygons:
            p.select = p.material_index == idx
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.delete(type="FACE")
        bpy.ops.object.mode_set(mode="OBJECT")

# uniform scale to cm * scale, applied into data (the glTF importer may already convert to scene units)
head_z = (karm.matrix_world @ karm.data.bones["Head"].head_local).z
factor = (CFG.get("karin_head_m", P["head_m"]) * SCALE) / head_z   # head height = Karin_Original's, any source
REPORT["import_head_z"] = head_z
REPORT["scale_factor"] = factor
bpy.ops.object.select_all(action="DESELECT")
karm.scale = (factor, factor, factor)
for o in [karm] + meshes:
    o.select_set(True)
bpy.context.view_layer.objects.active = karm
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

# --- re-pose Karin into the W ref pose ------------------------------------------------------------------------------
bpy.context.view_layer.objects.active = karm
bpy.ops.object.mode_set(mode="POSE")
pbs = karm.pose.bones


def joint(name):
    return karm.matrix_world @ pbs[name].head


def rotate_about(pb, R):
    h = pb.head.copy()
    M = Matrix.Translation(h) @ R.to_4x4() @ Matrix.Translation(-h) @ pb.matrix
    pb.matrix = M
    bpy.context.view_layer.update()


# Pieces hanging off a re-posed limb (a sleeve under the T-pose forearm) would swing with it into the body; their hang
# bones are turned back to their source world direction after the limb alignment.
HANG = {}
for hb in P.get("hang", ()):
    path = [hb]
    while karm.data.bones[path[-1]].children:
        kids = karm.data.bones[path[-1]].children
        path.append(max(kids, key=lambda b: len(b.children_recursive)).name)
    HANG[hb] = (path[-1], (joint(path[-1]) - joint(hb)).normalized())

align_log = []
for kb, kchild, sb, schild in ALIGN:
    if kb not in pbs:
        continue
    pb = pbs[kb]
    if kchild and kchild in pbs:
        cur = (joint(kchild) - joint(kb))
    else:  # leaf: use the bone's own direction
        cur = (karm.matrix_world.to_3x3() @ (pb.tail - pb.head))
    if cur.length < 1e-6:
        continue
    cur.normalize()
    tgt = w_dir(sb, schild)
    R = cur.rotation_difference(tgt).to_matrix()
    ang = math.degrees(cur.angle(tgt))
    rotate_about(pb, R)
    align_log.append([kb, round(ang, 2)])

# hand roll: align palm lateral axis (index -> pinky proximal) with W after the swing, twist forearm half / hand half
for s, S in SIDE.items():
    hand = pbs[f"{S}Hand"]
    axis = w_dir(f"hand_{s}", f"middle_01_{s}")
    cur = joint(f"{S}LittleProximal") - joint(f"{S}IndexProximal")
    tgt = w_world[f"pinky_01_{s}"].translation - w_world[f"index_01_{s}"].translation
    cur = (cur - axis * cur.dot(axis)).normalized()
    tgt = (tgt - axis * tgt.dot(axis)).normalized()
    ang = cur.angle(tgt)
    if cur.cross(tgt).dot(axis) < 0:
        ang = -ang
    fore_axis = w_dir(f"lowerarm_{s}", f"hand_{s}")
    rotate_about(pbs[f"{S}LowerArm"], Matrix.Rotation(ang * 0.5, 3, fore_axis))
    rotate_about(hand, Matrix.Rotation(ang * 0.5, 3, axis))
    align_log.append([f"{S}Hand.roll", round(math.degrees(ang), 2)])
for hb, (tip, d0) in HANG.items():
    cur = (joint(tip) - joint(hb)).normalized()
    align_log.append([hb + ".hang", round(math.degrees(cur.angle(d0)), 2)])
    rotate_about(pbs[hb], cur.rotation_difference(d0).to_matrix())
REPORT["align_deg"] = align_log

# bake pose into meshes and make it the rest pose
bpy.ops.object.mode_set(mode="OBJECT")
for o in meshes:
    bpy.context.view_layer.objects.active = o
    for m in list(o.modifiers):
        if m.type == "ARMATURE":
            bpy.ops.object.modifier_apply(modifier=m.name)
bpy.context.view_layer.objects.active = karm
bpy.ops.object.mode_set(mode="POSE")
bpy.ops.pose.armature_apply(selected=False)
bpy.ops.object.mode_set(mode="OBJECT")
KJ = {b.name: karm.matrix_world @ b.head_local for b in karm.data.bones}
KT = {b.name: karm.matrix_world @ b.tail_local for b in karm.data.bones}

# --- Sifu joint placement ------------------------------------------------------------------------------------------
pos = {}
for sb, kb in LIMB.items():
    if kb in KJ:
        pos[sb] = KJ[kb].copy()
# pelvis: above the hip joints like W, scaled by hip width
w_mid = (w_world["thigh_l"].translation + w_world["thigh_r"].translation) / 2
k_mid = (pos["thigh_l"] + pos["thigh_r"]) / 2
hip_ratio = (pos["thigh_l"] - pos["thigh_r"]).length / (w_world["thigh_l"].translation - w_world["thigh_r"].translation).length
pos["pelvis"] = k_mid + (w_world["pelvis"].translation - w_mid) * hip_ratio
# spine: W fractions along pelvis -> neck_01, W lateral/forward offsets scaled by torso length ratio
wp, wn = w_world["pelvis"].translation, w_world["neck_01"].translation
kp, kn = pos["pelvis"], pos["neck_01"]
torso_ratio = (kn - kp).length / (wn - wp).length
for b in ("spine_01", "spine_02", "spine_03"):
    wb = w_world[b].translation
    t = (wb - wp).dot(wn - wp) / (wn - wp).length_squared
    off = (wb - wp) - (wn - wp) * t
    pos[b] = kp + (kn - kp) * t + off * torso_ratio
# clavicles pivot near the sternum like W (Karin's shoulder joint sits almost on the upper arm)
for s in ("l", "r"):
    pos[f"clavicle_{s}"] = pos["spine_03"] + (w_world[f"clavicle_{s}"].translation - w_world["spine_03"].translation) * torso_ratio
# neck_02 between neck_01 and head
wh = w_world["head"].translation
t = (w_world["neck_02"].translation - wn).dot(wh - wn) / (wh - wn).length_squared
pos["neck_02"] = pos["neck_01"] + (pos["head"] - pos["neck_01"]) * t
# twist bones along the limb segments at W fractions
for s in ("l", "r"):
    for seg, a, b in (("upperarm", f"upperarm_{s}", f"lowerarm_{s}"), ("lowerarm", f"lowerarm_{s}", f"hand_{s}"),
                      ("thigh", f"thigh_{s}", f"calf_{s}"), ("calf", f"calf_{s}", f"foot_{s}")):
        for i in range(1, 5):
            n = f"{seg}_twist_0{i}_{s}"
            wa, wb = w_world[a].translation, w_world[b].translation
            t = (w_world[n].translation - wa).dot(wb - wa) / (wb - wa).length_squared
            pos[n] = pos[a] + (pos[b] - pos[a]) * t

# head scale for face bones: Karin face width vs W head width at eye level
face = [o for o in meshes if o.name == "Body"][0]
fco = np.array([face.matrix_world @ v.co for v in face.data.vertices])
k_head_w = fco[:, 0].max() - fco[:, 0].min()
REPORT["karin_face_width_cm"] = float(k_head_w)
head_ratio = k_head_w / CFG.get("w_face_width_cm", 15.5)
REPORT["head_ratio"] = head_ratio


def seg_ratio(parent):
    """Scale applied to W-local offsets of helper bones under `parent`."""
    if parent in ("head",) or (w_parent.get(parent) == "head"):
        return head_ratio
    if parent in ("jaw", "tongue_01", "tongue_02", "neck_02"):
        return head_ratio
    if parent.startswith(("upperarm", "lowerarm", "hand", "thigh", "calf", "foot", "clavicle", "index", "middle", "ring", "pinky", "thumb")):
        return torso_ratio
    return torso_ratio


ABS = {"root"}  # 'Animation' retarget bones & root-level helpers keep W positions
for n in w_names:
    if w_parent[n] == "root" and n not in ("pelvis",):
        ABS.add(n)
order = w_names  # parents precede children
for n in order:
    if n in pos:
        continue
    p = w_parent[n]
    if n in ABS or p is None or (p in ABS and p != "root" and n not in pos):
        pos[n] = w_world[n].translation.copy()
        continue
    # W-relative offset in the parent's frame, scaled
    off_w = w_world[n].translation - w_world[p].translation
    pos[n] = pos[p] + off_w * seg_ratio(p)

# facial rig: warp W facial bones onto Karin's face, transfer + fit facial weights
face_weights = {}
if CFG.get("face_rig", True):
    face_weights = face_stage.run([o for o in meshes if o.name == "Body"][0], karm, pos, None, w_bones, w_world,
                                  CFG["w_glb"], CFG["pose_asset"], (pos["eye_l"], pos["eye_r"]), factor, REPORT)
# eyes: Karin eye joints are the rotation pivots; keep them
REPORT["joints_cm"] = {n: [round(x, 3) for x in pos[n]] for n in ("pelvis", "spine_03", "neck_01", "head", "upperarm_l", "hand_l", "thigh_l", "foot_l", "eye_l", "jaw")}

# --- build the Sifu armature --------------------------------------------------------------------------------------
world = {}
for n in w_names:
    m = w_world[n].copy()
    m.translation = pos[n]
    world[n] = m
sarm = sc.build_armature("Armature", w_bones, world)

# --- weights --------------------------------------------------------------------------------------------------------
def hat(t, centers):
    """Piecewise-linear partition of unity over the twist bones."""
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


def smooth01(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def map_group(kname, co):
    """Karin group name + vertex position -> list of (sifu bone, factor)."""
    for S, s in (("Left", "l"), ("Right", "r")):
        for seg, kb, a, b in (("upperarm", f"{S}UpperArm", f"upperarm_{s}", f"lowerarm_{s}"),
                              ("lowerarm", f"{S}LowerArm", f"lowerarm_{s}", f"hand_{s}"),
                              ("thigh", f"{S}UpperLeg", f"thigh_{s}", f"calf_{s}"),
                              ("calf", f"{S}LowerLeg", f"calf_{s}", f"foot_{s}")):
            if kname == kb:
                A, B = pos[a], pos[b]
                t = (co - A).dot(B - A) / (B - A).length_squared
                ws = hat(t, TWIST[seg])
                return [(f"{seg}_twist_0{i + 1}_{s}", w) for i, w in enumerate(ws)]
    if kname == "Chest":
        a = smooth01(((co - pos["spine_02"]).dot(pos["spine_03"] - pos["spine_02"])) / (pos["spine_03"] - pos["spine_02"]).length_squared)
        return [("spine_02", 1 - a), ("spine_03", a)]
    if kname == "Neck":
        a = smooth01(((co - pos["neck_01"]).dot(pos["neck_02"] - pos["neck_01"])) / (pos["neck_02"] - pos["neck_01"]).length_squared)
        return [("neck_01", 1 - a), ("neck_02", a)]
    if kname == "Hips":
        return [("pelvis", 1.0)]
    if kname == "Spine":
        return [("spine_01", 1.0)]
    for sb, kb in LIMB.items():
        if kb == kname:
            return [(sb, 1.0)]
    for pre, sb in FOLD_PREFIX:
        if kname.startswith(pre):
            return [(sb, 1.0)]
    if P["fold_ancestor"] and KP.get(kname):
        return map_group(KP[kname], co)
    if P["fold_ancestor"] and kname in KP:      # a root above Hips (e.g. "Root")
        return [("pelvis", 1.0)]
    return None


# dominant Karin group per vertex (drives the cloth piece split)
dom_groups = {}
for o in meshes:
    gname = {g.index: g.name for g in o.vertex_groups}
    dom = []
    for v in o.data.vertices:
        gs = sorted(((g.weight, gname[g.group]) for g in v.groups), reverse=True)
        dom.append(gs[0][1] if gs else None)
    dom_groups[o.name] = dom

unmapped = {}
MAXINF = 8
for o in meshes:
    gname = {g.index: g.name for g in o.vertex_groups}
    neww = []
    for v in o.data.vertices:
        co = o.matrix_world @ v.co
        acc = {}
        for g in v.groups:
            if g.weight <= 1e-5:
                continue
            kn = gname[g.group]
            m = map_group(kn, co)
            if m is None:
                unmapped[kn] = unmapped.get(kn, 0) + 1
                m = [("head", 1.0)]
            for sb, f in m:
                if f > 0:
                    acc[sb] = acc.get(sb, 0.0) + g.weight * f
        items = sorted(acc.items(), key=lambda kv: -kv[1])[:MAXINF]
        tot = sum(w for _, w in items) or 1.0
        neww.append([(b, w / tot) for b, w in items if w / tot > 1e-3])
    for g in list(o.vertex_groups):
        o.vertex_groups.remove(g)
    groups = {}
    for vi, items in enumerate(neww):
        for b, w in items:
            if b not in groups:
                groups[b] = o.vertex_groups.new(name=b)
            groups[b].add([vi], w, "REPLACE")
    o.parent = sarm
    o.matrix_parent_inverse = Matrix.Identity(4)
    for m in list(o.modifiers):
        o.modifiers.remove(m)
    mod = o.modifiers.new("Armature", "ARMATURE")
    mod.object = sarm
REPORT["unmapped_groups"] = unmapped
if face_weights:
    fo = [o for o in meshes if o.name == "Body"][0]
    groups = {g.name: g for g in fo.vertex_groups}
    for vi, ws in face_weights.items():
        for g in fo.vertex_groups:
            g.remove([vi])
        tot = sum(ws.values()) or 1.0
        for bname, w in sorted(ws.items(), key=lambda kv: -kv[1])[:8]:
            if w / tot < 1e-3:
                continue
            if bname not in groups:
                groups[bname] = fo.vertex_groups.new(name=bname)
            groups[bname].add([vi], w / tot, "REPLACE")
    REPORT["face_weighted_verts"] = len(face_weights)

# remove Karin's armature; UE strips a root null only when it is literally named "Armature"
kdata = karm.data
bpy.data.objects.remove(karm, do_unlink=True)
bpy.data.armatures.remove(kdata)
sarm.name = "Armature"
sarm.data.name = "Armature"
REPORT["armature_name"] = sarm.name

# --- material slot renames (UE slot names) -------------------------------------------------------------------------
REPORT["materials"] = sorted({m.name for o in meshes for m in o.data.materials if m})
if len(REPORT["materials"]) > 11:   # W outfits 2/3 override slots 11-16 and 18: visible slots must stay at 0-10
    raise RuntimeError(f"too many material slots: {REPORT['materials']}")
REPORT["mesh_stats"] = {o.name: {"verts": len(o.data.vertices), "polys": len(o.data.polygons)} for o in meshes}
co_all = np.array([o.matrix_world @ v.co for o in meshes for v in o.data.vertices])
REPORT["bbox_cm"] = [co_all.min(0).round(2).tolist(), co_all.max(0).round(2).tolist()]

# --- cloth proxies, collision capsules, vertex colors ----------------------------------------------------------------
REPORT["_w_pos"] = {n: w_world[n].translation.copy() for n in w_names}
proxies, cloth_specs, physics, colliders = cloth_stage.run(meshes, sarm, pos, world, KJ, KT, dom_groups, CFG["w_glb"], REPORT)
del REPORT["_w_pos"]
dyn_physics, rigidbody = dyn_stage.run(meshes, sarm, pos, world, KJ, KT, dom_groups, colliders, REPORT, KP=KP,
                                       skel_parent=sc.skel_parents(CFG.get("base_skel")))
fwd = (pos["ball_l"] - pos["foot_l"]).xy.normalized()
if P.get("torso_targets"):
    tw_objs = [o for o in meshes + proxies if o.name in P["torso_targets"]]
else:
    tw_objs = [o for o in meshes + proxies if o.name not in P.get("torso_exclude", ())]
REPORT["torso_weights"] = torso_weights.run(CFG["w_glb"], tw_objs, {n: pos[n] for n in torso_weights.JOINTS}, (fwd.x, fwd.y))
for o in meshes:
    me = o.data
    for a in list(me.color_attributes):
        if a.name != "Col":
            me.color_attributes.remove(a)
for o in meshes + proxies:
    me = o.data
    me.color_attributes.active_color = me.color_attributes["Col"]
    me.color_attributes.render_color_index = me.color_attributes.find("Col")
json.dump({"cloth": cloth_specs, "physics": physics, "dynamics": dyn_physics, "rigidbody": rigidbody},
          open(CFG["out_cloth"], "w", encoding="utf-8"), indent=1)

bpy.ops.wm.save_as_mainfile(filepath=CFG["out_blend"])
sc.export_fbx(CFG["out_fbx"], [sarm] + meshes + proxies)
json.dump(REPORT, open(CFG["out_report"], "w", encoding="utf-8"), indent=1, default=str)
print("BUILD_DONE")
