# Render Karin's face under Sifu facial poses (additive PoseAsset deltas applied exactly like UE does).
# blender -b karin_sifu.blend --python preview_face.py -- <pose_asset.json> <out_prefix> <pose names...>
import sys, json, math
import bpy
import numpy as np
from mathutils import Euler, Quaternion, Vector
import os
sys.path.insert(0, os.path.dirname(__file__))
import sifu_common as sc

args = sys.argv[sys.argv.index("--") + 1:]
pa_json, out = args[0], args[1]
poses = args[2:]
C = np.array(sc.C3)
arm = [o for o in bpy.data.objects if o.type == "ARMATURE"][0]
face = bpy.data.objects["Body"]
pc = json.load(open(pa_json))[0]["Properties"]["PoseContainer"]
tracks = pc["Tracks"]
pnames = [p["DisplayName"] for p in pc["PoseNames"]]
bone_ue = {b.name: (C @ np.array((arm.matrix_world @ b.matrix_local).translation)) for b in arm.data.bones}
rot_ue = {b.name: C @ np.array((arm.matrix_world @ b.matrix_local).to_3x3()) @ C for b in arm.data.bones}


def pose(nm):
    p = pc["Poses"][pnames.index(nm)]
    out = {}
    for kv in p["TrackToBufferIndex"]:
        t = p["LocalSpacePose"][kv["Value"]]
        tr, q = t["Translation"], t["Rotation"]
        out[tracks[int(kv["Key"])]] = (np.array([tr["X"], tr["Y"], tr["Z"]]),
                                       np.array(Quaternion((q["W"], q["X"], q["Y"], q["Z"])).to_matrix()))
    return out


def parent_name(b):
    pb = arm.data.bones[b].parent
    return pb.name if pb else None


def cs_delta(b, P, cache):
    """Component-space skinning matrix (4x4, UE) of bone b for additive pose P (head and above static)."""
    if b in cache:
        return cache[b]
    par = parent_name(b)
    if par is None or b == "head" or b not in bone_ue:
        cache[b] = np.eye(4)
        return cache[b]
    Mpar = cs_delta(par, P, cache)
    if b in P:
        dt, dR = P[b]
        Rp = rot_ue[par]
        Rc = Rp @ dR @ Rp.T
        p = bone_ue[b]
        local = np.eye(4)
        local[:3, :3] = Rc
        local[:3, 3] = p + Rp @ dt - Rc @ p
    else:
        local = np.eye(4)
    cache[b] = Mpar @ local
    return cache[b]


me = face.data
gname = {g.index: g.name for g in face.vertex_groups}
co_bl = np.array([v.co for v in me.vertices])
co_ue = co_bl @ C.T
if not me.shape_keys:
    face.shape_key_add(name="Basis")
sc_ = bpy.context.scene
sc_.render.engine = "BLENDER_WORKBENCH"
sc_.display.shading.light = "STUDIO"
sc_.display.shading.color_type = "TEXTURE"
sc_.render.resolution_x, sc_.render.resolution_y = 600, 600
cam_data = bpy.data.cameras.new("cam"); cam_data.type = "ORTHO"; cam_data.ortho_scale = 26; cam_data.clip_end = 10000
cam = bpy.data.objects.new("cam", cam_data); sc_.collection.objects.link(cam); sc_.camera = cam
hz = float(np.median(co_bl[:, 2]))
cam.location = (0, -200, 156); cam.rotation_euler = Euler((math.radians(90), 0, 0))
for o in bpy.data.objects:
    if o.type == "MESH" and o.name not in ("Body", "hair", "kemomimi"):
        o.hide_render = True
for nm in ["Rest"] + poses:
    if nm == "Rest":
        new = co_bl
    else:
        P = pose(nm)
        cache = {}
        new_ue = np.zeros_like(co_ue)
        for i, v in enumerate(me.vertices):
            acc = np.zeros(3)
            tot = 0.0
            for g in v.groups:
                b = gname[g.group]
                M = cs_delta(b, P, cache)
                acc += g.weight * (M[:3, :3] @ co_ue[i] + M[:3, 3])
                tot += g.weight
            new_ue[i] = acc / tot if tot > 0 else co_ue[i]
        new = new_ue @ C.T
    kb = face.shape_key_add(name="P_" + nm, from_mix=False)
    for i, k in enumerate(kb.data):
        k.co = Vector(new[i])
    for k in me.shape_keys.key_blocks[1:]:
        k.value = 1.0 if k == kb else 0.0
    sc_.render.filepath = f"{out}_{nm.replace(' ', '_')}.png"
    bpy.ops.render.render(write_still=True)
print("FACE_PREVIEW_DONE")
