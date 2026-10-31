"""Normalize the Karin_Original FBX into a source .blend for fit_karin.py (Blender 5.0, background).

blender -b --factory-startup --python prep_karin_original.py -- <Karin(Clone)_BlenderSafe.fbx> <out.blend> <tex_dir>

Karin_Original ships only as VRM + a Unity FBX (no .blend, no texture folder). The FBX armature object is
rotated 90 deg X / scaled 0.01 (Unity centimetres) and its bones carry Unity-style names (LeftUpperArm, LeftToeBase).
- import with automatic bone orientation: every bone's Y points at its child, as fit_karin.py needs it for the
  limb stretch (Karin joint-to-joint vs bone Y) and for the physics chain directions (KP bone = head->tail)
- armature and meshes get their object transforms applied (armature = identity, metres; frame forward -Y, up +Z,
  left +X like the other Karin sources); meshes are re-parented to the armature
- helper empties (PBCollider_*, Anchor Target) are dropped
- packed textures are written to <tex_dir> as Karin_<Face|Alpha|Body|Hair|HairClipping|Costume>.png
Shape keys are kept (fit_karin.py bakes the mix: the outfit "kisekae_*" / underwear keys are set in the FBX).
"""
import bpy, os, sys
from mathutils import Matrix

argv = sys.argv[sys.argv.index("--") + 1:]
fbx, out_blend, tex_dir = argv[0], argv[1], argv[2]
os.makedirs(tex_dir, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=fbx, automatic_bone_orientation=True)
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
arm.name = "KarinOriginalRig"
for o in [o for o in bpy.data.objects if o.type not in ('ARMATURE', 'MESH')]:
    bpy.data.objects.remove(o)
meshes = [o for o in bpy.data.objects if o.type == 'MESH']

# unparent meshes (keep world), apply every object transform, re-parent at identity
world = {o.name: o.matrix_world.copy() for o in meshes}
for o in meshes:
    o.parent = None
    o.matrix_world = world[o.name]
for o in [arm] + meshes:
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
for o in meshes:
    o.parent = arm
    o.matrix_parent_inverse = Matrix.Identity(4)
    mods = [m for m in o.modifiers if m.type == 'ARMATURE']
    assert mods and mods[0].object == arm, o.name

NAMES = {"Karin_Face": "Face", "Karin_Alpha": "Alpha", "Karin_Body": "Body", "Karin_Hair": "Hair",
         "Karin_Hair_Clipping": "HairClipping", "Karin_Costume": "Costume"}
written = {}
for im in bpy.data.images:
    if not im.packed_file:
        continue
    key = next((v for k, v in NAMES.items() if k + "_" in im.name + "_" and (k != "Karin_Hair" or "Clipping" not in im.name)), None)
    if key is None or key in written:
        continue
    p = os.path.join(tex_dir, f"Karin_{key}.png")
    open(p, "wb").write(im.packed_file.data)
    written[key] = (im.name, list(im.size))
print("PREP textures", written)

b = arm.data.bones
for n in ("Hips", "Head", "LeftUpperArm", "LeftHand", "LeftFoot", "LeftToeBase", "Hair_tail_L", "Skirt_0"):
    print("PREP bone", n, [round(x, 4) for x in b[n].head_local], [round(x, 4) for x in b[n].tail_local])
print("PREP meshes", [(o.name, len(o.data.vertices)) for o in meshes], "bones", len(b))
bpy.ops.wm.save_as_mainfile(filepath=out_blend)
print("PREP_OK", out_blend)
