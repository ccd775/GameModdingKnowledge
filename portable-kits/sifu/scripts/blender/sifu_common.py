# Shared helpers for Blender-side Sifu authoring.
# UE (left-handed, Z up, cm)  <->  Blender export scene (right-handed, Z up, unit scale 0.01 => 1 BU = 1 cm):
#   p_bl = C p_ue,  R_bl = C R_ue C,  C = diag(1,-1,1).  Source models in meters are scaled by 100 before export.
import json
import os
import bpy
from mathutils import Matrix, Quaternion, Vector

C3 = Matrix(((1, 0, 0), (0, -1, 0), (0, 0, 1)))


def ue_local(b):
    """UE local transform (dict with t, q[x,y,z,w], s) -> 4x4 in UE space (cm)."""
    x, y, z, w = b["q"]
    m = Quaternion((w, x, y, z)).to_matrix().to_4x4()
    sx, sy, sz = b["s"]
    m = m @ Matrix.Diagonal((sx, sy, sz, 1.0))
    m.translation = Vector(b["t"])
    return m


def ue_world(bones):
    """bones: list in index order with parent indices -> {name: 4x4 UE world (cm)}."""
    out = {}
    names = [b["name"] for b in bones]
    for b in bones:
        loc = ue_local(b)
        out[b["name"]] = out[names[b["parent"]]] @ loc if b["parent"] >= 0 else loc
    return out


def ue_to_bl(m):
    """4x4 UE world (cm) -> 4x4 Blender world (m)."""
    r = C3 @ m.to_3x3() @ C3
    t = C3 @ m.translation
    out = r.to_4x4()
    out.translation = t
    return out


def bl_to_ue(m):
    r = C3 @ m.to_3x3() @ C3
    t = C3 @ m.translation
    out = r.to_4x4()
    out.translation = t
    return out


def load_skel(path):
    d = json.load(open(path))
    return d["bones"]


# SifuExport "skel" dump of Sifu/Content/Characters/Skeleton/Base_skeleton: build_cfg "base_skel" or SIFU_BASE_SKEL.
BASE_SKEL = os.environ.get("SIFU_BASE_SKEL")


def skel_parents(path=None):
    """{bone: parent} of the game's Base_skeleton (dynamics chains may only use its bones, with its parents)."""
    if not (path or BASE_SKEL):
        raise RuntimeError('Base_skeleton json: set "base_skel" in build_cfg.json or the environment variable SIFU_BASE_SKEL')
    bones = load_skel(path or BASE_SKEL)
    names = [b["name"] for b in bones]
    return {b["name"]: (names[b["parent"]] if b["parent"] >= 0 else None) for b in bones}


def setup_cm_scene():
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 0.01


def build_armature(name, bones, world_bl, bone_len=3.0, collection=None):
    """Create an armature whose edit-bone matrices equal world_bl[name] (Blender world)."""
    arm = bpy.data.armatures.new(name)
    obj = bpy.data.objects.new(name, arm)
    (collection or bpy.context.scene.collection).objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    ebs = {}
    for b in bones:
        eb = arm.edit_bones.new(b["name"])
        eb.head = (0, 0, 0)
        eb.tail = (0, bone_len, 0)
        eb.matrix = world_bl[b["name"]]
        ebs[b["name"]] = eb
    names = [b["name"] for b in bones]
    for b in bones:
        if b["parent"] >= 0:
            ebs[b["name"]].parent = ebs[names[b["parent"]]]
            ebs[b["name"]].use_connect = False
    bpy.ops.object.mode_set(mode="OBJECT")
    return obj


def export_fbx(path, objects):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objects:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.export_scene.fbx(
        filepath=path, use_selection=True, object_types={"ARMATURE", "MESH"},
        apply_unit_scale=True, apply_scale_options="FBX_SCALE_NONE", global_scale=1.0,
        axis_forward="-Z", axis_up="Y", bake_space_transform=False,
        use_mesh_modifiers=True, mesh_smooth_type="FACE", use_tspace=False,
        add_leaf_bones=False, primary_bone_axis="Y", secondary_bone_axis="X",
        use_armature_deform_only=False, armature_nodetype="NULL",
        bake_anim=False, path_mode="STRIP", embed_textures=False, colors_type="LINEAR")
