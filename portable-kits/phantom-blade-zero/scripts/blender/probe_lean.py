# blender -b <run>/build.blend --python probe_lean.py -- <out_prefix> [--lean 15] [--twist 10] [--head-fixed 1]
#                                                       [--views side,rside,qback] [--center-z 112]
# Pose probe for cloth that hangs from the head (long hair) over clothing that moves with the torso: leans the torso
# forward at spine_01 (degrees about the lateral axis) and twists it at spine_03 (about the vertical axis), keeps the
# head at its rest world orientation (as the run animations hold it level and facing forward), then renders the skinned
# body with no simulation. Hair slots are blue (tails red), the rest grey; the *Sim shells are hidden. Whatever
# hair the jacket swallows here, the cloth's anim drive, max distance and backstop are all centred inside the jacket.
# (Lenko round 4, 2026-11-03: lk3 back hair skinned to the head alone disappeared into the jacket at a 15 degree lean;
# head -> spine_05 blend kept it outside; a split over the spine bones kinked every strand under a 10 degree twist.)
import bpy, sys, math, argparse
from mathutils import Matrix, Vector

ap = argparse.ArgumentParser(prog="probe_lean.py", description="Lean / twist pose probe of a build_*.py build.blend "
                             "(run inside Blender: blender -b build.blend --python probe_lean.py -- <out_prefix> ...)")
ap.add_argument("out_prefix", help="PNG path prefix; writes <prefix>_<view>.png")
ap.add_argument("--lean", type=float, default=15.0, help="forward lean at spine_01, degrees")
ap.add_argument("--twist", type=float, default=10.0, help="torso twist at spine_03, degrees")
ap.add_argument("--head-fixed", type=int, default=1, help="1: head back to its rest world orientation")
ap.add_argument("--views", default="side,rside,qback", help="comma list of side, rside, back, qback")
ap.add_argument("--center-z", type=float, default=112.0, help="camera target height, cm")
args = ap.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["--help"])

body = bpy.data.objects["SK_Karin_Body"]; arm = body.parent
sc = bpy.context.scene
for o in bpy.data.objects:
    if o.type == "MESH": o.hide_render = o.name != "SK_Karin_Body"
mats = [s.material.name for s in body.material_slots]
me = body.data
for p in me.polygons:   # simulation shells are not rendered in game
    if mats[p.material_index].endswith("Sim"):
        for v in p.vertices: me.vertices[v].co.z -= 1000.0
def colour(n):
    if "Hair" in n: return (0.9, 0.1, 0.1) if "Tail" in n else (0.15, 0.3, 0.95)
    if any(k in n for k in ("Coat", "Jacket")): return (0.85, 0.85, 0.85)
    return (0.6, 0.55, 0.5)
for i, n in enumerate(mats):
    m = bpy.data.materials.new("P_" + n); m.diffuse_color = (*colour(n), 1.0); body.material_slots[i].material = m
sc.render.engine = "BLENDER_WORKBENCH"; sc.display.shading.color_type = "MATERIAL"; sc.display.shading.light = "STUDIO"

def rot_world(bname, axis, deg):
    pb = arm.pose.bones[bname]
    h = arm.matrix_world @ pb.head
    R = Matrix.Translation(h) @ Matrix.Rotation(math.radians(deg), 4, axis) @ Matrix.Translation(-h)
    pb.matrix = arm.matrix_world.inverted() @ R @ arm.matrix_world @ pb.matrix
    bpy.context.view_layer.update()
head_rest = (arm.matrix_world @ arm.pose.bones["head"].matrix).to_3x3().copy()
rot_world("spine_01", "X", args.lean)    # +X rotation moves the top toward -Y, the front
rot_world("spine_03", "Z", args.twist)
if args.head_fixed:
    pb = arm.pose.bones["head"]; hw = arm.matrix_world @ pb.matrix
    pb.matrix = arm.matrix_world.inverted() @ (Matrix.Translation(hw.to_translation()) @ head_rest.to_4x4())
    bpy.context.view_layer.update()

cd = bpy.data.cameras.new("c"); cd.type = "ORTHO"; cam = bpy.data.objects.new("c", cd); sc.collection.objects.link(cam); sc.camera = cam
DIRS = {"side": (1, 0, 0), "rside": (-1, 0, 0), "back": (0, 1, 0), "qback": (0.6, 0.8, 0.1)}
C = Vector((0, 8, args.center_z))
for v in args.views.split(","):
    sc.render.resolution_x, sc.render.resolution_y = 700, 900
    cd.ortho_scale = 80.0; cam.location = C + Vector(DIRS[v]) * 500
    cam.rotation_euler = (C - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = f"{args.out_prefix}_{v}.png"; bpy.ops.render.render(write_still=True)
print("LEAN_OK")
