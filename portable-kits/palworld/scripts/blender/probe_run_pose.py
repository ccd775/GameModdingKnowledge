# Diagnostic: pose a run's build.blend with a game animation (rotation-only retarget, as the game's "Skeleton"
# translation mode does) and render the hip/skirt area. Skirt bones stay rigid with the pelvis (no physics), so the
# renders show the worst case that the cloth physics has to fix.
#   blender --background <run>/build.blend --python probe_run_pose.py -- <run_dir> <anim.ueanim> <tag> [frames]
# frames: comma list; default = frames of maximum left/right hip flexion.
import bpy, sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
from palcommon import *
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1:]
RUN, ANIM, TAG = os.path.abspath(argv[0]), argv[1], argv[2]
FRAMES = [int(x) for x in argv[3].split(",")] if len(argv) > 3 else None
OUT = os.path.join(RUN, "probe"); os.makedirs(OUT, exist_ok=True)
enable_ueformat()
from io_scene_ueformat.importer.import_context import UEFormatImport
from io_scene_ueformat.options import UEAnimOptions

K = bpy.data.objects["Armature"]
objs = import_uemodel(os.path.join(CACHE_UE, r"Outfit\SK_Player_Female_Outfit_OldCloth001\SK_Player_Female_Outfit_OldCloth001.uemodel"))
V = next(o for o in objs if o.type == "ARMATURE")
for o in objs:
    if o.type == "MESH":
        o.hide_render = True
action, dto = UEFormatImport(UEAnimOptions(rotation_only=True, override_skeleton=V, scale_factor=1.0)).import_file_with_dto(ANIM)
TRACKS = {t.name.lower() for t in dto.tracks}
NF = dto.metadata.num_frames
print("ANIM", os.path.basename(ANIM), "frames", NF, "fps", dto.metadata.frames_per_second, "tracks", len(TRACKS))

def rot(m):
    return m.to_quaternion().to_matrix().to_4x4()
KR = {b.name: K.matrix_world @ b.matrix_local for b in K.data.bones}
VR = {b.name: V.matrix_world @ b.matrix_local for b in V.data.bones}
# per-bone frame offset C (K frame = V frame @ C) for bones both armatures share
C = {n: rot(VR[n]).inverted() @ rot(KR[n]) for n in KR if n in VR}
print("frame offset deg max", round(max(math.degrees(c.to_quaternion().angle) for c in C.values()), 2))

def thigh_flex(side):
    pb = V.pose.bones["thigh_" + side]
    d = (V.matrix_world @ pb.matrix).to_3x3() @ Vector((1, 0, 0))   # ueformat bones: X along the bone? measure both
    return d

def pose_frame(f):
    bpy.context.scene.frame_set(f)
    VP = {b.name: V.matrix_world @ b.matrix for b in V.pose.bones}
    Q = {}
    for b in K.data.bones:   # parents come first in bone order
        n = b.name; p = b.parent.name if b.parent else None
        if n in C and n.lower() in TRACKS:
            vp = VP[b.parent.name] if p else Matrix()
            Lr = rot(VP[n]) if not p else rot(vp).inverted() @ rot(VP[n])     # anim local rotation (V frames)
            if p:
                Mp = KR[p] @ (C[p].inverted() if p in C else Matrix())
                Mb = KR[n] @ C[n].inverted()
                t = (Mp.inverted() @ Mb).translation
                P = Q[p] @ (C[p].inverted() if p in C else Matrix()) @ Matrix.Translation(t) @ Lr
            else:
                P = Matrix.Translation(KR[n].translation) @ Lr
            Q[n] = P @ C[n]
        else:
            Q[n] = (Q[p] @ (KR[p].inverted() @ KR[n])) if p else KR[n]
    for b in K.data.bones:
        n = b.name; p = b.parent.name if b.parent else None
        rest_rel = (KR[p].inverted() @ KR[n]) if p else KR[n]
        cur_rel = (Q[p].inverted() @ Q[n]) if p else Q[n]
        pbn = K.pose.bones[n]; pbn.rotation_mode = "QUATERNION"
        pbn.matrix_basis = rest_rel.inverted() @ cur_rel
    bpy.context.view_layer.update()

def flexion(side):
    # angle between thigh and the pelvis-down axis, in K's posed state
    th = K.pose.bones["thigh_" + side]; ca = K.pose.bones["calf_" + side]
    d = (ca.head - th.head).normalized()
    return math.degrees(d.angle(Vector((0, 0, -1))))

if FRAMES is None:
    best = {"l": (0, -1), "r": (0, -1)}
    for f in range(0, NF):
        pose_frame(f)
        for s in "lr":
            th = K.pose.bones["thigh_" + s]; ca = K.pose.bones["calf_" + s]
            fwd = (ca.head - th.head).normalized().dot(Vector((0, -1, 0)))   # Blender -Y = character front
            if fwd > best[s][0]:
                best[s] = (fwd, f)
    FRAMES = sorted({best["l"][1], best["r"][1]})
    print("max flexion frames", best)

sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"; sc.display.shading.light = "STUDIO"; sc.display.shading.color_type = "TEXTURE"
sc.render.resolution_x, sc.render.resolution_y = 700, 700
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = "ORTHO"; cam.data.ortho_scale = 55
pel = lambda: K.matrix_world @ K.pose.bones["pelvis"].head
VIEWS = {"front": ((0, -150, -8), (90, 0, 0)), "side_l": ((150, 0, -8), (90, 0, 90)), "q_l": ((106, -106, -8), (90, 0, 45)),
         "q_r": ((-106, -106, -8), (90, 0, -45)), "side_r": ((-150, 0, -8), (90, 0, -90))}
for f in FRAMES:
    pose_frame(f)
    print("frame", f, "flex l %.1f r %.1f" % (flexion("l"), flexion("r")))
    c = pel()
    for name, (off, r) in VIEWS.items():
        cam.location = c + Vector(off)
        cam.rotation_euler = [math.radians(x) for x in r]
        sc.render.filepath = os.path.join(OUT, f"{TAG}_f{f:03d}_{name}.png"); bpy.ops.render.render(write_still=True)
print("PROBE_OK")
