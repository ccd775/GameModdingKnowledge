# Builds an FBX carrying the exact Sifu Base_skeleton (all bones) plus one tiny tetra per bone, so that importing it in
# UE creates an editor-side /Game/Characters/Skeleton/Base_skeleton and lets us verify the axis/orientation pipeline.
# Usage: blender -b --factory-startup --python make_skeleton_fbx.py -- <Base_skeleton.skel.json> <out.fbx>
import os, sys
import bpy, bmesh
from mathutils import Vector
sys.path.insert(0, os.path.dirname(__file__))
import sifu_common as sc

skel_json, out_fbx = sys.argv[sys.argv.index("--") + 1:][:2]
bpy.ops.wm.read_factory_settings(use_empty=True)
sc.setup_cm_scene()
bones = sc.load_skel(skel_json)
world_ue = sc.ue_world(bones)
world_bl = {n: sc.ue_to_bl(m) for n, m in world_ue.items()}
arm = sc.build_armature("Armature", bones, world_bl)

me = bpy.data.meshes.new("SK_BaseSkeleton")
bm = bmesh.new()
groups = []
s = 0.4
for b in bones:
    p = world_bl[b["name"]].translation
    vs = [bm.verts.new(p + Vector(o)) for o in ((s, 0, 0), (0, s, 0), (0, 0, s), (-s, -s, -s))]
    for f in ((0, 1, 2), (0, 3, 1), (1, 3, 2), (2, 3, 0)):
        bm.faces.new([vs[i] for i in f])
    groups.append(b["name"])
bm.to_mesh(me)
bm.free()
obj = bpy.data.objects.new("SK_BaseSkeleton", me)
bpy.context.scene.collection.objects.link(obj)
for i, n in enumerate(groups):
    vg = obj.vertex_groups.new(name=n)
    vg.add([i * 4 + k for k in range(4)], 1.0, "REPLACE")
obj.parent = arm
mod = obj.modifiers.new("Armature", "ARMATURE")
mod.object = arm
sc.export_fbx(out_fbx, [arm, obj])
print("wrote", out_fbx)
