# What Deacon's lip-sync visemes do to Karin's mouth (Blender 4.2 background, on a build.blend).
#
# usage: blender -b <run>/build.blend --python viseme_sim.py -- <cooked mesh.uasset> <out_dir> [viseme ...]
#
# Days Gone lip sync blends Deacon's additive viseme poses (Animation/Deacon/vo/lipsync/dcn_visemes-*, 2 frames,
# AAT_LocalSpaceBase against misc/dcn_ref_pose frame 0) on the face_* joints. This applies one viseme to the build's
# face weights with blink_sim.Rig (LBS of the joint deltas) and renders a front close-up of the mouth next to Karin's
# own VRM mouth shape keys; prints how far the lips part.
import bpy, sys, os, json, math
import numpy as np
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blink_sim, anim_pertrack, dgpaths   # blink_sim puts the kit's scripts/ on sys.path

argv = sys.argv[sys.argv.index("--") + 1:]
COOKED, OUT = argv[0], os.path.abspath(argv[1]); os.makedirs(OUT, exist_ok=True)
VIS = argv[2:] or ["AA", "OY", "EY", "W"]
SKEL_JSON = dgpaths.skel_json()   # <DG_CACHE>/deacon_master_Skeleton.deacon_master_Skeleton.skel.json
ANIM = dgpaths.anim_dir()         # <DG_CACHE>/anim/raw/animj/BendGame/Content/Animation/Deacon

rig = blink_sim.Rig(COOKED, SKEL_JSON)
base = anim_pertrack.decode(os.path.join(ANIM, "misc", "dcn_ref_pose.uasset"))
ob = bpy.data.objects["deacon_head_standard"]; me = ob.data
kb = me.shape_keys.key_blocks
co = np.array([v.co for v in kb[0].data])
gname = {g.index: g.name for g in ob.vertex_groups}
W = [{gname[g.group]: g.weight for g in v.groups if g.weight > 1e-6} for v in me.vertices]
face = [i for i, w in enumerate(W) if any(n.startswith("face_") or n.startswith("tongue") or n in ("Jaw", "lowerPalette_jnt") for n in w)]
report = {}
mouthA = np.array([v.co for v in kb["kuchi_A"].data]) - co
mv = np.where(np.linalg.norm(mouthA, axis=1) > 1e-3)[0]
# lip line: mouth shape-key vertices on the front surface; upper = moves up / less, lower = moves down in kuchi_A
upper = mv[(mouthA[mv, 2] > -0.05) & (co[mv, 1] < co[mv, 1].min() + 0.6)]
lower = mv[(mouthA[mv, 2] < -0.5) & (co[mv, 1] < co[mv, 1].min() + 0.6)]
def gap(d):   # opening between the lips at the centre: mean dz of lower lip centre minus upper lip centre (cm, >0 = closes)
    c = lambda ix: ix[np.abs(co[ix, 0]) < 0.6]
    return float(d[c(upper), 2].mean() - d[c(lower), 2].mean())
report["kuchi_A_open"] = round(gap(mouthA), 3)
report["mouth_verts"] = int(len(mv)); report["upper"] = int(len(upper)); report["lower"] = int(len(lower))
sims = {}
for v in VIS:
    an = anim_pertrack.decode(os.path.join(ANIM, "vo", "lipsync", "dcn_visemes-%s.uasset" % v))
    deltas = rig.mood_deltas(an, base, frame=0)
    d = np.zeros_like(co)
    d[face] = rig.displacement(co[face], [W[i] for i in face], deltas)
    sims[v] = d
    report[v] = {"open": round(gap(d), 3), "mouth_max": round(float(np.linalg.norm(d[mv], axis=1).max()), 3),
                 "face_max": round(float(np.linalg.norm(d, axis=1).max()), 3)}
# weights of the lip line: which joints carry the upper / lower lip centre
def wsum(ix):
    acc = {}
    for i in ix:
        for n, x in W[i].items(): acc[n] = acc.get(n, 0) + x / len(ix)
    return {n: round(x, 3) for n, x in sorted(acc.items(), key=lambda kv: -kv[1])[:6]}
report["upper_weights"] = wsum(upper[np.abs(co[upper, 0]) < 0.6]); report["lower_weights"] = wsum(lower[np.abs(co[lower, 0]) < 0.6])

sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"; sc.display.shading.light = "STUDIO"; sc.display.shading.color_type = "TEXTURE"
sc.render.resolution_x = 400; sc.render.resolution_y = 400
cam = bpy.data.objects.get("cam")
if cam is None:
    cd = bpy.data.cameras.new("cam"); cam = bpy.data.objects.new("cam", cd); sc.collection.objects.link(cam)
cam.data.type = "ORTHO"; cam.data.ortho_scale = 9; sc.camera = cam
for o in bpy.data.objects: o.hide_render = o is not ob
mz = float(co[mv, 2].mean())
cam.location = (0, -80, mz); cam.rotation_euler = (math.radians(90), 0, 0)
for k in kb: k.value = 0.0
tmp = []
for v, d in sims.items():
    sk = ob.shape_key_add(name="sim_" + v, from_mix=False)
    for i in face: sk.data[i].co = Vector(co[i] + d[i])
    tmp.append(sk)
shots = [("rest", None)] + [("sim_" + v, "sim_" + v) for v in sims] + [("kuchi_A", "kuchi_A"), ("kuchi_O", "kuchi_O")]
for tag, key in shots:
    for k in me.shape_keys.key_blocks: k.value = 1.0 if k.name == key else 0.0
    sc.render.filepath = os.path.join(OUT, "mouth_%s.png" % tag); bpy.ops.render.render(write_still=True)
for k in me.shape_keys.key_blocks: k.value = 0.0
json.dump(report, open(os.path.join(OUT, "viseme_sim.json"), "w"), indent=1)
print("VISEME_SIM", json.dumps(report))
