# Render the built Karin mesh posed with frames of a game animation (SifuExport "anim" json), to check skinning
# issues that only show in motion (midriff gap, skirt vs thighs).
# blender -b karin_sifu.blend --python pose_preview.py -- <anim.json> <out_prefix> [frame_index ...]
# Rotations come from the animation (UE uses them as-is); translations stay at the mesh reference (Skeleton
# retargeting), root stays at rest. Simulated chain bones stay at rest.
import sys, os, json, math
import bpy
from mathutils import Quaternion, Euler, Matrix, Vector
sys.path.insert(0, os.path.dirname(__file__))
import sifu_common as sc

args = sys.argv[sys.argv.index("--") + 1:]
anim = json.load(open(args[0]))
out = args[1]
which = [int(a) for a in args[2:]] or list(range(len(anim["frames"])))
# simulated chain hosts (spare Base_skeleton bones, none of them is a W mesh bone) stay at rest
SIM = ("cloth_", "accessories_", "upperarm_sleeve", "lowerarm_sleeve", "thigh_sleeve", "calf_sleeve")

arm = bpy.data.objects["Armature"]
bones = list(arm.data.bones)
rest_ue = {b.name: sc.bl_to_ue(b.matrix_local) for b in bones}


def ordered(bs):
    done, res = set(), []
    while len(res) < len(bs):
        for b in bs:
            if b.name not in done and (b.parent is None or b.parent.name in done):
                done.add(b.name)
                res.append(b)
    return res


ORDER = ordered(bones)


def apply_frame(fr):
    A = {b["name"]: b for b in fr["bones"]} if fr else {}
    world = {}
    for b in ORDER:
        par = b.parent
        local_rest = rest_ue[par.name].inverted() @ rest_ue[b.name] if par else rest_ue[b.name].copy()
        a = A.get(b.name)
        if a and a["keyed"] and par is not None and not b.name.startswith(SIM):
            x, y, z, w = a["q"]
            local = Quaternion((w, x, y, z)).to_matrix().to_4x4()
            local.translation = local_rest.translation
        else:
            local = local_rest
        world[b.name] = world[par.name] @ local if par else local
    for b in ORDER:
        P = sc.ue_to_bl(world[b.name])
        if b.parent:
            Pp = sc.ue_to_bl(world[b.parent.name])
            basis = (b.parent.matrix_local.inverted() @ b.matrix_local).inverted() @ Pp.inverted() @ P
        else:
            basis = b.matrix_local.inverted() @ P
        arm.pose.bones[b.name].matrix_basis = basis
    bpy.context.view_layer.update()


scn = bpy.context.scene
scn.render.engine = "BLENDER_WORKBENCH"
scn.display.shading.light = "STUDIO"
scn.display.shading.color_type = "TEXTURE"
scn.render.resolution_x, scn.render.resolution_y = 520, 640
for o in bpy.data.objects:
    if o.type == "MESH" and o.name.startswith("Proxy_"):
        o.hide_render = True
cam_data = bpy.data.cameras.new("cam")
cam_data.type = "ORTHO"
cam_data.ortho_scale = 95
cam_data.clip_end = 10000
cam = bpy.data.objects.new("cam", cam_data)
scn.collection.objects.link(cam)
scn.camera = cam
# Karin faces -Y in this scene
VIEWS = {"side": ((260, 0, 100), (math.radians(90), 0, math.radians(90))),
         "front": ((0, -260, 100), (math.radians(90), 0, 0)),
         "q34": ((190, -190, 100), (math.radians(90), 0, math.radians(45)))}


def belly_camera(back=False):
    """Camera square to the posed waist (front or back): spine_02 along the posed body forward (rest forward is -Y)."""
    b = arm.data.bones["spine_02"]
    P = arm.matrix_world @ arm.pose.bones["spine_02"].matrix
    R = P.to_3x3() @ (arm.matrix_world @ b.matrix_local).to_3x3().inverted()
    fwd, up = R @ Vector((0, 1 if back else -1, 0)), R @ Vector((0, 0, 1))
    c = P.translation + up * 1.0
    z = fwd.normalized()                      # camera looks down -Z, i.e. back at the belly
    x = up.cross(z).normalized()
    y = z.cross(x)
    m = Matrix((x, y, z)).transposed().to_4x4()
    m.translation = c + fwd * 200
    return m


VIEWS["belly"] = None
VIEWS["back"] = None
for fi in ["rest"] + which:
    apply_frame(None if fi == "rest" else anim["frames"][fi])
    for vn, v in VIEWS.items():
        if v is None:
            cam.matrix_world = belly_camera(vn == "back")
            cam_data.ortho_scale = 45
        else:
            cam.location = v[0]
            cam.rotation_euler = Euler(v[1])
            cam_data.ortho_scale = 95
        scn.render.filepath = f"{out}_{fi}_{vn}.png"
        bpy.ops.render.render(write_still=True)
print("POSE_PREVIEW_DONE")
