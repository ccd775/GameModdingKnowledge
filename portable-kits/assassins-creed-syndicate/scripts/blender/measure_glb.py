"""Measure an AnvilToolkit GLB in Blender: per-mesh evaluated (skinned rest) bounds in the import frame.

  blender -b --factory-startup --python measure_glb.py -- <file.glb>

The fit frame (after glb_rotate.py +90, as imported): forward +X, up -Y, left +Z; "sole" = the lowest point = max Y.
"""
import sys

import bpy

glb = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb, merge_vertices=False, import_shading='NORMALS', guess_original_bind_pose=True,
                          bone_heuristic='BLENDER')
dg = bpy.context.evaluated_depsgraph_get()
for o in bpy.data.objects:
    if o.type != 'MESH':
        continue
    e = o.evaluated_get(dg)
    m = e.to_mesh()
    pts = [e.matrix_world @ v.co for v in m.vertices]
    lo = [min(p[i] for p in pts) for i in range(3)]
    hi = [max(p[i] for p in pts) for i in range(3)]
    print(f"MEASURE {o.name}: verts {len(pts)} min ({lo[0]:.4f}, {lo[1]:.4f}, {lo[2]:.4f}) "
          f"max ({hi[0]:.4f}, {hi[1]:.4f}, {hi[2]:.4f})")
    e.to_mesh_clear()
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE']
for a in arm:
    for n in ("Hips", "Head", "LeftFoot", "LeftFootThumb1"):
        b = a.data.bones.get(n)
        if b:
            p = a.matrix_world @ b.head_local
            print(f"MEASURE bone {n}: ({p[0]:.4f}, {p[1]:.4f}, {p[2]:.4f})")
