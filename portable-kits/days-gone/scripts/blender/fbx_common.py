# Shared FBX export for UE 4.11 (Blender 4.2).
#
# UE 4.11's FBX importer takes the armature object's FBX null as the root bone. Deacon's skeleton root bone is itself
# called "Armature" (-> "Align" -> "Hips"...), so the armature object is named "Armature" and the "Armature" bone is
# dropped: the null becomes UE's "Armature" root (identity) and "Align" keeps its component-space bind matrix. Only the
# local decomposition of the two animation-driven root bones differs from the game skeleton; every bind matrix used for
# skinning is unchanged.
import bpy

def export_for_ue411(arm, meshes, path, mesh_name):
    for o in list(bpy.data.objects):
        if o not in meshes and o != arm:
            bpy.data.objects.remove(o, do_unlink=True)
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm.data.edit_bones
    root = eb.get("Armature")
    if root is not None:
        for c in list(root.children):
            c.parent = None
        eb.remove(root)
    bpy.ops.object.mode_set(mode="OBJECT")
    for m in meshes:
        g = m.vertex_groups.get("Armature")
        if g is not None:
            m.vertex_groups.remove(g)
    arm.name = "Armature"; arm.data.name = "Armature"
    meshes[0].name = mesh_name; meshes[0].data.name = mesh_name
    bpy.context.scene.unit_settings.scale_length = 0.01
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True)
    for m in meshes: m.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, add_leaf_bones=False, bake_anim=False,
                             use_mesh_modifiers=False, mesh_smooth_type="FACE", use_tspace=False,
                             object_types={"ARMATURE", "MESH"}, primary_bone_axis="Y", secondary_bone_axis="X",
                             armature_nodetype="NULL")
