# Eyelid bones for Karin's blink (Blender 4.2 background, on a face_rig.py build.blend).
#
# usage: blender -b <run>/build.blend --python blink_rig.py -- <cooked mesh.uasset> <out_run_dir> [--render]
#
# Deacon blinks with face joints that drop ~0.5-1 cm (face_1544 / face_1911: neutral open +0.2, blink -0.6, eyes closed
# -1.0 along Head X); Karin's anime lid travels up to 3.9 cm and her face weights (sampled from Deacon's skin) leave the
# lid region on Head, so in game only the brow area moved. Karin's own VRM shape keys blink_L / blink_R describe the
# closed lid exactly; a shape key is a linear displacement field, and so is linear blend skinning with bones that only
# translate. Per eye this adds mesh-only bones under Head, one per Head-local half axis the lid moves along
# (KB_Blink_<L|R>_<Xn|Xp|Yn|Yp|Zn|Zp>, X = up, Y = her left, Z = forward), each translating by a fixed magnitude M_a at
# full closure, and gives every lid vertex the weights w_a = c_a / M_a (c_a = its displacement component along the half
# axis) plus the remainder (1 - sum w) on its old weights. At closure s in [0, 1] the vertex moves s * displacement, the
# same path as the VRM shape key. In game each lid bone sits under an amplifier bone whose cooked rest pose carries a
# rotation and a scale (pytools/blink_amp.py), and an AnimBP CopyBone copies Deacon's lid joint local translation onto the
# lid bone (pytools/abp_springs.py "copies"): the lid bone then moves R * S * (joint delta - open delta) in Head space,
# which is s * M_a along its half axis. (BoneDrivenController nodes had no effect in game, t28b-e.)
# Output: <out>/build.blend, <out>/deacon_head_standard.fbx, <out>/blink_rig.json (bones, magnitudes, fit errors),
# --render: <out>/blink_{open,key,rig}_front.png (rest, VRM shape key closed, skinned closed).
import bpy, sys, os, json, math
import numpy as np
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blink_sim, dgpaths   # blink_sim puts the kit's scripts/ (refskel, anim_pertrack, dgpaths) on sys.path

argv = sys.argv[sys.argv.index("--") + 1:]
COOKED, OUT = argv[0], os.path.abspath(argv[1]); os.makedirs(OUT, exist_ok=True)
RENDER = "--render" in argv
MAX_INF = 4          # UE 4.11 GPU skin influences
MIN_COMP = 0.1       # cm: a half axis whose largest component is below this gets no bone
S_MAX = 0.9          # largest summed blink weight of a vertex (the rest stays on its old weights)
SKEL_JSON = dgpaths.skel_json()   # <DG_CACHE>/deacon_master_Skeleton.deacon_master_Skeleton.skel.json

rig = blink_sim.Rig(COOKED, SKEL_JSON)
ob = bpy.data.objects["deacon_head_standard"]; me = ob.data; arm = ob.parent
kb = me.shape_keys.key_blocks
basis = np.array([v.co for v in kb[0].data])
co = np.array([v.co for v in me.vertices])
assert np.abs(basis - co).max() < 1e-5
gname = {g.index: g.name for g in ob.vertex_groups}
W = [{gname[g.group]: g.weight for g in v.groups if g.weight > 1e-6} for v in me.vertices]
AX = {"X": rig.axis_blender([1, 0, 0]), "Y": rig.axis_blender([0, 1, 0]), "Z": rig.axis_blender([0, 0, 1])}
report = {"bones": {}, "sides": {}}

new_w = {}
bones = []          # (name, side, local axis vector (Head space), magnitude, head position Blender)
for side, key in (("L", "blink_L"), ("R", "blink_R")):
    d = np.array([v.co for v in kb[key].data]) - basis
    idx = np.where(np.linalg.norm(d, axis=1) > 1e-4)[0]
    comp = {a: d[idx] @ AX[a] for a in "XYZ"}               # Head-local components (cm)
    half = {}
    for a in "XYZ":
        for sgn, tag in ((-1, "n"), (1, "p")):
            c = np.maximum(sgn * comp[a], 0.0)
            if c.max() >= MIN_COMP:
                half[a + tag] = (sgn, c)
    # magnitudes: start at each half axis' largest component, scale all so the summed weight stays <= S_MAX
    M = {h: c.max() for h, (sgn, c) in half.items()}
    S = sum(c / M[h] for h, (sgn, c) in half.items())
    k = max(S.max() / S_MAX, 1.0)
    M = {h: m * k for h, m in M.items()}
    centre = co[idx].mean(0)
    for h, (sgn, c) in half.items():
        name = "KB_Blink_%s_%s" % (side, h)
        local = np.zeros(3); local["XYZ".index(h[0])] = sgn
        bones.append((name, side, local, M[h], centre))
    # weights
    errs = []
    for j, v in enumerate(idx):
        bw = {"KB_Blink_%s_%s" % (side, h): c[j] / M[h] for h, (sgn, c) in half.items() if c[j] / M[h] > 1e-3}
        s = sum(bw.values())
        old = sorted(W[v].items(), key=lambda kv: -kv[1])[:max(MAX_INF - len(bw), 1)]
        if len(bw) >= MAX_INF:          # cannot happen with <= 3 axes, kept as a guard
            raise SystemExit("too many blink influences at vertex %d" % v)
        to = sum(x for _, x in old) or 1.0
        w = dict(bw)
        for n, x in old:
            w[n] = w.get(n, 0.0) + (1.0 - s) * x / to
        new_w[int(v)] = w
        pred = sum(c[j] / M[h] * M[h] * (sgn * AX[h[0]]) for h, (sgn, c) in half.items())
        errs.append(np.linalg.norm(pred - d[v]))
    report["sides"][side] = {"verts": int(len(idx)), "max_disp": round(float(np.linalg.norm(d[idx], axis=1).max()), 3),
                             "magnitudes": {h: round(m, 3) for h, m in M.items()}, "scale_k": round(float(k), 3),
                             "max_sum_w": round(float((sum(c / M[h] for h, (sgn, c) in half.items())).max()), 3),
                             "fit_err_max": round(float(max(errs)), 4)}

# bones: mesh-only; each lid bone KB_Blink_* hangs under its own amplifier KB_Amp_* (child of Head). Blender rest poses
# cannot carry scale: pytools/blink_amp.py sets the amplifier's rotation / scale and the lid bone's local translation in
# the cooked mesh, and an AnimBP CopyBone (parent bone space, translation) copies Deacon's lid joint local translation onto
# the lid bone, so the lid bone moves R * S * (joint delta) in Head space.
W_ = np.array(arm.matrix_world); Wi = np.linalg.inv(W_)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="EDIT")
eb_head = arm.data.edit_bones["Head"]
for name, side, local, mag, centre in bones:
    h = (Wi @ np.r_[centre, 1.0])[:3]
    amp = arm.data.edit_bones.new(name.replace("KB_Blink_", "KB_Amp_"))
    amp.head = Vector(h); amp.tail = Vector(h + (Wi[:3, :3] @ AX["X"]) * 1.0)
    amp.parent = eb_head; amp.use_connect = False
    eb = arm.data.edit_bones.new(name)
    eb.head = Vector(h); eb.tail = Vector(h + (Wi[:3, :3] @ AX["X"]) * 1.0)
    eb.parent = amp; eb.use_connect = False
    report["bones"][name] = {"side": side, "axis_head_local": local.tolist(), "magnitude": round(float(mag), 4),
                             "head_blender": np.round(centre, 3).tolist()}
bpy.ops.object.mode_set(mode="OBJECT")

groups = {g.name: g for g in ob.vertex_groups}
for name, *_ in bones:
    groups[name] = ob.vertex_groups.new(name=name)
for v, w in new_w.items():
    for g in list(me.vertices[v].groups):
        ob.vertex_groups[g.group].remove([v])
    for n, x in w.items():
        if n not in groups: groups[n] = ob.vertex_groups.new(name=n)
        groups[n].add([v], x, "REPLACE")

# check: skinned closure (bones at full magnitude) against the shape keys, from the written vertex groups
gname = {g.index: g.name for g in ob.vertex_groups}
offs = {name: mag * (local @ np.eye(3)) for name, side, local, mag, centre in bones}
def skinned(side):
    out = np.zeros_like(co)
    for v in new_w:
        for g in me.vertices[v].groups:
            n = gname[g.group]
            if n.startswith("KB_Blink_%s_" % side):
                loc = offs[n]
                out[v] += g.weight * (loc[0] * AX["X"] + loc[1] * AX["Y"] + loc[2] * AX["Z"])
    return out
for side, key in (("L", "blink_L"), ("R", "blink_R")):
    d = np.array([v.co for v in kb[key].data]) - basis
    e = np.linalg.norm(skinned(side) - d, axis=1)
    report["sides"][side]["skinned_err_max"] = round(float(e.max()), 4)
    report["sides"][side]["skinned_err_mean"] = round(float(e[np.linalg.norm(d, axis=1) > 1e-4].mean()), 4)
inf = [len([g for g in me.vertices[v].groups if g.weight > 1e-6]) for v in new_w]
report["max_influences"] = int(max(inf))
report["weights_sum_minmax"] = [round(min(sum(g.weight for g in me.vertices[v].groups) for v in new_w), 4),
                                round(max(sum(g.weight for g in me.vertices[v].groups) for v in new_w), 4)]

if RENDER:
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"; sc.display.shading.light = "STUDIO"; sc.display.shading.color_type = "TEXTURE"
    sc.render.resolution_x = 700; sc.render.resolution_y = 420
    cam = bpy.data.objects.get("cam")
    if cam is None:
        cd = bpy.data.cameras.new("cam"); cam = bpy.data.objects.new("cam", cd); sc.collection.objects.link(cam)
    cam.data.type = "ORTHO"; cam.data.ortho_scale = 26; sc.camera = cam
    for o in bpy.data.objects: o.hide_render = o is not ob
    eye_z = float(np.mean([b[4][2] for b in bones]))
    cam.location = (0, -80, eye_z); cam.rotation_euler = (math.radians(90), 0, 0)
    sk = ob.shape_key_add(name="blink_rig_test", from_mix=False)
    both = skinned("L") + skinned("R")
    for i in range(len(co)): sk.data[i].co = Vector(co[i] + both[i])
    for k_ in kb: k_.value = 0.0
    for tag, keys in (("open", ()), ("key", ("blink_L", "blink_R")), ("rig", ("blink_rig_test",))):
        for k_ in me.shape_keys.key_blocks: k_.value = 1.0 if k_.name in keys else 0.0
        sc.render.filepath = os.path.join(OUT, "blink_%s_front.png" % tag); bpy.ops.render.render(write_still=True)
    for k_ in me.shape_keys.key_blocks: k_.value = 0.0
    ob.shape_key_remove(sk)

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "build.blend"))
from fbx_common import export_for_ue411
export_for_ue411(arm, [ob], os.path.join(OUT, "deacon_head_standard.fbx"), "deacon_head_standard")
json.dump(report, open(os.path.join(OUT, "blink_rig.json"), "w"), indent=1)
print("BLINK_RIG_OK", json.dumps(report["sides"]), "max_inf", report["max_influences"], report["weights_sum_minmax"])
