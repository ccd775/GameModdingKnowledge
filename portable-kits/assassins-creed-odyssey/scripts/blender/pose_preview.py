"""Render Karin's face in a fit blend under Kassandra head-skeleton poses (2026-10-19), to see what the game shows.

blender -b <fit.blend> --python pose_preview.py -- <out_dir> <states.json> [--res 700] [--dist 0.9]
        [--head-xml <Kassandra head skeleton xml>]

states.json: {"name": {"poses": [[pose_id, weight], ...], "lid": deg}, ...}. Poses blend additively on the head
skeleton's rest locals (aco_pose_sim), "lid" turns both upper-lid bones (xA5D29CD8 / x08FBF534) about the head frame's
lateral +Z (+ = closing) on top. The game moves bone b by dW = G_pose G_rest^-1 (head frame); the rig shows the game
rest in its pose (face_rig keeps bind-offset bones posed back on c), so each pose bone gets A dW A^-1 * rest pose matrix,
A = head frame -> armature space (similarity fitted on the rest heads of the head bones without a bind offset).
Portable kit: aco_pose_sim.py is one folder up (scripts/); the head skeleton XML comes from --head-xml, else from
ACO_HEAD_SKELETON_XML or ACO_WORK (see aco_pose_sim.py). A one-off scheduled task does not inherit the session's
environment variables, so pass --head-xml there. Workbench needs an OpenGL context: run it in an interactive desktop
session.
"""
import bpy, sys, os, json, math, zlib
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import aco_pose_sim as sim

argv = sys.argv[sys.argv.index("--") + 1:]
out_dir, states = argv[0], json.load(open(argv[1]))
RES = int(argv[argv.index("--res") + 1]) if "--res" in argv else 700
DIST = float(argv[argv.index("--dist") + 1]) if "--dist" in argv else 0.9
HEAD_XML = argv[argv.index("--head-xml") + 1] if "--head-xml" in argv else None  # else ACO_HEAD_SKELETON_XML / ACO_WORK
LIDS = (0xA5D29CD8, 0x08FBF534)
os.makedirs(out_dir, exist_ok=True)

S = sim.Skel(HEAD_XML)
rig = bpy.data.objects["NaoeRig"]
bid = lambda n: int(n) if n.isdigit() else zlib.crc32(n.encode())
pb = {bid(p.name): p for p in rig.pose.bones if bid(p.name) in S.G0}
# bind-offset bones (face_rig: jaw, lids, eyes) have edit bones away from the game rest; children of an offset bone
# also display shifted in the saved pose, so the game rest of every bone is rebuilt as A G0 K (K = bone axis convention)
OFFSET = {0x581BFF12, 0xA5D29CD8, 0x08FBF534, 0xE8AAD140, 0x8CA848A3, 0x3FAC092B, 0x06CBB870, 0xB1A846F5, 0x86260864}
moved = {b for b in pb if b in OFFSET and np.abs(np.array(pb[b].matrix) - np.array(pb[b].bone.matrix_local)).max() > 1e-5}
src = np.array([S.G0[b][:3, 3] for b in pb if b not in OFFSET])
dst = np.array([np.array(pb[b].bone.head_local) for b in pb if b not in OFFSET])
ma, mb = src.mean(0), dst.mean(0)
U, Sv, Vt = np.linalg.svd((dst - mb).T @ (src - ma) / len(src))
D = np.eye(3); D[2, 2] = np.sign(np.linalg.det(U @ Vt))
R = U @ D @ Vt
s = (Sv * np.diag(D)).sum() / ((src - ma) ** 2).sum(1).mean()
A = np.eye(4); A[:3, :3] = s * R; A[:3, 3] = mb - s * R @ ma
res = np.abs((src @ (s * R).T + A[:3, 3]) - dst).max()
Ainv = np.linalg.inv(A)
Ks = [np.linalg.inv(A @ S.G0[b]) @ np.array(pb[b].bone.matrix_local) for b in pb if b not in OFFSET]
K = Ks[0]
k_err = max(np.abs(k - K).max() for k in Ks)
rest_pose = {b: A @ S.G0[b] @ K for b in pb}
print(f"PREVIEW head->armature scale {s:.4f}, fit residual {res*1000:.2f} mm, axis convention spread {k_err:.2e}, "
      f"{len(pb)} head bones, bind-offset bones {sorted(hex(b) for b in moved)}")
depth = {}
for b in S.order:
    p = S.parent[b]
    depth[b] = 0 if p is None else depth[p] + 1


def blend_locals(poses):
    loc = {}
    for pid, w in poses:
        for b, L in S.poses[int(pid)].items():
            cur = loc.get(b, S.L0[b])
            L0 = S.L0[b]
            dR = L0[:3, :3].T @ L[:3, :3]
            a = math.acos(max(-1.0, min(1.0, (np.trace(dR) - 1) / 2)))
            if a > 1e-9:
                ax = np.array([dR[2, 1] - dR[1, 2], dR[0, 2] - dR[2, 0], dR[1, 0] - dR[0, 1]]) / (2 * math.sin(a))
                dR = sim.rodrigues(ax, a * w)
            M = np.eye(4); M[:3, :3] = cur[:3, :3] @ dR; M[:3, 3] = cur[:3, 3] + w * (L[:3, 3] - L0[:3, 3])
            loc[b] = M
    return loc


def apply_state(st):
    G = S.globals(blend_locals(st.get("poses", [])))
    lid = math.radians(st.get("lid", 0.0))
    if lid:
        for b in LIDS:
            c = S.G0[b][:3, 3]
            Rz = sim.rodrigues(np.array([0, 0, 1.0]), lid)
            M = np.eye(4); M[:3, :3] = Rz; M[:3, 3] = c - Rz @ c
            G[b] = M @ G[b]
    for lvl in sorted(set(depth[b] for b in pb)):
        for b in pb:
            if depth[b] != lvl:
                continue
            dW = G[b] @ np.linalg.inv(S.G0[b])
            pb[b].matrix = Matrix((A @ dW @ Ainv @ rest_pose[b]).tolist())
        bpy.context.view_layer.update()


# scene: face close-up (world: forward +X, up -Y), hide the vanilla reference heads
sc = bpy.context.scene
for o in bpy.data.objects:
    if o.type == 'MESH' and o.name.startswith("NaoeHeadRef"):
        o.hide_render = True
eyes = [rig.matrix_world @ Vector(rest_pose[b][:3, 3].tolist()) for b in (0x3FAC092B, 0x06CBB870)]  # game rest
mid = (eyes[0] + eyes[1]) / 2
cam_data = bpy.data.cameras.new("PreviewCam"); cam_data.lens = 85
cam = bpy.data.objects.new("PreviewCam", cam_data); sc.collection.objects.link(cam)
cam.location = mid + Vector((DIST, 0.0, 0.0))
fwd = (mid - cam.location).normalized()
up = Vector((0.0, -1.0, 0.0))
right = fwd.cross(up).normalized(); up = right.cross(fwd).normalized()
cam.matrix_world = Matrix(((right.x, up.x, -fwd.x, cam.location.x), (right.y, up.y, -fwd.y, cam.location.y),
                           (right.z, up.z, -fwd.z, cam.location.z), (0, 0, 0, 1)))
sc.camera = cam
sun = bpy.data.objects.new("PreviewSun", bpy.data.lights.new("PreviewSun", 'SUN'))
sun.data.energy = 3.0; sc.collection.objects.link(sun)
sun.matrix_world = cam.matrix_world.copy()
if sc.world is None:
    sc.world = bpy.data.worlds.new("PreviewWorld")
sc.world.use_nodes = True
bg = sc.world.node_tree.nodes.get("Background")
if bg:
    bg.inputs[0].default_value = (0.8, 0.8, 0.85, 1.0); bg.inputs[1].default_value = 0.8
# flat texture colour only: bind-offset bakes store vertices up to ~1.4 m away, and Blender re-derives their custom
# normals from that stored shape, so lit renders shade the baked regions wrongly (the game keeps the exported normals)
sc.render.engine = 'BLENDER_WORKBENCH'
sc.display.shading.light = 'FLAT'
sc.display.shading.color_type = 'TEXTURE'
sc.render.resolution_x = sc.render.resolution_y = RES
sc.render.film_transparent = False
sc.view_settings.view_transform = 'Standard'
for name, st in states.items():
    apply_state(st)
    sc.render.filepath = os.path.join(out_dir, f"{name}.png")
    bpy.ops.render.render(write_still=True)
    print("PREVIEW", name, sc.render.filepath)
print("PREVIEW_OK")
