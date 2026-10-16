# Dump the Karin mesh's per-corner data for patching normals into the cooked mesh (Blender 4.2 background).
#
# usage: blender -b <run>/build.blend --python dump_loop_normals.py -- <out.npz>
#
# UE 4.11 imported the FBX with "Compute Normals", which threw away the VRM's authored custom normals (the face ones are
# made for anime shading; without them nose and mouth shade like a realistic face). The npz holds, per corner: the
# position and UV of its vertex, and its custom normal, all in UE space (x, -y, z; V flipped), plus the material index.
import bpy, sys
import numpy as np

out = sys.argv[sys.argv.index("--") + 1]
body = bpy.data.objects["deacon_head_standard"]
me = body.data
co = np.array([v.co for v in me.vertices], dtype=np.float64)
lv = np.array([l.vertex_index for l in me.loops])
uv = np.array([d.uv for d in me.uv_layers[0].data], dtype=np.float64)
cn = np.array([c.vector for c in me.corner_normals], dtype=np.float64)
mat = np.zeros(len(me.loops), dtype=np.int32)
for p in me.polygons:
    mat[p.loop_start:p.loop_start + p.loop_total] = p.material_index
flip = np.array([1.0, -1.0, 1.0])
np.savez(out, pos=co[lv] * flip, uv=np.c_[uv[:, 0], 1.0 - uv[:, 1]], normal=cn * flip, material=mat,
         materials=np.array([s.material.name if s.material else "" for s in body.material_slots]))
print("DUMP_OK", out, len(lv))
